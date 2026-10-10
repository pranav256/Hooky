# Story parts

An export-only subproject for turning a narrated long-form video into a
condensed, chronological series of vertical parts.

## Run

From the repository root, after the main project's setup:

```bash
./parts.sh story.mp4
./parts.sh 'https://www.youtube.com/watch?v=VIDEO_ID'
./parts.sh story.mp4 --part-seconds 60 --labels
./parts.sh story.mp4 --caption-file story.srt --dry-run
```

Python: `.venv/bin/python -m reelclip.parts story.mp4`.
Windows: `parts.bat story.mp4`.
Installed command: `reelclip-parts story.mp4`.

## Defaults

- AI decides retained story length from the evidence.
- Retain setup, stakes, developments, causal context, and payoff in source order.
- Remove sponsors, repeated explanations, and filler.
- Preserve original footage and audio.
- Aim for 60 seconds per part; prefer sentence endings/edit joins and stay
  below the 90-second hard limit.
- Fit the entire source picture into 1080x1920 over a blurred background.
- Burn existing karaoke subtitles, remapped onto the edited timeline.
- Export files under `output/parts/<source-id>/` and preserve the input video.

## Options

| Option | Purpose |
| --- | --- |
| `--part-seconds N` | Target duration; defaults to `PARTS_TARGET_SECONDS=60`. |
| `--background blur\|plain` | Blurred backdrop or lighter plain padding; defaults to `PARTS_BACKGROUND=blur`. |
| `--labels` | Visible `Part N / Total` label in the upper padding. |
| `--caption-file FILE` | Use a specific VTT/SRT track as spoken evidence. |
| `--subtitle-source auto\|source\|whisper` | Prefer captions, require captions, or regenerate retained subtitle timing. |
| `--sub-style NAME` | Existing `hormozi`, `clean`, or `yellow` subtitle styles. |
| `--sub-lang LANG` | Whisper language hint. |
| `--no-subs` | Export without burned-in subtitles. |
| `--dry-run` | Write the story and parts plan before rendering. |
| `--out DIR` | Choose an export directory. |
| `--profile` | Write stage timings to `profile.json`. |

The pipeline still needs spoken evidence with `--no-subs`. It uses available
caption tracks first, or caches independently transcribed five-minute Whisper
windows when captions are missing. Caption cue timing is interpolated across
words; explicit Whisper timing costs more CPU but can improve alignment.

## Outputs and recovery

`story_plan.json` contains the selected source ranges and each part's source
fragments, edited-timeline boundaries, and fragment offsets. `manifest.json`
lists completed exports and final completion status. MP4s use names such as
`part_001.mp4`; subtitle-enabled exports include a corresponding ASS sidecar.

Rerun the same command after interruption. Selection requests, speech windows,
rendered fragments, and completed parts have versioned checkpoints keyed by
their source/options. Each fragment encodes sequentially, then the final part
is assembled with stream copy. Validated completed parts release their
temporary assembly fragments. Blurring runs at 480p before scaling up.

## Modules

- `cli.py` / `__main__.py`: local-file and single-URL entry points.
- `options.py`: validated parts options.
- `planner.py`: AI story beats, chronology, timeline mapping, and part boundaries.
- `renderer.py`: resumable per-fragment encoding and final assembly.
- `pipeline.py`: evidence acquisition, checkpoints, manifests, and export orchestration.

Shared utilities live in `reelclip/core/`; this subproject uses the main `.env`
and its Gemini, download authentication, encoding, and Whisper settings.
