"""Repositorio y reglas del libro de gastos."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Iterable, Sequence
from urllib.parse import quote

from ..core.catalog import CATEGORIES
from ..core.dates import month_bounds, now_iso
from ..core.db import Database
from ..core.models import (
    Account,
    Category,
    CategoryTotal,
    DailyPoint,
    Totals,
    Transaction,
    TransactionView,
)
from ..core.money import split_sign
from .categorizer import suggest_category


class LedgerError(ValueError):
    pass


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:20]}"


def _row_account(row) -> Account:
    return Account(
        id=row["id"],
        name=row["name"],
        institution=row["institution"],
        kind=row["kind"],
        currency=row["currency"],
        initial_balance_cents=row["initial_balance_cents"],
        balance_cents=row["balance_cents"],
        color=row["color"],
        icon=row["icon"],
        provider=row["provider"],
        provider_ref=row["provider_ref"],
        last_sync_at=row["last_sync_at"],
        is_demo=bool(row["is_demo"]),
        is_archived=bool(row["is_archived"]),
        created_at=row["created_at"],
    )


def _row_category(row) -> Category:
    return Category(
        id=row["id"],
        name=row["name"],
        icon=row["icon"],
        color=row["color"],
        kind=row["kind"],
        sort_order=row["sort_order"],
        builtin=bool(row["builtin"]),
    )


def _row_transaction(row) -> Transaction:
    keys = row.keys()
    return Transaction(
        id=row["id"],
        account_id=row["account_id"],
        amount_cents=row["amount_cents"],
        currency=row["currency"],
        description=row["description"],
        merchant=row["merchant"],
        category_id=row["category_id"],
        occurred_at=row["occurred_at"],
        created_at=row["created_at"],
        source=row["source"],
        external_id=row["external_id"],
        pending=bool(row["pending"]),
        notes=row["notes"],
        sync_state=row["sync_state"],
        deleted=bool(row["deleted"]),
        raw_json=row["raw_json"] if "raw_json" in keys else None,
    )


class Ledger:
    def __init__(self, db: Database):
        self.db = db

    # ------------------------------------------------------------------ cuentas

    def accounts(self, *, include_archived: bool = False) -> list[Account]:
        where = "" if include_archived else "WHERE is_archived = 0"
        rows = self.db.query(
            f"SELECT * FROM accounts {where} ORDER BY is_demo DESC, created_at ASC"
        )
        return [_row_account(r) for r in rows]

    def account(self, account_id: str) -> Account | None:
        row = self.db.query_one("SELECT * FROM accounts WHERE id = ?", (account_id,))
        return _row_account(row) if row else None

    def demo_account(self) -> Account | None:
        row = self.db.query_one(
            "SELECT * FROM accounts WHERE is_demo = 1 AND is_archived = 0 "
            "ORDER BY created_at LIMIT 1"
        )
        return _row_account(row) if row else None

    def create_account(
        self,
        name: str,
        *,
        institution: str = "",
        kind: str = "debit",
        currency: str = "MXN",
        initial_balance_cents: int = 0,
        color: str = "#0F6B54",
        icon: str = "ACCOUNT_BALANCE_WALLET_ROUNDED",
        provider: str = "manual",
        provider_ref: str | None = None,
        is_demo: bool = False,
    ) -> Account:
        name = (name or "").strip()
        if not name:
            raise LedgerError("Ponle un nombre a la cuenta")
        account_id = _new_id("acc")
        balance_cents = initial_balance_cents if provider in {"manual", "cash"} else None
        self.db.execute(
            """INSERT INTO accounts
            (id, name, institution, kind, currency, initial_balance_cents, balance_cents,
             color, icon, provider, provider_ref, last_sync_at, is_demo, is_archived, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (
                account_id,
                name,
                institution.strip(),
                kind,
                currency,
                int(initial_balance_cents),
                balance_cents,
                color,
                icon,
                provider,
                provider_ref,
                None,
                1 if is_demo else 0,
                now_iso(),
            ),
        )
        return self.account(account_id)  # type: ignore[return-value]

    def update_account(self, account_id: str, **fields) -> Account:
        allowed = {
            "name", "institution", "kind", "color", "icon", "initial_balance_cents",
            "balance_cents", "provider", "provider_ref", "last_sync_at", "is_archived",
        }
        values = {k: v for k, v in fields.items() if k in allowed}
        if not values:
            return self.account(account_id)  # type: ignore[return-value]
        assignments = ", ".join(f"{key} = ?" for key in values)
        self.db.execute(
            f"UPDATE accounts SET {assignments} WHERE id = ?",
            (*values.values(), account_id),
        )
        account = self.account(account_id)
        if not account:
            raise LedgerError("Cuenta no encontrada")
        return account

    def upsert_remote_account(
        self,
        *,
        account_id: str,
        name: str,
        institution: str = "",
        kind: str = "debit",
        currency: str = "MXN",
        balance_cents: int | None = None,
        color: str = "#0F6B54",
        icon: str = "ACCOUNT_BALANCE_WALLET_ROUNDED",
        provider: str = "plaid",
        provider_ref: str | None = None,
        last_sync_at: str | None = None,
    ) -> Account:
        existing = self.account(account_id)
        if existing:
            self.db.execute(
                """UPDATE accounts SET name = ?, institution = ?, kind = ?, currency = ?,
                   balance_cents = ?, color = ?, icon = ?, provider = ?, provider_ref = ?,
                   last_sync_at = ?, is_archived = 0 WHERE id = ?""",
                (
                    name, institution, kind, currency, balance_cents, color, icon,
                    provider, provider_ref, last_sync_at, account_id,
                ),
            )
        else:
            self.db.execute(
                """INSERT INTO accounts
                (id, name, institution, kind, currency, initial_balance_cents, balance_cents,
                 color, icon, provider, provider_ref, last_sync_at, is_demo, is_archived, created_at)
                VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, 0, 0, ?)""",
                (
                    account_id, name, institution, kind, currency, balance_cents,
                    color, icon, provider, provider_ref, last_sync_at, now_iso(),
                ),
            )
        return self.account(account_id)  # type: ignore[return-value]

    def archive_account(self, account_id: str) -> None:
        self.db.execute("UPDATE accounts SET is_archived = 1 WHERE id = ?", (account_id,))

    def set_provider_balance(
        self, account_id: str, balance_cents: int | None, last_sync_at: str | None = None
    ) -> None:
        self.db.execute(
            "UPDATE accounts SET balance_cents = ?, last_sync_at = ? WHERE id = ?",
            (balance_cents, last_sync_at or now_iso(), account_id),
        )

    def account_balance(self, account: Account) -> int:
        if account.provider not in {"manual", "cash", "demo"} and account.balance_cents is not None:
            return int(account.balance_cents)
        net = self.db.scalar(
            "SELECT COALESCE(SUM(amount_cents), 0) FROM transactions "
            "WHERE account_id = ? AND deleted = 0",
            (account.id,),
        )
        return int(account.initial_balance_cents) + int(net)

    def total_balance(self) -> int:
        return sum(self.account_balance(a) for a in self.accounts())

    # --------------------------------------------------------------- categorías

    def categories(self, kind: str | None = None) -> list[Category]:
        if kind:
            rows = self.db.query(
                "SELECT * FROM categories WHERE kind = ? ORDER BY sort_order, name",
                (kind,),
            )
        else:
            rows = self.db.query("SELECT * FROM categories ORDER BY sort_order, name")
        return [_row_category(r) for r in rows]

    def category(self, category_id: str | None) -> Category | None:
        if not category_id:
            return None
        row = self.db.query_one("SELECT * FROM categories WHERE id = ?", (category_id,))
        return _row_category(row) if row else None

    def ensure_categories(self) -> None:
        for cid, name, icon, color, kind, order in CATEGORIES:
            self.db.execute(
                """INSERT OR IGNORE INTO categories
                (id, name, icon, color, kind, sort_order, builtin)
                VALUES (?, ?, ?, ?, ?, ?, 1)""",
                (cid, name, icon, color, kind, order),
            )

    # ------------------------------------------------------------- movimientos

    def add_transaction(
        self,
        *,
        account_id: str,
        amount_cents: int,
        description: str = "",
        category_id: str | None = None,
        occurred_at: str | None = None,
        kind: str | None = None,
        merchant: str | None = None,
        source: str = "manual",
        external_id: str | None = None,
        pending: bool = False,
        notes: str | None = None,
        currency: str | None = None,
        sync_state: str | None = None,
        raw_json: str | None = None,
    ) -> Transaction:
        account = self.account(account_id)
        if not account:
            raise LedgerError("Elige una cuenta válida")
        if account.is_archived:
            raise LedgerError("Esa cuenta está archivada")

        amount = split_sign(amount_cents, kind) if kind else int(amount_cents)
        if amount == 0:
            raise LedgerError("El monto no puede ser cero")

        category = self.category(category_id) if category_id else None
        if category is None:
            fallback = "income" if amount > 0 else suggest_category(description, merchant)
            category = self.category(fallback) or self.category("other")
        description = (description or "").strip()
        if not description:
            description = category.name if category else ("Ingreso" if amount > 0 else "Gasto")

        external_id = (external_id or "").strip() or None
        if external_id:
            existing = self.db.query_one(
                "SELECT * FROM transactions WHERE account_id = ? AND external_id = ?",
                (account_id, external_id),
            )
            if existing:
                return _row_transaction(existing)

        tx_id = _new_id("tx")
        created = now_iso()
        occurred = occurred_at or created
        currency = currency or account.currency
        state = sync_state or ("synced" if source != "manual" else "local")
        self.db.execute(
            """INSERT INTO transactions
            (id, account_id, amount_cents, currency, description, merchant, category_id,
             occurred_at, created_at, source, external_id, pending, notes, sync_state,
             deleted, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (
                tx_id,
                account_id,
                amount,
                currency,
                description[:240],
                (merchant or "").strip() or None,
                category.id if category else None,
                occurred,
                created,
                source,
                external_id,
                1 if pending else 0,
                notes,
                state,
                raw_json,
            ),
        )
        return self.transaction(tx_id)  # type: ignore[return-value]

    def upsert_external_transaction(
        self,
        *,
        account_id: str,
        external_id: str,
        amount_cents: int,
        description: str,
        occurred_at: str,
        category_id: str | None = None,
        merchant: str | None = None,
        pending: bool = False,
        source: str = "bank",
        raw_json: str | None = None,
        currency: str = "MXN",
    ) -> tuple[Transaction, bool]:
        existing = self.db.query_one(
            "SELECT * FROM transactions WHERE account_id = ? AND external_id = ?",
            (account_id, external_id),
        )
        if existing:
            self.db.execute(
                """UPDATE transactions SET amount_cents = ?, description = ?,
                   occurred_at = ?, category_id = COALESCE(?, category_id),
                   merchant = COALESCE(?, merchant), pending = ?, raw_json = ?
                   WHERE id = ?""",
                (
                    int(amount_cents), description[:240], occurred_at, category_id,
                    merchant, 1 if pending else 0, raw_json, existing["id"],
                ),
            )
            return self.transaction(existing["id"]), False  # type: ignore[return-value]

        category = self.category(category_id) if category_id else None
        if category is None:
            category = self.category(
                "income" if amount_cents > 0 else suggest_category(description, merchant)
            )
        created = self.add_transaction(
            account_id=account_id,
            amount_cents=amount_cents,
            description=description,
            category_id=category.id if category else None,
            occurred_at=occurred_at,
            merchant=merchant,
            source=source,
            external_id=external_id,
            pending=pending,
            sync_state="synced",
            raw_json=raw_json,
            currency=currency,
        )
        return created, True

    def transaction(self, tx_id: str) -> Transaction | None:
        row = self.db.query_one("SELECT * FROM transactions WHERE id = ?", (tx_id,))
        return _row_transaction(row) if row else None

    def update_transaction(self, tx_id: str, **fields) -> Transaction:
        current = self.transaction(tx_id)
        if not current:
            raise LedgerError("Movimiento no encontrado")
        allowed = {
            "account_id", "amount_cents", "description", "merchant", "category_id", "occurred_at",
            "notes", "pending", "sync_state", "deleted",
        }
        values = {k: v for k, v in fields.items() if k in allowed}
        if "account_id" in values and not self.account(values["account_id"]):
            raise LedgerError("Cuenta inválida")
        if "amount_cents" in values:
            amount = int(values["amount_cents"])
            if amount == 0:
                raise LedgerError("El monto no puede ser cero")
            values["amount_cents"] = amount
        if not values:
            return current
        if "category_id" in values and values["category_id"] is not None:
            if not self.category(values["category_id"]):
                raise LedgerError("Categoría inválida")
        assignments = ", ".join(f"{key} = ?" for key in values)
        self.db.execute(
            f"UPDATE transactions SET {assignments} WHERE id = ?",
            (*values.values(), tx_id),
        )
        updated = self.transaction(tx_id)
        if not updated:
            raise LedgerError("Movimiento no encontrado")
        return updated

    def delete_transaction(self, tx_id: str) -> None:
        self.db.execute(
            "UPDATE transactions SET deleted = 1, sync_state = 'deleted' WHERE id = ?",
            (tx_id,),
        )

    def restore_transaction(self, tx_id: str) -> None:
        self.db.execute(
            "UPDATE transactions SET deleted = 0, sync_state = 'local' WHERE id = ?",
            (tx_id,),
        )

    def transaction_views(
        self,
        *,
        start: str | None = None,
        end: str | None = None,
        account_id: str | None = None,
        kind: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TransactionView]:
        clauses = ["t.deleted = 0", "a.is_archived = 0"]
        params: list = []
        if start:
            clauses.append("t.occurred_at >= ?")
            params.append(start)
        if end:
            clauses.append("t.occurred_at < ?")
            params.append(end)
        if account_id:
            clauses.append("t.account_id = ?")
            params.append(account_id)
        if kind == "expense":
            clauses.append("t.amount_cents < 0")
        elif kind == "income":
            clauses.append("t.amount_cents > 0")
        if search:
            clauses.append(
                "(LOWER(t.description) LIKE ? OR LOWER(COALESCE(t.merchant, '')) LIKE ?)"
            )
            needle = f"%{search.lower()}%"
            params.extend([needle, needle])
        params.extend([max(1, limit), max(0, offset)])
        rows = self.db.query(
            f"""SELECT t.*, c.name AS category_name, c.icon AS category_icon,
                       c.color AS category_color, c.kind AS category_kind,
                       c.sort_order AS category_order, c.builtin AS category_builtin,
                       a.name AS account_name, a.institution AS account_institution
                FROM transactions t
                JOIN accounts a ON a.id = t.account_id
                LEFT JOIN categories c ON c.id = t.category_id
                WHERE {' AND '.join(clauses)}
                ORDER BY t.occurred_at DESC, t.created_at DESC
                LIMIT ? OFFSET ?""",
            params,
        )
        return [self._view_from_join(r) for r in rows]

    def _view_from_join(self, row) -> TransactionView:
        tx = _row_transaction(row)
        category = None
        if row["category_name"]:
            category = Category(
                id=row["category_id"] or "",
                name=row["category_name"],
                icon=row["category_icon"],
                color=row["category_color"],
                kind=row["category_kind"],
                sort_order=row["category_order"],
                builtin=bool(row["category_builtin"]),
            )
        account = self.account(row["account_id"])
        return TransactionView(transaction=tx, account=account, category=category)

    def recent_views(self, limit: int = 8) -> list[TransactionView]:
        return self.transaction_views(limit=limit)

    def all_transactions(self, limit: int = 5000, include_deleted: bool = True) -> list[Transaction]:
        where = "" if include_deleted else "WHERE deleted = 0"
        rows = self.db.query(
            f"SELECT * FROM transactions {where} ORDER BY occurred_at DESC LIMIT ?",
            (max(1, limit),),
        )
        return [_row_transaction(r) for r in rows]

    def mark_external_deleted(self, external_id: str) -> bool:
        """Marca como borrado un movimiento bancario que el proveedor retiró."""
        row = self.db.query_one(
            "SELECT id FROM transactions WHERE external_id = ? LIMIT 1", (external_id,)
        )
        if not row:
            return False
        self.db.execute(
            "UPDATE transactions SET deleted = 1, sync_state = 'synced' WHERE id = ?",
            (row["id"],),
        )
        return True

    def totals(
        self,
        *,
        start: str | None = None,
        end: str | None = None,
        account_id: str | None = None,
    ) -> Totals:
        clauses = ["deleted = 0"]
        params: list = []
        if start:
            clauses.append("occurred_at >= ?")
            params.append(start)
        if end:
            clauses.append("occurred_at < ?")
            params.append(end)
        if account_id:
            clauses.append("account_id = ?")
            params.append(account_id)
        row = self.db.query_one(
            f"""SELECT
                COALESCE(SUM(CASE WHEN amount_cents < 0 THEN -amount_cents ELSE 0 END), 0) AS expenses,
                COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents ELSE 0 END), 0) AS income,
                COUNT(*) AS count,
                COALESCE(SUM(CASE WHEN amount_cents < 0 THEN 1 ELSE 0 END), 0) AS expense_count
                FROM transactions WHERE {' AND '.join(clauses)}""",
            params,
        )
        return Totals(
            expenses_cents=int(row["expenses"]),
            income_cents=int(row["income"]),
            count=int(row["count"]),
            expense_count=int(row["expense_count"]),
        ) if row else Totals()

    def category_totals(
        self,
        *,
        start: str | None = None,
        end: str | None = None,
        kind: str = "expense",
    ) -> list[CategoryTotal]:
        clauses = ["t.deleted = 0"]
        params: list = []
        if start:
            clauses.append("t.occurred_at >= ?")
            params.append(start)
        if end:
            clauses.append("t.occurred_at < ?")
            params.append(end)
        if kind == "expense":
            clauses.append("t.amount_cents < 0")
            amount_expr = "-t.amount_cents"
        else:
            clauses.append("t.amount_cents > 0")
            amount_expr = "t.amount_cents"
        rows = self.db.query(
            f"""SELECT t.category_id, COALESCE(SUM({amount_expr}), 0) AS total,
                       COUNT(*) AS count
                FROM transactions t
                WHERE {' AND '.join(clauses)}
                GROUP BY t.category_id
                ORDER BY total DESC""",
            params,
        )
        grand = sum(int(r["total"]) for r in rows) or 1
        results: list[CategoryTotal] = []
        for r in rows:
            category = self.category(r["category_id"]) or self.category("other")
            if not category:
                continue
            results.append(
                CategoryTotal(
                    category=category,
                    total_cents=int(r["total"]),
                    count=int(r["count"]),
                    share=int(r["total"]) / grand,
                )
            )
        return results

    def daily_totals(
        self,
        *,
        start: str,
        end: str,
        account_id: str | None = None,
    ) -> list[DailyPoint]:
        clauses = ["deleted = 0", "occurred_at >= ?", "occurred_at < ?"]
        params: list = [start, end]
        if account_id:
            clauses.append("account_id = ?")
            params.append(account_id)
        rows = self.db.query(
            f"""SELECT substr(occurred_at, 1, 10) AS day,
                       COALESCE(SUM(CASE WHEN amount_cents < 0 THEN -amount_cents ELSE 0 END), 0) AS expenses,
                       COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents ELSE 0 END), 0) AS income
                FROM transactions
                WHERE {' AND '.join(clauses)}
                GROUP BY day ORDER BY day""",
            params,
        )
        return [
            DailyPoint(
                day=r["day"],
                expenses_cents=int(r["expenses"]),
                income_cents=int(r["income"]),
            )
            for r in rows
        ]

    def unsynced_transactions(self, limit: int = 200) -> list[Transaction]:
        rows = self.db.query(
            "SELECT * FROM transactions WHERE sync_state = 'local' ORDER BY created_at LIMIT ?",
            (limit,),
        )
        return [_row_transaction(r) for r in rows]

    def pending_changes(self, limit: int = 500) -> list[Transaction]:
        rows = self.db.query(
            "SELECT * FROM transactions WHERE sync_state IN ('local', 'deleted') "
            "ORDER BY created_at LIMIT ?",
            (limit,),
        )
        return [_row_transaction(r) for r in rows]

    def apply_remote_transaction(self, data: dict) -> Transaction | None:
        """Inserta/actualiza un movimiento que llegó del servidor."""
        tx_id = str(data.get("id") or "").strip()
        account_id = str(data.get("account_id") or "").strip()
        if not tx_id or not account_id:
            return None
        if not self.account(account_id):
            self.upsert_remote_account(
                account_id=account_id,
                name=data.get("account_name") or "Cuenta vinculada",
                institution=data.get("institution") or "",
                currency=data.get("currency") or "MXN",
                provider=data.get("provider") or "plaid",
            )
        occurred_at = data.get("occurred_at") or now_iso()
        amount = int(data.get("amount_cents") or 0)
        existing = self.transaction(tx_id)
        if existing:
            self.db.execute(
                """UPDATE transactions SET amount_cents = ?, description = ?,
                   merchant = ?, category_id = ?, occurred_at = ?, pending = ?,
                   deleted = ?, sync_state = 'synced', external_id = COALESCE(?, external_id),
                   raw_json = COALESCE(?, raw_json) WHERE id = ?""",
                (
                    amount,
                    str(data.get("description") or existing.description)[:240],
                    data.get("merchant"),
                    data.get("category_id"),
                    occurred_at,
                    1 if data.get("pending") else 0,
                    1 if data.get("deleted") else 0,
                    data.get("external_id"),
                    data.get("raw_json"),
                    tx_id,
                ),
            )
        else:
            self.db.execute(
                """INSERT INTO transactions
                (id, account_id, amount_cents, currency, description, merchant, category_id,
                 occurred_at, created_at, source, external_id, pending, notes, sync_state,
                 deleted, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'synced', ?, ?)""",
                (
                    tx_id,
                    account_id,
                    amount,
                    data.get("currency") or "MXN",
                    str(data.get("description") or "Movimiento")[:240],
                    data.get("merchant"),
                    data.get("category_id"),
                    occurred_at,
                    data.get("created_at") or now_iso(),
                    data.get("source") or "bank",
                    data.get("external_id"),
                    1 if data.get("pending") else 0,
                    data.get("notes"),
                    1 if data.get("deleted") else 0,
                    data.get("raw_json"),
                ),
            )
        return self.transaction(tx_id)

    def serialize_account(self, account: Account) -> dict:
        return {
            "id": account.id,
            "name": account.name,
            "institution": account.institution,
            "kind": account.kind,
            "currency": account.currency,
            "balance_cents": self.account_balance(account),
            "color": account.color,
            "icon": account.icon,
            "provider": account.provider,
            "provider_ref": account.provider_ref,
            "last_sync_at": account.last_sync_at,
            "is_demo": account.is_demo,
        }

    def serialize_transaction(self, tx: Transaction) -> dict:
        return {
            "id": tx.id,
            "account_id": tx.account_id,
            "amount_cents": tx.amount_cents,
            "currency": tx.currency,
            "description": tx.description,
            "merchant": tx.merchant,
            "category_id": tx.category_id,
            "occurred_at": tx.occurred_at,
            "created_at": tx.created_at,
            "source": tx.source,
            "external_id": tx.external_id,
            "pending": tx.pending,
            "notes": tx.notes,
            "deleted": tx.deleted,
        }


    def mark_synced(self, tx_ids: Sequence[str]) -> None:
        if not tx_ids:
            return
        placeholders = ",".join("?" for _ in tx_ids)
        self.db.execute(
            f"UPDATE transactions SET sync_state = 'synced' WHERE id IN ({placeholders})",
            tuple(tx_ids),
        )

    # ------------------------------------------------------------------- varios

    def count_transactions(self) -> int:
        return int(self.db.scalar("SELECT COUNT(*) FROM transactions WHERE deleted = 0"))

    def log_sync(
        self, provider: str, status: str, message: str = "", count: int = 0
    ) -> None:
        self.db.execute(
            "INSERT INTO sync_log(at, provider, status, message, count) VALUES (?, ?, ?, ?, ?)",
            (now_iso(), provider, status, message[:500], int(count)),
        )

    def sync_history(self, limit: int = 20):
        return self.db.query(
            "SELECT * FROM sync_log ORDER BY id DESC LIMIT ?", (max(1, limit),)
        )

    def month_totals(self, day: datetime | None = None) -> Totals:
        start, end = month_bounds(day)
        return self.totals(start=start, end=end)

    def latest_transaction_at(self) -> str | None:
        row = self.db.query_one(
            "SELECT occurred_at FROM transactions WHERE deleted = 0 "
            "ORDER BY occurred_at DESC LIMIT 1"
        )
        return row["occurred_at"] if row else None

    def export_rows(self) -> list[dict]:
        views = self.transaction_views(limit=100000)
        return [
            {
                "fecha": v.transaction.occurred_at,
                "descripcion": v.transaction.description,
                "comercio": v.transaction.merchant or "",
                "categoria": v.category.name if v.category else "",
                "cuenta": v.account.name if v.account else "",
                "monto": f"{v.transaction.amount_cents / 100:.2f}",
                "moneda": v.transaction.currency,
                "origen": v.transaction.source,
                "notas": v.transaction.notes or "",
            }
            for v in views
        ]

    def seed_initial(self) -> bool:
        from ..core.seed import seed_initial

        return seed_initial(self)

    def load_demo(self) -> bool:
        from ..core.seed import load_demo_data

        return load_demo_data(self)

    def seed_demo(self, target_balances: dict[str, int] | None = None) -> bool:
        """Datos de ejemplo reproducibles, útiles para pruebas."""
        from ..core.seed import seed_demo_data

        return seed_demo_data(self, target_balances=target_balances)

    def clear_demo(self) -> None:
        """Elimina movimientos demo y cuentas demo, conservando lo manual."""
        self.db.execute("DELETE FROM transactions WHERE source = 'demo'")
        self.db.execute("DELETE FROM transactions WHERE account_id LIKE 'acc_demo%'")
        self.db.execute("DELETE FROM accounts WHERE is_demo = 1")
        self.db.execute("UPDATE settings SET value = '1' WHERE key = 'demo_live'")

    def to_json(self, tx: Transaction) -> str:
        return json.dumps(
            {
                "id": tx.id,
                "account_id": tx.account_id,
                "amount_cents": tx.amount_cents,
                "currency": tx.currency,
                "description": tx.description,
                "merchant": tx.merchant,
                "category_id": tx.category_id,
                "occurred_at": tx.occurred_at,
                "source": tx.source,
                "external_id": tx.external_id,
                "pending": tx.pending,
            },
            ensure_ascii=False,
        )


def like_escape(value: str) -> str:
    return quote(value, safe="")
