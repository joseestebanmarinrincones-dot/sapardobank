"""Persistencia específica del servidor: enlaces bancarios y auditoría."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from libreta.core.db import Database, set_setting
from libreta.core.dates import now_iso
from libreta.services.ledger import Ledger
from libreta.services.settings import SettingsService

EXTRA_SCHEMA = """
CREATE TABLE IF NOT EXISTS bank_links (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    item_id TEXT NOT NULL UNIQUE,
    access_token TEXT NOT NULL,
    cursor TEXT,
    institution TEXT,
    created_at TEXT NOT NULL,
    last_sync_at TEXT
);

CREATE TABLE IF NOT EXISTS firewall_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    host TEXT NOT NULL,
    method TEXT NOT NULL,
    status INTEGER,
    allowed INTEGER NOT NULL,
    detail TEXT
);

CREATE TABLE IF NOT EXISTS webhook_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    source TEXT NOT NULL,
    event_key TEXT,
    status TEXT,
    detail TEXT
);
"""


@dataclass(slots=True)
class BankLink:
    id: str
    provider: str
    item_id: str
    access_token: str
    cursor: str | None
    institution: str | None
    created_at: str
    last_sync_at: str | None


class ServerStore:
    def __init__(self, db: Database):
        self.db = db
        self.ledger = Ledger(db)
        self.settings = SettingsService(db)

    def init(self, daily_budget_cents: int = 45000) -> "ServerStore":
        with self.db.connect() as conn:
            conn.executescript(EXTRA_SCHEMA)
        self.ledger.ensure_categories()
        set_setting(self.db, "daily_budget_cents", str(max(0, daily_budget_cents)))
        set_setting(self.db, "seeded", "1")
        return self

    # ------------------------------------------------------------------ links

    def add_link(
        self, provider: str, item_id: str, access_token: str, institution: str | None = None
    ) -> BankLink:
        link_id = f"link_{item_id}"
        self.db.execute(
            """INSERT INTO bank_links
            (id, provider, item_id, access_token, cursor, institution, created_at, last_sync_at)
            VALUES (?, ?, ?, ?, NULL, ?, ?, NULL)
            ON CONFLICT(item_id) DO UPDATE SET
                access_token = excluded.access_token,
                institution = COALESCE(excluded.institution, bank_links.institution),
                provider = excluded.provider""",
            (link_id, provider, item_id, access_token, institution, now_iso()),
        )
        return self.link_by_item(item_id)  # type: ignore[return-value]

    def link_by_item(self, item_id: str) -> BankLink | None:
        row = self.db.query_one("SELECT * FROM bank_links WHERE item_id = ?", (item_id,))
        return self._row_link(row) if row else None

    def links(self) -> list[BankLink]:
        rows = self.db.query("SELECT * FROM bank_links ORDER BY created_at DESC")
        return [self._row_link(r) for r in rows]

    def _row_link(self, row: sqlite3.Row) -> BankLink:
        return BankLink(
            id=row["id"],
            provider=row["provider"],
            item_id=row["item_id"],
            access_token=row["access_token"],
            cursor=row["cursor"],
            institution=row["institution"],
            created_at=row["created_at"],
            last_sync_at=row["last_sync_at"],
        )

    def update_link_sync(self, item_id: str, cursor: str | None) -> None:
        self.db.execute(
            "UPDATE bank_links SET cursor = ?, last_sync_at = ? WHERE item_id = ?",
            (cursor, now_iso(), item_id),
        )

    # --------------------------------------------------------------- auditoría

    def log_firewall(
        self, host: str, method: str, status: int | None, allowed: bool, detail: str
    ) -> None:
        self.db.execute(
            "INSERT INTO firewall_log(at, host, method, status, allowed, detail) VALUES (?, ?, ?, ?, ?, ?)",
            (now_iso(), host[:200], method[:12], status, 1 if allowed else 0, detail[:500]),
        )

    def log_webhook(self, source: str, event_key: str | None, status: str, detail: str = "") -> None:
        self.db.execute(
            "INSERT INTO webhook_events(at, source, event_key, status, detail) VALUES (?, ?, ?, ?, ?)",
            (now_iso(), source, (event_key or "")[:200], status[:40], detail[:500]),
        )

    def firewall_recent(self, limit: int = 50):
        return self.db.query(
            "SELECT * FROM firewall_log ORDER BY id DESC LIMIT ?", (max(1, limit),)
        )

    def webhook_recent(self, limit: int = 50):
        return self.db.query(
            "SELECT * FROM webhook_events ORDER BY id DESC LIMIT ?", (max(1, limit),)
        )
