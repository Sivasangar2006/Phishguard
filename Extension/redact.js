// ===============================================================
// 🛡️ PhishGuard - PII redaction (on-device JS port of redact.py)
// ===============================================================
// Strips PII before a reported message is stored locally, so even
// crowdsourced reports never keep raw sensitive data — no backend needed.
//   PhishGuardRedact.redact(text) -> { text: "<redacted>", counts: {...} }
// ===============================================================

(function (root) {
  // Order matters: specific patterns before greedier ones.
  const RULES = [
    ["UPI", /\b[\w.\-]{2,}@(?:oksbi|okaxis|okhdfcbank|okicici|ybl|ibl|apl|paytm|upi|axl|sbi)\b/gi],
    ["EMAIL", /\b[\w.+\-]+@[\w\-]+\.[\w.\-]+\b/g],
    ["PAN", /\b[A-Z]{5}[0-9]{4}[A-Z]\b/g],
    ["CARD", /\b(?:\d[ \-]?){13,16}\b/g],
    ["AADHAAR", /\b\d{4}\s?\d{4}\s?\d{4}\b/g],
    ["ACCOUNT", /\b[Xx]{3,}\d{2,}\b/g],
    ["PHONE", /(?:\+?91[\-\s]?)?\b[6-9]\d{9}\b/g],
    ["OTP", /\b\d{6}\b/g],
    ["NUMBER", /\b\d{9,}\b/g],
  ];
  // Personal name right after a greeting (best-effort, no NER).
  const NAME_RE = /\b(dear|hi|hello|hey|प्रिय|प्रिया|வணக்கம்|హాయ్)\s+([A-Z][a-z]+|[ऀ-ॿ]{2,}|[஀-௿]{2,})/giu;

  function redact(text) {
    if (!text) return { text: text || "", counts: {} };
    const counts = {};
    let out = text.replace(NAME_RE, (_m, greet) => {
      counts.NAME = (counts.NAME || 0) + 1;
      return greet + " <NAME>";
    });
    for (const [label, re] of RULES) {
      out = out.replace(re, () => {
        counts[label] = (counts[label] || 0) + 1;
        return "<" + label + ">";
      });
    }
    return { text: out, counts };
  }

  function summary(counts) {
    const keys = Object.keys(counts);
    if (!keys.length) return "no PII found";
    return keys.sort().map((k) => counts[k] + "x " + k).join(", ");
  }

  const api = { redact, summary };
  root.PhishGuardRedact = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
