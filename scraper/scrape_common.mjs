/** Gedeelde scrape-helpers (sinds, args, staging). */

import { writeFileSync } from "fs";
import { join } from "path";

export const STAGING_BASE =
  process.env.SCRAPE_STAGING_DIR || "/tmp/vacature-scrape";

export const SINDS_DAYS = {
  gisteren: 1,
  "1d": 1,
  "3d": 3,
  "5d": 5,
  "7d": 7,
  "10d": 10,
  "1maand": 30,
  "30d": 30,
  all: null,
};

export function parseArgs(argv) {
  const opts = { sinds: "5d", headed: false };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--sinds" && argv[i + 1]) opts.sinds = argv[++i];
    else if (a.startsWith("--sinds=")) opts.sinds = a.split("=", 2)[1];
    else if (a === "--headed") opts.headed = true;
    else if (a === "--no-txt") opts.noTxt = true;
    else if (a === "--run-id" && argv[i + 1]) opts.runId = argv[++i];
    else if (a === "--filter" && argv[i + 1]) i++;
  }
  opts.sinds = opts.sinds.toLowerCase().replace(/\s+/g, "");
  if (!(opts.sinds in SINDS_DAYS)) {
    throw new Error(`Onbekende sinds-waarde: ${opts.sinds}`);
  }
  return opts;
}

export function todayTag() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}`;
}

export function cutoffDate(sinds) {
  const days = SINDS_DAYS[sinds];
  if (days === null) return null;
  const now = new Date();
  const local = new Date(
    now.toLocaleString("en-US", { timeZone: "Europe/Amsterdam" })
  );
  local.setHours(0, 0, 0, 0);
  local.setDate(local.getDate() - days);
  return local;
}

/** Query string for IkWerk component-rendering vacaturelijst (pagina + filters). */
export function ikwerkListQuery(filters = "", page = 1) {
  const parts = [
    "_hn:type=component-rendering",
    "_hn:ref=r82_r1_r4",
    `pagina=${page}`,
  ];
  const f = (filters || "").replace(/^\?/, "").replace(/^&/, "");
  if (f) {
    for (const seg of f.split("&")) {
      if (seg) parts.push(seg);
    }
  }
  return parts.join("&");
}

export function ikwerkListPath(filters = "", page = 1) {
  return `/werkaanbod/vacatures?${ikwerkListQuery(filters, page)}`;
}

const DUTCH_MONTHS = {
  januari: 0,
  februari: 1,
  maart: 2,
  april: 3,
  mei: 4,
  juni: 5,
  juli: 6,
  augustus: 7,
  september: 8,
  oktober: 9,
  november: 10,
  december: 11,
};

/** Parse Plaatsingsdatum from IkWerk list summary (fallback: detail-like text). */
export function parsePlaatsingsdatumFromListItem(vacancy) {
  const text =
    vacancy?.listText ||
    `${vacancy?.summary || ""} ${vacancy?.deadline || ""} ${vacancy?.title || ""}`;
  const m = text.match(/Plaatsingsdatum:\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})/i);
  if (!m) return null;
  const month = DUTCH_MONTHS[m[2].toLowerCase()];
  if (month === undefined) return null;
  const d = new Date(parseInt(m[3], 10), month, parseInt(m[1], 10));
  d.setHours(0, 0, 0, 0);
  return d;
}

export function listItemMatchesSinds(vacancy, sinds) {
  const cutoff = cutoffDate(sinds);
  if (!cutoff) return true;
  const placed = parsePlaatsingsdatumFromListItem(vacancy);
  if (!placed) return false;
  return placed.getTime() >= cutoff.getTime();
}

export function filterListBySinds(vacancies, sinds) {
  if (!sinds || sinds === "all" || SINDS_DAYS[sinds] === null) return vacancies;
  return vacancies.filter((v) => listItemMatchesSinds(v, sinds));
}

export function writeLastVervers(meta) {
  writeFileSync(
    join(STAGING_BASE, ".last-ververs.json"),
    JSON.stringify(meta, null, 2),
    "utf8"
  );
}
