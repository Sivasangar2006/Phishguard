# ===============================================================
# 🛡️ PhishGuard - FastAPI backend
# ===============================================================
# Serves the /scan endpoint that Extension/content.js already calls.
#
# Contract (matches content.js):
#   POST /scan
#     request : { "text": str, "source": str?, "url": str? }
#     response: { "risk": "high"|"medium"|"low",
#                 "reasons": [str, ...],
#                 "score": int }
#
# Run:
#   pip install -r requirements.txt
#   uvicorn main:app --reload --port 8000
# ===============================================================

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import classifier
from heuristics import HIGH_THRESHOLD, score_text
from redact import redact, redaction_summary

# Crowdsourced reports are appended here as JSONL (redacted text only).
DATA_DIR = Path(__file__).parent / "data"
REPORTS_FILE = DATA_DIR / "reports.jsonl"

app = FastAPI(
    title="PhishGuard",
    description="On-device-first vernacular phishing detection backend.",
    version="0.1.0",
)

# Content scripts issue fetch() with the *page's* origin (e.g.
# https://web.whatsapp.com), so the backend must allow cross-origin
# requests. Wide open is fine for local dev; tighten before any deploy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------
# Models
# ---------------------------------------------------------------

class ScanRequest(BaseModel):
    text: str = Field(..., description="Extracted DOM text to evaluate.")
    source: str | None = Field(None, description="Site name (WhatsApp, Gmail, ...).")
    url: str | None = Field(None, description="Page URL the text came from.")


class ScanResponse(BaseModel):
    risk: str
    reasons: list[str]
    score: int
    ml_prob: float | None = None   # Tier 1 phishing probability, if available


class ReportRequest(BaseModel):
    text: str = Field(..., description="The message the user is reporting.")
    source: str | None = Field(None, description="Site name (WhatsApp, Gmail, ...).")
    url: str | None = Field(None, description="Page URL the text came from.")
    user_label: str | None = Field(
        None, description='User verdict: "phish" or "legit" (optional).')


class ReportResponse(BaseModel):
    ok: bool
    redaction: str          # human summary of what PII was stripped
    redacted_preview: str   # the stored, PII-free text


# ---------------------------------------------------------------
# Fusion: Tier 0 (heuristics) + Tier 1 (ML) -> one risk band
# ---------------------------------------------------------------
# The ML model is a trained discriminator that can vote BOTH ways, so we
# use an ML-led weighted blend rather than a noisy-OR (which can only push
# risk up and would let a keyword false-positive survive a confident-legit
# ML verdict). High-precision structural URL signals (punycode, raw IP,
# look-alike domain, '@'-trick) still override upward -- those almost never
# false-positive.

HIGH_BAND = 0.70
MEDIUM_BAND = 0.40
W_ML = 0.65          # trust the trained model more than raw keyword counts
W_HEURISTIC = 0.35
STRUCTURAL_FLOOR = 0.75   # a look-alike/punycode/IP URL alone is near-certain


def fuse(result, ml_prob: float | None) -> tuple[str, float]:
    h_conf = min(result.score / HIGH_THRESHOLD, 1.0)
    if ml_prob is None:
        fused = h_conf                      # Tier 0 only (model not loaded)
    else:
        fused = W_ML * ml_prob + W_HEURISTIC * h_conf

    if result.structural:
        fused = max(fused, STRUCTURAL_FLOOR)

    if fused >= HIGH_BAND:
        return "high", fused
    if fused >= MEDIUM_BAND:
        return "medium", fused
    return "low", fused


# ---------------------------------------------------------------
# Routes
# ---------------------------------------------------------------

@app.get("/")
def root() -> dict:
    return {
        "service": "phishguard",
        "status": "running",
        "endpoints": {
            "POST /scan": "score text for phishing risk",
            "GET /health": "liveness check",
            "GET /docs": "interactive API explorer",
        },
    }


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "phishguard",
        "tier0": "heuristics",
        "tier1": classifier.status(),
    }


@app.post("/scan", response_model=ScanResponse)
def scan(req: ScanRequest) -> ScanResponse:
    # The page URL is itself a strong signal, so fold it into the scan.
    payload = req.text or ""
    if req.url:
        payload = f"{payload}\n{req.url}"

    # Tier 0 — heuristics (always on; produces explainable reasons).
    result = score_text(payload)

    # Tier 1 — ML classifier (None if the model artifact isn't loaded).
    ml_prob = classifier.predict_proba(payload)

    risk, fused = fuse(result, ml_prob)

    reasons = list(result.reasons)
    if ml_prob is not None:
        # Surface the ML view, especially when it drove a heuristic-quiet case.
        reasons.append(f"ML classifier: {round(ml_prob * 100)}% phishing probability")

    # Cap reasons returned to the UI; content.js joins these into a tooltip.
    return ScanResponse(
        risk=risk,
        reasons=reasons[:6],
        score=result.score,
        ml_prob=round(ml_prob, 3) if ml_prob is not None else None,
    )


@app.post("/report", response_model=ReportResponse)
def report(req: ReportRequest) -> ReportResponse:
    """Crowdsourced reporting -- the real-data pipeline. The message is
    PII-redacted ON THE SERVER before anything is written to disk, so the
    stored corpus is privacy-safe by construction. Only redacted text and
    the URL's host (not the full URL) are persisted."""
    redacted, counts = redact(req.text or "")

    # The current model's verdict, useful as a weak/auto label to triage.
    result = score_text(redacted)
    ml_prob = classifier.predict_proba(redacted)
    risk, _ = fuse(result, ml_prob)

    host = ""
    if req.url:
        try:
            host = urlparse(req.url).hostname or ""
        except ValueError:
            host = ""

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "text": redacted,                 # PII-free
        "source": req.source,
        "url_host": host,                 # host only, never the full URL
        "user_label": req.user_label,
        "auto_risk": risk,
        "auto_ml_prob": round(ml_prob, 3) if ml_prob is not None else None,
        "pii_removed": counts,
    }

    DATA_DIR.mkdir(exist_ok=True)
    with REPORTS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return ReportResponse(
        ok=True,
        redaction=redaction_summary(counts),
        redacted_preview=redacted,
    )
