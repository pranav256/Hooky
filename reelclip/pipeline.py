"""Resumable source-text selection -> styled subtitles -> render -> queue."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from .config import GEMINI_MODEL, GEMINI_FALLBACK_MODELS, OUTPUT_DIR
from .core.captions import generate_captions
from .core.checkpoints import (atomic_json, digest, file_revision, load_checkpoint,
                               save_checkpoint, source_id, clip_id)
from .core.cutter import cut_all_clips
from .core.highlights import find_highlights, plan_auto_clips, snap_clip_boundaries
from .core.lowspec import WHISPER_MODEL, WHISPER_COMPUTE
from .core.queue import enqueue_clips
from .core.source_text import load_caption_file, sidecar_caption_file
from .core.subtitles import transcribe
from .core.utils import get_duration
from .options import PipelineOptions


@dataclass
class Job:
    video: Path
    clips: list[dict] = field(default_factory=list)
    manifest: dict = field(default_factory=dict)


class Pipeline:
    """Source captions choose meaning; Whisper still creates styled word subtitles."""

    def __init__(self, options: PipelineOptions | None = None) -> None:
        self.options = options or PipelineOptions()
        self.state = {"find_highlights": find_highlights, "transcribe": transcribe,
                      "generate_captions": generate_captions,
                      "cut_all_clips": cut_all_clips}

    @staticmethod
    def _load_words_cache(path: Path) -> list[dict] | None:
        # Reading an explicitly supplied old word cache remains supported.
        # The pipeline itself uses versioned selected-window checkpoints.
        try:
            words = json.loads(path.read_text(encoding="utf-8"))
            return words if isinstance(words, list) and words else None
        except (OSError, ValueError):
            return None

    def transcribe_windows(self, video: Path, clips: list[dict],
                           cache_path: Path | None = None,
                           duration: float | None = None) -> list[dict]:
        if self.options.no_subs:
            return []
        windows = []
        for clip in sorted(clips, key=lambda c: c["start"]):
            start = max(0.0, float(clip["start"]) - 2.0)
            end = float(clip["end"]) + 2.0
            if duration is not None:
                end = min(end, duration)
            if end <= start:
                raise ValueError("Invalid transcription window")
            if windows and start <= windows[-1][1]:
                windows[-1][1] = max(end, windows[-1][1])
            else:
                windows.append([start, end])
        signature = {"version": 2, "source": file_revision(video), "windows": windows,
                     "model": WHISPER_MODEL, "compute": WHISPER_COMPUTE,
                     "language": self.options.sub_lang}
        words = load_checkpoint(cache_path, signature) if cache_path else None
        if not isinstance(words, list) or not words:
            words = self.state["transcribe"](
                video, language=self.options.sub_lang,
                clip_timestamps=[t for window in windows for t in window])
            if not isinstance(words, list) or not words:
                raise RuntimeError("No subtitle words detected; source remains unprocessed. "
                                   "Review the audio or explicitly use --no-subs.")
            if cache_path:
                save_checkpoint(cache_path, signature, words)
        return words

    def run(self, video: Path, *, context: dict | None = None,
            source_url: str = "", queue_state: dict | None = None,
            analysis_path: Path | None = None,
            source_transcript: list[dict] | None = None) -> Job:
        started = time.perf_counter()
        o = self.options
        video = Path(video)
        ident = source_id(video, source_url)
        out_dir = o.out if o.out is not None else OUTPUT_DIR / ident
        revision = file_revision(video)
        duration = get_duration(video)
        if duration < 3:
            raise ValueError("Source is too short for a Reel")
        count, minimum, maximum = ((o.clips, o.min_len, o.max_len) if o.clips else
                                   plan_auto_clips(duration))
        # One very long source must not overfill the publishing backlog either.
        if queue_state is not None and not o.no_upload:
            room = max(0, int(os.environ.get("QUEUE_MAX_PENDING", "12"))
                       - len(queue_state.get("pending", {})))
            if room == 0:
                raise RuntimeError("Posting queue is full; post/review it before making more clips")
            count = min(count, room)
        transcript = source_transcript or load_caption_file(sidecar_caption_file(video))
        selection_signature = {
            "version": 3, "source": revision, "transcript": digest(transcript),
            "count": count, "min": minimum, "max": maximum, "context": context,
            "model": GEMINI_MODEL, "fallbacks": GEMINI_FALLBACK_MODELS,
        }
        cache_dir = out_dir / ".checkpoints" / digest(selection_signature)
        clips = load_checkpoint(cache_dir / "highlights.json", selection_signature)
        if not isinstance(clips, list) or not clips:
            clips = self.state["find_highlights"](
                video, n_clips=count, clip_min=minimum, clip_max=maximum,
                context=context, analysis_path=analysis_path,
                transcript=transcript, cache_dir=cache_dir)
            if not clips:
                raise RuntimeError("No highlights selected; source remains unprocessed")
            clips = clips[:count]
            save_checkpoint(cache_dir / "highlights.json", selection_signature, clips)
        else:
            print("[resume] Reusing selected highlights")
        if o.dry_run:
            return Job(video, clips=clips)

        # Raw source captions never replace the custom burned-in ASS subtitles.
        words = [] if o.no_subs else self.transcribe_windows(
            analysis_path or video, clips,
            cache_path=cache_dir / "selected.words.json", duration=duration)
        if words:
            clips = snap_clip_boundaries(clips, words, minimum, maximum)
        # Enforce source bounds, durations and non-overlap after speech snapping.
        bounded = []
        for c in clips:
            start, end = max(0.0, c["start"]), min(duration, c["end"])
            start = max(start, bounded[-1]["end"] if bounded else 0)
            end = min(end, start + maximum)
            if end - start < min(minimum, duration):
                continue
            bounded.append({**c, "start": start, "end": end,
                            "clip_id": clip_id(ident, start, end)})
        clips = bounded
        if not clips:
            raise RuntimeError("No complete non-overlapping clips after boundary checks")
        if not o.no_subs:
            for c in clips:
                if not any(w["start"] < c["end"] and w["end"] > c["start"] for w in words):
                    raise RuntimeError("Selected clip has no subtitle words; review speech before queueing")

        caption_signature = {"version": 2, "source": revision, "clips": clips,
                             "context": context, "model": GEMINI_MODEL,
                             "fallbacks": GEMINI_FALLBACK_MODELS,
                             "spoken": digest(words)}
        meta = [{"caption": ""} for _ in clips] if o.no_captions else load_checkpoint(
            cache_dir / "captions.json", caption_signature)
        if meta is None:
            meta = self.state["generate_captions"](
                [{"index": i + 1, **c,
                  "spoken": " ".join(w["word"] for w in words
                                     if w["start"] < c["end"] and w["end"] > c["start"])[:2500]}
                 for i, c in enumerate(clips)], video.name, context=context)
            if not isinstance(meta, list) or len(meta) != len(clips):
                raise ValueError("Invalid caption count")
            save_checkpoint(cache_dir / "captions.json", caption_signature, meta)
        results = self.state["cut_all_clips"](
            video, clips, output_dir=out_dir, words=words, sub_style=o.sub_style)
        if len(results) != len(clips):
            raise RuntimeError("Renderer returned incomplete results; source remains unprocessed")
        manifest = {"version": 2, "source": str(video), "source_url": source_url,
                    "source_id": ident, "sub_style": None if o.no_subs else o.sub_style,
                    "selection_evidence": "source captions" if transcript else "visual/audio fallback",
                    "clips": []}
        job = Job(video=video, manifest=manifest)
        for result, caption, selected in zip(results, meta, clips):
            path = Path(result["path"])
            if not o.no_subs and not result.get("subtitled"):
                raise RuntimeError("Subtitle burn-in missing; refusing to queue an uncaptioned clip")
            text = str(caption.get("caption", ""))
            sidecar = path.with_suffix(".caption.txt")
            if not sidecar.exists():  # preserve the user's manual caption edits
                sidecar.write_text(text, encoding="utf-8")
            else:
                text = sidecar.read_text(encoding="utf-8").strip()
            item = {**result, "clip_id": selected["clip_id"], "path": str(path),
                    "caption": text, "cover": str(result.get("cover") or "")}
            manifest["clips"].append(item)
            job.clips.append({**item, "path": path})
        # Commit manifest before queueing; a rerun restores any missing queue entries.
        atomic_json(out_dir / "manifest.json", manifest)
        if queue_state is not None and not o.no_upload:
            for item in job.clips:
                enqueue_clips([item["path"]], source_url=source_url, state=queue_state,
                              title=(context or {}).get("title", video.stem),
                              caption=item["caption"], clip_id=item["clip_id"])
        print(f"[timing] total pipeline: {time.perf_counter() - started:.1f}s")
        return job
