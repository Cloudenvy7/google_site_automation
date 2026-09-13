#!/usr/bin/env bash
# Eval runner. Unit tests always (seconds, no model). Canary with --with-model.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${PYTHON:-python3}"
# PYTHON overrides; otherwise whatever python3 is on PATH. No machine-specific
# venv path -- see scripts/config.py for why those were removed.
echo "== coverage unit tests =="
"$PY" "$HERE/test_coverage_unit.py" || exit 1
echo; echo "== site-build gate (hook) tests =="
"$PY" "$HERE/test_site_build_gate.py" || exit 1
if [ "${1:-}" = "--with-model" ]; then
  echo; echo "== canary eval (model: ${2:-haiku}) =="
  "$PY" "$HERE/canary_partial_read.py" "${2:-haiku}" || exit 1
fi
