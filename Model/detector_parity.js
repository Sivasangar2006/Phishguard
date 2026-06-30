// Full-detector parity (JS side): run the on-device detector and confirm its
// verdicts match the backend's. Run AFTER detector_parity.py.
const fs = require("fs");
const path = require("path");

const EXT = path.join(__dirname, "..", "Extension");
require(path.join(EXT, "heuristics.js"));
require(path.join(EXT, "tier1.js"));
const Detector = require(path.join(EXT, "detector.js"));
const model = JSON.parse(fs.readFileSync(path.join(EXT, "model.json"), "utf-8"));
const data = JSON.parse(fs.readFileSync(path.join(__dirname, "detector_parity_data.json"), "utf-8"));

const det = Detector.make(model);

let fails = 0;
console.log("risk(py/js) | score(py/js) | ml(py/js)        | text");
console.log("-".repeat(78));
for (const row of data.rows) {
  const r = det.detect(row.text, "");
  const riskOk = r.risk === row.risk;
  const scoreOk = r.score === row.score;
  const mlOk = Math.abs((r.ml_prob ?? 0) - (row.ml ?? 0)) <= 2e-3;
  const ok = riskOk && scoreOk && mlOk;
  if (!ok) fails++;
  console.log(
    `${(ok ? "OK " : "XX ")}${row.risk}/${r.risk} | ${row.score}/${r.score} | ` +
    `${row.ml}/${r.ml_prob} | ${row.text.slice(0, 30)}`
  );
}
console.log("-".repeat(78));
console.log(fails === 0 ? "DETECTOR PARITY OK — on-device == backend" : `FAILED — ${fails} mismatches`);
process.exit(fails === 0 ? 0 : 1);
