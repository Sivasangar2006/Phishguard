# Verifies the "Analyze with AI" button: loads the extension scripts, flags a
# scam, clicks the button, and confirms the local LLM verdict appears.
# Requires Ollama running with qwen2.5:3b.
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

EXT = Path(__file__).parent.parent / "Extension"
SCRIPTS = ["model-data.js", "tier1.js", "heuristics.js", "redact.js", "detector.js", "llm.js", "content.js"]
OUT = str(Path(__file__).parent / "phishguard_llm_button.png")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 820, "height": 700})
    errs = []
    page.on("console", lambda m: errs.append("[console] " + m.text) if m.type in ("error", "warning") else None)
    page.on("requestfailed", lambda r: errs.append("[reqfail] " + r.url + " :: " + str(r.failure)))
    page.goto("http://localhost:5500/extension-test.html", wait_until="load")
    for s in SCRIPTS:
        page.add_script_tag(path=str(EXT / s))
    page.evaluate("window.injectMessages()")

    page.wait_for_selector("#phishguard-banner button", timeout=15000)
    page.wait_for_timeout(2000)   # let all messages finish streaming so the banner is stable
    print("banner settled; clicking AI button…")
    page.click("#phishguard-banner button")

    # Poll up to ~45s for the AI line (populated on success OR error).
    banner = ""
    for _ in range(45):
        page.wait_for_timeout(1000)
        banner = page.eval_on_selector("#phishguard-banner", "e => e.innerText.replace(/\\n/g,' | ')")
        if "AI (" in banner or "unavailable" in banner:
            break
    page.screenshot(path=OUT)
    print("banner text:", banner)
    print("--- console/network issues ---")
    for e in errs[-8:]:
        print(" ", e[:200])
    browser.close()
