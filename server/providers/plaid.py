"""Integración con Plaid (sandbox y producción).

No se usa el SDK: las llamadas pasan por httpx y por el firewall de salida.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from libreta.core.dates import now_iso
from libreta.services.categorizer import suggest_category
from libreta.services.ledger import Ledger

from ..config import Settings
from ..firewall import FirewallError, OutboundFirewall
from ..store import BankLink, ServerStore


class PlaidError(RuntimeError):
    pass


@dataclass(slots=True)
class SyncStats:
    accounts: int = 0
    added: int = 0
    modified: int = 0
    removed: int = 0
    new_events: list[tuple[dict, dict]] = field(default_factory=list)


PLAID_CATEGORY_MAP = {
    "FOOD_AND_DRINK_COFFEE": "coffee",
    "FOOD_AND_DRINK_RESTAURANT": "food",
    "FOOD_AND_DRINK_FAST_FOOD": "food",
    "FOOD_AND_DRINK_GROCERIES": "groceries",
    "TRANSPORTATION_TAXIS_AND_RIDE_SHARES": "transport",
    "TRANSPORTATION_PUBLIC_TRANSIT": "transport",
    "TRANSPORTATION_GAS": "transport",
    "TRANSPORTATION_PARKING": "transport",
    "HOME_IMPROVEMENT": "home",
    "RENT_AND_UTILITIES": "bills",
    "MEDICAL": "health",
    "ENTERTAINMENT": "fun",
    "GENERAL_MERCHANDISE": "shopping",
    "GENERAL_SERVICES": "bills",
    "TRAVEL": "travel",
    "EDUCATION": "education",
    "INCOME": "income",
    "TRANSFER_IN": "income",
    "TRANSFER_OUT": "other",
}

PRIMARY_MAP = {
    "FOOD_AND_DRINK": "food",
    "TRANSPORTATION": "transport",
    "HOME_IMPROVEMENT": "home",
    "RENT_AND_UTILITIES": "bills",
    "MEDICAL": "health",
    "ENTERTAINMENT": "fun",
    "GENERAL_MERCHANDISE": "shopping",
    "GENERAL_SERVICES": "bills",
    "TRAVEL": "travel",
    "EDUCATION": "education",
    "INCOME": "income",
    "TRANSFER_IN": "income",
}

ACCOUNT_COLORS = ["#146EF5", "#0F6B54", "#8B5CF6", "#D9883A", "#D95D70", "#2F8F9D"]


class PlaidProvider:
    def __init__(self, config: Settings, firewall: OutboundFirewall):
        self.config = config
        self.firewall = firewall
        self.base_url = (
            "https://production.plaid.com"
            if config.plaid_env.lower() == "production"
            else "https://sandbox.plaid.com"
        )

    def _post(self, path: str, payload: dict) -> dict:
        body = dict(payload)
        body["client_id"] = self.config.plaid_client_id
        body["secret"] = self.config.plaid_secret
        try:
            response = self.firewall.post(
                f"{self.base_url}{path}",
                json=body,
                headers={"Content-Type": "application/json"},
            )
        except FirewallError as exc:
            raise PlaidError(str(exc)) from exc
        try:
            data = response.json()
        except Exception as exc:
            raise PlaidError(f"Respuesta inválida de Plaid ({response.status_code})") from exc
        if response.status_code >= 400:
            message = data.get("error_message") or data.get("display_message") or "Error de Plaid"
            code = data.get("error_code") or response.status_code
            raise PlaidError(f"Plaid {code}: {message}")
        return data

    def create_link_token(self, webhook_url: str | None = None) -> str:
        payload = {
            "user": {"client_user_id": "libreta-owner"},
            "client_name": "Sapardobank",
            "products": ["transactions"],
            "country_codes": self.config.countries,
            "language": "es",
        }
        if webhook_url:
            payload["webhook"] = webhook_url
        data = self._post("/link/token/create", payload)
        token = data.get("link_token")
        if not token:
            raise PlaidError("Plaid no devolvió link_token")
        return token

    def exchange_public_token(self, public_token: str) -> dict:
        return self._post("/item/public_token/exchange", {"public_token": public_token})

    def _accounts(self, access_token: str) -> list[dict]:
        data = self._post("/accounts/get", {"access_token": access_token})
        return data.get("accounts", [])

    def _tx_sync(self, access_token: str, cursor: str | None) -> dict:
        return self._post(
            "/transactions/sync",
            {
                "access_token": access_token,
                "cursor": cursor or "",
                "count": 500,
                "options": {"include_personal_finance_category": True},
            },
        )

    def sync_link(
        self,
        link: BankLink,
        ledger: Ledger,
        store: ServerStore,
        *,
        notify: bool = False,
        max_pages: int = 30,
    ) -> SyncStats:
        stats = SyncStats()
        accounts = self._accounts(link.access_token)
        account_map: dict[str, str] = {}
        currency_map: dict[str, str] = {}
        for index, account in enumerate(accounts):
            plaid_id = str(account.get("account_id") or "")
            if not plaid_id:
                continue
            local_id = f"plaid_{plaid_id}"
            account_map[plaid_id] = local_id
            balances = account.get("balances") or {}
            amount = balances.get("available")
            if amount is None:
                amount = balances.get("current")
            balance_cents = int(round(float(amount or 0) * 100))
            kind = self._account_kind(account)
            currency = balances.get("iso_currency_code") or "USD"
            currency_map[local_id] = currency
            ledger.upsert_remote_account(
                account_id=local_id,
                name=account.get("name") or account.get("official_name") or "Cuenta bancaria",
                institution=link.institution or "Banco vinculado",
                kind=kind,
                currency=currency,
                balance_cents=balance_cents,
                color=ACCOUNT_COLORS[index % len(ACCOUNT_COLORS)],
                icon=self._account_icon(kind),
                provider="plaid",
                provider_ref=link.item_id,
                last_sync_at=now_iso(),
            )
        stats.accounts = len(account_map)

        cursor = link.cursor
        for _ in range(max_pages):
            data = self._tx_sync(link.access_token, cursor)
            added = data.get("added", []) or []
            modified = data.get("modified", []) or []
            removed = data.get("removed", []) or []
            for raw in [*added, *modified]:
                local_account = account_map.get(str(raw.get("account_id")))
                if not local_account:
                    continue
                tx, created = self._apply_transaction(
                    ledger,
                    link,
                    raw,
                    local_account,
                    currency_map.get(local_account, "USD"),
                )
                if created:
                    stats.added += 1
                    if notify:
                        stats.new_events.append((tx, local_account))
                else:
                    stats.modified += 1
            for raw in removed:
                if ledger.mark_external_deleted(str(raw.get("transaction_id") or "")):
                    stats.removed += 1
            cursor = data.get("next_cursor") or cursor
            store.update_link_sync(link.item_id, cursor)
            if not data.get("has_more"):
                break
        return stats

    def _apply_transaction(
        self, ledger: Ledger, link: BankLink, raw: dict, account_id: str, currency: str
    ):
        amount = float(raw.get("amount") or 0)
        amount_cents = -int(round(amount * 100))
        if amount_cents == 0:
            amount_cents = -1
        description = raw.get("merchant_name") or raw.get("name") or "Movimiento bancario"
        merchant = raw.get("merchant_name")
        category = self.map_category(raw, amount_cents)
        occurred = self._occurred_at(raw)
        tx, created = ledger.upsert_external_transaction(
            account_id=account_id,
            external_id=str(raw.get("transaction_id") or ""),
            amount_cents=amount_cents,
            description=description,
            occurred_at=occurred,
            category_id=category,
            merchant=merchant,
            pending=bool(raw.get("pending")),
            source="plaid",
            raw_json=json.dumps(raw, ensure_ascii=False),
            currency=currency,
        )
        return ledger.serialize_transaction(tx), created

    def map_category(self, raw: dict, amount_cents: int) -> str:
        if amount_cents > 0:
            return "income"
        pfc = raw.get("personal_finance_category") or {}
        detailed = str(pfc.get("detailed") or "").upper()
        primary = str(pfc.get("primary") or "").upper()
        if detailed in PLAID_CATEGORY_MAP:
            return PLAID_CATEGORY_MAP[detailed]
        if primary in PRIMARY_MAP:
            return PRIMARY_MAP[primary]
        suggested = suggest_category(raw.get("merchant_name"), raw.get("name"))
        return suggested if suggested != "other" else "other"

    @staticmethod
    def _occurred_at(raw: dict) -> str:
        value = raw.get("authorized_datetime") or raw.get("datetime")
        if value:
            try:
                dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                return dt.astimezone().replace(tzinfo=None).replace(microsecond=0).isoformat()
            except ValueError:
                pass
        date_value = raw.get("authorized_date") or raw.get("date")
        if date_value:
            return f"{str(date_value)[:10]}T12:00:00"
        return now_iso()

    @staticmethod
    def _account_kind(account: dict) -> str:
        type_ = str(account.get("type") or "").lower()
        subtype = str(account.get("subtype") or "").lower()
        if type_ == "credit" or type_ == "loan":
            return "credit"
        if type_ == "investment":
            return "investment"
        if subtype in {"savings", "cd", "money market"}:
            return "savings"
        return "debit"

    @staticmethod
    def _account_icon(kind: str) -> str:
        return {
            "credit": "CREDIT_CARD_ROUNDED",
            "investment": "SHOW_CHART_ROUNDED",
            "savings": "SAVINGS_ROUNDED",
        }.get(kind, "ACCOUNT_BALANCE_WALLET_ROUNDED")
