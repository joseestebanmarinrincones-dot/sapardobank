from datetime import datetime, timedelta

from libreta.core.db import Database, get_setting
from libreta.core.dates import day_bounds, month_bounds
from libreta.core.models import Account
from libreta.services.ledger import Ledger
from libreta.services.settings import SettingsService


def make_ledger(tmp_path):
    db = Database(tmp_path / "test.db").init()
    ledger = Ledger(db)
    ledger.ensure_categories()
    return ledger


def test_initial_start_is_clean(tmp_path):
    ledger = make_ledger(tmp_path)
    ledger.seed_initial()
    accounts = ledger.accounts()
    assert len(accounts) == 1
    assert accounts[0].name == "Mi efectivo"
    assert ledger.count_transactions() == 0
    assert ledger.total_balance() == 0


def test_demo_is_opt_in_and_has_balance(tmp_path):
    ledger = make_ledger(tmp_path)
    ledger.seed_initial()
    ledger.load_demo()
    accounts = ledger.accounts()
    demo = next(a for a in accounts if a.is_demo)
    cash = next(a for a in accounts if not a.is_demo)
    assert ledger.account_balance(demo) == 1845000
    assert ledger.account_balance(cash) == 0
    assert ledger.count_transactions() >= 10
    assert ledger.total_balance() == 1845000


def test_seed_is_idempotent(tmp_path):
    ledger = make_ledger(tmp_path)
    assert ledger.seed_demo() is True
    count = ledger.count_transactions()
    assert ledger.seed_demo() is False
    assert ledger.count_transactions() == count


def test_add_update_delete_transaction(tmp_path):
    ledger = make_ledger(tmp_path)
    ledger.seed_demo()
    account = ledger.accounts()[0]
    now = datetime.now().replace(microsecond=0)
    tx = ledger.add_transaction(
        account_id=account.id,
        amount_cents=2500,
        kind="expense",
        description="Prueba",
        category_id="food",
        occurred_at=now.isoformat(),
    )
    assert tx.amount_cents == -2500
    assert tx.source == "manual"
    assert tx.sync_state == "local"
    start, end = day_bounds()
    totals = ledger.totals(start=start, end=end)
    assert totals.expenses_cents >= 2500
    assert totals.expense_count >= 1

    updated = ledger.update_transaction(tx.id, description="Prueba editada", amount_cents=-3000)
    assert updated.description == "Prueba editada"
    assert updated.amount_cents == -3000

    ledger.delete_transaction(tx.id)
    assert ledger.transaction(tx.id).deleted is True
    assert all(v.transaction.id != tx.id for v in ledger.transaction_views())


def test_transaction_requires_valid_account(tmp_path):
    ledger = make_ledger(tmp_path)
    ledger.seed_demo()
    try:
        ledger.add_transaction(account_id="nope", amount_cents=-100, description="x")
    except Exception as exc:
        assert "cuenta" in str(exc).lower()
    else:
        raise AssertionError("expected error")


def test_external_transaction_is_deduplicated(tmp_path):
    ledger = make_ledger(tmp_path)
    ledger.seed_demo()
    account = ledger.demo_account()
    external_id = "bank-123"
    first, created = ledger.upsert_external_transaction(
        account_id=account.id,
        external_id=external_id,
        amount_cents=-15900,
        description="Compra banco",
        occurred_at=datetime.now().isoformat(),
        merchant="Tienda",
    )
    assert created is True
    result = ledger.add_transaction(
        account_id=account.id,
        amount_cents=-15900,
        description="Compra banco",
        occurred_at=datetime.now().isoformat(),
        source="bank",
        external_id=external_id,
    )
    assert result.id == first.id
    second, created = ledger.upsert_external_transaction(
        account_id=account.id,
        external_id=external_id,
        amount_cents=-16900,
        description="Compra banco actualizada",
        occurred_at=datetime.now().isoformat(),
    )
    assert created is False
    assert second.id == first.id
    assert second.description == "Compra banco actualizada"


def test_category_breakdown(tmp_path):
    ledger = make_ledger(tmp_path)
    ledger.seed_demo()
    start, end = month_bounds()
    cats = ledger.category_totals(start=start, end=end)
    assert cats
    assert sum(c.total_cents for c in cats) == ledger.totals(start=start, end=end).expenses_cents
    assert all(0 <= c.share <= 1 for c in cats)
    assert cats[0].total_cents >= cats[-1].total_cents


def test_sync_mark(tmp_path):
    ledger = make_ledger(tmp_path)
    ledger.seed_demo()
    account = ledger.demo_account()
    tx = ledger.add_transaction(
        account_id=account.id,
        amount_cents=-1000,
        description="Sync test",
        occurred_at=datetime.now().isoformat(),
    )
    unsynced = ledger.unsynced_transactions()
    assert any(t.id == tx.id for t in unsynced)
    ledger.mark_synced([tx.id])
    assert ledger.transaction(tx.id).sync_state == "synced"
