# ===============================================================
# 🛡️ PhishGuard - Tier 1 ML classifier loader
# ===============================================================
# Loads the trained char-ngram TF-IDF + LogReg pipeline and exposes a
# single predict_proba(text) -> P(phishing). Degrades gracefully: if the
# artifact or sklearn is missing, the backend just runs Tier 0 alone.
#
# Train the artifact with:  python ../Model/train.py
# ===============================================================

from __future__ import annotations

from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent / "Model" / "classifier.joblib"

_pipe = None
_load_error: str | None = None


def _load() -> None:
    global _pipe, _load_error
    try:
        import joblib  # noqa: deferred so the backend boots without ML deps
        _pipe = joblib.load(MODEL_PATH)
    except Exception as e:  # missing file, missing sklearn, version skew, ...
        _pipe = None
        _load_error = f"{type(e).__name__}: {e}"


_load()


def is_ready() -> bool:
    return _pipe is not None


def status() -> str:
    return "ready" if is_ready() else f"unavailable ({_load_error})"


def predict_proba(text: str) -> float | None:
    """Return P(phishing) in [0,1], or None if the model isn't loaded."""
    if _pipe is None or not text:
        return None
    # Pipeline includes the vectorizer, so we pass raw text straight in.
    proba = _pipe.predict_proba([text])[0]
    # Class order follows pipe.classes_ ; label 1 == phishing.
    classes = list(_pipe.classes_)
    idx = classes.index(1) if 1 in classes else 1
    return float(proba[idx])
