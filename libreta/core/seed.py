"""Datos iniciales de demostración.

No son datos reales: sirven para que la app se sienta viva desde el primer
arranque y para probar el feed en tiempo real sin conectar un banco.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .dates import now_iso
from .db import Database, get_setting, set_setting
from .models import Account


def _at(day_offset: int, hour: int, minute: int) -> str:
    base = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    return (base + timedelta(days=day_offset)).isoformat()


def _minutes_ago(minutes: int) -> str:
    return (datetime.now() - timedelta(minutes=minutes)).replace(microsecond=0).isoformat()


DEMO_ACCOUNT_ID = "acc_demo_bbva"
CASH_ACCOUNT_ID = "acc_cash"


def ensure_demo_accounts(ledger) -> None:
    if not ledger.accounts(include_archived=True):
        now = now_iso()
        ledger.db.execute(
            """INSERT INTO accounts
            (id, name, institution, kind, currency, initial_balance_cents, balance_cents,
             color, icon, provider, provider_ref, last_sync_at, is_demo, is_archived, created_at)
            VALUES (?, ?, ?, ?, ?, 0, NULL, ?, ?, 'demo', 'demo-checking', NULL, 1, 0, ?)""",
            (
                DEMO_ACCOUNT_ID, "Débito BBVA", "BBVA", "debit", "MXN",
                "#146EF5", "ACCOUNT_BALANCE_WALLET_ROUNDED", now,
            ),
        )
        ledger.db.execute(
            """INSERT INTO accounts
            (id, name, institution, kind, currency, initial_balance_cents, balance_cents,
             color, icon, provider, provider_ref, last_sync_at, is_demo, is_archived, created_at)
            VALUES (?, ?, ?, ?, ?, 0, NULL, ?, ?, 'cash', NULL, NULL, 0, 0, ?)""",
            (
                CASH_ACCOUNT_ID, "Efectivo", "En tu bolsillo", "cash", "MXN",
                "#D9883A", "PAYMENTS_ROUNDED", now,
            ),
        )


DEMO_MOVEMENTS = [
    # offset_days, hora, minuto, cuenta, monto, descripción, categoría, comercio, origen
    (-6, 9, 15, DEMO_ACCOUNT_ID, -68000, "Súper de la semana", "groceries", "Soriana", "demo"),
    (-6, 14, 5, DEMO_ACCOUNT_ID, -14500, "Comida con equipo", "food", "La Cocina de Ana", "demo"),
    (-5, 8, 40, DEMO_ACCOUNT_ID, -4800, "Café y concha", "coffee", "Café Central", "demo"),
    (-5, 19, 20, CASH_ACCOUNT_ID, -9500, "Tacos al pastor", "food", "El Pastorcito", "manual"),
    (-4, 10, 30, DEMO_ACCOUNT_ID, -32000, "Gasolina", "transport", "Pemex", "demo"),
    (-4, 13, 10, DEMO_ACCOUNT_ID, -11000, "Comida corrida", "food", "Fonda Doña Mari", "demo"),
    (-3, 7, 55, DEMO_ACCOUNT_ID, -5500, "Café para llevar", "coffee", "Starbucks", "demo"),
    (-3, 16, 40, DEMO_ACCOUNT_ID, -24900, "Tenis para correr", "shopping", "Nike", "demo"),
    (-2, 9, 5, DEMO_ACCOUNT_ID, -18500, "Súper express", "groceries", "Oxxo", "demo"),
    (-2, 15, 25, DEMO_ACCOUNT_ID, -12900, "Cine + palomitas", "fun", "Cinepolis", "demo"),
    (-1, 8, 10, DEMO_ACCOUNT_ID, -4500, "Americano", "coffee", "Café Central", "demo"),
    (-1, 11, 30, DEMO_ACCOUNT_ID, -23000, "Súper", "groceries", "La Comer", "demo"),
    (-1, 18, 15, CASH_ACCOUNT_ID, -15000, "Flores para casa", "home", "Mercado", "manual"),
    (0, 9, 10, DEMO_ACCOUNT_ID, -3500, "Café de olla", "coffee", "Café Central", "demo"),
    (0, 13, 45, DEMO_ACCOUNT_ID, -12500, "Comida corrida", "food", "Fonda Doña Mari", "demo"),
    (0, 18, 20, DEMO_ACCOUNT_ID, -42500, "Despensa del día", "groceries", "Soriana", "demo"),
]


def seed_demo_data(ledger, target_balances: dict[str, int] | None = None) -> bool:
    """Siembra categorías, cuentas y movimientos. Devuelve True si sembró."""
    db: Database = ledger.db
    ledger.ensure_categories()
    ensure_demo_accounts(ledger)

    if get_setting(db, "seeded", "0") == "1" or ledger.count_transactions() > 0:
        set_setting(db, "seeded", "1")
        return False

    # Dos movimientos recientes relativos a la hora actual para que "Hoy" no
    # aparezca vacío al abrir la app por primera vez.
    ledger.add_transaction(
        account_id=DEMO_ACCOUNT_ID,
        amount_cents=-4200,
        description="Café de bienvenida",
        category_id="coffee",
        merchant="Café Central",
        occurred_at=_minutes_ago(95),
        source="demo",
        external_id="demo_seed_today_1",
    )
    ledger.add_transaction(
        account_id=DEMO_ACCOUNT_ID,
        amount_cents=-16800,
        description="Comida del día",
        category_id="food",
        merchant="Fonda Doña Mari",
        occurred_at=_minutes_ago(35),
        source="demo",
        external_id="demo_seed_today_2",
    )

    for offset, hour, minute, account_id, amount, description, category_id, merchant, source in DEMO_MOVEMENTS:
        occurred = _at(offset, hour, minute)
        # Evita duplicar los dos movimientos recientes de hoy.
        if offset == 0:
            continue
        ledger.add_transaction(
            account_id=account_id,
            amount_cents=amount,
            description=description,
            category_id=category_id,
            merchant=merchant,
            occurred_at=occurred,
            source=source,
            external_id=f"seed_{offset}_{hour}_{minute}_{account_id}" if source == "demo" else None,
        )

    # Un ingreso para que el libro no sea solo de salidas.
    ledger.add_transaction(
        account_id=DEMO_ACCOUNT_ID,
        amount_cents=380000,
        description="Venta de bici vieja",
        category_id="income",
        merchant="Mercado Libre",
        occurred_at=_at(-2, 17, 30),
        source="demo",
        external_id="demo_seed_income_1",
    )

    # Ajusta el saldo inicial para que las cuentas demo muestren un saldo
    # realista después de todo el historial anterior.
    targets = target_balances or {DEMO_ACCOUNT_ID: 1845000, CASH_ACCOUNT_ID: 125000}
    for account_id, target in targets.items():
        account: Account | None = ledger.account(account_id)
        if not account:
            continue
        net = db.scalar(
            "SELECT COALESCE(SUM(amount_cents), 0) FROM transactions "
            "WHERE account_id = ? AND deleted = 0",
            (account_id,),
        )
        ledger.update_account(
            account_id,
            initial_balance_cents=int(target) - int(net),
            last_sync_at=now_iso(),
        )

    set_setting(db, "seeded", "1")
    set_setting(db, "demo_live", "1")
    set_setting(db, "daily_budget_cents", "45000")
    ledger.log_sync("demo", "ok", "Datos de ejemplo cargados", ledger.count_transactions())
    return True
