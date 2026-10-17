#!/usr/bin/env bash
# Find funny moments, pack them chronologically, and burn only each part number.
set -eu
ROOT="$(dirname "$(readlink -f "$0")")"
if [ ! -x "$ROOT/.venv/bin/python" ]; then
    echo "[number-parts] .venv is missing; see README.md Setup."
    exit 1
fi
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
exec "$ROOT/.venv/bin/python" -m reelclip.parts "$@" --mode number-only
