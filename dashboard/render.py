"""One self-contained HTML page: KPI tiles, charts (Chart.js from CDN) and tables."""

import html
import json
from datetime import date, datetime

from .metrics import change

CHART_JS = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"


def money(x: float) -> str:
    return f"-${abs(x):,.0f}" if x < 0 else f"${x:,.0f}"


def pct(x: float | None) -> str:
    return "–" if x is None else f"{x:.1%}"


def _month_name(key: str, fmt: str = "%b") -> str:
    year, month = key.split("-")
    return date(int(year), int(month), 1).strftime(fmt)


def _delta(new: float, old: float | None) -> str:
    c = change(new, old) if old is not None else None
    if c is None:
        return ""
    cls = "up" if c >= 0 else "down"
    return f'<span class="{cls}">{"▲" if c >= 0 else "▼"} {abs(c):.0%}</span>'


def _tiles(s: dict) -> str:
    t, months = s["total"], list(s["months"].values())
    last, prev = (months[-1], months[-2]) if len(months) > 1 else (None, None)
    compare = ""
    if last:
        keys = list(s["months"])
        compare = f"{_month_name(keys[-1])} vs {_month_name(keys[-2])}"
    tiles = [
        ("Net sales", money(t["sales"]), "sales", "after refunds"),
        ("Net profit", money(t["profit"]), "profit", "after goods, shipping, fees, ads"),
        ("Profit margin", pct(t["margin"]), "margin", "net profit / net sales"),
        ("Orders", f"{t['orders']:,.0f}", "orders", f"{t['refunds'] / t['gross']:.1%} refunded"),
        ("Average order", f"${t['aov']:,.2f}", "aov", "net sales / paid orders"),
        ("Ad spend", money(t["ads"]), "ads", f"blended ROAS {t['roas']:.1f}x" if t["roas"] else ""),
    ]
    out = []
    for label, value, key, note in tiles:
        delta = _delta(last[key], prev[key]) if last else ""
        sub = f"{delta} <span class=muted>{compare}</span>" if delta else ""
        out.append(
            f'<div class="tile"><div class="label">{label}</div><div class="value">{value}</div>'
            f'<div class="sub">{sub}</div><div class="note">{note}</div></div>'
        )
    return "\n".join(out)


def _channel_rows(s: dict) -> str:
    rows = []
    for name, c in s["channels"].items():
        roas = f"{c['roas']:.1f}x" if c["roas"] else "no ads"
        neg = ' class="neg"' if c["profit"] < 0 else ""
        rows.append(
            f"<tr><td>{html.escape(name)}</td><td>{c['orders']:,.0f}</td>"
            f"<td>{money(c['sales'])}</td><td>{money(c['ads'])}</td><td>{roas}</td>"
            f"<td{neg}>{money(c['profit'])}</td><td>{pct(c['margin'])}</td></tr>"
        )
    return "\n".join(rows)


def _product_rows(s: dict) -> str:
    return "\n".join(
        f"<tr><td>{html.escape(p['name'])}</td><td>{p['units']:,.0f}</td>"
        f"<td>{money(p['sales'])}</td><td>{money(p['gross_profit'])}</td>"
        f"<td>{p['gross_profit'] / p['sales']:.0%}</td></tr>"
        for p in s["products"]
        if p["sales"]
    )


def chart_data(s: dict) -> dict:
    t = s["total"]
    return {
        "months": [_month_name(k) for k in s["months"]],
        "sales": [round(m["sales"], 2) for m in s["months"].values()],
        "ads": [round(m["ads"], 2) for m in s["months"].values()],
        "profit": [round(m["profit"], 2) for m in s["months"].values()],
        "channels": list(s["channels"]),
        "channelProfit": [round(c["profit"], 2) for c in s["channels"].values()],
        "split": {
            "Goods": round(t["goods"], 2),
            "Ads": round(t["ads"], 2),
            "Shipping": round(t["shipping"], 2),
            "Payment fees": round(t["fees"], 2),
            "Net profit": round(max(t["profit"], 0), 2),
        },
    }


def render(s: dict, title: str = "Sales & Profit Dashboard", note: str = "") -> str:
    start, end = s["period"]
    fees = s["fees"]
    replacements = {
        "__TITLE__": html.escape(title),
        "__PERIOD__": f"{start:%d %b %Y} – {end:%d %b %Y}",
        "__NOTE__": html.escape(note),
        "__TILES__": _tiles(s),
        "__CHANNEL_ROWS__": _channel_rows(s),
        "__PRODUCT_ROWS__": _product_rows(s),
        "__FEES__": f"{fees.rate:.1%} + ${fees.fixed:.2f} per order",
        "__CREATED__": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "__CHART_JS__": CHART_JS,
        "__DATA__": json.dumps(chart_data(s)),
    }
    page = TEMPLATE
    for key, value in replacements.items():
        page = page.replace(key, value)
    return page


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root {
    --bg: #f4f6fa; --card: #ffffff; --text: #18202f; --muted: #667085; --line: #e4e8ef;
    --sales: #2f6fed; --profit: #12a150; --ads: #f29a1f; --neg: #d92d20;
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--text);
         font: 15px/1.45 "Segoe UI", system-ui, -apple-system, sans-serif; }
  .wrap { max-width: 1200px; margin: 0 auto; padding: 24px 16px 40px; }
  header { display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px 16px;
           margin-bottom: 18px; }
  h1 { font-size: 26px; margin: 0; }
  .period { color: var(--muted); }
  .badge { background: #fff4e5; color: #9a5b00; border: 1px solid #f5d39c; border-radius: 99px;
           padding: 2px 10px; font-size: 13px; }
  .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }
  .tile, .card { background: var(--card); border: 1px solid var(--line); border-radius: 12px; }
  .tile { padding: 14px 16px; }
  .label { color: var(--muted); font-size: 13px; }
  .value { font-size: 26px; font-weight: 700; margin: 2px 0; font-variant-numeric: tabular-nums; }
  .sub { font-size: 13px; min-height: 18px; }
  .note { color: var(--muted); font-size: 12px; }
  .up { color: var(--profit); font-weight: 600; }
  .down { color: var(--neg); font-weight: 600; }
  .muted { color: var(--muted); }
  .grid { display: grid; grid-template-columns: 2fr 1fr; gap: 12px; margin-top: 12px; }
  .grid.even { grid-template-columns: 1fr 1fr; }
  .card { padding: 16px; min-width: 0; }
  h2 { font-size: 16px; margin: 0 0 10px; }
  .chart { position: relative; height: 290px; }
  .table-wrap { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
  th, td { padding: 7px 8px; border-bottom: 1px solid var(--line); text-align: right;
           white-space: nowrap; }
  th:first-child, td:first-child { text-align: left; }
  th { color: var(--muted); font-weight: 600; font-size: 13px; }
  td.neg { color: var(--neg); }
  footer { color: var(--muted); font-size: 13px; margin-top: 16px; }
  @media (max-width: 860px) { .grid, .grid.even { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>__TITLE__</h1>
    <span class="period">__PERIOD__</span>
    <span class="badge">__NOTE__</span>
  </header>

  <section class="tiles">
__TILES__
  </section>

  <section class="grid">
    <div class="card">
      <h2>Net sales, ad spend and net profit by month</h2>
      <div class="chart"><canvas id="monthly"></canvas></div>
    </div>
    <div class="card">
      <h2>Where each dollar of sales goes</h2>
      <div class="chart"><canvas id="split"></canvas></div>
    </div>
  </section>

  <section class="grid even">
    <div class="card">
      <h2>Profit by channel (after ad spend)</h2>
      <div class="chart"><canvas id="channels"></canvas></div>
    </div>
    <div class="card table-wrap">
      <h2>Channels</h2>
      <table>
        <tr><th>Channel</th><th>Orders</th><th>Net sales</th><th>Ad spend</th><th>ROAS</th>
            <th>Profit</th><th>Margin</th></tr>
__CHANNEL_ROWS__
      </table>
    </div>
  </section>

  <section class="card table-wrap" style="margin-top:12px">
    <h2>Products by gross profit (before ads)</h2>
    <table>
      <tr><th>Product</th><th>Units</th><th>Net sales</th><th>Gross profit</th><th>Margin</th></tr>
__PRODUCT_ROWS__
    </table>
  </section>

  <footer>
    Payment fees: __FEES__. Refunded orders: no sales and no goods cost; shipping and fees stay.
    Built __CREATED__ with Python from orders.csv + ad_spend.csv.
  </footer>
</div>

<script src="__CHART_JS__"></script>
<script>
const D = __DATA__;
const css = getComputedStyle(document.documentElement);
const C = (name) => css.getPropertyValue(name).trim();
const usd = (v) => (v < 0 ? "-$" : "$") + Math.abs(Math.round(v)).toLocaleString("en-US");
Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
Chart.defaults.color = C("--muted");
Chart.defaults.maintainAspectRatio = false;
const money = { callbacks: { label: (c) => c.dataset.label + ": " + usd(c.parsed.y ?? c.parsed) } };

new Chart(document.getElementById("monthly"), {
  data: {
    labels: D.months,
    datasets: [
      { type: "bar", label: "Net sales", data: D.sales, backgroundColor: C("--sales") },
      { type: "bar", label: "Ad spend", data: D.ads, backgroundColor: C("--ads") },
      { type: "bar", label: "Net profit", data: D.profit,
        backgroundColor: D.profit.map((v) => v < 0 ? C("--neg") : C("--profit")) },
    ],
  },
  options: { plugins: { tooltip: money },
             scales: { y: { ticks: { callback: usd }, grid: { color: C("--line") } },
                       x: { grid: { display: false } } } },
});

const splitColors = ["#8a94a6", C("--ads"), "#b5bcc9", "#d6dae2", C("--profit")];
const splitTotal = Object.values(D.split).reduce((a, b) => a + b, 0);
new Chart(document.getElementById("split"), {
  type: "doughnut",
  data: { labels: Object.keys(D.split),
          datasets: [{ data: Object.values(D.split), backgroundColor: splitColors,
                       borderColor: C("--card"), borderWidth: 2 }] },
  options: { cutout: "58%",
             plugins: { legend: { position: "bottom", labels: { boxWidth: 12 } },
                        tooltip: { callbacks: { label: (c) => c.label + ": " + usd(c.parsed)
                          + " (" + (100 * c.parsed / splitTotal).toFixed(1) + "%)" } } } },
});

new Chart(document.getElementById("channels"), {
  type: "bar",
  data: { labels: D.channels,
          datasets: [{ label: "Profit", data: D.channelProfit,
                       backgroundColor: D.channelProfit.map(
                         (v) => v < 0 ? C("--neg") : C("--profit")) }] },
  options: { indexAxis: "y",
             plugins: { legend: { display: false },
                        tooltip: { callbacks: { label: (c) => "Profit: " + usd(c.parsed.x) } } },
             scales: { x: { ticks: { callback: usd }, grid: { color: C("--line") } },
                       y: { grid: { display: false } } } },
});
</script>
</body>
</html>
"""
