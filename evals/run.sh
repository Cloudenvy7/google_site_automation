#!/usr/bin/env bash
# Eval runner. Unit tests always (seconds, no model). Canary with --with-model.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${PYTHON:-python3}"
[ -x "/home/tyler/Projects/Blackfox Studios/.venv/bin/python" ] && PY="/home/tyler/Projects/Blackfox Studios/.venv/bin/python"
echo "== coverage unit tests =="
"$PY" "$HERE/test_coverage_unit.py" || exit 1
if [ "${1:-}" = "--with-model" ]; then
  echo; echo "== canary eval (model: ${2:-haiku}) =="
  "$PY" "$HERE/canary_partial_read.py" "${2:-haiku}" || exit 1
fi
