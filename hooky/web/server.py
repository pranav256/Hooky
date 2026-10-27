from __future__ import annotations

import os
import re
import sys
import json
import time
import shutil
import asyncio
import subprocess
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from hooky.config import CHANNELS_FILE, LINKS_FILE, OUTPUT_DIR, PROJECT_ROOT, ENV_FILE
from hooky.doctor import dependency_checks
from hooky.core.subtitles import STYLES, build_ass
from hooky.core.source_text import parse_caption_file, caption_words
from hooky.core.cutter import cut_clip
from hooky.core.utils import format_timestamp
from hooky.web.analyzer import (
    ANALYSIS_JOBS,
    run_analysis_pipeline,
    extract_youtube_id,
    get_video_metadata,
)

app = FastAPI(title="Hooky Web Studio & Control Portal", version="2.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"

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
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k, _, v = stripped.partition("=")
            k = k.strip()
            v = v.strip().strip("'\"")
            if k == "IG_PASSWORD" and v:
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

    if "raw" in data and isinstance(data["raw"], str):
        # Preserve real IG_PASSWORD if submitted with dots
        lines = []
        for line in data["raw"].splitlines():
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, _, v = s.partition("=")
                k = k.strip()
                v = v.strip().strip("'\"")
                if k == "IG_PASSWORD" and v.startswith("••") and k in existing_secrets:
                    v_orig = existing_secrets[k]
                    lines.append(f'{k}="{v_orig}"' if " " in v_orig else f"{k}={v_orig}")
                    continue
            lines.append(line)
        content = "\n".join(lines).rstrip() + "\n"
        ENV_FILE.write_text(content, encoding="utf-8")
    elif "values" in data and isinstance(data["values"], dict):
        updated = dict(data["values"])
        # Protect IG_PASSWORD from being overwritten by mask
        if updated.get("IG_PASSWORD", "").startswith("••"):
            if "IG_PASSWORD" in existing_secrets:
                updated["IG_PASSWORD"] = existing_secrets["IG_PASSWORD"]
            else:
                updated.pop("IG_PASSWORD", None)

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


@app.get("/api/outputs")
async def list_outputs():
    """List rendered MP4 video files in output directory."""
    if not OUTPUT_DIR.exists():
        return {"files": []}
    files = []
    # Scan root output dir and immediate subdirs
    for p in sorted(OUTPUT_DIR.glob("**/*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
        stat = p.stat()
        if stat.st_size > 1000:
            files.append({
                "name": p.name,
                "rel_path": str(p.relative_to(OUTPUT_DIR)),
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "mtime": stat.st_mtime,
                "url": f"/api/outputs/{p.name}",
            })
    return {"files": files, "count": len(files)}


@app.get("/api/outputs/{filename}")
async def serve_output_file(filename: str):
    """Stream an output video file."""
    for p in OUTPUT_DIR.glob(f"**/{filename}"):
        if p.is_file():
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
    url = data.get("url", "https://www.youtube.com/watch?v=EDCwQe7P8T0").strip()
    start = float(data.get("start", 37.36))
    end = float(data.get("end", 50.79))
    style = data.get("style", "gold").strip().lower()
    framing = data.get("framing", "center").strip().lower()
    title = data.get("title", "Hooky Reel").strip()

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

            # 2. Build ASS Subtitles
            _JOBS[job_id]["progress"] = 55
            _JOBS[job_id]["step"] = f"Generating word-aligned ASS subtitles (Preset: {style})..."
            log(f"[subtitles] Synthesizing {style} subtitle cues...")

            vtt_candidates = sorted(cache_dir.glob("*.vtt"), key=lambda x: x.stat().st_mtime, reverse=True)
            cues = []
            if vtt_candidates:
                cues = parse_caption_file(vtt_candidates[0])
            
            hook_cues = [c for c in cues if c["start"] >= start - 1.0 and c["end"] <= end + 1.5]
            # Convert to 0-relative
            rel_cues = []
            for c in hook_cues:
                rel_cues.append({
                    "start": max(0.0, c["start"] - start),
                    "end": max(0.1, c["end"] - start),
                    "text": c["text"]
                })
            
            words = caption_words(rel_cues) if rel_cues else [
                {"start": 0.5, "end": 2.5, "word": "UNHINGED"},
                {"start": 2.5, "end": 4.5, "word": "CRAZY"},
                {"start": 4.5, "end": 6.5, "word": "TONIGHT"}
            ]

            clip_len = max(5.0, end - start)
            ass_content = build_ass(words, clip_start=0.0, clip_end=clip_len, style_name=style)
            ass_path = cache_dir / f"subs_{clean_name}_{style}.ass"
            ass_path.write_text(ass_content, encoding="utf-8")
            log(f"[subtitles] Saved ASS style file: {ass_path.name}")

            # 3. Cut & Encode 1080x1920 Vertical Video
            _JOBS[job_id]["progress"] = 75
            _JOBS[job_id]["step"] = "FFmpeg hardware encoding 1080x1920 vertical Reel..."
            log(f"[ffmpeg] Executing vertical filter: framing='{framing}', style='{style}'...")

            out_filename = f"reel_{clean_name}_{int(time.time())}.mp4"
            final_out_path = OUTPUT_DIR / out_filename

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

            _JOBS[job_id]["progress"] = 100
            _JOBS[job_id]["step"] = "Render completed successfully! Ready in Output Gallery."
            _JOBS[job_id]["status"] = "completed"
            _JOBS[job_id]["output_file"] = out_filename
            _JOBS[job_id]["output_url"] = f"/api/outputs/{out_filename}"
            log(f"[pipeline] Successfully rendered 9:16 Reel: {out_filename} ({final_out_path.stat().st_size / (1024*1024):.2f} MB)")

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
    style = data.get("style", "gold")
    framing = data.get("framing", "center")

    job_id = f"make_{int(time.time())}"
    cmd_args = [sys.executable, "-m", "hooky", "make"]
    if target and target.startswith("http"):
        links_content = LINKS_FILE.read_text(encoding="utf-8") if LINKS_FILE.exists() else ""
        if target not in links_content:
            LINKS_FILE.write_text((links_content.rstrip() + f"\n{target}\n").lstrip(), encoding="utf-8")
        cmd_args.append("--links")
    elif target:
        cmd_args.append(target)
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
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                cwd=str(PROJECT_ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
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
        except Exception as exc:
            _JOBS[job_id]["status"] = "failed"
            _JOBS[job_id]["error"] = str(exc)

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
    """Serve the single-page visual studio dashboard."""
    if INDEX_HTML.exists():
        return HTMLResponse(INDEX_HTML.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Hooky Portal Static File Missing</h1>")


def run_server(args: list[str] | None = None) -> int:
    """Entry point to launch the web portal server."""
    import uvicorn
    import webbrowser

    port = 8000
    host = "127.0.0.1"
    url = f"http://{host}:{port}"
    print(f"\n[hooky] 🚀 Launching Hooky Web Portal at {url}")

    try:
        webbrowser.open(url)
    except Exception:
        pass

    uvicorn.run("hooky.web.server:app", host=host, port=port, log_level="info")
    return 0
