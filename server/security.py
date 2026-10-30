"""Autenticación, HMAC y limitación de peticiones."""

from __future__ import annotations

import hashlib
import hmac
import time
from collections import defaultdict, deque
from typing import Callable

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


def bearer_ok(request: Request, expected: str) -> bool:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return False
    provided = header[7:].strip()
    return hmac.compare_digest(provided, expected)


def verify_hmac(secret: str, body: bytes, signature: str | None) -> bool:
    if not secret or not signature:
        return False
    value = signature.strip()
    if value.startswith("sha256="):
        value = value[7:]
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(value, expected)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), camera=(), microphone=()")
        if request.url.path.startswith("/v1/") or request.url.path.startswith("/webhooks/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit_per_minute: int = 120, max_body_bytes: int = 2_000_000):
        super().__init__(app)
        self.limit = max(10, int(limit_per_minute))
        self.max_body = max_body_bytes
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        length = request.headers.get("content-length")
        if length:
            try:
                if int(length) > self.max_body:
                    return JSONResponse({"detail": "Payload demasiado grande"}, status_code=413)
            except ValueError:
                pass
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        q = self.hits[ip]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= self.limit:
            return JSONResponse(
                {"detail": "Demasiadas peticiones. Espera un minuto."},
                status_code=429,
                headers={"Retry-After": "60"},
            )
        q.append(now)
        return await call_next(request)


def attempt(fn: Callable, *args, **kwargs):
    """Pequeño helper para mantener legibles los endpoints."""
    return fn(*args, **kwargs)
