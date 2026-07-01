# Evaluate a local Ollama LLM (qwen2.5) as the phishing classifier, on the
# same set the char-ngram model struggled with. Measures false positives,
# scam recall, and latency. Requires Ollama running with qwen2.5:3b.
import json
import sys
import time
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

OLLAMA = "http://localhost:11434/api/chat"
# Test any model:  python llm_test.py qwen2.5:7b
MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5:3b"

SYSTEM = (
    "You detect phishing/scam messages in English and Indian languages "
    "(Hindi, Tamil, Bengali, etc.), including romanized/code-mixed text.\n\n"
    "KEY RULE: a message is PHISHING only if it REQUESTS something dangerous "
    "FROM the reader (OTP, password, PIN, CVV, money, click a link to "
    "'verify/update') or THREATENS them (account will be blocked, arrest, "
    "legal action). A message that merely INFORMS the reader is LEGITIMATE, "
    "EVEN IF it mentions OTP, payment, bill, account, bank, or money.\n\n"
    "CRITICAL OTP RULE: a message that TELLS you a code ('Your OTP is 123456', "
    "'123456 is your verification code', 'Your OTP for X is 123456') is ALWAYS "
    "LEGITIMATE — the service is delivering YOUR code. It is phishing ONLY if it "
    "ASKS you to SHARE / SEND / TELL / enter your OTP.\n\n"
    "Examples:\n"
    "- 'Your OTP for Amazon is 728193' -> legitimate (tells you your code)\n"
    "- 'Share the OTP sent to your phone to verify your account' -> phishing (asks for it)\n"
    "- 'Thanks for your payment of Rs 499 to Netflix' -> legitimate\n"
    "- 'Your electricity bill of Rs 1240 is due, pay in the app' -> legitimate\n"
    "- 'आपके खाते में रु 2.00 जमा हुए' -> legitimate (credit alert)\n"
    "- 'Pay Rs 999 customs fee to release your parcel: http://x.top' -> phishing\n"
    "- 'तुरंत KYC update करें वरना खाता बंद हो जाएगा' -> phishing (threat + request)\n"
    "- 'Congrats! You won a lottery, pay fee to claim' -> phishing\n\n"
    'Respond ONLY as JSON: {"verdict": "phishing" | "legitimate", '
    '"confidence": 0.0-1.0, "reason": "<=12 words"}.'
)


def classify(text: str) -> dict:
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": text}],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }).encode("utf-8")
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.loads(r.read())
    return json.loads(out["message"]["content"])


LEGIT = [
    "Your OTP for Amazon login is 728193. Valid for 10 minutes.",
    "Your Zomato order #12345 is on the way! Track it in the app.",
    "Reminder: Your electricity bill of Rs 1240 is due on 5th. Pay via the app.",
    "Hi team, please find attached the Q3 report. Let me know your thoughts.",
    "Your package from Amazon has been delivered.",
    "Your account statement for July is ready. Download from net banking.",
    "Thanks for your payment of Rs 499 to Netflix.",
    "Swiggy: Your refund of Rs 120 has been credited to your account.",
    "Google: New sign-in on Windows. If this was you, no action needed.",
    "Congratulations on completing 5 years at the company!",
    "Payment of Rs 2000 received from Priya via UPI.",
    "आपके खाते XXXXX3917 में रु 2.00 जमा हुए। उपलब्ध शेष अपडेट किया गया।",
]
SCAM = [
    "URGENT! Aapka SBI khata band ho jayega. Turant KYC update karo aur OTP batao: https://sbi-verify.xyz",
    "प्रिय ग्राहक, आपका SBI खाता बंद हो जाएगा। तुरंत KYC update करें और OTP बताएं",
    "வாழ்த்துக்கள்! நீங்கள் பரிசு வென்றீர்கள். claim now: http://prize.top/redeem",
    "Dear customer, your HDFC account is suspended. Verify immediately with your CVV and PIN.",
    "This is CBI. You are under digital arrest, transfer Rs 50000 to verify account now",
    "Congrats! Loan of Rs 200000 pre-approved, download app: http://loan-app.xyz",
]


def run(name, items, want_phish):
    wrong = 0
    lat = []
    print(f"--- {name} ---")
    for m in items:
        t0 = time.time()
        try:
            r = classify(m)
        except Exception as e:
            print(f"  ERR {e}")
            wrong += 1
            continue
        lat.append(time.time() - t0)
        is_phish = str(r.get("verdict", "")).lower().startswith("phish")
        bad = is_phish != want_phish
        wrong += bad
        conf = r.get("confidence", "?")
        print(f"  {'WRONG' if bad else 'ok   '} {r.get('verdict',''):11s} conf={conf}  {m[:46]}")
    avg = sum(lat) / len(lat) if lat else 0
    return wrong, avg


if __name__ == "__main__":
    fp, l1 = run("LEGIT (want legitimate)", LEGIT, False)
    miss, l2 = run("SCAM (want phishing)", SCAM, True)
    print(f"\n=> false positives: {fp}/{len(LEGIT)}   scams missed: {miss}/{len(SCAM)}")
    print(f"=> avg latency: {(l1 + l2) / 2:.2f}s per message")
