// Scrape vacaturelijst via IkWerk component-rendering API (zelfde sessie).
// filters: query string zonder leading ?, bv. publishedSince=gisteren
// maxPages: optioneel veiligheidsnet (0 = onbeperkt)
// cutoffMs: UTC midnight cutoff (ms); null = geen client-side datumfilter
async (filters, maxPages, cutoffMs) => {
  const parser = new DOMParser();
  const seen = new Set();
  const all = [];
  let rawCount = 0;
  const pageLimit = maxPages && maxPages > 0 ? maxPages : 100000;
  const base = (filters || "").replace(/^\?/, "").replace(/^&/, "");

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

  function parsePlaatsingsdatum(v) {
    const text = v.listText || `${v.summary || ""} ${v.deadline || ""}`;
    const m = text.match(/Plaatsingsdatum:\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})/i);
    if (!m) return null;
    const month = DUTCH_MONTHS[m[2].toLowerCase()];
    if (month === undefined) return null;
    const d = new Date(parseInt(m[3], 10), month, parseInt(m[1], 10));
    d.setHours(0, 0, 0, 0);
    return d;
  }

  function matchesCutoff(v) {
    if (!cutoffMs) return true;
    const placed = parsePlaatsingsdatum(v);
    if (!placed) return false;
    return placed.getTime() >= cutoffMs;
  }

  function parseItem(section) {
    const titleA = section.querySelector(".vacancy__title a");
    if (!titleA) return null;
    const vacUrl = new URL(titleA.getAttribute("href"), window.location.origin).href;
    const org = section.querySelector(".vacancy__employer")?.textContent?.trim() || "";
    const lines = section.innerText
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);
    const orgIdx = lines.indexOf(org);
    let plaats = "",
      hours = "",
      scale = "",
      education = "",
      deadline = "",
      summary = "";
    if (orgIdx >= 0) {
      plaats = lines[orgIdx + 1] || "";
      hours = lines[orgIdx + 2] || "";
      scale = lines[orgIdx + 3] || "";
      education = lines[orgIdx + 4] || "";
      deadline = lines[orgIdx + 5] || "";
      summary = lines.slice(orgIdx + 6).join(" ");
    }
    const listText = section.innerText || "";
    return {
      slug: vacUrl.split("/").pop(),
      url: vacUrl,
      title: titleA.textContent.trim(),
      organisation: org,
      location: plaats,
      hours,
      scale,
      education,
      deadline,
      summary,
      listText,
    };
  }

  function parsePage(doc) {
    let added = 0;
    for (const sec of doc.querySelectorAll("#vacancies-list .vacancy")) {
      const v = parseItem(sec);
      if (!v || seen.has(v.url)) continue;
      seen.add(v.url);
      rawCount++;
      if (matchesCutoff(v)) {
        all.push(v);
        added++;
      }
    }
    return added;
  }

  function listUrl(page) {
    const parts = [
      "_hn:type=component-rendering",
      "_hn:ref=r82_r1_r4",
      `pagina=${page}`,
    ];
    if (base) {
      for (const seg of base.split("&")) {
        if (seg) parts.push(seg);
      }
    }
    return `/werkaanbod/vacatures?${parts.join("&")}`;
  }

  let page = 1;
  let lastPage = 1;
  const pageStats = [];
  while (page <= pageLimit) {
    const pageUrl = listUrl(page);
    const r = await fetch(pageUrl, { credentials: "include" });
    const t = await r.text();
    if (t.includes("Inloggen") && t.includes("Rijksmailadres")) {
      return {
        error: "not_logged_in",
        count: all.length,
        rawCount,
        vacancies: all,
        pageStats,
        filters: base,
      };
    }
    const doc = parser.parseFromString(t, "text/html");
    const before = all.length;
    const n = doc.querySelectorAll("#vacancies-list .vacancy").length;
    const added = parsePage(doc);
    pageStats.push({
      page,
      url: pageUrl,
      onPage: n,
      added,
      totalAfter: all.length,
    });
    if (!n) break;
    if (cutoffMs && added === 0) break;
    if (all.length === before && !cutoffMs) break;
    lastPage = page;
    page++;
  }

  return {
    count: all.length,
    rawCount,
    pages: lastPage,
    filters: base,
    vacancies: all,
    pageStats,
    cutoffMs,
  };
};
