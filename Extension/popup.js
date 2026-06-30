// PhishGuard popup: pings the local backend and shows live status.

const BACKEND = "http://localhost:8000";

async function refresh() {
    const dot = document.getElementById("dot");
    const status = document.getElementById("status");
    const tiers = document.getElementById("tiers");

    try {
        const res = await fetch(`${BACKEND}/health`, { cache: "no-store" });
        if (!res.ok) throw new Error("bad status");
        const data = await res.json();

        dot.className = "dot ok";
        status.textContent = "Protection active";
        tiers.hidden = false;
        document.getElementById("t0").textContent = data.tier0 || "—";

        const t1 = document.getElementById("t1");
        const ready = (data.tier1 || "").startsWith("ready");
        t1.textContent = ready ? "ready" : "not loaded (heuristics only)";
        t1.style.color = ready ? "#137333" : "#b06000";
    } catch {
        dot.className = "dot bad";
        status.innerHTML = 'Backend offline — start it on <code>:8000</code>';
        tiers.hidden = true;
    }
}

refresh();
