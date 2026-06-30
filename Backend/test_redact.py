# Sanity checks for PII redaction. Run: python test_redact.py
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from redact import redact

# (label, input, must_contain_placeholders, must_NOT_contain substrings)
CASES = [
    ("OTP + phone",
     "482913 is your OTP, call 9876543210 now",
     ["<OTP>", "<PHONE>"], ["482913", "9876543210"]),
    ("masked account",
     "Your A/C XXXXX3917 is credited with Rs 2.00",
     ["<ACCOUNT>"], ["XXXXX3917"]),
    ("card number",
     "Enter card 4111 1111 1111 1111 to verify",
     ["<CARD>"], ["4111"]),
    ("PAN + Aadhaar",
     "PAN ABCDE1234F Aadhaar 1234 5678 9012 update",
     ["<PAN>", "<AADHAAR>"], ["ABCDE1234F", "1234 5678 9012"]),
    ("email + UPI",
     "mail rahul@gmail.com or pay rahul@okaxis",
     ["<EMAIL>", "<UPI>"], ["rahul@gmail.com", "rahul@okaxis"]),
    ("greeting name",
     "Dear Rahul, your account is suspended",
     ["<NAME>"], ["Rahul"]),
    ("keeps scam structure",
     "URGENT! KYC update karo: http://sbi-verify.xyz",
     [], ["<"]),  # no PII -> nothing redacted, url + urgency preserved
]


def main() -> None:
    passed = 0
    for label, text, must, must_not in CASES:
        out, counts = redact(text)
        ok = all(p in out for p in must) and all(s not in out for s in must_not)
        # special: last case asserts NO placeholder was inserted
        if label == "keeps scam structure":
            ok = "<" not in out and "sbi-verify.xyz" in out and "URGENT" in out
        passed += ok
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")
        print(f"        -> {out}")
        if counts:
            print(f"        redacted: {counts}")
    print(f"\n{passed}/{len(CASES)} redaction cases passed")


if __name__ == "__main__":
    main()
