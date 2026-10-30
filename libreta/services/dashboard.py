"""Agregados para la pantalla de inicio, reportes y widget."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from ..core.dates import day_bounds, human_day, month_bounds, month_label
from ..core.models import Account, CategoryTotal, DailyPoint, Totals, TransactionView, WidgetSnapshot
from ..core.money import percentage
from .ledger import Ledger
from .settings import SettingsService


@dataclass(slots=True)
class DashboardData:
    today: Totals
    month: Totals
    all_time: Totals
    balance_cents: int
    budget_cents: int
    remaining_cents: int
    budget_used: float
    over_budget: bool
    categories: list[CategoryTotal]
    week: list[DailyPoint]
    recent: list[TransactionView]
    accounts: list[Account]
    monthly: list[tuple[str, int]]
    demo_live: bool
    today_label: str
    month_label: str

    @property
    def top_category(self) -> CategoryTotal | None:
        return self.categories[0] if self.categories else None

    @property
    def average_day_cents(self) -> int:
        active_days = len([p for p in self.week if p.expenses_cents > 0]) or 1
        return sum(p.expenses_cents for p in self.week) // active_days


@dataclass(slots=True)
class ReportsData:
    month: Totals
    previous_month: Totals
    categories: list[CategoryTotal]
    daily: list[DailyPoint]
    weekly: list[tuple[str, int]]
    monthly: list[tuple[str, int]]
    biggest_expense: TransactionView | None
    average_day_cents: int
    active_days: int
    projected_month_cents: int
    budget_daily_cents: int
    accounts: list[Account] = field(default_factory=list)


class DashboardService:
    def __init__(self, ledger: Ledger, settings: SettingsService):
        self.ledger = ledger
        self.settings = settings

    def load(self) -> DashboardData:
        today_start_iso, tomorrow = day_bounds()
        month_start, month_end = month_bounds()
        today = self.ledger.totals(start=today_start_iso, end=tomorrow)
        month = self.ledger.totals(start=month_start, end=month_end)
        all_time = self.ledger.totals()
        budget = self.settings.daily_budget_cents
        remaining = max(0, budget - today.expenses_cents) if budget else 0
        week = self.week_series(7)
        categories = self.ledger.category_totals(start=month_start, end=month_end)[:5]
        recent = self.ledger.recent_views(5)
        return DashboardData(
            today=today,
            month=month,
            all_time=all_time,
            balance_cents=self.ledger.total_balance(),
            budget_cents=budget,
            remaining_cents=remaining,
            budget_used=percentage(today.expenses_cents, budget) if budget else 0.0,
            over_budget=bool(budget and today.expenses_cents > budget),
            categories=categories,
            week=week,
            recent=recent,
            accounts=self.ledger.accounts(),
            monthly=self.monthly_series(6),
            demo_live=self.settings.demo_live,
            today_label=human_day(date.today()),
            month_label=month_label(),
        )

    def week_series(self, days: int = 7) -> list[DailyPoint]:
        end_day = date.today() + timedelta(days=1)
        start_day = date.today() - timedelta(days=days - 1)
        start = datetime.combine(start_day, datetime.min.time()).isoformat()
        end = datetime.combine(end_day, datetime.min.time()).isoformat()
        rows = {p.day: p for p in self.ledger.daily_totals(start=start, end=end)}
        points: list[DailyPoint] = []
        for i in range(days):
            d = start_day + timedelta(days=i)
            p = rows.get(d.isoformat())
            points.append(p or DailyPoint(day=d.isoformat(), expenses_cents=0, income_cents=0))
        return points

    def daily_series(self, month: date | None = None) -> list[DailyPoint]:
        start_iso, end_iso = month_bounds(month)
        start_dt = datetime.fromisoformat(start_iso)
        end_dt = datetime.fromisoformat(end_iso)
        rows = {p.day: p for p in self.ledger.daily_totals(start=start_iso, end=end_iso)}
        points: list[DailyPoint] = []
        d = start_dt.date()
        while d < end_dt.date():
            p = rows.get(d.isoformat())
            points.append(p or DailyPoint(day=d.isoformat(), expenses_cents=0, income_cents=0))
            d += timedelta(days=1)
        return points

    def monthly_series(self, months: int = 6) -> list[tuple[str, int]]:
        today = date.today()
        result: list[tuple[str, int]] = []
        for offset in range(months - 1, -1, -1):
            year = today.year
            month = today.month - offset
            while month <= 0:
                month += 12
                year -= 1
            start = date(year, month, 1)
            if month == 12:
                end = date(year + 1, 1, 1)
            else:
                end = date(year, month + 1, 1)
            start_iso = datetime.combine(start, datetime.min.time()).isoformat()
            end_iso = datetime.combine(end, datetime.min.time()).isoformat()
            totals = self.ledger.totals(start=start_iso, end=end_iso)
            result.append((month_label(start)[:3].upper() + f" {str(year)[2:]}", totals.expenses_cents))
        return result

    def reports(self) -> ReportsData:
        month_start, month_end = month_bounds()
        today = date.today()
        previous_end = date(today.year, today.month, 1)
        previous_start = (previous_end - timedelta(days=1)).replace(day=1)
        p_start, p_end = month_bounds(previous_start)
        current = self.ledger.totals(start=month_start, end=month_end)
        previous = self.ledger.totals(start=p_start, end=p_end)
        categories = self.ledger.category_totals(start=month_start, end=month_end)
        daily = self.daily_series(today)
        active_days = len([p for p in daily if p.expenses_cents > 0])
        weeks: list[tuple[str, int]] = []
        # Últimas 8 semanas completas + semana actual.
        for offset in range(7, -1, -1):
            ref = today - timedelta(weeks=offset)
            monday = ref - timedelta(days=ref.weekday())
            sunday = monday + timedelta(days=7)
            start_iso = datetime.combine(monday, datetime.min.time()).isoformat()
            end_iso = datetime.combine(sunday, datetime.min.time()).isoformat()
            t = self.ledger.totals(start=start_iso, end=end_iso)
            label = "Esta sem." if offset == 0 else f"{monday.day} {monday.strftime('%b').lower()}"
            weeks.append((label, t.expenses_cents))
        month_views = self.ledger.transaction_views(
            start=month_start, end=month_end, kind="expense", limit=1
        )
        biggest = month_views[0] if month_views else None
        # biggest por monto, no por fecha
        all_month = self.ledger.transaction_views(start=month_start, end=month_end, limit=2000)
        expenses = [v for v in all_month if v.transaction.amount_cents < 0]
        if expenses:
            biggest = max(expenses, key=lambda v: abs(v.transaction.amount_cents))
        budget = self.settings.daily_budget_cents
        days_in_month = (month_end_dt(month_end).date() - today.replace(day=1)).days
        projected = current.expenses_cents
        if today.day > 0:
            projected = int(current.expenses_cents / today.day * max(1, days_in_month))
        return ReportsData(
            month=current,
            previous_month=previous,
            categories=categories,
            daily=daily,
            weekly=weeks,
            monthly=self.monthly_series(6),
            biggest_expense=biggest,
            average_day_cents=current.expenses_cents // max(1, active_days),
            active_days=active_days,
            projected_month_cents=projected,
            budget_daily_cents=budget,
            accounts=self.ledger.accounts(),
        )

    def widget_snapshot(self, *, hidden: bool = False) -> WidgetSnapshot:
        data = self.load()
        top = data.top_category
        last = [
            {
                "description": v.transaction.description,
                "amount_cents": v.transaction.amount_cents,
                "category": v.category.name if v.category else "Otros",
                "color": v.category.color if v.category else "#89948D",
                "at": v.transaction.occurred_at,
            }
            for v in self.ledger.recent_views(4)
        ]
        from ..core.dates import now_iso

        return WidgetSnapshot(
            generated_at=now_iso(),
            currency_symbol=self.settings.symbol,
            spent_today_cents=data.today.expenses_cents,
            income_today_cents=data.today.income_cents,
            daily_budget_cents=data.budget_cents,
            remaining_cents=data.remaining_cents,
            month_spent_cents=data.month.expenses_cents,
            top_category=top.category.name if top and top.category else "Sin gastos",
            top_category_cents=top.total_cents if top else 0,
            last_transactions=last,
            hidden=hidden or self.settings.get_bool("widget_privacy", False),
            name=self.settings.user_name or "Sapardobank",
        )


def month_end_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def weekday_letter(day: str) -> str:
    d = datetime.fromisoformat(day).date()
    return ["L", "M", "M", "J", "V", "S", "D"][d.weekday()]


def weekday_short(day: str) -> str:
    d = datetime.fromisoformat(day).date()
    return ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"][d.weekday()]
