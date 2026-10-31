"""Screenshots of docs/index.html for the README (desktop and phone width).

Needs Playwright with Chromium (not a project dependency), e.g. from the scraping portfolio venv:
python scripts/screenshot.py
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "docs/index.html").as_uri()
OUT = ROOT / "docs/screenshots"

with sync_playwright() as p:
    browser = p.chromium.launch()
    for name, size in (("dashboard.png", (1280, 900)), ("mobile.png", (390, 844))):
        page = browser.new_page(viewport={"width": size[0], "height": size[1]})
        errors = []
        page.on("pageerror", lambda e, errors=errors: errors.append(str(e)))
        page.goto(PAGE, wait_until="networkidle")
        page.wait_for_timeout(1200)  # chart animations
        page.screenshot(path=OUT / name, full_page=True)
        width = page.evaluate("document.documentElement.scrollWidth")
        print(name, "errors:", errors or "none", "| page width:", width, "| viewport:", size[0])
    browser.close()
