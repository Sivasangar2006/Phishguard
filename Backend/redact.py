# ===============================================================
# 🛡️ PhishGuard - PII redaction
# ===============================================================
# Strips personally-identifiable data from a message BEFORE it is
# stored (for the dataset) or sent to any LLM (the future Tier 2).
# This is the privacy guarantee: scam-relevant structure (urgency
# words, URLs, brand names) is preserved, but victim PII is removed.
#
# Deterministic regex only -- no data leaves the process. Order
# matters: more specific patterns run before greedier ones.
#
#   redact("482913 is your OTP, call 9876543210")
#     -> ("<OTP> is your OTP, call <PHONE>", {"OTP": 1, "PHONE": 1})
# ===============================================================

from __future__ import annotations

import re

# Each rule: (placeholder, compiled-regex). Applied top to bottom.
_RULES: list[tuple[str, re.Pattern]] = [
    # UPI handle (name@bank) -- before email, which would also match.
    ("UPI", re.compile(
        r"\b[\w.\-]{2,}@(?:oksbi|okaxis|okhdfcbank|okicici|ybl|ibl|apl|paytm|upi|axl|sbi)\b",
        re.IGNORECASE)),
    # Email.
    ("EMAIL", re.compile(r"\b[\w.+\-]+@[\w\-]+\.[\w.\-]+\b")),
    # PAN card: ABCDE1234F.
    ("PAN", re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")),
    # Card number: 13-16 digits, optionally space/hyphen grouped.
    ("CARD", re.compile(r"\b(?:\d[ \-]?){13,16}\b")),
    # Aadhaar: 12 digits, optionally 4-4-4 grouped.
    ("AADHAAR", re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")),
    # Masked account: a run of X/x then digits (XXXXX3917).
    ("ACCOUNT", re.compile(r"\b[Xx]{3,}\d{2,}\b")),
    # Indian mobile: optional +91, then 6-9 followed by 9 digits.
    ("PHONE", re.compile(r"(?:\+?91[\-\s]?)?\b[6-9]\d{9}\b")),
    # Classic 6-digit OTP standalone.
    ("OTP", re.compile(r"\b\d{6}\b")),
    # Any remaining long digit run (>=9) -- account-number-ish.
    ("NUMBER", re.compile(r"\b\d{9,}\b")),
]

# Personal name right after a greeting (best-effort, no NER):
# "Dear Rahul," / "Hi Priya" / "प्रिय राहुल" / "வணக்கம் ராஜா".
_NAME_RULE = (
    "NAME",
    re.compile(
        r"(?P<greet>\b(?:dear|hi|hello|hey|प्रिय|प्रिया|வணக்கம்|హాయ్)\s+)"
        r"(?P<name>[A-Z][a-z]+|[ऀ-ॿ]{2,}|[஀-௿]{2,})",
        re.IGNORECASE),
)


def redact(text: str) -> tuple[str, dict[str, int]]:
    """Return (redacted_text, counts). counts maps placeholder -> hits."""
    if not text:
        return text, {}

    counts: dict[str, int] = {}
    out = text

    # Greeting-name first so the name isn't eaten by other rules.
    def _name_sub(m: re.Match) -> str:
        counts["NAME"] = counts.get("NAME", 0) + 1
        return f"{m.group('greet')}<NAME>"

    out = _NAME_RULE[1].sub(_name_sub, out)

    for label, pattern in _RULES:
        def _sub(m: re.Match, _label=label) -> str:
            counts[_label] = counts.get(_label, 0) + 1
            return f"<{_label}>"
        out = pattern.sub(_sub, out)

    return out, counts


def redaction_summary(counts: dict[str, int]) -> str:
    if not counts:
        return "no PII found"
    return ", ".join(f"{v}x {k}" for k, v in sorted(counts.items()))
