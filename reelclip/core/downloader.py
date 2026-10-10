"""Link handling: expand playlist/channel URLs, download videos with yt-dlp.

Supported link formats in links.txt (one per line, '#' starts a comment):

    https://youtube.com/watch?v=...          one video, default settings
    https://youtube.com/watch?v=... | clips=5 | min=10 max=45
                                             per-link overrides ('|' separated)
    /path/to/local/video.mp4                 local file: used directly

Per-link settings: clips=N, min=N, max=N, subs=0 (no subtitles),
style=NAME. Unknown keys are ignored with a warning.

yt-dlp is imported lazily so the rest of the tool works without it.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from ..config import (OUTPUT_DIR, SOURCE_LONG_SECONDS, SOURCE_MAX_HEIGHT_LONG,
                      SOURCE_MAX_HEIGHT_SHORT)
from .source_text import (download_source_captions, load_caption_file,
                          sidecar_caption_file)

DOWNLOADS_DIR = OUTPUT_DIR / "downloads"

VIDEO_HOST_HINTS = re.compile(
    r"^https?://", re.IGNORECASE)

# yt-dlp format: pre-merged h264/aac MP4, capped at an adaptive height (the
# cut renders 1080x1920, so this keeps the master sharp before the vertical
# crop). The highest profile uses <=1440p for long videos and <=2160p for
# short ones; QUALITY=high/low opts into lighter source downloads.
PROBE_FORMAT = "bv*+ba/b"    # permissive: only used to LIST formats, not download


class YouTubeAuthRequired(RuntimeError):
    """YouTube refused an anonymous or invalidly authenticated request."""


_AUTH_MARKERS = (
    "sign in to confirm", "cookies-from-browser", "cookies from browser",
    "confirm you’re not a bot", "confirm you're not a bot", "login required",
)


def is_youtube_auth_error(error: BaseException) -> bool:
    text = str(error).lower()
    return any(marker in text for marker in _AUTH_MARKERS)


def youtube_auth_help() -> str:
    browser = os.environ.get("YTDLP_COOKIES_FROM_BROWSER", "").strip()
    cookie_file = os.environ.get("YTDLP_COOKIES_FILE", "").strip()
    if browser:
        return (f"YTDLP_COOKIES_FROM_BROWSER={browser!r} is configured, but "
                "YouTube rejected those cookies. Open YouTube in that browser, "
                "sign in, solve any CAPTCHA, close the browser, and retry; "
                "otherwise export fresh Netscape cookies and use YTDLP_COOKIES_FILE.")
    if cookie_file:
        return (f"YTDLP_COOKIES_FILE points to {cookie_file!r}, but YouTube rejected "
                "it. Export a fresh Netscape cookies.txt after signing in and retry.")
    return ("YouTube needs authentication. Set YTDLP_COOKIES_FROM_BROWSER=firefox "
            "(or chrome/brave/edge) after signing into YouTube, close that browser, "
            "and retry. Alternatively export Netscape cookies.txt and set "
            "YTDLP_COOKIES_FILE=/absolute/path/cookies.txt.")


def _auth_failure(error: BaseException) -> YouTubeAuthRequired:
    return YouTubeAuthRequired(f"{error}\n\n[youtube] {youtube_auth_help()}")


def yt_dlp_auth_opts() -> dict:
    """Optional yt-dlp authentication, shared by downloads and channel scans.

    YouTube often answers anonymous downloads with 'Sign in to confirm you're
    not a bot'. Set one of these in .env to fix it:
      YTDLP_COOKIES_FROM_BROWSER=chrome        (chrome|firefox|brave|edge|...)
      YTDLP_COOKIES_FROM_BROWSER=chrome:Profile 1   (with a profile name)
      YTDLP_COOKIES_FILE=cookies.txt           (Netscape cookies.txt export)
    """
    auth: dict = {}
    browser = os.environ.get("YTDLP_COOKIES_FROM_BROWSER", "").strip()
    cookie_file = os.path.expanduser(os.environ.get("YTDLP_COOKIES_FILE", "").strip())
    if browser and cookie_file:
        raise ValueError("Set only one of YTDLP_COOKIES_FROM_BROWSER or "
                         "YTDLP_COOKIES_FILE")
    if browser:
        name, _, profile = browser.partition(":")
        name = name.strip().lower()
        allowed = {"brave", "chrome", "chromium", "edge", "firefox", "opera",
                   "safari", "vivaldi"}
        if name not in allowed:
            raise ValueError(f"Unsupported browser '{name}' in "
                             "YTDLP_COOKIES_FROM_BROWSER")
        auth["cookiesfrombrowser"] = (
            name, profile.strip() or None, None, None)
    if cookie_file:
        path = Path(cookie_file)
        if not path.is_file():
            raise FileNotFoundError(
                f"YTDLP_COOKIES_FILE does not exist: {path}. "
                "Export a Netscape cookies.txt file first.")
        auth["cookiefile"] = str(path)
    return auth


def check_youtube_access(url: str) -> bool:
    """Probe one URL without downloading and print an actionable diagnosis."""
    try:
        import yt_dlp
        auth = yt_dlp_auth_opts()
        print("[youtube] authentication: " +
              ("configured browser/cookie file" if auth else "anonymous (no cookies)"))
        opts = {"quiet": True, "no_warnings": True, "noplaylist": True,
                "skip_download": True, **auth}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info:
            print("[youtube] no metadata returned", file=sys.stderr)
            return False
        print(f"[youtube] OK: {info.get('title') or info.get('id') or url}")
        return True
    except Exception as exc:
        if is_youtube_auth_error(exc):
            print(f"[youtube] AUTHENTICATION FAILED: {_auth_failure(exc)}",
                  file=sys.stderr)
        else:
            print(f"[youtube] probe failed: {exc}", file=sys.stderr)
        return False


def _format_string(max_height: int) -> str:
    return (
        f"bv*[ext=mp4][height<={max_height}]+ba[ext=m4a]"
        f"/b[ext=mp4][height<={max_height}]/b"
    )


def _pick_height(duration: float | None) -> int:
    """Adaptive master cap: 1440p for short videos, 1080p for long ones.

    Unknown duration -> the safer (lower) cap. When both caps are pinned to
    the same value this is a no-op.
    """
    if SOURCE_MAX_HEIGHT_LONG == SOURCE_MAX_HEIGHT_SHORT:
        return SOURCE_MAX_HEIGHT_SHORT
    if not duration or duration <= 0:
        return SOURCE_MAX_HEIGHT_LONG
    return (SOURCE_MAX_HEIGHT_SHORT if duration <= SOURCE_LONG_SECONDS
            else SOURCE_MAX_HEIGHT_LONG)


# --- analysis twin -----------------------------------------------------------
# AI work (Gemini frames, audio energy, scene detection) runs on a small 480p
# proxy so analysis decodes ~6x faster; the CUT always uses the master.
ANALYSIS_HEIGHT = 480


def _analysis_path(master: Path) -> Path:
    return master.with_name(master.stem + "_analysis.mp4")


def make_analysis_twin(master: Path) -> Path | None:
    """Create (or reuse) a 480p proxy of the master for AI analysis.

    Returns the twin path, or None when the master is missing/invalid or the
    encode failed (callers then just analyse the master — same as before).
    """
    if not master.exists() or master.stat().st_size == 0:
        return None
    twin = _analysis_path(master)
    if twin.exists() and twin.stat().st_size > 0 \
            and twin.stat().st_mtime >= master.stat().st_mtime - 1:
        return twin                      # already built (or master unchanged)
    tmp = twin.with_suffix(".tmp.mp4")
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(master),
        "-vf", f"scale=-2:{ANALYSIS_HEIGHT}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
        "-c:a", "aac", "-b:a", "96k",   # keep audio: energy analysis needs it
        str(tmp),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    except Exception:
        return None
    if result.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
        print(f"[links] analysis twin failed for {master.name}; "
              f"using master for analysis", file=sys.stderr)
        tmp.unlink(missing_ok=True)
        return None
    tmp.replace(twin)
    print(f"[links] analysis twin ready: {twin.name} "
          f"({twin.stat().st_size / (1024 * 1024):.0f} MB)")
    return twin


def _attach_analysis(videos: list[dict]) -> None:
    for v in videos:
        # Semantic source captions already let Gemini select textually; avoid
        # transcoding the entire long master into a 480p proxy. The proxy is
        # retained only for the visual/audio fallback when captions are absent.
        v["analysis"] = (None if v.get("source_transcript")
                          else make_analysis_twin(v["path"]))


def parse_links_file(links_path: Path) -> list[dict]:
    """Parse links.txt into [{url, clips, min_len, max_len, sub_style, no_subs}].

    Skips blanks/#comments and previously-processed lines (marked '# DONE').
    """
    entries: list[dict] = []
    if not links_path.exists():
        return entries

    for line_no, raw in enumerate(links_path.read_text(encoding="utf-8").splitlines(),
                                  start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # Accept the older plain ``DONE <url>`` marker as well as ``# DONE``.
        if line.upper().startswith("DONE "):
            continue
        if "# DONE" in raw or "# DONE" in line.upper():
            continue

        parts = [p.strip() for p in line.split("|")]
        url, overrides = parts[0], parts[1:]
        entry = {
            "line_no": line_no,
            "url": url,
            "clips": None, "min_len": None, "max_len": None,
            "sub_style": None, "no_subs": None,
            "raw_line": line,
        }
        for ov in overrides:
            # a segment may hold several settings: "min=10 max=45"
            for token in ov.split():
                key, _, value = token.partition("=")
                key = key.strip().lower()
                value = value.strip()
                try:
                    if key == "clips":
                        entry["clips"] = 0 if value.lower() in ("auto", "0") \
                            else max(1, int(value))
                    elif key == "min":
                        entry["min_len"] = max(3, int(value))
                    elif key == "max":
                        entry["max_len"] = max(5, int(value))
                    elif key == "subs":
                        entry["no_subs"] = value in ("0", "false", "no", "off")
                    elif key == "style":
                        entry["sub_style"] = value
                    else:
                        print(f"[links] line {line_no}: unknown setting "
                              f"'{key}' ignored", file=sys.stderr)
                except ValueError:
                    print(f"[links] line {line_no}: bad value for '{key}': "
                          f"'{value}' — ignored", file=sys.stderr)
        entries.append(entry)
    return entries


def is_url(text: str) -> bool:
    return bool(VIDEO_HOST_HINTS.match(text.strip()))


def _already_downloaded(url: str, info: dict | None = None,
                        min_requested_height: int | None = None) -> Path | None:
    """Find a suitable cached file for this link.

    A cache made with a lower quality cap must not silently satisfy a later
    highest-quality run. Older metadata has no quality marker, so it is only
    accepted when no minimum is requested; the next quality-aware run will
    refresh it.
    """
    if not DOWNLOADS_DIR.exists():
        return None
    for meta_path in DOWNLOADS_DIR.glob("*.json"):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        # downloads/ may also contain transcript or tool JSON. Only the
        # downloader's object metadata can identify a cached URL.
        if not isinstance(meta, dict) or meta.get("url") != url:
            continue
        if min_requested_height is not None:
            cached_height = meta.get("requested_height")
            if (not isinstance(cached_height, (int, float))
                    or cached_height < min_requested_height):
                continue
        video_file = Path(meta.get("file", ""))
        if video_file.exists() and video_file.stat().st_size > 0:
            return video_file
    return None


def _merge_info(base: dict | None, extra: dict | None) -> dict:
    """Merge playlist-entry info with full info; prefer non-empty values."""
    merged = dict(base or {})
    for key, value in (extra or {}).items():
        if value not in (None, "", []) and (key not in merged or merged[key] in (None, "", [])):
            merged[key] = value
    return merged


def _safe_stem(title: str, video_id: str) -> str:
    stem = re.sub(r"[^\w\- ]", "", title or "").strip().replace(" ", "_")[:80]
    return f"{stem or 'video'}_{video_id or 'x'}"


def expand_and_download(entry: dict, limits: dict) -> tuple[list[dict], bool]:
    """Expand one link entry into processable video dicts.

    Returns (videos, processed_something):
      videos: [{"path": Path, "url": str|None, "title": str, "description": str,
                "uploader": str, "clips": int, "min_len": int, "max_len": int,
                "sub_style": str|None, "no_subs": bool|None}]
      processed_something: False when the link is new and nothing succeeded
    """
    url = entry["url"]
    videos: list[dict] = []

    # --- local file path -----------------------------------------------------
    if not is_url(url):
        p = Path(url)
        if p.exists():
            videos.append(_video_entry(p, None, None, entry, limits))
            if limits.get("make_analysis", True):
                _attach_analysis(videos)
            return videos, True
        print(f"[links] line {entry['line_no']}: not a link or file: {url}",
              file=sys.stderr)
        return videos, False

    # --- yt-dlp ---------------------------------------------------------------
    try:
        import yt_dlp
    except ImportError:
        print("[links] yt-dlp not installed — cannot handle links. "
              "Run: pip install yt-dlp", file=sys.stderr)
        return videos, False

    ydl_opts = {
        "format": PROBE_FORMAT,
        "outtmpl": str(DOWNLOADS_DIR / "%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 3,
        "socket_timeout": 30,
        "noplaylist": True,           # one source video per link
        "extract_flat": "in_playlist",  # list entries first, download one by one
        **yt_dlp_auth_opts(),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        if is_youtube_auth_error(exc):
            print(f"[links] YouTube authentication failed: {_auth_failure(exc)}",
                  file=sys.stderr)
        else:
            print(f"[links] Failed to read {url}: {exc}", file=sys.stderr)
        return videos, False

    if info is None:
        return videos, False

    flat_entries = info.get("entries") or []
    max_sources = limits.get("max_sources")
    if flat_entries:
        flat_entries = [entry for entry in flat_entries if entry]
        if max_sources:
            flat_entries = flat_entries[:max(1, int(max_sources))]
        items = [(entry, None) for entry in flat_entries]
    else:
        items = [(info, None)]

    downloaded_any = False
    for flat, _ in items:
        video_id = str(flat.get("id", ""))

        # Adaptive source quality: decide the master cap from the video's
        # length BEFORE checking the cache. A lower-quality old master must not
        # be reused when the user asks for a sharper vertical crop.
        duration = flat.get("duration")
        try:
            duration = float(duration) if duration else None
        except (TypeError, ValueError):
            duration = None
        height = _pick_height(duration)
        source_url = flat.get("url") or flat.get("webpage_url") or url
        cached = _already_downloaded(source_url, min_requested_height=height)
        caption_path = None
        if cached is not None:
            caption_path = _caption_path_from_metadata(cached)
            if caption_path is None:
                caption_path = download_source_captions(
                    source_url, video_id, DOWNLOADS_DIR)
            print(f"[links] Cached ({height}p quality target), skipping download: "
                  f"{cached.name}")
            videos.append(_video_entry(cached, source_url, None, entry, limits,
                                       cached_meta=flat,
                                       source_caption_path=caption_path))
            downloaded_any = True
            continue
        dl_opts = dict(ydl_opts)
        dl_opts["format"] = _format_string(height)
        len_note = (f"{duration / 60:.0f} min" if duration
                    else "length unknown")
        print(f"[links] {flat.get('title', video_id)[:60]}: {len_note} "
              f"-> downloading master at <= {height}p")

        full = None
        try:
            with yt_dlp.YoutubeDL(dl_opts) as ydl:
                full = ydl.extract_info(flat.get("url") or flat.get("webpage_url") or url,
                                        download=True)
        except Exception as exc:
            if is_youtube_auth_error(exc):
                print(f"[links] YouTube authentication failed: {_auth_failure(exc)}",
                      file=sys.stderr)
            else:
                print(f"[links] Download failed for {flat.get('title', video_id)}: {exc}",
                      file=sys.stderr)
            continue

        merged = _merge_info(flat, full)
        file_path = Path(full.get("requested_downloads", [{}])[0].get("filepath", "")) \
            if full.get("requested_downloads") else None
        if file_path is None or not file_path.exists():
            # fall back to the id-based template
            candidates = sorted(DOWNLOADS_DIR.glob(f"{video_id}.*"))
            candidates = [c for c in candidates if c.suffix.lower() != ".json"]
            file_path = candidates[0] if candidates else None
        if file_path is None or not file_path.exists():
            print(f"[links] Downloaded but file not found for {video_id}", file=sys.stderr)
            continue

        meta_path = file_path.with_suffix(".json")
        source_url = merged.get("webpage_url") or url
        caption_path = download_source_captions(
            source_url, video_id, DOWNLOADS_DIR)
        meta_path.write_text(json.dumps({
            "url": source_url,
            "file": str(file_path),
            "title": merged.get("title", ""),
            "video_id": video_id,
            "requested_height": height,
            "source_captions": str(caption_path) if caption_path else "",
        }, ensure_ascii=False, indent=2), encoding="utf-8")

        videos.append(_video_entry(file_path, source_url, merged, entry, limits,
                                   source_caption_path=caption_path))
        downloaded_any = True

    if limits.get("make_analysis", True):
        _attach_analysis(videos)
    return videos, downloaded_any


def _caption_path_from_metadata(video_path: Path) -> Path | None:
    meta_path = video_path.with_suffix(".json")
    try:
        value = json.loads(meta_path.read_text(encoding="utf-8")).get(
            "source_captions", "")
    except (OSError, json.JSONDecodeError, AttributeError):
        value = ""
    path = Path(value) if value else None
    return path if path and path.exists() else None


def _video_entry(path: Path, url: str | None, info: dict | None, entry: dict,
                 limits: dict, cached_meta: dict | None = None,
                 source_caption_path: Path | None = None) -> dict:
    meta = info or cached_meta or {}
    merged = _merge_info(cached_meta, info)
    caption_path = source_caption_path or sidecar_caption_file(path)
    return {
        "path": path,
        "url": url or (meta.get("webpage_url") if meta else None),
        "video_id": merged.get("id") or merged.get("video_id") or "",
        "source_transcript": load_caption_file(caption_path),
        "source_caption_path": str(caption_path) if caption_path else "",
        "title": merged.get("title") or path.stem,
        "description": (merged.get("description") or "")[:1200],
        "uploader": merged.get("uploader") or merged.get("channel") or "",
        # clips=None -> AUTO: content determines the count by default
        "clips": entry["clips"] if entry["clips"] is not None else limits["clips"],
        "min_len": entry["min_len"] or limits["min"],
        "max_len": entry["max_len"] or limits["max"],
        "sub_style": entry["sub_style"],
        "no_subs": entry["no_subs"],
        "analysis": None,
    }
