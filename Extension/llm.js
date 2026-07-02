// ===============================================================
// 🛡️ PhishGuard - optional local-LLM analysis (Ollama)
// ===============================================================
// On-demand "second opinion": sends ONE message to a local Ollama model
// and returns a reasoned verdict. This is NOT the primary detector (the
// on-device heuristics+ML are), just a deeper explanation when the user
// clicks "Analyze with AI".
//
// Requires: Ollama running locally with the model below.
//   MODEL: qwen2.5:3b — a compact multilingual CHAT model (~2 GB) that fits
//   alongside a browser and emits clean JSON verdicts. Larger 8B models
//   (aya-expanse, Foundation-Sec) were evaluated but rejected: they need ~6 GB
//   free RAM (OOM with a browser open on a 16 GB machine), and Foundation-Sec
//   is a base/completion model that doesn't follow instructions.
// For use on real sites, Ollama must allow the page origin:
//   set OLLAMA_ORIGINS=*  and restart Ollama.
// ===============================================================

(function (root) {
  const OLLAMA = "http://localhost:11434/api/chat";
  const MODEL = "qwen2.5:3b";

  const SYSTEM =
    "You detect phishing/scam messages in English and Indian languages " +
    "(Hindi, Tamil, Bengali, etc.), including romanized/code-mixed text.\n\n" +
    "KEY RULE: a message is PHISHING only if it REQUESTS something dangerous " +
    "FROM the reader (OTP, password, PIN, CVV, money, click a link to " +
    "'verify/update') or THREATENS them. A message that merely INFORMS the " +
    "reader is LEGITIMATE, even if it mentions OTP, payment, bill, or money.\n" +
    "CRITICAL OTP RULE: a message that TELLS you a code ('Your OTP is 123456', " +
    "'123456 is your verification code') is ALWAYS legitimate. It is phishing " +
    "ONLY if it ASKS you to share/send/tell your OTP.\n" +
    "Examples: 'Thanks for your payment of Rs 499' -> legitimate; " +
    "'Pay Rs 999 fee to release your parcel: link' -> phishing; " +
    "'तुरंत KYC update करें वरना खाता बंद' -> phishing.\n" +
    'Respond ONLY as JSON: {"verdict":"phishing"|"legitimate",' +
    '"confidence":0.0-1.0,"reason":"<=12 words"}.';

  async function analyze(text) {
    const res = await fetch(OLLAMA, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: MODEL,
        messages: [{ role: "system", content: SYSTEM }, { role: "user", content: text }],
        stream: false,
        format: "json",
        options: { temperature: 0, num_ctx: 1024 },
      }),
    });
    if (!res.ok) throw new Error("Ollama returned " + res.status);
    const data = await res.json();
    return JSON.parse(data.message.content);   // {verdict, confidence, reason}
  }

  root.PhishGuardLLM = { analyze, MODEL };
  if (typeof module !== "undefined" && module.exports) module.exports = root.PhishGuardLLM;
})(typeof window !== "undefined" ? window : globalThis);
