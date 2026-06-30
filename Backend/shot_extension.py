# Drives the LITERAL Extension/content.js against the test page and
# screenshots the borders it paints. Proves hop #4: the real content script
# (not a proxy) decorates DOM nodes from the live /scan backend.
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CONTENT_JS = Path(__file__).parent.parent / "Extension" / "content.js"
URL = "http://localhost:5500/extension-test.html"
OUT = str(Path(__file__).parent / "phishguard_extension_render.png")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 820, "height": 1300})
    logs = []
    page.on("console", lambda m: logs.append(m.text))

    page.goto(URL, wait_until="load")
    # Inject the REAL content script. It sees hostname 'localhost', matches the
    # SITE_CONFIG entry, and starts its MutationObserver immediately.
    page.add_script_tag(path=str(CONTENT_JS))
    # Now stream in the planted messages so the observer catches them live.
    page.evaluate("window.injectMessages()")

    # Wait for the SCAN to resolve, not a fixed timer. content.js sets a 2px
    # solid-orange "scanning" border before fetch; a resolved node is red
    # (high), 3px orange (medium), or green (low). Wait until all 6 are final.
    page.wait_for_function(
        """() => {
            const els = [...document.querySelectorAll('.msg')];
            if (els.length < 6) return false;
            return els.every(e => {
                const cs = getComputedStyle(e);
                const c = cs.borderBottomColor, w = cs.borderBottomWidth;
                const red = c.includes('255, 0, 0');
                const green = c.includes('0, 128, 0');
                const orange3 = c.includes('165') && w === '3px';
                return red || green || orange3;   // final, not 2px-orange scanning
            });
        }""",
        timeout=15000,
    )
    page.screenshot(path=OUT, full_page=True)

    # Ground truth: read the computed border each node actually got.
    rows = page.eval_on_selector_all(".msg", """els => els.map(e => {
        const cs = getComputedStyle(e);
        const label = e.parentElement.querySelector('.label')?.textContent || '';
        return { label, color: cs.borderBottomColor, width: cs.borderBottomWidth };
    })""")

    def band(color: str) -> str:
        c = color.replace(" ", "")
        if "255,0,0" in c or c == "red":
            return "RED  (high)"
        if "255,165,0" in c or "orange" in c:
            return "ORANGE (med)"
        if "0,128,0" in c or "green" in c:
            return "GREEN (low)"
        return f"none/other ({color})"

    print(f"content.js decorated {len(rows)} .msg nodes -> {OUT}\n")
    for r in rows:
        print(f"  {r['label'][:34]:34s} | width {r['width']:>4} | {band(r['color'])}")
    browser.close()
