"""Cuentas, conexiones bancarias y estado de la nube."""

from __future__ import annotations

import flet as ft

from ...core.dates import time_label
from ...core.money import format_money
from .. import theme
from ..theme import alpha, text
from ..components import (
    account_card,
    empty_state,
    icon_button,
    pill,
    primary_button,
    secondary_button,
    section_header,
    soft_card,
    text_button,
)



def _status_dot(ok: bool) -> ft.Container:
    return ft.Container(
        width=7,
        height=7,
        border_radius=4,
        bgcolor=theme.GREEN if ok else theme.CORAL,
    )


def build_accounts(app) -> ft.Control:
    accounts = app.ledger.accounts()
    symbol = app.symbol
    total = app.ledger.total_balance()
    internet = app.settings.get_bool("internet_enabled", False)
    api_url = app.settings.get("api_url", "")
    last_sync = app.settings.get("last_sync_at", "")
    linked = [a for a in accounts if a.provider not in {"manual", "cash", "demo"}]
    demo = next((a for a in accounts if a.is_demo), None)

    header = ft.Container(
        padding=ft.Padding.only(left=20, right=20, top=20, bottom=10),
        content=ft.Row(
            [
                ft.Column(
                    [
                        text("Cuentas", size=27, display=True),
                        text("Tus saldos y conexiones.", size=11.5, color=theme.MUTED),
                    ],
                    spacing=1,
                    expand=True,
                ),
                icon_button(
                    ft.Icons.ADD_CARD_ROUNDED,
                    lambda e: app.open_account_form(),
                    bgcolor=theme.GREEN,
                    color=theme.WHITE,
                    size=42,
                    tooltip="Agregar cuenta",
                ),
            ],
        ),
    )

    total_card = ft.Container(
        border_radius=26,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=[theme.GREEN_DEEP, theme.darken(theme.GREEN_DEEP, 0.35)],
        ),
        padding=20,
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.ACCOUNT_BALANCE_ROUNDED, size=15, color=alpha(theme.WHITE, 0.6)),
                                text("Patrimonio disponible", size=11, color=alpha(theme.WHITE, 0.62)),
                            ],
                            spacing=6,
                        ),
                        pill(
                            f"{len(accounts)} cuentas",
                            color=theme.WHITE,
                            bgcolor=alpha(theme.WHITE, 0.10),
                            size=9.5,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                text("••••••" if app.hide_balances else format_money(total, symbol), size=36, color=theme.WHITE, display=True),
                ft.Container(height=4),
                ft.Row(
                    [
                        ft.Row(
                            [
                                _status_dot(internet),
                                text("Nube conectada" if internet else "Solo este teléfono", size=10.5, color=alpha(theme.WHITE, 0.62)),
                            ],
                            spacing=6,
                        ),
                        text(f"Actualizado {time_label(last_sync)}" if last_sync else "Sin sincronizar", size=9.5, color=alpha(theme.WHITE, 0.45)),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ],
            spacing=2,
        ),
    )

    if accounts:
        cards = [
            ft.Container(
                content=account_card(
                    a,
                    app.ledger.account_balance(a),
                    symbol,
                    on_click=lambda e, aa=a: app.open_account_detail(aa),
                ),
                margin=ft.Margin.only(bottom=10),
            )
            for a in accounts
        ]
    else:
        cards = [
            soft_card(
                empty_state(
                    ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED,
                    "Agrega tu primera cuenta",
                    "Puede ser una cuenta de banco, efectivo o una tarjeta.",
                    primary_button("Agregar cuenta", lambda e: app.open_account_form()),
                )
            )
        ]

    demo_controls = ft.Container()
    if demo:
        live = app.settings.demo_live
        demo_controls = soft_card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                width=38,
                                height=38,
                                border_radius=12,
                                bgcolor=theme.GOLD_SOFT,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Icon(ft.Icons.AUTO_AWESOME_ROUNDED, size=19, color=theme.GOLD),
                            ),
                            ft.Column(
                                [
                                    text("Feed de demostración", size=13, weight=ft.FontWeight.W_700),
                                    text(
                                        f"Activo · nueva compra cada {app.settings.get_int('demo_interval_seconds', 75)} s"
                                        if live
                                        else "Pausado · no se generan compras",
                                        size=10.5,
                                        color=theme.MUTED,
                                    ),
                                ],
                                spacing=1,
                                expand=True,
                            ),
                            ft.Switch(
                                value=live,
                                active_color=theme.GREEN,
                                on_change=lambda e: app.set_demo_live(bool(e.control.value)),
                            ),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Container(height=10),
                    ft.Row(
                        [
                            secondary_button(
                                "Simular compra",
                                lambda e: app.simulate_expense(),
                                icon=ft.Icons.BOLT_ROUNDED,
                                expand=True,
                                height=40,
                            ),
                            secondary_button(
                                "Simular ingreso",
                                lambda e: app.simulate_income(),
                                icon=ft.Icons.TRENDING_UP_ROUNDED,
                                expand=True,
                                height=40,
                            ),
                        ],
                        spacing=8,
                    ),
                ],
                spacing=0,
            ),
            padding=14,
        )

    server_card = soft_card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            width=40,
                            height=40,
                            border_radius=13,
                            bgcolor=theme.MINT_SOFT if internet else alpha(theme.LINE, 0.4),
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(ft.Icons.CLOUD_ROUNDED, size=20, color=theme.GREEN if internet else theme.MUTED),
                        ),
                        ft.Column(
                            [
                                text("Nube Sapardobank", size=13, weight=ft.FontWeight.W_700),
                                text(
                                    api_url.replace("https://", "").replace("http://", "")[:34] if api_url else "Sin servidor configurado",
                                    size=10.5,
                                    color=theme.MUTED,
                                    max_lines=1,
                                ),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        pill(
                            "ACTIVA" if internet else "APAGADA",
                            color=theme.GREEN if internet else theme.MUTED,
                            bgcolor=theme.MINT_SOFT if internet else alpha(theme.LINE, 0.4),
                            size=9,
                        ),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=10),
                ft.Row(
                    [
                        secondary_button(
                            "Configurar",
                            lambda e: app.select_tab(4),
                            icon=ft.Icons.SETTINGS_ROUNDED,
                            expand=True,
                            height=40,
                        ),
                        primary_button(
                            "Sincronizar",
                            app.sync_now_async,
                            icon=ft.Icons.SYNC_ROUNDED,
                            expand=True,
                            height=40,
                        ),
                    ],
                    spacing=8,
                ),
            ],
            spacing=0,
        ),
        padding=14,
    )

    link_card = soft_card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            width=40,
                            height=40,
                            border_radius=13,
                            bgcolor=alpha(theme.BLUE, 0.12),
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(ft.Icons.LINK_ROUNDED, size=20, color=theme.BLUE),
                        ),
                        ft.Column(
                            [
                                text("Vincular un banco", size=13, weight=ft.FontWeight.W_700),
                                text("Plaid, webhook o importación", size=10.5, color=theme.MUTED),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        pill(f"{len(linked)} vinculada{'s' if len(linked) != 1 else ''}", color=theme.BLUE, bgcolor=alpha(theme.BLUE, 0.10), size=9),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=8),
                text(
                    "Conecta una cuenta para que los movimientos lleguen solos. Las compras del banco se guardan con su identificador para no duplicarlas.",
                    size=10.5,
                    color=theme.MUTED,
                ),
                ft.Container(height=10),
                secondary_button(
                    "Ver opciones de conexión",
                    lambda e: app.open_connect_sheet(),
                    icon=ft.Icons.ADD_LINK_ROUNDED,
                    expand=True,
                    height=40,
                ),
            ],
            spacing=0,
        ),
        padding=14,
    )

    security = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.SHIELD_OUTLINED, size=17, color=theme.GREEN),
                ft.Column(
                    [
                        text("Firewall de red incluido", size=11.5, weight=ft.FontWeight.W_700),
                        text("Solo HTTPS, destinos permitidos y webhooks firmados.", size=9.5, color=theme.MUTED),
                    ],
                    spacing=0,
                    expand=True,
                ),
            ],
            spacing=9,
        ),
        bgcolor=theme.MINT_SOFT,
        border_radius=16,
        padding=12,
    )

    content = ft.Column(
        [
            header,
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=20),
                content=ft.Column(
                    [
                        total_card,
                        ft.Container(height=18),
                        section_header("Tus cuentas", f"{len(accounts)} activas"),
                        ft.Container(height=8),
                        *cards,
                        ft.Container(height=4),
                        demo_controls,
                        ft.Container(height=16),
                        section_header("Conexiones", "Datos bancarios en tiempo real"),
                        ft.Container(height=8),
                        server_card,
                        ft.Container(height=10),
                        link_card,
                        ft.Container(height=10),
                        security,
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