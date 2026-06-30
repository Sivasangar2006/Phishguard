# Renders the extension popup and screenshots it. Backend must be on :8000.
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = str(Path(__file__).parent / "phishguard_popup.png")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 300, "height": 220})
    page.goto("http://localhost:5500/popup.html", wait_until="networkidle")
    page.wait_for_selector(".dot.ok, .dot.bad", timeout=8000)
    page.wait_for_timeout(300)
    page.screenshot(path=OUT)
    status = page.eval_on_selector("#status", "e => e.textContent")
    print(f"popup status: {status!r} -> {OUT}")
    browser.close()
