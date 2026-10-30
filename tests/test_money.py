from datetime import datetime

import pytest

from libreta.core.money import MoneyError, format_money, parse_amount_to_cents


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1234.50", 123450),
        ("$1,234.50", 123450),
        ("1.234,50", 123450),
        ("12,50", 1250),
        ("1,500", 150000),
        ("0.01", 1),
        ("$ 89", 8900),
        ("-45.20", -4520),
    ],
)
def test_parse_amount(raw, expected):
    assert parse_amount_to_cents(raw) == expected


@pytest.mark.parametrize("raw", ["", "abc", "0", "-0.00", " "])
def test_parse_amount_invalid(raw):
    with pytest.raises(MoneyError):
        parse_amount_to_cents(raw)


def test_format_money():
    assert format_money(123450) == "$1,234.50"
    assert format_money(-4200, show_sign=False) == "-$42.00"
    assert format_money(123450, decimals=False) == "$1,234"
    assert format_money(None) == "$—"


def test_format_compact():
    from libreta.core.money import format_compact

    assert format_compact(123450) == "$1.2k"
    assert format_compact(120000) == "$1.2k"
    assert format_compact(1500000) == "$15k"
    assert format_compact(100) == "$1"
