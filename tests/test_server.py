import hashlib
import hmac
import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from server.config import Settings
from server.main import create_app


def make_client(tmp_path: Path) -> TestClient:
    cfg = Settings(
        data_dir=str(tmp_path / "server"),
        api_token="test-token",
        rate_limit_per_minute=1000,
        bank_webhook_secret="bank-secret",
        webhook_path_secret="plaid-key",
        daily_budget_cents=45000,
        public_base_url="https://libreta.example.com",
    )
    return TestClient(create_app(cfg))


def auth():
    return {"Authorization": "Bearer test-token"}


def test_health_and_auth(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/health").status_code == 200
    assert client.get("/v1/accounts").status_code == 401
    assert client.get("/v1/accounts", headers=auth()).status_code == 200


def test_sync_roundtrip_and_summary(tmp_path):
    client = make_client(tmp_path)
    payload = {
        "accounts": [
            {
                "id": "acc_test",
                "name": "Cuenta prueba",
                "institution": "Banco",
                "kind": "debit",
                "currency": "MXN",
                "balance_cents": 100000,
                "provider": "manual",
            }
        ],
        "transactions": [
            {
                "id": "tx_test_1",
                "account_id": "acc_test",
                "amount_cents": -12345,
                "currency": "MXN",
                "description": "Café",
                "category_id": "coffee",
                "occurred_at": "2026-10-30T10:00:00",
                "created_at": "2026-10-30T10:00:00",
                "source": "manual",
                "deleted": False,
            }
        ],
    }
    response = client.post("/v1/sync", headers=auth(), json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert any(a["id"] == "acc_test" for a in data["accounts"])
    assert any(t["id"] == "tx_test_1" for t in data["transactions"])
    summary = client.get("/v1/widget/summary", headers=auth())
    assert summary.status_code == 200
    body = summary.json()
    assert "spent_today_cents" in body
    assert body["currency_symbol"] == "$"


def test_demo_tick_publishes_and_returns(tmp_path):
    client = make_client(tmp_path)
    response = client.post("/v1/demo/tick", headers=auth())
    assert response.status_code == 200
    assert response.json()["created"] == 1


def test_bank_webhook_hmac(tmp_path):
    client = make_client(tmp_path)
    payload = {
        "account": {
            "id": "acc_webhook",
            "name": "Cuenta Belvo",
            "institution": "Banco",
            "balance_cents": 50000,
            "provider": "webhook",
        },
        "transactions": [
            {
                "external_id": "bank-1",
                "amount_cents": -4500,
                "description": "Café",
                "occurred_at": "2026-10-30T09:00:00",
            }
        ],
    }
    raw = json.dumps(payload).encode()
    signature = hmac.new(b"bank-secret", raw, hashlib.sha256).hexdigest()
    bad = client.post(
        "/v1/webhooks/bank",
        content=raw,
        headers={"Content-Type": "application/json", "X-Libreta-Signature": "bad"},
    )
    assert bad.status_code == 401
    good = client.post(
        "/v1/webhooks/bank",
        content=raw,
        headers={"Content-Type": "application/json", "X-Libreta-Signature": signature},
    )
    assert good.status_code == 200, good.text
    assert good.json()["added"] == 1
    again = client.post(
        "/v1/webhooks/bank",
        content=raw,
        headers={"Content-Type": "application/json", "X-Libreta-Signature": signature},
    )
    assert again.json()["added"] == 0


def test_plaid_webhook_requires_key(tmp_path):
    client = make_client(tmp_path)
    response = client.post("/v1/webhooks/plaid?key=wrong", json={"webhook_type": "TRANSACTIONS"})
    assert response.status_code == 401
    ok = client.post("/v1/webhooks/plaid?key=plaid-key", json={"webhook_type": "TRANSACTIONS"})
    assert ok.status_code == 200


def test_link_page_requires_token(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/link").status_code == 401
    page = client.get("/link?token=test-token")
    assert page.status_code == 200
    assert "Plaid" in page.text
