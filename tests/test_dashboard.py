from datetime import datetime

from libreta.core.db import Database
from libreta.services.dashboard import DashboardService
from libreta.services.ledger import Ledger
from libreta.services.settings import SettingsService


def make_services(tmp_path):
    db = Database(tmp_path / "test.db").init()
    ledger = Ledger(db)
    ledger.seed_demo()
    settings = SettingsService(db)
    return ledger, settings, DashboardService(ledger, settings)


def test_dashboard_load(tmp_path):
    ledger, settings, dashboard = make_services(tmp_path)
    data = dashboard.load()
    assert data.balance_cents == 1970000
    assert data.budget_cents == 45000
    assert len(data.week) == 7
    assert len(data.monthly) == 6
    assert data.accounts
    assert data.today_label == "Hoy"


def test_widget_snapshot(tmp_path):
    ledger, settings, dashboard = make_services(tmp_path)
    ledger.add_transaction(
        account_id=ledger.demo_account().id,
        amount_cents=-1111,
        description="Widget",
        occurred_at=datetime.now().isoformat(),
    )
    snapshot = dashboard.widget_snapshot()
    assert snapshot.spent_today_cents >= 1111
    assert snapshot.currency_symbol == "$"
    assert len(snapshot.last_transactions) >= 1
    assert snapshot.name


def test_reports(tmp_path):
    ledger, settings, dashboard = make_services(tmp_path)
    report = dashboard.reports()
    assert len(report.daily) >= 28
    assert len(report.weekly) == 8
    assert len(report.monthly) == 6
    assert report.active_days >= 1
    assert report.projected_month_cents >= report.month.expenses_cents
