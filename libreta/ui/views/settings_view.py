"""Ajustes, seguridad, nube, widget y datos."""

from __future__ import annotations

import flet as ft

from ...core.money import format_money
from .. import theme
from ..theme import alpha, text
from ..components import (
    icon_button,
    input_field,
    full_width,
    pill,
    primary_button,
    secondary_button,
    section_header,
    soft_card,
    text_button,
)


CURRENCIES = [
    ("MXN", "$", "Peso mexicano · MXN"),
    ("USD", "$", "Dólar · USD"),
    ("EUR", "€", "Euro · EUR"),
    ("COP", "$", "Peso colombiano · COP"),
    ("ARS", "$", "Peso argentino · ARS"),
    ("CLP", "$", "Peso chileno · CLP"),
]


def _row_switch(label: str, subtitle: str, value: bool, on_change) -> ft.Row:
    return ft.Row(
        [
            ft.Column(
                [
                    text(label, size=13, weight=ft.FontWeight.W_700),
                    text(subtitle, size=10.5, color=theme.MUTED),
                ],
                spacing=1,
                expand=True,
            ),
            ft.Switch(value=value, active_color=theme.GREEN, on_change=on_change),
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def build_settings(app) -> ft.Control:
    settings = app.settings
    symbol = app.symbol
    budget = settings.daily_budget_cents

    name_field = input_field(
        "Tu nombre",
        value=settings.user_name,
        prefix_icon=ft.Icons.PERSON_OUTLINE_ROUNDED,
    )
    currency_field = ft.Dropdown(
        label="Moneda",
        value=settings.currency,
        options=[
            ft.DropdownOption(key=code, text=label)
            for code, sym, label in CURRENCIES
        ],
        filled=True,
        fill_color=theme.CARD_WARM,
        border=ft.InputBorder.NONE,
        border_radius=14,
        content_padding=ft.Padding.symmetric(horizontal=14, vertical=8),
        expand=True,
    )
    budget_field = input_field(
        "Presupuesto diario",
        value=f"{budget / 100:.2f}",
        prefix_icon=ft.Icons.SAVINGS_OUTLINED,
        keyboard_type=ft.KeyboardType.NUMBER,
        suffix=text(symbol, size=13, color=theme.MUTED),
    )
    profile_card = soft_card(
        ft.Column(
            [
                text("Tu libreta", size=14, weight=ft.FontWeight.W_700),
                ft.Container(height=8),
                full_width(name_field),
                ft.Container(height=8),
                ft.Row([currency_field], spacing=0),
                ft.Container(height=8),
                full_width(budget_field),
                ft.Container(height=10),
                ft.Row([primary_button("Guardar perfil", lambda e: app.save_profile_from_controls(e), expand=True, height=44)]),
            ],
            spacing=0,
        ),
        padding=16,
    )
    app.settings_form = {
        "name": name_field,
        "currency": currency_field,
        "budget": budget_field,
    }

    internet_on = settings.get_bool("internet_enabled", False)
    url_field = input_field(
        "https://tu-servidor.com",
        value=settings.get("api_url", ""),
        prefix_icon=ft.Icons.LINK_ROUNDED,
        keyboard_type=ft.KeyboardType.URL,
    )
    token_field = input_field(
        "Token de acceso",
        value=settings.get("api_token", ""),
        prefix_icon=ft.Icons.KEY_ROUNDED,
        password=True,
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
                            bgcolor=theme.MINT_SOFT if internet_on else alpha(theme.LINE, 0.4),
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(ft.Icons.CLOUD_ROUNDED, size=20, color=theme.GREEN if internet_on else theme.MUTED),
                        ),
                        ft.Column(
                            [
                                text("Acceso a internet", size=13, weight=ft.FontWeight.W_700),
                                text("Sincroniza con tu servidor Sapardobank", size=10.5, color=theme.MUTED),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        ft.Switch(value=internet_on, active_color=theme.GREEN, on_change=lambda e: app.set_internet(bool(e.control.value))),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=10),
                full_width(url_field),
                ft.Container(height=8),
                full_width(token_field),
                ft.Container(height=8),
                ft.Row(
                    [
                        secondary_button(
                            "Probar conexión",
                            lambda e: app.test_server_async(),
                            icon=ft.Icons.NETWORK_CHECK_ROUNDED,
                            expand=True,
                            height=42,
                        ),
                        primary_button(
                            "Guardar",
                            lambda e: app.save_server_async(),
                            icon=ft.Icons.SAVE_ROUNDED,
                            expand=True,
                            height=42,
                        ),
                    ],
                    spacing=8,
                ),
                ft.Container(height=10),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.SHIELD_OUTLINED, size=16, color=theme.GREEN),
                            text("Firewall: solo HTTPS, hosts permitidos y webhooks HMAC.", size=9.5, color=theme.MUTED),
                        ],
                        spacing=6,
                    ),
                    bgcolor=theme.MINT_SOFT,
                    border_radius=12,
                    padding=10,
                ),
                ft.Container(height=8),
                ft.Row(
                    [
                        text("Destinos permitidos", size=9.5, color=theme.MUTED, expand=True),
                        pill("Plaid", color=theme.BLUE, bgcolor=alpha(theme.BLUE, 0.10), size=8.5),
                    ]
                ),
            ],
            spacing=0,
        ),
        padding=16,
    )
    app.server_form = {
        "url": url_field,
        "token": token_field,
    }

    widget_card = soft_card(
        ft.Row(
            [
                ft.Container(
                    width=44,
                    height=44,
                    border_radius=14,
                    bgcolor=theme.GOLD_SOFT,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(ft.Icons.WIDGETS_ROUNDED, size=21, color="#8A6525"),
                ),
                ft.Column(
                    [
                        text("Widget de pantalla de inicio", size=13, weight=ft.FontWeight.W_700),
                        text("Elige diseño, tema y privacidad.", size=10.5, color=theme.MUTED),
                    ],
                    spacing=1,
                    expand=True,
                ),
                icon_button(ft.Icons.ARROW_FORWARD_ROUNDED, app.open_widget_sheet, bgcolor=theme.GOLD_SOFT, color="#8A6525", size=34),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=14,
    )

    current_palette = settings.get("theme_palette", "esmeralda")
    palette_cards = []
    for choice in theme.theme_choices():
        selected = choice["key"] == current_palette
        palette_cards.append(
            ft.Container(
                width=112,
                height=76,
                border_radius=16,
                padding=10,
                bgcolor=alpha(choice["brand"], 0.10) if selected else theme.CARD_WARM,
                border=ft.Border.all(2 if selected else 1, choice["brand"] if selected else theme.LINE),
                on_click=lambda e, key=choice["key"]: app.set_theme_palette(key),
                ink=True,
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Container(width=20, height=20, border_radius=10, bgcolor=choice["brand"]),
                                ft.Container(width=14, height=14, border_radius=7, bgcolor=choice["deep"]),
                                ft.Container(width=14, height=14, border_radius=7, bgcolor=choice["mint"]),
                            ],
                            spacing=5,
                        ),
                        text(
                            choice["label"],
                            size=11,
                            color=choice["brand"] if selected else theme.INK,
                            weight=ft.FontWeight.W_700 if selected else None,
                        ),
                    ],
                    spacing=6,
                ),
            )
        )
    appearance_card = soft_card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                text("Color de la app", size=13, weight=ft.FontWeight.W_700),
                                text("Cambia el acento, fondos y tarjetas al instante.", size=10.5, color=theme.MUTED),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        ft.Icon(ft.Icons.PALETTE_OUTLINED, size=20, color=theme.GREEN),
                    ]
                ),
                ft.Container(height=10),
                ft.Row(palette_cards, wrap=True, spacing=8, run_spacing=8),
            ],
            spacing=0,
        ),
        padding=14,
    )

    demo_card = soft_card(
        ft.Column(
            [
                _row_switch(
                    "Modo demostración",
                    "Genera compras simuladas para probar la app.",
                    settings.demo_live,
                    lambda e: app.set_demo_live(bool(e.control.value)),
                ),
                ft.Container(height=8),
                ft.Row(
                    [
                        text("Frecuencia del feed", size=12, color=theme.INK, expand=True),
                        ft.Dropdown(
                            value=str(settings.get_int("demo_interval_seconds", 75)),
                            options=[
                                ft.DropdownOption(key="30", text="30 segundos"),
                                ft.DropdownOption(key="75", text="75 segundos"),
                                ft.DropdownOption(key="180", text="3 minutos"),
                            ],
                            width=160,
                            filled=True,
                            fill_color=theme.CARD_WARM,
                            border=ft.InputBorder.NONE,
                            border_radius=12,
                            content_padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                            on_select=lambda e: app.set_demo_interval(int(e.control.value or 75)),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=0,
        ),
        padding=16,
    )

    data_card = soft_card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            width=36,
                            height=36,
                            border_radius=12,
                            bgcolor=theme.MINT_SOFT,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(ft.Icons.DOWNLOAD_ROUNDED, size=18, color=theme.GREEN),
                        ),
                        ft.Column(
                            [
                                text("Exportar movimientos", size=12.5, weight=ft.FontWeight.W_700),
                                text("Archivo CSV para Excel o Sheets.", size=10, color=theme.MUTED),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        text_button("Exportar", app.export_csv_async, icon=None),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=1, bgcolor=theme.LINE),
                ft.Row(
                    [
                        ft.Container(
                            width=36,
                            height=36,
                            border_radius=12,
                            bgcolor=alpha(theme.CORAL, 0.10),
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(ft.Icons.RESTART_ALT_ROUNDED, size=18, color=theme.CORAL),
                        ),
                        ft.Column(
                            [
                                text("Reiniciar demostración", size=12.5, weight=ft.FontWeight.W_700),
                                text("Vuelve a cargar los datos de ejemplo.", size=10, color=theme.MUTED),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        text_button("Reiniciar", app.reset_demo_async, color=theme.CORAL),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=1, bgcolor=theme.LINE),
                ft.Row(
                    [
                        ft.Container(
                            width=36,
                            height=36,
                            border_radius=12,
                            bgcolor=alpha(theme.CORAL, 0.10),
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(ft.Icons.DELETE_OUTLINE_ROUNDED, size=18, color=theme.CORAL),
                        ),
                        ft.Column(
                            [
                                text("Borrar todos los datos", size=12.5, weight=ft.FontWeight.W_700),
                                text("No se puede deshacer.", size=10, color=theme.MUTED),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        text_button("Borrar", app.confirm_wipe, color=theme.CORAL),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=8,
        ),
        padding=14,
    )

    about = ft.Container(
        padding=ft.Padding.only(left=4, right=4, top=8),
        content=ft.Column(
            [
                ft.Row(
                    [
                        text("Sapardobank", size=12, weight=ft.FontWeight.W_700, color=theme.GREEN),
                        text("v1.0.0", size=10, color=theme.MUTED),
                    ],
                    spacing=6,
                ),
                text(
                    "Hecha en Python con Flet. Local-first: tus movimientos se guardan en este dispositivo; "
                    "la nube es opcional y se protege con HTTPS, token y firewall de salida.",
                    size=10,
                    color=theme.MUTED,
                ),
                text("Iconos y fuentes con licencia abierta. Datos de demostración, no reales.", size=9, color=theme.MUTED_LIGHT),
            ],
            spacing=3,
        ),
    )

    content = ft.Column(
        [
            ft.Container(
                padding=ft.Padding.only(left=20, right=20, top=20, bottom=10),
                content=ft.Column(
                    [
                        text("Ajustes", size=27, display=True),
                        text("Tu dinero, tus reglas.", size=11.5, color=theme.MUTED),
                    ],
                    spacing=1,
                ),
            ),
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=20),
                content=ft.Column(
                    [
                        profile_card,
                        ft.Container(height=16),
                        section_header("Apariencia", "Hazla tuya"),
                        ft.Container(height=8),
                        appearance_card,
                        ft.Container(height=16),
                        section_header(
                            "Conexión",
                            "Internet opcional, seguro por defecto",
                            text_button(
                                "Tutorial",
                                app.open_tutorial,
                                icon=ft.Icons.PLAY_CIRCLE_OUTLINE_ROUNDED,
                            ),
                        ),
                        ft.Container(height=8),
                        server_card,
                        ft.Container(height=10),
                        ft.Row(
                            [
                                secondary_button(
                                    "Vincular banco o cuenta",
                                    lambda e: app.open_connect_sheet(),
                                    icon=ft.Icons.ACCOUNT_BALANCE_ROUNDED,
                                    expand=True,
                                    height=44,
                                )
                            ]
                        ),
                        ft.Container(height=16),
                        section_header("Widget", "Tus gastos en la pantalla de inicio"),
                        ft.Container(height=8),
                        widget_card,
                        ft.Container(height=16),
                        section_header("Demostración", "Para probar sin banco"),
                        ft.Container(height=8),
                        demo_card,
                        ft.Container(height=16),
                        section_header("Datos", "Tu información, portable"),
                        ft.Container(height=8),
                        data_card,
                        ft.Container(height=20),
                        about,
                        ft.Container(height=28),
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


