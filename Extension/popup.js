// PhishGuard popup: detection is fully on-device, so there's no backend to
// ping. Show on-device status + how many messages have been reported.

async function refresh() {
    const dot = document.getElementById("dot");
    const status = document.getElementById("status");
    const tiers = document.getElementById("tiers");

    dot.className = "dot ok";
    status.textContent = "On-device protection active";
    tiers.hidden = false;
    document.getElementById("t0").textContent = "heuristics";
    document.getElementById("t1").textContent = "on-device ML (no backend)";
    document.getElementById("t1").style.color = "#137333";

    try {
        if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
            const { reports = [] } = await chrome.storage.local.get({ reports: [] });
            const r = document.getElementById("reports");
            if (r) r.textContent = String(reports.length);
        }
    } catch { /* ignore */ }
}

refresh();
