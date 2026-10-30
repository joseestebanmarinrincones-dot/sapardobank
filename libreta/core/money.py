"""Dinero en centavos, sin errores de punto flotante."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


class MoneyError(ValueError):
    pass


_CLEAN_RE = re.compile(r"[^0-9,.\-]")


def parse_amount_to_cents(raw: str | int | float | Decimal) -> int:
    """Convierte texto de usuario a centavos.

    Acepta formatos como ``$1,234.50``, ``1.234,50``, ``1234``, ``12,50``.
    Lanza MoneyError si el valor no es válido o es cero.
    """
    if isinstance(raw, bool):
        raise MoneyError("Monto inválido")
    if isinstance(raw, (int, float, Decimal)):
        value = Decimal(str(raw))
    else:
        text = str(raw).strip().replace("\u00a0", "").replace(" ", "")
        if not text:
            raise MoneyError("Escribe un monto")
        text = _CLEAN_RE.sub("", text)
        if not text or text in {"-", ".", ","}:
            raise MoneyError("Escribe un monto válido")

        negative = text.startswith("-")
        text = text.lstrip("-")
        has_comma = "," in text
        has_dot = "." in text

        if has_comma and has_dot:
            # El último separador que aparece es el decimal.
            if text.rfind(",") > text.rfind("."):
                text = text.replace(".", "").replace(",", ".")
            else:
                text = text.replace(",", "")
        elif has_comma:
            parts = text.split(",")
            if len(parts) > 2:
                # 1,234,567 -> separador de miles
                text = "".join(parts)
            elif len(parts[-1]) == 3 and len(parts[0]) <= 3 and parts[0] != "0":
                # 1,500 se interpreta como miles (formato frecuente en México)
                text = "".join(parts)
            else:
                text = ".".join(parts)
        elif has_dot:
            parts = text.split(".")
            if len(parts) > 2:
                text = "".join(parts[:-1]) + "." + parts[-1]
            elif len(parts[-1]) == 3 and len(parts[0]) <= 3 and parts[0] != "0":
                text = "".join(parts)
        if negative:
            text = "-" + text
        try:
            value = Decimal(text)
        except InvalidOperation as exc:
            raise MoneyError("Escribe un monto válido") from exc

    if not value.is_finite():
        raise MoneyError("Escribe un monto válido")
    cents = int((value * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if cents == 0:
        raise MoneyError("El monto debe ser mayor a cero")
    return cents


def split_sign(amount_cents: int, kind: str) -> int:
    """Devuelve el monto firmado según sea gasto o ingreso."""
    amount = abs(int(amount_cents))
    if amount <= 0:
        raise MoneyError("El monto debe ser mayor a cero")
    return amount if kind == "income" else -amount


def format_money(
    cents: int | None,
    symbol: str = "$",
    *,
    show_sign: bool = False,
    decimals: bool = True,
) -> str:
    if cents is None:
        return f"{symbol}—"
    cents = int(cents)
    sign = "-" if cents < 0 else ("+" if show_sign and cents > 0 else "")
    absolute = abs(cents)
    whole = absolute // 100
    fraction = absolute % 100
    if _use_decimal_comma(symbol):
        grouped = f"{whole:,}".replace(",", ".")
        return f"{sign}{symbol}{grouped},{fraction:02d}" if decimals else f"{sign}{symbol}{grouped}"
    grouped = f"{whole:,}"
    return f"{sign}{symbol}{grouped}.{fraction:02d}" if decimals else f"{sign}{symbol}{grouped}"


def _use_decimal_comma(symbol: str) -> bool:
    # Formato mexicano/español: $1.234,50. Para USD conservamos 1,234.50.
    return symbol in {"€", "ARS", "CLP"}


def format_compact(cents: int, symbol: str = "$") -> str:
    absolute = abs(cents) / 100
    sign = "-" if cents < 0 else ""
    if absolute >= 1_000_000:
        return f"{sign}{symbol}{absolute / 1_000_000:.1f}M".replace(".0M", "M")
    if absolute >= 1_000:
        value = absolute / 1_000
        text = f"{value:.1f}".rstrip("0").rstrip(".")
        return f"{sign}{symbol}{text}k"
    return format_money(cents, symbol, decimals=False)


def percentage(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return max(0.0, min(1.0, part / total))
