# Builds README demo.gif: drives the real extension on demo.html, captures
# frames as messages arrive + get flagged + AI-analyzed, assembles a GIF.
# Requires Ollama running with qwen2.5:3b (for the final AI frame).
import io
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

EXT = Path(__file__).parent.parent / "Extension"
SCRIPTS = ["model-data.js", "tier1.js", "heuristics.js", "redact.js", "detector.js", "llm.js", "content.js"]
OUT_DIR = Path(__file__).parent.parent / "docs"
OUT_DIR.mkdir(exist_ok=True)
OUT = str(OUT_DIR / "demo.gif")

frames = []  # (PIL.Image, duration_ms)


def snap(page, dur):
    png = page.screenshot()
    frames.append((Image.open(io.BytesIO(png)).convert("RGB"), dur))


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 760, "height": 600}, device_scale_factor=1)
    page.goto("http://localhost:5500/demo.html", wait_until="load")
    for s in SCRIPTS:
        page.add_script_tag(path=str(EXT / s))
    page.wait_for_timeout(400)
    snap(page, 700)                                   # empty chat

    page.evaluate("window.pushMsg(0)")                # legit: lunch
    page.wait_for_timeout(1100); snap(page, 1100)
    page.evaluate("window.pushMsg(1)")                # legit: amazon
    page.wait_for_timeout(1100); snap(page, 1100)

    page.evaluate("window.pushMsg(2)")                # phishing: SBI KYC
    page.wait_for_selector("#phishguard-banner button", timeout=15000)
    page.wait_for_timeout(400); snap(page, 1800)      # red banner + flagged msg

    page.click("#phishguard-banner button")           # Analyze with AI
    page.wait_for_timeout(400); snap(page, 1300)      # "Analyzing…"
    page.wait_for_function(
        "() => (document.querySelector('#phishguard-banner')?.innerText || '').includes('AI (')",
        timeout=90000)
    page.wait_for_timeout(400); snap(page, 3000)      # AI verdict
    snap(page, 2600)                                  # hold on final
    browser.close()

# Assemble GIF (downscale a bit to keep the file small).
imgs, durs = [], []
for im, d in frames:
    im = im.resize((int(im.width * 0.82), int(im.height * 0.82)))
    imgs.append(im.convert("P", palette=Image.ADAPTIVE, colors=128))
    durs.append(d)
imgs[0].save(OUT, save_all=True, append_images=imgs[1:], duration=durs, loop=0, optimize=True, disposal=2)
size_kb = Path(OUT).stat().st_size / 1024
print(f"wrote {OUT}  ({len(imgs)} frames, {size_kb:.0f} KB)")
