from __future__ import annotations

import os
import re
import sys
import json
import time
import shutil
import secrets
import hmac
import asyncio
import subprocess
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from hooky.config import CHANNELS_FILE, LINKS_FILE, OUTPUT_DIR, PROJECT_ROOT, ENV_FILE
from hooky.doctor import dependency_checks
from hooky.core.subtitles import STYLES, build_ass
from hooky.core.source_text import parse_caption_file, caption_words
from hooky.core.cutter import cut_clip
from hooky.core.utils import format_timestamp, validate_video_url
from hooky.web.analyzer import (
    ANALYSIS_JOBS,
    run_analysis_pipeline,
    extract_youtube_id,
    get_video_metadata,
    download_captions,
    extract_ranked_scenes,
)

def _load_or_create_web_token() -> str:
    env_token = os.environ.get("HOOKY_WEB_TOKEN", "").strip()
    if env_token:
        return env_token
    state_dir = Path(os.environ.get("STATE_DIR") or PROJECT_ROOT / ".hooky-state")
    token_file = state_dir / ".web_token"
    try:
        if token_file.exists():
            saved = token_file.read_text(encoding="utf-8").strip()
            if len(saved) >= 16:
                os.environ["HOOKY_WEB_TOKEN"] = saved
                return saved
        state_dir.mkdir(parents=True, exist_ok=True)
        new_token = secrets.token_urlsafe(32)
        token_file.write_text(new_token, encoding="utf-8")
        try:
            token_file.chmod(0o600)
        except OSError:
            pass
        os.environ["HOOKY_WEB_TOKEN"] = new_token
        return new_token
    except Exception:
        new_token = secrets.token_urlsafe(32)
        os.environ["HOOKY_WEB_TOKEN"] = new_token
        return new_token


_WEB_TOKEN = _load_or_create_web_token()


def get_web_token() -> str:
    """Return active secret token required for Web Studio API calls."""
    return _WEB_TOKEN


app = FastAPI(title="Hooky Web Studio & Control Portal", version="2.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Enforce loopback Host header to prevent DNS rebinding, and authenticate API calls."""
    # 1. Host header validation
    host_header = request.headers.get("host", "")
    host = host_header.split(":")[0].strip("[]").lower()
    allowed_hosts = {"127.0.0.1", "localhost", "::1", "testserver"}
    if host and host not in allowed_hosts:
        return JSONResponse(
            status_code=403,
            content={"detail": f"Forbidden: Host header '{host_header}' is not allowed"},
        )

    # 2. Token authentication for /api/* routes (exempt CORS OPTIONS preflight)
    if request.url.path.startswith("/api/") and request.method != "OPTIONS":
        token = (
            request.headers.get("x-hooky-token")
            or request.cookies.get("hooky_token")
            or request.query_params.get("token")
        )
        if not token or not hmac.compare_digest(token, _WEB_TOKEN):
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized: Missing or invalid X-Hooky-Token"},
            )

    return await call_next(request)

STATIC_DIR = Path(__file__).parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="studio-static")

_JOBS: dict[str, dict[str, Any]] = {}


@app.get("/api/doctor")
async def get_doctor_status():
    """Return diagnostic checks from Hooky's doctor module."""
    raw_checks = dependency_checks()
    checks = [
        {"name": c.name, "ok": c.ok, "detail": c.detail, "required": c.required}
        for c in raw_checks
    ]
    gpu_type = "CPU (Multi-threaded)"
    if shutil.which("nvidia-smi"):
        gpu_type = "NVIDIA NVENC (CUDA Accelerated)"
    elif sys.platform == "darwin":
        gpu_type = "Apple Silicon VideoToolbox (Metal)"

    return {
        "status": "online",
        "gpu": gpu_type,
        "checks": checks,
        "all_required_ok": all(c.ok for c in raw_checks if c.required),
        "subtitle_styles": list(STYLES.keys()),
    }


@app.get("/api/channels")
async def get_channels():
    """Return active lines from channels.txt."""
    if not CHANNELS_FILE.exists():
        return {"channels": []}
    lines = [
        line.strip()
        for line in CHANNELS_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    return {"channels": lines, "count": len(lines)}


@app.post("/api/channels")
async def save_channels(request: Request):
    """Save updated channels list to channels.txt."""
    data = await request.json()
    new_channels = data.get("channels", [])
    content = "\n".join(new_channels) + "\n"
    CHANNELS_FILE.write_text(content, encoding="utf-8")
    return {"status": "saved", "count": len(new_channels)}


@app.get("/api/links")
async def get_links():
    """Return active lines from links.txt."""
    if not LINKS_FILE.exists():
        return {"links": []}
    lines = [
        line.strip()
        for line in LINKS_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    return {"links": lines, "count": len(lines)}


@app.post("/api/links")
async def save_links(request: Request):
    """Save updated links list to links.txt."""
    data = await request.json()
    new_links = data.get("links", [])
    content = "\n".join(new_links) + "\n"
    LINKS_FILE.write_text(content, encoding="utf-8")
    return {"status": "saved", "count": len(new_links)}


@app.get("/api/env")
async def get_env_config():
    """Return sanitized content and parsed key-value pairs from .env with sensitive credentials masked."""
    if not ENV_FILE.exists():
        return {"raw": "", "values": {}}
    raw = ENV_FILE.read_text(encoding="utf-8")
    values = {}
    masked_raw_lines = []
    sensitive_keys = {"IG_PASSWORD", "GEMINI_API_KEY"}
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k, _, v = stripped.partition("=")
            k = k.strip()
            v = v.strip().strip("'\"")
            if k in sensitive_keys and v:
                values[k] = "••••••••"
                masked_raw_lines.append(f"{k}=••••••••")
                continue
            values[k] = v
        masked_raw_lines.append(line)
    return {"raw": "\n".join(masked_raw_lines), "values": values}


@app.post("/api/env")
async def save_env_config(request: Request):
    """Save updated .env configuration from either raw text or key-value dict."""
    ct = request.headers.get("content-type", "").lower()
    if "application/json" not in ct:
        raise HTTPException(status_code=415, detail="Content-Type must be application/json")

    data = await request.json()
    existing_raw = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
    existing_secrets = {}
    for line in existing_raw.splitlines():
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, _, v = s.partition("=")
            existing_secrets[k.strip()] = v.strip().strip("'\"")

    key_pattern = re.compile(r"^[A-Z0-9_]{2,64}$")
    sensitive_keys = {"IG_PASSWORD", "GEMINI_API_KEY"}

    if "raw" in data and isinstance(data["raw"], str):
        lines = []
        for line in data["raw"].splitlines():
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, _, v = s.partition("=")
                k = k.strip()
                v = v.strip().strip("'\"")
                if not key_pattern.match(k):
                    continue
                if k in sensitive_keys and v.startswith("••") and k in existing_secrets:
                    v_orig = existing_secrets[k]
                    lines.append(f'{k}="{v_orig}"' if " " in v_orig else f"{k}={v_orig}")
                    continue
            lines.append(line)
        content = "\n".join(lines).rstrip() + "\n"
        ENV_FILE.write_text(content, encoding="utf-8")
    elif "values" in data and isinstance(data["values"], dict):
        updated = {}
        for k, v in data["values"].items():
            k_clean = str(k).strip()
            if not key_pattern.match(k_clean):
                continue
            v_clean = str(v).strip()
            if k_clean in sensitive_keys and v_clean.startswith("••"):
                if k_clean in existing_secrets:
                    updated[k_clean] = existing_secrets[k_clean]
            else:
                updated[k_clean] = v_clean

        raw = existing_raw
        lines = raw.splitlines()
        existing = set()
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k, _, _ = stripped.partition("=")
                k = k.strip()
                existing.add(k)
                if k in updated:
                    v = str(updated[k]).strip()
                    if " " in v or "\\" in v:
                        v = f'"{v}"'
                    new_lines.append(f"{k}={v}")
                    continue
            new_lines.append(line)
        for k, v in updated.items():
            if k not in existing:
                v_str = f'"{v}"' if " " in str(v) else str(v)
                new_lines.append(f"{k}={v_str}")
        content = "\n".join(new_lines) + "\n"
        ENV_FILE.write_text(content, encoding="utf-8")
    else:
        raise HTTPException(status_code=400, detail="Invalid request payload; provide 'raw' or 'values'")

    # Reload into os.environ
    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip("'\"")
            if k:
                os.environ[k] = v

    return {"status": "saved", "message": ".env configuration saved successfully"}


def sanitize_folder_name(name: str, fallback: str = "video_reels") -> str:
    """Sanitize video title to create clean, human-readable directory name."""
    if not name:
        return fallback
    # Remove invalid Windows/POSIX filename characters: \ / : * ? " < > |
    cleaned = re.sub(r'[\\/*?:"<>|]', '', str(name)).strip()
    # Normalize whitespaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip('. ')
    if not cleaned:
        return fallback
    return cleaned[:60].rstrip('. ')


@app.get("/api/outputs")
async def list_outputs():
    """List rendered MP4 video files grouped by source video folder, strictly excluding internal caches/downloads."""
    if not OUTPUT_DIR.exists():
        return {"folders": [], "files": [], "count": 0}

    manifest_cache = {}

    def resolve_folder_title(folder_dir: Path) -> str:
        if folder_dir in manifest_cache:
            return manifest_cache[folder_dir]
        manifest_p = folder_dir / "manifest.json"
        if manifest_p.exists():
            try:
                import json
                m_data = json.loads(manifest_p.read_text(encoding="utf-8"))
                source = m_data.get("source", "")
                if source:
                    src_json = Path(source).with_suffix(".json")
                    if src_json.exists():
                        j_data = json.loads(src_json.read_text(encoding="utf-8"))
                        if j_data.get("title"):
                            title_val = str(j_data["title"]).strip()
                            manifest_cache[folder_dir] = title_val
                            return title_val
            except Exception:
                pass
        manifest_cache[folder_dir] = folder_dir.name
        return folder_dir.name

    folders_dict: dict[str, dict] = {}
    all_files = []

    for p in sorted(OUTPUT_DIR.glob("**/*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
        # Exclude temporary, cache, raw downloads, checkpoints, and hidden files
        rel_parts = p.relative_to(OUTPUT_DIR).parts
        if any(part in ("web_cache", "downloads", ".checkpoints", ".cache") or part.startswith(".") for part in rel_parts):
            continue
        if p.name.startswith(".") or p.name.startswith("snippet_") or p.name.endswith(".tmp.mp4") or p.name.endswith(".part"):
            continue

        stat = p.stat()
        if stat.st_size <= 1000:
            continue

        rel_path = str(p.relative_to(OUTPUT_DIR)).replace("\\", "/")

        if len(rel_parts) > 1:
            raw_folder_dir = OUTPUT_DIR / rel_parts[0]
            display_folder = resolve_folder_title(raw_folder_dir)
            folder_key = rel_parts[0]
        else:
            display_folder = "Standalone Reels"
            folder_key = "standalone"

        item = {
            "name": p.name,
            "folder": display_folder,
            "folder_key": folder_key,
            "rel_path": rel_path,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "mtime": stat.st_mtime,
            "url": f"/api/outputs/{rel_path}",
        }
        all_files.append(item)
        if display_folder not in folders_dict:
            folders_dict[display_folder] = {
                "name": display_folder,
                "folder_key": folder_key,
                "files": [],
                "latest_mtime": stat.st_mtime,
            }
        folders_dict[display_folder]["files"].append(item)
        if stat.st_mtime > folders_dict[display_folder]["latest_mtime"]:
            folders_dict[display_folder]["latest_mtime"] = stat.st_mtime

    folders_list = sorted(folders_dict.values(), key=lambda f: f["latest_mtime"], reverse=True)
    for f in folders_list:
        f["count"] = len(f["files"])

    return {
        "folders": folders_list,
        "files": all_files,
        "count": len(all_files),
    }


@app.get("/api/outputs/{filepath:path}")
async def serve_output_file(filepath: str):
    """Stream an output video file from output directory or subfolder."""
    # 1. Direct path lookup relative to OUTPUT_DIR
    try:
        clean = Path(filepath).as_posix().lstrip("/")
        candidate = (OUTPUT_DIR / clean).resolve()
        if candidate.is_relative_to(OUTPUT_DIR.resolve()) and candidate.is_file():
            return FileResponse(candidate, media_type="video/mp4")
    except Exception:
        pass

    # 2. Recursive basename search as fallback
    name = Path(filepath).name
    for p in OUTPUT_DIR.glob(f"**/{name}"):
        if p.is_file() and p.resolve().is_relative_to(OUTPUT_DIR.resolve()):
            return FileResponse(p, media_type="video/mp4")

    raise HTTPException(status_code=404, detail="File not found")


@app.post("/api/analyze/start")
async def start_analyze_job(request: Request):
    """Start asynchronous video hook analysis job with real-time progress tracking."""
    data = await request.json()
    url = data.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="Missing URL")

    job_id = f"analyze_{int(time.time() * 1000)}"
    ANALYSIS_JOBS[job_id] = {
        "id": job_id,
        "url": url,
        "status": "running",
        "progress": 5,
        "step_number": 1,
        "step": "Initializing video stream probe...",
        "logs": [f"[{time.strftime('%H:%M:%S')}] Started analysis job for {url}"],
        "created_at": time.time(),
        "result": None,
    }

    asyncio.create_task(run_analysis_pipeline(url, job_id))
    return {"job_id": job_id, "status": "started"}


@app.get("/api/analyze/status/{job_id}")
async def get_analyze_status(job_id: str):
    """Get status, progress, and logs for an ongoing or completed analysis job."""
    if job_id not in ANALYSIS_JOBS:
        raise HTTPException(status_code=404, detail="Analysis job not found")
    return ANALYSIS_JOBS[job_id]


@app.post("/api/analyze")
async def analyze_video(request: Request):
    """Synchronous or direct video hook analysis endpoint."""
    data = await request.json()
    url = data.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="Missing URL")

    job_id = f"analyze_sync_{int(time.time())}"
    ANALYSIS_JOBS[job_id] = {
        "id": job_id,
        "url": url,
        "status": "running",
        "progress": 10,
        "step_number": 1,
        "step": "Analyzing video hooks...",
        "logs": [],
        "created_at": time.time(),
        "result": None,
    }
    return await run_analysis_pipeline(url, job_id)


@app.post("/api/jobs/render_clip")
@app.post("/api/jobs/render")
@app.post("/api/render")
async def render_single_clip(request: Request):
    """Render a selected hook into a 1080x1920 vertical Reel with burned-in subtitles."""
    data = await request.json()
    url = data.get("url", "").strip()
    if not url or not validate_video_url(url):
        raise HTTPException(status_code=400, detail="Invalid or missing video URL; must be an http(s) URL.")

    try:
        start = float(data.get("start", 0))
        end = float(data.get("end", 0))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Start and end timestamps must be numeric.")

    if start < 0 or end <= start:
        raise HTTPException(status_code=400, detail="Invalid clip timestamps: start must be >= 0 and end must be > start.")

    style = data.get("style", "gold").strip().lower()
    framing = data.get("framing", "center").strip().lower()
    title = data.get("title", "Hooky Reel").strip()
    video_title = (data.get("video_title") or data.get("source_title") or "").strip()
    if not video_title:
        try:
            meta = get_video_metadata(url)
            video_title = meta.get("title", "").strip()
        except Exception:
            pass

    job_id = f"render_{int(time.time())}"
    _JOBS[job_id] = {
        "id": job_id,
        "type": "render_clip",
        "status": "running",
        "title": title,
        "progress": 10,
        "step": "Preparing video slice...",
        "logs": [f"[{time.strftime('%H:%M:%S')}] Requested render: '{title}' [{format_timestamp(start)} - {format_timestamp(end)}]"],
        "created_at": time.time(),
        "output_file": None,
    }

    async def _render_task():
        cache_dir = OUTPUT_DIR / "web_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        def log(msg: str):
            print(msg)
            _JOBS[job_id]["logs"].append(f"[{time.strftime('%H:%M:%S')}] {msg}")

        try:
            # 1. Download specific video section
            _JOBS[job_id]["progress"] = 25
            _JOBS[job_id]["step"] = f"Downloading footage segment [{format_timestamp(start)} - {format_timestamp(end)}] via yt-dlp..."
            log(f"[downloader] Fetching {end - start:.1f}s section from {url}...")

            clean_name = re.sub(r"[^\w\-]", "_", title.lower())[:32]
            snippet_path = cache_dir / f"snippet_{clean_name}_{int(start)}_{int(end)}.mp4"

            if not (snippet_path.exists() and snippet_path.stat().st_size > 10000):
                cmd = [
                    sys.executable, "-m", "yt_dlp",
                    "--download-sections", f"*{int(start)}-{int(end + 1.5)}",
                    "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
                    "--merge-output-format", "mp4",
                    "-o", str(snippet_path),
                    "--",
                    url,
                ]
                proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                s_out, s_err = await proc.communicate()
                if proc.returncode != 0:
                    err_msg = s_err.decode("utf-8", errors="replace").strip()
                    log(f"[downloader] yt-dlp failure: {err_msg}")
                    raise RuntimeError(f"yt-dlp error (code {proc.returncode}): {err_msg[:200]}")
                log(f"[downloader] Download complete: {snippet_path.name}")
            else:
                log(f"[downloader] Reusing cached segment: {snippet_path.name}")

            # 2. Build ASS Subtitles keyed strictly by video ID
            _JOBS[job_id]["progress"] = 55
            _JOBS[job_id]["step"] = f"Generating word-aligned ASS subtitles (Preset: {style})..."
            log(f"[subtitles] Synthesizing {style} subtitle cues...")

            vid_id = extract_youtube_id(url)
            vtt_file = None
            if vid_id:
                candidate = cache_dir / f"yt_{vid_id}.vtt"
                if candidate.exists() and candidate.stat().st_size > 0:
                    vtt_file = candidate

            cues = []
            if vtt_file:
                cues = parse_caption_file(vtt_file)
            
            hook_cues = [c for c in cues if c["start"] >= start - 1.0 and c["end"] <= end + 1.5]
            # Convert to 0-relative
            rel_cues = []
            for c in hook_cues:
                rel_cues.append({
                    "start": max(0.0, c["start"] - start),
                    "end": max(0.1, c["end"] - start),
                    "text": c["text"]
                })
            
            clip_len = max(1.0, end - start)
            ass_path = None
            if rel_cues:
                words = caption_words(rel_cues)
                if words:
                    ass_content = build_ass(words, clip_start=0.0, clip_end=clip_len, style_name=style)
                    ass_path = cache_dir / f"subs_{clean_name}_{style}.ass"
                    ass_path.write_text(ass_content, encoding="utf-8")
                    log(f"[subtitles] Saved ASS style file: {ass_path.name}")
                else:
                    log("[subtitles] No words in cues; skipping subtitles")
            else:
                log("[subtitles] No timed captions found for segment; rendering clean video without subtitles")

            # 3. Cut & Encode 1080x1920 Vertical Video into dedicated folder named after video title
            _JOBS[job_id]["progress"] = 75
            _JOBS[job_id]["step"] = "FFmpeg hardware encoding 1080x1920 vertical Reel..."
            log(f"[ffmpeg] Executing vertical filter: framing='{framing}', style='{style}'...")

            clean_folder = sanitize_folder_name(video_title, fallback=clean_name or f"video_{vid_id or 'reels'}")
            target_folder = OUTPUT_DIR / clean_folder
            target_folder.mkdir(parents=True, exist_ok=True)

            out_filename = f"reel_{clean_name}_{int(time.time())}.mp4"
            final_out_path = target_folder / out_filename
            rel_out_path = f"{clean_folder}/{out_filename}"

            # Run cut_clip in thread
            await asyncio.to_thread(
                cut_clip,
                video_path=snippet_path,
                start=0.0,
                end=clip_len,
                out_path=final_out_path,
                ass_path=ass_path,
                framing=framing,
            )

            if final_out_path.exists() and final_out_path.stat().st_size > 1000:
                _JOBS[job_id]["progress"] = 100
                _JOBS[job_id]["step"] = "Render completed successfully! Ready in Output Gallery."
                _JOBS[job_id]["status"] = "completed"
                _JOBS[job_id]["output_file"] = rel_out_path
                _JOBS[job_id]["output_url"] = f"/api/outputs/{rel_out_path}?token={_WEB_TOKEN}"
                log(f"[pipeline] Successfully rendered 9:16 Reel into '{clean_folder}': {out_filename} ({final_out_path.stat().st_size / (1024*1024):.2f} MB)")
                # Remove intermediate landscape snippet to prevent duplicate footage on disk
                try:
                    if snippet_path.exists():
                        snippet_path.unlink()
                except OSError:
                    pass
            else:
                raise RuntimeError("FFmpeg render failed: output file not created.")

        except Exception as exc:
            log(f"[renderer] Error during render: {exc}")
            _JOBS[job_id]["status"] = "failed"
            _JOBS[job_id]["error"] = str(exc)

    asyncio.create_task(_render_task())
    return {"job_id": job_id, "status": "started"}


@app.post("/api/jobs/make")
@app.post("/api/make")
async def launch_make_job(request: Request):
    """Launch full autonomous Hooky pipeline run."""
    data = await request.json()
    target = data.get("target", "").strip()
    if target.startswith("-"):
        raise HTTPException(status_code=400, detail="Invalid target: cannot start with option flag '-'")
    if target and not (target.startswith("http://") or target.startswith("https://") or target.startswith("@") or Path(target).exists()):
        raise HTTPException(status_code=400, detail="Target must be a valid URL, @channel, or local file.")

    style = data.get("style", "gold")
    framing = data.get("framing", "center")

    job_id = f"make_{int(time.time())}"
    cmd_args = [sys.executable, "-u", "-m", "hooky", "make"]
    if target:
        state_dir = Path(os.environ.get("STATE_DIR") or PROJECT_ROOT / ".hooky-state")
        state_dir.mkdir(parents=True, exist_ok=True)
        job_links_file = state_dir / f"job_{job_id}_links.txt"
        job_links_file.write_text(f"{target}\n", encoding="utf-8")
        cmd_args.extend(["--links", str(job_links_file)])
    else:
        cmd_args.append("--links")

    if style:
        cmd_args.extend(["--style", style])
    if framing:
        cmd_args.extend(["--framing", framing])
    cmd_args.extend(["--no-post", "--no-upload"])

    _JOBS[job_id] = {
        "id": job_id,
        "type": "make",
        "status": "running",
        "command": " ".join(cmd_args[1:]),
        "target": target or "channels.txt queue",
        "progress": 5,
        "step": "Initializing Hooky pipeline...",
        "logs": [f"[{time.strftime('%H:%M:%S')}] $ {' '.join(cmd_args)}"],
        "created_at": time.time(),
    }

    async def _run_process():
        try:
            sub_env = {**os.environ, "PYTHONUNBUFFERED": "1"}
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                cwd=str(PROJECT_ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=sub_env,
            )

            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace").rstrip()
                if decoded:
                    _JOBS[job_id]["logs"].append(decoded)
                    lower = decoded.lower()
                    if "download" in lower:
                        _JOBS[job_id]["progress"] = 25
                        _JOBS[job_id]["step"] = "Downloading source video & audio..."
                    elif "gemini" in lower or "highlight" in lower:
                        _JOBS[job_id]["progress"] = 50
                        _JOBS[job_id]["step"] = "Gemini analyzing narrative hook points..."
                    elif "whisper" in lower or "transcrib" in lower:
                        _JOBS[job_id]["progress"] = 70
                        _JOBS[job_id]["step"] = "Faster-whisper word-level audio alignment..."
                    elif "cut" in lower or "ffmpeg" in lower or "render" in lower:
                        _JOBS[job_id]["progress"] = 85
                        _JOBS[job_id]["step"] = "FFmpeg hardware encoding 1080x1920 vertical reel..."
                    elif "complete" in lower or "done" in lower:
                        _JOBS[job_id]["progress"] = 100
                        _JOBS[job_id]["step"] = "Pipeline completed successfully!"

            exit_code = await process.wait()
            _JOBS[job_id]["exit_code"] = exit_code
            _JOBS[job_id]["status"] = "completed" if exit_code == 0 else "failed"
            _JOBS[job_id]["progress"] = 100 if exit_code == 0 else _JOBS[job_id]["progress"]
            if exit_code == 0:
                _JOBS[job_id]["step"] = "Pipeline completed successfully!"
            else:
                _JOBS[job_id]["step"] = f"Pipeline finished with exit code {exit_code}"
        except Exception as exc:
            _JOBS[job_id]["status"] = "failed"
            _JOBS[job_id]["error"] = str(exc)

    async def _run_selective_make_pipeline(url: str, style_name: str, framing_mode: str):
        cache_dir = OUTPUT_DIR / "web_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        def log(msg: str):
            print(msg)
            _JOBS[job_id]["logs"].append(f"[{time.strftime('%H:%M:%S')}] {msg}")

        try:
            # 1. Fetch metadata and VTT captions without downloading the video
            _JOBS[job_id]["progress"] = 10
            _JOBS[job_id]["step"] = "Connecting to stream & fetching timed captions (no video download)..."
            log(f"[pipeline] Fast Selective Pipeline initiated for URL: {url}")
            log(f"[pipeline] Step 1: Fetching video metadata and caption track...")

            meta = get_video_metadata(url)
            title = meta.get("title", "Video")
            duration = float(meta.get("duration", 0.0))
            vid_id = meta.get("id") or extract_youtube_id(url)
            dur_label = format_timestamp(duration) if duration > 0 else "Unknown"
            log(f"[meta] Title: '{title}' | Duration: {dur_label} | ID: {vid_id or 'none'}")

            sub_prefix = cache_dir / (f"yt_{vid_id}" if vid_id else f"sub_{int(time.time())}")
            vtt_path = await download_captions(url, sub_prefix, log)

            cues = []
            if vtt_path and vtt_path.exists():
                cues = parse_caption_file(vtt_path)
                log(f"[captions] Parsed {len(cues)} timed dialogue cues from {vtt_path.name}")
            else:
                log("[captions] Notice: Video has no pre-existing YouTube caption tracks.")

            if not cues:
                # Fast Audio-Only Whisper Fallback:
                # Download ONLY the lightweight audio track (~20 MB instead of a 5 GB video!)
                _JOBS[job_id]["progress"] = 15
                _JOBS[job_id]["step"] = "Downloading lightweight audio stream for faster-whisper transcription..."
                log(f"[pipeline] Downloading audio-only stream (~20-30 MB, no heavy video download)...")

                audio_path = cache_dir / f"audio_{vid_id}.m4a"
                if not (audio_path.exists() and audio_path.stat().st_size > 10000):
                    dl_cmd = [
                        sys.executable, "-m", "yt_dlp",
                        "-f", "ba/bestaudio",
                        "-o", str(audio_path),
                        "--",
                        url,
                    ]
                    dl_proc = await asyncio.create_subprocess_exec(
                        *dl_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await dl_proc.communicate()

                if audio_path.exists() and audio_path.stat().st_size > 10000:
                    _JOBS[job_id]["progress"] = 20
                    _JOBS[job_id]["step"] = "Transcribing audio with faster-whisper..."
                    log(f"[whisper] Running faster-whisper word-level audio alignment...")
                    from hooky.core.subtitles import transcribe
                    words = await asyncio.to_thread(transcribe, audio_path)

                    # Group words into speech cue blocks
                    cues = []
                    curr = []
                    for w in words:
                        curr.append(w)
                        t = str(w.get("word", "")).strip()
                        if (t and t[-1] in ".!?") or len(curr) >= 8:
                            cues.append({
                                "start": curr[0]["start"],
                                "end": curr[-1]["end"],
                                "text": " ".join(x["word"] for x in curr)
                            })
                            curr = []
                    if curr:
                        cues.append({
                            "start": curr[0]["start"],
                            "end": curr[-1]["end"],
                            "text": " ".join(x["word"] for x in curr)
                        })
                    log(f"[whisper] Transcribed {len(words)} words into {len(cues)} dialogue cues.")

            if not cues:
                log("[pipeline] Dialogue transcription unavailable; falling back to standard pipeline...")
                await _run_process()
                return

            # 2. Extract and rank the best scenes across the entire video
            _JOBS[job_id]["progress"] = 25
            _JOBS[job_id]["step"] = "Analyzing entire transcript to extract & rank best scenes..."
            log(f"[analyzer] Step 2: Scoring dialogue pacing, emotional tension, and engagement...")

            # Extract as many non-overlapping scenes as runtime justifies (4-10 scenes)
            target_clips = min(10, max(4, int(duration // 240) + 1)) if duration > 0 else 6
            ranked_scenes = extract_ranked_scenes(cues, title, vid_id, duration, max_clips=target_clips)

            if not ranked_scenes:
                log("[analyzer] No scenes met threshold; falling back to standard pipeline...")
                await _run_process()
                return

            total_scenes = len(ranked_scenes)
            log(f"[analyzer] Extracted {total_scenes} top viral scenes, ranked in best-first order:")
            for sc in ranked_scenes:
                log(f"  - Rank #{sc['rank']} ({sc['retention_score']} pts): \"{sc['title']}\" [{format_timestamp(sc['start'])} - {format_timestamp(sc['end'])}] ({sc['duration']}s)")

            # 3. Selectively download and encode each ranked scene (Rank 1 -> Rank N)
            rendered_files = []
            for sc in ranked_scenes:
                rank = sc["rank"]
                sc_title = sc["title"]
                score = sc["retention_score"]
                start = sc["start"]
                end = sc["end"]
                dur = sc["duration"]

                prog = 25 + int(((rank - 1) / total_scenes) * 70)
                _JOBS[job_id]["progress"] = prog
                _JOBS[job_id]["step"] = f"[{rank}/{total_scenes}] Processing Rank #{rank} ({score} pts): {sc_title}..."
                log(f"[pipeline] >>> [{rank}/{total_scenes}] Downloading section for Rank #{rank}: '{sc_title}' [{format_timestamp(start)} - {format_timestamp(end)}]...")

                clean_name = re.sub(r"[^\w\-]", "_", sc_title.lower())[:24].strip("_")
                snippet_path = cache_dir / f"snippet_{vid_id}_{int(start)}_{int(end)}.mp4"

                # Download ONLY this short slice (typically ~5-15 MB instead of several GB!)
                if not (snippet_path.exists() and snippet_path.stat().st_size > 10000):
                    cmd = [
                        sys.executable, "-m", "yt_dlp",
                        "--download-sections", f"*{int(start)}-{int(end + 1.5)}",
                        "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
                        "--merge-output-format", "mp4",
                        "-o", str(snippet_path),
                        "--",
                        url,
                    ]
                    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                    s_out, s_err = await proc.communicate()
                    if proc.returncode != 0:
                        err_msg = s_err.decode("utf-8", errors="replace").strip()
                        log(f"[downloader] Section download warning for Rank #{rank}: {err_msg[:120]}")
                        continue
                    log(f"[downloader] Section download complete ({snippet_path.stat().st_size / (1024*1024):.1f} MB)")
                else:
                    log(f"[downloader] Reusing cached section: {snippet_path.name}")

                # Build ASS subtitles
                hook_cues = [c for c in cues if c["start"] >= start - 1.0 and c["end"] <= end + 1.5]
                rel_cues = []
                for c in hook_cues:
                    rel_cues.append({
                        "start": max(0.0, c["start"] - start),
                        "end": max(0.1, c["end"] - start),
                        "text": c["text"]
                    })

                ass_path = None
                if rel_cues:
                    words = caption_words(rel_cues)
                    if words:
                        ass_content = build_ass(words, clip_start=0.0, clip_end=dur, style_name=style_name)
                        ass_path = cache_dir / f"subs_rank{rank:02d}_{clean_name}_{style_name}.ass"
                        ass_path.write_text(ass_content, encoding="utf-8")

                # Video title folder
                clean_folder = sanitize_folder_name(title, fallback=f"video_{vid_id}" if vid_id else "video_reels")
                target_folder = OUTPUT_DIR / clean_folder
                target_folder.mkdir(parents=True, exist_ok=True)

                # Cut and encode 1080x1920 vertical Reel
                out_filename = f"reel_rank{rank:02d}_{score}pts_{clean_name}_{int(time.time())}.mp4"
                final_out_path = target_folder / out_filename
                rel_out_path = f"{clean_folder}/{out_filename}"
                log(f"[ffmpeg] Encoding vertical 1080x1920 reel for Rank #{rank} (style: {style_name}, framing: {framing_mode}) in folder '{clean_folder}'...")

                await asyncio.to_thread(
                    cut_clip,
                    video_path=snippet_path,
                    start=0.0,
                    end=dur,
                    out_path=final_out_path,
                    ass_path=ass_path,
                    framing=framing_mode,
                )

                if final_out_path.exists() and final_out_path.stat().st_size > 1000:
                    rendered_files.append(rel_out_path)
                    log(f"[pipeline] Successfully rendered Rank #{rank}: {out_filename} ({final_out_path.stat().st_size / (1024*1024):.2f} MB)")
                    # Clean up intermediate snippet to prevent duplicate video storage
                    try:
                        if snippet_path.exists():
                            snippet_path.unlink()
                    except OSError:
                        pass

            # 4. Final summary
            _JOBS[job_id]["progress"] = 100
            _JOBS[job_id]["status"] = "completed"
            _JOBS[job_id]["output_file"] = rendered_files[0] if rendered_files else ""
            _JOBS[job_id]["output_url"] = f"/api/outputs/{rendered_files[0]}?token={_WEB_TOKEN}" if rendered_files else ""
            _JOBS[job_id]["step"] = f"Pipeline complete! Rendered {len(rendered_files)} ranked reels in Output Gallery."
            log(f"[pipeline] Autonomous selective pipeline finished: {len(rendered_files)} ranked reels ready in Gallery.")

        except Exception as exc:
            log(f"[pipeline error] {exc}")
            _JOBS[job_id]["status"] = "failed"
            _JOBS[job_id]["error"] = str(exc)

    if target and (target.startswith("http://") or target.startswith("https://")):
        asyncio.create_task(_run_selective_make_pipeline(target, style, framing))
    else:
        asyncio.create_task(_run_process())

    return {"job_id": job_id, "status": "started"}


@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Retrieve status and recent logs for an execution job."""
    if job_id not in _JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    return _JOBS[job_id]


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve the single-page visual studio dashboard with auth token injected."""
    if INDEX_HTML.exists():
        content = INDEX_HTML.read_text(encoding="utf-8")
        content = content.replace("HOOKY_AUTH_TOKEN_PLACEHOLDER", _WEB_TOKEN)
        response = HTMLResponse(content)
        response.set_cookie(
            key="hooky_token",
            value=_WEB_TOKEN,
            httponly=False,
            samesite="lax",
            path="/",
        )
        return response
    return HTMLResponse("<h1>Hooky Portal Static File Missing</h1>")


def run_server(args: list[str] | None = None) -> int:
    """Entry point to launch the web portal server."""
    import uvicorn
    import webbrowser

    arg_list = args or []
    if "--setup" in arg_list:
        from ..setup.cli import main as setup_main
        setup_main(["--redo"])
    elif (
        os.environ.get("HOOKY_LAUNCHER_PROMPTED") != "1"
        and sys.stdin
        and sys.stdin.isatty()
        and not any(a in arg_list for a in ("--no-prompt", "--skip-setup", "--headless", "-y"))
    ):
        try:
            ans = input("[hooky] Would you like to review or update .env choices before launching? [y/N]: ").strip().lower()
            if ans in ("y", "yes"):
                from ..setup.cli import main as setup_main
                setup_main(["--redo"])
        except (EOFError, KeyboardInterrupt):
            pass

    port = 8000
    host = "127.0.0.1"
    url = f"http://{host}:{port}"
    portal_url = f"{url}/?token={_WEB_TOKEN}"
    try:
        print(f"\n[hooky] Launching Hooky Web Portal at {portal_url}")
    except Exception:
        pass

    try:
        webbrowser.open(portal_url)
    except Exception:
        pass

    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0
