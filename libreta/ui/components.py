"""Componentes reutilizables de la interfaz móvil."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

import flet as ft

from ..core.catalog import category_icon
from ..core.dates import human_day, time_label, weekday_short
from ..core.models import Account, Category, CategoryTotal, DailyPoint, TransactionView
from ..core.money import format_money
from . import theme
from .theme import FONT_DISPLAY, FONT_UI, alpha, darken, lighten, text



def soft_card(
    content: ft.Control,
    *,
    padding: int | ft.Padding = 20,
    radius: int = 24,
    bgcolor: str | None = None,
    border: ft.Border | None = None,
    shadow: bool = True,
    on_click: Callable | None = None,
    margin: int = 0,
) -> ft.Container:
    return ft.Container(
        content=content,
        padding=padding,
        border_radius=radius,
        bgcolor=bgcolor or theme.CARD,
        border=border,
        margin=margin,
        alignment=ft.Alignment.TOP_LEFT,
        on_click=on_click,
        ink=bool(on_click),
        shadow=ft.BoxShadow(
            blur_radius=28,
            spread_radius=-8,
            color=alpha("#0B2B22", 0.10),
            offset=ft.Offset(0, 10),
        ) if shadow else None,
    )


def icon_bubble(
    icon: ft.IconData | str,
    color: str | None = None,
    *,
    size: int = 44,
    icon_size: int = 22,
    bgcolor: str | None = None,
    radius: int = 14,
) -> ft.Container:
    color = color or theme.GREEN
    return ft.Container(
        width=size,
        height=size,
        border_radius=radius,
        bgcolor=bgcolor or alpha(color, 0.12),
        alignment=ft.Alignment.CENTER,
        content=ft.Icon(icon if not isinstance(icon, str) else getattr(ft.Icons, icon, ft.Icons.CIRCLE), size=icon_size, color=color),
    )


def category_bubble(category: Category | None, size: int = 44) -> ft.Container:
    if not category:
        return icon_bubble(ft.Icons.MORE_HORIZ_ROUNDED, theme.MUTED, size=size)
    return icon_bubble(
        category_icon(category.icon),
        category.color,
        size=size,
        bgcolor=alpha(category.color, 0.13),
    )


def pill(
    label: str,
    color: str | None = None,
    bgcolor: str | None = None,
    *,
    icon: ft.IconData | None = None,
    size: float = 11,
    on_click: Callable | None = None,
) -> ft.Container:
    color = color or theme.GREEN
    controls: list[ft.Control] = []
    if icon:
        controls.append(ft.Icon(icon, size=13, color=color))
    controls.append(text(label, size=size, color=color, weight=ft.FontWeight.W_700))
    return ft.Container(
        content=ft.Row(controls, spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.Padding.symmetric(horizontal=9, vertical=5),
        border_radius=99,
        bgcolor=bgcolor or alpha(color, 0.10),
        on_click=on_click,
        ink=bool(on_click),
    )


def section_header(
    title: str,
    subtitle: str | None = None,
    action: ft.Control | None = None,
    *,
    padding: ft.Padding | int = 0,
) -> ft.Container:
    left: list[ft.Control] = [text(title, size=18, weight=ft.FontWeight.W_700)]
    if subtitle:
        left.append(text(subtitle, size=12, color=theme.MUTED))
    return ft.Container(
        padding=padding,
        content=ft.Row(
            controls=[
                ft.Column(left, spacing=2, expand=True),
                action if action else ft.Container(),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def text_button(label: str, on_click, color: str | None = None, icon: ft.IconData | None = None) -> ft.TextButton:
    color = color or theme.GREEN
    return ft.TextButton(
        content=text(label, size=12.5, color=color, weight=ft.FontWeight.W_700),
        icon=icon,
        icon_color=color,
        on_click=on_click,
        style=ft.ButtonStyle(
            padding=ft.Padding.symmetric(horizontal=8, vertical=6),
            shape=ft.RoundedRectangleBorder(radius=10),
        ),
    )


def primary_button(
    label: str,
    on_click,
    *,
    icon: ft.IconData | None = None,
    bgcolor: str | None = None,
    color: str | None = None,
    expand: bool = False,
    height: int = 50,
) -> ft.Container:
    bgcolor = bgcolor or theme.GREEN
    color = color or theme.WHITE
    content: list[ft.Control] = []
    if icon:
        content.append(ft.Icon(icon, size=19, color=color))
    content.append(text(label, size=14, color=color, weight=ft.FontWeight.W_700))
    return ft.Container(
        content=ft.Row(content, spacing=8, alignment=ft.MainAxisAlignment.CENTER, tight=True),
        height=height,
        border_radius=16,
        bgcolor=bgcolor,
        alignment=ft.Alignment.CENTER,
        on_click=on_click,
        ink=True,
        expand=expand,
    )


def secondary_button(
    label: str,
    on_click,
    *,
    icon: ft.IconData | None = None,
    expand: bool = False,
    height: int = 46,
    color: str | None = None,
) -> ft.Container:
    color = color or theme.GREEN
    content: list[ft.Control] = []
    if icon:
        content.append(ft.Icon(icon, size=18, color=color))
    content.append(text(label, size=13, color=color, weight=ft.FontWeight.W_700))
    return ft.Container(
        content=ft.Row(content, spacing=7, alignment=ft.MainAxisAlignment.CENTER, tight=True),
        height=height,
        border_radius=14,
        bgcolor=theme.CARD,
        border=ft.Border.all(1, theme.LINE),
        alignment=ft.Alignment.CENTER,
        on_click=on_click,
        ink=True,
        expand=expand,
    )


def icon_button(
    icon: ft.IconData,
    on_click,
    *,
    bgcolor: str | None = None,
    color: str | None = None,
    size: int = 40,
    tooltip: str | None = None,
) -> ft.Container:
    bgcolor = bgcolor or theme.CARD
    color = color or theme.INK
    return ft.Container(
        width=size,
        height=size,
        border_radius=size // 2,
        bgcolor=bgcolor,
        alignment=ft.Alignment.CENTER,
        on_click=on_click,
        ink=True,
        tooltip=tooltip,
        content=ft.Icon(icon, size=size * 0.5, color=color),
    )


def input_field(
    hint: str,
    *,
    value: str = "",
    prefix_icon: ft.IconData | None = None,
    keyboard_type: ft.KeyboardType = ft.KeyboardType.TEXT,
    on_change=None,
    on_submit=None,
    autofocus: bool = False,
    suffix: ft.Control | None = None,
    read_only: bool = False,
    password: bool = False,
    max_length: int | None = None,
) -> ft.TextField:
    return ft.TextField(
        value=value,
        hint_text=hint,
        hint_style=ft.TextStyle(color=theme.MUTED_LIGHT, size=14),
        text_size=14,
        color=theme.INK,
        cursor_color=theme.GREEN,
        border=ft.InputBorder.NONE,
        filled=True,
        fill_color=theme.CARD_WARM,
        content_padding=ft.Padding.symmetric(horizontal=14, vertical=14),
        border_radius=14,
        prefix_icon=prefix_icon,
        suffix=suffix,
        keyboard_type=keyboard_type,
        on_change=on_change,
        on_submit=on_submit,
        autofocus=autofocus,
        read_only=read_only,
        password=password,
        can_reveal_password=password,
        max_length=max_length,
    )


def field_shell(content: ft.Control, *, padding: int = 0, border_color: str | None = None) -> ft.Container:
    return ft.Container(
        content=content,
        border_radius=14,
        bgcolor=theme.CARD,
        border=ft.Border.all(1, border_color or theme.LINE),
        padding=padding,
    )


def full_width(control: ft.Control) -> ft.Control:
    """Hace que un campo ocupe el ancho disponible dentro de una columna."""
    try:
        control.expand = True
    except Exception:
        pass
    return ft.Row([control], spacing=0)


def tx_tile(
    view: TransactionView,
    symbol: str = "$",
    *,
    on_click: Callable | None = None,
    show_account: bool = False,
    dense: bool = False,
) -> ft.Container:
    tx = view.transaction
    category = view.category
    subtitle_parts = []
    if category:
        subtitle_parts.append(category.name)
    if show_account and view.account:
        subtitle_parts.append(view.account.name)
    subtitle_parts.append(time_label(tx.occurred_at))
    if tx.pending:
        subtitle_parts.append("Pendiente")
    amount_color = theme.GREEN if tx.amount_cents > 0 else theme.INK
    sign = "+" if tx.amount_cents > 0 else "-"
    amount = f"{sign}{format_money(abs(tx.amount_cents), symbol)}"
    return ft.Container(
        content=ft.Row(
            [
                category_bubble(category, size=40 if dense else 44),
                ft.Column(
                    [
                        text(tx.description, size=14 if dense else 14.5, weight=ft.FontWeight.W_700, max_lines=1),
                        text(" · ".join(subtitle_parts), size=11.5, color=theme.MUTED, max_lines=1),
                    ],
                    spacing=2,
                    expand=True,
                ),
                text(amount, size=13.5 if dense else 14, color=amount_color, weight=ft.FontWeight.W_700),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding.symmetric(horizontal=12, vertical=9),
        border_radius=16,
        on_click=on_click,
        ink=bool(on_click),
    )


def empty_state(
    icon: ft.IconData,
    title: str,
    message: str,
    action: ft.Control | None = None,
) -> ft.Container:
    return ft.Container(
        padding=ft.Padding.symmetric(vertical=34, horizontal=24),
        alignment=ft.Alignment.CENTER,
        content=ft.Column(
            [
                icon_bubble(icon, theme.GREEN, size=58, icon_size=27, bgcolor=theme.MINT_SOFT),
                text(title, size=17, weight=ft.FontWeight.W_700, align=ft.TextAlign.CENTER),
                text(message, size=12.5, color=theme.MUTED, align=ft.TextAlign.CENTER),
                action if action else ft.Container(),
            ],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def mini_bars(
    points: list[DailyPoint],
    *,
    symbol: str = "$",
    height: int = 96,
    labels: bool = True,
    highlight_last: bool = True,
    bar_width: int = 16,
) -> ft.Container:
    maximum = max([p.expenses_cents for p in points] + [1])
    columns: list[ft.Control] = []
    for index, point in enumerate(points):
        bar_h = max(5, int(point.expenses_cents / maximum * height))
        is_last = highlight_last and index == len(points) - 1
        color = theme.GREEN if is_last else alpha(theme.GREEN, 0.22)
        column_items: list[ft.Control] = [
            ft.Container(expand=True),
            ft.Container(
                width=bar_width,
                height=bar_h,
                bgcolor=color,
                border_radius=ft.BorderRadius.all(7),
                tooltip=f"{human_day(point.day)}: {format_money(point.expenses_cents, symbol)}",
            ),
        ]
        if labels:
            try:
                label = weekday_short(point.day)
            except ValueError:
                label = ""
            column_items.append(text(label, size=10, color=theme.MUTED, align=ft.TextAlign.CENTER))
        columns.append(
            ft.Container(
                content=ft.Column(
                    column_items,
                    spacing=6,
                    alignment=ft.MainAxisAlignment.END,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                expand=True,
                height=height + (22 if labels else 0),
            )
        )
    return ft.Container(content=ft.Row(columns, spacing=6, vertical_alignment=ft.CrossAxisAlignment.END))


def category_progress_row(
    item: CategoryTotal,
    symbol: str = "$",
    *,
    show_count: bool = False,
    dense: bool = False,
) -> ft.Container:
    category = item.category
    color = category.color if category else theme.MUTED
    name = category.name if category else "Otros"
    meta = f"{item.count} mov." if show_count else f"{int(item.share * 100)}%"
    bar = ft.ProgressBar(
        value=item.share,
        color=color,
        bgcolor=alpha(color, 0.12),
        bar_height=5,
        border_radius=9,
    )
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        category_bubble(category, size=32 if dense else 36),
                        ft.Column(
                            [
                                text(name, size=13 if dense else 13.5, weight=ft.FontWeight.W_700),
                                text(meta, size=10.5, color=theme.MUTED),
                            ],
                            spacing=0,
                            expand=True,
                        ),
                        text(format_money(item.total_cents, symbol), size=13, weight=ft.FontWeight.W_700),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bar,
            ],
            spacing=7,
        ),
        padding=ft.Padding.symmetric(vertical=4),
    )


def progress_bar(
    value: float,
    *,
    color: str | None = None,
    bgcolor: str | None = None,
    height: int = 8,
) -> ft.ProgressBar:
    return ft.ProgressBar(
        value=max(0.0, min(1.0, value)),
        color=color or theme.GOLD,
        bgcolor=bgcolor or alpha(theme.WHITE, 0.15),
        bar_height=height,
        border_radius=99,
    )


def account_card(
    account: Account,
    balance_cents: int,
    symbol: str = "$",
    *,
    on_click: Callable | None = None,
    compact: bool = False,
) -> ft.Container:
    base = account.color or theme.GREEN
    top = darken(base, 0.25)
    bottom = darken(base, 0.52)
    linked = account.provider not in {"manual", "cash"}
    badge = "DEMO" if account.is_demo else ("VINCULADA" if linked else "MANUAL")
    card = ft.Container(
        padding=18 if compact else 20,
        border_radius=24,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=[top, bottom],
        ),
        on_click=on_click,
        ink=bool(on_click),
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            width=38,
                            height=38,
                            border_radius=12,
                            bgcolor=alpha(theme.WHITE, 0.14),
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(
                                getattr(ft.Icons, account.icon, ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED),
                                color=theme.WHITE,
                                size=20,
                            ),
                        ),
                        ft.Column(
                            [
                                text(account.name, size=14, color=theme.WHITE, weight=ft.FontWeight.W_700, max_lines=1),
                                text(account.institution or "Cuenta", size=11, color=alpha(theme.WHITE, 0.64), max_lines=1),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        pill(badge, color=theme.WHITE, bgcolor=alpha(theme.WHITE, 0.16), size=9),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=10 if compact else 18),
                text("Saldo disponible", size=11, color=alpha(theme.WHITE, 0.62)),
                text(
                    format_money(balance_cents, symbol),
                    size=26 if compact else 30,
                    color=theme.WHITE,
                    display=True,
                ),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.SYNC_ROUNDED, size=13, color=alpha(theme.WHITE, 0.60)),
                            text(
                                "Sincroniza en tiempo real" if linked else "Registro manual",
                                size=10.5,
                                color=alpha(theme.WHITE, 0.60),
                            ),
                        ],
                        spacing=5,
                    ),
                    margin=ft.Margin.only(top=8),
                ) if not compact else ft.Container(),
            ],
            spacing=2,
        ),
    )
    return card


def demo_banner(on_disable: Callable | None = None, interval: int = 75) -> ft.Container:
    controls: list[ft.Control] = [
        ft.Icon(ft.Icons.AUTO_AWESOME_ROUNDED, size=18, color=theme.GOLD),
        ft.Column(
            [
                text("Modo demostración activo", size=12, weight=ft.FontWeight.W_700, color="#73551B"),
                text(f"Se genera una compra simulada cada {interval} s.", size=10.5, color="#8A6A2E"),
            ],
            spacing=1,
            expand=True,
        ),
    ]
    if on_disable:
        controls.append(
            ft.TextButton(
                "Desactivar",
                on_click=on_disable,
                style=ft.ButtonStyle(
                    color="#73551B",
                    padding=ft.Padding.symmetric(horizontal=6, vertical=4),
                ),
            )
        )
    return ft.Container(
        content=ft.Row(controls, spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=theme.GOLD_SOFT,
        border=ft.Border.all(1, alpha(theme.GOLD, 0.35)),
        border_radius=18,
        padding=ft.Padding.symmetric(horizontal=14, vertical=10),
    )


def fab_add(on_click: Callable) -> ft.Container:
    return ft.Container(
        width=56,
        height=56,
        border_radius=20,
        bgcolor=theme.GREEN,
        alignment=ft.Alignment.CENTER,
        shadow=ft.BoxShadow(blur_radius=22, color=alpha(theme.GREEN, 0.35), offset=ft.Offset(0, 8)),
        on_click=on_click,
        ink=True,
        content=ft.Icon(ft.Icons.ADD_ROUNDED, color=theme.WHITE, size=28),
    )


def badge_icon(icon: ft.IconData, color: str | None = None, bgcolor: str | None = None, size: int = 34) -> ft.Container:
    return icon_bubble(icon, color or theme.GREEN, size=size, icon_size=size * 0.48, bgcolor=bgcolor)


def divider() -> ft.Container:
    return ft.Container(height=1, bgcolor=theme.LINE, margin=ft.Margin.symmetric(vertical=4))