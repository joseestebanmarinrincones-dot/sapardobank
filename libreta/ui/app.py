"""Shell de la aplicación: navegación, servicios, feed en vivo y sincronización."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import date, datetime
from pathlib import Path

import flet as ft

from ..core.dates import day_bounds, month_label, now_iso
from ..core.db import Database, get_setting, set_setting
from ..core.money import MoneyError, format_money, parse_amount_to_cents
from ..paths import DB_PATH
from ..services.dashboard import DashboardService
from ..services.demo_feed import DemoFeed
from ..services.export import ExportService
from ..services.ledger import Ledger
from ..services.remote import RemoteClient, RemoteError, SyncManager, validate_server_url
from ..services.settings import SettingsService
from ..services.updates import UpdateChecker, UpdateInfo, is_newer
from ..services.widget import WidgetService
from .. import __version__
from . import theme
from .theme import alpha, text
from .components import primary_button, text_button
from .sheets import (
    AccountDetailSheet,
    AccountFormSheet,
    AddTransactionSheet,
    ConnectBankSheet,
    HomeConnectSheet,
    TutorialSheet,
    WidgetSheet,
)

from .views.accounts import build_accounts
from .views.home import build_home
from .views.movements import MovementsView
from .views.reports import build_reports
from .views.settings_view import build_settings, CURRENCIES

CURRENCY_SYMBOLS = {code: symbol for code, symbol, _ in CURRENCIES}


class LibretaApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.db = Database().init()
        self.ledger = Ledger(self.db)
        self.settings = SettingsService(self.db)
        theme.apply_palette(self.settings.get("theme_palette", "esmeralda"))
        theme.configure_page(page)
        self.ledger.seed_initial()
        self.dashboard = DashboardService(self.ledger, self.settings)
        self.demo_feed = DemoFeed(self.ledger, self.settings)
        self.widget_service = WidgetService(self.dashboard, self.settings)
        self.exports = ExportService(self.ledger)
        self.update_checker = UpdateChecker()
        self.sync = SyncManager(
            self.ledger,
            self.settings,
            on_event=self._on_remote_event,
            on_status=self._on_sync_status,
        )
        self.current_tab = 0
        self.hide_balances = self.settings.get_bool("hide_balances", False)
        self.movements_month_offset = 0
        self.movements_kind = "all"
        self.sync_state = "idle"
        self.settings_form: dict = {}
        self.server_form: dict = {}

        self.prefs = ft.SharedPreferences()
        self.file_picker = ft.FilePicker()
        self.url_launcher = ft.UrlLauncher()
        self.clipboard = ft.Clipboard()
        self.share = ft.Share()
        page.services.extend([self.prefs, self.file_picker, self.url_launcher, self.clipboard, self.share])

        self._build_shell()
        page.on_close = self._on_close
        page.update()
        self.refresh()
        page.run_task(self._demo_loop)
        page.run_task(self._remote_loop)
        page.run_task(self._startup)
        page.run_task(self._tutorial_startup)
        page.run_task(self._update_loop)
        page.run_task(self._refresh_widget_background)

    # ------------------------------------------------------------------ shell

    def _build_shell(self) -> None:
        self.content_host = ft.Container(expand=True, bgcolor=theme.PAPER)
        self.nav = ft.NavigationBar(
            selected_index=0,
            bgcolor=theme.CARD,
            indicator_color=theme.MINT,
            label_behavior=ft.NavigationBarLabelBehavior.ALWAYS_SHOW,
            elevation=0,
            height=70,
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME_ROUNDED, label="Inicio"),
                ft.NavigationBarDestination(icon=ft.Icons.RECEIPT_LONG_OUTLINED, selected_icon=ft.Icons.RECEIPT_LONG_ROUNDED, label="Movs."),
                ft.NavigationBarDestination(icon=ft.Icons.PIE_CHART_OUTLINE_ROUNDED, selected_icon=ft.Icons.PIE_CHART_ROUNDED, label="Reportes"),
                ft.NavigationBarDestination(icon=ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, selected_icon=ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED, label="Cuentas"),
                ft.NavigationBarDestination(icon=ft.Icons.TUNE_ROUNDED, selected_icon=ft.Icons.TUNE_ROUNDED, label="Ajustes"),
            ],
            on_change=self._on_nav_change,
        )
        shell = ft.Column([self.content_host, self.nav], spacing=0, expand=True)
        self.page.add(ft.SafeArea(content=shell, expand=True, minimum_padding=0))

    def _on_nav_change(self, event) -> None:
        index = int(event.control.selected_index or 0)
        if index == self.current_tab:
            return
        self.current_tab = index
        self.refresh()

    def select_tab(self, index: int) -> None:
        self.current_tab = max(0, min(4, index))
        self.refresh()

    def _build_view(self, index: int) -> ft.Control:
        if index == 0:
            return build_home(self)
        if index == 1:
            return MovementsView(self).build()
        if index == 2:
            return build_reports(self)
        if index == 3:
            return build_accounts(self)
        return build_settings(self)

    def refresh(self) -> None:
        try:
            view = self._build_view(self.current_tab)
            self.content_host.content = view
            self.nav.selected_index = self.current_tab
            self.page.update()
        except Exception as exc:
            # Un fallo de render no debe tumbar la app; lo registramos para
            # poder diagnosticarlo desde la consola.
            import traceback

            traceback.print_exc()
            try:
                self.show_snack(f"Error al dibujar: {exc}", error=True)
            except Exception:
                pass

    def _on_close(self, event=None) -> None:
        self.sync.stop()

    # ------------------------------------------------------------------ helpers

    @property
    def symbol(self) -> str:
        return self.settings.symbol

    @property
    def connection_label(self) -> str:
        if self.settings.get_bool("internet_enabled", False):
            return "Nube en vivo" if self.sync_state == "connected" else "Nube"
        if self.settings.demo_live:
            return "Demo en vivo"
        return "Datos locales"

    def today_transactions(self, limit: int = 5):
        start, end = day_bounds()
        return self.ledger.transaction_views(start=start, end=end, limit=limit)

    def show_snack(self, message: str, error: bool = False) -> None:
        try:
            snack = ft.SnackBar(
                content=ft.Text(message, color=theme.WHITE, size=12.5),
                bgcolor=theme.CORAL if error else theme.GREEN_DEEP,
                duration=3200,
                behavior=ft.SnackBarBehavior.FLOATING,
                margin=ft.Margin.symmetric(horizontal=16, vertical=12),
                shape=ft.RoundedRectangleBorder(radius=14),
                show_close_icon=False,
            )
            self.page.show_dialog(snack)
        except Exception:
            pass

    def copy_text(self, value: str) -> None:
        try:
            self.page.run_task(self.clipboard.set, value)
            self.show_snack("Copiado al portapapeles")
        except Exception:
            self.show_snack("No se pudo copiar", error=True)

    def open_url(self, url: str) -> None:
        try:
            self.page.run_task(self.url_launcher.launch_url, url)
        except Exception:
            self.show_snack("No se pudo abrir el navegador", error=True)

    # ------------------------------------------------------------------ acciones

    def open_add(self, *, kind: str = "expense", default_account_id: str | None = None) -> None:
        AddTransactionSheet(self, kind=kind, default_account_id=default_account_id).open()

    def open_edit(self, view) -> None:
        AddTransactionSheet(self, tx_view=view).open()

    def open_account_form(self) -> None:
        AccountFormSheet(self).open()

    def open_account_detail(self, account) -> None:
        AccountDetailSheet(self, account).open()

    def open_connect_sheet(self) -> None:
        ConnectBankSheet(self).open()

    def open_widget_sheet(self) -> None:
        WidgetSheet(self).open()

    def open_tutorial(self, event=None) -> None:
        TutorialSheet(self).open()

    def open_home_connect(self, event=None) -> None:
        self.request_network_permission(lambda: HomeConnectSheet(self).open())

    def request_network_permission(self, on_allow=None, on_deny=None) -> None:
        if self.settings.get_bool("network_permission_granted", False):
            if on_allow:
                on_allow()
            return
        dialog: ft.AlertDialog

        def allow(event=None):
            self.settings.set("network_permission_granted", True)
            try:
                self.page.pop_dialog()
            except Exception:
                pass
            self.refresh()
            if on_allow:
                on_allow()
            self.page.run_task(self._check_updates_once)

        def deny(event=None):
            try:
                self.page.pop_dialog()
            except Exception:
                pass
            if on_deny:
                on_deny()

        dialog = ft.AlertDialog(
            modal=True,
            icon=ft.Icon(ft.Icons.WIFI_ROUNDED, color=theme.GREEN, size=30),
            title=text("Permiso de red", size=19, display=True),
            content=text(
                "Sapardobank necesita permiso para usar la red de tu casa y buscar el servidor local. "
                "Solo se conecta a la dirección que configures; no lee tus fotos, contactos ni otros datos.",
                size=11.5,
                color=theme.MUTED,
            ),
            actions=[
                ft.TextButton("Ahora no", on_click=deny),
                ft.FilledButton(
                    "Permitir",
                    on_click=allow,
                    style=ft.ButtonStyle(bgcolor=theme.GREEN, color=theme.WHITE),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            inset_padding=ft.Padding.all(18),
            bgcolor=theme.CARD,
        )
        self.page.show_dialog(dialog)

    async def _tutorial_startup(self) -> None:
        """Muestra el tutorial una vez, sin bloquear el arranque."""
        await asyncio.sleep(1.2)
        try:
            if not self.settings.get_bool("tutorial_seen", False):
                self.open_tutorial()
        except Exception:
            pass

    def after_change(self, message: str | None = None) -> None:
        self.refresh()
        if message:
            self.show_snack(message)
        self.page.run_task(self._refresh_widget_background)

    def toggle_balance_visibility(self, event=None) -> None:
        self.hide_balances = not self.hide_balances
        self.settings.set("hide_balances", self.hide_balances)
        self.refresh()

    def set_theme_palette(self, name: str) -> None:
        applied = theme.apply_palette(name)
        self.settings.set("theme_palette", applied)
        self.page.bgcolor = theme.PAPER
        self.page.theme = theme.app_theme()
        self.content_host.bgcolor = theme.PAPER
        self.nav.bgcolor = theme.CARD
        self.nav.indicator_color = theme.MINT
        self.refresh()
        self.page.run_task(self._refresh_widget_background)
        label = theme.PALETTES[applied]["label"]
        self.show_snack(f"Tema {label} aplicado")

    def set_demo_live(self, value: bool) -> None:
        if value and not self.ledger.demo_account():
            self.ledger.load_demo()
        self.settings.set("demo_live", value)
        self.refresh()
        self.show_snack("Feed de demostración activado" if value else "Feed de demostración pausado")

    def disable_demo(self, event=None) -> None:
        self.set_demo_live(False)

    def set_demo_interval(self, seconds: int) -> None:
        self.settings.set("demo_interval_seconds", max(15, int(seconds)))

    def simulate_expense(self, account_id: str | None = None) -> None:
        tx = self.demo_feed.generate(force=True)
        if not tx:
            self.show_snack("No hay una cuenta demo disponible", error=True)
            return
        self.after_change(f"Compra simulada: {tx.description}")

    def simulate_income(self) -> None:
        tx = self.demo_feed.simulate_income()
        if not tx:
            self.show_snack("No hay una cuenta demo disponible", error=True)
            return
        self.after_change("Ingreso simulado")

    # ------------------------------------------------------------------ ajustes

    def save_profile_from_controls(self, event=None) -> None:
        form = self.settings_form
        if not form:
            return
        name = (form["name"].value or "").strip()
        currency = form["currency"].value or "MXN"
        symbol = CURRENCY_SYMBOLS.get(currency, "$")
        try:
            raw = (form["budget"].value or "").strip()
            budget = 0 if raw in {"", "0", "0.00"} else parse_amount_to_cents(raw)
        except MoneyError as exc:
            self.show_snack(str(exc), error=True)
            return
        self.settings.set("user_name", name)
        self.settings.set("currency", currency)
        self.settings.set("currency_symbol", symbol)
        self.settings.set("daily_budget_cents", max(0, budget))
        self.refresh()
        self.page.run_task(self._refresh_widget_background)
        self.show_snack("Perfil guardado")

    def set_internet(self, value: bool) -> None:
        if not value:
            self._apply_internet(False)
            return
        if not (self.settings.get("api_url") and self.settings.get("api_token")):
            self.settings.set("internet_enabled", False)
            self.show_snack("Configura el servidor y el token primero", error=True)
            self.refresh()
            return
        if not self.settings.get_bool("network_permission_granted", False):
            self.request_network_permission(
                lambda: self._apply_internet(True),
                lambda: self._apply_internet(False),
            )
            return
        self._apply_internet(True)

    def _apply_internet(self, value: bool) -> None:
        self.settings.set("internet_enabled", value)
        self.refresh()
        self.show_snack("Internet activado" if value else "Internet desactivado")
        if value:
            self.page.run_task(self._kick_sync)
            self.page.run_task(self._check_updates_once)

    def save_server_async(self) -> None:
        form = self.server_form
        if not form:
            return
        raw_url = (form["url"].value or "").strip()
        token = (form["token"].value or "").strip()
        try:
            url = validate_server_url(raw_url)
            if not token:
                raise RemoteError("Escribe el token del servidor")
        except RemoteError as exc:
            self.show_snack(str(exc), error=True)
            return
        self.settings.set("api_url", url)
        self.settings.set("api_token", token)
        self.refresh()

        def begin():
            self.settings.set("internet_enabled", True)
            self.refresh()
            self.show_snack("Servidor guardado; probando conexión…")
            self.page.run_task(self._test_and_sync, url, token)

        def deny():
            self.settings.set("internet_enabled", False)
            self.refresh()

        if self.settings.get_bool("network_permission_granted", False):
            begin()
        else:
            self.request_network_permission(begin, deny)

    def test_server_async(self) -> None:
        form = self.server_form
        if not form:
            return
        raw_url = (form["url"].value or "").strip()
        token = (form["token"].value or "").strip()
        self.request_network_permission(
            lambda: self.page.run_task(self._test_server, raw_url, token)
        )

    async def _test_server(self, raw_url: str, token: str) -> None:
        try:
            url = validate_server_url(raw_url)
            if not token:
                raise RemoteError("Falta el token")
            client = RemoteClient(url, token)
            info = await asyncio.to_thread(client.health)
            self.show_snack(f"Conectado · {info.get('app', 'Sapardobank')} {info.get('version', '')}")
        except Exception as exc:
            self.show_snack(str(exc), error=True)

    async def _test_and_sync(self, url: str, token: str) -> None:
        try:
            client = RemoteClient(url, token)
            await asyncio.to_thread(client.health)
            self.sync_state = "connected"
            result = await asyncio.to_thread(self.sync.sync_now)
            if result.ok:
                self.refresh()
                self.show_snack(
                    f"Sincronizado · {result.transactions} movimientos"
                )
            else:
                self.show_snack(result.message, error=True)
        except Exception as exc:
            self.sync_state = "error"
            self.show_snack(str(exc), error=True)

    async def _kick_sync(self) -> None:
        result = await asyncio.to_thread(self.sync.sync_now)
        if result.ok:
            self.refresh()
            self.show_snack(f"Sincronizado · {result.transactions} movimientos")
        else:
            self.show_snack(result.message, error=True)

    def sync_now_async(self, event=None) -> None:
        if not self.settings.get_bool("internet_enabled", False):
            if not (self.settings.get("api_url") and self.settings.get("api_token")):
                self.show_snack("Configura el servidor o usa Conectar a mi casa", error=True)
                return
            self.request_network_permission(
                lambda: self._enable_and_sync(),
                None,
            )
            return
        self.show_snack("Sincronizando…")
        self.page.run_task(self._kick_sync)

    def _enable_and_sync(self) -> None:
        self.settings.set("internet_enabled", True)
        self.refresh()
        self.show_snack("Sincronizando…")
        self.page.run_task(self._kick_sync)

    def open_bank_link(self) -> None:
        try:
            url = self.sync.client().link_url()
        except Exception as exc:
            self.show_snack(str(exc), error=True)
            return
        self.open_url(url)
        self.show_snack("Termina la vinculación en el navegador y vuelve a sincronizar.")
        self.page.run_task(self._delayed_sync)

    async def _delayed_sync(self) -> None:
        await asyncio.sleep(20)
        if self.settings.get_bool("internet_enabled", False):
            result = await asyncio.to_thread(self.sync.sync_now)
            if result.ok:
                self.refresh()

    # ------------------------------------------------------------ actualizaciones

    def set_check_updates(self, value: bool) -> None:
        self.settings.set("check_updates", value)
        self.refresh()
        if value:
            self.page.run_task(self._check_updates_once)

    async def _check_updates_once(self) -> None:
        if not (
            self.settings.get_bool("check_updates", True)
            and self.settings.get_bool("network_permission_granted", False)
            and self.settings.get_bool("tutorial_seen", False)
        ):
            return
        try:
            info = await asyncio.to_thread(self.update_checker.check)
        except Exception:
            return
        if not info:
            return
        if not is_newer(info.version, __version__):
            return
        if self.settings.get("skipped_version", "") == info.version:
            return
        self._show_update_dialog(info)

    async def _update_loop(self) -> None:
        await asyncio.sleep(15)
        while True:
            await self._check_updates_once()
            await asyncio.sleep(6 * 3600)

    def _show_update_dialog(self, info: UpdateInfo, *, test: bool = False) -> None:
        def later(event=None):
            if not test:
                self.settings.set("skipped_version", info.version)
            try:
                self.page.pop_dialog()
            except Exception:
                pass

        def download(event=None):
            if not test:
                self.settings.set("skipped_version", info.version)
            try:
                self.page.pop_dialog()
            except Exception:
                pass
            self.open_url(info.download_url)

        dialog = ft.AlertDialog(
            modal=True,
            icon=ft.Icon(ft.Icons.SYSTEM_UPDATE_ROUNDED, color=theme.GREEN, size=32),
            title=text("Nueva versión disponible", size=20, display=True),
            content=ft.Column(
                [
                    text(
                        f"Sapardobank {info.version} ya está disponible. La tienes instalada: {__version__}.",
                        size=12,
                        color=theme.MUTED,
                    ),
                    ft.Container(height=6),
                    text(
                        "Descarga el APK nuevo y ábrelo para actualizar. Tus datos locales se conservan.",
                        size=11,
                        color=theme.MUTED,
                    ),
                ],
                spacing=0,
                tight=True,
            ),
            actions=[
                ft.TextButton("Ahora no", on_click=later),
                ft.FilledButton(
                    "Descargar",
                    on_click=download,
                    style=ft.ButtonStyle(bgcolor=theme.GREEN, color=theme.WHITE),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            inset_padding=ft.Padding.all(18),
            bgcolor=theme.CARD,
        )
        self.page.show_dialog(dialog)

    def test_update_popup(self, event=None) -> None:
        current = [int(x) for x in __version__.split(".") if x.isdigit()]
        while len(current) < 3:
            current.append(0)
        current[2] += 1
        fake = ".".join(str(x) for x in current)
        self._show_update_dialog(
            UpdateInfo(
                version=fake,
                tag=f"v{fake}",
                download_url="https://github.com/joseestebanmarinrincones-dot/sapardobank/releases/latest",
                release_url="https://github.com/joseestebanmarinrincones-dot/sapardobank/releases/latest",
                notes="Vista previa del aviso de actualización.",
            ),
            test=True,
        )

    # ------------------------------------------------------------------ datos

    def export_csv_async(self, event=None) -> None:
        self.page.run_task(self._export_csv_task)

    async def _export_csv_task(self) -> None:
        try:
            data = self.exports.csv_bytes()
            name = self.exports.suggested_name()
            path = await self.file_picker.save_file(
                dialog_title="Guardar movimientos",
                file_name=name,
                allowed_extensions=["csv"],
                file_type=ft.FilePickerFileType.CUSTOM,
                src_bytes=data,
            )
            if path:
                self.show_snack(f"Guardado en {Path(path).name}")
            else:
                fallback = self.exports.save_to_disk()
                self.show_snack(f"Guardado en {fallback}")
        except Exception as exc:
            self.show_snack(f"No pude exportar: {exc}", error=True)

    def reset_demo_async(self, event=None) -> None:
        dialog = ft.AlertDialog(
            modal=True,
            title=text("¿Cargar datos de demostración?", size=18, display=True),
            content=text(
                "Se agregará una cuenta demo con movimientos de ejemplo. Tus cuentas y movimientos reales no se tocan.",
                size=12,
                color=theme.MUTED,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()),
                ft.FilledButton(
                    "Cargar demo",
                    on_click=lambda e: self._do_load_demo(),
                    style=ft.ButtonStyle(bgcolor=theme.GREEN, color=theme.WHITE),
                ),
            ],
        )
        self.page.show_dialog(dialog)

    def _do_load_demo(self) -> None:
        self.page.pop_dialog()
        self.ledger.load_demo()
        self.after_change("Datos de demostración cargados")

    def confirm_wipe(self, event=None) -> None:
        dialog = ft.AlertDialog(
            modal=True,
            title=text("¿Borrar todos los datos?", size=18, display=True),
            content=text("Se eliminarán cuentas, movimientos y presupuestos. La app quedará como nueva, sin datos de ejemplo.", size=12, color=theme.MUTED),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()),
                ft.FilledButton("Borrar todo", on_click=lambda e: self._do_wipe(), style=ft.ButtonStyle(bgcolor=theme.CORAL, color=theme.WHITE)),
            ],
        )
        self.page.show_dialog(dialog)

    def _do_wipe(self) -> None:
        self.page.pop_dialog()
        for table in ["transactions", "accounts", "budgets", "sync_log"]:
            self.ledger.db.execute(f"DELETE FROM {table}")
        self.ledger.ensure_categories()
        self.ledger.create_account(
            "Mi efectivo",
            institution="En tu bolsillo",
            kind="cash",
            initial_balance_cents=0,
            color=theme.GREEN,
            icon="PAYMENTS_ROUNDED",
            provider="cash",
        )
        set_setting(self.ledger.db, "seeded", "1")
        set_setting(self.ledger.db, "demo_live", "0")
        set_setting(self.ledger.db, "daily_budget_cents", "45000")
        self.after_change("Datos borrados; empiezas de cero")

    # ------------------------------------------------------------------ widget

    async def _refresh_widget_background(self) -> None:
        try:
            render = await asyncio.to_thread(self.widget_service.render)
            await self._push_widget_prefs(render)
        except Exception:
            pass

    def publish_widget(self, render) -> None:
        self.page.run_task(self._push_widget_prefs, render)
        self.page.run_task(self._broadcast_widget_refresh)
        self.show_snack("Widget actualizado. Agrégalo desde el inicio del teléfono.")

    async def _push_widget_prefs(self, render) -> None:
        try:
            meta_path = render.path.with_suffix(".json")
            data = await asyncio.to_thread(meta_path.read_text, "utf-8")
            payload = {
                "variant": render.variant,
                "theme": render.theme,
                "updated_at": now_iso(),
                **json.loads(data),
            }
            await self.prefs.set("libreta_widget", json.dumps(payload, ensure_ascii=False))
        except Exception:
            pass

    async def _broadcast_widget_refresh(self) -> None:
        """Opcional: si pyjnius está disponible, despierta al widget nativo."""
        try:
            from jnius import autoclass  # type: ignore

            activity_thread = autoclass("android.app.ActivityThread")
            application = activity_thread.currentApplication()
            context = application.getApplicationContext()
            intent = autoclass("android.content.Intent")("com.sapardobank.app.WIDGET_REFRESH")
            intent.setPackage(context.getPackageName())
            context.sendBroadcast(intent)
        except Exception:
            pass

    def export_widget_image(self, render) -> None:
        self.page.run_task(self._export_widget_task, render)

    async def _export_widget_task(self, render) -> None:
        try:
            path = await self.file_picker.save_file(
                dialog_title="Guardar widget",
                file_name="libreta-widget.png",
                allowed_extensions=["png"],
                file_type=ft.FilePickerFileType.CUSTOM,
                src_bytes=render.image_bytes,
            )
            if path:
                self.show_snack(f"Widget guardado en {Path(path).name}")
            else:
                fallback = render.path
                self.show_snack(f"Widget actualizado en {fallback.name}")
        except Exception as exc:
            self.show_snack(f"No pude guardar la imagen: {exc}", error=True)

    # ------------------------------------------------------------------ loops

    async def _startup(self) -> None:
        await asyncio.sleep(1)
        if (
            self.settings.get_bool("internet_enabled", False)
            and self.settings.get_bool("network_permission_granted", False)
            and self.settings.get("api_url")
        ):
            result = await asyncio.to_thread(self.sync.sync_now)
            if result.ok:
                self.refresh()

    async def _demo_loop(self) -> None:
        first = True
        while True:
            try:
                if not self.settings.demo_live:
                    await asyncio.sleep(10)
                    continue
                interval = max(15, self.settings.get_int("demo_interval_seconds", 75))
                await asyncio.sleep(min(interval, 30) if first else interval)
                first = False
                if not self.settings.demo_live:
                    continue
                tx = await asyncio.to_thread(self.demo_feed.generate)
                if tx:
                    self.refresh()
                    self.show_snack(f"Nuevo gasto demo · {tx.description}")
                    await self._refresh_widget_background()
            except asyncio.CancelledError:
                raise
            except Exception:
                await asyncio.sleep(10)

    def _on_remote_event(self, event: dict) -> None:
        if event.get("type") == "transaction" and event.get("transaction"):
            tx = event["transaction"]
            self.refresh()
            self.show_snack(f"Nuevo movimiento del banco · {tx.get('description', '')}")
            self.page.run_task(self._refresh_widget_background)
        elif event.get("type") == "hello":
            self.sync_state = "connected"

    def _on_sync_status(self, status: str) -> None:
        self.sync_state = status

    async def _remote_loop(self) -> None:
        config = None
        stream_task: asyncio.Task | None = None
        last_sync = 0.0
        while True:
            try:
                enabled = self.settings.get_bool("internet_enabled", False) and self.settings.get_bool("network_permission_granted", False)
                url = self.settings.get("api_url")
                token = self.settings.get("api_token")
                current = (enabled, url, token)
                if current != config:
                    if stream_task:
                        stream_task.cancel()
                        stream_task = None
                    config = current
                    last_sync = 0.0
                    if enabled and url and token:
                        self.sync = SyncManager(
                            self.ledger,
                            self.settings,
                            on_event=self._on_remote_event,
                            on_status=self._on_sync_status,
                        )
                        stream_task = asyncio.create_task(self.sync.run_stream())
                if enabled and url and token and (time.time() - last_sync > 120):
                    result = await asyncio.to_thread(self.sync.sync_now)
                    last_sync = time.time()
                    if result.ok:
                        self.sync_state = "connected"
                        self.refresh()
                await asyncio.sleep(15)
            except asyncio.CancelledError:
                if stream_task:
                    stream_task.cancel()
                raise
            except Exception:
                await asyncio.sleep(15)
