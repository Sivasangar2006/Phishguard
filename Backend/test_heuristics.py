# Quick sanity checks for the Tier 0 engine. Run: python test_heuristics.py
import sys

# Windows consoles default to cp1252 and can't print Devanagari/Tamil reasons.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from heuristics import score_text

CASES = [
    # (label, text, expected_risk)
    ("Hindi OTP scam (Romanized)",
     "URGENT! Aapka SBI khata band ho jayega. Turant KYC update karo aur OTP batao: https://sbi-verify.xyz",
     "high"),
    ("English lottery bait + shortener",
     "Congratulations! You have won a lottery prize. Claim now: http://bit.ly/win-cash",
     "high"),
    ("Devanagari KYC + IP link",
     "तुरंत अपना केवाईसी सत्यापित करें वरना खाता बंद हो जाएगा http://203.0.113.9/kyc",
     "high"),
    ("Mild marketing (should be low/medium)",
     "Amazon sale is live, check out the offers on electronics today.",
     "low"),
    ("Normal chat",
     "Hey, are we still meeting for lunch at 1pm tomorrow?",
     "low"),
    ("Tamil reward bait",
     "வாழ்த்துக்கள்! நீங்கள் ஒரு பரிசு வென்றுள்ளீர்கள். claim now link: http://prize.top/redeem",
     "high"),
    ("Bank impersonation + urgency combo",
     "Dear customer, your HDFC account is suspended. Verify your account immediately with your CVV and PIN.",
     "high"),
]


def main() -> None:
    passed = 0
    for label, text, expected in CASES:
        r = score_text(text)
        ok = r.risk == expected
        passed += ok
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {label}")
        print(f"       risk={r.risk} (expected {expected}) score={r.score}")
        for reason in r.reasons[:4]:
            print(f"         - {reason}")
        print()
    print(f"{passed}/{len(CASES)} cases passed")


if __name__ == "__main__":
    main()
