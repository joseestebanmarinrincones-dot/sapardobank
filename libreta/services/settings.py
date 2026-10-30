"""Servicios de configuración local."""

from __future__ import annotations

from ..core.db import Database, get_setting, get_setting_bool, get_setting_int, set_setting


class SettingsService:
    def __init__(self, db: Database):
        self.db = db

    def get(self, key: str, default: str = "") -> str:
        return get_setting(self.db, key, default)

    def get_int(self, key: str, default: int = 0) -> int:
        return get_setting_int(self.db, key, default)

    def get_bool(self, key: str, default: bool = False) -> bool:
        return get_setting_bool(self.db, key, default)

    def set(self, key: str, value: str | int | bool) -> None:
        if isinstance(value, bool):
            value = "1" if value else "0"
        set_setting(self.db, key, str(value))

    @property
    def currency(self) -> str:
        return self.get("currency", "MXN")

    @property
    def symbol(self) -> str:
        return self.get("currency_symbol", "$")

    @property
    def daily_budget_cents(self) -> int:
        return max(0, self.get_int("daily_budget_cents", 45000))

    @property
    def demo_live(self) -> bool:
        return self.get_bool("demo_live", True)

    @property
    def user_name(self) -> str:
        return self.get("user_name", "").strip()
