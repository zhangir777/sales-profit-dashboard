"""Make the demo exports in samples/: orders.csv and ad_spend.csv (made-up online store, 6 months).

py -m uv run python scripts/make_sample.py
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "samples"
START, END = date(2026, 5, 1), date(2026, 10, 31)
# product: (price, unit cost)
PRODUCTS = {
    "Ceramic Mug": (18.0, 6.5),
    "Coffee Beans 1kg": (32.0, 17.0),
    "Pour-Over Set": (54.0, 24.0),
    "Gift Box": (75.0, 41.0),
    "Tea Sampler": (24.0, 9.0),
    "Travel Tumbler": (29.0, 12.5),
    "Hand Grinder": (89.0, 52.0),
}
# channel: (share of orders, daily ad budget at start)
CHANNELS = {
    "Instagram Ads": (0.30, 75.0),
    "Google Ads": (0.25, 30.0),
    "Organic": (0.30, 0.0),
    "Email": (0.15, 0.0),
}


def main() -> None:
    rng = random.Random(42)
    orders, ads = [], []
    order_no = 1001
    day = START
    while day <= END:
        growth = 1 + (day - START).days / 300
        weekend = 1.25 if day.weekday() >= 5 else 1.0
        for _ in range(round(rng.randint(5, 9) * growth * weekend)):
            channel = rng.choices(list(CHANNELS), [w for w, _ in CHANNELS.values()])[0]
            product = rng.choice(list(PRODUCTS))
            price, cost = PRODUCTS[product]
            qty = rng.choices([1, 2, 3], [0.75, 0.2, 0.05])[0]
            orders.append(
                {
                    "order_id": f"#{order_no}",
                    "date": day.isoformat(),
                    "channel": channel,
                    "product": product,
                    "quantity": qty,
                    "unit_price": f"{price:.2f}",
                    "unit_cost": f"{cost:.2f}",
                    "shipping_cost": f"{rng.choice([4.5, 5.9, 7.2]):.2f}",
                    "refunded": "yes" if rng.random() < 0.04 else "no",
                }
            )
            order_no += 1
        for channel, (_, budget) in CHANNELS.items():
            if budget:
                spend = budget * growth * rng.uniform(0.85, 1.15)
                ads.append({"date": day.isoformat(), "channel": channel, "spend": f"{spend:.2f}"})
        day += timedelta(days=1)

    OUT.mkdir(exist_ok=True)
    for name, rows in (("orders.csv", orders), ("ad_spend.csv", ads)):
        with (OUT / name).open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    print(f"{len(orders)} orders, {len(ads)} ad spend rows -> {OUT}")


if __name__ == "__main__":
    main()
