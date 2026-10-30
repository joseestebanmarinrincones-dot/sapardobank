from libreta.core.db import Database
from libreta.services.ledger import Ledger

from server.config import Settings
from server.firewall import FirewallError, OutboundFirewall
from server.providers.plaid import PlaidProvider


def test_firewall_rejects_unlisted_host():
    fw = OutboundFirewall(["sandbox.plaid.com"])
    try:
        fw.validate("https://evil.example.com")
    except FirewallError as exc:
        assert "no permitido" in str(exc)
    else:
        raise AssertionError("expected firewall error")


def test_firewall_rejects_http():
    fw = OutboundFirewall(["sandbox.plaid.com"])
    try:
        fw.validate("http://sandbox.plaid.com")
    except FirewallError as exc:
        assert "HTTPS" in str(exc)
    else:
        raise AssertionError("expected firewall error")


def test_plaid_category_mapping(tmp_path):
    db = Database(tmp_path / "s.db").init()
    ledger = Ledger(db)
    ledger.ensure_categories()
    cfg = Settings(data_dir=str(tmp_path / "data"), plaid_client_id="x", plaid_secret="y")
    provider = PlaidProvider(cfg, OutboundFirewall(["sandbox.plaid.com"]))
    assert provider.map_category(
        {"personal_finance_category": {"primary": "FOOD_AND_DRINK"}}, -100
    ) == "food"
    assert provider.map_category(
        {"personal_finance_category": {"detailed": "FOOD_AND_DRINK_COFFEE"}}, -100
    ) == "coffee"
    assert provider.map_category({"merchant_name": "Uber"}, -100) == "transport"
    assert provider.map_category({"merchant_name": "Nómina"}, 100) == "income"


def test_plaid_occurred_at():
    assert PlaidProvider._occurred_at({"date": "2026-10-30"}).startswith("2026-10-30T12:00")
