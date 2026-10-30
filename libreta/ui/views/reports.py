"""Reportes: comparativas, categorías y salud del presupuesto."""

from __future__ import annotations

from datetime import date

import flet as ft

from ...core.dates import human_day, month_label
from ...core.money import format_money
from .. import theme
from ..theme import alpha, text
from ..components import (
    category_progress_row,
    empty_state,
    icon_button,
    mini_bars,
    primary_button,
    secondary_button,
    section_header,
    soft_card,
    text_button,
    tx_tile,
)



def _stat(label: str, value: str, icon, color: str | None = None) -> ft.Container:
    color = color or theme.GREEN
    return ft.Container(
        bgcolor=theme.CARD,
        border_radius=18,
        padding=14,
        expand=True,
        border=ft.Border.all(1, alpha(theme.LINE, 0.8)),
        content=ft.Column(
            [
                ft.Container(
                    width=30,
                    height=30,
                    border_radius=10,
                    bgcolor=alpha(color, 0.11),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(icon, size=16, color=color),
                ),
                text(value, size=16, weight=ft.FontWeight.W_700, max_lines=1),
                text(label, size=10, color=theme.MUTED, max_lines=2),
            ],
            spacing=4,
        ),
    )


def build_reports(app) -> ft.Control:
    report = app.dashboard.reports()
    symbol = app.symbol
    current = report.month
    previous = report.previous_month
    if previous.expenses_cents > 0:
        delta = (current.expenses_cents - previous.expenses_cents) / previous.expenses_cents
        delta_text = f"{delta * 100:+.0f}% vs mes anterior"
        delta_color = theme.CORAL if delta > 0 else theme.GREEN
    else:
        delta_text = "Primer mes con datos"
        delta_color = theme.MUTED

    header = ft.Container(
        padding=ft.Padding.only(left=20, right=20, top=20, bottom=10),
        content=ft.Row(
            [
                ft.Column(
                    [
                        text("Reportes", size=27, display=True),
                        text(month_label(), size=11.5, color=theme.MUTED),
                    ],
                    spacing=1,
                    expand=True,
                ),
                icon_button(
                    ft.Icons.IOS_SHARE_ROUNDED,
                    app.export_csv_async,
                    bgcolor=theme.CARD,
                    color=theme.GREEN,
                    size=40,
                    tooltip="Exportar CSV",
                ),
            ],
        ),
    )

    month_card = ft.Container(
        border_radius=26,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=[theme.GOLD_SOFT, theme.mix(theme.GOLD_SOFT, theme.GOLD, 0.22)],
        ),
        padding=20,
        content=ft.Column(
            [
                ft.Row(
                    [
                        text("GASTO DEL MES", size=10.5, color=theme.darken(theme.GOLD, 0.55), weight=ft.FontWeight.W_700),
                        ft.Container(
                            content=text(delta_text, size=9.5, color=delta_color, weight=ft.FontWeight.W_700),
                            bgcolor=alpha(theme.WHITE, 0.55),
                            border_radius=99,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                text(format_money(current.expenses_cents, symbol), size=38, display=True, color=theme.darken(theme.GOLD, 0.62)),
                ft.Row(
                    [
                        text(f"{report.active_days} días con actividad", size=10.5, color=theme.darken(theme.GOLD, 0.55)),
                        text(f"Promedio {format_money(report.average_day_cents, symbol)}/día", size=10.5, color=theme.darken(theme.GOLD, 0.55)),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(height=8),
                ft.ProgressBar(
                    value=min(1.0, current.expenses_cents / max(1, report.budget_daily_cents * 30)),
                    color=theme.darken(theme.GOLD, 0.35),
                    bgcolor=alpha(theme.darken(theme.GOLD, 0.35), 0.15),
                    bar_height=7,
                    border_radius=99,
                ),
                text(
                    f"Proyección del mes: {format_money(report.projected_month_cents, symbol)}",
                    size=10,
                    color=theme.darken(theme.GOLD, 0.55),
                ),
            ],
            spacing=2,
        ),
    )

    weekly_card = soft_card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                text("Últimas 8 semanas", size=14, weight=ft.FontWeight.W_700),
                                text("Compara tu ritmo", size=10.5, color=theme.MUTED),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        text(format_money(sum(v for _, v in report.weekly), symbol), size=13, weight=ft.FontWeight.W_700),
                    ]
                ),
                ft.Container(height=14),
                mini_bars(
                    [
                        type("P", (), {"day": f"{i:02d}", "expenses_cents": v})()
                        for i, (_, v) in enumerate(report.weekly)
                    ],
                    symbol=symbol,
                    labels=False,
                    highlight_last=True,
                    height=86,
                    bar_width=22,
                ),
                ft.Container(height=6),
                ft.Row(
                    [
                        text(report.weekly[0][0] if report.weekly else "", size=9, color=theme.MUTED),
                        text("Esta semana", size=9, color=theme.GREEN, weight=ft.FontWeight.W_700),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ],
            spacing=0,
        ),
        padding=18,
    )

    if report.categories:
        cat_card = soft_card(
            ft.Column(
                [
                    ft.Row(
                        [
                            text("Por categoría", size=14, weight=ft.FontWeight.W_700, expand=True),
                            text(f"{len(report.categories)} categorías", size=10.5, color=theme.MUTED),
                        ]
                    ),
                    ft.Container(height=8),
                    ft.Column(
                        [category_progress_row(c, symbol, show_count=True) for c in report.categories],
                        spacing=8,
                    ),
                ],
                spacing=0,
            ),
            padding=18,
        )
    else:
        cat_card = soft_card(empty_state(ft.Icons.PIE_CHART_ROUNDED, "Aún no hay datos", "Agrega movimientos para ver tu mezcla de categorías."))

    stats = ft.Row(
        [
            _stat("Promedio diario", format_money(report.average_day_cents, symbol), ft.Icons.CALENDAR_MONTH_ROUNDED, theme.GREEN),
            _stat("Día más activo", f"{report.active_days} días", ft.Icons.LOCAL_FIRE_DEPARTMENT_ROUNDED, theme.CORAL),
        ],
        spacing=10,
    )
    stats2 = ft.Row(
        [
            _stat("Mayor gasto", format_money(abs(report.biggest_expense.transaction.amount_cents), symbol) if report.biggest_expense else "—", ft.Icons.TRENDING_DOWN_ROUNDED, theme.CORAL),
            _stat("Presupuesto diario", format_money(report.budget_daily_cents, symbol), ft.Icons.SAVINGS_ROUNDED, theme.GOLD),
        ],
        spacing=10,
    )

    export_card = soft_card(
        ft.Row(
            [
                ft.Container(
                    width=44,
                    height=44,
                    border_radius=14,
                    bgcolor=theme.MINT_SOFT,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(ft.Icons.DOWNLOAD_ROUNDED, size=21, color=theme.GREEN),
                ),
                ft.Column(
                    [
                        text("Lleva tus datos contigo", size=13, weight=ft.FontWeight.W_700),
                        text("Exporta un CSV compatible con Excel y Sheets.", size=10.5, color=theme.MUTED),
                    ],
                    spacing=1,
                    expand=True,
                ),
                icon_button(ft.Icons.ARROW_FORWARD_ROUNDED, app.export_csv_async, bgcolor=theme.MINT_SOFT, color=theme.GREEN, size=36),
            ],
            spacing=11,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=14,
    )

    content = ft.Column(
        [
            header,
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=20),
                content=ft.Column(
                    [
                        month_card,
                        ft.Container(height=12),
                        weekly_card,
                        ft.Container(height=16),
                        section_header("Composición", "Tu mes en categorías"),
                        ft.Container(height=8),
                        cat_card,
                        ft.Container(height=16),
                        section_header("Datos que importan", "Sin ruido, solo señales"),
                        ft.Container(height=8),
                        stats,
                        ft.Container(height=8),
                        stats2,
                        ft.Container(height=12),
                        export_card,
                        ft.Container(height=10),
                        ft.Row(
                            [
                                secondary_button(
                                    "Diseñar widget de inicio",
                                    app.open_widget_sheet,
                                    icon=ft.Icons.WIDGETS_ROUNDED,
                                    expand=True,
                                )
                            ]
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