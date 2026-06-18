import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import {
  parseSitemapXml,
  filterBySinds,
} from "../../scraper/wbo_sitemap.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const fixture = readFileSync(
  join(__dirname, "fixtures/wbo-sitemap-snippet.xml"),
  "utf8"
);

test("parseSitemapXml extracts slug and lastmod", () => {
  const entries = parseSitemapXml(fixture);
  assert.equal(entries.length, 3);
  assert.equal(entries[0].slug, "objectmanager-RVB-2026-7170");
  assert.ok(entries[0].lastmod instanceof Date);
  assert.equal(entries[1].slug, "oud-vacature-2020-001");
  assert.equal(entries[2].slug, "recent-zonder-lastmod");
  assert.equal(entries[2].lastmod, null);
});

test("filterBySinds keeps recent and entries without lastmod", () => {
  const entries = parseSitemapXml(fixture);
  const filtered = filterBySinds(entries, "5d");
  const slugs = filtered.map((e) => e.slug);
  assert.ok(slugs.includes("objectmanager-RVB-2026-7170"));
  assert.ok(slugs.includes("recent-zonder-lastmod"));
  assert.ok(!slugs.includes("oud-vacature-2020-001"));
});

test("filterBySinds all returns everything", () => {
  const entries = parseSitemapXml(fixture);
  assert.equal(filterBySinds(entries, "all").length, 3);
});
