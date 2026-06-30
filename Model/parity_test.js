// Step 2 of the parity test: run the JS scorer on the same messages and
// compare to Python's predict_proba. Run AFTER parity_test.py.
//   node parity_test.js
const fs = require("fs");
const path = require("path");

const PhishGuardTier1 = require(path.join(__dirname, "..", "Extension", "tier1.js"));
const model = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "Extension", "model.json"), "utf-8"));
const data = JSON.parse(fs.readFileSync(path.join(__dirname, "parity_data.json"), "utf-8"));

const scorer = PhishGuardTier1.makeScorer(model);

let maxDiff = 0;
let fails = 0;
const TOL = 1e-3;

console.log("msg# |  python  |   js    |  diff");
console.log("-----+----------+---------+--------");
data.messages.forEach((m, i) => {
  const py = data.python[i];
  const js = scorer.proba(m);
  const diff = Math.abs(py - js);
  maxDiff = Math.max(maxDiff, diff);
  if (diff > TOL) fails++;
  const flag = diff > TOL ? "  <-- MISMATCH" : "";
  console.log(
    `${String(i).padStart(4)} | ${py.toFixed(5)} | ${js.toFixed(5)} | ${diff.toExponential(1)}${flag}`
  );
});

console.log("-----+----------+---------+--------");
console.log(`max abs diff: ${maxDiff.toExponential(2)}   (tolerance ${TOL})`);
console.log(fails === 0 ? "PARITY OK — JS matches Python" : `PARITY FAILED — ${fails} mismatches`);
process.exit(fails === 0 ? 0 : 1);
