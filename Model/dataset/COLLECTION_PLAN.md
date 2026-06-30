# PhishGuard — Real Vernacular Phishing Data-Collection Plan

> **Why this document exists.** PhishGuard's model currently trains on
> *synthetic* seed data. That data has hit its ceiling (the "unseen template"
> eval saturates at ~1.0; see [`README.md`](README.md)). The single highest-value
> thing the project can do next is collect, label, and carefully release a
> **real** Indian vernacular phishing corpus — the artifact that doesn't exist
> publicly and that would make the model actually work. This is the plan for that.
>
> **Status:** plan, not legal advice. Items flagged ⚖️ need qualified counsel
> (an Indian data-protection lawyer) before execution.

---

## 1. Executive summary

- **Goal:** a labeled, multilingual (Hindi, Tamil, Telugu, Bengali, Marathi… +
  code-mixed) corpus of real phishing/scam messages and matched legitimate
  messages, with a held-out benchmark, released safely under a documented
  license.
- **Core constraint:** real scam messages contain **third-party PII** (victim
  names, OTPs, account/card numbers, phones). Collection and release are
  governed by India's **DPDP Act 2023** and, for any EU users, **GDPR**.
  Redaction-before-storage is non-negotiable and already implemented
  ([`Backend/redact.py`](../../Backend/redact.py)).
- **Strategy:** start with the source we control and that has clean consent —
  **in-extension crowdsourced reporting** — then layer in honeypots and public
  archives. Label with native speakers, measure inter-annotator agreement, and
  evaluate with leakage-proof splits.
- **Primary risk:** volume and representativeness. One person cannot collect a
  balanced multilingual corpus quickly; partnerships and incentives matter.

## 2. Phased roadmap

### Month 0–1 — Foundations (you can start today)
- ✅ Ship the redaction + `/report` pipeline (done — redacts before storage).
- Add a one-tap **"Report as phishing / not phishing"** affordance in the
  extension (Alt+Click hook exists; make it a visible button).
- Stand up storage: append-only JSONL → a small Postgres/SQLite with a schema
  (§5). Encrypt at rest.
- Write the **consent copy** shown before a user's first report ⚖️.
- Seed a **honeypot**: 2–3 phone numbers + email addresses posted where scrapers
  harvest them; auto-ingest incoming SMS/email.
- Deliverable: 200–500 real, redacted, *unlabeled* messages.

### Month 1–3 — Labeling & first benchmark
- Recruit 2 native annotators **per language** (start Hindi + Tamil).
- Finalize the annotation guideline (§4) and label 2–3k messages with
  double-annotation; measure κ; adjudicate.
- Publish **v0 benchmark**: train/val/**temporal-test** split (§7).
- Retrain Tier 1 on real + synthetic; report the honest delta vs synthetic-only.
- Deliverable: labeled v0 set + a real-world F1 number (expected: lower than
  synthetic — that's the point).

### Month 3–6 — Scale, coverage, release
- Expand to Telugu, Bengali, Marathi; fill scam-type and temporal gaps (§6).
- Add adversarial/evasive variants; add a drift-monitoring loop.
- Legal review of the release ⚖️; produce a **Datasheet for Datasets**.
- Release the **gated benchmark** (§6) + a public leaderboard.
- Deliverable: citable dataset + paper/blog.

## 3. Data sources & acquisition

Ranked by *start-ability* and consent-cleanliness:

| Source | Volume | Languages | Consent / legality | Notes |
|--------|--------|-----------|--------------------|-------|
| **In-extension reporting** | grows with users | whatever users get | Cleanest — explicit user consent at report time | Start here. Already built. |
| **Honeypots** (seed numbers/emails) | low→med | broad | You own the inbox → strong basis | Cheap, no victim PII beyond the scammer's content |
| **Public scam-awareness groups** (Telegram/Reddit/Twitter where people post scams they got) | med | broad | Public posts, but re-use needs care ⚖️ | Noisy; needs dedup + verification |
| **Govt / telecom portals** — CERT-In, cybercrime.gov.in, Sanchar Saathi / **Chakshu** (report-suspected-fraud) | potentially high | broad | Access likely needs partnership/MoU ⚖️ | Verify current access terms — *do not assume a public bulk feed exists* |
| **Telecom DLT / spam feeds** (TRAI framework) | high | broad | Requires operator partnership ⚖️ | Aspirational; long lead time |
| **NGO / consumer-forum / bank fraud-desk partnerships** | med | regional depth | Data-sharing agreement ⚖️ | High-quality, pre-triaged samples |
| **Academic corpora / translated phishing kits** | low | mixed | Check each license | Useful for bootstrapping legit/scam URL patterns |

**Month-1 priority:** in-extension reports + honeypots (both self-owned, clean
consent), supplemented by manually curated public-group samples for diversity.
*Every volume/access figure above is an estimate — verify before committing.*

## 4. Annotation & labeling methodology

**Label schema** (per message):
- `label`: phish / legit (primary)
- `scam_type`: multi-label from the taxonomy in §6 (kyc, otp_scam, digital_arrest,
  loan_app, upi_collect, courier, investment, …)
- `lang` + `script`; `code_mixed`: bool
- `severity`: low / med / high (credential-harvest & money-transfer = high)
- `pii_types_present`: which categories the redactor stripped (audit trail)

**Guideline — the hard edge cases** (these define quality):
- *Legit OTP vs scam OTP*: "**123456 is your OTP, do not share**" = legit;
  "**share OTP 123456 to verify**" = phish. Direction of the ask is the signal.
- *Marketing vs bait*: a real sale with the brand's true domain = legit; urgency +
  look-alike domain = phish.
- *Real bank alert vs impersonation*: transaction receipts = legit; "account
  suspended, click to restore" = phish.

**Process:**
- 2 native annotators per language; **double-annotate** every item.
- Target **Cohen's κ ≥ 0.75**; below that, refine the guideline and re-train
  annotators before scaling.
- Disagreements → adjudication by a third senior annotator; adjudicated items
  become the **gold set** for ongoing QC and annotator calibration.
- Tooling: **Label Studio** or **Doccano** (both self-hostable, support custom
  labels and multi-annotator workflows).

**Vernacular-specific challenges to bake into the guideline:**
- Transliteration variants ("paisa"/"paise"/"पैसा") — label by meaning, not spelling.
- Code-mixing within one message — tag `code_mixed`, don't force one `lang`.
- Inconsistent scripts (Tamil typed in Latin) — record the script as written.

## 5. Storage schema

```jsonc
{
  "id": "uuid",
  "ts": "ISO-8601",
  "text": "<redacted message>",        // PII stripped BEFORE write
  "lang": "ta", "script": "taml", "code_mixed": false,
  "label": "phish", "scam_type": ["digital_arrest"],
  "severity": "high",
  "source": "extension_report|honeypot|partner|public",
  "url_host": "sbi-verify.xyz",          // host only, never full URL
  "pii_types_present": ["OTP","PHONE"],  // audit, from redactor
  "annotators": ["a1","a2"], "kappa_item": 1.0,
  "first_seen": "ISO-8601"               // for temporal splits
}
```
Encrypt at rest; access-controlled; raw (pre-redaction) text is **never**
persisted.

## 6. Coverage, class balance & adversarial robustness

**Scam-type taxonomy to cover** (current synthetic set already spans most):
kyc, otp_scam, lottery, refund, courier/customs, **digital_arrest**, loan_app,
investment/crypto, job, upi_collect, fake_customer_care, electricity/gas/utility,
reward_points, marketplace_qr, sextortion (handle with care), **+ a "novel"
bucket** for emerging types.

**Targets & gap-filling:**
- Track a coverage matrix of *language × scam_type × month*; surface empty cells.
- Maintain meaningful **hard-negative** ratio (legit OTP, real bank alerts,
  genuine promos) — the model's current weakness is over-flagging unseen legit.
- **Temporal coverage:** scams drift fast (digital-arrest barely existed before
  2023). Keep ingesting; never freeze.
- **Adversarial variants:** homoglyphs, inserted spaces/zero-width chars,
  vernacular leetspeak, emoji obfuscation. Generate some; harvest the rest.

## 7. Benchmark & evaluation design

Leakage is the enemy. Three split types, reported together:
1. **Random split** — in-distribution ceiling only (not a headline number).
2. **Group split by campaign/sender/template** — generalization to new phrasing.
3. **Temporal split** — train on past, test on a *later* time window. This is the
   number that reflects real deployment (drift). **Report this as primary.**
4. A small **human-curated real-world test set**, never used for training.

**Metrics:** F1 + precision/recall, **per-language breakdown**, **false-positive
rate on hard negatives** (the failure mode we already see), and **calibration**
(reliability curve) since the backend blends the probability. Always report class
balance alongside, and never quote the random-split number as skill.

## 8. Ethics, safety & governance

- **Never republish live malicious URLs** — store host only; defang in any
  release (`hxxp://`, `[.]`). Coordinate takedowns with CERT-In where possible.
- **Victim-first PII protection** — redact before storage (done); periodic audits
  that the redactor still catches new PII shapes.
- **Licensing & access** ⚖️ — favour **gated access** (request form + usage
  agreement) over a fully open dump, given the sensitivity; consider CC-BY-NC for
  derived, fully-scrubbed subsets.
- **Documentation** — ship a **Datasheet for Datasets** (motivation, composition,
  collection, preprocessing, distribution, maintenance).
- **Bias** — monitor and correct under-representation of languages/regions so the
  model isn't only good at Hindi.
- **Governance** — a lightweight review step before each release; a contribution
  policy; an abuse/contact channel.

## 9. Compliance & safety checklist (one page)

- [ ] Consent copy shown before a user's first report ⚖️
- [ ] PII redaction runs **before** any persistence (✅ implemented)
- [ ] Raw, unredacted text never written to disk or logs
- [ ] Storage encrypted at rest; access-controlled
- [ ] URLs stored as host-only; live URLs defanged in any export
- [ ] Retention limit defined and enforced (e.g. raw honeypot inbox purged after N days)
- [ ] Lawful basis documented per source (DPDP) ⚖️
- [ ] Data-sharing agreements signed for partner sources ⚖️
- [ ] Datasheet for Datasets written before release
- [ ] Release is gated (usage agreement) unless fully scrubbed
- [ ] Annotator agreement (κ) measured and ≥ target before scaling
- [ ] Temporal test split held out and never trained on

## 10. Honest risks & open questions

- **Volume/representativeness** is the real risk — a balanced multilingual corpus
  needs users or partners, not just code. Plan for slow, steady growth.
- **DPDP specifics** ⚖️ — lawful basis for processing third-party PII inside
  reported messages, and the bar for "anonymized" release, need a lawyer. Do not
  ship a public dataset on the strength of this document alone.
- **Government/telecom feeds** may not offer the bulk access often assumed —
  treat as partnership efforts with long lead times, not turnkey sources.
- **Redactor recall** — regex misses novel PII shapes; pair it with periodic
  audits and consider a lightweight on-device NER before any LLM (Tier 2) use.
- **Label drift** — as scam types evolve, the guideline and taxonomy must be
  living documents.

---

*This plan is the bridge from a working synthetic-data MVP to a defensible,
real-world detector. The hard part isn't the model — it's getting real data,
safely.*
