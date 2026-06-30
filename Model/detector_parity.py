# Full-detector parity (Python side): for each message, compute the backend's
# fused verdict exactly as /scan would, and dump it for the JS side to match.
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent.parent / "Backend"))
from heuristics import score_text          # noqa: E402
import classifier                          # noqa: E402
from main import fuse                      # noqa: E402

from parity_test import MESSAGES           # reuse the same message set  # noqa: E402

rows = []
for m in MESSAGES:
    h = score_text(m)
    ml = classifier.predict_proba(m)
    risk, _ = fuse(h, ml)
    rows.append({
        "text": m, "risk": risk, "score": h.score,
        "ml": round(ml, 3) if ml is not None else None,
    })

(Path(__file__).parent / "detector_parity_data.json").write_text(
    json.dumps({"rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"Wrote backend verdicts for {len(rows)} messages -> detector_parity_data.json")
