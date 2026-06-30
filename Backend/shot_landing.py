from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = str(Path(__file__).parent / "phishguard_landing.png")
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 880, "height": 1000})
    pg.goto("http://localhost:5501/index.html", wait_until="networkidle")
    pg.screenshot(path=OUT, full_page=True)
    print("->", OUT)
    b.close()
