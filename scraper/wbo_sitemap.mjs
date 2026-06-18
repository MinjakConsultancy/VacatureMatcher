/** Parse werkenbijdeoverheid.nl sitemap-vacatures.xml */

import { cutoffDate } from "./scrape_common.mjs";

export const WBO_SITEMAP_URL =
  "https://www.werkenbijdeoverheid.nl/sitemap-vacatures.xml";

/**
 * @param {string} xml
 * @returns {{ slug: string, url: string, lastmod: Date | null }[]}
 */
export function parseSitemapXml(xml) {
  const entries = [];
  const urlBlocks = xml.match(/<url>[\s\S]*?<\/url>/g) || [];
  for (const block of urlBlocks) {
    const locM = block.match(/<loc>([^<]+)<\/loc>/);
    if (!locM) continue;
    const url = locM[1].trim();
    if (!url.includes("/vacatures/") || url.endsWith("/bewaard")) continue;
    const slug = url.split("/vacatures/").pop()?.split("?")[0] || "";
    if (!slug) continue;
    let lastmod = null;
    const modM = block.match(/<lastmod>([^<]+)<\/lastmod>/);
    if (modM) {
      const d = new Date(modM[1].trim());
      if (!Number.isNaN(d.getTime())) lastmod = d;
    }
    entries.push({ slug, url, lastmod });
  }
  return entries;
}

/**
 * @param {{ slug: string, url: string, lastmod: Date | null }[]} entries
 * @param {string} sinds
 */
export function filterBySinds(entries, sinds) {
  const cutoff = cutoffDate(sinds);
  if (!cutoff) return entries;
  return entries.filter((e) => {
    if (!e.lastmod) return true;
    return e.lastmod >= cutoff;
  });
}

export async function fetchSitemapEntries(sinds) {
  const res = await fetch(WBO_SITEMAP_URL);
  if (!res.ok) {
    throw new Error(`Sitemap ophalen mislukt: ${res.status}`);
  }
  const xml = await res.text();
  const all = parseSitemapXml(xml);
  const filtered = filterBySinds(all, sinds);
  filtered.sort((a, b) => {
    const ta = a.lastmod ? a.lastmod.getTime() : 0;
    const tb = b.lastmod ? b.lastmod.getTime() : 0;
    return tb - ta;
  });
  return filtered;
}
