#!/usr/bin/env bash
# Open the guided terminal workflow, or pass explicit CLI arguments through.
set -eu
ROOT="$(dirname "$(readlink -f "$0")")"
cd "$ROOT"
if [ ! -x "$ROOT/.venv/bin/python" ]; then
    echo "[reelclip] .venv is missing; see README.md Setup."
    exit 1
fi
if [ "$#" -eq 0 ]; then
    exec "$ROOT/.venv/bin/python" -m reelclip --interactive
fi
exec "$ROOT/.venv/bin/python" -m reelclip "$@"
