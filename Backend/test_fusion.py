# Locks in the Tier 0 + Tier 1 fusion behavior. Run: python test_fusion.py
# Pure logic test (no server) — constructs stub heuristic results.
import sys
from types import SimpleNamespace

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from main import fuse


def R(score: int, structural: bool = False):
    return SimpleNamespace(score=score, structural=structural)


# (label, heuristic_result, ml_prob, expected_risk)
CASES = [
    ("clean chat",                 R(0),               0.05, "low"),
    # The regression that bit us: heuristic over-fires on 'OTP' (score 40),
    # but a confident-legit ML must pull it back to low.
    ("legit OTP (false-pos fix)",  R(40),              0.04, "low"),
    ("strong scam + lookalike",    R(46, True),        0.97, "high"),
    # Structural override: a look-alike URL alone is near-certain even if ML is unsure.
    ("structural override",        R(46, True),        0.10, "high"),
    # Borderline ML with no real heuristic signal is now SUPPRESSED for
    # precision (it overlaps with legit text); only very-confident ML flags solo.
    ("weak ML, no signal -> low",  R(14),              0.61, "low"),
    ("very confident ML alone",    R(0),               0.93, "high"),
    # Model absent -> Tier 0 only.
    ("no model, strong heuristic", R(60),              None, "high"),
    ("no model, clean",            R(0),               None, "low"),
]


def main() -> None:
    passed = 0
    for label, result, ml, expected in CASES:
        risk, fused = fuse(result, ml)
        ok = risk == expected
        passed += ok
        print(f"[{'PASS' if ok else 'FAIL'}] {label:28s} -> {risk:6s} "
              f"(fused {fused:.2f}, expected {expected})")
    print(f"\n{passed}/{len(CASES)} fusion cases passed")
    if passed != len(CASES):
        sys.exit(1)


if __name__ == "__main__":
    main()
