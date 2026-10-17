#!/usr/bin/env bash
# Canonical Linux launcher for Ziv's normal CLI.
# Explicit workflows and flags are forwarded to ``ziv``.
set -eu
ROOT="$(dirname "$(readlink -f "$0")")"
cd "$ROOT"
if [ ! -x "$ROOT/.venv/bin/python" ]; then
    echo "[ziv] .venv is missing; see README.md Setup." >&2
    exit 1
fi
exec "$ROOT/.venv/bin/python" -m ziv "$@"
