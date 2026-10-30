"""Catálogo de categorías e iconos (nombres de Material Icons de Flet)."""

from __future__ import annotations

CATEGORIES = [
    # id, nombre, icono, color, tipo, orden
    ("food", "Comida", "RESTAURANT_ROUNDED", "#E8894A", "expense", 10),
    ("groceries", "Súper", "SHOPPING_BASKET_ROUNDED", "#65A86B", "expense", 20),
    ("coffee", "Café", "LOCAL_CAFE_ROUNDED", "#B9764F", "expense", 30),
    ("transport", "Transporte", "DIRECTIONS_CAR_FILLED_ROUNDED", "#4E7CD8", "expense", 40),
    ("home", "Hogar", "HOME_ROUNDED", "#8B7CC8", "expense", 50),
    ("health", "Salud", "FAVORITE_ROUNDED", "#D95D70", "expense", 60),
    ("fun", "Ocio", "CELEBRATION_ROUNDED", "#E0B43C", "expense", 70),
    ("shopping", "Compras", "SHOPPING_BAG_ROUNDED", "#C77A9A", "expense", 80),
    ("bills", "Servicios", "RECEIPT_LONG_ROUNDED", "#6C8B94", "expense", 90),
    ("education", "Educación", "MENU_BOOK_ROUNDED", "#5B9BB5", "expense", 100),
    ("travel", "Viajes", "FLIGHT_TAKEOFF_ROUNDED", "#4FA3A3", "expense", 110),
    ("other", "Otros", "MORE_HORIZ_ROUNDED", "#89948D", "expense", 999),
    ("income", "Ingresos", "TRENDING_UP_ROUNDED", "#2E9D73", "income", 10),
]

CATEGORY_BY_ID = {c[0]: c for c in CATEGORIES}

ACCOUNT_ICONS = {
    "debit": "ACCOUNT_BALANCE_WALLET_ROUNDED",
    "credit": "CREDIT_CARD_ROUNDED",
    "cash": "PAYMENTS_ROUNDED",
    "savings": "SAVINGS_ROUNDED",
    "investment": "SHOW_CHART_ROUNDED",
}

MERCHANT_RULES = [
    ("coffee", ["cafe", "café", "starbucks", "tim horton", "dunkin", "barista", "latte"]),
    ("groceries", ["super", "súper", "walmart", "soriana", "chedraui", "costco", "la comer", "oxxo", "abarrotes", "mercado"]),
    ("food", ["restaurant", "restaurante", "taqueria", "taquería", "pizza", "burger", "sushi", "comida", "tacos", "fondita", "uber eats", "rappi", "didi food"]),
    ("transport", ["uber", "didi", "taxi", "gasolina", "pemex", "shell", "metro", "camion", "camión", "estacionamiento", "peaje", "cabify"]),
    ("home", ["renta", "casa", "hogar", "mueble", "ikea", "ferreteria", "ferretería", "limpieza"]),
    ("health", ["farmacia", "medico", "médico", "hospital", "dentista", "gym", "gimnasio", "clinica", "clínica"]),
    ("fun", ["cine", "netflix", "spotify", "concierto", "bar", "cerveza", "juego", "steam", "disney"]),
    ("shopping", ["amazon", "mercado libre", "zara", "ropa", "tenis", "liverpool", "shein", "tienda"]),
    ("bills", ["luz", "agua", "internet", "telcel", "att", "telmex", "gas natural", "recibo", "plan"]),
    ("education", ["escuela", "curso", "libro", "colegiatura", "udemy", "platzi"]),
    ("travel", ["hotel", "vuelo", "aeromexico", "aeroméxico", "volaris", "airbnb", "booking", "viaje"]),
    ("income", ["nomina", "nómina", "salario", "deposito", "depósito", "transferencia recibida", "reembolso", "venta"]),
]


def category_icon(icon_name: str):
    """Devuelve el icono de Flet de forma perezosa, sin acoplar el dominio a la UI."""
    import flet as ft

    return getattr(ft.Icons, icon_name, ft.Icons.CIRCLE)
