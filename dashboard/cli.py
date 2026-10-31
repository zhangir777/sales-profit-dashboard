"""uv run build-dashboard samples/orders.csv samples/ad_spend.csv --out docs/index.html"""

import argparse
from pathlib import Path

from .metrics import Fees, load_ads, load_orders, summarize
from .render import money, pct, render


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Orders + ad spend exports -> HTML profit dashboard")
    p.add_argument("orders", type=Path, help="orders CSV")
    p.add_argument("ads", type=Path, help="ad spend CSV (date, channel, spend)")
    p.add_argument("--out", type=Path, default=Path("out/dashboard.html"))
    p.add_argument("--title", default="Sales & Profit Dashboard")
    p.add_argument("--note", default="", help="small badge next to the title")
    p.add_argument("--fee-rate", type=float, default=0.029, help="payment fee share, 0.029 = 2.9%%")
    p.add_argument("--fee-fixed", type=float, default=0.30, help="payment fee per order")
    a = p.parse_args(argv)

    orders = load_orders(a.orders)
    if not orders:
        p.error(f"no orders in {a.orders}")
    s = summarize(orders, load_ads(a.ads), Fees(a.fee_rate, a.fee_fixed))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(render(s, a.title, a.note), encoding="utf-8")
    t = s["total"]
    print(
        f"{t['orders']:.0f} orders, net sales {money(t['sales'])}, "
        f"net profit {money(t['profit'])} ({pct(t['margin'])}) -> {a.out}"
    )


if __name__ == "__main__":
    main()
