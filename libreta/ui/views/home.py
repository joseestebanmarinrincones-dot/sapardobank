"""Pantalla de inicio: el día, el saldo y el pulso de los gastos."""

from __future__ import annotations

from datetime import date

import flet as ft

from ...core.dates import human_day, month_label, today_start, day_bounds
from ...core.money import format_money
from .. import theme
from ..theme import alpha, text
from ..components import (
    account_card,
    category_progress_row,
    demo_banner,
    empty_state,
    icon_button,
    mini_bars,
    primary_button,
    section_header,
    soft_card,
    text_button,
    tx_tile,
)



def _quick_action(icon, label: str, on_click, *, primary: bool = False) -> ft.Container:
    color = theme.WHITE if primary else theme.GREEN
    bg = theme.GREEN if primary else theme.CARD
    return ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    width=34,
                    height=34,
                    border_radius=12,
                    bgcolor=alpha(theme.WHITE, 0.13) if primary else theme.MINT_SOFT,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(icon, size=18, color=color),
                ),
                text(label, size=11.5, color=color, weight=ft.FontWeight.W_700, align=ft.TextAlign.CENTER),
            ],
            spacing=5,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=bg,
        border_radius=18,
        height=78,
        expand=True,
        alignment=ft.Alignment.CENTER,
        on_click=on_click,
        ink=True,
        shadow=ft.BoxShadow(
            blur_radius=20,
            spread_radius=-8,
            color=alpha("#0B2B22", 0.12),
            offset=ft.Offset(0, 8),
        ) if not primary else None,
    )


def _hero(app, data) -> ft.Container:
    symbol = app.symbol
    hidden = app.hide_balances
    balance_text = "••••••" if hidden else format_money(data.balance_cents, symbol)
    spent_text = "••••" if hidden else format_money(data.today.expenses_cents, symbol)
    remaining_text = "••••" if hidden else format_money(data.remaining_cents, symbol)
    pct = int(data.budget_used * 100)

    content = ft.Column(
        [
            ft.Row(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED, size=15, color=alpha(theme.WHITE, 0.65)),
                            text("Saldo total", size=11.5, color=alpha(theme.WHITE, 0.70)),
                        ],
                        spacing=6,
                    ),
                    ft.Container(
                        content=ft.Icon(
                            ft.Icons.VISIBILITY_OFF_ROUNDED if hidden else ft.Icons.VISIBILITY_ROUNDED,
                            size=17,
                            color=alpha(theme.WHITE, 0.70),
                        ),
                        width=30,
                        height=30,
                        border_radius=15,
                        bgcolor=alpha(theme.WHITE, 0.08),
                        alignment=ft.Alignment.CENTER,
                        on_click=app.toggle_balance_visibility,
                        ink=True,
                        tooltip="Ocultar saldos",
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            text(balance_text, size=38, color=theme.WHITE, display=True),
            ft.Container(height=8),
            ft.Row(
                [
                    ft.Column(
                        [
                            text("Gastado hoy", size=10.5, color=alpha(theme.WHITE, 0.60)),
                            text(spent_text, size=16, color=theme.WHITE, weight=ft.FontWeight.W_700),
                        ],
                        spacing=1,
                        expand=True,
                    ),
                    ft.Container(width=1, height=34, bgcolor=alpha(theme.WHITE, 0.13)),
                    ft.Column(
                        [
                            text("Te queda hoy", size=10.5, color=alpha(theme.WHITE, 0.60)),
                            text(remaining_text, size=16, color=theme.GOLD if not data.over_budget else "#FFB39E", weight=ft.FontWeight.W_700),
                        ],
                        spacing=1,
                        expand=True,
                    ),
                ],
                spacing=18,
            ),
            ft.Container(height=12),
            ft.Row(
                [
                    text("Presupuesto diario", size=10, color=alpha(theme.WHITE, 0.58)),
                    text("Excedido" if data.over_budget else f"{pct}% usado", size=10, color=alpha(theme.WHITE, 0.72), weight=ft.FontWeight.W_700),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Container(height=5),
            ft.ProgressBar(
                value=min(1.0, data.budget_used),
                color="#FFB39E" if data.over_budget else theme.GOLD,
                bgcolor=alpha(theme.WHITE, 0.13),
                bar_height=6,
                border_radius=99,
            ),
        ],
        spacing=2,
    )

    return ft.Container(
        height=252,
        border_radius=28,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=[theme.GREEN_DEEP, theme.GREEN],
        ),
        content=ft.Stack(
            [
                ft.Container(
                    width=210,
                    height=210,
                    border_radius=105,
                    bgcolor=alpha(theme.WHITE, 0.045),
                    right=-70,
                    top=-80,
                ),
                ft.Container(
                    width=130,
                    height=130,
                    border_radius=65,
                    bgcolor=alpha(theme.WHITE, 0.04),
                    left=-50,
                    bottom=-70,
                ),
                ft.Container(
                    content=ft.Column(
                        [
                            content,
                            ft.Container(expand=True),
                            ft.Row(
                                [
                                    ft.Container(
                                        content=ft.Row(
                                            [
                                                ft.Icon(ft.Icons.ADD_ROUNDED, size=15, color=theme.WHITE),
                                                text("Agregar gasto", size=11.5, color=theme.WHITE, weight=ft.FontWeight.W_700),
                                            ],
                                            spacing=4,
                                            tight=True,
                                        ),
                                        bgcolor=alpha(theme.WHITE, 0.14),
                                        border_radius=99,
                                        padding=ft.Padding.symmetric(horizontal=12, vertical=7),
                                        on_click=lambda e: app.open_add(kind="expense"),
                                        ink=True,
                                    ),
                                    text(app.connection_label, size=9.5, color=alpha(theme.WHITE, 0.50)),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                        ],
                        expand=True,
                    ),
                    padding=ft.Padding.only(left=22, right=22, top=20, bottom=16),
                    expand=True,
                ),
            ],
            expand=True,
        ),
    )


def build_home(app) -> ft.Control:
    data = app.dashboard.load()
    symbol = app.symbol
    today = app.today_transactions(limit=5)
    greeting = "Hola" + (f", {app.settings.user_name}" if app.settings.user_name else "")
    subtitle = f"{human_day(date.today())} · {month_label()}"
    savings = sum(max(0, a) for a in [data.balance_cents])

    header = ft.Container(
        padding=ft.Padding.only(left=20, right=20, top=18, bottom=12),
        content=ft.Row(
            [
                ft.Column(
                    [
                        text("SAPARDOBANK", size=10, color=theme.GREEN, weight=ft.FontWeight.W_700),
                        text(greeting, size=26, display=True),
                        text(subtitle, size=11.5, color=theme.MUTED),
                    ],
                    spacing=1,
                    expand=True,
                ),
                ft.Row(
                    [
                        icon_button(
                            ft.Icons.SYNC_ROUNDED,
                            app.sync_now_async,
                            bgcolor=theme.CARD,
                            color=theme.GREEN if app.settings.get_bool("internet_enabled", False) else theme.MUTED,
                            size=38,
                            tooltip="Sincronizar",
                        ),
                        icon_button(
                            ft.Icons.DASHBOARD_CUSTOMIZE_ROUNDED,
                            app.open_widget_sheet,
                            bgcolor=theme.CARD,
                            color=theme.INK,
                            size=38,
                            tooltip="Widget",
                        ),
                    ],
                    spacing=8,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    quick = ft.Container(
        padding=ft.Padding.symmetric(horizontal=20, vertical=12),
        content=ft.Row(
            [
                _quick_action(ft.Icons.ADD_ROUNDED, "Gasto", lambda e: app.open_add(kind="expense"), primary=True),
                _quick_action(ft.Icons.CLOUD_SYNC_ROUNDED, "Sincronizar", app.sync_now_async),
                _quick_action(ft.Icons.WIDGETS_ROUNDED, "Widget", app.open_widget_sheet),
            ],
            spacing=10,
        ),
    )

    if today:
        today_card = ft.Container(
            bgcolor=theme.CARD,
            border_radius=24,
            padding=8,
            content=ft.Column(
                [
                    tx_tile(v, symbol, on_click=lambda e, vv=v: app.open_edit(vv), show_account=True, dense=True)
                    for v in today
                ],
                spacing=0,
            ),
        )
    else:
        today_card = soft_card(
            empty_state(
                ft.Icons.SPA_ROUNDED,
                "Un día limpio",
                "Todavía no hay gastos hoy. Disfruta el silencio.",
                primary_button("Agregar el primero", lambda e: app.open_add(kind="expense"), expand=False),
            ),
            padding=4,
        )

    week_total = sum(p.expenses_cents for p in data.week)
    week_card = soft_card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                text("Últimos 7 días", size=14, weight=ft.FontWeight.W_700),
                                text("Tu ritmo de gasto", size=10.5, color=theme.MUTED),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        ft.Column(
                            [
                                text(format_money(week_total, symbol), size=15, weight=ft.FontWeight.W_700),
                                text("en total", size=9.5, color=theme.MUTED),
                            ],
                            spacing=0,
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                        ),
                    ]
                ),
                ft.Container(height=12),
                mini_bars(data.week, symbol=symbol),
                ft.Container(height=10),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.INSIGHTS_ROUNDED, size=14, color=theme.GREEN),
                            text(
                                f"Promedio diario {format_money(week_total // 7, symbol)}"
                                + (f" · {data.top_category.category.name} es tu mayor gasto del mes" if data.top_category else ""),
                                size=10.5,
                                color=theme.MUTED,
                            ),
                        ],
                        spacing=5,
                    ),
                    padding=ft.Padding.only(top=4),
                ),
            ],
            spacing=0,
        ),
        padding=18,
    )

    cat_rows = data.categories[:4]
    if cat_rows:
        cats_card = soft_card(
            ft.Column(
                [
                    ft.Row(
                        [
                            text("En qué se fue el mes", size=14, weight=ft.FontWeight.W_700, expand=True),
                            text(format_money(sum(c.total_cents for c in cat_rows), symbol), size=12, color=theme.MUTED),
                        ]
                    ),
                    ft.Container(height=8),
                    ft.Column([category_progress_row(c, symbol) for c in cat_rows], spacing=9),
                ],
                spacing=0,
            ),
            padding=18,
        )
    else:
        cats_card = ft.Container()

    accounts_row: ft.Control
    if data.accounts:
        cards = [
            account_card(a, app.ledger.account_balance(a), symbol, compact=True, on_click=lambda e, aa=a: app.open_account_detail(aa))
            for a in data.accounts[:2]
        ]
        accounts_row = ft.Column(cards, spacing=10)
    else:
        accounts_row = ft.Container()

    content = ft.Column(
        [
            header,
            ft.Container(padding=ft.Padding.symmetric(horizontal=20), content=_hero(app, data)),
            quick,
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=20),
                content=ft.Column(
                    [
                        section_header(
                            "Hoy",
                            f"{data.today.expense_count} gasto{'s' if data.today.expense_count != 1 else ''}",
                            text_button("Ver todos", lambda e: app.select_tab(1), icon=ft.Icons.ARROW_FORWARD_ROUNDED),
                        ),
                        ft.Container(height=8),
                        today_card,
                        ft.Container(height=20),
                        section_header("Tu semana", "Un vistazo rápido"),
                        ft.Container(height=8),
                        week_card,
                        ft.Container(height=20),
                        cats_card,
                        ft.Container(height=20),
                        section_header(
                            "Cuentas",
                            "Saldos disponibles",
                            text_button("Administrar", lambda e: app.select_tab(3), icon=ft.Icons.ARROW_FORWARD_ROUNDED),
                        ),
                        ft.Container(height=8),
                        accounts_row,
                        ft.Container(height=18),
                        demo_banner(app.disable_demo, app.settings.get_int("demo_interval_seconds", 75)) if data.demo_live else ft.Container(),
                        ft.Container(height=18),
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.LOCK_OUTLINE_ROUNDED, size=13, color=theme.MUTED),
                                text("Tus datos viven primero en tu teléfono.", size=10.5, color=theme.MUTED),
                            ],
                            spacing=5,
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        ft.Container(height=26),
                    ],
                    spacing=0,
                ),
            ),
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
    return content