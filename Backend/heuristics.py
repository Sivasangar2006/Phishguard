# ===============================================================
# 🛡️ PhishGuard - Tier 0 Heuristics Engine
# ===============================================================
# Language-agnostic, on-the-server phishing scoring.
# No ML, no external calls -> fast and deterministic.
#
# Scams in India arrive in Devanagari/Tamil/Telugu script AND in
# Romanized ("Hinglish") form, so the keyword banks cover both.
#
# Each signal contributes a weighted score. The total maps to a
# risk band that the extension's content.js already understands:
#   high  -> red banner
#   medium-> orange banner
#   low   -> green/clear
# ===============================================================

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse


# ---------------------------------------------------------------
# 1. Signal definition
# ---------------------------------------------------------------

@dataclass
class Signal:
    """One fired heuristic: a human-readable reason + its weight."""
    reason: str
    weight: int


@dataclass
class ScanResult:
    risk: str                       # "high" | "medium" | "low"
    score: int
    reasons: list[str] = field(default_factory=list)
    signals: list[Signal] = field(default_factory=list)
    # True when a HIGH-PRECISION structural URL signal fired (punycode, raw
    # IP, confusable chars, brand look-alike, '@'-trick). These rarely
    # false-positive, so fusion lets them override the ML upward.
    structural: bool = False


# ---------------------------------------------------------------
# 2. Keyword banks  (lowercased matching)
# ---------------------------------------------------------------
# Grouped by intent. Romanized + native-script variants live
# together so one scam phrase fires regardless of how it's typed.

URGENCY_TERMS = [
    # English
    "urgent", "immediately", "act now", "last warning", "final notice",
    "account suspended", "account blocked", "within 24 hours", "expire",
    "limited time", "right now", "verify now",
    # Romanized Hindi
    "turant", "abhi", "jaldi", "antim chetavni", "khata band",
    "khata block", "samay seema",
    # Devanagari
    "तुरंत", "अभी", "जल्दी", "खाता बंद", "अंतिम चेतावनी", "खाता बंद हो",
    # Tamil
    "உடனடியாக", "உடனே", "கணக்கு முடக்கம்",
]

CREDENTIAL_TERMS = [
    # English
    "otp", "one time password", "cvv", "pin", "password", "verify your account",
    "confirm your identity", "kyc", "update kyc", "re-kyc", "aadhaar", "pan card",
    "net banking", "debit card", "credit card", "card number", "expiry date",
    "login to verify", "verify your details", "share the code",
    # Romanized
    "otp batao", "otp share", "pin batao", "kyc update karo", "verify karo",
    "details bhejo", "code bhejo",
    # Devanagari
    "ओटीपी", "पासवर्ड", "केवाईसी", "आधार", "सत्यापित करें", "कोड भेजो",
    # Tamil
    "கடவுச்சொல்", "சரிபார்க்கவும்",
]

REWARD_BAIT_TERMS = [
    # English
    "you have won", "congratulations", "lottery", "prize", "lucky winner",
    "cash reward", "claim now", "free gift", "cashback", "refund pending",
    "you are selected", "redeem", "bonus credited",
    # Romanized
    "aap jeet gaye", "inaam", "lottery laga", "badhai ho", "paisa wapas",
    "free gift", "claim karo",
    # Devanagari
    "बधाई हो", "इनाम", "लॉटरी", "आप जीत गए", "मुफ्त उपहार",
    # Tamil
    "வாழ்த்துக்கள்", "பரிசு", "லாட்டரி",
]

THREAT_TERMS = [
    "legal action", "fir", "police case", "arrest", "fine", "penalty",
    "court", "blocked permanently", "account will be closed",
    "kanooni karyavahi", "police", "jurmana", "girftar",
    "कानूनी कार्रवाई", "गिरफ्तार", "जुर्माना",
]

AUTHORITY_IMPERSONATION = [
    "income tax", "rbi", "reserve bank", "sbi", "hdfc", "icici", "paytm",
    "phonepe", "google pay", "amazon", "flipkart", "courier", "fedex",
    "customs", "electricity board", "tneb", "gas agency", "bank manager",
    "support team", "customer care", "helpdesk",
]

ACTION_LURES = [
    "click here", "click the link", "click below", "tap here", "open link",
    "download app", "install", "scan qr", "scan the qr",
    "yaha click karo", "link kholo", "qr scan karo",
    "यहां क्लिक करें", "लिंक खोलें",
]


# ---------------------------------------------------------------
# 3. URL heuristics
# ---------------------------------------------------------------

URL_REGEX = re.compile(r"\b((?:https?://|www\.)[^\s<>\"')]+)", re.IGNORECASE)
IP_HOST_REGEX = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")

# Free / abused TLDs heavily used by phishing kits.
SUSPICIOUS_TLDS = {
    "zip", "mov", "xyz", "top", "click", "link", "gq", "tk", "ml", "cf", "ga",
    "work", "rest", "country", "kim", "loan", "men", "date",
}

URL_SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "buff.ly",
    "rebrand.ly", "cutt.ly", "shorturl.at", "rb.gy", "tiny.cc",
}

# Brand keywords that, when they appear in the *domain label* of a
# non-official-looking host, suggest a look-alike (e.g. "sbi-verify.xyz").
BRAND_LABELS = [
    "sbi", "hdfc", "icici", "axis", "kotak", "paytm", "phonepe", "gpay",
    "amazon", "flipkart", "netflix", "instagram", "facebook", "whatsapp",
    "income-tax", "incometax", "rbi", "irctc", "epfo", "uidai", "aadhaar",
]

# Confusable characters used in homograph attacks (Cyrillic/Greek look-alikes).
CONFUSABLE_CHARS = {
    "а", "е", "о", "р", "с", "х", "у",   # Cyrillic
    "ѕ", "і", "ј", "ԁ", "ɡ",
    "α", "ο", "ρ", "ν",                  # Greek
}


def _extract_urls(text: str) -> list[str]:
    return URL_REGEX.findall(text or "")


def _host_of(url: str) -> str:
    if "://" not in url:
        url = "http://" + url
    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


def analyze_urls(text: str) -> list[Signal]:
    signals: list[Signal] = []
    seen_hosts: set[str] = set()

    for url in _extract_urls(text):
        host = _host_of(url)
        if not host or host in seen_hosts:
            continue
        seen_hosts.add(host)

        # Punycode / IDN homograph
        if "xn--" in host:
            signals.append(Signal(f"Punycode/IDN domain: {host}", 35))
        if any(ch in CONFUSABLE_CHARS for ch in host):
            signals.append(Signal(f"Look-alike (confusable) characters in: {host}", 35))

        # Raw IP address as host
        if IP_HOST_REGEX.match(host):
            signals.append(Signal(f"Link points to a raw IP address: {host}", 30))

        # URL shortener (hides true destination)
        if host in URL_SHORTENERS:
            signals.append(Signal(f"Shortened/obscured link: {host}", 20))

        # Suspicious TLD
        tld = host.rsplit(".", 1)[-1] if "." in host else ""
        if tld in SUSPICIOUS_TLDS:
            signals.append(Signal(f"High-risk top-level domain: .{tld}", 18))

        # Brand look-alike: brand name sits in a label but host isn't the
        # brand's real domain (cheap check: brand appears with extra hyphen/word).
        label = host.split(".")[0]
        for brand in BRAND_LABELS:
            if brand in host and not host.endswith(f"{brand}.com") \
                    and not host.endswith(f"{brand}.in") \
                    and not host.endswith(f"{brand}.co.in"):
                signals.append(
                    Signal(f"Brand look-alike domain ('{brand}' in {host})", 28)
                )
                break

        # Excessive subdomains (e.g. secure.sbi.account.login.evil.com)
        if host.count(".") >= 4:
            signals.append(Signal(f"Excessive subdomains: {host}", 12))

        # "@" trick in the raw URL (credentials-in-URL redirect)
        if "@" in url.split("//")[-1].split("/")[0]:
            signals.append(Signal("Link uses '@' to disguise its real host", 25))

    return signals


# ---------------------------------------------------------------
# 4. Text heuristics
# ---------------------------------------------------------------

_TERM_CACHE: dict[str, re.Pattern] = {}


def _term_pattern(term: str) -> re.Pattern:
    # Match the term only at word-ish boundaries, so short words like "fir",
    # "pin", "otp" don't match INSIDE bigger words ("confirmed", "shipping").
    # Lookarounds (not \b) so it also works for multi-word phrases and the
    # Devanagari/Tamil terms.
    pat = _TERM_CACHE.get(term)
    if pat is None:
        pat = re.compile(r"(?<!\w)" + re.escape(term) + r"(?!\w)")
        _TERM_CACHE[term] = pat
    return pat


def _count_hits(haystack: str, terms: list[str]) -> list[str]:
    return [t for t in terms if _term_pattern(t).search(haystack)]


def analyze_text(text: str) -> list[Signal]:
    signals: list[Signal] = []
    low = (text or "").lower()

    # Each intent category. Weight scales a little with how many distinct
    # phrases fired, capped so one category can't dominate alone.
    categories = [
        ("Urgency/pressure language", URGENCY_TERMS, 14, 28),
        ("Credential/OTP/KYC request", CREDENTIAL_TERMS, 22, 45),
        ("Reward/lottery bait", REWARD_BAIT_TERMS, 16, 32),
        ("Threat/intimidation", THREAT_TERMS, 16, 30),
        ("Action lure (click/scan/install)", ACTION_LURES, 12, 24),
    ]

    fired_intents = 0
    for label, terms, base, cap in categories:
        hits = _count_hits(low, terms)
        if hits:
            fired_intents += 1
            weight = min(base + (len(hits) - 1) * 6, cap)
            sample = ", ".join(hits[:3])
            signals.append(Signal(f"{label}: {sample}", weight))

    # Authority impersonation only matters alongside another scam intent;
    # "amazon" alone in a normal chat shouldn't fire.
    auth_hits = _count_hits(low, AUTHORITY_IMPERSONATION)
    if auth_hits and fired_intents:
        signals.append(
            Signal(f"Impersonates a known brand/authority: {auth_hits[0]}", 18)
        )

    # Classic combo: credential request + urgency in the same message.
    has_cred = any(t in low for t in CREDENTIAL_TERMS)
    has_urgency = any(t in low for t in URGENCY_TERMS)
    if has_cred and has_urgency:
        signals.append(Signal("Combo: asks for credentials AND creates urgency", 20))

    # Phone number to "call immediately" is a common vishing setup. Require a
    # real scam intent (urgency or credential ask) -- a number next to a brand
    # name alone is just a normal bank/transaction notice, not vishing.
    if re.search(r"(?:\+?\d[\d\s-]{8,}\d)", low) and (has_urgency or has_cred):
        signals.append(Signal("Contact number paired with urgency/credential cues", 10))

    return signals


# ---------------------------------------------------------------
# 5. Scoring + band mapping
# ---------------------------------------------------------------

HIGH_THRESHOLD = 45
MEDIUM_THRESHOLD = 22


def score_text(text: str) -> ScanResult:
    url_signals = analyze_urls(text)
    signals = url_signals + analyze_text(text)
    total = sum(s.weight for s in signals)

    # High-precision URL signals (weight >= 25) are near-certain phishing
    # markers; weaker ones (shortener, suspicious TLD, extra subdomains) are not.
    structural = any(s.weight >= 25 for s in url_signals)

    if total >= HIGH_THRESHOLD:
        risk = "high"
    elif total >= MEDIUM_THRESHOLD:
        risk = "medium"
    else:
        risk = "low"

    # Dedupe reasons while preserving order, strongest first.
    signals_sorted = sorted(signals, key=lambda s: s.weight, reverse=True)
    reasons: list[str] = []
    for s in signals_sorted:
        if s.reason not in reasons:
            reasons.append(s.reason)

    return ScanResult(risk=risk, score=total, reasons=reasons,
                      signals=signals_sorted, structural=structural)
