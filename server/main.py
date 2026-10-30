"""Servidor Sapardobank: sincronización, banca, SSE y firewall.

Arranque:
    uvicorn server.main:app --host 0.0.0.0 --port 8787

El token de la app se genera en server_data/token.txt la primera vez.
"""

from __future__ import annotations

import asyncio
import hmac
import html
import json
import secrets
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, StreamingResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from libreta import __version__
from libreta.core.db import Database
from libreta.core.dates import now_iso
from libreta.services.dashboard import DashboardService

from .config import ROOT, Settings
from .events import EventBus, sse_data
from .firewall import FirewallError, OutboundFirewall
from .providers import demo as demo_provider
from .providers.plaid import PlaidError, PlaidProvider
from .security import (
    RateLimiterMiddleware,
    SecurityHeadersMiddleware,
    bearer_ok,
    verify_hmac,
)
from .store import ServerStore

STATIC = Path(__file__).resolve().parent / "static"


class Context:
    def __init__(self, config: Settings):
        self.config = config
        config.ensure_token()
        if not config.webhook_path_secret:
            secret_path = config.data_path / "plaid_webhook_secret.txt"
            if secret_path.exists():
                config.webhook_path_secret = secret_path.read_text(encoding="utf-8").strip()
            else:
                config.webhook_path_secret = secrets.token_urlsafe(24)
                secret_path.write_text(config.webhook_path_secret, encoding="utf-8")
        if not config.bank_webhook_secret:
            secret_path = config.data_path / "bank_webhook_secret.txt"
            if secret_path.exists():
                config.bank_webhook_secret = secret_path.read_text(encoding="utf-8").strip()
            else:
                config.bank_webhook_secret = secrets.token_urlsafe(32)
                secret_path.write_text(config.bank_webhook_secret, encoding="utf-8")

        self.db = Database(config.db_path).init()
        self.store = ServerStore(self.db).init(config.daily_budget_cents)
        self.ledger = self.store.ledger
        self.settings = self.store.settings
        self.bus = EventBus()
        self.firewall = OutboundFirewall(
            config.outbound_allowlist,
            log=lambda *args: self.store.log_firewall(*args),
        )
        self.plaid = PlaidProvider(config, self.firewall)
        self.dashboard = DashboardService(self.ledger, self.settings)

    @property
    def token(self) -> str:
        return self.config.api_token

    def webhook_url(self, source: str = "plaid") -> str | None:
        base = self.config.public_base_url.strip().rstrip("/")
        if not base:
            return None
        if source == "plaid":
            return f"{base}/v1/webhooks/plaid?key={self.config.webhook_path_secret}"
        return f"{base}/v1/webhooks/bank"


def require_token(request: Request) -> Context:
    ctx: Context = request.app.state.ctx
    if not bearer_ok(request, ctx.token):
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Token de dispositivo inválido")
    return ctx


def _account_for(ctx: Context, account_id: str) -> dict | None:
    account = ctx.ledger.account(account_id)
    return ctx.ledger.serialize_account(account) if account else None


def _broadcast_new_events(ctx: Context, events: list[tuple[dict, str]]) -> None:
    for tx, account_id in events:
        account = ctx.ledger.account(account_id)
        ctx.bus.publish_transaction(
            tx,
            ctx.ledger.serialize_account(account) if account else None,
        )


def create_app(config: Settings | None = None) -> FastAPI:
    cfg = config or Settings()
    ctx = Context(cfg)

    app = FastAPI(
        title="Sapardobank Server",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.ctx = ctx

    if cfg.trusted_hosts and cfg.trusted_hosts != "*":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=[h.strip() for h in cfg.trusted_hosts.split(",") if h.strip()],
        )
    app.add_middleware(
        RateLimiterMiddleware,
        limit_per_minute=cfg.rate_limit_per_minute,
        max_body_bytes=cfg.max_body_bytes,
    )
    app.add_middleware(SecurityHeadersMiddleware)

    @app.exception_handler(FirewallError)
    async def firewall_error(request: Request, exc: FirewallError):
        return JSONResponse({"detail": str(exc)}, status_code=502)

    @app.exception_handler(PlaidError)
    async def plaid_error(request: Request, exc: PlaidError):
        return JSONResponse({"detail": str(exc)}, status_code=502)

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "app": "Sapardobank Server",
            "version": __version__,
            "time": now_iso(),
            "plaid": cfg.plaid_enabled,
            "accounts": len(ctx.ledger.accounts()),
        }

    @app.get("/")
    async def root():
        return PlainTextResponse(
            "Sapardobank Server activo. La app móvil usa la API /v1. "
            "Configura LIBRETA_API_TOKEN y HTTPS antes de exponerlo."
        )

    # ------------------------------------------------------------------ sync

    @app.post("/v1/sync")
    async def sync(request: Request):
        ctx = require_token(request)
        payload = await request.json()
        if not isinstance(payload, dict):
            return JSONResponse({"detail": "Payload inválido"}, status_code=400)
        accounts = payload.get("accounts") or []
        transactions = payload.get("transactions") or []
        if not isinstance(accounts, list) or not isinstance(transactions, list):
            return JSONResponse({"detail": "Payload inválido"}, status_code=400)
        if len(accounts) > 100 or len(transactions) > 1000:
            return JSONResponse({"detail": "Demasiados elementos en el lote"}, status_code=413)

        for a in accounts:
            if not isinstance(a, dict) or a.get("is_demo"):
                continue
            aid = str(a.get("id") or "").strip()
            if not aid:
                continue
            ctx.ledger.upsert_remote_account(
                account_id=aid,
                name=str(a.get("name") or "Cuenta")[:80],
                institution=str(a.get("institution") or "")[:80],
                kind=str(a.get("kind") or "debit"),
                currency=str(a.get("currency") or "MXN"),
                balance_cents=int(a.get("balance_cents") or 0),
                color=str(a.get("color") or "#0F6B54"),
                icon=str(a.get("icon") or "ACCOUNT_BALANCE_WALLET_ROUNDED"),
                provider=str(a.get("provider") or "manual"),
                provider_ref=a.get("provider_ref"),
                last_sync_at=a.get("last_sync_at") or now_iso(),
            )
        for t in transactions:
            if isinstance(t, dict):
                ctx.ledger.apply_remote_transaction(t)

        demo_ids = {a.id for a in ctx.ledger.accounts(include_archived=True) if a.is_demo}
        accounts_out = [
            ctx.ledger.serialize_account(a)
            for a in ctx.ledger.accounts()
            if not a.is_demo
        ]
        tx_out = [
            ctx.ledger.serialize_transaction(t)
            for t in ctx.ledger.all_transactions(limit=5000, include_deleted=True)
            if t.account_id not in demo_ids
        ]
        ctx.ledger.log_sync("app", "ok", "Sync app", len(transactions))
        return {
            "server_time": now_iso(),
            "accounts": accounts_out,
            "transactions": tx_out,
        }

    @app.get("/v1/events")
    async def events(request: Request):
        ctx = require_token(request)
        queue = ctx.bus.subscribe()

        async def stream():
            try:
                yield "retry: 3000\n\n"
                yield sse_data({"type": "hello", "server_time": now_iso()})
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=20)
                    except asyncio.TimeoutError:
                        yield ": keepalive\n\n"
                        continue
                    yield sse_data(event)
            finally:
                ctx.bus.unsubscribe(queue)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get("/v1/accounts")
    async def accounts(request: Request):
        ctx = require_token(request)
        return {
            "accounts": [
                ctx.ledger.serialize_account(a)
                for a in ctx.ledger.accounts()
                if not a.is_demo
            ]
        }

    @app.get("/v1/transactions")
    async def transactions(request: Request, limit: int = 200):
        ctx = require_token(request)
        limit = max(1, min(1000, limit))
        return {
            "transactions": [
                ctx.ledger.serialize_transaction(t)
                for t in ctx.ledger.all_transactions(limit=limit, include_deleted=False)
                if not (ctx.ledger.account(t.account_id) and ctx.ledger.account(t.account_id).is_demo)
            ]
        }

    @app.get("/v1/widget/summary")
    async def widget_summary(request: Request):
        ctx = require_token(request)
        snapshot = ctx.dashboard.widget_snapshot()
        payload = asdict(snapshot)
        payload["server_time"] = now_iso()
        return payload

    # ------------------------------------------------------------------ demo

    @app.post("/v1/demo/tick")
    async def demo_tick(request: Request):
        ctx = require_token(request)
        account, created = await asyncio.to_thread(demo_provider.generate, ctx.ledger)
        for tx in created:
            ctx.bus.publish_transaction(
                ctx.ledger.serialize_transaction(tx),
                ctx.ledger.serialize_account(account),
            )
        return {"ok": True, "created": len(created)}

    @app.post("/v1/demo/seed")
    async def demo_seed(request: Request):
        ctx = require_token(request)
        account, created = await asyncio.to_thread(demo_provider.generate, ctx.ledger, force_seed=5)
        for tx in created:
            ctx.bus.publish_transaction(
                ctx.ledger.serialize_transaction(tx),
                ctx.ledger.serialize_account(account),
            )
        return {"ok": True, "created": len(created)}

    # ---------------------------------------------------------------- plaid

    @app.post("/v1/plaid/link_token")
    async def plaid_link_token(request: Request):
        ctx = require_token(request)
        if not cfg.plaid_enabled:
            return JSONResponse(
                {"detail": "Plaid no está configurado en el servidor"}, status_code=503
            )
        token = await asyncio.to_thread(
            ctx.plaid.create_link_token, ctx.webhook_url("plaid")
        )
        return {"link_token": token, "env": cfg.plaid_env}

    @app.post("/v1/plaid/exchange")
    async def plaid_exchange(request: Request):
        ctx = require_token(request)
        if not cfg.plaid_enabled:
            return JSONResponse({"detail": "Plaid no está configurado"}, status_code=503)
        body = await request.json()
        public_token = str(body.get("public_token") or "").strip()
        if not public_token:
            return JSONResponse({"detail": "Falta public_token"}, status_code=400)
        institution = str(body.get("institution") or "Banco vinculado")[:100]
        data = await asyncio.to_thread(ctx.plaid.exchange_public_token, public_token)
        item_id = str(data.get("item_id") or "")
        access_token = str(data.get("access_token") or "")
        if not item_id or not access_token:
            raise PlaidError("Plaid no devolvió el item")
        link = ctx.store.add_link("plaid", item_id, access_token, institution)
        stats = await asyncio.to_thread(ctx.plaid.sync_link, link, ctx.ledger, ctx.store)
        accounts = [
            ctx.ledger.serialize_account(a)
            for a in ctx.ledger.accounts()
            if a.provider == "plaid"
        ]
        return {
            "ok": True,
            "item_id": item_id,
            "accounts": accounts,
            "transactions": stats.added,
        }

    @app.post("/v1/plaid/sync")
    async def plaid_sync(request: Request):
        ctx = require_token(request)
        if not cfg.plaid_enabled:
            return JSONResponse({"detail": "Plaid no está configurado"}, status_code=503)
        links = ctx.store.links()
        totals = {"links": len(links), "accounts": 0, "added": 0, "modified": 0, "removed": 0}
        events: list[tuple[dict, str]] = []
        for link in links:
            stats = await asyncio.to_thread(
                ctx.plaid.sync_link, link, ctx.ledger, ctx.store, notify=True
            )
            totals["accounts"] = max(totals["accounts"], stats.accounts)
            totals["added"] += stats.added
            totals["modified"] += stats.modified
            totals["removed"] += stats.removed
            events.extend(stats.new_events)
        _broadcast_new_events(ctx, events)
        return {"ok": True, **totals}

    @app.get("/link", response_class=HTMLResponse)
    async def plaid_link_page(request: Request):
        ctx = request.app.state.ctx
        token = request.query_params.get("token", "")
        if not hmac.compare_digest(token, ctx.token):
            return HTMLResponse(
                "<h1>No autorizado</h1><p>Abre este enlace desde Sapardobank.</p>",
                status_code=401,
            )
        link_html = (STATIC / "link.html").read_text(encoding="utf-8")
        if not cfg.plaid_enabled:
            page = link_html.replace(
                "{{CONTENT}}",
                """
                <div class="card">
                  <div class="badge">PENDIENTE</div>
                  <h1>Falta configurar Plaid</h1>
                  <p>Agrega <code>LIBRETA_PLAID_CLIENT_ID</code> y
                  <code>LIBRETA_PLAID_SECRET</code> al archivo <code>.env</code> del servidor
                  y vuelve a iniciar el proceso.</p>
                  <p class="muted">La app puede seguir usando cuentas manuales, webhooks
                  o el modo demo mientras tanto.</p>
                </div>
                """,
            )
            return HTMLResponse(page)
        try:
            link_token = await asyncio.to_thread(
                ctx.plaid.create_link_token, ctx.webhook_url("plaid")
            )
        except Exception as exc:
            page = link_html.replace(
                "{{CONTENT}}",
                f"""
                <div class="card">
                  <div class="badge error">ERROR</div>
                  <h1>No se pudo abrir Plaid</h1>
                  <p>{html.escape(str(exc))}</p>
                  <p class="muted">Revisa las credenciales y que el servidor tenga salida a
                  <code>sandbox.plaid.com</code> o <code>production.plaid.com</code>.</p>
                </div>
                """,
            )
            return HTMLResponse(page)
        content = f"""
        <div class="card">
          <div class="brand"><span class="mark">S</span> SAPARDOBANK</div>
          <div class="badge">{html.escape(cfg.plaid_env.upper())}</div>
          <h1>Vincula tu banco</h1>
          <p>Se abrirá Plaid, el estándar seguro para conectar cuentas bancarias.
          Sapardobank nunca recibe tu usuario ni contraseña del banco.</p>
          <button id="open">Abrir Plaid</button>
          <p id="status" class="muted">Esperando autorización…</p>
          <div class="security">Conexión cifrada · Token de un solo uso · Firewall de salida</div>
        </div>
        <script>
        const linkToken = {json.dumps(link_token)};
        const apiToken = {json.dumps(token)};
        let handler = null;
        try {{
          handler = Plaid.create({{
            token: linkToken,
            onSuccess: async (publicToken, metadata) => {{
              document.getElementById('status').textContent = 'Guardando conexión…';
              try {{
                const response = await fetch('/v1/plaid/exchange', {{
                  method: 'POST',
                  headers: {{
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + apiToken
                  }},
                  body: JSON.stringify({{
                    public_token: publicToken,
                    institution: (metadata.institution && metadata.institution.name) || 'Banco vinculado'
                  }})
                }});
                const data = await response.json();
                if (!response.ok) throw new Error(data.detail || 'Error al vincular');
                document.getElementById('status').innerHTML =
                  '<strong>¡Cuenta vinculada!</strong><br>Vuelve a Sapardobank y toca Sincronizar.';
              }} catch (error) {{
                document.getElementById('status').textContent = error.message;
              }}
            }},
            onExit: (error) => {{
              if (error) document.getElementById('status').textContent = 'Vinculación cancelada.';
            }}
          }});
          document.getElementById('open').addEventListener('click', () => handler.open());
        }} catch (error) {{
          document.getElementById('status').textContent = 'No se pudo inicializar Plaid: ' + error.message;
        }}
        </script>
        """
        page = link_html.replace("{{CONTENT}}", content)
        return HTMLResponse(page)

    @app.post("/v1/webhooks/plaid")
    async def plaid_webhook(request: Request):
        ctx = request.app.state.ctx
        expected = cfg.webhook_path_secret
        if expected and not hmac.compare_digest(request.query_params.get("key", ""), expected):
            ctx.store.log_webhook("plaid", None, "rejected", "key inválida")
            return JSONResponse({"detail": "No autorizado"}, status_code=401)
        body = await request.json()
        event_type = body.get("webhook_type")
        event_code = body.get("webhook_code")
        item_id = body.get("item_id")
        ctx.store.log_webhook("plaid", str(item_id), "received", f"{event_type}/{event_code}")
        if event_type == "TRANSACTIONS" and event_code == "SYNC_UPDATES_AVAILABLE" and item_id:
            link = ctx.store.link_by_item(str(item_id))
            if not link:
                return {"ok": True, "ignored": "link desconocido"}
            stats = await asyncio.to_thread(
                ctx.plaid.sync_link, link, ctx.ledger, ctx.store, notify=True
            )
            _broadcast_new_events(ctx, stats.new_events)
            return {"ok": True, "added": stats.added, "modified": stats.modified}
        return {"ok": True, "ignored": True}

    @app.post("/v1/webhooks/bank")
    async def bank_webhook(request: Request):
        ctx = request.app.state.ctx
        raw = await request.body()
        signature = request.headers.get("x-libreta-signature")
        if not cfg.bank_webhook_secret:
            return JSONResponse(
                {"detail": "Configura LIBRETA_BANK_WEBHOOK_SECRET"}, status_code=503
            )
        if not verify_hmac(cfg.bank_webhook_secret, raw, signature):
            ctx.store.log_webhook("bank", None, "rejected", "firma HMAC inválida")
            return JSONResponse({"detail": "Firma inválida"}, status_code=401)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            return JSONResponse({"detail": "JSON inválido"}, status_code=400)
        account_data = payload.get("account") or {}
        transactions = payload.get("transactions") or []
        if not isinstance(account_data, dict) or not isinstance(transactions, list):
            return JSONResponse({"detail": "Formato inválido"}, status_code=400)
        account_id = str(account_data.get("id") or "").strip()
        if not account_id:
            return JSONResponse({"detail": "Falta account.id"}, status_code=400)
        ctx.ledger.upsert_remote_account(
            account_id=account_id,
            name=str(account_data.get("name") or "Cuenta webhook")[:80],
            institution=str(account_data.get("institution") or "Banco")[:80],
            kind=str(account_data.get("kind") or "debit"),
            currency=str(account_data.get("currency") or "MXN"),
            balance_cents=account_data.get("balance_cents"),
            provider=str(account_data.get("provider") or "webhook"),
            provider_ref=account_data.get("provider_ref"),
            last_sync_at=now_iso(),
        )
        account = ctx.ledger.account(account_id)
        added = 0
        events = []
        for item in transactions[:500]:
            if not isinstance(item, dict):
                continue
            ext = str(item.get("external_id") or item.get("id") or "").strip()
            if not ext:
                continue
            amount = int(item.get("amount_cents") or 0)
            if amount == 0:
                continue
            tx, created = ctx.ledger.upsert_external_transaction(
                account_id=account_id,
                external_id=ext,
                amount_cents=amount,
                description=str(item.get("description") or "Movimiento")[:240],
                occurred_at=str(item.get("occurred_at") or now_iso()),
                category_id=item.get("category_id"),
                merchant=item.get("merchant"),
                pending=bool(item.get("pending")),
                source="webhook",
                currency=str(item.get("currency") or (account.currency if account else "MXN")),
                raw_json=json.dumps(item, ensure_ascii=False),
            )
            if created:
                added += 1
                events.append((ctx.ledger.serialize_transaction(tx), account_id))
        _broadcast_new_events(ctx, events)
        ctx.store.log_webhook("bank", str(payload.get("event_id") or ""), "ok", f"{added} nuevos")
        return {"ok": True, "added": added}

    @app.get("/v1/security/audit")
    async def security_audit(request: Request):
        ctx = require_token(request)
        return {
            "firewall": [dict(r) for r in ctx.store.firewall_recent(50)],
            "webhooks": [dict(r) for r in ctx.store.webhook_recent(50)],
            "public_base_url": cfg.public_base_url,
            "plaid_env": cfg.plaid_env,
            "webhook_path_configured": bool(cfg.webhook_path_secret),
            "bank_webhook_configured": bool(cfg.bank_webhook_secret),
        }

    # Un pequeño alias para no exponer el token en logs.
    return app


app = create_app()
