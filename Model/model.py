# ===============================================================
# 🛡️ PhishGuard - Tier 1 inference CLI
# ===============================================================
# Loads the trained classifier and scores text from the command line.
#
#   python model.py "Aapka SBI khata band ho jayega, OTP batao"
#   echo "some message" | python model.py
#
# Train the artifact first:  python train.py
# ===============================================================

from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import joblib

MODEL = Path(__file__).parent / "classifier.joblib"


def main() -> None:
    if not MODEL.exists():
        sys.exit("No model found. Run:  python train.py")

    pipe = joblib.load(MODEL)

    text = " ".join(sys.argv[1:]).strip()
    if not text and not sys.stdin.isatty():
        text = sys.stdin.read().strip()
    if not text:
        sys.exit('Usage: python model.py "message text to score"')

    classes = list(pipe.classes_)
    idx = classes.index(1) if 1 in classes else 1
    prob = float(pipe.predict_proba([text])[0][idx])

    verdict = "PHISHING" if prob >= 0.5 else "legit"
    print(f"P(phishing) = {prob:.3f}  ->  {verdict}")


if __name__ == "__main__":
    main()
