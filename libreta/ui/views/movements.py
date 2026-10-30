"""Lista de movimientos con búsqueda, filtros y navegación por mes."""

from __future__ import annotations

from datetime import date, datetime

import flet as ft

from ...core.dates import human_day, month_bounds, month_label
from ...core.money import format_money
from .. import theme
from ..theme import alpha, text
from ..components import (
    empty_state,
    icon_button,
    input_field,
    primary_button,
    section_header,
    soft_card,
    tx_tile,
)



def shift_month(reference: date, offset: int) -> date:
    month = reference.month + offset
    year = reference.year
    while month < 1:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    return date(year, month, 1)


class MovementsView:
    def __init__(self, app):
        self.app = app
        self.page = app.page
        self.symbol = app.symbol
        self.month_offset = app.movements_month_offset
        self.month_date = shift_month(date.today().replace(day=1), self.month_offset)
        self.kind = app.movements_kind
        self.query = ""
        self.search_field: ft.TextField | None = None
        self.filters_host: ft.Container | None = None
        self.list_host: ft.Container | None = None

    def build(self) -> ft.Control:
        start, end = month_bounds(self.month_date)
        totals = self.app.ledger.totals(start=start, end=end)
        can_go_next = self.month_offset < 0

        header = ft.Container(
            padding=ft.Padding.only(left=20, right=20, top=20, bottom=8),
            content=ft.Row(
                [
                    ft.Column(
                        [
                            text("Movimientos", size=27, display=True),
                            text("Cada peso, en su lugar.", size=11.5, color=theme.MUTED),
                        ],
                        spacing=1,
                        expand=True,
                    ),
                    icon_button(
                        ft.Icons.ADD_ROUNDED,
                        lambda e: self.app.open_add(kind="expense"),
                        bgcolor=theme.GREEN,
                        color=theme.WHITE,
                        size=42,
                        tooltip="Agregar movimiento",
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        month_card = soft_card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Icon(ft.Icons.CHEVRON_LEFT_ROUNDED, size=18, color=theme.INK),
                                width=32,
                                height=32,
                                border_radius=16,
                                bgcolor=theme.MINT_SOFT,
                                alignment=ft.Alignment.CENTER,
                                on_click=lambda e: self._change_month(-1),
                                ink=True,
                            ),
                            ft.Column(
                                [
                                    text(month_label(self.month_date), size=13.5, weight=ft.FontWeight.W_700, align=ft.TextAlign.CENTER),
                                    text(
                                        f"{totals.expense_count} gasto{'s' if totals.expense_count != 1 else ''}",
                                        size=10.5,
                                        color=theme.MUTED,
                                        align=ft.TextAlign.CENTER,
                                    ),
                                ],
                                spacing=1,
                                expand=True,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.Container(
                                content=ft.Icon(
                                    ft.Icons.CHEVRON_RIGHT_ROUNDED,
                                    size=18,
                                    color=theme.INK if can_go_next else alpha(theme.INK, 0.20),
                                ),
                                width=32,
                                height=32,
                                border_radius=16,
                                bgcolor=theme.MINT_SOFT if can_go_next else alpha(theme.LINE, 0.35),
                                alignment=ft.Alignment.CENTER,
                                on_click=(lambda e: self._change_month(1)) if can_go_next else None,
                                ink=can_go_next,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Container(height=12),
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    text("Gastos", size=10, color=theme.MUTED),
                                    text(format_money(totals.expenses_cents, self.symbol), size=18, weight=ft.FontWeight.W_700, color=theme.INK),
                                ],
                                spacing=1,
                                expand=True,
                            ),
                            ft.Container(width=1, height=34, bgcolor=theme.LINE),
                            ft.Column(
                                [
                                    text("Ingresos", size=10, color=theme.MUTED),
                                    text(format_money(totals.income_cents, self.symbol), size=18, weight=ft.FontWeight.W_700, color=theme.GREEN),
                                ],
                                spacing=1,
                                expand=True,
                                horizontal_alignment=ft.CrossAxisAlignment.END,
                            ),
                        ],
                        spacing=16,
                    ),
                ],
                spacing=0,
            ),
            padding=16,
        )

        self.search_field = input_field(
            "Buscar por descripción o comercio",
            prefix_icon=ft.Icons.SEARCH_ROUNDED,
            on_change=self._on_search,
        )
        search_container = ft.Container(
            content=self.search_field,
            border_radius=14,
            border=ft.Border.all(1, theme.LINE),
            bgcolor=theme.CARD,
        )

        self.filters_host = ft.Container(content=self._filters())

        self.list_host = ft.Container(content=self._build_list(start, end))

        return ft.Column(
            [
                header,
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=20),
                    content=ft.Column(
                        [
                            month_card,
                            ft.Container(height=12),
                            search_container,
                            ft.Container(height=10),
                            self.filters_host,
                            ft.Container(height=8),
                            self.list_host,
                            ft.Container(height=28),
                        ],
                        spacing=0,
                    ),
                ),
            ],
            spacing=0,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

    def _filters(self) -> ft.Row:
        items = [("all", "Todas"), ("expense", "Gastos"), ("income", "Ingresos")]
        controls = []
        for key, label in items:
            active = self.kind == key
            controls.append(
                ft.Container(
                    content=text(label, size=11.5, color=theme.WHITE if active else theme.INK, weight=ft.FontWeight.W_700),
                    bgcolor=theme.GREEN if active else theme.CARD,
                    border_radius=99,
                    padding=ft.Padding.symmetric(horizontal=13, vertical=7),
                    on_click=lambda e, k=key: self._set_kind(k),
                    ink=True,
                    border=ft.Border.all(1, theme.GREEN if active else theme.LINE),
                )
            )
        return ft.Row(controls, spacing=7)

    def _change_month(self, delta: int) -> None:
        self.month_offset = max(-24, min(0, self.month_offset + delta))
        self.app.movements_month_offset = self.month_offset
        self.app.refresh()

    def _set_kind(self, kind: str) -> None:
        self.kind = kind
        self.app.movements_kind = kind
        if self.filters_host:
            self.filters_host.content = self._filters()
        self._refresh_list()

    def _on_search(self, event) -> None:
        self.query = (event.control.value or "").strip()
        self._refresh_list()

    def _refresh_list(self) -> None:
        start, end = month_bounds(self.month_date)
        if self.list_host:
            self.list_host.content = self._build_list(start, end)
        self.page.update()

    def _build_list(self, start: str, end: str) -> ft.Control:
        views = self.app.ledger.transaction_views(
            start=start,
            end=end,
            kind=self.kind if self.kind != "all" else None,
            search=self.query or None,
            limit=1000,
        )
        if not views:
            return soft_card(
                empty_state(
                    ft.Icons.RECEIPT_LONG_ROUNDED,
                    "Sin movimientos",
                    "No hay nada con estos filtros. Prueba con otro mes o agrega un gasto.",
                    primary_button("Agregar gasto", lambda e: self.app.open_add(kind="expense")),
                ),
                padding=4,
                margin=ft.Margin.only(top=6),
            )

        groups: list[tuple[str, list]] = []
        current_day = None
        current: list = []
        for view in views:
            day = view.transaction.occurred_at[:10]
            if day != current_day:
                if current_day:
                    groups.append((current_day, current))
                current_day = day
                current = []
            current.append(view)
        if current_day:
            groups.append((current_day, current))

        nodes: list[ft.Control] = []
        for day, items in groups:
            day_total = sum(abs(v.transaction.amount_cents) for v in items if v.transaction.amount_cents < 0)
            nodes.append(
                ft.Container(
                    padding=ft.Padding.only(left=4, right=4, top=12, bottom=6),
                    content=ft.Row(
                        [
                            text(human_day(day), size=11.5, color=theme.MUTED, weight=ft.FontWeight.W_700),
                            text(f"-{format_money(day_total, self.symbol)}", size=10.5, color=theme.MUTED),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                )
            )
            nodes.append(
                ft.Container(
                    bgcolor=theme.CARD,
                    border_radius=22,
                    padding=7,
                    content=ft.Column(
                        [
                            tx_tile(
                                v,
                                self.symbol,
                                on_click=lambda e, vv=v: self.app.open_edit(vv),
                                show_account=True,
                                dense=True,
                            )
                            for v in items
                        ],
                        spacing=0,
                    ),
                )
            )
            nodes.append(ft.Container(height=4))
        return ft.Column(nodes, spacing=0)