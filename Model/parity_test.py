# Step 1 of the parity test: compute Python predict_proba for a set of
# messages and dump them, so the JS scorer can be checked against them.
import json
import sys
from pathlib import Path

import joblib

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).parent
pipe = joblib.load(HERE / "classifier.joblib")
classes = list(pipe.classes_)
idx = classes.index(1) if 1 in classes else 1

MESSAGES = [
    "URGENT! Aapka SBI khata band ho jayega. Turant KYC update karo aur OTP batao: http://sbi-verify.xyz",
    "प्रिय ग्राहक, आपका SBI खाता बंद हो जाएगा। तुरंत KYC update करें और OTP बताएं: http://sbi-verify.xyz",
    "வாழ்த்துக்கள்! நீங்கள் ஒரு பரிசு வென்றுள்ளீர்கள். claim now: http://prize.top/redeem",
    "482913 is your OTP for SBI login. Do NOT share it with anyone. -SBI",
    "Hey, are we still meeting for lunch at 1pm tomorrow?",
    "Dear customer, your HDFC account is suspended. Verify immediately with your CVV and PIN.",
    "Your Swiggy order has been delivered. Please rate your experience.",
    "This is CBI. You are under digital arrest, transfer Rs 50000 now",
    "Amazon sale is live, flat 50% off on electronics today.",
    "மருத்துவர் திங்கள் 11 மணிக்கு சந்திப்பை உறுதி செய்துள்ளார்.",
    "Ghar baithe rozana 5000 kamaiye, abhi register karein",
    "Your cab is arriving in 3 minutes at the gate.",
]

out = {"messages": MESSAGES,
       "python": [float(pipe.predict_proba([m])[0][idx]) for m in MESSAGES]}
(HERE / "parity_data.json").write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
print(f"Wrote Python probabilities for {len(MESSAGES)} messages -> parity_data.json")
