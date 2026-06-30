# PhishGuard Vernacular Phishing Dataset (seed v1)

A labeled, multilingual corpus for training the Tier 1 phishing classifier.
Covers **English, Romanized Hindi ("Hinglish"), Devanagari Hindi, and Tamil** —
languages underserved by English-first phishing detectors.

## ⚠️ Honest provenance — read this first

This is **synthetic seed data**, generated from hand-written templates with
slot-filling ([`generate_dataset.py`](generate_dataset.py)). It exists to:

- bootstrap the pipeline end-to-end, and
- teach the model **intent across scripts** (via deliberately hard negatives).

It is **not** a substitute for real-world data. A model that scores well on
this corpus has learned the template distribution, not the full diversity of
real scams. **Treat in-distribution metrics as an upper bound, not field
performance.** Collecting and labeling real reported scams (SMS archives,
forwarded WhatsApp/email samples, honeypots) is the documented next step and
the project's real moat.

## Schema

CSV with one message per row:

| column        | meaning                                                    |
|---------------|------------------------------------------------------------|
| `text`        | the message                                                |
| `label`       | `1` = phishing, `0` = legit                                |
| `lang`        | `en` \| `hi_rom` \| `hi_dev` \| `ta`                       |
| `category`    | scam/legit type (e.g. `kyc`, `otp_legit`, `txn_alert`)     |
| `template_id` | source template — enables **group-aware** train/test splits |
| `source`      | provenance tag (`synthetic_seed_v1`)                       |

## Why `template_id` matters

A random train/test split leaks: the model sees the same templates in both
sets and memorizes them (→ ~1.0 F1, meaningless). The trainer instead does a
**group split on `template_id`**, holding out whole templates so the test set
is phrasings the model never saw. That number (~0.81 F1) is the honest one.

## Hard negatives (the important part)

Several legit categories deliberately share vocabulary with scams, forcing the
model to learn intent rather than keywords:

- `otp_legit` — *"482913 is your OTP. Do NOT share it."* (contains "OTP")
- `promo` — marketing with discounts and links (contains urls + "offer")
- `bill_legit` — *"your electricity bill is due"* (contains "bill due")
- `txn_alert` — real credit/debit notices (contains bank names + amounts)

## Composition

Run the generator to (re)build and print stats:

```bash
python generate_dataset.py
```

Current seed: **1,766 rows** — phishing ≈ 1,224, legit ≈ 542, across 4 languages
(en ≈ 482, hi_dev ≈ 445, hi_rom ≈ 445, **ta ≈ 394**). Tamil was previously
under-represented (98 rows); the expansion below 4×'d it.

Scam categories covered include: kyc, otp_scam, lottery, refund, courier,
electricity, job, **digital_arrest, instant_loan_app, upi_collect_scam,
fake_customer_care, investment_crypto, reward_points_expiry, utility_kyc,
marketplace_qr_scam**; plus legit hard-negatives (txn_alert, otp_legit, promo,
bill_legit, upi_legit, ecommerce_legit, govt_service_legit, chat).

## Two template sources

1. `TEMPLATES` in [`generate_dataset.py`](generate_dataset.py) — the base set.
2. [`templates_extra.json`](templates_extra.json) — additional archetypes, loaded
   automatically if present and **slot-validated** (templates using unknown slots
   or bad languages are skipped, not crashed). This is where machine- or
   batch-authored templates land.

## Extending it

1. Add archetypes to `templates_extra.json` (allowed slots: `bank amount acct
   name otp phone phish_url legit_url agency app`).
2. **Better:** append real labeled rows with `source` set to the real origin, and
   keep `template_id`/`category` honest so the group-aware evals stay meaningful.
