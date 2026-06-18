/** Werkenbijdeoverheid scrape: sitemap + details (geen login). */

import { writeFileSync, mkdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath, pathToFileURL } from "url";
import { randomUUID } from "crypto";
import {
  STAGING_BASE,
  parseArgs,
  todayTag,
  writeLastVervers,
} from "./scrape_common.mjs";
import { fetchDetailBatches } from "./scrape_details.mjs";
import { fetchSitemapEntries } from "./wbo_sitemap.mjs";
import { parseSummaryFromDetail } from "./wbo_parse_summary.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SCRAPER = __dirname;
const FILTER_SET = "wbo";

const { chromium } = await import(
  pathToFileURL(join(SCRAPER, "node_modules/playwright/index.mjs")).href
);

function browserHeadless(opts) {
  if (opts.headed || process.env.IKWERK_BROWSER_HEADLESS === "0") return false;
  return true;
}

export async function runWboScrape(argv = process.argv) {
  const opts = parseArgs(argv);
  const runId =
    opts.runId ||
    new Date().toISOString().replace(/[-:]/g, "").slice(0, 15) +
      "Z-" +
      randomUUID().slice(0, 8);
  const outDir = join(STAGING_BASE, runId, FILTER_SET);
  mkdirSync(STAGING_BASE, { recursive: true });
  mkdirSync(outDir, { recursive: true });

  console.log(`WbO sitemap ophalen (sinds=${opts.sinds})…`);
  const entries = await fetchSitemapEntries(opts.sinds);
  console.log(`WbO: ${entries.length} vacatures na sinds-filter`);

  const browser = await chromium.launch({
    headless: browserHeadless(opts),
    args: ["--no-sandbox", "--disable-dev-shm-usage"],
  });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    locale: "nl-NL",
    timezoneId: "Europe/Amsterdam",
  });
  const page = await context.newPage();
  try {
    const urls = entries.map((e) => e.url);
    const details = await fetchDetailBatches(
      page,
      urls,
      opts.sinds,
      FILTER_SET,
      outDir
    );

    const summaries = [];
    for (const entry of entries) {
      const text = details[entry.url];
      if (text) {
        summaries.push(parseSummaryFromDetail(entry.url, text));
      } else {
        summaries.push({
          slug: entry.slug,
          url: entry.url,
          title: entry.slug,
        });
      }
    }

    const summaryPath = join(
      outDir,
      `vacatures-summary-${opts.sinds}-${todayTag()}.json`
    );
    writeFileSync(summaryPath, JSON.stringify(summaries, null, 2), "utf8");
    console.log(`WbO summary: ${summaries.length} → ${summaryPath}`);

    const meta = {
      run_id: runId,
      sinds: opts.sinds,
      source: "wbo",
      filter_set: FILTER_SET,
      filter_sets: [FILTER_SET],
      summaries: [
        {
          filter_set: FILTER_SET,
          path: summaryPath,
          out_dir: outDir,
        },
      ],
      staging_dir: STAGING_BASE,
      at: new Date().toISOString(),
    };
    writeLastVervers(meta);
    console.log("WbO fetch klaar. run_id=" + runId);
    return meta;
  } finally {
    await context.close();
    await browser.close();
  }
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  runWboScrape().catch((e) => {
    console.error(e.message || e);
    process.exit(1);
  });
}
