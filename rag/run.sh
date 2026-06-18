#!/usr/bin/env bash
# Wrapper: zet PYTHONPATH en draait build_index.py of query.py
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PY="${PYTHON:-/usr/bin/python3}"
DEPS="${ROOT}/deps"

if [[ ! -d "${DEPS}/sklearn" ]]; then
  echo "Installeer RAG-deps in ${DEPS}..." >&2
  "$PY" -m pip install --target "${DEPS}" -r "${ROOT}/requirements.txt" >&2
fi

export PYTHONPATH="${DEPS}:${ROOT}"
exec "$PY" "$@"
