"""Cliente del backend Sapardobank: sincronización, SSE y vinculación bancaria.

La app funciona sin internet. Este cliente solo se activa cuando el usuario
configura un servidor y un token. Nunca envía datos a un host no configurado.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import socket
from dataclasses import dataclass
from datetime import datetime
from typing import Awaitable, Callable
from urllib.parse import urlparse

import httpx

from ..core.dates import now_iso
from ..core.db import set_setting
from .ledger import Ledger
from .settings import SettingsService

DEFAULT_TIMEOUT = 25.0


class RemoteError(RuntimeError):
    pass


@dataclass(slots=True)
class SyncResult:
    ok: bool
    accounts: int = 0
    transactions: int = 0
    pushed: int = 0
    message: str = ""


def _is_private_host(host: str) -> bool:
    if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".local"):
        return True
    try:
        return ipaddress.ip_address(host).is_private
    except ValueError:
        pass
    try:
        resolved = socket.gethostbyname(host)
        return ipaddress.ip_address(resolved).is_private
    except (OSError, ValueError):
        return False


def validate_server_url(raw: str) -> str:
    url = (raw or "").strip().rstrip("/")
    if not url:
        raise RemoteError("Escribe la dirección del servidor")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    if not parsed.netloc or not parsed.hostname:
        raise RemoteError("La dirección no es válida")
    if parsed.scheme == "http" and not _is_private_host(parsed.hostname):
        raise RemoteError("Por seguridad, usa HTTPS. HTTP solo se permite en tu red local.")
    if parsed.scheme not in {"http", "https"}:
        raise RemoteError("Solo se permiten conexiones HTTPS")
    return url


def local_private_ip() -> str:
    """IP de la Wi-Fi/LAN actual, sin enviar tráfico real."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.settimeout(0.3)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
    except OSError as exc:
        raise RemoteError("No estoy en una red Wi-Fi.") from exc
    finally:
        sock.close()
    try:
        address = ipaddress.ip_address(ip)
    except ValueError as exc:
        raise RemoteError("No pude detectar tu red Wi-Fi.") from exc
    if not address.is_private:
        raise RemoteError("Conéctate al Wi-Fi de tu casa, no a datos móviles.")
    return ip


async def discover_local_servers(
    port: int = 8787,
    *,
    timeout: float = 0.65,
    concurrency: int = 64,
) -> list[dict]:
    """Busca servidores Sapardobank en la misma red /24 del teléfono."""
    ip = await asyncio.to_thread(local_private_ip)
    octets = ip.split(".")
    if len(octets) != 4:
        raise RemoteError("Tu red no es IPv4")
    base = ".".join(octets[:3])
    hosts = [f"{base}.{i}" for i in range(1, 255)]
    if ip not in hosts:
        hosts.append(ip)
    hosts.append("127.0.0.1")
    semaphore = asyncio.Semaphore(concurrency)
    results: list[dict] = []
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=0)

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(timeout),
        verify=False,
        follow_redirects=False,
        limits=limits,
        headers={"User-Agent": "Sapardobank-Discovery/1.0"},
    ) as client:

        async def probe(host: str) -> None:
            async with semaphore:
                try:
                    response = await client.get(f"http://{host}:{port}/health")
                    if response.status_code != 200:
                        return
                    data = response.json()
                except Exception:
                    return
            app_name = str(data.get("app") or "")
            if "Sapardobank" not in app_name and "Libreta" not in app_name:
                return
            url = f"http://{host}:{port}"
            if not any(item["url"] == url for item in results):
                results.append(
                    {
                        "url": url,
                        "name": app_name,
                        "version": str(data.get("version") or ""),
                        "plaid": bool(data.get("plaid")),
                    }
                )

        await asyncio.gather(*(probe(host) for host in hosts))
    return sorted(results, key=lambda item: item["url"])



class RemoteClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = validate_server_url(base_url)
        self.token = (token or "").strip()
        if not self.token:
            raise RemoteError("Falta el token del servidor")
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "User-Agent": "Sapardobank/1.0",
        }

    def _client(self, timeout: float = DEFAULT_TIMEOUT) -> httpx.Client:
        return httpx.Client(
            timeout=timeout,
            verify=True,
            headers=self._headers,
            follow_redirects=False,
        )

    def health(self) -> dict:
        try:
            with self._client(10) as client:
                r = client.get(f"{self.base_url}/health")
                r.raise_for_status()
                return r.json()
        except httpx.HTTPError as exc:
            raise RemoteError(f"No pude conectar: {exc}") from exc

    def sync_payload(self, accounts: list[dict], transactions: list[dict]) -> dict:
        payload = {"accounts": accounts, "transactions": transactions, "client_time": now_iso()}
        try:
            with self._client(35) as client:
                r = client.post(f"{self.base_url}/v1/sync", json=payload)
                if r.status_code in (401, 403):
                    raise RemoteError("Token incorrecto o vencido")
                r.raise_for_status()
                return r.json()
        except httpx.HTTPStatusError as exc:
            raise RemoteError(f"El servidor respondió {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise RemoteError(f"No pude sincronizar: {exc}") from exc

    def summary(self) -> dict:
        try:
            with self._client(15) as client:
                r = client.get(f"{self.base_url}/v1/widget/summary")
                r.raise_for_status()
                return r.json()
        except httpx.HTTPError as exc:
            raise RemoteError(f"No pude leer el resumen: {exc}") from exc

    def link_url(self) -> str:
        return f"{self.base_url}/link?token={self.token}"

    async def stream_events(
        self,
        on_event: Callable[[dict], Awaitable[None] | None],
        on_status: Callable[[str], Awaitable[None] | None] | None = None,
        stop: asyncio.Event | None = None,
    ) -> None:
        """Escucha SSE con reconexión exponencial. Se cancela con la tarea."""
        delay = 2.0
        while not (stop and stop.is_set()):
            try:
                timeout = httpx.Timeout(connect=15, read=None, write=15, pool=15)
                async with httpx.AsyncClient(timeout=timeout, headers=self._headers, verify=True) as client:
                    async with client.stream("GET", f"{self.base_url}/v1/events") as response:
                        response.raise_for_status()
                        if on_status:
                            result = on_status("connected")
                            if asyncio.iscoroutine(result):
                                await result
                        delay = 2.0
                        async for line in response.aiter_lines():
                            if stop and stop.is_set():
                                return
                            line = line.strip()
                            if not line.startswith("data:"):
                                continue
                            raw = line[5:].strip()
                            if not raw:
                                continue
                            try:
                                event = json.loads(raw)
                            except json.JSONDecodeError:
                                continue
                            result = on_event(event)
                            if asyncio.iscoroutine(result):
                                await result
            except asyncio.CancelledError:
                raise
            except Exception:
                if stop and stop.is_set():
                    return
                if on_status:
                    result = on_status("reconnecting")
                    if asyncio.iscoroutine(result):
                        await result
                await asyncio.sleep(delay)
                delay = min(delay * 1.8, 45.0)


class SyncManager:
    """Orquesta el intercambio local ↔ servidor y mantiene el stream SSE."""

    def __init__(
        self,
        ledger: Ledger,
        settings: SettingsService,
        *,
        on_event: Callable[[dict], None] | None = None,
        on_status: Callable[[str], None] | None = None,
    ):
        self.ledger = ledger
        self.settings = settings
        self.on_event = on_event
        self.on_status = on_status
        self._stop = asyncio.Event()

    def client(self) -> RemoteClient:
        return RemoteClient(self.settings.get("api_url"), self.settings.get("api_token"))

    def sync_now(self) -> SyncResult:
        if not self.settings.get_bool("internet_enabled", False):
            return SyncResult(False, message="El acceso a internet está desactivado")
        try:
            client = self.client()
            demo_ids = {a.id for a in self.ledger.accounts(include_archived=True) if a.is_demo}
            accounts = [
                self.ledger.serialize_account(a) for a in self.ledger.accounts() if not a.is_demo
            ]
            pending = [
                t for t in self.ledger.pending_changes() if t.account_id not in demo_ids
            ]
            payload = [self.ledger.serialize_transaction(t) for t in pending]
            data = client.sync_payload(accounts, payload)
            remote_accounts = data.get("accounts", [])
            remote_transactions = data.get("transactions", [])
            for a in remote_accounts:
                if a.get("is_demo"):
                    continue
                self.ledger.upsert_remote_account(
                    account_id=a["id"],
                    name=a.get("name", "Cuenta"),
                    institution=a.get("institution", ""),
                    kind=a.get("kind", "debit"),
                    currency=a.get("currency", "MXN"),
                    balance_cents=a.get("balance_cents"),
                    color=a.get("color", "#0F6B54"),
                    icon=a.get("icon", "ACCOUNT_BALANCE_WALLET_ROUNDED"),
                    provider=a.get("provider", "plaid"),
                    provider_ref=a.get("provider_ref"),
                    last_sync_at=a.get("last_sync_at"),
                )
            for tx in remote_transactions:
                self.ledger.apply_remote_transaction(tx)
            self.ledger.mark_synced([t.id for t in pending])
            set_setting(self.ledger.db, "last_sync_at", now_iso())
            self.ledger.log_sync("server", "ok", "Sincronización completa", len(remote_transactions))
            return SyncResult(
                ok=True,
                accounts=len(remote_accounts),
                transactions=len(remote_transactions),
                pushed=len(payload),
            )
        except Exception as exc:
            self.ledger.log_sync("server", "error", str(exc), 0)
            return SyncResult(False, message=str(exc))

    async def run_stream(self) -> None:
        if not self.settings.get_bool("internet_enabled", False):
            return
        try:
            client = self.client()
        except RemoteError as exc:
            if self.on_status:
                self.on_status(str(exc))
            return

        async def handle(event: dict):
            if event.get("type") == "transaction" and event.get("transaction"):
                if event.get("account"):
                    a = event["account"]
                    self.ledger.upsert_remote_account(
                        account_id=a["id"],
                        name=a.get("name", "Cuenta"),
                        institution=a.get("institution", ""),
                        kind=a.get("kind", "debit"),
                        currency=a.get("currency", "MXN"),
                        balance_cents=a.get("balance_cents"),
                        provider=a.get("provider", "plaid"),
                        provider_ref=a.get("provider_ref"),
                        last_sync_at=a.get("last_sync_at"),
                    )
                self.ledger.apply_remote_transaction(event["transaction"])
                set_setting(self.ledger.db, "last_sync_at", now_iso())
            if self.on_event:
                self.on_event(event)

        def status(value: str):
            if self.on_status:
                self.on_status(value)

        await client.stream_events(handle, status, self._stop)

    def stop(self) -> None:
        self._stop.set()
