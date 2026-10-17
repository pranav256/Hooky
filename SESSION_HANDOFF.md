# Session handover

## Goal

Continue the `Clipper` project as a low-resource video clipping toolkit that is
easy to operate from a terminal.

Current acceptance criteria:

- Podcast auto mode can choose a content-dependent number of worthwhile clips.
- Story mode can condense long-form videos into chronological vertical parts.
- Number-only mode runs Gemini to find funny/highlight-worthy moments, keeps
  those moments in chronological order, skips Whisper and subtitles, and burns
  only a numeric part marker (`1`, `2`, `3`, …).
- Outputs remain export-only for the parts workflows and do not enter the
  Instagram queue.
- The project remains reproducible and documented for the low-resource machine.
- Visual analysis and retry work should stay bounded on the low-resource machine.
- A terminal user can start common workflows from a guided menu without
  memorizing flags; scripted commands remain non-interactive.

## State

Repository: `/pranav/Projects/Clipper`

- Branch: `main`
- Revision: `50d211c perf: reduce analysis work and add terminal wizard`
- Remote: `origin/main` is at the same revision
- The optimization and terminal wizard are committed. This handover file is
  updated separately so the next session starts with current evidence.
- `.env` was not committed or uploaded.

Implemented behavior:

- `./make.sh podcast.mp4 --clips auto` uses content-based Gemini selection.
- `./parts.sh story.mp4` uses the condensed-story workflow.
- `./number-parts.sh cartoon.mp4` invokes number-only mode.
- `./parts.sh cartoon.mp4 --mode number-only --part-seconds 60` is the
  equivalent direct entry point.
- Number-only mode asks Gemini to focus on funny, surprising, absurd, reaction,
  visual-gag, and punchline moments. It uses source captions when available;
  without captions it uses the existing visual/audio fallback. It does not run
  Whisper and does not burn subtitles.
- Parts use the existing full-picture vertical renderer with blurred padding by
  default, or plain padding with `--background plain`.
- Story plans, manifests, and renderer checkpoints support resume.

Known gap:

- A final end-to-end media render for number-only mode was not completed in the
  last session. FFmpeg/FFprobe behavior on this machine was unreliable: some
  FFmpeg checks worked, but FFprobe and repeated pytest/import commands could
  hang before producing output. Do not call the media render fully verified.

Optimization and terminal changes:

- Visual fallback analysis defaults to 12 sparse frames instead of 20 and
  caches frames by source revision, frame count, and JPEG settings.
- Candidate visual-review frames are cached under the selection checkpoint, so
  a retry does not re-run successful FFmpeg frame extraction.
- Fit-framing renders use a 480px blurred background before scaling to the
  1080x1920 output; subtitle ASS generation receives only overlapping words.
- The default no-cover path avoids a second render-state fsync-heavy JSON write.
- `reelclip --interactive` and executable `./run.sh` provide a guided terminal
  menu for highlights, story parts, number-only parts, queue status, and help.
  Interactive mode refuses to prompt when stdin is not a TTY.

## Files in the latest committed feature

- `.env.example` — documents `PARTS_MODE` and related settings.
- `README.md` — documents podcast auto selection, story parts, and number-only
  funny-moment parts.
- `reelclip/core/highlights.py` — adds an editorial `focus` to Gemini highlight
  prompts and ranking.
- `reelclip/parts/cli.py` — adds `--mode story|number-only`.
- `reelclip/parts/options.py` — validates the mode and forces numeric-only
  output behavior in number-only mode.
- `reelclip/parts/pipeline.py` — adds Gemini funny-moment selection and creates
  numeric-only plans/manifests without Whisper or subtitle timing.
- `reelclip/parts/renderer.py` — burns only the numeric label in number-only
  mode.
- `reelclip/parts/README.md` — documents both parts workflows.
- `number-parts.sh` / `number-parts.bat` — number-only launchers.
- `tests/test_parts_number_only.py` — targeted mode, pipeline, and numeric-label
  tests.
- `reelclip/interactive.py` — guided terminal workflow.
- `run.sh` — guided entry point; explicit arguments pass through to the CLI.
- `tests/test_interactive.py` — offline wizard exit behavior.
- `tests/test_cutter_resume.py` — bounded subtitle and fit-background checks.
- `tests/test_highlights.py` — revision-keyed visual-frame cache check.

## Decisions

- Number-only does **not** mean “split the entire source.” It means Gemini
  selects the best funny moments, then the selected ranges are packed into
  parts in source order.
- The numeric marker is the only generated overlay in number-only mode. No
  subtitles, caption text, or `Part N / Total` label is added.
- Number-only remains export-only and never queues clips to Instagram.
- The default target part length is 60 seconds, constrained by the existing
  90-second Reel limit.
- No new dependency was added for the feature.

## Checks

### Tests

- Full offline suite passed after the optimization commit:
  - Command: `timeout 120s .venv/bin/python -m pytest -q`
  - Result: `220 passed, 2 skipped in 27.10s`
- Targeted regression suite passed:
  - Command: `timeout 120s .venv/bin/python -m pytest -q tests/test_cutter_resume.py tests/test_interactive.py tests/test_parts_number_only.py tests/test_highlights.py`
  - Result: `14 passed in 1.25s`

### Lint / formatting

- No project lint command is configured.
- `git diff --check`: passed before commit.
- `bash -n make.sh parts.sh number-parts.sh post.sh run.sh`: passed.
- `python3 -m compileall -q reelclip tests`: passed.
- `python3 -m reelclip --help` and `python3 -m reelclip.parts --help`: passed.
- `python3 -m reelclip --interactive </dev/null`: returned 2 with a clear
  non-TTY message; no prompt was attempted.

### Typecheck / build

- No separate typecheck or build command is configured.
- Python compilation for the changed modules and targeted test file: passed.
- End-to-end FFmpeg/FFprobe render: not run. The container has neither
  `ffmpeg` nor `ffprobe` on PATH, so `pytest -q --run-integration` fails before
  rendering with `FileNotFoundError: [Errno 2] No such file or directory:
  'ffmpeg'`. Install the project’s declared system media dependency in the
  clean build environment before treating media output as verified.

## Next step

Run one media verification when the environment has FFmpeg available:

```bash
cd /pranav/Projects/Clipper
.venv/bin/python -m pytest -q --run-integration
```

Then run a short synthetic number-only render with a tiny local video and
inspect that the output has the expected 1080x1920 dimensions, audio, and only
the numeric overlay. Do not commit or upload generated media, `.env`, cookies,
or session files.
