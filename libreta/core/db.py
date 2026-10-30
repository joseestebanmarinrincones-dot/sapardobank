"""Acceso a SQLite con conexiones cortas y WAL.

La app es local-first: cada operación abre su propia conexión, de modo que
la UI, el feed en vivo y el sincronizador pueden convivir sin bloqueos.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from ..paths import DB_PATH

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    institution TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL DEFAULT 'debit',
    currency TEXT NOT NULL DEFAULT 'MXN',
    initial_balance_cents INTEGER NOT NULL DEFAULT 0,
    balance_cents INTEGER,
    color TEXT NOT NULL DEFAULT '#0F6B54',
    icon TEXT NOT NULL DEFAULT 'account_balance_wallet',
    provider TEXT NOT NULL DEFAULT 'manual',
    provider_ref TEXT,
    last_sync_at TEXT,
    is_demo INTEGER NOT NULL DEFAULT 0,
    is_archived INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    icon TEXT NOT NULL,
    color TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'expense',
    sort_order INTEGER NOT NULL DEFAULT 100,
    builtin INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    currency TEXT NOT NULL DEFAULT 'MXN',
    description TEXT NOT NULL,
    merchant TEXT,
    category_id TEXT,
    occurred_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'manual',
    external_id TEXT,
    pending INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    sync_state TEXT NOT NULL DEFAULT 'local',
    deleted INTEGER NOT NULL DEFAULT 0,
    raw_json TEXT,
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_transactions_external
    ON transactions(account_id, external_id)
    WHERE external_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_transactions_occurred
    ON transactions(occurred_at DESC);
CREATE INDEX IF NOT EXISTS ix_transactions_account
    ON transactions(account_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS ix_transactions_sync
    ON transactions(sync_state, created_at);

CREATE TABLE IF NOT EXISTS budgets (
    id TEXT PRIMARY KEY,
    category_id TEXT,
    period TEXT NOT NULL DEFAULT 'month',
    amount_cents INTEGER NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    provider TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS network_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    host TEXT NOT NULL,
    method TEXT NOT NULL,
    status INTEGER,
    allowed INTEGER NOT NULL,
    detail TEXT
);
"""

DEFAULT_SETTINGS = {
    "seeded": "0",
    "user_name": "",
    "currency": "MXN",
    "currency_symbol": "$",
    "daily_budget_cents": "45000",
    "demo_live": "0",
    "clean_start_done": "0",
    "demo_interval_seconds": "75",
    "internet_enabled": "0",
    "network_permission_granted": "0",
    "check_updates": "1",
    "skipped_version": "",
    "api_url": "",
    "api_token": "",
    "last_sync_at": "",
    "widget_theme": "forest",
    "widget_privacy": "0",
    "widget_variant": "wide",
    "theme_palette": "esmeralda",
    "tutorial_seen": "0",
    "last_widget_at": "",
    "last_widget_path": "",
    "week_start": "monday",
}


class Database:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else DB_PATH

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=15000")
        return conn

    def init(self) -> "Database":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            conn.executemany(
                "INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)",
                DEFAULT_SETTINGS.items(),
            )
        return self

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def query(self, sql: str, params: tuple | list = ()) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(conn.execute(sql, params).fetchall())

    def query_one(self, sql: str, params: tuple | list = ()) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(sql, params).fetchone()

    def execute(self, sql: str, params: tuple | list = ()) -> int:
        with self.transaction() as conn:
            cur = conn.execute(sql, params)
            return cur.lastrowid or cur.rowcount

    def scalar(self, sql: str, params: tuple | list = (), default=0):
        row = self.query_one(sql, params)
        if row is None:
            return default
        value = row[0]
        return default if value is None else value


def get_setting(db: Database, key: str, default: str = "") -> str:
    row = db.query_one("SELECT value FROM settings WHERE key = ?", (key,))
    return row["value"] if row else default


def set_setting(db: Database, key: str, value: str) -> None:
    db.execute(
        "INSERT INTO settings(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )


def get_setting_int(db: Database, key: str, default: int = 0) -> int:
    try:
        return int(float(get_setting(db, key, str(default))))
    except (TypeError, ValueError):
        return default


def get_setting_bool(db: Database, key: str, default: bool = False) -> bool:
    value = get_setting(db, key, "1" if default else "0").strip().lower()
    return value in {"1", "true", "yes", "si", "sí", "on"}
