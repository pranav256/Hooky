# reelclip

A lean pipeline for turning long videos into high-quality Instagram Reels.
It selects moments with Gemini, transcribes only the selected windows, burns
karaoke subtitles, renders 1080x1920 H.264 clips, and posts through Instagram.

## Workflow

```text
channels.txt / links.txt / local video
      ↓
channel scanner ranks videos by views (upload date is ignored)
      ↓
source captions are read in bounded semantic chunks
      ↓
Gemini selects complete spoken moments and visually reviews framing
      ↓
Whisper transcribes only selected windows for your burned-in subtitles
      ↓
FFmpeg center-crops or selectively fits clips into 1080x1920
      ↓
clips enter the Instagram queue
      ↓
post.sh uploads them at a paced interval
```

The pipeline does not include YouTube uploads, TikTok uploads, multi-account
routing, jump cuts, progress bars, hooks, or auto-watcher modes. Channel
discovery is limited to finding unseen high-performing source videos by view
count. Framing is deliberately selective: normal close-ups use the fast center
crop, while Gemini can request a full-frame fit with blurred padding when a
center crop would cut off a presentation, screen, or group.

## Quality

The default `QUALITY=highest` profile produces:

- 1080x1920 vertical output
- H.264 High Profile, level 4.1, `yuv420p`
- 30 fps
- CRF 15 with the medium x264 preset
- AAC audio at 256 kbps

Source downloads use up to 1440p for long videos and 2160p for shorter videos
before the vertical crop. A quality-aware cache refuses to reuse an older
lower-resolution master when a sharper source is requested.

The medium preset is intentional: at the same CRF, `slow` mostly saves a
small amount of file size while costing much more CPU time. Instagram will
transcode the upload anyway.

Instagram performs its own final server-side transcode. The private API can
upload the prepared high-quality file, but it cannot reliably toggle
Instagram's mobile **Upload at highest quality** account setting. Enable that
setting in the Instagram app as well.

For a weaker computer:

```dotenv
QUALITY=high
```

## Requirements

- Python 3.10+
- FFmpeg and FFprobe on `PATH`
- Gemini API key
- Instagram username and password for posting
- yt-dlp only when discovering channels or processing URLs from `links.txt`

Install FFmpeg on Debian/Ubuntu:

```bash
sudo apt install ffmpeg python3 python3-venv
```

On Windows:

```powershell
winget install ffmpeg
```

## Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

Set these values in `.env`:

```dotenv
GEMINI_API_KEY=your_gemini_key
IG_USERNAME=your_instagram_username
IG_PASSWORD=your_instagram_password
```

The first Instagram login caches `.ig_session`. If Instagram requests a
verification code, set `IG_2FA_CODE` or enter it interactively.

Never commit `.env` or `.ig_session`.

## Make clips

Local video:

```bash
./make.sh /path/to/video.mp4
```

Multiple local files or a folder:

```bash
./make.sh /path/to/videos --clips auto
```

Channel mode uses `channels.txt`:

```bash
./make.sh
```

With no arguments, `make.sh` first scans every configured channel, ranks its
videos by view count regardless of upload date, appends unseen winners to
`links.txt`, and then processes those links. It does not choose only recent
uploads. The scan stores selected video IDs in `output/channel_history.json`
so the same winner is not added repeatedly; later scans advance to the next
unseen high-performing videos. Compact channel listings are cached for 24
hours by default, and `CHANNEL_BACKLOG_MAX=20` prevents a scan from filling the
machine with unprocessed sources.

Run discovery without processing:

```bash
.venv/bin/python -m reelclip --source
```

Configure channels in this format:

```text
https://www.youtube.com/@veritasium | limit=5
@lexfridman | limit=3 | min_views=100000
```

`limit` controls the number of unseen winners per channel. `min_views` sets an
optional floor. `scan=0` (the default) examines the full available channel
video list, so older high-performing videos are eligible. Set `scan=N` only if
a channel is extremely large and you deliberately want to cap metadata work.
The ranking is still view-dominant, with light like/comment, topic-potential,
and title-diversity signals. `CHANNEL_BACKLOG_MAX=20` prevents discovery from
adding more than 20 active, unprocessed links; existing links are not deleted
when you lower that setting. Copy `channels.example.txt` for the format.

Direct link mode remains available:

```bash
.venv/bin/python -m reelclip --links --no-post
```

Each link is marked `# DONE` after successful processing. Copy
`links.example.txt` for per-link settings such as `clips=5`, `min=10`, and
`max=45`.

Useful options:

```bash
./make.sh video.mp4 --no-subs
./make.sh video.mp4 --no-captions
./make.sh video.mp4 --sub-style clean
./make.sh video.mp4 --dry-run
```

## Post to Instagram

Post the queue immediately:

```bash
./post.sh
```

Post only when the configured window and cooldown allow:

```bash
./post.sh --due
```

The queue stores a JSON-safe Instagram media code after every successful
upload, so a successful post cannot be mistaken for a failed upload because of
Media-object serialization. Posting state now lives in `.reelclip-state/`,
separate from disposable rendered/downloaded media. Before each upload it
writes a durable safety hold. If the request outcome is unknown, posting stops
instead of automatically risking a duplicate.

After checking Instagram, resolve a hold explicitly:

```bash
.venv/bin/python -m reelclip --confirm-posted /path/to/reel.mp4 MEDIA_CODE
# or, only after confirming no Reel exists:
.venv/bin/python -m reelclip --retry-after-review /path/to/reel.mp4
```

Inspect the queue:

```bash
.venv/bin/python -m reelclip --queue-status
```

Reset the cooldown:

```bash
.venv/bin/python -m reelclip --reset-gap
```

Remove a clip from the queue:

```bash
.venv/bin/python -m reelclip --ignore /absolute/path/to/reel.mp4
```

## Configuration

Useful optional settings in `.env`:

```dotenv
QUALITY=highest
# SOURCE_MAX_HEIGHT=2160
# SOURCE_LONG_THRESHOLD_MINUTES=10
# SOURCE_MAX_HEIGHT_LONG=1440
# SOURCE_MAX_HEIGHT_SHORT=2160
# WHISPER_MODEL=tiny
# WHISPER_COMPUTE=int8
# SUB_FONT=Arial
# POST_HOURS=17-0
# QUEUE_MIN_GAP_MINUTES=60
# QUEUE_MAX_GAP_MINUTES=120
# QUEUE_MAX_ATTEMPTS=3
# CHANNEL_BACKLOG_MAX=20
# CHANNEL_CACHE_HOURS=24
# CHANNEL_SCAN_MAX=0
# MAKE_MAX_SOURCES=2
# QUEUE_MAX_PENDING=12
```

For YouTube links that trigger bot protection, use one of these optional
download settings:

```dotenv
# YTDLP_COOKIES_FROM_BROWSER=chrome
# YTDLP_COOKIES_FILE=cookies.txt
```

## Tests

Fast offline checks:

```bash
.venv/bin/python -m pytest -q
```

The optional synthetic FFmpeg test can be enabled with:

```bash
.venv/bin/python -m pytest -q --run-integration
```

A real Instagram upload requires credentials and network access and is not run
by the test suite.

## Project layout

- `reelclip/cli.py` - lean command-line workflow and Instagram posting
- `reelclip/pipeline.py` - selection, selected transcription, rendering, queueing
- `reelclip/core/highlights.py` - Gemini highlight selection
- `reelclip/core/subtitles.py` - Whisper timing and ASS subtitles
- `reelclip/core/cutter.py` - center crop, render, and covers
- `reelclip/core/downloader.py` - optional links.txt downloads and source captions
- `reelclip/core/source_text.py` - WebVTT/SRT parsing and caption download cache
- `reelclip/core/queue.py` - durable Instagram-only queue and review holds
- `reelclip/platforms/instagram.py` - login and Reel upload
- `make.sh` / `post.sh` - make-only and post-only entry points

## Recovery copy

Before the selective framing/resume work, a sanitized code backup was created
at:

```text
/pranav/Projects/clipping_pre_smartcrop_backup_sanitized_20261002_192017.tar.gz
```

It excludes `.env`, `.ig_session`, `.venv`, and generated output. Keep those
local files backed up separately if you need to preserve credentials or media.
