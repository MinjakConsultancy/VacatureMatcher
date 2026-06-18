/**
 * Ververs vacaturedata: router naar IkWerk of Werkenbijdeoverheid.
 * Gebruik: node ververs_data.mjs --sinds 5d|all [--headed]
 *
 * SCRAPE_SOURCE=auto|ikwerk|wbo (default auto)
 */
import { readFileSync, existsSync, mkdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { parseArgs, STAGING_BASE } from "../../../../scraper/scrape_common.mjs";
import { runIkwerkScrape } from "../../../../scraper/ververs_ikwerk.mjs";
import { runWboScrape } from "../../../../scraper/ververs_wbo.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, "../../../..");

function loadEnv() {
  const envPath = join(REPO, ".env");
  const out = {};
  if (existsSync(envPath)) {
    for (const line of readFileSync(envPath, "utf8").split("\n")) {
      const t = line.trim();
      if (!t || t.startsWith("#")) continue;
      const eq = t.indexOf("=");
      if (eq < 0) continue;
      out[t.slice(0, eq).trim()] = t.slice(eq + 1).trim();
    }
  }
  return {
    email: process.env.IKWERK_EMAIL || out.IKWERK_EMAIL || "",
    password: process.env.IKWERK_PASSWORD || out.IKWERK_PASSWORD || "",
    scrapeSource: (
      process.env.SCRAPE_SOURCE ||
      out.SCRAPE_SOURCE ||
      "auto"
    ).toLowerCase(),
  };
}

function resolveSource(env) {
  const src = env.scrapeSource;
  if (src === "ikwerk" || src === "wbo") return src;
  if (src !== "auto") {
    throw new Error(`Onbekende SCRAPE_SOURCE: ${src} (auto|ikwerk|wbo)`);
  }
  if (env.email && env.password) return "ikwerk";
  return "wbo";
}

async function main() {
  const opts = parseArgs(process.argv);
  mkdirSync(STAGING_BASE, { recursive: true });
  const env = loadEnv();
  const source = resolveSource(env);
  console.log(`Scrape-bron: ${source}`);
  if (source === "ikwerk") {
    await runIkwerkScrape(process.argv);
  } else {
    await runWboScrape(process.argv);
  }
}

main().catch((e) => {
  console.error(e.message || e);
  process.exit(1);
});
