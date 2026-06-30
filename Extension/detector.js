// ===============================================================
// 🛡️ PhishGuard - on-device detector (Tier 0 + Tier 1 fusion)
// ===============================================================
// Combines the JS heuristics and ML scorer with the same fusion as
// Backend/main.py, so the extension produces identical verdicts with NO
// backend. Verified against the server by Model/detector_parity.
//   const d = PhishGuardDetector.make(PHISHGUARD_MODEL);
//   d.detect(text, pageUrl) -> { risk, reasons, score, ml_prob }
// ===============================================================

(function (root) {
  const H = root.PhishGuardHeuristics;
  const T1 = root.PhishGuardTier1;

  // Fusion constants — keep in sync with Backend/main.py.
  const HIGH_BAND = 0.70, MEDIUM_BAND = 0.40;
  const W_ML = 0.65, W_HEURISTIC = 0.35, STRUCTURAL_FLOOR = 0.75;

  function fuse(result, mlProb) {
    const hConf = Math.min(result.score / H.HIGH_THRESHOLD, 1.0);
    let fused = mlProb == null ? hConf : W_ML * mlProb + W_HEURISTIC * hConf;
    if (result.structural) fused = Math.max(fused, STRUCTURAL_FLOOR);
    const risk = fused >= HIGH_BAND ? "high" : fused >= MEDIUM_BAND ? "medium" : "low";
    return { risk, fused };
  }

  function make(model) {
    const scorer = T1.makeScorer(model);
    return {
      detect(text, pageUrl) {
        // The page URL is itself a signal (matches the backend's behavior).
        const payload = pageUrl ? text + "\n" + pageUrl : text;
        const h = H.scoreText(payload);
        const mlProb = scorer.proba(payload);
        const { risk } = fuse(h, mlProb);
        const reasons = h.reasons.slice();
        reasons.push("ML classifier: " + Math.round(mlProb * 100) + "% phishing probability");
        return {
          risk,
          reasons: reasons.slice(0, 6),
          score: h.score,
          ml_prob: Math.round(mlProb * 1000) / 1000,
        };
      },
    };
  }

  const api = { make, fuse };
  root.PhishGuardDetector = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
