import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import { parseSummaryFromDetail } from "../../scraper/wbo_parse_summary.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const detailText = readFileSync(
  join(__dirname, "fixtures/wbo-detail.txt"),
  "utf8"
);
const url =
  "https://www.werkenbijdeoverheid.nl/vacatures/senior-data-engineer-voorbeeld-2026-001";

test("parseSummaryFromDetail extracts title and organisation", () => {
  const row = parseSummaryFromDetail(url, detailText);
  assert.equal(row.slug, "senior-data-engineer-voorbeeld-2026-001");
  assert.equal(row.title, "Senior Data Engineer");
  assert.equal(row.organisation, "Ministerie van Voorbeeld");
  assert.equal(row.location, "Den Haag");
  assert.equal(row.hours, "36 uur");
  assert.ok(row.scale.includes("4.624"));
  assert.equal(row.education, "Wo");
  assert.equal(row.deadline, "15 juli 2026");
  assert.ok(row.summary.includes("data pipelines"));
});
