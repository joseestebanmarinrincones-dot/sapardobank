import asyncio
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from libreta.core.db import Database
from libreta.services.ledger import Ledger
from libreta.services.remote import RemoteClient, SyncManager
from libreta.services.settings import SettingsService

base = "http://127.0.0.1:8788"
token = "test-token"
tmp = Path(tempfile.mkdtemp(prefix="libreta-int-"))
db = Database(tmp / "local.db").init()
ledger = Ledger(db)
ledger.seed_demo()
settings = SettingsService(db)
settings.set("api_url", base)
settings.set("api_token", token)
settings.set("internet_enabled", True)
account = ledger.accounts()[0]
tx = ledger.add_transaction(
    account_id=account.id,
    amount_cents=-4321,
    description="Prueba integración",
    category_id="food",
    occurred_at=datetime.now().isoformat(),
)
sm = SyncManager(ledger, settings)
result = sm.sync_now()
print("SYNC", result)
assert result.ok, result.message
with httpx.Client(headers={"Authorization": f"Bearer {token}"}) as c:
    accs = c.get(base + "/v1/accounts").json()["accounts"]
    print("SERVER ACCOUNTS", len(accs), [a["name"] for a in accs])
    summary = c.get(base + "/v1/widget/summary").json()
    print("SUMMARY", summary["spent_today_cents"], summary["daily_budget_cents"])


async def sse_test():
    events = []

    async def on_event(e):
        events.append(e)

    async def on_status(s):
        print("STATUS", s)

    client = RemoteClient(base, token)
    task = asyncio.create_task(client.stream_events(on_event, on_status))
    await asyncio.sleep(1.2)
    async with httpx.AsyncClient() as c:
        r = await c.post(base + "/v1/demo/tick", headers={"Authorization": f"Bearer {token}"})
        print("TICK", r.status_code, r.json())
    for _ in range(30):
        if any(e.get("type") == "transaction" for e in events):
            break
        await asyncio.sleep(0.2)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    print("EVENTS", [e.get("type") for e in events])
    assert any(e.get("type") == "transaction" for e in events), events


asyncio.run(sse_test())
print("OK")
