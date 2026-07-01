# 🛡️ PhishGuard

**On-device-first phishing & scam detection for Indian vernacular languages.**

Most phishing detectors are English-first. India gets scammed in 20+ languages —
Hindi, Tamil, Telugu, Bengali, and code-mixed "Hinglish". PhishGuard is a browser
extension that flags scam messages **in the languages people actually get scammed
in**, doing the work locally and escalating rarely.

> **Status:** working end-to-end MVP — and detection now runs **fully
> on-device** (no backend). The trained model is exported to JS and runs in the
> browser, so the extension is self-contained and installable. The FastAPI
> service remains as a reference/training implementation. See
> [Roadmap](#roadmap).
>
> **On-device:** the browser detector produces verdicts **identical** to the
> Python backend — verified to ~1e-6 by `Model/parity_test` and
> `Model/detector_parity`. Reports are PII-redacted in-browser and stored in
> `chrome.storage` — nothing leaves the device.

---

## Architecture — a three-tier escalation pipeline

The design principle: **do the smart thing locally, escalate only when needed.**

```
 DOM message (any site)
        │
        ▼
┌───────────────────────────────────────────────┐
│ TIER 0 — Heuristics            (Backend/heuristics.py)
│  URL look-alike / punycode / IP / shorteners   │
│  multilingual scam-intent keywords             │
│  → fast, deterministic, explainable reasons    │
└───────────────┬───────────────────────────────┘
                ▼
┌───────────────────────────────────────────────┐
│ TIER 1 — On-device ML          (Model/ + classifier.py)
│  char-ngram TF-IDF + LogReg (cross-script)     │
│  catches scams with no obvious keywords        │
│  → phishing probability                        │
└───────────────┬───────────────────────────────┘
                ▼
        FUSED risk  (main.py: ML-led blend +
        structural override)  → high / medium / low
                ▼
        content.js paints red / orange / green
```

A future **Tier 2** (a consented, PII-redacted LLM fallback for ambiguous cases)
plugs in behind the same `/scan` contract — the redaction layer
([`Backend/redact.py`](Backend/redact.py)) already exists.

## Repo layout

| Path | What it is |
|------|------------|
| [`Extension/`](Extension/) | the Chrome extension (MV3): `content.js`, `manifest.json` |
| [`Backend/`](Backend/) | FastAPI service: `/scan`, `/report`, fusion, heuristics, redaction |
| [`Model/`](Model/) | Tier 1 dataset, trainer, and trained classifier |
| `Extension/extension-test.html` | local harness that runs the **real** content.js |
| `Extension/index.html` | backend+render demo (no extension needed) |

## Quickstart — just load the extension (no backend)

```
Chrome → chrome://extensions → Developer mode → Load unpacked → select Extension/
```

That's it. Open WhatsApp Web / Gmail and suspicious messages get a colored
underline; **Alt+Click** a flagged message to report it (redacted locally). The
toolbar popup shows on-device status. Nothing needs to run on a server.

### Retraining the model (optional)

The browser uses `Extension/model-data.js`, exported from the trained model. To
retrain on new data and re-export:

```bash
cd Model
pip install -r requirements.txt
python dataset/generate_dataset.py   # build the corpus
python train.py                      # train -> classifier.joblib
python export_model.py               # -> Extension/model-data.js (+ model.json)
```

### Reference backend (optional)

`Backend/` is the original FastAPI implementation of the same detector, kept as a
reference and for server-side experiments. The on-device JS is verified to match
it exactly. Run it with `uvicorn main:app --port 8000` if you want the API.

## How well does it work?

Honest numbers on the **synthetic seed** dataset (1,766 rows, 4 languages).
Real-world will be lower until real data is collected — that's the headline next
step:

| Metric | Value |
|--------|-------|
| Tier 1 F1, **unseen scam type** (category holdout) | **~0.87** ← the meaningful number |
| Tier 1 F1, unseen templates (new phrasing) | ~1.00 — synthetic ceiling |
| Tier 1 F1, random split | ~1.00 — memorization, not skill |
| Tier 0 heuristics F1 (same test set) | ~0.86 |

The honest catch: on an *unseen scam category* the model catches phishing
(recall ≈ 1.0) but over-flags unfamiliar **legit** messages (legit recall ≈
0.46). That false-positive gap is exactly why real data is the priority. The
value of Tier 1 still shows on **heuristic-quiet** scams (no keywords/URLs) the
rules miss. See [`Model/README.md`](Model/README.md) for the methodology.

## Privacy

- Detection runs locally; only message text hits the local backend.
- **Reporting redacts PII server-side before storage** — OTPs, account/card
  numbers, phones, Aadhaar/PAN, emails, UPI IDs, names are stripped; only host
  (not full URL) is kept. See [`Backend/redact.py`](Backend/redact.py).
- Crowdsourced reports (`Backend/data/`) are git-ignored.

## Optional: Analyze with AI (local LLM)

The verdict banner has an **"Analyze with AI"** button that sends the message to a
**local** LLM (via [Ollama](https://ollama.com)) for a reasoned second opinion —
nothing leaves the device. The on-device heuristics + ML stay the *primary*
detector (instant, 0 false positives on the test set); the LLM is an optional,
on-demand explainer.

Setup:
```bash
ollama pull qwen2.5:3b          # ~2 GB, fits alongside a browser
# allow the extension's page origin to reach Ollama, then restart Ollama:
setx OLLAMA_ORIGINS "*"
```
Model is set in [`Extension/llm.js`](Extension/llm.js) (`MODEL`). `qwen2.5:3b`
runs comfortably next to Chrome; `aya-expanse:8b` is more accurate on Indic text
but needs ~6 GB free RAM (it OOMs on a 16 GB machine with a browser open).

**Honest note:** in testing, the small local LLM was *not* more accurate than the
tuned on-device model (qwen2.5:3b: 2/12 false positives, ~6 s/message; the
on-device model: 0/18, instant). So the LLM is a bonus "explain-why" feature, not
a replacement — a good example of measuring before committing to an architecture.

## Roadmap

1. **Real data** — collect & label real vernacular scams (the moat). See the
   detailed [data-collection plan](Model/dataset/COLLECTION_PLAN.md).
2. **Better Tier 1** — fine-tune MuRIL / IndicBERT for true cross-lingual
   transfer; distill → int8 → ONNX Runtime Web to run *in the browser*.
3. **Tier 2** — consented, redacted LLM fallback on ambiguous cases only.
4. More languages (Telugu, Bengali, Marathi, Kannada…) and scam types.

## License

See [LICENSE](LICENSE).

---

*PhishGuard is a defensive security tool. The synthetic scam templates exist only
to train the detector.*
