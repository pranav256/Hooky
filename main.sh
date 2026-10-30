#!/usr/bin/env bash
# Hooky Main All-in-One Runner & Setup (Linux & macOS)
# Usage:
#   ./main.sh          -> Auto-setup if needed, launch Web Studio, open browser
#   ./main.sh web      -> Launch Web Studio (http://127.0.0.1:8000)
#   ./main.sh make     -> Run autonomous batch pipeline
#   ./main.sh doctor   -> Run system health checks
#   ./main.sh <cmd>    -> Any Hooky CLI command
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$ROOT"

# 1. Run setup if .venv is missing
if [ ! -f "$ROOT/.venv/bin/python" ]; then
    printf '%s\n' '[hooky] First-time setup detected. Initializing environment...'
    bash "$ROOT/setup.sh" --non-interactive || true
fi

# 2. Ensure .env exists
if [ ! -f "$ROOT/.env" ] && [ -f "$ROOT/.env.example" ]; then
    cp "$ROOT/.env.example" "$ROOT/.env"
    printf '%s\n' '[hooky] Created .env configuration from template.'
fi

# 3. Determine command: default to web studio (which opens the browser)
if [ $# -eq 0 ]; then
    printf '\n%s\n\n' '[hooky] 🚀 Launching Hooky Web Studio...'
    exec "$ROOT/.venv/bin/python" -m hooky web
else
    exec "$ROOT/.venv/bin/python" -m hooky "$@"
fi
