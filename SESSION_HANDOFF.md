# Session handover

## Goal

Build **Ziv**, a Linux-first terminal GUI for managing long-video clipping:
named links, named YouTube channels, resumable clipping jobs, queue state,
logs, and safe YouTube-cookie diagnostics. The main screen is a colored source
browser, not a literal system monitor.

## Current state

- Public package facade: `ziv/`.
- Public command: `ziv`.
- Single Linux launcher: `ziv.sh`.
- All application modules live under the `ziv/` package.
- The old multiple `.sh` and Windows `.bat` launchers were removed.
- The TUI is curses-based, dependency-light, colored, and refuses to prompt on a
  redirected/non-TTY stdin.
- The catalog stores named sources in `.ziv-state/catalog.json`, imports the
  existing `links.txt` and `channels.txt`, and materializes named entries back
  into those workflow files for pipeline commands.
- The TUI can add/delete/import sources and launch one selected resumable job.
- The main screen is now a colored LINKS / CHANNELS source browser with
  friendly names, status badges, selected-row highlighting, and a detail pane;
  queue/log tabs are secondary and CPU/memory telemetry is not the focus.
- The main view is LINKS / CHANNELS with friendly names, colored status badges,
  selected-row highlighting, and a detail pane. Queue and logs are secondary
  tabs; CPU/memory telemetry is not the product focus.
- YouTube diagnostics validate browser-cookie configuration and cookie-file
  metadata without opening or printing cookie contents. Browser login and
  CAPTCHA solving remain manual.

## TUI controls

- `a` add a named link
- `c` add a named channel
- `i` import `links.txt` and `channels.txt`
- `d` delete the selected catalog record
- `R` run the selected source in a child process
- `x` request safe stop of the running child
- `r` refresh; `1`-`4` or Tab switch views; `[`/`]` switch links/channels;
  `j`/`k` navigate; `q` quit

## Important files

- `ziv/cli.py` — public command routing and catalog/doctor subcommands.
- `ziv.sh` — only shell launcher; no arguments open the TUI.
- `ziv/catalog.py` — catalog persistence, queue/log views.
- `ziv/tui.py` — terminal-independent model, rendering, curses adapter, actions.
- `ziv/core/downloader.py` — YouTube authentication validation and probing.
- `tests/test_ziv_*.py` and `tests/test_catalog_tui.py` — Ziv behavior coverage.
- `.env.example` — credentials and low-resource configuration examples.

## Safety and migration decisions

- Use `ziv/` imports and the `ziv`/`ziv-parts` console commands.
- New state uses `.ziv-state`; cleanup never deletes existing output, queue,
  cookies, credentials, or other user data.
- Test files belong in GitHub. This handoff is development continuity, not a
  runtime requirement; sanitize it before publishing because local paths and
  work notes do not belong in a public repository.
- Never commit `.env`, `.ig_session`, browser cookies, downloaded media, output,
  virtual environments, or runtime state.

## Checks completed

### Tests

- Full offline suite after the colored source-browser redesign: `248 passed, 2 skipped`.
- Latest Ziv/catalog/TUI/browser-focused suite: `25 passed`.

### Lint / syntax

- `python3 -m compileall -q ziv tests` passed.
- `bash -n ziv.sh` passed.
- `git diff --check` passed for the current changes.

### Media integration

- Attempted with `timeout 90s .venv/bin/python -m pytest -q --run-integration`.
  Result: `248 passed, 2 failed`; both failures stop before rendering because
  `ffmpeg` is missing from `PATH`. Install FFmpeg and rerun the same command.

### YouTube

- Offline cookie configuration tests pass.
- A real browser-cookie/YouTube request remains unverified until a local
  browser session or exported cookies and network access are available.

## Next step

Run the full offline suite and inspect the complete diff. Exercise `./ziv.sh`
from a real terminal and run a synthetic FFmpeg integration check on a machine
with FFmpeg installed before committing the cleanup when requested.
