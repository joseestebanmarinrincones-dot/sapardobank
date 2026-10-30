"""Datos de arranque y datos de demostración (opt-in).

La app arranca vacía: solo categorías, presupuesto y una cuenta de efectivo.
Los datos demo se cargan únicamente cuando el usuario lo pide.
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


def ensure_demo_account(ledger) -> None:
    """Crea la cuenta BBVA de demostración si no existe."""
    if ledger.account(DEMO_ACCOUNT_ID):
        return
    ledger.db.execute(
        """INSERT INTO accounts
        (id, name, institution, kind, currency, initial_balance_cents, balance_cents,
         color, icon, provider, provider_ref, last_sync_at, is_demo, is_archived, created_at)
        VALUES (?, ?, ?, ?, ?, 0, NULL, ?, ?, 'demo', 'demo-checking', NULL, 1, 0, ?)""",
        (
            DEMO_ACCOUNT_ID, "Débito BBVA (demo)", "BBVA", "debit", "MXN",
            "#146EF5", "ACCOUNT_BALANCE_WALLET_ROUNDED", now_iso(),
        ),
    )


def seed_initial(ledger) -> bool:
    """Arranque limpio: sin movimientos demo, con una cuenta de efectivo."""
    db: Database = ledger.db
    ledger.ensure_categories()

    # Migración única: si una versión anterior dejó datos demo, los retiramos
    # y apagamos el feed. No toca movimientos manuales ni de bancos reales.
    if get_setting(db, "clean_start_done", "0") != "1":
        db.execute(
            "DELETE FROM transactions WHERE source = 'demo' OR account_id LIKE 'acc_demo%'"
        )
        db.execute("DELETE FROM accounts WHERE is_demo = 1")
        set_setting(db, "clean_start_done", "1")
        set_setting(db, "demo_live", "0")

    if not ledger.accounts(include_archived=True):
        ledger.create_account(
            "Mi efectivo",
            institution="En tu bolsillo",
            kind="cash",
            initial_balance_cents=0,
            color="#D9883A",
            icon="PAYMENTS_ROUNDED",
            provider="cash",
        )

    set_setting(db, "seeded", "1")
    if not get_setting(db, "daily_budget_cents", ""):
        set_setting(db, "daily_budget_cents", "45000")
    return True


DEMO_MOVEMENTS = [
    # offset_days, hora, minuto, monto, descripción, categoría, comercio
    (-6, 9, 15, -68000, "Súper de la semana", "groceries", "Soriana"),
    (-6, 14, 5, -14500, "Comida con equipo", "food", "La Cocina de Ana"),
    (-5, 8, 40, -4800, "Café y concha", "coffee", "Café Central"),
    (-5, 19, 20, -9500, "Tacos al pastor", "food", "El Pastorcito"),
    (-4, 10, 30, -32000, "Gasolina", "transport", "Pemex"),
    (-4, 13, 10, -11000, "Comida corrida", "food", "Fonda Doña Mari"),
    (-3, 7, 55, -5500, "Café para llevar", "coffee", "Starbucks"),
    (-3, 16, 40, -24900, "Tenis para correr", "shopping", "Nike"),
    (-2, 9, 5, -18500, "Súper express", "groceries", "Oxxo"),
    (-2, 15, 25, -12900, "Cine + palomitas", "fun", "Cinepolis"),
    (-1, 8, 10, -4500, "Americano", "coffee", "Café Central"),
    (-1, 11, 30, -23000, "Súper", "groceries", "La Comer"),
    (-1, 18, 15, -15000, "Flores para casa", "home", "Mercado"),
    (0, 9, 10, -3500, "Café de olla", "coffee", "Café Central"),
    (0, 13, 45, -12500, "Comida corrida", "food", "Fonda Doña Mari"),
    (0, 18, 20, -42500, "Despensa del día", "groceries", "Soriana"),
]


def load_demo_data(ledger, target_balances: dict[str, int] | None = None) -> bool:
    """Carga o recarga la demo sin borrar las cuentas reales del usuario."""
    db: Database = ledger.db
    ledger.ensure_categories()
    # Solo eliminamos lo que pertenece a la demo.
    db.execute(
        "DELETE FROM transactions WHERE source = 'demo' OR account_id LIKE 'acc_demo%'"
    )
    db.execute("DELETE FROM accounts WHERE is_demo = 1")
    ensure_demo_account(ledger)
    _insert_demo_movements(ledger)
    _set_demo_balances(ledger, target_balances)
    set_setting(db, "seeded", "1")
    set_setting(db, "clean_start_done", "1")
    set_setting(db, "demo_live", "1")
    ledger.log_sync("demo", "ok", "Datos de demostración cargados", ledger.count_transactions())
    return True


def seed_demo_data(ledger, target_balances: dict[str, int] | None = None) -> bool:
    """Compatibilidad con pruebas y arranques antiguos: siembra si está vacío."""
    db: Database = ledger.db
    ledger.ensure_categories()
    ensure_demo_account(ledger)
    if get_setting(db, "seeded", "0") == "1" or ledger.count_transactions() > 0:
        set_setting(db, "seeded", "1")
        return False
    _insert_demo_movements(ledger)
    _set_demo_balances(ledger, target_balances)
    set_setting(db, "seeded", "1")
    set_setting(db, "demo_live", "1")
    set_setting(db, "daily_budget_cents", "45000")
    ledger.log_sync("demo", "ok", "Datos de ejemplo cargados", ledger.count_transactions())
    return True


def _insert_demo_movements(ledger) -> None:
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
    for offset, hour, minute, amount, description, category_id, merchant in DEMO_MOVEMENTS:
        if offset == 0:
            continue
        ledger.add_transaction(
            account_id=DEMO_ACCOUNT_ID,
            amount_cents=amount,
            description=description,
            category_id=category_id,
            merchant=merchant,
            occurred_at=_at(offset, hour, minute),
            source="demo",
            external_id=f"seed_{offset}_{hour}_{minute}_{category_id}",
        )
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


def _set_demo_balances(ledger, target_balances: dict[str, int] | None = None) -> None:
    db = ledger.db
    targets = target_balances or {DEMO_ACCOUNT_ID: 1845000}
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
