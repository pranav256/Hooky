# Session handover

## Goal

Build **Ziv**, a Linux-first terminal GUI for managing long-video clipping:
named links, named YouTube channels, resumable clipping jobs, queue state,
resource usage, logs, and safe YouTube-cookie diagnostics.

## Current state

- Public package facade: `ziv/`.
- Public command: `ziv`.
- Single Linux launcher: `ziv.sh`.
- Existing `reelclip/` implementation remains as an internal compatibility
  layer while the migration is completed.
- The old multiple `.sh` and Windows `.bat` launchers were removed.
- The TUI is curses-based, dependency-light, and refuses to prompt on a
  redirected/non-TTY stdin.
- The catalog stores named sources in `.ziv-state/catalog.json`, imports the
  existing `links.txt` and `channels.txt`, and materializes named entries back
  into those workflow files for compatibility.
- The TUI can add/delete/import sources and launch one selected resumable job.
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
- `r` refresh; `1`-`4` or Tab switch views; `j`/`k` navigate; `q` quit

## Important files

- `ziv/cli.py` — public command routing and catalog/doctor subcommands.
- `ziv.sh` — only shell launcher; no arguments open the TUI.
- `reelclip/catalog.py` — catalog persistence, legacy import, queue/resource/log views.
- `reelclip/tui.py` — terminal-independent model, rendering, curses adapter, actions.
- `reelclip/core/downloader.py` — YouTube authentication validation and probing.
- `tests/test_ziv_*.py` and `tests/test_catalog_tui.py` — Ziv behavior coverage.
- `.env.example` — credentials and low-resource configuration examples.

## Safety and migration decisions

- Keep `reelclip/` imports and console aliases until downstream users migrate;
  do not delete existing output, queue, cookies, or credentials.
- New state uses `.ziv-state`; `.reelclip-state` is read as legacy state and
  is never deleted automatically.
- Test files belong in GitHub. This handoff is development continuity, not a
  runtime requirement; sanitize it before publishing because local paths and
  work notes do not belong in a public repository.
- Never commit `.env`, `.ig_session`, browser cookies, downloaded media, output,
  virtual environments, or runtime state.

## Checks completed

### Tests

- Full offline suite after the latest TUI/catalog additions: `248 passed, 2 skipped`.
- Latest Ziv/catalog/TUI/browser-focused suite: `25 passed`.

### Lint / syntax

- `python3 -m compileall -q reelclip ziv tests` passed.
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

Run the full offline suite, inspect the complete diff, then commit the Ziv TUI,
catalog, launcher consolidation, state migration, and YouTube diagnostics as a
focused change. After that, exercise `./ziv.sh` from a real terminal and run a
synthetic FFmpeg integration check on a machine with FFmpeg installed.
