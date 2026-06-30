# PhishGuard Backend

FastAPI service that powers the extension's phishing scan. It exposes the
`/scan` endpoint that [`Extension/content.js`](../Extension/content.js) already
calls, and **fuses two tiers** behind that one contract:

- **Tier 0 — heuristics** ([`heuristics.py`](heuristics.py)): fast,
  deterministic, language-agnostic URL + text rules. Always on; produces the
  human-readable reasons.
- **Tier 1 — ML** ([`classifier.py`](classifier.py)): the trained
  [`Model/`](../Model) classifier, loaded if present. Catches scams the rules
  miss. Degrades gracefully — if the artifact/sklearn is absent, the backend
  runs Tier 0 alone and `/health` reports `tier1: unavailable`.

The two are combined by an **ML-led weighted blend** with a structural override
(`fuse()` in `main.py`): the model can move the verdict both ways, but
high-precision URL signals (punycode, raw IP, look-alike domain) still force the
risk up.

## Files

| File                | Purpose                                              |
|---------------------|------------------------------------------------------|
| `main.py`           | FastAPI app, `/scan` `/report` `/health`, Tier 0+1 fusion |
| `heuristics.py`     | Tier 0 scoring engine (URL + multilingual text)      |
| `classifier.py`     | Tier 1 loader: `Model/classifier.joblib` → P(phish)  |
| `redact.py`         | PII redaction (OTP, account, card, phone, email, …)  |
| `test_heuristics.py`| Sanity checks across EN / Hindi / Devanagari / Tamil |
| `test_redact.py`    | Redaction sanity checks                              |
| `requirements.txt`  | Python dependencies                                  |

To enable Tier 1, train the model once: `cd ../Model && python train.py`.

## Run (Windows, Python 3.10)

```bash
cd Backend
py -3.10 -m pip install -r requirements.txt
py -3.10 -m uvicorn main:app --reload --port 8000
```

> Use Python 3.10–3.12. Python 3.14 has no prebuilt `pydantic-core` wheel yet
> and pip will try (and fail) to compile it from source.

Then load the unpacked extension (`Extension/`) in Chrome via
`chrome://extensions` → Developer mode → Load unpacked.

## API

### `POST /scan`

```json
// request
{ "text": "Aapka SBI khata band ho jayega, OTP batao", "source": "WhatsApp", "url": "https://sbi-verify.xyz" }

// response
{
  "risk": "high",
  "reasons": ["Credential/OTP/KYC request: ...", "ML classifier: 95% phishing probability"],
  "score": 150,
  "ml_prob": 0.95
}
```

`risk` is `high` | `medium` | `low`, derived from the **fused** Tier 0 + Tier 1
confidence (not the raw `score` alone). `ml_prob` is the Tier 1 phishing
probability, or `null` when the model isn't loaded. `score` is the Tier 0
heuristic total, kept for transparency.

### `POST /report`

Crowdsourced reporting — the real-data pipeline. The message is **PII-redacted
on the server before anything is written to disk**, so the stored corpus is
privacy-safe by construction.

```json
// request
{ "text": "Dear Rahul, share OTP 482913, call 9876543210", "source": "WhatsApp", "url": "http://sbi-verify.xyz", "user_label": "phish" }

// response
{ "ok": true, "redaction": "1x NAME, 1x OTP, 1x PHONE", "redacted_preview": "Dear <NAME>, share OTP <OTP>, call <PHONE>" }
```

Records append to `Backend/data/reports.jsonl` (git-ignored). Only redacted text
and the URL's **host** (never the full URL) are stored, with an auto-triage
verdict. In the extension, **Alt+Click** a flagged message to report it.

### `GET /health`

```json
{ "status": "ok", "service": "phishguard", "tier0": "heuristics", "tier1": "ready" }
```

`tier1` is `ready` when the model loaded, or `unavailable (...)` otherwise.

## Test

```bash
cd Backend
py -3.10 test_heuristics.py
```
