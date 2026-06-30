// ===============================================================
// 🛡️ PhishGuard - Tier 0 heuristics (on-device JS port)
// ===============================================================
// Mirrors Backend/heuristics.py: multilingual scam-intent keywords +
// URL look-alike / punycode / IP / shortener checks, with word-boundary
// matching so short words don't match inside bigger words. Runs in the
// content script, no backend.
//   PhishGuardHeuristics.scoreText(text) -> {risk, score, reasons, structural}
// ===============================================================

(function (root) {
  const URGENCY = [
    "urgent","immediately","act now","last warning","final notice",
    "account suspended","account blocked","within 24 hours","expire",
    "limited time","right now","verify now",
    "turant","abhi","jaldi","antim chetavni","khata band","khata block","samay seema",
    "तुरंत","अभी","जल्दी","खाता बंद","अंतिम चेतावनी","खाता बंद हो",
    "உடனடியாக","உடனே","கணக்கு முடக்கம்",
  ];
  const CREDENTIAL = [
    "otp","one time password","cvv","pin","password","verify your account",
    "confirm your identity","kyc","update kyc","re-kyc","aadhaar","pan card",
    "net banking","debit card","credit card","card number","expiry date",
    "login to verify","verify your details","share the code",
    "otp batao","otp share","pin batao","kyc update karo","verify karo",
    "details bhejo","code bhejo",
    "ओटीपी","पासवर्ड","केवाईसी","आधार","सत्यापित करें","कोड भेजो",
    "கடவுச்சொல்","சரிபார்க்கவும்",
  ];
  const REWARD = [
    "you have won","congratulations","lottery","prize","lucky winner",
    "cash reward","claim now","free gift","cashback","refund pending",
    "you are selected","redeem","bonus credited",
    "aap jeet gaye","inaam","lottery laga","badhai ho","paisa wapas","free gift","claim karo",
    "बधाई हो","इनाम","लॉटरी","आप जीत गए","मुफ्त उपहार",
    "வாழ்த்துக்கள்","பரிசு","லாட்டரி",
  ];
  const THREAT = [
    "legal action","fir","police case","arrest","fine","penalty","court",
    "blocked permanently","account will be closed",
    "kanooni karyavahi","police","jurmana","girftar",
    "कानूनी कार्रवाई","गिरफ्तार","जुर्माना",
  ];
  const AUTHORITY = [
    "income tax","rbi","reserve bank","sbi","hdfc","icici","paytm","phonepe",
    "google pay","amazon","flipkart","courier","fedex","customs",
    "electricity board","tneb","gas agency","bank manager","support team",
    "customer care","helpdesk",
  ];
  const ACTION = [
    "click here","click the link","click below","tap here","open link",
    "download app","install","scan qr","scan the qr",
    "yaha click karo","link kholo","qr scan karo",
    "यहां क्लिक करें","लिंक खोलें",
  ];

  const SUSPICIOUS_TLDS = new Set(["zip","mov","xyz","top","click","link","gq","tk","ml","cf","ga","work","rest","country","kim","loan","men","date"]);
  const URL_SHORTENERS = new Set(["bit.ly","tinyurl.com","t.co","goo.gl","ow.ly","is.gd","buff.ly","rebrand.ly","cutt.ly","shorturl.at","rb.gy","tiny.cc"]);
  const BRAND_LABELS = ["sbi","hdfc","icici","axis","kotak","paytm","phonepe","gpay","amazon","flipkart","netflix","instagram","facebook","whatsapp","income-tax","incometax","rbi","irctc","epfo","uidai","aadhaar"];
  const CONFUSABLE = new Set(["а","е","о","р","с","х","у","ѕ","і","ј","ԁ","ɡ","α","ο","ρ","ν"]);

  const URL_RE = /\b((?:https?:\/\/|www\.)[^\s<>"')]+)/gi;
  const IP_RE = /^\d{1,3}(\.\d{1,3}){3}$/;
  const PHONE_RE = /(?:\+?\d[\d\s-]{8,}\d)/;

  // Word-boundary matcher. Unicode-aware so it works for Devanagari/Tamil too
  // (a "word char" = letter, number, mark/matra, or underscore).
  const WORD = "[\\p{L}\\p{N}\\p{M}_]";
  const _cache = new Map();
  function termRe(term) {
    let re = _cache.get(term);
    if (!re) {
      const esc = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      re = new RegExp("(?<!" + WORD + ")" + esc + "(?!" + WORD + ")", "u");
      _cache.set(term, re);
    }
    return re;
  }
  function countHits(low, terms) {
    return terms.filter((t) => termRe(t).test(low));
  }

  function hostOf(url) {
    let u = url;
    if (!u.includes("://")) u = "http://" + u;
    try { return (new URL(u).hostname || "").toLowerCase(); } catch { return ""; }
  }

  function analyzeUrls(text) {
    const signals = [];
    const seen = new Set();
    const matches = (text || "").matchAll(URL_RE);
    for (const m of matches) {
      const url = m[1];
      const host = hostOf(url);
      if (!host || seen.has(host)) continue;
      seen.add(host);

      if (host.includes("xn--")) signals.push(["Punycode/IDN domain: " + host, 35]);
      if ([...host].some((ch) => CONFUSABLE.has(ch))) signals.push(["Look-alike (confusable) characters in: " + host, 35]);
      if (IP_RE.test(host)) signals.push(["Link points to a raw IP address: " + host, 30]);
      if (URL_SHORTENERS.has(host)) signals.push(["Shortened/obscured link: " + host, 20]);

      const tld = host.includes(".") ? host.split(".").pop() : "";
      if (SUSPICIOUS_TLDS.has(tld)) signals.push(["High-risk top-level domain: ." + tld, 18]);

      for (const brand of BRAND_LABELS) {
        if (host.includes(brand) && !host.endsWith(brand + ".com") && !host.endsWith(brand + ".in") && !host.endsWith(brand + ".co.in")) {
          signals.push(["Brand look-alike domain ('" + brand + "' in " + host + ")", 28]);
          break;
        }
      }
      if ((host.match(/\./g) || []).length >= 4) signals.push(["Excessive subdomains: " + host, 12]);
      if (url.split("//").pop().split("/")[0].includes("@")) signals.push(["Link uses '@' to disguise its real host", 25]);
    }
    return signals;
  }

  function analyzeText(text) {
    const signals = [];
    const low = (text || "").toLowerCase();
    const cats = [
      ["Urgency/pressure language", URGENCY, 14, 28],
      ["Credential/OTP/KYC request", CREDENTIAL, 22, 45],
      ["Reward/lottery bait", REWARD, 16, 32],
      ["Threat/intimidation", THREAT, 16, 30],
      ["Action lure (click/scan/install)", ACTION, 12, 24],
    ];
    let fired = 0;
    for (const [label, terms, base, cap] of cats) {
      const hits = countHits(low, terms);
      if (hits.length) {
        fired++;
        const weight = Math.min(base + (hits.length - 1) * 6, cap);
        signals.push([label + ": " + hits.slice(0, 3).join(", "), weight]);
      }
    }
    const auth = countHits(low, AUTHORITY);
    if (auth.length && fired) signals.push(["Impersonates a known brand/authority: " + auth[0], 18]);

    const hasCred = CREDENTIAL.some((t) => low.includes(t));
    const hasUrg = URGENCY.some((t) => low.includes(t));
    if (hasCred && hasUrg) signals.push(["Combo: asks for credentials AND creates urgency", 20]);
    if (PHONE_RE.test(low) && (hasUrg || hasCred)) signals.push(["Contact number paired with urgency/credential cues", 10]);
    return signals;
  }

  const HIGH = 45, MEDIUM = 22;

  function scoreText(text) {
    const urlSignals = analyzeUrls(text);
    const signals = urlSignals.concat(analyzeText(text));
    const total = signals.reduce((s, x) => s + x[1], 0);
    const structural = urlSignals.some((x) => x[1] >= 25);
    const risk = total >= HIGH ? "high" : total >= MEDIUM ? "medium" : "low";
    const sorted = signals.slice().sort((a, b) => b[1] - a[1]);
    const reasons = [];
    for (const [reason] of sorted) if (!reasons.includes(reason)) reasons.push(reason);
    return { risk, score: total, reasons, structural };
  }

  const api = { scoreText, HIGH_THRESHOLD: HIGH };
  root.PhishGuardHeuristics = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
