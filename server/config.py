"""Configuración del servidor Sapardobank."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LIBRETA_",
        env_file=str(ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: str = str(ROOT / "server_data")
    host: str = "0.0.0.0"
    port: int = 8787
    api_token: str = ""
    public_base_url: str = ""
    daily_budget_cents: int = 45000

    # Plaid
    plaid_client_id: str = ""
    plaid_secret: str = ""
    plaid_env: str = "sandbox"  # sandbox | production
    plaid_countries: str = "US,CA"
    plaid_webhook_verify: bool = False

    # Webhooks / seguridad
    bank_webhook_secret: str = ""
    webhook_path_secret: str = ""
    allowed_outbound_hosts: str = "sandbox.plaid.com,production.plaid.com"
    rate_limit_per_minute: int = 120
    max_body_bytes: int = 2_000_000
    trusted_hosts: str = "*"

    @property
    def data_path(self) -> Path:
        path = Path(self.data_dir).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def db_path(self) -> Path:
        return self.data_path / "server.db"

    @property
    def token_path(self) -> Path:
        return self.data_path / "token.txt"

    @property
    def outbound_allowlist(self) -> list[str]:
        return [h.strip().lower() for h in self.allowed_outbound_hosts.split(",") if h.strip()]

    @property
    def countries(self) -> list[str]:
        return [c.strip().upper() for c in self.plaid_countries.split(",") if c.strip()]

    @property
    def plaid_enabled(self) -> bool:
        return bool(self.plaid_client_id and self.plaid_secret)

    def ensure_token(self) -> str:
        """Token de acceso para la app; se genera una vez y se guarda localmente."""
        if self.api_token:
            return self.api_token
        if self.token_path.exists():
            token = self.token_path.read_text(encoding="utf-8").strip()
            if token:
                self.api_token = token
                return token
        token = secrets.token_urlsafe(36)
        self.token_path.write_text(token, encoding="utf-8")
        try:
            os.chmod(self.token_path, 0o600)
        except OSError:
            pass
        self.api_token = token
        return token
