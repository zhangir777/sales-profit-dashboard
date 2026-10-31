from datetime import date

import pytest

from dashboard.cli import main
from dashboard.metrics import Fees, Order, change, summarize
from dashboard.render import money, render


def order(day, channel="Organic", qty=1, price=100.0, cost=40.0, refunded=False):
    return Order("#1", day, channel, "Mug", qty, price, cost, 5.0, refunded)


ORDERS = [
    order(date(2026, 9, 10), "Instagram Ads", qty=2),  # 200 sales
    order(date(2026, 10, 1), "Organic"),  # 100 sales
    order(date(2026, 10, 2), "Organic", refunded=True),  # refunded: 0 sales, 0 goods
]
ADS = [(date(2026, 9, 10), "Instagram Ads", 50.0), (date(2026, 10, 1), "Instagram Ads", 30.0)]


def test_totals_and_profit():
    t = summarize(ORDERS, ADS, Fees(0.03, 0.30))["total"]
    assert t["orders"] == 3 and t["paid_orders"] == 2
    assert t["gross"] == 400 and t["refunds"] == 100 and t["sales"] == 300
    assert t["goods"] == 120  # 2*40 + 40, refunded item comes back
    assert t["shipping"] == 15  # shipping stays after a refund
    assert t["fees"] == pytest.approx(12 + 0.9)  # 3% of 400 + 3 x 0.30
    assert t["ads"] == 80
    assert t["profit"] == pytest.approx(300 - 120 - 15 - 12.9 - 80)
    assert t["aov"] == 150
    assert t["roas"] == pytest.approx(300 / 80)


def test_months_and_channels():
    s = summarize(ORDERS, ADS, Fees(0, 0))
    assert list(s["months"]) == ["2026-09", "2026-10"]
    assert s["months"]["2026-10"]["ads"] == 30
    assert s["channels"]["Organic"]["roas"] is None  # no ads, no ROAS
    assert s["channels"]["Instagram Ads"]["profit"] == pytest.approx(200 - 80 - 5 - 80)
    assert s["period"] == (date(2026, 9, 10), date(2026, 10, 2))


def test_ads_without_orders_still_count():
    s = summarize(ORDERS, [*ADS, (date(2026, 10, 5), "TikTok Ads", 20.0)], Fees(0, 0))
    assert s["channels"]["TikTok Ads"]["profit"] == -20


def test_change_and_money():
    assert change(120, 100) == pytest.approx(0.2)
    assert change(5, 0) is None
    assert money(-1234.4) == "-$1,234" and money(99.6) == "$100"


def test_render_has_numbers_and_no_placeholders():
    page = render(summarize(ORDERS, ADS, Fees()), "Shop <test>", "Demo data")
    assert "Shop &lt;test&gt;" in page and "__" not in page.replace("__proto__", "")
    assert "$300" in page and "Oct vs Sep" in page and "no ads" in page


def test_cli_on_samples(tmp_path, capsys):
    out = tmp_path / "d.html"
    main(["samples/orders.csv", "samples/ad_spend.csv", "--out", str(out)])
    assert out.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")
    assert "net profit" in capsys.readouterr().out
