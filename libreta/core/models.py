"""Modelos de dominio."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Account:
    id: str
    name: str
    institution: str
    kind: str
    currency: str
    initial_balance_cents: int
    balance_cents: int | None
    color: str
    icon: str
    provider: str
    provider_ref: str | None
    last_sync_at: str | None
    is_demo: bool
    is_archived: bool
    created_at: str

    @property
    def is_linked(self) -> bool:
        return self.provider not in {"manual", "cash"}


@dataclass(slots=True)
class Category:
    id: str
    name: str
    icon: str
    color: str
    kind: str
    sort_order: int
    builtin: bool


@dataclass(slots=True)
class Transaction:
    id: str
    account_id: str
    amount_cents: int
    currency: str
    description: str
    merchant: str | None
    category_id: str | None
    occurred_at: str
    created_at: str
    source: str
    external_id: str | None
    pending: bool
    notes: str | None
    sync_state: str
    deleted: bool
    raw_json: str | None = None

    @property
    def is_expense(self) -> bool:
        return self.amount_cents < 0

    @property
    def absolute_cents(self) -> int:
        return abs(self.amount_cents)


@dataclass(slots=True)
class TransactionView:
    transaction: Transaction
    account: Account | None
    category: Category | None


@dataclass(slots=True)
class Totals:
    expenses_cents: int = 0
    income_cents: int = 0
    count: int = 0
    expense_count: int = 0

    @property
    def net_cents(self) -> int:
        return self.income_cents - self.expenses_cents


@dataclass(slots=True)
class CategoryTotal:
    category: Category | None
    total_cents: int
    count: int
    share: float = 0.0


@dataclass(slots=True)
class DailyPoint:
    day: str
    expenses_cents: int
    income_cents: int = 0


@dataclass(slots=True)
class WidgetSnapshot:
    generated_at: str
    currency_symbol: str
    spent_today_cents: int
    income_today_cents: int
    daily_budget_cents: int
    remaining_cents: int
    month_spent_cents: int
    top_category: str
    top_category_cents: int
    last_transactions: list[dict[str, Any]] = field(default_factory=list)
    hidden: bool = False
    name: str = "Sapardobank"
