# Session handover

## Goal

Maintain **Ziv** as a normal Linux-first command-line video clipping tool for
named links, named YouTube channels, resumable jobs, queue state, logs, and
safe YouTube-cookie diagnostics.

## Current state

- Public package: `ziv/`.
- Public command: `ziv`.
- Single launcher: `ziv.sh`.
- The old `reelclip` package, multiple shell launchers, and Windows launchers
  are removed.
- Ziv no longer opens a curses/TUI or interactive workflow by default. No
  arguments use the normal CLI error/help path; explicit commands and flags are
  required.
- Named links/channels are stored in `.ziv-state/catalog.json`, can be listed
  with `ziv links` / `ziv channels`, and can be added with `ziv add`.
- Existing `links.txt` and `channels.txt` are imported by catalog commands.
- YouTube diagnostics validate cookie configuration without reading or printing
  cookie contents. Browser login and CAPTCHA solving remain manual.

## Normal commands

```bash
./ziv.sh --help
./ziv.sh make video.mp4 --clips auto
./ziv.sh parts story.mp4
./ziv.sh add link "Interview" "https://www.youtube.com/watch?v=ID"
./ziv.sh add channel "Show" "@show" limit=3
./ziv.sh links
./ziv.sh channels
./ziv.sh doctor youtube
./ziv.sh post --due
```

## Important files

- `ziv/cli.py` — public command routing and catalog/doctor subcommands.
- `ziv/pipeline_cli.py` — normal clipping CLI and Instagram queue operations.
- `ziv/catalog.py` — named-source catalog and legacy text-file import.
- `ziv/core/downloader.py` — YouTube authentication validation and probing.
- `ziv/parts/` — story and number-only parts workflows.
- `ziv.sh` — one Linux CLI launcher.
- `tests/` — offline behavior and workflow coverage.

## Safety decisions

- Use `ziv/` imports and the `ziv` / `ziv-parts` console commands.
- New state uses `.ziv-state`; existing output, queues, cookies, credentials,
  and user media are never deleted automatically.
- Test files belong in GitHub. This handoff is development continuity, not a
  runtime requirement; sanitize it before publishing if needed.
- Never commit `.env`, `.ig_session`, browser cookies, downloaded media,
  output, virtual environments, or runtime state.

## Checks

### Tests

- Full offline suite after the CLI reversion: `244 passed, 2 skipped`.
- Focused CLI/catalog/YouTube tests: `25 passed`.

### Syntax

- `python3 -m compileall -q ziv tests` passed.
- `bash -n ziv.sh` passed.
- `git diff --check` passed.
- `python -m ziv --help` passed; no arguments return the normal CLI error.

### Media integration

- FFmpeg integration remains unavailable in this container because `ffmpeg` and
  `ffprobe` are not on `PATH`.

### YouTube

- Offline cookie configuration tests pass.
- A real browser-cookie/YouTube request remains unverified until a local browser
  session or exported cookies and network access are available.

## Next step

The normal-CLI reversion is verified and ready to commit.
