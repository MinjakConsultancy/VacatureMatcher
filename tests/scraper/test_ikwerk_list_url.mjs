import assert from "node:assert/strict";
import { test } from "node:test";
import {
  ikwerkListPath,
  ikwerkListQuery,
} from "../../scraper/scrape_common.mjs";

test("ikwerkListQuery includes component-rendering params and pagina", () => {
  const q = ikwerkListQuery("publishedSince=gisteren", 1);
  assert.ok(q.includes("_hn:type=component-rendering"));
  assert.ok(q.includes("_hn:ref=r82_r1_r4"));
  assert.ok(q.includes("pagina=1"));
  assert.ok(q.includes("publishedSince=gisteren"));
});

test("ikwerkListQuery pagina 2 keeps publishedSince filter", () => {
  const q = ikwerkListQuery("publishedSince=5d", 2);
  assert.ok(q.includes("pagina=2"));
  assert.ok(q.includes("publishedSince=5d"));
});

test("ikwerkListPath builds werkaanbod URL", () => {
  assert.equal(
    ikwerkListPath("publishedSince=gisteren", 1),
    "/werkaanbod/vacatures?_hn:type=component-rendering&_hn:ref=r82_r1_r4&pagina=1&publishedSince=gisteren"
  );
});

test("ikwerkListQuery without filters omits publishedSince", () => {
  const q = ikwerkListQuery("", 1);
  assert.ok(!q.includes("publishedSince"));
  assert.ok(q.includes("pagina=1"));
});
