import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import {
  filterListBySinds,
  parsePlaatsingsdatumFromListItem,
} from "../../scraper/scrape_common.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));

const sample = [
  {
    summary:
      "Solliciteer voor 3 juli 2026 Arbeidsovereenkomst Vacature Plaatsingsdatum: 18 juni 2026",
  },
  {
    summary:
      "Solliciteer voor 1 jan 2025 Arbeidsovereenkomst Vacature Plaatsingsdatum: 10 januari 2024",
  },
];

test("parsePlaatsingsdatumFromListItem reads summary", () => {
  const d = parsePlaatsingsdatumFromListItem(sample[0]);
  assert.ok(d);
  assert.equal(d.getFullYear(), 2026);
  assert.equal(d.getMonth(), 5);
  assert.equal(d.getDate(), 18);
});

test("filterListBySinds gisteren keeps recent only", () => {
  const filtered = filterListBySinds(sample, "gisteren");
  assert.equal(filtered.length, 1);
  assert.ok(filtered[0].summary.includes("18 juni 2026"));
});

test("filterListBySinds all keeps everything", () => {
  assert.equal(filterListBySinds(sample, "all").length, 2);
});
