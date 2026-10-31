"""Profit numbers from an orders export and an ad spend export.

Per order: net sales = quantity x price (0 if refunded); costs = goods (0 if refunded, the item
comes back), shipping and payment fee (both stay even after a refund). Ads are subtracted per
day and channel, so channels without ads (Organic, Email) carry no ad cost.
"""

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass
class Order:
    order_id: str
    day: date
    channel: str
    product: str
    quantity: int
    unit_price: float
    unit_cost: float
    shipping: float
    refunded: bool


@dataclass
class Fees:
    rate: float = 0.029  # card payment fee, share of the order amount
    fixed: float = 0.30  # per order


def _read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_orders(path: Path) -> list[Order]:
    return [
        Order(
            order_id=r["order_id"],
            day=date.fromisoformat(r["date"]),
            channel=r["channel"],
            product=r["product"],
            quantity=int(r["quantity"]),
            unit_price=float(r["unit_price"]),
            unit_cost=float(r["unit_cost"]),
            shipping=float(r["shipping_cost"]),
            refunded=r["refunded"].strip().lower() in {"yes", "true", "1"},
        )
        for r in _read(path)
    ]


def load_ads(path: Path) -> list[tuple[date, str, float]]:
    return [(date.fromisoformat(r["date"]), r["channel"], float(r["spend"])) for r in _read(path)]


def _empty() -> dict:
    keys = [
        "orders",
        "paid_orders",
        "units",
        "gross",
        "refunds",
        "sales",
        "goods",
        "shipping",
        "fees",
        "ads",
    ]
    return dict.fromkeys(keys, 0.0)


def _finish(t: dict) -> dict:
    """Add profit, margin, AOV and ROAS to a totals dict."""
    t["gross_profit"] = t["sales"] - t["goods"] - t["shipping"] - t["fees"]
    t["profit"] = t["gross_profit"] - t["ads"]
    t["margin"] = t["profit"] / t["sales"] if t["sales"] else 0.0
    t["aov"] = t["sales"] / t["paid_orders"] if t["paid_orders"] else 0.0
    t["roas"] = t["sales"] / t["ads"] if t["ads"] else None
    return t


def summarize(orders: list[Order], ads: list[tuple[date, str, float]], fees: Fees) -> dict:
    total, months, channels, products = _empty(), {}, {}, {}
    for o in orders:
        amount = o.quantity * o.unit_price
        row = {
            "orders": 1,
            "paid_orders": 0 if o.refunded else 1,
            "units": o.quantity,
            "gross": amount,
            "refunds": amount if o.refunded else 0.0,
            "sales": 0.0 if o.refunded else amount,
            "goods": 0.0 if o.refunded else o.quantity * o.unit_cost,
            "shipping": o.shipping,
            "fees": amount * fees.rate + fees.fixed,
        }
        month = o.day.strftime("%Y-%m")
        for bucket in (
            total,
            months.setdefault(month, _empty()),
            channels.setdefault(o.channel, _empty()),
            products.setdefault(o.product, _empty()),
        ):
            for key, value in row.items():
                bucket[key] += value
    for day, channel, spend in ads:
        total["ads"] += spend
        months.setdefault(day.strftime("%Y-%m"), _empty())["ads"] += spend
        channels.setdefault(channel, _empty())["ads"] += spend

    days = sorted({o.day for o in orders} | {d for d, _, _ in ads})
    by_product = sorted(
        ({"name": k, **_finish(v)} for k, v in products.items()),
        key=lambda p: p["gross_profit"],
        reverse=True,
    )
    return {
        "period": (days[0], days[-1]) if days else None,
        "total": _finish(total),
        "months": {k: _finish(v) for k, v in sorted(months.items())},
        "channels": dict(
            sorted(
                ((k, _finish(v)) for k, v in channels.items()),
                key=lambda kv: kv[1]["profit"],
                reverse=True,
            )
        ),
        "products": by_product,
        "fees": fees,
    }


def change(new: float, old: float) -> float | None:
    """Relative change, None when there is nothing to compare with."""
    return (new - old) / abs(old) if old else None
