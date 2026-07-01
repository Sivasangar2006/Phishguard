// ===============================
// 🛡️ PhishGuard - Production Content Script
// ===============================
// Detection runs fully ON-DEVICE — no backend. The model + scorer +
// heuristics + fusion are loaded as content scripts before this file
// (see manifest.json). Verdicts are identical to the reference Python
// backend (verified by Model/detector_parity).

console.log("🛡️ PhishGuard: Protection Active");

// On-device detector (Tier 0 heuristics + Tier 1 ML + fusion).
const PG_DETECTOR =
    (typeof PHISHGUARD_MODEL !== "undefined" && typeof PhishGuardDetector !== "undefined")
        ? PhishGuardDetector.make(PHISHGUARD_MODEL)
        : null;

if (!PG_DETECTOR) {
    console.error("⚠ PhishGuard: model/detector not loaded — check manifest script order.");
}

// =====================================
// 1️⃣ SITE CONFIGURATION (ADD SITES HERE)
// =====================================

const SITE_CONFIG = {
    "web.whatsapp.com": {
        name: "WhatsApp",
        selector: 'div.copyable-text[data-pre-plain-text]'
    },
    "twitter.com": {
        name: "Twitter",
        selector: '[data-testid="tweetText"]'
    },
    "x.com": {
        name: "X",
        selector: '[data-testid="tweetText"]'
    },
    "mail.google.com": {
        name: "Gmail",
        selector: "div.a3s"
    },
    "linkedin.com": {
        name: "LinkedIn",
        selector: "div.feed-shared-update-v2__description"
    },
    // Dev-only: local test harness (extension-test.html). Lets the real
    // content script run against planted messages. Harmless in production
    // since no real site is served from localhost with .msg nodes.
    "localhost": {
        name: "TestHarness",
        selector: ".msg"
    }
};

// =====================================
// 2️⃣ STATE MANAGEMENT
// =====================================

const processedNodes = new WeakSet();     // Prevent reprocessing DOM nodes
const scannedTexts = new Set();           // Prevent duplicate text scanning
let activeConfig = null;

// =====================================
// 3️⃣ DETECT CURRENT SITE
// =====================================

const currentHost = window.location.hostname;

for (const domain in SITE_CONFIG) {
    if (currentHost.includes(domain)) {
        activeConfig = SITE_CONFIG[domain];
        console.log(`✅ PhishGuard Mode: ${activeConfig.name}`);
        break;
    }
}

// =====================================
// 4️⃣ START OBSERVER FOR MESSAGING SITES
// =====================================

if (activeConfig) {
    startObserver(activeConfig);
}

// =====================================
// 5️⃣ MUTATION OBSERVER ENGINE
// =====================================

function startObserver(config) {

    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {

            mutation.addedNodes.forEach((node) => {

                if (!(node instanceof HTMLElement)) return;

                // Case A: Node itself matches selector
                if (node.matches?.(config.selector)) {
                    processNode(node, config.name);
                }

                // Case B: Node contains matching elements
                const children = node.querySelectorAll?.(config.selector);
                children?.forEach(child => processNode(child, config.name));

            });
        });
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
}

// =====================================
// 6️⃣ PROCESS MESSAGE NODE
// =====================================

function processNode(node, sourceName) {

    if (processedNodes.has(node)) return;

    const text = node.innerText?.trim();
    if (!text || text.length < 5) return;

    console.log("📝 Extracted Text:", text);

    if (scannedTexts.has(text)) return;

    processedNodes.add(node);
    scannedTexts.add(text);

    triggerScan(text, node, sourceName);
}

// =====================================
// 7️⃣ BACKEND CONNECTOR
// =====================================

function triggerScan(text, node, sourceName) {

    if (!PG_DETECTOR) {
        node.style.borderBottom = "2px dotted gray";
        return;
    }

    // On-device detection — instant, no network.
    node.style.transition = "border 0.2s ease";
    const data = PG_DETECTOR.detect(text, window.location.href);
    handleResponse(data, node, text, sourceName);
}

// =====================================
// 8️⃣ HANDLE BACKEND RESPONSE
// =====================================

function handleResponse(data, node, originalText, sourceName) {

    if (!data || !data.risk) return;

    // Show the top-of-page verdict banner with a confidence score.
    showBanner(data.risk, data.confidence, data.reasons, originalText);

    if (data.risk === "high") {

        node.style.borderBottom = "4px solid red";
        node.style.backgroundColor = "rgba(255, 0, 0, 0.2)";
        node.title = `⚠️ PHISHING DETECTED: ${data.reasons?.join(", ") || ""}\n(Alt+Click to report)`;
        markReportable(node, originalText, sourceName);

        console.warn("🚨 PHISHING DETECTED:", originalText.substring(0, 40));

    } else if (data.risk === "medium") {

        node.style.borderBottom = "3px solid orange";
        node.title = `⚠ Suspicious: ${data.reasons?.join(", ") || ""}\n(Alt+Click to report)`;
        markReportable(node, originalText, sourceName);

    } else {

        node.style.borderBottom = "2px solid green";

        setTimeout(() => {
            node.style.borderBottom = "none";
            node.style.backgroundColor = "transparent";
        }, 3000);
    }
}

// =====================================
// 8️⃣ ⃣a VERDICT BANNER (top-of-page popup with confidence)
// =====================================

const BANNER_STYLES = {
    high:   { bg: "#c5221f", icon: "🚨", title: "Phishing attempt detected" },
    medium: { bg: "#b06000", icon: "⚠️", title: "Suspicious message" },
    low:    { bg: "#137333", icon: "✅", title: "Looks legitimate" },
};

let _bannerTimer = null;
let _bannerRisk = null;

function ensureBanner() {
    let el = document.getElementById("phishguard-banner");
    if (el) return el;
    el = document.createElement("div");
    el.id = "phishguard-banner";
    el.style.cssText =
        "position:fixed;top:12px;left:50%;transform:translateX(-50%);" +
        "z-index:2147483647;max-width:560px;width:calc(100% - 24px);" +
        "padding:12px 16px;border-radius:10px;color:#fff;" +
        "font-family:system-ui,'Segoe UI',Roboto,sans-serif;font-size:14px;" +
        "box-shadow:0 6px 24px rgba(0,0,0,.25);display:none;gap:10px;" +
        "align-items:flex-start;line-height:1.4;";
    (document.body || document.documentElement).appendChild(el);
    return el;
}

function showBanner(risk, confidence, reasons, text) {
    const cfg = BANNER_STYLES[risk];
    if (!cfg) return;

    // Don't let a later "legitimate" message overwrite a live phishing alert.
    if (_bannerRisk === "high" && risk !== "high") return;

    const conf = typeof confidence === "number" ? confidence : 0;
    const pct = Math.round((risk === "low" ? 1 - conf : conf) * 100);
    const tail = risk === "low" ? "% confidence it's safe" : "% confidence it's phishing";

    const el = ensureBanner();
    el.style.background = cfg.bg;
    el.style.display = "flex";
    el.replaceChildren();

    const icon = document.createElement("div");
    icon.style.cssText = "font-size:20px;line-height:1";
    icon.textContent = cfg.icon;

    const body = document.createElement("div");
    body.style.flex = "1";
    const head = document.createElement("div");
    head.style.fontWeight = "700";
    head.textContent = `${cfg.title} — ${pct}${tail}`;   // textContent = no injection
    body.appendChild(head);
    if (reasons && reasons.length) {
        const sub = document.createElement("div");
        sub.style.cssText = "font-size:12px;opacity:.92;margin-top:3px";
        sub.textContent = reasons.slice(0, 2).join("  ·  ");
        body.appendChild(sub);
    }

    // Optional on-demand LLM "second opinion" (local Ollama).
    if (typeof PhishGuardLLM !== "undefined" && text) {
        const aiLine = document.createElement("div");
        aiLine.style.cssText = "font-size:12.5px;margin-top:6px;display:none";
        const btn = document.createElement("button");
        btn.textContent = "🔍 Analyze with AI";
        btn.style.cssText = "margin-top:8px;background:rgba(255,255,255,.2);color:#fff;" +
            "border:1px solid rgba(255,255,255,.45);border-radius:6px;padding:4px 10px;" +
            "font-size:12px;cursor:pointer";
        btn.onclick = async () => {
            clearTimeout(_bannerTimer);        // keep the banner open while analyzing
            btn.disabled = true;
            btn.textContent = "Analyzing with local AI… (~6s)";
            aiLine.style.display = "block";
            aiLine.textContent = "";
            try {
                const r = await PhishGuardLLM.analyze(text);
                const v = String(r.verdict || "").toLowerCase();
                const c = Math.round((r.confidence || 0) * 100);
                aiLine.textContent = `🤖 AI (${PhishGuardLLM.MODEL}): ${v} · ${c}% · ${r.reason || ""}`;
                btn.textContent = "✓ Analyzed with AI";
            } catch (e) {
                aiLine.textContent = "AI unavailable — is Ollama running? " + e.message;
                btn.disabled = false;
                btn.textContent = "🔍 Retry AI";
            }
        };
        body.append(btn, aiLine);
    }

    const close = document.createElement("div");
    close.style.cssText = "cursor:pointer;font-size:18px;opacity:.85;padding:0 2px";
    close.textContent = "×";
    close.onclick = () => { el.style.display = "none"; _bannerRisk = null; };

    el.append(icon, body, close);
    _bannerRisk = risk;

    clearTimeout(_bannerTimer);
    // Auto-dismiss the "safe" banner; keep warnings until dismissed.
    if (risk === "low") {
        _bannerTimer = setTimeout(() => { el.style.display = "none"; _bannerRisk = null; }, 4000);
    }
}

// =====================================
// 8️⃣ ⃣b USER REPORTING (crowdsourced data — the real-data moat)
// =====================================
// Non-intrusive: Alt+Click a flagged message to report it. The backend
// redacts all PII before storing, so nothing sensitive leaves as raw text.

function markReportable(node, originalText, sourceName) {
    node.dataset.pgReport = originalText;
    node.dataset.pgSource = sourceName || "Unknown";
    node.style.cursor = "context-menu";
}

async function reportMessage(text, sourceName, userLabel) {
    // Redact PII ON-DEVICE, then store locally — no backend, nothing
    // sensitive leaves the browser.
    let redacted = text, counts = {};
    if (typeof PhishGuardRedact !== "undefined") {
        const r = PhishGuardRedact.redact(text);
        redacted = r.text;
        counts = r.counts;
    }
    const record = {
        ts: new Date().toISOString(),
        text: redacted,
        source: sourceName,
        url_host: location.hostname,
        user_label: userLabel || null,
        pii_removed: counts
    };

    try {
        if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
            const cur = await chrome.storage.local.get({ reports: [] });
            cur.reports.push(record);
            await chrome.storage.local.set({ reports: cur.reports });
        }
        console.log("🛡️ PhishGuard report saved locally. Redacted:",
            typeof PhishGuardRedact !== "undefined" ? PhishGuardRedact.summary(counts) : counts);
        return true;
    } catch (e) {
        console.error("⚠ Could not save report locally.", e);
        return false;
    }
}

// One delegated listener for the whole page (added once).
document.addEventListener("click", (e) => {
    if (!e.altKey) return;
    const node = e.target.closest?.("[data-pg-report]");
    if (!node) return;
    e.preventDefault();
    reportMessage(node.dataset.pgReport, node.dataset.pgSource, "phish").then((ok) => {
        if (ok) {
            const prev = node.style.outline;
            node.style.outline = "2px solid #137333";
            node.title = "✅ Reported to PhishGuard (PII redacted)";
            setTimeout(() => { node.style.outline = prev; }, 1500);
        }
    });
}, true);

// =====================================
// 9️⃣ WEBSITE PHISHING DETECTION (LOGIN PAGES)
// =====================================

window.addEventListener("load", () => {

    const hasPassword = document.querySelector('input[type="password"]');
    const hasCard = document.querySelector('input[name*="card" i]');
    const hasOTP = document.querySelector('input[name*="otp" i]');

    if (hasPassword || hasCard || hasOTP) {

        console.log("🔎 Sensitive form detected. Scanning page...");

        const pageText = extractVisibleText(2000);

        if (pageText.length > 20) {
            triggerScan(pageText, document.body, "Website");
        }
    }
});

// =====================================
// 🔟 SAFE VISIBLE TEXT EXTRACTION
// =====================================

function extractVisibleText(limit = 2000) {

    const walker = document.createTreeWalker(
        document.body,
        NodeFilter.SHOW_TEXT,
        {
            acceptNode: function (node) {

                if (!node.parentElement) return NodeFilter.FILTER_REJECT;

                const style = window.getComputedStyle(node.parentElement);

                if (
                    style.display === "none" ||
                    style.visibility === "hidden"
                ) {
                    return NodeFilter.FILTER_REJECT;
                }

                if (node.nodeValue.trim().length < 5) {
                    return NodeFilter.FILTER_REJECT;
                }

                return NodeFilter.FILTER_ACCEPT;
            }
        }
    );

    let text = "";

    while (walker.nextNode() && text.length < limit) {
        text += walker.currentNode.nodeValue.trim() + " ";
    }

    return text.slice(0, limit);
}
