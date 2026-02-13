// ===============================
// 🛡️ PhishGuard - Production Content Script
// ===============================

console.log("🛡️ PhishGuard: Protection Active");

// =====================================
// 1️⃣ SITE CONFIGURATION (ADD SITES HERE)
// =====================================

const SITE_CONFIG = {
    "web.whatsapp.com": {
        name: "WhatsApp",
        selector: "span.selectable-text"
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

async function triggerScan(text, node, sourceName) {

    // Visual state: scanning
    node.style.borderBottom = "2px solid orange";
    node.style.transition = "border 0.2s ease";

    try {

        const response = await fetch("http://localhost:8000/scan", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                text: text,
                source: sourceName,
                url: window.location.href
            })
        });

        if (!response.ok) throw new Error("Backend Error");

        const data = await response.json();

        handleResponse(data, node, text);

    } catch (error) {
        console.error("⚠ Backend unreachable. Is FastAPI running?");
        node.style.borderBottom = "2px dotted gray";
    }
}

// =====================================
// 8️⃣ HANDLE BACKEND RESPONSE
// =====================================

function handleResponse(data, node, originalText) {

    if (!data || !data.risk) return;

    if (data.risk === "high") {

        node.style.borderBottom = "4px solid red";
        node.style.backgroundColor = "rgba(255, 0, 0, 0.2)";
        node.title = `⚠️ PHISHING DETECTED: ${data.reasons?.join(", ") || ""}`;

        console.warn("🚨 PHISHING DETECTED:", originalText.substring(0, 40));

    } else if (data.risk === "medium") {

        node.style.borderBottom = "3px solid orange";
        node.title = `⚠ Suspicious: ${data.reasons?.join(", ") || ""}`;

    } else {

        node.style.borderBottom = "2px solid green";

        setTimeout(() => {
            node.style.borderBottom = "none";
            node.style.backgroundColor = "transparent";
        }, 3000);
    }
}

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
