/** IkWerk scrape: login + lijst + details (alleen sinds-filter). */

import {
  writeFileSync,
  readFileSync,
  existsSync,
  mkdirSync,
  unlinkSync,
  readdirSync,
} from "fs";
import { join, dirname } from "path";
import { fileURLToPath, pathToFileURL } from "url";
import { randomUUID } from "crypto";
import {
  STAGING_BASE,
  parseArgs,
  todayTag,
  writeLastVervers,
  ikwerkListPath,
  cutoffDate,
  filterListBySinds,
} from "./scrape_common.mjs";
import { fetchDetailBatches } from "./scrape_details.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, "..");
const SCRAPER = __dirname;

const SINDS_URL = {
  gisteren: "gisteren",
  "1d": "gisteren",
  "3d": "3d",
  "5d": "5d",
  "7d": "7d",
  "10d": "10d",
  "1maand": "1maand",
  "30d": "1maand",
  all: null,
};

const USER_DATA = (() => {
  if (process.env.IKWERK_PLAYWRIGHT_PROFILE) {
    return process.env.IKWERK_PLAYWRIGHT_PROFILE;
  }
  return join(SCRAPER, ".playwright-ikwerk-profile");
})();
const STORAGE_STATE = join(USER_DATA, "ikwerk-storage-state.json");
const MAX_PAGES = parseInt(process.env.IKWERK_MAX_PAGES || "500", 10) || 500;
const FILTER_SET = "ikwerk";

const { chromium } = await import(
  pathToFileURL(join(SCRAPER, "node_modules/playwright/index.mjs")).href
);

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
  };
}

function readBrowserFn(path) {
  return readFileSync(path, "utf8")
    .replace(/^\/\/[^\n]*\n/, "")
    .replace(/;\s*$/, "")
    .trim();
}

const FETCH_LIST = readBrowserFn(join(SCRAPER, "fetch_list.js"));

function filtersFor(sinds) {
  const pub = SINDS_URL[sinds];
  if (pub === null) return "";
  return `publishedSince=${pub}`;
}

function clearStaleChromiumLock(userDataDir) {
  for (const name of ["SingletonLock", "SingletonSocket", "SingletonCookie"]) {
    const p = join(userDataDir, name);
    if (!existsSync(p)) continue;
    try {
      unlinkSync(p);
    } catch (e) {
      console.warn(`Kon ${name} niet verwijderen:`, e.message || e);
    }
  }
  try {
    for (const ent of readdirSync(userDataDir)) {
      if (/^[a-f0-9]+-\d+$/i.test(ent)) {
        unlinkSync(join(userDataDir, ent));
      }
    }
  } catch {
    /* ignore */
  }
}

function browserHeadless(opts) {
  if (opts.headed || process.env.IKWERK_BROWSER_HEADLESS === "0") return false;
  if (process.env.IKWERK_BROWSER_HEADLESS === "1") return true;
  return true;
}

function launchContextOpts(opts) {
  const launchOpts = {
    headless: browserHeadless(opts),
    viewport: { width: 1280, height: 900 },
    locale: "nl-NL",
    timezoneId: "Europe/Amsterdam",
    ignoreDefaultArgs: ["--enable-automation"],
    args: [
      "--disable-blink-features=AutomationControlled",
      "--no-sandbox",
      "--disable-dev-shm-usage",
    ],
  };
  if (existsSync(STORAGE_STATE)) {
    launchOpts.storageState = STORAGE_STATE;
  }
  return launchOpts;
}

async function typeHuman(locator, text) {
  await locator.click();
  await locator.fill("");
  await locator.pressSequentially(text, { delay: 45 });
}

async function exportStorageState(context) {
  mkdirSync(USER_DATA, { recursive: true });
  await context.storageState({ path: STORAGE_STATE });
}

async function persistSession(context) {
  try {
    await exportStorageState(context);
  } catch (e) {
    console.warn("Kon sessie niet opslaan:", e.message || e);
  }
}

async function dismissCookies(page) {
  await page.evaluate(() => {
    const close = [...document.querySelectorAll("button")].find(
      (b) => b.textContent.trim() === "×"
    );
    if (close) close.click();
  });
}

async function isAuthenticated(page) {
  await page.goto("https://www.ikwerkvoornederland.nl/werkaanbod/vacatures", {
    waitUntil: "domcontentloaded",
  });
  if (page.url().includes("/inloggen")) return false;
  try {
    await page.locator("#vacancies-list .vacancy").first().waitFor({ timeout: 15000 });
    return true;
  } catch {
    return false;
  }
}

async function login(page, creds, headed) {
  await page.goto("https://www.ikwerkvoornederland.nl/inloggen", {
    waitUntil: "networkidle",
  });
  await dismissCookies(page);
  await typeHuman(page.locator("#usernameField"), creds.email);
  await typeHuman(page.locator("#passwordField"), creds.password);
  await page.waitForFunction(
    () => typeof window.grecaptcha !== "undefined",
    null,
    { timeout: 30000 }
  );
  await page.waitForTimeout(1500);
  await page.locator('form[action$="/login"] button.g-recaptcha').click();
  try {
    await page.waitForURL((u) => !u.pathname.includes("/inloggen"), {
      timeout: 90000,
    });
  } catch {
    if (headed) {
      console.log("Automatisch inloggen mislukt. Log handmatig in (max 5 min)…");
      await page.waitForURL((u) => !u.pathname.includes("/inloggen"), {
        timeout: 300000,
      });
    } else {
      throw new Error(
        "Inloggen mislukt. Controleer IKWERK_EMAIL/IKWERK_PASSWORD in .env."
      );
    }
  }
}

async function ensureLoggedIn(page, context, creds, headed) {
  if (await isAuthenticated(page)) {
    await persistSession(context);
    return;
  }
  if (!creds.email || !creds.password) {
    throw new Error("Geen IKWERK_EMAIL/IKWERK_PASSWORD in .env of environment");
  }
  await login(page, creds, headed);
  if (!(await isAuthenticated(page))) {
    throw new Error("Ingelogd maar vacaturelijst niet bereikbaar. Probeer --headed.");
  }
  await persistSession(context);
}

async function fetchList(page, filters, sinds, outDir) {
  const url =
    "https://www.ikwerkvoornederland.nl" + ikwerkListPath(filters, 1);
  await page.goto(url, { waitUntil: "networkidle" });
  const cutoff = cutoffDate(sinds);
  const result = await page.evaluate(
    async ({ fn, filters, maxPages, cutoffMs }) => {
      const f = eval(fn);
      return await f(filters, maxPages, cutoffMs);
    },
    {
      fn: FETCH_LIST,
      filters,
      maxPages: MAX_PAGES,
      cutoffMs: cutoff ? cutoff.getTime() : null,
    }
  );
  if (result.error) throw new Error("Niet ingelogd bij IkWerk");
  const filtered = filterListBySinds(result.vacancies, sinds);
  result.vacancies = filtered;
  result.count = filtered.length;
  mkdirSync(outDir, { recursive: true });
  const out = join(outDir, `vacatures-summary-${sinds}-${todayTag()}.json`);
  writeFileSync(out, JSON.stringify(result.vacancies, null, 2), "utf8");
  console.log(
    `ikwerk: ${result.count} vacatures na sinds-filter (${result.rawCount ?? "?"} ruw, ${result.pages} pag.) → ${out}`
  );
  return { vacancies: result.vacancies, summaryPath: out };
}

export async function runIkwerkScrape(argv = process.argv) {
  const opts = parseArgs(argv);
  const creds = loadEnv();
  const filters = filtersFor(opts.sinds);
  const runId =
    opts.runId ||
    new Date().toISOString().replace(/[-:]/g, "").slice(0, 15) +
      "Z-" +
      randomUUID().slice(0, 8);
  const outDir = join(STAGING_BASE, runId, FILTER_SET);
  mkdirSync(STAGING_BASE, { recursive: true });
  mkdirSync(USER_DATA, { recursive: true });
  clearStaleChromiumLock(USER_DATA);

  const context = await chromium.launchPersistentContext(
    USER_DATA,
    launchContextOpts(opts)
  );
  const page = context.pages()[0] || (await context.newPage());
  try {
    await ensureLoggedIn(page, context, creds, opts.headed);
    const { vacancies, summaryPath } = await fetchList(
      page,
      filters,
      opts.sinds,
      outDir
    );
    await fetchDetailBatches(
      page,
      vacancies.map((v) => v.url),
      opts.sinds,
      FILTER_SET,
      outDir
    );
    const meta = {
      run_id: runId,
      sinds: opts.sinds,
      source: "ikwerk",
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
    console.log("IkWerk fetch klaar. run_id=" + runId);
    return meta;
  } finally {
    await context.close();
  }
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  runIkwerkScrape().catch((e) => {
    console.error(e.message || e);
    process.exit(1);
  });
}
