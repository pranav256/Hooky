#!/usr/bin/env bash
# Condense one video story and export chronological parts.
set -eu
ROOT="$(dirname "$(readlink -f "$0")")"
if [ ! -x "$ROOT/.venv/bin/python" ]; then
    echo "[parts] .venv is missing; see README.md Setup."
    exit 1
fi
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
exec "$ROOT/.venv/bin/python" -m reelclip.parts "$@"
