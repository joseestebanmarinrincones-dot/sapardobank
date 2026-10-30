"""Sistema visual de Sapardobank: papel cálido, color de marca y acentos.

Los colores son globales mutables a propósito: al cambiar de paleta se
reconstruyen las vistas y todos los componentes leen el color activo.
"""

from __future__ import annotations

import flet as ft

FONT_UI = "Lato"
FONT_DISPLAY = "DMSerif"

PALETTES = {
    "esmeralda": {
        "label": "Esmeralda",
        "brand": "#0F6B54",
        "deep": "#0A3D2F",
        "ink": "#14241D",
        "muted": "#6C7A72",
        "paper": "#F4F1E9",
        "paper_deep": "#EBE6DA",
        "mint": "#DDEFE5",
        "mint_soft": "#EEF7F2",
        "line": "#E8E2D6",
        "card_warm": "#FBF8F1",
        "gold": "#E9B65A",
        "gold_soft": "#FBF0D8",
        "coral": "#D9654C",
        "coral_soft": "#FBE9E3",
        "blue": "#406FB3",
    },
    "oceano": {
        "label": "Océano",
        "brand": "#1F618D",
        "deep": "#123B57",
        "ink": "#13232D",
        "muted": "#667A83",
        "paper": "#F1F4F5",
        "paper_deep": "#E4EBED",
        "mint": "#DCEBF2",
        "mint_soft": "#EDF5F8",
        "line": "#DDE6E9",
        "card_warm": "#F7FAFB",
        "gold": "#E2AD5C",
        "gold_soft": "#FBF1DD",
        "coral": "#D9654C",
        "coral_soft": "#FBE9E3",
        "blue": "#2E6F9E",
    },
    "lavanda": {
        "label": "Lavanda",
        "brand": "#6A5AA5",
        "deep": "#3E3468",
        "ink": "#211C2C",
        "muted": "#756F85",
        "paper": "#F4F1F7",
        "paper_deep": "#EAE5F0",
        "mint": "#E7E1F4",
        "mint_soft": "#F3EFFA",
        "line": "#E7E1EC",
        "card_warm": "#FAF8FC",
        "gold": "#D7A85A",
        "gold_soft": "#F8EEDC",
        "coral": "#C75D6C",
        "coral_soft": "#F8E5E8",
        "blue": "#6A5AA5",
    },
    "terracota": {
        "label": "Terracota",
        "brand": "#B5563E",
        "deep": "#6E2F22",
        "ink": "#2B1D18",
        "muted": "#836F66",
        "paper": "#F7F1EA",
        "paper_deep": "#EFE4D9",
        "mint": "#F3DED5",
        "mint_soft": "#FBF0EB",
        "line": "#EBDDD2",
        "card_warm": "#FCF7F2",
        "gold": "#D9A24A",
        "gold_soft": "#F9EED8",
        "coral": "#B5563E",
        "coral_soft": "#F7E3DC",
        "blue": "#4A7A9B",
    },
    "grafito": {
        "label": "Grafito",
        "brand": "#3E4A45",
        "deep": "#232B28",
        "ink": "#1A1F1D",
        "muted": "#707873",
        "paper": "#F2F2EF",
        "paper_deep": "#E7E8E3",
        "mint": "#E3E9E6",
        "mint_soft": "#F0F4F2",
        "line": "#E1E3DE",
        "card_warm": "#F8F8F5",
        "gold": "#C9A55A",
        "gold_soft": "#F6EEDC",
        "coral": "#C15D4B",
        "coral_soft": "#F6E6E1",
        "blue": "#4C6F87",
    },
    "cereza": {
        "label": "Cereza",
        "brand": "#A33A5B",
        "deep": "#5E1F33",
        "ink": "#2A1920",
        "muted": "#856A74",
        "paper": "#F8F1F2",
        "paper_deep": "#F0E4E7",
        "mint": "#F4DEE6",
        "mint_soft": "#FBF0F4",
        "line": "#ECDDE2",
        "card_warm": "#FCF7F8",
        "gold": "#D8A54E",
        "gold_soft": "#F9EED9",
        "coral": "#A33A5B",
        "coral_soft": "#F6E0E6",
        "blue": "#5F7FA8",
    },
}

ACTIVE_PALETTE = "esmeralda"
# Valores iniciales; apply_palette() los reemplaza al iniciar la app.
GREEN = "#0F6B54"
GREEN_DEEP = "#0A3D2F"
GREEN_DARK = "#072B22"
MINT = "#DDEFE5"
MINT_SOFT = "#EEF7F2"
INK = "#14241D"
INK_SOFT = "#2C3E35"
MUTED = "#6C7A72"
MUTED_LIGHT = "#95A199"
PAPER = "#F4F1E9"
PAPER_DEEP = "#EBE6DA"
CARD = "#FFFFFF"
CARD_WARM = "#FBF8F1"
LINE = "#E8E2D6"
GOLD = "#E9B65A"
GOLD_SOFT = "#FBF0D8"
CORAL = "#D9654C"
CORAL_SOFT = "#FBE9E3"
BLUE = "#406FB3"
WHITE = "#FFFFFF"


def mix(hex_a: str, hex_b: str, ratio: float) -> str:
    ratio = max(0.0, min(1.0, ratio))
    a = hex_a.lstrip("#")
    b = hex_b.lstrip("#")
    out = []
    for i in range(0, 6, 2):
        va = int(a[i : i + 2], 16)
        vb = int(b[i : i + 2], 16)
        out.append(f"{int(va + (vb - va) * ratio):02X}")
    return "#" + "".join(out)


def darken(hex_color: str, amount: float = 0.35) -> str:
    return mix(hex_color, "#061A13", amount)


def lighten(hex_color: str, amount: float = 0.8) -> str:
    return mix(hex_color, "#FFFFFF", amount)


def alpha(hex_color: str, opacity: float) -> str:
    return ft.Colors.with_opacity(opacity, hex_color)


def apply_palette(name: str | None) -> str:
    """Activa una paleta y actualiza los colores globales."""
    global ACTIVE_PALETTE, GREEN, GREEN_DEEP, GREEN_DARK, MINT, MINT_SOFT
    global INK, INK_SOFT, MUTED, MUTED_LIGHT, PAPER, PAPER_DEEP, CARD, CARD_WARM
    global LINE, GOLD, GOLD_SOFT, CORAL, CORAL_SOFT, BLUE, WHITE

    key = (name or "").strip().lower()
    if key not in PALETTES:
        key = "esmeralda"
    p = PALETTES[key]
    ACTIVE_PALETTE = key
    GREEN = p["brand"]
    GREEN_DEEP = p["deep"]
    GREEN_DARK = darken(p["deep"], 0.28)
    MINT = p["mint"]
    MINT_SOFT = p["mint_soft"]
    INK = p["ink"]
    INK_SOFT = mix(p["ink"], "#FFFFFF", 0.15)
    MUTED = p["muted"]
    MUTED_LIGHT = mix(p["muted"], "#FFFFFF", 0.38)
    PAPER = p["paper"]
    PAPER_DEEP = p["paper_deep"]
    CARD = "#FFFFFF"
    CARD_WARM = p["card_warm"]
    LINE = p["line"]
    GOLD = p["gold"]
    GOLD_SOFT = p["gold_soft"]
    CORAL = p["coral"]
    CORAL_SOFT = p["coral_soft"]
    BLUE = p["blue"]
    WHITE = "#FFFFFF"
    return key


def theme_choices() -> list[dict]:
    return [
        {
            "key": key,
            "label": value["label"],
            "brand": value["brand"],
            "deep": value["deep"],
            "mint": value["mint"],
            "paper": value["paper"],
        }
        for key, value in PALETTES.items()
    ]


def app_theme() -> ft.Theme:
    return ft.Theme(
        color_scheme_seed=GREEN,
        font_family=FONT_UI,
        use_material3=True,
        scaffold_bgcolor=PAPER,
        card_bgcolor=CARD,
        divider_color=LINE,
        visual_density=ft.VisualDensity.COMFORTABLE,
    )


def configure_page(page: ft.Page) -> None:
    page.title = "Sapardobank · Gastos diarios"
    page.bgcolor = PAPER
    page.padding = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = app_theme()
    page.fonts = {
        FONT_UI: "fonts/Lato-Regular.ttf",
        FONT_DISPLAY: "fonts/DMSerifDisplay-Regular.ttf",
    }
    page.window.width = 430
    page.window.height = 900
    page.window.min_width = 360
    page.window.min_height = 640
    page.window.bgcolor = PAPER


def text(
    value: str,
    size: float = 14,
    color: str | None = None,
    weight: ft.FontWeight | None = None,
    *,
    display: bool = False,
    max_lines: int | None = None,
    align: ft.TextAlign | None = None,
    italic: bool = False,
    expand: bool = False,
    selectable: bool = False,
    tooltip: str | None = None,
) -> ft.Text:
    return ft.Text(
        value,
        size=size,
        color=color or INK,
        weight=weight,
        font_family=FONT_DISPLAY if display else FONT_UI,
        max_lines=max_lines,
        overflow=ft.TextOverflow.ELLIPSIS if max_lines else None,
        text_align=align,
        italic=italic,
        expand=expand,
        selectable=selectable,
        tooltip=tooltip,
    )
