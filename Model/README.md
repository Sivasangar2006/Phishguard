# PhishGuard — Tier 1 ML Model

The machine-learning tier of the detection pipeline. It complements the Tier 0
heuristics by catching scams that have **no obvious keywords or URLs** — the
cases rules miss.

## What's here

| File                      | Purpose                                                  |
|---------------------------|----------------------------------------------------------|
| `dataset/`                | the vernacular corpus + generator (see its README)       |
| `train.py`                | trains the classifier, prints honest + optimistic metrics |
| `model.py`                | CLI to score a single message                            |
| `classifier.joblib`       | the trained artifact (consumed by the backend)           |
| `requirements.txt`        | ML dependencies                                          |

## The model

**Character n-gram TF-IDF + Logistic Regression.**

Why this, as a baseline:

- **Cross-script by construction.** Character n-grams (`char_wb`, 2–5) need no
  tokenizer or language-ID step, so one model handles Latin, Devanagari, and
  Tamil together.
- **Tiny + portable.** The artifact is ~160 KB and could be ported to run
  on-device in the browser — the eventual Tier 1 goal.
- **Calibrated-ish probability** out of logistic regression, which the backend
  blends with the heuristic confidence.

## Honest metrics (seed dataset, 1,766 rows)

Three evaluations, run every time you train — each strips away a different kind
of leakage:

| Eval | Phishing F1 | What it means |
|------|-------------|---------------|
| Random split (in-distribution) | ~1.00 | memorization — *not* a real number |
| Unseen **templates** (new phrasing) | ~1.00 | synthetic data is too cleanly separable |
| **Unseen categories (new scam type)** | **~0.87** | the meaningful number — see caveat |
| Tier 0 heuristics (same test set) | ~0.86 | rules baseline, for comparison |

**Read the category number carefully.** When held out from a whole scam
*category* it never trained on, the model catches the phishing (recall ≈ 1.0)
but **over-flags unfamiliar *legitimate* messages** (legit recall ≈ 0.46). So
the ~0.87 phishing F1 hides a real false-positive problem on unseen-legit text.

That weakness — and the fact that "unseen templates" saturates at ~1.0 — is the
strongest evidence the **synthetic data has hit its ceiling**. Real, messy,
diverse data is the only way to get a number that reflects field performance.
This is a baseline floor, not a finished model.

## Run it

```bash
pip install -r requirements.txt
python dataset/generate_dataset.py      # build the corpus
python train.py                         # train + evaluate -> classifier.joblib
python model.py "Aapka SBI khata band ho jayega, OTP batao"
```

## Upgrade path (the resume arc)

This baseline is deliberately the *floor*. The documented progression, all
behind the **same `/scan` contract** so nothing downstream changes:

1. **Now:** char-ngram TF-IDF + LogReg, fused with heuristics.
2. **Next:** fine-tune a multilingual encoder built for Indian languages —
   **MuRIL** or **IndicBERT** — on a real (not synthetic) labeled corpus. This
   buys genuine cross-lingual transfer (e.g. learns Tamil scams from Hindi ones).
3. **On-device:** distill that encoder small, quantize to int8, export to
   **ONNX Runtime Web**, and run inference in a Web Worker inside the
   extension — zero data leaves the browser. That is the privacy-preserving,
   sub-100ms Tier 1 the architecture is designed around.

The backend already treats Tier 1 as a pluggable probability source
([`Backend/classifier.py`](../Backend/classifier.py)), so swapping the model is
a local change — the extension and the API are untouched.
