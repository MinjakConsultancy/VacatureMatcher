/** Gedeelde detail-batch fetch (Playwright page.evaluate + fetch_details_fn). */

import {
  readFileSync,
  writeFileSync,
  readdirSync,
  existsSync,
  mkdirSync,
} from "fs";
import { join } from "path";
import { fileURLToPath } from "url";
import { dirname } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
export const BATCH_SIZE = 15;

function readBrowserFn(path) {
  return readFileSync(path, "utf8")
    .replace(/^\/\/[^\n]*\n/, "")
    .replace(/;\s*$/, "")
    .trim();
}

export const FETCH_DETAILS_FN = readBrowserFn(
  join(__dirname, "fetch_details_fn.js")
);

export function isLoginText(text) {
  return text.includes("Rijksmailadres") && text.includes("Inloggen");
}

export function loadDetails(outDir, sinds, prefix) {
  const details = {};
  if (!existsSync(outDir)) return details;
  const pat = new RegExp(`^details-batch-${sinds}-${prefix}-\\d+\\.json$`);
  for (const name of readdirSync(outDir)) {
    if (!pat.test(name)) continue;
    const payload = JSON.parse(readFileSync(join(outDir, name), "utf8"));
    const val = payload?.result?.value ?? payload?.value ?? payload;
    if (val && typeof val === "object") Object.assign(details, val);
  }
  return details;
}

export async function fetchDetailBatches(page, urls, sinds, prefix, outDir) {
  mkdirSync(outDir, { recursive: true });
  const have = loadDetails(outDir, sinds, prefix);
  const missing = urls.filter((u) => !have[u] || isLoginText(have[u] || ""));
  console.log(`Details te fetchen (${prefix}): ${missing.length}`);
  let batch = 0;
  for (let i = 0; i < missing.length; i += BATCH_SIZE) {
    batch++;
    const chunk = missing.slice(i, i + BATCH_SIZE);
    const details = await page.evaluate(
      async ({ fn, urls }) => {
        const f = eval(fn);
        return await f(urls);
      },
      { fn: FETCH_DETAILS_FN, urls: chunk }
    );
    const path = join(
      outDir,
      `details-batch-${sinds}-${prefix}-${String(batch).padStart(2, "0")}.json`
    );
    writeFileSync(path, JSON.stringify({ value: details }, null, 2), "utf8");
    console.log(`  batch ${batch}: ${chunk.length} → ${path}`);
    if (i + BATCH_SIZE < missing.length) {
      await page.waitForTimeout(200);
    }
  }
  return loadDetails(outDir, sinds, prefix);
}
