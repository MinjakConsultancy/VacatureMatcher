/** Metadata uit WbO detailtekst (#content innerText). */

/**
 * @param {string} url
 * @param {string} detailText
 * @returns {Record<string, string>}
 */
export function parseSummaryFromDetail(url, detailText) {
  const slug = url.split("/vacatures/").pop()?.split("?")[0] || "";
  const lines = detailText
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);

  let title = "";
  let organisation = "";
  let location = "";
  let hours = "";
  let scale = "";
  let education = "";
  let deadline = "";
  let summary = "";

  const skip = new Set([
    "Naar overzicht",
    "Op deze pagina",
    "Vacature",
    "Stage",
    "Solliciteren op externe site",
    "Bekijk vacature",
    "Feedback",
  ]);

  let i = 0;
  while (i < lines.length && skip.has(lines[i])) i++;

  if (i < lines.length && !lines[i].startsWith("Dit ")) {
    title = lines[i++];
  }
  if (i < lines.length && !lines[i].startsWith("Solliciteer") && !lines[i].startsWith("Dit ")) {
    organisation = lines[i++];
  }
  if (i < lines.length && lines[i].startsWith("Solliciteer voor")) {
    deadline = lines[i].replace(/^Solliciteer voor\s*/i, "").trim();
    i++;
  }

  for (; i < lines.length; i++) {
    const line = lines[i];
    if (line.startsWith("Plaatsingsdatum:")) continue;
    if (line.match(/€[\d.,\s-]+/) && line.length < 60) {
      if (!scale) scale = line;
      continue;
    }
    if (line.match(/^\d+\s*-\s*\d+\s*uur$/i) || line.match(/^\d+\s*uur$/i)) {
      hours = line;
      continue;
    }
    if (line.match(/^(Wo|Hbo|Mbo|Gepromoveerd)/i) && line.length < 40) {
      education = line;
      continue;
    }
    if (
      !location &&
      line.length < 80 &&
      !line.startsWith("Dit ") &&
      !line.startsWith("Arbeidsovereenkomst") &&
      !line.startsWith("Tijdelijke") &&
      !line.startsWith("Vaste") &&
      organisation &&
      line !== organisation
    ) {
      const looksLikePlace =
        line.includes("(") ||
        /^[A-Z][a-z]+(\s|$)/.test(line) ||
        line.includes("Den Haag") ||
        line.includes("Utrecht");
      if (looksLikePlace && !line.includes("€")) {
        location = line;
        continue;
      }
    }
    if (line.startsWith("Dit ga je doen")) {
      summary = lines.slice(i + 1, i + 4).join(" ").slice(0, 400);
      break;
    }
  }

  return {
    slug,
    url,
    title: title || slug,
    organisation,
    location,
    hours,
    scale,
    education,
    deadline,
    summary,
  };
}
