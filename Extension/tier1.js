// ===============================================================
// 🛡️ PhishGuard - Tier 1 on-device scorer
// ===============================================================
// Replicates the trained scikit-learn pipeline (char_wb TF-IDF +
// LogisticRegression) in pure JS, so detection runs in the browser with
// NO backend. The math is identical to sklearn's; verified numerically by
// Model/parity_test (JS proba == Python predict_proba within tolerance).
//
// Usage:  const t1 = PhishGuardTier1.makeScorer(modelJson);
//         t1.proba("some message")  ->  0..1 phishing probability
// ===============================================================

(function (root) {
  // char_wb n-grams: pad each whitespace-split word with spaces, take char
  // n-grams that don't cross word boundaries. Mirrors sklearn _char_wb_ngrams.
  function ngramCounts(text, minN, maxN, lowercase) {
    const s = lowercase ? text.toLowerCase() : text;
    const words = s.split(/\s+/).filter(Boolean);
    const counts = new Map();
    for (const word of words) {
      const w = " " + word + " ";
      const L = w.length;
      for (let n = minN; n <= maxN; n++) {
        let offset = 0;
        const first = w.substring(0, n);
        counts.set(first, (counts.get(first) || 0) + 1);
        while (offset + n < L) {
          offset++;
          const g = w.substring(offset, offset + n);
          counts.set(g, (counts.get(g) || 0) + 1);
        }
        // sklearn breaks here for a word shorter than n: it is counted ONCE,
        // not once per larger n. Without this, short words over-count.
        if (offset === 0) break;
      }
    }
    return counts;
  }

  function makeScorer(model) {
    const [minN, maxN] = model.ngram_range;
    const terms = model.terms;
    const sublinear = model.sublinear_tf;
    const lc = model.lowercase;
    const intercept = model.intercept;

    return {
      proba(text) {
        if (!text) return 0;
        const counts = ngramCounts(text, minN, maxN, lc);
        let dot = 0;
        let norm2 = 0;
        for (const [ng, c] of counts) {
          const t = terms[ng];
          if (!t) continue;            // ngram not in vocab -> not a feature
          const idf = t[0];
          const coef = t[1];
          const tf = sublinear ? 1 + Math.log(c) : c;
          const tfidf = tf * idf;
          norm2 += tfidf * tfidf;      // for L2 normalization
          dot += tfidf * coef;         // unnormalized decision contribution
        }
        const norm = Math.sqrt(norm2) || 1;
        const decision = dot / norm + intercept;   // L2-normalized tfidf dot coef
        return 1 / (1 + Math.exp(-decision));       // sigmoid -> P(phishing)
      },
    };
  }

  const api = { makeScorer };
  root.PhishGuardTier1 = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
