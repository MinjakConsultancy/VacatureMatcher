#!/usr/bin/env bash
# Ververs vacaturedata: fetch → MinIO → Postgres.
# Gebruik: ./run_ververs.sh [sinds] [--headed] [--no-txt]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
PYTHON="${PYTHON:-python3}"
SINDS="${1:-5d}"
shift || true

SCRAPER="$REPO/scraper"
export SCRAPE_STAGING_DIR="${SCRAPE_STAGING_DIR:-/tmp/vacature-scrape}"
NODE_ARGS=(--sinds "$SINDS")

for arg in "$@"; do
  NODE_ARGS+=("$arg")
done

ensure_playwright() {
  unset PLAYWRIGHT_BROWSERS_PATH

  if [[ ! -d "$SCRAPER/node_modules/playwright" ]]; then
    echo "Playwright installeren in $SCRAPER…"
    (cd "$SCRAPER" && npm init -y >/dev/null 2>&1 && npm install playwright@^1.61.0 --no-save)
  fi

  if ! (cd "$SCRAPER" && node -e "require('playwright').chromium.launch({headless:true}).then(b=>b.close())" >/dev/null 2>&1); then
    echo "Playwright Chromium downloaden (eenmalig ~280MB)…"
    (cd "$SCRAPER" && node node_modules/playwright/cli.js install chromium --force)
  fi
}
ensure_playwright

export NODE_PATH="$SCRAPER/node_modules"
unset PLAYWRIGHT_BROWSERS_PATH

run_ververs_node() {
  local use_xvfb=0
  if [[ -z "${DISPLAY:-}" ]] && [[ "${IKWERK_SKIP_XVFB:-}" != "1" ]] && command -v Xvfb >/dev/null 2>&1; then
    local xvfb_display=":${RANDOM:-99}"
    Xvfb "$xvfb_display" -screen 0 1280x900x24 >/dev/null 2>&1 &
    export DISPLAY="$xvfb_display"
    sleep 1
    use_xvfb=1
  fi
  if [[ "$use_xvfb" == "1" ]]; then
    IKWERK_BROWSER_HEADLESS=0 node "$SCRIPT_DIR/ververs_data.mjs" "$@"
  else
    node "$SCRIPT_DIR/ververs_data.mjs" "$@"
  fi
}
run_ververs_node "${NODE_ARGS[@]}"

/usr/bin/env "$PYTHON" "$SCRIPT_DIR/merge_after_fetch.py"

if [[ " ${NODE_ARGS[*]} " != *" --no-txt "* ]]; then
  echo "Herbouw RAG-index uit Postgres…"
  if [[ -f "$REPO/rag/run.sh" ]]; then
    (cd "$REPO/rag" && ./run.sh build_index.py) || true
  fi
fi

echo "Verversen afgerond (sinds=$SINDS, staging=$SCRAPE_STAGING_DIR)."
