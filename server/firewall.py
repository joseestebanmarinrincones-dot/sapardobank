"""Firewall de salida del servidor.

Toda llamada a un banco/agregador pasa por aquí. Solo se permiten HTTPS,
hosts explícitamente autorizados y direcciones públicas (nunca loopback,
redes privadas ni link-local). Cada intento queda auditado en SQLite.
"""

from __future__ import annotations

import ipaddress
import socket
from datetime import datetime
from typing import Callable
from urllib.parse import urlparse

import httpx


class FirewallError(RuntimeError):
    pass


LogFn = Callable[[str, str, int | None, bool, str], None]


class OutboundFirewall:
    def __init__(self, allowlist: list[str], log: LogFn | None = None, timeout: float = 25.0):
        self.allowlist = {h.strip().lower() for h in allowlist if h.strip()}
        self.log = log
        self.timeout = timeout

    def _audit(self, host: str, method: str, status: int | None, allowed: bool, detail: str = ""):
        if self.log:
            try:
                self.log(host, method, status, allowed, detail[:500])
            except Exception:
                pass

    def validate(self, url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme.lower() != "https":
            raise FirewallError("El firewall solo permite HTTPS")
        host = (parsed.hostname or "").lower().strip(".")
        if not host:
            raise FirewallError("URL sin host")
        if host not in self.allowlist:
            raise FirewallError(f"Host no permitido por el firewall: {host}")
        try:
            infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise FirewallError(f"No se pudo resolver {host}") from exc
        for info in infos:
            ip_text = info[4][0]
            try:
                ip = ipaddress.ip_address(ip_text.split("%")[0])
            except ValueError:
                raise FirewallError(f"Dirección inválida para {host}")
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_reserved
                or ip.is_unspecified
            ):
                raise FirewallError(f"{host} resuelve a una dirección privada/no permitida")
        return host

    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        host = ""
        try:
            host = self.validate(url)
            headers = dict(kwargs.pop("headers", {}) or {})
            headers.setdefault("User-Agent", "Sapardobank-Server/1.0")
            with httpx.Client(
                timeout=self.timeout,
                verify=True,
                follow_redirects=False,
                headers=headers,
            ) as client:
                response = client.request(method.upper(), url, **kwargs)
            self._audit(host, method.upper(), response.status_code, True)
            return response
        except FirewallError as exc:
            self._audit(host or "?", method.upper(), None, False, str(exc))
            raise
        except httpx.HTTPError as exc:
            self._audit(host or "?", method.upper(), None, True, f"network error: {exc}")
            raise FirewallError(f"Error de red hacia {host or 'destino'}: {exc}") from exc

    def get(self, url: str, **kwargs) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> httpx.Response:
        return self.request("POST", url, **kwargs)
