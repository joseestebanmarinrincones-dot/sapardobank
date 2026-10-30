"""Generación de la imagen del widget para pantalla de inicio.

Android/iOS no permiten ejecutar Python dentro del launcher. Por eso Sapardobank
genera un "widget visual" PNG de alta resolución que puedes colocar con el
widget de Fotos/Galería del sistema y actualizar desde la app. El JSON adjunto
sirve como puente para una integración nativa (ver native_widget/README.md).
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ..core.dates import now_iso, time_label
from ..core.models import WidgetSnapshot
from ..core.money import format_money
from ..paths import WIDGET_DIR, ensure_dir
from .dashboard import DashboardService
from .settings import SettingsService

PALETTES = {
    "forest": {
        "top": (12, 50, 39),
        "bottom": (18, 112, 82),
        "text": (247, 244, 235),
        "muted": (196, 224, 210),
        "accent": (242, 196, 107),
        "panel": (22, 78, 61),
        "bar_bg": (255, 255, 255, 40),
        "danger": (255, 143, 116),
    },
    "paper": {
        "top": (247, 242, 232),
        "bottom": (232, 222, 204),
        "text": (20, 38, 30),
        "muted": (99, 113, 103),
        "accent": (15, 107, 84),
        "panel": (255, 253, 247),
        "bar_bg": (15, 107, 84, 35),
        "danger": (185, 75, 52),
    },
    "night": {
        "top": (14, 22, 20),
        "bottom": (31, 53, 44),
        "text": (244, 241, 233),
        "muted": (157, 177, 166),
        "accent": (126, 220, 181),
        "panel": (31, 49, 41),
        "bar_bg": (255, 255, 255, 36),
        "danger": (255, 138, 120),
    },
}

VARIANTS = {"wide": (1080, 540), "square": (1080, 1080), "compact": (540, 540)}
ROOT = Path(__file__).resolve().parents[2]
FONT_CANDIDATES = [
    ROOT / "assets" / "fonts",
    Path.cwd() / "assets" / "fonts",
    Path(os.environ.get("FLET_APP_STORAGE_DATA", "")) / "fonts" if os.environ.get("FLET_APP_STORAGE_DATA") else None,
]


@dataclass(slots=True)
class WidgetRender:
    path: Path
    image_bytes: bytes
    snapshot: WidgetSnapshot
    variant: str
    theme: str


def _font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for folder in FONT_CANDIDATES:
        if not folder:
            continue
        path = folder / name
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                pass
    return ImageFont.load_default()


def _gradient(size: tuple[int, int], top: tuple, bottom: tuple) -> Image.Image:
    width, height = size
    base = Image.new("RGB", (1, height))
    px = base.load()
    for y in range(height):
        ratio = y / max(1, height - 1)
        px[0, y] = tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3))
    return base.resize((width, height))


def _money(cents: int, symbol: str, hidden: bool) -> str:
    if hidden:
        return f"{symbol}••••"
    return format_money(cents, symbol, decimals=False)


def _short_money(cents: int, symbol: str) -> str:
    value = abs(cents) / 100
    if value >= 1000:
        return f"{symbol}{value / 1000:.1f}k".replace(".0k", "k")
    return format_money(cents, symbol, decimals=False)


def _fit_font(draw, text: str, font_name: str, start: int, min_size: int, max_width: int):
    size = start
    while size > min_size:
        font = _font(font_name, size)
        if draw.textlength(text, font=font) <= max_width:
            return font
        size -= 4
    return _font(font_name, min_size)


def _text(draw, xy, text, font, fill, anchor=None):
    draw.text(xy, text, font=font, fill=fill, anchor=anchor)


def _progress(draw, box, fraction: float, palette: dict, over: bool):
    x1, y1, x2, y2 = box
    height = y2 - y1
    draw.rounded_rectangle(box, radius=height // 2, fill=palette["bar_bg"])
    filled = int((x2 - x1) * max(0.0, min(1.0, fraction)))
    color = palette["danger"] if over else palette["accent"]
    if filled > 0:
        draw.rounded_rectangle((x1, y1, x1 + max(height, filled), y2), radius=height // 2, fill=color)


def _decorations(img: Image.Image, palette: dict):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    w, h = img.size
    d.ellipse((w - 260, -140, w + 80, 200), fill=(255, 255, 255, 12))
    d.ellipse((w - 150, h - 120, w + 140, h + 170), fill=(255, 255, 255, 8))
    d.ellipse((-120, h - 220, 140, h + 40), fill=(255, 255, 255, 6))
    img.alpha_composite(overlay)


def _brand(draw, x, y, palette, name: str = "SAPARDOBANK"):
    draw.rounded_rectangle((x, y, x + 38, y + 38), radius=11, fill=palette["accent"])
    _text(draw, (x + 19, y + 20), "L", _font("DMSerifDisplay-Regular.ttf", 24), palette["top"], anchor="mm")
    _text(draw, (x + 52, y + 19), name, _font("Lato-Bold.ttf", 17), palette["text"], anchor="lm")
    _text(draw, (x + 52, y + 42), "GASTOS DIARIOS", _font("Lato-Regular.ttf", 12), palette["muted"], anchor="lm")


def _tx_row(draw, x, y, width, item, palette, symbol, hidden, compact=False):
    dot_color = tuple(int(item.get("color", "#89948D").lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    draw.ellipse((x, y + 7, x + 16, y + 23), fill=dot_color)
    _text(draw, (x + 30, y + 16), item["description"][:32], _font("Lato-Bold.ttf", 18 if not compact else 16), palette["text"], anchor="lm")
    category = item.get("category", "")
    at = time_label(item.get("at"))
    _text(draw, (x + 30, y + 38), f"{category} · {at}"[:36], _font("Lato-Regular.ttf", 13 if not compact else 12), palette["muted"], anchor="lm")
    amount = item["amount_cents"]
    text = "••••" if hidden else format_money(amount, symbol, decimals=False)
    _text(draw, (x + width, y + 22), text, _font("Lato-Bold.ttf", 18 if not compact else 16), palette["text"], anchor="rm")


class WidgetService:
    def __init__(self, dashboard: DashboardService, settings: SettingsService):
        self.dashboard = dashboard
        self.settings = settings

    def snapshot(self, hidden: bool | None = None) -> WidgetSnapshot:
        if hidden is None:
            hidden = self.settings.get_bool("widget_privacy", False)
        return self.dashboard.widget_snapshot(hidden=hidden)

    def render(
        self,
        variant: str | None = None,
        theme: str | None = None,
        hidden: bool | None = None,
    ) -> WidgetRender:
        variant = variant or self.settings.get("widget_variant", "wide")
        theme = theme or self.settings.get("widget_theme", "forest")
        if variant not in VARIANTS:
            variant = "wide"
        if theme not in PALETTES:
            theme = "forest"
        snapshot = self.snapshot(hidden)
        palette = PALETTES[theme]
        width, height = VARIANTS[variant]
        img = _gradient((width, height), palette["top"], palette["bottom"]).convert("RGBA")
        _decorations(img, palette)
        draw = ImageDraw.Draw(img)
        symbol = snapshot.currency_symbol
        hidden_amounts = snapshot.hidden

        if variant == "wide":
            self._draw_wide(draw, img, snapshot, palette, symbol, hidden_amounts)
        elif variant == "square":
            self._draw_square(draw, img, snapshot, palette, symbol, hidden_amounts)
        else:
            self._draw_compact(draw, img, snapshot, palette, symbol, hidden_amounts)

        _text(
            draw,
            (width - 48, height - 28),
            f"Actualizado {datetime.now().strftime('%H:%M')}",
            _font("Lato-Regular.ttf", 13),
            palette["muted"],
            anchor="rm",
        )
        out_dir = ensure_dir(WIDGET_DIR)
        path = out_dir / f"libreta_widget_{variant}.png"
        img.convert("RGB").save(path, "PNG", optimize=True)
        meta_path = out_dir / f"libreta_widget_{variant}.json"
        meta_path.write_text(
            json.dumps(asdict(snapshot), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        # Un único snapshot "actual" para un futuro widget nativo.
        snapshot_payload = {
            "variant": variant,
            "theme": theme,
            "updated_at": now_iso(),
            **asdict(snapshot),
        }
        data_json = json.dumps(snapshot_payload, ensure_ascii=False, indent=2)
        (out_dir / "widget_data.json").write_text(data_json, encoding="utf-8")
        # Puente nativo: en Android FLET_APP_STORAGE_DATA es
        # /data/data/<package>/files/data, accesible por el AppWidgetProvider.
        native_target = out_dir.parent / "widget_data.json"
        tmp_path = native_target.with_suffix(".json.tmp")
        tmp_path.write_text(data_json, encoding="utf-8")
        os.replace(tmp_path, native_target)
        self.settings.set("last_widget_at", now_iso())
        self.settings.set("last_widget_path", str(path))
        self.settings.set("widget_variant", variant)
        self.settings.set("widget_theme", theme)
        if hidden is not None:
            self.settings.set("widget_privacy", hidden)
        image_bytes = path.read_bytes()
        return WidgetRender(path=path, image_bytes=image_bytes, snapshot=snapshot, variant=variant, theme=theme)

    def _draw_wide(self, draw, img, snap, palette, symbol, hidden):
        w, h = img.size
        _brand(draw, 52, 40, palette, name="SAPARDOBANK")
        try:
            date_label = datetime.fromisoformat(snap.generated_at).strftime("%d %b %Y").upper()
        except ValueError:
            date_label = datetime.now().strftime("%d %b %Y").upper()
        _text(draw, (w - 52, 60), date_label, _font("Lato-Regular.ttf", 15), palette["muted"], anchor="rm")

        _text(draw, (52, 132), "GASTOS DE HOY", _font("Lato-Bold.ttf", 16), palette["accent"], anchor="lm")
        amount = _money(snap.spent_today_cents, symbol, hidden)
        font = _fit_font(draw, amount, "DMSerifDisplay-Regular.ttf", 104, 62, 540)
        _text(draw, (48, 178), amount, font, palette["text"], anchor="la")

        fraction = snap.spent_today_cents / snap.daily_budget_cents if snap.daily_budget_cents else 1.0
        _progress(draw, (52, 328, 590, 346), fraction, palette, snap.spent_today_cents > snap.daily_budget_cents)
        remaining = _money(snap.remaining_cents, symbol, hidden)
        _text(draw, (52, 372), f"Te quedan {remaining}" if snap.remaining_cents else "Presupuesto agotado", _font("Lato-Bold.ttf", 17), palette["text"], anchor="lm")
        _text(draw, (52, 398), f"Presupuesto diario {_money(snap.daily_budget_cents, symbol, hidden)}", _font("Lato-Regular.ttf", 14), palette["muted"], anchor="lm")

        panel = (636, 112, w - 52, 462)
        draw.rounded_rectangle(panel, radius=30, fill=palette["panel"])
        _text(draw, (668, 146), "ÚLTIMOS MOVIMIENTOS", _font("Lato-Bold.ttf", 14), palette["accent"], anchor="lm")
        items = snap.last_transactions[:2]
        y = 184
        for item in items:
            _tx_row(draw, 668, y, panel[2] - 668 - 32, item, palette, symbol, hidden)
            y += 104
        if not items:
            _text(draw, (668, 220), "Sin movimientos todavía", _font("Lato-Regular.ttf", 16), palette["muted"], anchor="lm")
        _text(draw, (668, 430), f"Mes: {_money(snap.month_spent_cents, symbol, hidden)}", _font("Lato-Regular.ttf", 14), palette["muted"], anchor="lm")

    def _draw_square(self, draw, img, snap, palette, symbol, hidden):
        w, h = img.size
        _brand(draw, 56, 52, palette, name="SAPARDOBANK")
        _text(draw, (w - 56, 72), datetime.now().strftime("%d %b").upper(), _font("Lato-Bold.ttf", 15), palette["muted"], anchor="rm")
        _text(draw, (56, 196), "GASTOS DE HOY", _font("Lato-Bold.ttf", 18), palette["accent"], anchor="lm")
        amount = _money(snap.spent_today_cents, symbol, hidden)
        font = _fit_font(draw, amount, "DMSerifDisplay-Regular.ttf", 154, 80, 900)
        _text(draw, (52, 250), amount, font, palette["text"], anchor="la")
        fraction = snap.spent_today_cents / snap.daily_budget_cents if snap.daily_budget_cents else 1.0
        _progress(draw, (56, 450, w - 56, 474), fraction, palette, snap.spent_today_cents > snap.daily_budget_cents)
        _text(draw, (56, 502), f"Te quedan {_money(snap.remaining_cents, symbol, hidden)}", _font("Lato-Bold.ttf", 20), palette["text"], anchor="lm")
        _text(draw, (w - 56, 502), f"Mes {_money(snap.month_spent_cents, symbol, hidden)}", _font("Lato-Regular.ttf", 15), palette["muted"], anchor="rm")

        draw.rounded_rectangle((56, 570, w - 56, 950), radius=34, fill=palette["panel"])
        _text(draw, (92, 610), "MOVIMIENTOS RECIENTES", _font("Lato-Bold.ttf", 15), palette["accent"], anchor="lm")
        y = 660
        for item in snap.last_transactions[:3]:
            _tx_row(draw, 92, y, w - 92 - 56, item, palette, symbol, hidden)
            y += 86
        _text(draw, (92, 916), f"Mayor categoría: {snap.top_category}", _font("Lato-Regular.ttf", 14), palette["muted"], anchor="lm")

    def _draw_compact(self, draw, img, snap, palette, symbol, hidden):
        w, h = img.size
        _brand(draw, 34, 30, palette, name="SAPARDOBANK")
        _text(draw, (34, 152), "HOY", _font("Lato-Bold.ttf", 14), palette["accent"], anchor="lm")
        amount = _money(snap.spent_today_cents, symbol, hidden)
        font = _fit_font(draw, amount, "DMSerifDisplay-Regular.ttf", 86, 50, 440)
        _text(draw, (30, 180), amount, font, palette["text"], anchor="la")
        fraction = snap.spent_today_cents / snap.daily_budget_cents if snap.daily_budget_cents else 1.0
        _progress(draw, (34, 360, w - 34, 376), fraction, palette, snap.spent_today_cents > snap.daily_budget_cents)
        _text(draw, (34, 408), f"Quedan {_money(snap.remaining_cents, symbol, hidden)}", _font("Lato-Bold.ttf", 16), palette["text"], anchor="lm")
        _text(draw, (34, 440), f"{snap.top_category} · mes {_short_money(snap.month_spent_cents, symbol)}", _font("Lato-Regular.ttf", 13), palette["muted"], anchor="lm")
