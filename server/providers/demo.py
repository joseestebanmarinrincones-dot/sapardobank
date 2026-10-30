"""Proveedor demo del servidor: genera movimientos y eventos SSE."""

from __future__ import annotations

import random
import time
import uuid

from libreta.core.dates import now_iso
from libreta.services.ledger import Ledger

DEMO_ACCOUNT_ID = "acc_server_demo"
PATTERNS = [
    ("food", "Comida corrida", "Fonda Doña Mari", 9500, 26000),
    ("coffee", "Café de olla", "Café Central", 3200, 7000),
    ("groceries", "Despensa", "Soriana", 12000, 65000),
    ("transport", "Viaje en Uber", "Uber", 5500, 28000),
    ("fun", "Cine", "Cinépolis", 12000, 35000),
]
COLORS = ["#0F6B54", "#146EF5", "#D9883A", "#8B5CF6", "#D95D70"]


def ensure_demo_account(ledger: Ledger):
    account = ledger.account(DEMO_ACCOUNT_ID)
    if account:
        return account
    return ledger.create_account(
        "Cuenta demo servidor",
        institution="Sapardobank Demo",
        kind="debit",
        initial_balance_cents=2500000,
        color="#0F6B54",
        icon="ACCOUNT_BALANCE_WALLET_ROUNDED",
        provider="demo",
        provider_ref="server-demo",
        is_demo=True,
    )


def generate(ledger: Ledger, *, force_seed: int = 0):
    account = ensure_demo_account(ledger)
    created = []
    count = force_seed or 1
    for _ in range(max(1, count)):
        category, description, merchant, low, high = random.choice(PATTERNS)
        amount = max(100, random.randint(low, high) // 50 * 50)
        tx = ledger.add_transaction(
            account_id=account.id,
            amount_cents=-amount,
            description=description,
            category_id=category,
            merchant=merchant,
            occurred_at=now_iso(),
            source="demo",
            external_id=f"server_demo_{int(time.time())}_{uuid.uuid4().hex[:8]}",
        )
        created.append(tx)
    ledger.set_provider_balance(account.id, ledger.account_balance(account), now_iso())
    ledger.log_sync("demo-server", "ok", f"{len(created)} movimientos demo", len(created))
    return account, created
