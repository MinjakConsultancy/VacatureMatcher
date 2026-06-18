async (urls) => {
  const parser = new DOMParser();
  const out = {};
  for (const url of urls) {
    const resp = await fetch(url, { credentials: "include" });
    const doc = parser.parseFromString(await resp.text(), "text/html");
    const content = doc.querySelector("#content");
    out[url] = content ? content.innerText : doc.body.innerText;
  }
  return out;
}
