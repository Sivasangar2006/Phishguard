# 🛡️ PhishGuard

**On-device-first phishing & scam detection for Indian vernacular languages.**

Most phishing detectors are English-first. India gets scammed in 20+ languages —
Hindi, Tamil, Telugu, Bengali, and code-mixed "Hinglish". PhishGuard is a browser
extension that flags scam messages **in the languages people actually get scammed
in**, doing the work locally and escalating rarely.

> **Status:** working end-to-end MVP. Tier 0 (heuristics) + Tier 1 (ML) fused
> behind one API, a Chrome extension that decorates suspicious messages in real
> time, a synthetic seed dataset + trained classifier, and a privacy-safe
> crowdsourced reporting pipeline. See [Roadmap](#roadmap) for what's next.

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

## Quickstart

```bash
# 1. Backend (Python 3.10–3.12)
cd Backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000

# 2. Train the Tier 1 model (enables ML; backend runs Tier-0-only without it)
cd ../Model
pip install -r requirements.txt
python dataset/generate_dataset.py
python train.py

# 3. Load the extension
#    Chrome → chrome://extensions → Developer mode → Load unpacked → select Extension/
```

Open WhatsApp Web / Gmail and suspicious messages get a colored underline.
`http://localhost:8000/health` shows tier status; `http://localhost:8000/docs`
is the interactive API.

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
