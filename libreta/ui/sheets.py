"""Hojas modales: alta/edición de movimientos, cuentas, conexiones y widget."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, time, timedelta

import flet as ft

from ..core.catalog import ACCOUNT_ICONS
from ..core.dates import human_day, now_iso
from ..core.models import Account, TransactionView
from ..core.money import MoneyError, format_money, parse_amount_to_cents
from ..services.remote import RemoteClient, RemoteError, discover_local_servers, validate_server_url
from . import theme
from .theme import alpha, text
from .components import (
    account_card,
    category_bubble,
    full_width,
    icon_bubble,
    icon_button,
    input_field,
    pill,
    primary_button,
    secondary_button,
    section_header,
    soft_card,
    text_button,
    tx_tile,
)



def _sheet_height(app) -> int:
    height = app.page.height or 820
    return max(560, min(860, int(height * 0.92)))


def _close(app) -> None:
    app.page.pop_dialog()


class AddTransactionSheet:
    def __init__(
        self,
        app,
        *,
        tx_view: TransactionView | None = None,
        kind: str = "expense",
        default_account_id: str | None = None,
    ):
        self.app = app
        self.tx_view = tx_view
        self.tx = tx_view.transaction if tx_view else None
        self.kind = "income" if self.tx and self.tx.amount_cents > 0 else kind
        self.selected_category = (
            self.tx.category_id if self.tx and self.tx.category_id else ("income" if self.kind == "income" else "coffee")
        )
        self.selected_date = (
            datetime.fromisoformat(self.tx.occurred_at).date() if self.tx else date.today()
        )
        self.default_account_id = (
            self.tx.account_id if self.tx else (default_account_id or (app.ledger.accounts()[0].id if app.ledger.accounts() else None))
        )
        self.category_row: ft.Row | None = None
        self.date_text: ft.Text | None = None
        self.amount_field: ft.TextField | None = None
        self.desc_field: ft.TextField | None = None
        self.account_dropdown: ft.Dropdown | None = None
        self.sheet: ft.BottomSheet | None = None

    def open(self) -> None:
        categories = self._categories_for_kind()
        if self.selected_category not in [c.id for c in categories]:
            self.selected_category = categories[0].id if categories else "other"

        title = "Editar movimiento" if self.tx else ("Nuevo ingreso" if self.kind == "income" else "Nuevo gasto")
        amount_value = f"{abs(self.tx.amount_cents) / 100:.2f}" if self.tx else ""
        self.amount_field = ft.TextField(
            value=amount_value,
            hint_text="0.00",
            text_size=34,
            color=theme.INK,
            cursor_color=theme.GREEN,
            border=ft.InputBorder.NONE,
            content_padding=ft.Padding.symmetric(horizontal=8, vertical=8),
            keyboard_type=ft.KeyboardType.NUMBER,
            autofocus=not bool(self.tx),
            prefix=text(self.app.symbol, size=30, color=theme.MUTED, display=True),
            expand=True,
        )
        amount_shell = ft.Container(
            content=ft.Row(
                [
                    self.amount_field,
                    pill(self.app.settings.currency, color=theme.GREEN, bgcolor=theme.MINT_SOFT, size=9),
                ],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=theme.CARD_WARM,
            border=ft.Border.all(1, theme.LINE),
            border_radius=18,
            padding=ft.Padding.symmetric(horizontal=8, vertical=2),
        )

        self.desc_field = input_field(
            "¿En qué fue? (ej. Comida con Ana)",
            value=self.tx.description if self.tx else "",
            prefix_icon=ft.Icons.EDIT_NOTE_ROUNDED,
        )

        self.category_row = ft.Row(wrap=True, spacing=7, run_spacing=7)
        self._refresh_categories()

        accounts = self.app.ledger.accounts()
        self.account_dropdown = ft.Dropdown(
            label="Cuenta",
            value=self.default_account_id,
            options=[
                ft.DropdownOption(
                    key=a.id,
                    text=f"{a.name} · {format_money(self.app.ledger.account_balance(a), self.app.symbol)}",
                )
                for a in accounts
            ],
            filled=True,
            fill_color=theme.CARD_WARM,
            border=ft.InputBorder.NONE,
            border_radius=14,
            content_padding=ft.Padding.symmetric(horizontal=14, vertical=8),
            leading_icon=ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED,
            expand=True,
        )

        self.date_text = text(human_day(self.selected_date), size=13, color=theme.INK, weight=ft.FontWeight.W_700)
        date_button = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.CALENDAR_MONTH_ROUNDED, size=18, color=theme.GREEN),
                    ft.Column(
                        [
                            text("Fecha", size=9.5, color=theme.MUTED),
                            self.date_text,
                        ],
                        spacing=0,
                        expand=True,
                    ),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, size=17, color=theme.MUTED),
                ],
                spacing=9,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=theme.CARD,
            border=ft.Border.all(1, theme.LINE),
            border_radius=14,
            padding=ft.Padding.symmetric(horizontal=13, vertical=9),
            on_click=self._pick_date,
            ink=True,
        )

        save_label = "Guardar cambios" if self.tx else "Guardar movimiento"
        if self.tx:
            actions: list[ft.Control] = [
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Icon(ft.Icons.DELETE_OUTLINE_ROUNDED, size=20, color=theme.CORAL),
                            width=50,
                            height=50,
                            border_radius=16,
                            bgcolor=theme.CORAL_SOFT,
                            alignment=ft.Alignment.CENTER,
                            on_click=self._confirm_delete,
                            ink=True,
                            tooltip="Eliminar",
                        ),
                        primary_button(save_label, self._save, icon=ft.Icons.CHECK_ROUNDED, expand=True, height=50),
                    ],
                    spacing=8,
                )
            ]
        else:
            actions = [
                ft.Row(
                    [primary_button(save_label, self._save, icon=ft.Icons.CHECK_ROUNDED, expand=True, height=50)]
                )
            ]

        form = ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                text(title, size=23, display=True),
                                text(
                                    "Corrige el detalle" if self.tx else "Registra en segundos",
                                    size=10.5,
                                    color=theme.MUTED,
                                ),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Icon(ft.Icons.CLOSE_ROUNDED, size=20, color=theme.INK),
                            width=36,
                            height=36,
                            border_radius=18,
                            bgcolor=theme.CARD_WARM,
                            alignment=ft.Alignment.CENTER,
                            on_click=lambda e: _close(self.app),
                            ink=True,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=12),
                ft.SegmentedButton(
                    segments=[
                        ft.Segment(
                            value="expense",
                            label=text("Gasto", size=12, weight=ft.FontWeight.W_700),
                            icon=ft.Icons.ARROW_UPWARD_ROUNDED,
                        ),
                        ft.Segment(
                            value="income",
                            label=text("Ingreso", size=12, weight=ft.FontWeight.W_700),
                            icon=ft.Icons.ARROW_DOWNWARD_ROUNDED,
                        ),
                    ],
                    selected=[self.kind],
                    on_change=self._on_kind_change,
                    style=ft.ButtonStyle(
                        color={ft.ControlState.SELECTED: theme.WHITE, ft.ControlState.DEFAULT: theme.INK},
                        bgcolor={ft.ControlState.SELECTED: theme.GREEN, ft.ControlState.DEFAULT: theme.CARD_WARM},
                        shape=ft.RoundedRectangleBorder(radius=12),
                        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                    ),
                ),
                ft.Container(height=12),
                amount_shell,
                ft.Container(height=10),
                full_width(self.desc_field),
                ft.Container(height=12),
                text("Categoría", size=11, color=theme.MUTED, weight=ft.FontWeight.W_700),
                ft.Container(height=6),
                self.category_row,
                ft.Container(height=12),
                ft.Row([self.account_dropdown], spacing=0),
                ft.Container(height=8),
                date_button,
                ft.Container(height=16),
                *actions,
                ft.Container(height=12),
            ],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        self.sheet = ft.BottomSheet(
            content=ft.Container(
                content=form,
                padding=ft.Padding.only(left=20, right=20, top=8, bottom=12),
                height=_sheet_height(self.app),
            ),
            bgcolor=theme.CARD,
            show_drag_handle=True,
            use_safe_area=True,
            dismissible=True,
            draggable=True,
        )
        self.app.page.show_dialog(self.sheet)

    def _categories_for_kind(self):
        return self.app.ledger.categories("income" if self.kind == "income" else "expense")

    def _refresh_categories(self) -> None:
        if not self.category_row:
            return
        chips = []
        for cat in self._categories_for_kind():
            selected = cat.id == self.selected_category
            chips.append(
                ft.Container(
                    width=101,
                    height=68,
                    border_radius=14,
                    bgcolor=alpha(cat.color, 0.13) if selected else theme.CARD_WARM,
                    border=ft.Border.all(2 if selected else 1, cat.color if selected else theme.LINE),
                    alignment=ft.Alignment.CENTER,
                    on_click=lambda e, c=cat: self._select_category(c.id),
                    ink=True,
                    content=ft.Column(
                        [
                            ft.Icon(getattr(ft.Icons, cat.icon, ft.Icons.CIRCLE), size=19, color=cat.color),
                            text(cat.name, size=10, color=theme.INK if selected else theme.INK_SOFT, weight=ft.FontWeight.W_700 if selected else None, align=ft.TextAlign.CENTER, max_lines=1),
                        ],
                        spacing=3,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )
        self.category_row.controls = chips
        try:
            self.category_row.update()
        except Exception:
            pass

    def _select_category(self, category_id: str) -> None:
        self.selected_category = category_id
        self._refresh_categories()

    def _on_kind_change(self, event) -> None:
        selected = event.control.selected
        if selected:
            new_kind = selected[0]
            if new_kind != self.kind:
                self.kind = new_kind
                categories = self._categories_for_kind()
                self.selected_category = categories[0].id if categories else "other"
                self._refresh_categories()

    def _pick_date(self, event) -> None:
        picker = ft.DatePicker(
            value=datetime.combine(self.selected_date, datetime.min.time()),
            first_date=date(2015, 1, 1),
            last_date=date.today() + timedelta(days=1),
            on_change=self._date_changed,
        )
        self.app.page.show_dialog(picker)

    def _date_changed(self, event) -> None:
        value = event.control.value
        if isinstance(value, datetime):
            self.selected_date = value.date()
        elif isinstance(value, date):
            self.selected_date = value
        if self.date_text:
            self.date_text.value = human_day(self.selected_date)
            self.date_text.update()
        try:
            event.control.open = False
            event.control.update()
        except Exception:
            pass

    def _occurred_at(self) -> str:
        if self.tx:
            original = datetime.fromisoformat(self.tx.occurred_at)
            if original.date() == self.selected_date:
                return original.replace(microsecond=0).isoformat()
        now = datetime.now().replace(microsecond=0)
        if self.selected_date == now.date():
            return now.isoformat()
        return datetime.combine(self.selected_date, time(12, 0)).isoformat()

    def _save(self, event=None) -> None:
        try:
            amount = parse_amount_to_cents(self.amount_field.value if self.amount_field else "")
        except MoneyError as exc:
            self.app.show_snack(str(exc), error=True)
            return
        account_id = self.account_dropdown.value if self.account_dropdown else None
        if not account_id:
            self.app.show_snack("Elige una cuenta", error=True)
            return
        description = (self.desc_field.value or "").strip() if self.desc_field else ""
        category = self.app.ledger.category(self.selected_category)
        if not description:
            description = "Ingreso" if self.kind == "income" else "Gasto"
        signed = amount if self.kind == "income" else -amount
        occurred = self._occurred_at()
        try:
            if self.tx:
                self.app.ledger.update_transaction(
                    self.tx.id,
                    account_id=account_id,
                    amount_cents=signed,
                    description=description,
                    category_id=self.selected_category,
                    occurred_at=occurred,
                )
                message = "Movimiento actualizado"
            else:
                self.app.ledger.add_transaction(
                    account_id=account_id,
                    amount_cents=signed,
                    description=description,
                    category_id=self.selected_category,
                    occurred_at=occurred,
                    source="manual",
                )
                message = "Ingreso guardado" if self.kind == "income" else "Gasto guardado"
        except Exception as exc:
            self.app.show_snack(str(exc), error=True)
            return
        _close(self.app)
        self.app.after_change(message)

    def _confirm_delete(self, event=None) -> None:
        dialog = ft.AlertDialog(
            modal=True,
            title=text("¿Eliminar movimiento?", size=18, display=True),
            content=text("Esta acción no se puede deshacer.", size=12, color=theme.MUTED),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.app.page.pop_dialog()),
                ft.FilledButton(
                    "Eliminar",
                    on_click=lambda e: self._do_delete(),
                    style=ft.ButtonStyle(bgcolor=theme.CORAL, color=theme.WHITE),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.app.page.show_dialog(dialog)

    def _do_delete(self) -> None:
        if self.tx:
            self.app.ledger.delete_transaction(self.tx.id)
        self.app.page.pop_dialog()  # alerta
        _close(self.app)  # hoja
        self.app.after_change("Movimiento eliminado")


class AccountFormSheet:
    def __init__(self, app):
        self.app = app
        self.name_field: ft.TextField | None = None
        self.institution_field: ft.TextField | None = None
        self.balance_field: ft.TextField | None = None
        self.kind_dropdown: ft.Dropdown | None = None
        self.color = "#0F6B54"

    def open(self) -> None:
        self.name_field = input_field("Nombre de la cuenta", prefix_icon=ft.Icons.BADGE_ROUNDED)
        self.institution_field = input_field("Banco o institución (opcional)", prefix_icon=ft.Icons.ACCOUNT_BALANCE_ROUNDED)
        self.balance_field = input_field(
            "Saldo inicial",
            value="0.00",
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix_icon=ft.Icons.PAYMENTS_OUTLINED,
            suffix=text(self.app.symbol, size=13, color=theme.MUTED),
        )
        self.kind_dropdown = ft.Dropdown(
            label="Tipo de cuenta",
            value="debit",
            options=[
                ft.DropdownOption(key="debit", text="Débito"),
                ft.DropdownOption(key="credit", text="Crédito"),
                ft.DropdownOption(key="cash", text="Efectivo"),
                ft.DropdownOption(key="savings", text="Ahorro"),
            ],
            filled=True,
            fill_color=theme.CARD_WARM,
            border=ft.InputBorder.NONE,
            border_radius=14,
            content_padding=ft.Padding.symmetric(horizontal=14, vertical=8),
            expand=True,
        )
        swatches = ft.Row(
            [
                ft.Container(
                    width=28,
                    height=28,
                    border_radius=14,
                    bgcolor=color,
                    border=ft.Border.all(3, theme.INK if self.color == color else theme.WHITE),
                    on_click=lambda e, c=color: self._select_color(c),
                    ink=True,
                )
                for color in ["#0F6B54", "#146EF5", "#D9883A", "#8B5CF6", "#D95D70", "#2F8F9D"]
            ],
            spacing=8,
        )
        self.swatches_row = swatches
        form = ft.Column(
            [
                ft.Row(
                    [
                        text("Nueva cuenta", size=23, display=True, expand=True),
                        ft.Container(
                            content=ft.Icon(ft.Icons.CLOSE_ROUNDED, size=20, color=theme.INK),
                            width=36,
                            height=36,
                            border_radius=18,
                            bgcolor=theme.CARD_WARM,
                            alignment=ft.Alignment.CENTER,
                            on_click=lambda e: _close(self.app),
                            ink=True,
                        ),
                    ]
                ),
                ft.Container(height=12),
                full_width(self.name_field),
                ft.Container(height=8),
                full_width(self.institution_field),
                ft.Container(height=8),
                ft.Row([self.kind_dropdown], spacing=0),
                ft.Container(height=8),
                full_width(self.balance_field),
                ft.Container(height=12),
                text("Color", size=11, color=theme.MUTED, weight=ft.FontWeight.W_700),
                ft.Container(height=6),
                swatches,
                ft.Container(height=16),
                ft.Row([primary_button("Crear cuenta", self._save, icon=ft.Icons.CHECK_ROUNDED, expand=True)]),
                ft.Container(height=10),
            ],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        sheet = ft.BottomSheet(
            content=ft.Container(
                content=form,
                padding=ft.Padding.only(left=20, right=20, top=8, bottom=12),
                height=_sheet_height(self.app) - 100,
            ),
            bgcolor=theme.CARD,
            show_drag_handle=True,
            use_safe_area=True,
            draggable=True,
        )
        self.app.page.show_dialog(sheet)

    def _select_color(self, color: str) -> None:
        self.color = color
        if hasattr(self, "swatches_row"):
            for swatch in self.swatches_row.controls:
                try:
                    swatch.border = ft.Border.all(3, theme.INK if swatch.bgcolor == color else theme.WHITE)
                except Exception:
                    pass
            try:
                self.swatches_row.update()
            except Exception:
                pass

    def _save(self, event=None) -> None:
        name = (self.name_field.value or "").strip() if self.name_field else ""
        if not name:
            self.app.show_snack("Ponle un nombre a la cuenta", error=True)
            return
        kind = self.kind_dropdown.value if self.kind_dropdown else "debit"
        try:
            raw = (self.balance_field.value or "").strip() if self.balance_field else "0"
            initial = 0 if raw in {"", "0", "0.00"} else parse_amount_to_cents(raw)
        except MoneyError as exc:
            self.app.show_snack(str(exc), error=True)
            return
        try:
            self.app.ledger.create_account(
                name,
                institution=(self.institution_field.value or "").strip() if self.institution_field else "",
                kind=kind or "debit",
                initial_balance_cents=initial,
                color=self.color,
                icon=ACCOUNT_ICONS.get(kind or "debit", "ACCOUNT_BALANCE_WALLET_ROUNDED"),
            )
        except Exception as exc:
            self.app.show_snack(str(exc), error=True)
            return
        _close(self.app)
        self.app.after_change("Cuenta creada")


class AccountDetailSheet:
    def __init__(self, app, account: Account):
        self.app = app
        self.account = account

    def open(self) -> None:
        account = self.account
        balance = self.app.ledger.account_balance(account)
        views = self.app.ledger.transaction_views(account_id=account.id, limit=5)
        provider = {
            "demo": "Cuenta demo con feed en vivo",
            "manual": "Registro manual",
            "cash": "Efectivo",
            "plaid": "Vinculada con Plaid",
            "webhook": "Conectada por webhook",
        }.get(account.provider, account.provider)

        actions = [
            secondary_button(
                "Agregar gasto",
                lambda e: self._add_expense(),
                icon=ft.Icons.ADD_ROUNDED,
                expand=True,
                height=42,
            ),
        ]
        if account.is_demo:
            actions.append(
                secondary_button(
                    "Simular",
                    lambda e: self._simulate(),
                    icon=ft.Icons.BOLT_ROUNDED,
                    expand=True,
                    height=42,
                )
            )
        elif account.is_linked:
            actions.append(
                secondary_button(
                    "Sincronizar",
                    lambda e: self._sync(),
                    icon=ft.Icons.SYNC_ROUNDED,
                    expand=True,
                    height=42,
                )
            )
        tx_list: list[ft.Control] = []
        if views:
            tx_list = [
                tx_tile(
                    v,
                    self.app.symbol,
                    on_click=lambda e, vv=v: self._edit(vv),
                    show_account=False,
                    dense=True,
                )
                for v in views
            ]
        else:
            tx_list = [text("Sin movimientos en esta cuenta.", size=11.5, color=theme.MUTED)]

        archive_button = ft.Container()
        if not account.is_demo:
            archive_button = ft.Container(
                content=text_button("Archivar cuenta", self._confirm_archive, color=theme.MUTED),
                alignment=ft.Alignment.CENTER,
                margin=ft.Margin.only(top=4),
            )

        content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                text(account.name, size=23, display=True),
                                text(provider, size=10.5, color=theme.MUTED),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Icon(ft.Icons.CLOSE_ROUNDED, size=20, color=theme.INK),
                            width=36,
                            height=36,
                            border_radius=18,
                            bgcolor=theme.CARD_WARM,
                            alignment=ft.Alignment.CENTER,
                            on_click=lambda e: _close(self.app),
                            ink=True,
                        ),
                    ]
                ),
                ft.Container(height=12),
                account_card(account, balance, self.app.symbol),
                ft.Container(height=12),
                ft.Row(actions, spacing=8),
                ft.Container(height=16),
                section_header("Últimos movimientos", f"{len(views)} recientes"),
                ft.Container(height=6),
                ft.Container(
                    content=ft.Column(tx_list, spacing=0),
                    bgcolor=theme.CARD_WARM,
                    border_radius=18,
                    padding=6,
                ),
                archive_button,
                ft.Container(height=10),
            ],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        sheet = ft.BottomSheet(
            content=ft.Container(
                content=content,
                padding=ft.Padding.only(left=20, right=20, top=8, bottom=12),
                height=_sheet_height(self.app) - 60,
            ),
            bgcolor=theme.CARD,
            show_drag_handle=True,
            use_safe_area=True,
            draggable=True,
        )
        self.app.page.show_dialog(sheet)

    def _add_expense(self) -> None:
        _close(self.app)
        self.app.open_add(default_account_id=self.account.id)

    def _simulate(self) -> None:
        _close(self.app)
        self.app.simulate_expense(self.account.id)

    def _sync(self) -> None:
        _close(self.app)
        self.app.sync_now_async()

    def _edit(self, view: TransactionView) -> None:
        _close(self.app)
        self.app.open_edit(view)

    def _confirm_archive(self, event=None) -> None:
        dialog = ft.AlertDialog(
            modal=True,
            title=text("¿Archivar cuenta?", size=18, display=True),
            content=text("Los movimientos se conservan, pero la cuenta dejará de aparecer.", size=12, color=theme.MUTED),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.app.page.pop_dialog()),
                ft.FilledButton(
                    "Archivar",
                    on_click=lambda e: self._archive(),
                    style=ft.ButtonStyle(bgcolor=theme.CORAL, color=theme.WHITE),
                ),
            ],
        )
        self.app.page.show_dialog(dialog)

    def _archive(self) -> None:
        self.app.ledger.archive_account(self.account.id)
        self.app.page.pop_dialog()
        _close(self.app)
        self.app.after_change("Cuenta archivada")


class ConnectBankSheet:
    def __init__(self, app):
        self.app = app

    def open(self) -> None:
        configured = bool(self.app.settings.get("api_url") and self.app.settings.get("api_token"))
        server_url = self.app.settings.get("api_url", "")
        endpoint = f"{server_url}/v1/webhooks/bank" if server_url else "Configura tu servidor para ver el endpoint"

        demo = soft_card(
            ft.Column(
                [
                    ft.Row(
                        [
                            icon_bubble(ft.Icons.AUTO_AWESOME_ROUNDED, theme.GOLD),
                            ft.Column(
                                [
                                    text("Cuenta demo", size=13, weight=ft.FontWeight.W_700),
                                    text("Prueba compras en tiempo real sin conectar un banco.", size=10.5, color=theme.MUTED),
                                ],
                                spacing=1,
                                expand=True,
                            ),
                        ],
                        spacing=10,
                    ),
                    ft.Container(height=8),
                    secondary_button(
                        "Simular una compra ahora",
                        lambda e: self._demo(),
                        icon=ft.Icons.BOLT_ROUNDED,
                        expand=True,
                        height=40,
                    ),
                ],
                spacing=0,
            ),
            padding=14,
        )

        plaid = soft_card(
            ft.Column(
                [
                    ft.Row(
                        [
                            icon_bubble(ft.Icons.LINK_ROUNDED, theme.BLUE),
                            ft.Column(
                                [
                                    text("Plaid", size=13, weight=ft.FontWeight.W_700),
                                    text("Bancos de EE. UU., Canadá y Europa.", size=10.5, color=theme.MUTED),
                                ],
                                spacing=1,
                                expand=True,
                            ),
                            pill("HTTPS", color=theme.GREEN, bgcolor=theme.MINT_SOFT, size=8.5),
                        ],
                        spacing=10,
                    ),
                    ft.Container(height=8),
                    text(
                        "Abre el portal seguro del servidor Sapardobank, elige tu banco y autoriza la conexión. Los movimientos nuevos llegan por webhook y SSE.",
                        size=10.5,
                        color=theme.MUTED,
                    ),
                    ft.Container(height=8),
                    primary_button(
                        "Abrir vinculación" if configured else "Configurar servidor",
                        lambda e: self._plaid() if configured else self._go_settings(),
                        icon=ft.Icons.OPEN_IN_NEW_ROUNDED if configured else ft.Icons.SETTINGS_ROUNDED,
                        expand=True,
                        height=42,
                    ),
                ],
                spacing=0,
            ),
            padding=14,
        )

        webhook = soft_card(
            ft.Column(
                [
                    ft.Row(
                        [
                            icon_bubble(ft.Icons.WEBHOOK_ROUNDED, theme.GREEN),
                            ft.Column(
                                [
                                    text("Webhook / banco directo", size=13, weight=ft.FontWeight.W_700),
                                    text("Para Belvo, tu banco o una integración propia.", size=10.5, color=theme.MUTED),
                                ],
                                spacing=1,
                                expand=True,
                            ),
                        ],
                        spacing=10,
                    ),
                    ft.Container(height=8),
                    text(endpoint, size=9.5, color=theme.INK, selectable=True),
                    ft.Container(height=6),
                    text(
                        "Firma cada payload con HMAC-SHA256 y el secreto del servidor. El firewall bloquea cualquier destino que no esté en la lista permitida.",
                        size=9.5,
                        color=theme.MUTED,
                    ),
                    ft.Container(height=8),
                    secondary_button(
                        "Copiar endpoint",
                        lambda e: self.app.copy_text(endpoint),
                        icon=ft.Icons.CONTENT_COPY_ROUNDED,
                        expand=True,
                        height=40,
                    ),
                ],
                spacing=0,
            ),
            padding=14,
        )

        manual = soft_card(
            ft.Row(
                [
                    icon_bubble(ft.Icons.EDIT_NOTE_ROUNDED, theme.GREEN),
                    ft.Column(
                        [
                            text("Agregar cuenta manual", size=13, weight=ft.FontWeight.W_700),
                            text("Efectivo, tarjeta o una cuenta que registras a mano.", size=10.5, color=theme.MUTED),
                        ],
                        spacing=1,
                        expand=True,
                    ),
                    icon_button(ft.Icons.ADD_ROUNDED, lambda e: self._manual(), bgcolor=theme.MINT_SOFT, color=theme.GREEN, size=34),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=14,
        )

        content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                text("Vincular banco", size=23, display=True),
                                text("Elige cómo quieres recibir los movimientos.", size=10.5, color=theme.MUTED),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Icon(ft.Icons.CLOSE_ROUNDED, size=20, color=theme.INK),
                            width=36,
                            height=36,
                            border_radius=18,
                            bgcolor=theme.CARD_WARM,
                            alignment=ft.Alignment.CENTER,
                            on_click=lambda e: _close(self.app),
                            ink=True,
                        ),
                    ]
                ),
                ft.Container(height=12),
                demo,
                ft.Container(height=10),
                plaid,
                ft.Container(height=10),
                webhook,
                ft.Container(height=10),
                manual,
                ft.Container(height=10),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.SHIELD_OUTLINED, size=16, color=theme.GREEN),
                            text("Nunca guardamos tus credenciales bancarias en el teléfono.", size=9.5, color=theme.MUTED),
                        ],
                        spacing=6,
                    ),
                    bgcolor=theme.MINT_SOFT,
                    border_radius=14,
                    padding=10,
                ),
                ft.Container(height=8),
            ],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        sheet = ft.BottomSheet(
            content=ft.Container(
                content=content,
                padding=ft.Padding.only(left=20, right=20, top=8, bottom=12),
                height=_sheet_height(self.app) - 30,
            ),
            bgcolor=theme.CARD,
            show_drag_handle=True,
            use_safe_area=True,
            draggable=True,
        )
        self.app.page.show_dialog(sheet)

    def _demo(self) -> None:
        _close(self.app)
        self.app.simulate_expense()

    def _plaid(self) -> None:
        _close(self.app)
        self.app.open_bank_link()

    def _go_settings(self) -> None:
        _close(self.app)
        self.app.select_tab(4)

    def _manual(self) -> None:
        _close(self.app)
        self.app.open_account_form()


class HomeConnectSheet:
    """Busca el servidor Sapardobank en la Wi-Fi de casa y lo deja configurado."""

    def __init__(self, app):
        self.app = app
        self.url = ""
        self.server_list = ft.Column(spacing=6)
        self.status = text("Buscando el servidor en tu Wi-Fi…", size=10.5, color=theme.MUTED)
        self.progress = ft.ProgressBar(
            value=None,
            color=theme.GREEN,
            bgcolor=theme.MINT_SOFT,
            bar_height=4,
            border_radius=4,
        )
        self.url_field = input_field(
            "Se llena al buscar el servidor",
            value="",
            prefix_icon=ft.Icons.LAN_ROUNDED,
            keyboard_type=ft.KeyboardType.URL,
        )
        self.token_field = input_field(
            "Token de server_data/token.txt",
            value=self.app.settings.get("api_token", ""),
            prefix_icon=ft.Icons.KEY_ROUNDED,
            password=True,
        )
        self.connect_button: ft.Control | None = None

    def open(self) -> None:
        form = ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                text("Conectar a mi casa", size=23, display=True),
                                text("Mismo Wi-Fi, sin escribir la IP.", size=10.5, color=theme.MUTED),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Icon(ft.Icons.CLOSE_ROUNDED, size=20, color=theme.INK),
                            width=36,
                            height=36,
                            border_radius=18,
                            bgcolor=theme.CARD_WARM,
                            alignment=ft.Alignment.CENTER,
                            on_click=lambda e: _close(self.app),
                            ink=True,
                        ),
                    ]
                ),
                ft.Container(height=12),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.WIFI_ROUNDED, size=20, color=theme.GREEN),
                            ft.Column(
                                [
                                    text("Enciende el servidor en tu computadora", size=11.5, weight=ft.FontWeight.W_700),
                                    text(
                                        "Ejecuta run_server.bat, deja la PC y el teléfono en el mismo Wi-Fi y permite el puerto 8787 en el firewall de Windows.",
                                        size=9.5,
                                        color=theme.MUTED,
                                    ),
                                ],
                                spacing=1,
                                expand=True,
                            ),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    bgcolor=theme.MINT_SOFT,
                    border_radius=14,
                    padding=12,
                ),
                ft.Container(height=12),
                ft.Row(
                    [
                        primary_button("Buscar en mi Wi-Fi", self._search_click, icon=ft.Icons.WIFI_FIND_ROUNDED, expand=True, height=44),
                    ]
                ),
                ft.Container(height=8),
                self.progress,
                ft.Container(height=4),
                self.status,
                ft.Container(height=6),
                self.server_list,
                ft.Container(height=8),
                self.url_field,
                ft.Container(height=8),
                self.token_field,
                ft.Container(height=6),
                text(
                    "El token está en server_data/token.txt de la computadora. No lo compartas.",
                    size=9.5,
                    color=theme.MUTED,
                ),
                ft.Container(height=14),
                ft.Row(
                    [
                        primary_button("Conectar", self._connect_click, icon=ft.Icons.LINK_ROUNDED, expand=True, height=48),
                    ]
                ),
                ft.Container(height=10),
            ],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        sheet = ft.BottomSheet(
            content=ft.Container(
                content=form,
                padding=ft.Padding.only(left=20, right=20, top=8, bottom=12),
                height=_sheet_height(self.app),
            ),
            bgcolor=theme.CARD,
            show_drag_handle=True,
            draggable=True,
            use_safe_area=True,
        )
        self.app.page.show_dialog(sheet)
        self.app.page.run_task(self._search)

    def _search_click(self, event=None) -> None:
        self.app.page.run_task(self._search)

    async def _search(self) -> None:
        self.progress.visible = True
        self.status.value = "Buscando el servidor en tu Wi-Fi…"
        self.server_list.controls = []
        self.app.page.update()
        try:
            servers = await discover_local_servers()
        except Exception as exc:
            self.progress.visible = False
            self.status.value = str(exc)
            self.status.color = theme.CORAL
            self.app.page.update()
            return
        self.progress.visible = False
        if not servers:
            self.status.value = (
                "No encontré el servidor. Verifica que run_server.bat esté abierto y que el firewall permita el puerto 8787."
            )
            self.status.color = theme.CORAL
            self.app.page.update()
            return
        self.status.value = f"Encontré {len(servers)} servidor{'es' if len(servers) != 1 else ''}. Elige uno:"
        self.status.color = theme.GREEN
        self.server_list.controls = [self._server_card(item) for item in servers]
        self.url = servers[0]["url"]
        self.url_field.value = self.url
        self.app.page.update()

    def _server_card(self, item: dict) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.DNS_ROUNDED, size=18, color=theme.GREEN),
                    ft.Column(
                        [
                            text(item.get("name") or "Sapardobank Server", size=11.5, weight=ft.FontWeight.W_700),
                            text(item["url"], size=10, color=theme.MUTED),
                        ],
                        spacing=0,
                        expand=True,
                    ),
                    text(item.get("version") or "", size=9.5, color=theme.MUTED),
                ],
                spacing=9,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=10,
            border_radius=12,
            border=ft.Border.all(1, theme.LINE),
            bgcolor=theme.CARD_WARM,
            on_click=lambda e, value=item["url"]: self._select_server(value),
            ink=True,
        )

    def _select_server(self, url: str) -> None:
        self.url = url
        self.url_field.value = url
        self.app.page.update()

    def _connect_click(self, event=None) -> None:
        self.app.page.run_task(self._connect)

    async def _connect(self) -> None:
        raw_url = (self.url_field.value or self.url or "").strip()
        token = (self.token_field.value or "").strip()
        if not raw_url:
            self.status.value = "Primero busca el servidor o escribe su URL."
            self.status.color = theme.CORAL
            self.app.page.update()
            return
        try:
            url = validate_server_url(raw_url)
            if not token:
                raise RemoteError("Pega el token de server_data/token.txt")
        except RemoteError as exc:
            self.status.value = str(exc)
            self.status.color = theme.CORAL
            self.app.page.update()
            return
        self.status.value = "Probando conexión…"
        self.status.color = theme.MUTED
        self.app.page.update()
        try:
            client = RemoteClient(url, token)
            info = await asyncio.to_thread(client.health)
        except Exception as exc:
            self.status.value = str(exc)
            self.status.color = theme.CORAL
            self.app.page.update()
            return
        self.app.settings.set("api_url", url)
        self.app.settings.set("api_token", token)
        self.app.settings.set("internet_enabled", True)
        self.app.settings.set("network_permission_granted", True)
        _close(self.app)
        self.app.refresh()
        self.app.show_snack(f"Conectado a {info.get('app', 'tu casa')} · sincronizando")
        self.app.page.run_task(self.app._kick_sync)
        self.app.page.run_task(self.app._check_updates_once)


class TutorialSheet:
    """Tutorial corto de conexión: internet, banco y primer movimiento."""

    STEPS = [
        {
            "icon": ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED,
            "color": theme.GREEN,
            "title": "Tu dinero, en orden",
            "body": "Sapardobank guarda tus gastos en este teléfono. Para recibir movimientos de tu banco en tiempo real, conecta internet y vincula una cuenta.",
            "detail": "¿Sin banco? Prueba el modo demo desde Cuentas. No necesitas servidor para empezar.",
        },
        {
            "icon": ft.Icons.WIFI_ROUNDED,
            "color": theme.BLUE,
            "title": "Conecta tu internet",
            "body": "Ve a Ajustes → Conexión → Conectar a mi casa. Acepta el permiso de red; Sapardobank buscará el servidor en tu Wi-Fi y te pedirá el token de server_data/token.txt.",
            "detail": "En tu Wi-Fi se permite HTTP local; fuera de casa usa siempre HTTPS. El firewall sigue bloqueando destinos no permitidos en el servidor.",
        },
        {
            "icon": ft.Icons.LINK_ROUNDED,
            "color": theme.GOLD,
            "title": "Vincula tu banco",
            "body": "En Cuentas → Vincular un banco elige Plaid (EE. UU., Canadá y Europa) o webhook/Belvo. Autoriza en el navegador y vuelve a Sapardobank.",
            "detail": "Las compras llegan por SSE y se guardan con su identificador para no duplicarse. También puedes simular una compra.",
        },
        {
            "icon": ft.Icons.CHECK_CIRCLE_ROUNDED,
            "color": theme.GREEN,
            "title": "Todo listo",
            "body": "Sincroniza desde Inicio o Cuentas. Tus gastos aparecerán en la libreta y en el widget de la pantalla de inicio.",
            "detail": "Tu token y tus datos no se comparten con tus compañeros: cada instalación es independiente.",
        },
    ]

    def __init__(self, app):
        self.app = app
        self.step = 0
        self.host: ft.Container | None = None
        self.dialog: ft.AlertDialog | None = None

    def open(self) -> None:
        width = max(310, min(420, int((self.app.page.width or 430) - 28)))
        height = max(540, min(650, int((self.app.page.height or 820) - 120)))
        self.host = ft.Container(
            width=width,
            height=height,
            padding=ft.Padding.only(left=22, right=22, top=16, bottom=16),
            content=self._content(),
        )
        self.dialog = ft.AlertDialog(
            modal=True,
            content=self.host,
            content_padding=0,
            inset_padding=ft.Padding.all(12),
            bgcolor=theme.CARD,
            shape=ft.RoundedRectangleBorder(radius=26),
        )
        self.app.page.show_dialog(self.dialog)

    def _content(self) -> ft.Control:
        step = self.STEPS[self.step]
        total = len(self.STEPS)
        last = self.step == total - 1
        back_enabled = self.step > 0

        dots = [
            ft.Container(
                width=20 if i == self.step else 7,
                height=7,
                border_radius=4,
                bgcolor=theme.GREEN if i == self.step else theme.LINE,
            )
            for i in range(total)
        ]
        header = ft.Row(
            [
                text("SAPARDOBANK", size=9.5, color=theme.GREEN, weight=ft.FontWeight.W_700),
                ft.Container(expand=True),
                text_button("Saltar", self._finish, color=theme.MUTED),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        back = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.ARROW_BACK_ROUNDED, size=17, color=theme.INK if back_enabled else theme.MUTED),
                    text("Atrás", size=13, color=theme.INK if back_enabled else theme.MUTED, weight=ft.FontWeight.W_700),
                ],
                spacing=5,
                alignment=ft.MainAxisAlignment.CENTER,
                tight=True,
            ),
            height=48,
            border_radius=14,
            border=ft.Border.all(1, theme.LINE),
            bgcolor=theme.CARD,
            alignment=ft.Alignment.CENTER,
            opacity=1 if back_enabled else 0.45,
            on_click=self._back if back_enabled else None,
            ink=back_enabled,
            expand=True,
        )
        next_button = primary_button(
            "Empezar" if last else "Siguiente",
            self._next,
            icon=ft.Icons.CHECK_ROUNDED if last else ft.Icons.ARROW_FORWARD_ROUNDED,
            expand=True,
            height=48,
        )
        return ft.Column(
            [
                header,
                ft.Container(height=10),
                ft.Row(
                    [
                        ft.Row(dots, spacing=5),
                        text(f"{self.step + 1} de {total}", size=10, color=theme.MUTED),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(expand=True),
                icon_bubble(step["icon"], step["color"], size=68, icon_size=30, bgcolor=alpha(step["color"], 0.12)),
                ft.Container(height=14),
                text(step["title"], size=28, display=True, align=ft.TextAlign.CENTER),
                ft.Container(height=6),
                text(step["body"], size=12.5, color=theme.MUTED, align=ft.TextAlign.CENTER),
                ft.Container(height=14),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.LIGHTBULB_OUTLINE_ROUNDED, size=17, color=step["color"]),
                            text(step["detail"], size=10.5, color=theme.MUTED, expand=True),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    bgcolor=theme.MINT_SOFT,
                    border_radius=14,
                    padding=12,
                ),
                ft.Container(expand=True),
                ft.Row([back, next_button], spacing=8),
                ft.Container(height=4),
            ],
            spacing=0,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _render(self) -> None:
        if not self.host:
            return
        self.host.content = self._content()
        try:
            self.host.update()
        except Exception:
            pass

    def _back(self, event=None) -> None:
        if self.step > 0:
            self.step -= 1
            self._render()

    def _next(self, event=None) -> None:
        if self.step < len(self.STEPS) - 1:
            self.step += 1
            self._render()
        else:
            self._finish()

    def _finish(self, event=None) -> None:
        self.app.settings.set("tutorial_seen", True)
        try:
            self.app.page.pop_dialog()
        except Exception:
            pass
        self.app.show_snack("Tutorial completado · puedes repetirlo en Ajustes → Conexión")
        try:
            self.app.page.run_task(self.app._check_updates_once)
        except Exception:
            pass


class WidgetSheet:
    def __init__(self, app):
        self.app = app
        self.variant = app.settings.get("widget_variant", "wide")
        self.theme = app.settings.get("widget_theme", "forest")
        self.hidden = app.settings.get_bool("widget_privacy", False)
        self.preview_host: ft.Container | None = None
        self.updated_text: ft.Text | None = None
        self.theme_row: ft.Row | None = None

    def open(self) -> None:
        try:
            render = self.app.widget_service.render(self.variant, self.theme, self.hidden)
            image_bytes = render.image_bytes
        except Exception:
            image_bytes = None
        self.preview_host = ft.Container(
            content=ft.Image(src=image_bytes or b"", fit=ft.BoxFit.CONTAIN, border_radius=18) if image_bytes else ft.Container(),
            height=200 if self.variant == "wide" else (260 if self.variant == "square" else 190),
            alignment=ft.Alignment.CENTER,
        )
        self.updated_text = text(
            f"Actualizado {datetime.now().strftime('%H:%M')}",
            size=9.5,
            color=alpha(theme.WHITE, 0.62),
        )
        wallpaper = ft.Container(
            height=300,
            border_radius=24,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=["#D9D1C2", "#BFB4A1"],
            ),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            content=ft.Stack(
                [
                    ft.Container(width=80, height=80, border_radius=18, bgcolor=alpha(theme.WHITE, 0.20), right=26, top=28),
                    ft.Container(width=80, height=80, border_radius=18, bgcolor=alpha(theme.WHITE, 0.13), right=120, top=28),
                    ft.Container(
                        content=ft.Column(
                            [
                                self.preview_host,
                                ft.Container(height=5),
                                self.updated_text,
                            ],
                            spacing=0,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=ft.Padding.only(left=28, right=28, top=54),
                        expand=True,
                    ),
                ],
                expand=True,
            ),
        )
        theme_swatches = ft.Row(
            [
                self._theme_dot("forest", "#0C3E30"),
                self._theme_dot("paper", "#EFE6D4"),
                self._theme_dot("night", "#111A17"),
            ],
            spacing=9,
        )
        self.theme_row = theme_swatches
        variant_control = ft.SegmentedButton(
            segments=[
                ft.Segment(value="wide", label="Ancho"),
                ft.Segment(value="square", label="Cuadrado"),
                ft.Segment(value="compact", label="Compacto"),
            ],
            selected=[self.variant],
            on_change=self._variant_changed,
            style=ft.ButtonStyle(
                color={ft.ControlState.SELECTED: theme.WHITE, ft.ControlState.DEFAULT: theme.INK},
                bgcolor={ft.ControlState.SELECTED: theme.GREEN, ft.ControlState.DEFAULT: theme.CARD_WARM},
                shape=ft.RoundedRectangleBorder(radius=11),
                padding=ft.Padding.symmetric(horizontal=8, vertical=7),
            ),
        )

        form = ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                text("Widget de inicio", size=23, display=True),
                                text("Tus gastos, sin abrir la app.", size=10.5, color=theme.MUTED),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Icon(ft.Icons.CLOSE_ROUNDED, size=20, color=theme.INK),
                            width=36,
                            height=36,
                            border_radius=18,
                            bgcolor=theme.CARD_WARM,
                            alignment=ft.Alignment.CENTER,
                            on_click=lambda e: _close(self.app),
                            ink=True,
                        ),
                    ]
                ),
                ft.Container(height=12),
                wallpaper,
                ft.Container(height=14),
                text("Formato", size=11, color=theme.MUTED, weight=ft.FontWeight.W_700),
                ft.Container(height=6),
                variant_control,
                ft.Container(height=10),
                ft.Row(
                    [
                        text("Tema", size=11, color=theme.MUTED, weight=ft.FontWeight.W_700, expand=True),
                        theme_swatches,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=10),
                ft.Row(
                    [
                        ft.Column(
                            [
                                text("Ocultar montos", size=12, weight=ft.FontWeight.W_700),
                                text("Ideal si compartes tu pantalla.", size=9.5, color=theme.MUTED),
                            ],
                            spacing=0,
                            expand=True,
                        ),
                        ft.Switch(value=self.hidden, active_color=theme.GREEN, on_change=self._privacy_changed),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=12),
                ft.Row(
                    [
                        secondary_button(
                            "Guardar imagen",
                            lambda e: self.app.export_widget_image(self.app.widget_service.render(self.variant, self.theme, self.hidden)),
                            icon=ft.Icons.DOWNLOAD_ROUNDED,
                            expand=True,
                            height=44,
                        ),
                        primary_button(
                            "Publicar widget",
                            self._publish,
                            icon=ft.Icons.WIDGETS_ROUNDED,
                            expand=True,
                            height=44,
                        ),
                    ],
                    spacing=8,
                ),
                ft.Container(height=12),
                ft.Container(
                    content=ft.Column(
                        [
                            text("Cómo agregarlo", size=11, weight=ft.FontWeight.W_700),
                            text(
                                "Android: mantén presionado el inicio → Widgets → Sapardobank. "
                                "iOS: exporta la imagen y usa un widget de Fotos. "
                                "Si tu launcher no muestra el widget nativo, la imagen exportada es el respaldo.",
                                size=9.5,
                                color=theme.MUTED,
                            ),
                        ],
                        spacing=3,
                    ),
                    bgcolor=theme.CARD_WARM,
                    border_radius=14,
                    padding=12,
                ),
                ft.Container(height=10),
            ],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        sheet = ft.BottomSheet(
            content=ft.Container(
                content=form,
                padding=ft.Padding.only(left=20, right=20, top=8, bottom=12),
                height=_sheet_height(self.app),
            ),
            bgcolor=theme.CARD,
            show_drag_handle=True,
            use_safe_area=True,
            draggable=True,
        )
        self.app.page.show_dialog(sheet)

    def _theme_dot(self, name: str, color: str) -> ft.Container:
        selected = self.theme == name
        return ft.Container(
            width=32,
            height=32,
            border_radius=16,
            bgcolor=color,
            border=ft.Border.all(3, theme.GREEN if selected else theme.WHITE),
            on_click=lambda e, n=name: self._set_theme(n),
            ink=True,
            tooltip=name.capitalize(),
        )

    def _refresh_preview(self) -> None:
        render = self.app.widget_service.render(self.variant, self.theme, self.hidden)
        if self.preview_host:
            self.preview_host.content = ft.Image(src=render.image_bytes, fit=ft.BoxFit.CONTAIN, border_radius=18)
            self.preview_host.height = 200 if self.variant == "wide" else (260 if self.variant == "square" else 190)
            self.preview_host.update()
        if self.updated_text:
            self.updated_text.value = f"Actualizado {datetime.now().strftime('%H:%M')}"
            self.updated_text.update()
        self.app.page.update()

    def _variant_changed(self, event) -> None:
        selected = event.control.selected
        if selected:
            self.variant = selected[0]
            self.app.settings.set("widget_variant", self.variant)
            self._refresh_preview()

    def _set_theme(self, name: str) -> None:
        self.theme = name
        self.app.settings.set("widget_theme", name)
        if self.theme_row:
            self.theme_row.controls = [
                self._theme_dot("forest", "#0C3E30"),
                self._theme_dot("paper", "#EFE6D4"),
                self._theme_dot("night", "#111A17"),
            ]
            try:
                self.theme_row.update()
            except Exception:
                pass
        self._refresh_preview()

    def _privacy_changed(self, event) -> None:
        self.hidden = bool(event.control.value)
        self.app.settings.set("widget_privacy", self.hidden)
        self._refresh_preview()

    def _publish(self, event=None) -> None:
        render = self.app.widget_service.render(self.variant, self.theme, self.hidden)
        self.app.publish_widget(render)