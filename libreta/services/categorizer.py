"""Categorización automática por palabras clave."""

from __future__ import annotations

import unicodedata

from ..core.catalog import MERCHANT_RULES


def _normalize(text: str | None) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def suggest_category(description: str | None, merchant: str | None = None) -> str:
    haystack = _normalize(f"{description or ''} {merchant or ''}")
    if not haystack.strip():
        return "other"
    for category_id, keywords in MERCHANT_RULES:
        for keyword in keywords:
            if _normalize(keyword) in haystack:
                return category_id
    return "other"
