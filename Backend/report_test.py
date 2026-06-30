# Verifies the literal content.js Alt+Click reporting path writes a
# redacted record via /report. Backend must be running on :8000.
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CONTENT_JS = Path(__file__).parent.parent / "Extension" / "content.js"
REPORTS = Path(__file__).parent / "data" / "reports.jsonl"
URL = "http://localhost:5500/extension-test.html"


def line_count(p: Path) -> int:
    return len(p.read_text(encoding="utf-8").splitlines()) if p.exists() else 0


before = line_count(REPORTS)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(URL, wait_until="load")
    page.add_script_tag(path=str(CONTENT_JS))
    page.evaluate("window.injectMessages()")
    # Wait for at least one flagged (reportable) node to exist.
    page.wait_for_selector("[data-pg-report]", timeout=15000)
    # Alt+Click the first flagged message.
    page.click("[data-pg-report]", modifiers=["Alt"])
    page.wait_for_timeout(800)
    browser.close()

after = line_count(REPORTS)
print(f"reports.jsonl: {before} -> {after}  ({'OK +1' if after == before + 1 else 'UNEXPECTED'})")
if after > before:
    last = REPORTS.read_text(encoding="utf-8").splitlines()[-1]
    print("newest record:", last)
