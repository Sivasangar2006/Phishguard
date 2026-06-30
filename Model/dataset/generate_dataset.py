# ===============================================================
# 🛡️ PhishGuard - Vernacular phishing dataset generator
# ===============================================================
# Produces a balanced, multilingual labeled corpus for training the
# Tier 1 classifier. Languages: English, Romanized Hindi ("Hinglish"),
# Devanagari Hindi, Tamil.
#
# IMPORTANT (honesty): this is SYNTHETIC *seed* data built from
# templates + slot-filling. It bootstraps the pipeline and lets the
# model learn intent across scripts, but it is NOT a substitute for
# real scraped/reported scams. Real-world collection is the documented
# next step (see dataset/README.md). Treat metrics on this data as an
# upper bound, not field performance.
#
# Run:  python generate_dataset.py            -> phishguard_dataset.csv
# ===============================================================

from __future__ import annotations

import csv
import json
import random
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

random.seed(42)  # reproducible

OUT = Path(__file__).parent / "phishguard_dataset.csv"
# Optional machine-authored templates (e.g. from the expansion workflow).
EXTRA = Path(__file__).parent / "templates_extra.json"
LANGS = {"en", "hi_rom", "hi_dev", "ta"}

# ---------------------------------------------------------------
# Slot fillers
# ---------------------------------------------------------------

BANKS = ["SBI", "HDFC", "ICICI", "Axis", "Kotak", "Paytm", "PhonePe", "Yes Bank"]
AMOUNTS = ["499", "999", "1,250", "2,00,000", "50,000", "9,999", "1,00,000", "750"]
ACCTS = ["XXXXX3917", "XXXXX1042", "XXXXX8830", "XXXXX0571", "XXXXX7766"]
NAMES = ["Rahul", "Priya", "Arjun", "Kavya", "Suresh", "Meena", "customer", "ग्राहक"]
OTPS = ["482913", "705621", "338190", "991204", "650017"]
PHONES = ["18001234", "9876543210", "1800111", "08041234567"]

# Phishing URLs: lookalike / free-TLD / shortener.
PHISH_URLS = [
    "http://sbi-verify.xyz/login", "https://kyc-update.top/now",
    "http://paytm-kyc.link/verify", "https://secure-bank-login.xyz",
    "http://bit.ly/win-cash", "https://hdfc-rewards.click/claim",
    "http://icici-netbanking.online/auth", "https://rbi-refund.gq/form",
]
# Legit URLs: real domains.
LEGIT_URLS = [
    "https://onlinesbi.sbi", "https://www.amazon.in", "https://paytm.com",
    "https://netbanking.hdfcbank.com", "https://www.icicibank.com",
]
# Authorities impersonated in digital-arrest scams.
AGENCIES = ["CBI", "Mumbai Police", "Customs Department", "TRAI",
            "Cyber Crime Branch", "Narcotics Control Bureau", "Income Tax Department"]
# Fictional app names for loan/investment scams (never real apps).
APPS = ["RupeeFast", "CashBee", "QuickRupee", "InstaPaisa", "LoanKamao", "TradeMax"]


def pick(seq):
    return random.choice(seq)


# Slot names the filler knows how to populate. Any template using a slot
# outside this set is rejected at load time.
ALLOWED_SLOTS = {
    "bank", "amount", "acct", "name", "otp", "phone",
    "phish_url", "legit_url", "agency", "app",
}


# ---------------------------------------------------------------
# Templates
# ---------------------------------------------------------------
# Each entry: (category, language, label, template-with-{slots})
#   label: 1 = phishing, 0 = legit
#   languages: en | hi_rom | hi_dev | ta
#
# Slots: {bank} {amount} {acct} {name} {otp} {phone} {phish_url} {legit_url}

TEMPLATES: list[tuple[str, str, int, str]] = [

    # ====================== PHISHING ======================

    # --- KYC / account-suspension scam ---
    ("kyc", "en", 1, "Dear {name}, your {bank} account is suspended. Complete KYC immediately or your account will be blocked: {phish_url}"),
    ("kyc", "en", 1, "URGENT: {bank} A/C {acct} blocked due to incomplete KYC. Update now to avoid permanent closure {phish_url}"),
    ("kyc", "hi_rom", 1, "Priya {bank} account band ho jayega! Turant KYC update karo varna account block ho jayega: {phish_url}"),
    ("kyc", "hi_rom", 1, "Aapka {bank} khata {acct} suspend kar diya gaya hai. Abhi KYC complete karein: {phish_url}"),
    ("kyc", "hi_dev", 1, "प्रिय ग्राहक, आपका {bank} खाता बंद हो जाएगा। तुरंत KYC अपडेट करें वरना खाता ब्लॉक हो जाएगा: {phish_url}"),
    ("kyc", "hi_dev", 1, "जरूरी सूचना: आपका {bank} खाता {acct} केवाईसी अधूरी होने के कारण बंद किया जा रहा है। अभी सत्यापित करें {phish_url}"),
    ("kyc", "ta", 1, "உங்கள் {bank} கணக்கு முடக்கப்படும்! உடனடியாக KYC புதுப்பிக்கவும் இல்லையெனில் கணக்கு நிரந்தரமாக மூடப்படும்: {phish_url}"),

    # --- OTP / credential harvest ---
    ("otp_scam", "en", 1, "{bank} security alert: share the OTP {otp} sent to your phone to verify your account, else it will be deactivated."),
    ("otp_scam", "hi_rom", 1, "{bank} se: account verify karne ke liye OTP {otp} abhi share karein, nahi to account band ho jayega."),
    ("otp_scam", "hi_dev", 1, "{bank} सुरक्षा: अपना खाता सत्यापित करने के लिए OTP {otp} तुरंत बताएं अन्यथा खाता निष्क्रिय हो जाएगा।"),
    ("otp_scam", "ta", 1, "{bank} பாதுகாப்பு எச்சரிக்கை: உங்கள் கணக்கை சரிபார்க்க OTP {otp} ஐ பகிரவும், இல்லையெனில் முடக்கப்படும்."),

    # --- Lottery / reward bait ---
    ("lottery", "en", 1, "Congratulations {name}! You have WON Rs {amount} in the {bank} lucky draw. Claim now: {phish_url}"),
    ("lottery", "hi_rom", 1, "Badhai ho! Aap {bank} lucky draw me Rs {amount} jeet gaye hain. Abhi claim karein: {phish_url}"),
    ("lottery", "hi_dev", 1, "बधाई हो! आप {bank} लकी ड्रॉ में रु {amount} जीत गए हैं। अभी इनाम क्लेम करें: {phish_url}"),
    ("lottery", "ta", 1, "வாழ்த்துக்கள்! நீங்கள் {bank} லக்கி டிராவில் ரூ {amount} வென்றுள்ளீர்கள். இப்போது claim செய்யவும்: {phish_url}"),

    # --- Refund / cashback scam ---
    ("refund", "en", 1, "Your refund of Rs {amount} is pending. Verify your bank details to receive it: {phish_url}"),
    ("refund", "hi_rom", 1, "Aapka Rs {amount} ka refund pending hai. Paane ke liye bank details verify karein: {phish_url}"),
    ("refund", "hi_dev", 1, "आपका रु {amount} का रिफंड लंबित है। इसे पाने के लिए बैंक विवरण सत्यापित करें: {phish_url}"),

    # --- Delivery / customs scam ---
    ("delivery_scam", "en", 1, "Your parcel is held at customs. Pay Rs {amount} clearance fee within 24 hours or it will be returned: {phish_url}"),
    ("delivery_scam", "hi_rom", 1, "Aapka courier customs me ruka hai. 24 ghante me Rs {amount} fees bharein warna wapas chala jayega: {phish_url}"),
    ("delivery_scam", "hi_dev", 1, "आपका पार्सल कस्टम में रुका है। 24 घंटे में रु {amount} शुल्क भरें अन्यथा वापस भेज दिया जाएगा: {phish_url}"),

    # --- Electricity disconnection scam ---
    ("electricity", "en", 1, "Dear consumer, your electricity will be disconnected tonight as your bill is not updated. Call {phone} immediately {phish_url}"),
    ("electricity", "hi_rom", 1, "Aaj raat aapki bijli kaat di jayegi kyunki bill update nahi hua. Turant {phone} par call karein {phish_url}"),
    ("electricity", "hi_dev", 1, "प्रिय उपभोक्ता, बिल अपडेट न होने के कारण आज रात आपकी बिजली काट दी जाएगी। तुरंत {phone} पर संपर्क करें {phish_url}"),

    # --- Job / earn-money scam ---
    ("job_scam", "en", 1, "Work from home and earn Rs {amount} daily! Limited seats. Register now with a small fee: {phish_url}"),
    ("job_scam", "hi_rom", 1, "Ghar baithe Rs {amount} roz kamayein! Seats limited hain. Choti si fees ke saath register karein: {phish_url}"),
    ("job_scam", "hi_dev", 1, "घर बैठे रोज रु {amount} कमाएं! सीटें सीमित हैं। छोटी सी फीस देकर अभी रजिस्टर करें: {phish_url}"),

    # ====================== LEGIT ======================

    # --- Transaction alert (legit) ---
    ("txn_alert", "en", 0, "Dear {name}, your A/C {acct} is credited with Rs {amount} on 27JUN. Avl Bal updated. -{bank}"),
    ("txn_alert", "en", 0, "Rs {amount} debited from A/C {acct} for UPI payment. Not you? Call {phone}. -{bank}"),
    ("txn_alert", "hi_rom", 0, "Aapke khate {acct} me Rs {amount} jama hue. Available balance update ho gaya. -{bank}"),
    ("txn_alert", "hi_dev", 0, "प्रिय ग्राहक, आपके खाते {acct} में रु {amount} जमा हुए। उपलब्ध शेष अपडेट किया गया। -{bank}"),
    ("txn_alert", "ta", 0, "உங்கள் கணக்கு {acct} இல் ரூ {amount} வரவு வைக்கப்பட்டது. இருப்பு புதுப்பிக்கப்பட்டது. -{bank}"),

    # --- Legit OTP (HARD NEGATIVE: contains "OTP" but is real) ---
    ("otp_legit", "en", 0, "{otp} is your OTP for {bank} login. Do NOT share it with anyone. -{bank}"),
    ("otp_legit", "hi_rom", 0, "{otp} aapka {bank} login OTP hai. Ise kisi ke saath share na karein. -{bank}"),
    ("otp_legit", "hi_dev", 0, "{otp} आपके {bank} लॉगिन के लिए OTP है। इसे किसी के साथ साझा न करें। -{bank}"),
    ("otp_legit", "ta", 0, "{otp} உங்கள் {bank} உள்நுழைவுக்கான OTP. யாருடனும் பகிர வேண்டாம். -{bank}"),

    # --- Promo / marketing (HARD NEGATIVE) ---
    ("promo", "en", 0, "{bank} Sale is live! Flat {amount} off on your next purchase. Shop now at {legit_url}"),
    ("promo", "hi_rom", 0, "{bank} sale shuru! Agli kharidari par {amount} ki chhoot. Abhi kharidein {legit_url}"),
    ("promo", "hi_dev", 0, "{bank} सेल लाइव है! अगली खरीद पर {amount} की छूट। अभी खरीदें {legit_url}"),

    # --- Delivery update (legit) ---
    ("delivery_legit", "en", 0, "Your order is out for delivery and will arrive today. Track at {legit_url}"),
    ("delivery_legit", "hi_rom", 0, "Aapka order aaj deliver hoga. Yaha track karein {legit_url}"),
    ("delivery_legit", "hi_dev", 0, "आपका ऑर्डर आज डिलीवर होगा। यहां ट्रैक करें {legit_url}"),

    # --- Bill reminder (legit; HARD NEGATIVE: "bill due") ---
    ("bill_legit", "en", 0, "Reminder: your electricity bill of Rs {amount} is due on 5th. Pay via the official app {legit_url}"),
    ("bill_legit", "hi_rom", 0, "Yaad dilaye: aapka Rs {amount} ka bijli bill 5 tarikh ko due hai. Official app se bharein {legit_url}"),
    ("bill_legit", "hi_dev", 0, "अनुस्मारक: आपका रु {amount} का बिजली बिल 5 तारीख को देय है। आधिकारिक ऐप से भुगतान करें {legit_url}"),

    # --- Personal chat (legit) ---
    ("chat", "en", 0, "Hey {name}, are we still meeting for lunch at 1pm tomorrow?"),
    ("chat", "en", 0, "Got the documents, thanks! I'll review them tonight and call you."),
    ("chat", "hi_rom", 0, "Hey {name}, kal lunch pe milte hain na 1 baje?"),
    ("chat", "hi_dev", 0, "अरे {name}, कल दोपहर 1 बजे लंच पर मिल रहे हैं ना?"),
    ("chat", "ta", 0, "ஹாய் {name}, நாளை மதியம் 1 மணிக்கு சந்திக்கலாமா?"),
]


def fill(template: str) -> str:
    return template.format(
        bank=pick(BANKS), amount=pick(AMOUNTS), acct=pick(ACCTS),
        name=pick(NAMES), otp=pick(OTPS), phone=pick(PHONES),
        phish_url=pick(PHISH_URLS), legit_url=pick(LEGIT_URLS),
        agency=pick(AGENCIES), app=pick(APPS),
    )


def load_extra_templates() -> list[tuple[str, str, int, str]]:
    """Load optional machine-authored templates from templates_extra.json.
    Expected shape: {"archetypes": [{"category", "templates": [
        {"lang", "label", "text", "category"?}, ...]}]}.
    Templates using unknown slots or bad languages are skipped, not crashed."""
    if not EXTRA.exists():
        return []
    try:
        data = json.loads(EXTRA.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"  (could not parse {EXTRA.name}: {e})")
        return []

    rows: list[tuple[str, str, int, str]] = []
    skipped = 0
    for arch in data.get("archetypes", []):
        arch_cat = arch.get("category", "extra")
        for t in arch.get("templates", []):
            text = t.get("text", "")
            lang = t.get("lang", "")
            cat = t.get("category", arch_cat)
            try:
                label = int(t.get("label"))
            except (TypeError, ValueError):
                skipped += 1
                continue
            slots = set(re.findall(r"\{(\w+)\}", text))
            if lang not in LANGS or label not in (0, 1) or not slots <= ALLOWED_SLOTS:
                skipped += 1
                continue
            rows.append((cat, lang, label, text))
    if skipped:
        print(f"  (skipped {skipped} invalid extra templates)")
    if rows:
        print(f"  (loaded {len(rows)} extra templates from {EXTRA.name})")
    return rows


# ---------------------------------------------------------------
# Generation: expand each template with N slot variations
# ---------------------------------------------------------------

VARIATIONS_PER_TEMPLATE = 18


def generate() -> list[dict]:
    rows: list[dict] = []
    seen: set[str] = set()
    # template_id lets the trainer do GROUP-AWARE splits (hold out whole
    # templates) so we measure generalization to unseen phrasings, not
    # memorization of template strings.
    all_templates = TEMPLATES + load_extra_templates()
    for template_id, (category, lang, label, template) in enumerate(all_templates):
        made = 0
        attempts = 0
        while made < VARIATIONS_PER_TEMPLATE and attempts < VARIATIONS_PER_TEMPLATE * 6:
            attempts += 1
            text = fill(template)
            if text in seen:
                continue
            seen.add(text)
            rows.append({
                "text": text,
                "label": label,
                "lang": lang,
                "category": category,
                "template_id": template_id,
                "source": "synthetic_seed_v1",
            })
            made += 1
    random.shuffle(rows)
    return rows


def main() -> None:
    rows = generate()
    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["text", "label", "lang", "category", "template_id", "source"])
        writer.writeheader()
        writer.writerows(rows)

    phish = sum(r["label"] for r in rows)
    legit = len(rows) - phish
    langs = sorted({r["lang"] for r in rows})
    print(f"Wrote {len(rows)} rows -> {OUT.name}")
    print(f"  phishing: {phish}   legit: {legit}")
    print(f"  languages: {', '.join(langs)}")
    by_lang = {l: sum(1 for r in rows if r['lang'] == l) for l in langs}
    print(f"  per language: {by_lang}")


if __name__ == "__main__":
    main()
