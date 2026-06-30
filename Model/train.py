# ===============================================================
# 🛡️ PhishGuard - Tier 1 baseline trainer
# ===============================================================
# Trains a character n-gram TF-IDF + Logistic Regression classifier.
#
# Why char n-grams: they work ACROSS scripts (Latin, Devanagari, Tamil)
# with no tokenizer or language-ID step, so one model covers all four
# languages. The artifact is tiny (KBs) and trivially portable to the
# browser later -- a genuine on-device Tier 1 baseline.
#
# This is the BASELINE. The documented upgrade is a distilled MuRIL/
# IndicBERT encoder exported to ONNX (see README). Same /scan contract.
#
# Run:  python train.py
# Out:  classifier.joblib  + printed metrics (overall, per-language,
#       and vs the Tier 0 heuristic baseline on the same test set)
# ===============================================================

from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.pipeline import Pipeline

HERE = Path(__file__).parent
DATA = HERE / "dataset" / "phishguard_dataset.csv"
MODEL_OUT = HERE / "classifier.joblib"

# Let us reuse the Tier 0 engine for an apples-to-apples comparison.
sys.path.insert(0, str(HERE.parent / "Backend"))
try:
    from heuristics import score_text  # type: ignore
    HAVE_HEURISTIC = True
except Exception:
    HAVE_HEURISTIC = False


def heuristic_label(text: str) -> int:
    """Map the Tier 0 risk band to a binary label (high/medium -> phish)."""
    return 0 if score_text(text).risk == "low" else 1


def build_pipe() -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            analyzer="char_wb",   # char n-grams within word boundaries
            ngram_range=(2, 5),
            min_df=2,
            sublinear_tf=True,
        )),
        ("clf", LogisticRegression(
            class_weight="balanced",   # corrects the 60/40 skew
            max_iter=2000,
            C=4.0,
        )),
    ])


def grouped_eval(df: pd.DataFrame, group_col: str, title: str, note: str) -> float:
    """Group-aware generalization: hold out whole GROUPS (templates or
    categories) so the test set shares nothing with training at that level."""
    gss = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=7)
    train_idx, test_idx = next(gss.split(df["text"], df["label"], groups=df[group_col]))
    tr, te = df.iloc[train_idx], df.iloc[test_idx]
    # Skip degenerate splits where the test set is single-class.
    if te["label"].nunique() < 2:
        print(f"{title}: skipped (single-class test split)\n")
        return float("nan")
    pipe = build_pipe()
    pipe.fit(tr["text"], tr["label"])
    pred = pipe.predict(te["text"])
    f1 = f1_score(te["label"], pred)
    print("=" * 56)
    print(title)
    print("=" * 56)
    print(f"Held out {te[group_col].nunique()} whole {group_col}s "
          f"({len(te)} rows) the model never trained on.")
    print(classification_report(te["label"], pred, target_names=["legit", "phish"], digits=3))
    print(f"Phishing F1: {f1:.3f}   ({note})\n")
    return f1


def main() -> None:
    df = pd.read_csv(DATA)
    print(f"Loaded {len(df)} rows from {DATA.name} "
          f"(phish={df.label.sum()}, legit={(df.label == 0).sum()})\n")

    # (1a) Unseen PHRASINGS — hold out whole templates.
    grouped_eval(df, "template_id",
                 "HONEST EVAL — unseen TEMPLATES (new phrasing, known scam type)",
                 "generalization to new wording")
    # (1b) Unseen SCAM TYPES — hold out whole categories. The hard, realistic
    # test: can it flag a scam category it never trained on? On clean synthetic
    # data even this saturates; on real data it would not.
    grouped_eval(df, "category",
                 "HONEST EVAL — unseen CATEGORIES (scam type never seen)",
                 "generalization to new scam types — the meaningful number")

    # (2) The optimistic random-row split (in-distribution upper bound).
    X_train, X_test, y_train, y_test, lang_train, lang_test = train_test_split(
        df["text"], df["label"], df["lang"],
        test_size=0.25, stratify=df["label"], random_state=42,
    )

    pipe = build_pipe()
    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)

    # ---------------- overall ----------------
    print("=" * 56)
    print("OPTIMISTIC EVAL — random split (in-distribution upper bound)")
    print("=" * 56)
    print(classification_report(y_test, y_pred, target_names=["legit", "phish"], digits=3))
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
    print(f"Confusion: TP={tp} TN={tn} FP={fp} FN={fn}")
    ml_f1 = f1_score(y_test, y_pred)
    print(f"Phishing F1: {ml_f1:.3f}\n")

    # ---------------- per language ----------------
    print("Per-language phishing F1 (test set):")
    test_df = pd.DataFrame({"y": y_test.values, "p": y_pred, "lang": lang_test.values})
    for lang in sorted(test_df["lang"].unique()):
        sub = test_df[test_df["lang"] == lang]
        if sub["y"].nunique() < 2:
            print(f"  {lang:7s}: n={len(sub):3d}  (single-class slice, F1 n/a)")
            continue
        f1 = f1_score(sub["y"], sub["p"])
        print(f"  {lang:7s}: n={len(sub):3d}  F1={f1:.3f}")
    print()

    # ---------------- vs Tier 0 heuristic ----------------
    if HAVE_HEURISTIC:
        h_pred = [heuristic_label(t) for t in X_test]
        h_f1 = f1_score(y_test, h_pred)
        print("Baseline comparison on the SAME test set:")
        print(f"  Tier 0 heuristics  Phishing F1: {h_f1:.3f}")
        print(f"  Tier 1 ML model    Phishing F1: {ml_f1:.3f}")
        delta = ml_f1 - h_f1
        print(f"  Δ (ML - heuristic): {delta:+.3f}\n")

    joblib.dump(pipe, MODEL_OUT)
    print(f"Saved model -> {MODEL_OUT.name} "
          f"({MODEL_OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
