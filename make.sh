#!/usr/bin/env bash
# Make clips and fill the Instagram posting queue. Never posts.
#
#   ./make.sh video.mp4       process a local file
#   ./make.sh                 scan channels.txt, then process links.txt
set -u
cd "$(dirname "${BASH_SOURCE[0]}")"

if [ ! -x ".venv/bin/python" ]; then
    echo "[reelclip] .venv is missing; run: python3 -m venv .venv"
    echo "[reelclip] then: .venv/bin/pip install -r requirements.txt"
    exit 1
fi

if [ "$#" -gt 0 ]; then
    exec .venv/bin/python -m reelclip --no-post "$@"
fi

if [ -f "channels.txt" ]; then
    .venv/bin/python -m reelclip --source || exit $?
fi

if [ -s "links.txt" ]; then
    exec .venv/bin/python -m reelclip --links --no-post
fi

echo "[reelclip] Nothing to make. Add channels to channels.txt or a video/link to links.txt."
exit 1
