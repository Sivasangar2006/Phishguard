from playwright.sync_api import sync_playwright

OUT = "phishguard_render.png"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 820, "height": 1400})
    page.goto("http://localhost:5500/", wait_until="networkidle")
    # Wait until every card has a verdict badge rendered (scans resolved).
    page.wait_for_selector(".badge", timeout=10000)
    page.wait_for_timeout(800)  # let the last few settle
    page.screenshot(path=OUT, full_page=True)
    n = page.eval_on_selector_all(".badge", "els => els.length")
    print(f"rendered {n} verdict badges -> {OUT}")
    browser.close()
