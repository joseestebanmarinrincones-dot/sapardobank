"""Fechas locales y etiquetas en español, sin dependencias externas."""

from __future__ import annotations

from datetime import date, datetime, timedelta

MONTHS_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
WEEKDAYS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def today_start() -> datetime:
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)


def day_bounds(day: date | datetime | None = None) -> tuple[str, str]:
    d = day or date.today()
    if isinstance(d, datetime):
        d = d.date()
    start = datetime.combine(d, datetime.min.time())
    end = start + timedelta(days=1)
    return start.isoformat(), end.isoformat()


def month_bounds(day: date | datetime | None = None) -> tuple[str, str]:
    d = day or date.today()
    if isinstance(d, datetime):
        d = d.date()
    start = d.replace(day=1)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return datetime.combine(start, datetime.min.time()).isoformat(), end.isoformat()


def week_bounds(day: date | datetime | None = None) -> tuple[str, str]:
    d = day or date.today()
    if isinstance(d, datetime):
        d = d.date()
    start = d - timedelta(days=d.weekday())
    end = start + timedelta(days=7)
    return datetime.combine(start, datetime.min.time()).isoformat(), end.isoformat()


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d")
        except ValueError:
            return None


def human_day(value: str | datetime | date | None, *, relative: bool = True) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        parsed = parse_iso(value)
        if not parsed:
            return value
        d = parsed.date()
    elif isinstance(value, datetime):
        d = value.date()
    else:
        d = value
    today = date.today()
    if relative:
        if d == today:
            return "Hoy"
        if d == today - timedelta(days=1):
            return "Ayer"
        if d == today + timedelta(days=1):
            return "Mañana"
    return f"{WEEKDAYS_ES[d.weekday()].capitalize()} {d.day} de {MONTHS_ES[d.month - 1]}"


def short_date(value: str | datetime | date | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        parsed = parse_iso(value)
        if not parsed:
            return value
        d = parsed.date()
    elif isinstance(value, datetime):
        d = value.date()
    else:
        d = value
    return f"{d.day:02d} {MONTHS_ES[d.month - 1][:3]}"


def month_label(value: date | datetime | None = None) -> str:
    d = value or date.today()
    if isinstance(d, datetime):
        d = d.date()
    return f"{MONTHS_ES[d.month - 1].capitalize()} {d.year}"


def time_label(iso: str | None) -> str:
    dt = parse_iso(iso)
    if not dt:
        return ""
    h = dt.hour % 12 or 12
    suffix = "a. m." if dt.hour < 12 else "p. m."
    return f"{h}:{dt.minute:02d} {suffix}"


def greeting(now: datetime | None = None) -> str:
    now = now or datetime.now()
    if now.hour < 12:
        return "Buenos días"
    if now.hour < 19:
        return "Buenas tardes"
    return "Buenas noches"


def weekday_short(value: str | date | datetime) -> str:
    if isinstance(value, str):
        parsed = parse_iso(value)
        d = parsed.date() if parsed else date.today()
    elif isinstance(value, datetime):
        d = value.date()
    else:
        d = value
    return ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"][d.weekday()]
