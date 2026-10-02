#!/usr/bin/env bash
# Post the Instagram queue. Rendering and downloading never happen here.
#
#   ./post.sh          post the whole queue now
#   ./post.sh --due    respect POST_HOURS and scheduled queue gaps
#
set -u
cd "$(dirname "${BASH_SOURCE[0]}")"

if [ ! -x ".venv/bin/python" ]; then
    echo "[reelclip] .venv is missing; install the project first."
    exit 1
fi

case "${1:-}" in
    "") exec .venv/bin/python -m reelclip --post-now ;;
    --due|--post-due) exec .venv/bin/python -m reelclip --post-due ;;
    *) echo "Usage: ./post.sh [--due]"; exit 1 ;;
esac
