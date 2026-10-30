"""Feed bancario simulado en tiempo real (modo demostración)."""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass

from ..core.dates import now_iso
from ..core.models import Transaction
from .ledger import Ledger
from .settings import SettingsService


@dataclass(frozen=True)
class SpendingPattern:
    category_id: str
    descriptions: tuple[tuple[str, str], ...]
    minimum_cents: int
    maximum_cents: int
    weight: int


PATTERNS = [
    SpendingPattern(
        "coffee",
        (("Café de olla", "Café Central"), ("Latte para llevar", "Starbucks"), ("Americano", "Café Central")),
        3200, 7800, 20,
    ),
    SpendingPattern(
        "food",
        (("Comida corrida", "Fonda Doña Mari"), ("Tacos al pastor", "El Pastorcito"), ("Ramen del día", "Ramen Ya"), ("Pizza con amigos", "Pizzeria Roma")),
        9500, 32000, 25,
    ),
    SpendingPattern(
        "groceries",
        (("Despensa", "Soriana"), ("Súper express", "Oxxo"), ("Frutas y verduras", "Mercado"), ("Compra semanal", "La Comer")),
        12000, 85000, 18,
    ),
    SpendingPattern(
        "transport",
        (("Viaje en Uber", "Uber"), ("Gasolina", "Pemex"), ("Viaje en DiDi", "DiDi"), ("Estacionamiento", "Park")),
        5500, 45000, 15,
    ),
    SpendingPattern(
        "fun",
        (("Cine y palomitas", "Cinépolis"), ("Cerveza con amigos", "La Cervecería"), ("Concierto", "Ticketmaster")),
        12000, 48000, 8,
    ),
    SpendingPattern(
        "shopping",
        (("Compra en línea", "Amazon"), ("Playera nueva", "Zara"), ("Accesorio", "Mercado Libre")),
        15000, 120000, 8,
    ),
    SpendingPattern(
        "home",
        (("Ferretería", "Home Depot"), ("Limieza", "Walmart"), ("Foco y pilas", "La Comer")),
        8000, 60000, 6,
    ),
]


class DemoFeed:
    def __init__(self, ledger: Ledger, settings: SettingsService):
        self.ledger = ledger
        self.settings = settings
        self.rng = random.Random()
        self._weights = [p.weight for p in PATTERNS]

    def generate(self, *, force: bool = False) -> Transaction | None:
        if not force and not self.settings.demo_live:
            return None
        account = self.ledger.demo_account()
        if not account:
            return None
        pattern = self.rng.choices(PATTERNS, weights=self._weights, k=1)[0]
        description, merchant = self.rng.choice(pattern.descriptions)
        amount = self.rng.randint(pattern.minimum_cents, pattern.maximum_cents)
        # Cifras "bonitas" de 50 centavos para que se sientan de ticket real.
        amount = max(100, (amount // 50) * 50)
        occurred = now_iso()
        external_id = f"demo_live_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        tx = self.ledger.add_transaction(
            account_id=account.id,
            amount_cents=-amount,
            description=description,
            category_id=pattern.category_id,
            merchant=merchant,
            occurred_at=occurred,
            source="demo",
            external_id=external_id,
        )
        self.ledger.set_provider_balance(account.id, self.ledger.account_balance(account), occurred)
        self.ledger.log_sync("demo", "ok", f"Compra simulada: {description}", 1)
        return tx

    def simulate_income(self) -> Transaction | None:
        account = self.ledger.demo_account()
        if not account:
            return None
        tx = self.ledger.add_transaction(
            account_id=account.id,
            amount_cents=150000,
            description="Venta en mercado",
            category_id="income",
            merchant="Mercado Libre",
            occurred_at=now_iso(),
            source="demo",
            external_id=f"demo_income_{uuid.uuid4().hex[:8]}",
        )
        self.ledger.log_sync("demo", "ok", "Ingreso simulado", 1)
        return tx
