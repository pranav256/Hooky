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
from .core.profiling import PipelineProfile
from .core.queue import enqueue_clips
from .core.source_text import caption_words, load_caption_file, sidecar_caption_file
from .core.subtitles import transcribe
from .core.utils import get_duration
from .options import PipelineOptions


@dataclass
class Job:
    video: Path
    clips: list[dict] = field(default_factory=list)
    manifest: dict = field(default_factory=dict)


class Pipeline:
    """Source captions choose meaning and can provide styled subtitle timing."""

    def __init__(self, options: PipelineOptions | None = None) -> None:
        self.options = options or PipelineOptions()
        self.last_subtitle_source = "none"
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
            self.last_subtitle_source = "disabled"
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
        if isinstance(words, list) and words:
            return words

        # Cache each union window independently as well as retaining the old
        # combined checkpoint format. Editing one clip then only retranscribes
        # the newly introduced windows.
        cached_words: list[dict] = []
        missing: list[list[float]] = []
        paths: dict[tuple[float, float], Path] = {}
        for window in windows:
            window_signature = {"version": 1, "source": file_revision(video),
                                "window": window, "model": WHISPER_MODEL,
                                "compute": WHISPER_COMPUTE,
                                "language": self.options.sub_lang}
            window_path = None
            if cache_path:
                window_path = cache_path.with_name(
                    f"{cache_path.stem}.{digest(window_signature)}{cache_path.suffix}")
                paths[(window[0], window[1])] = window_path
            value = load_checkpoint(window_path, window_signature) if window_path else None
            if isinstance(value, list):
                cached_words.extend(value)
            else:
                missing.append(window)

        if missing:
            generated = self.state["transcribe"](
                video, language=self.options.sub_lang,
                clip_timestamps=[t for window in missing for t in window])
            if not isinstance(generated, list):
                generated = []
            for window in missing:
                start, end = window
                selected = [word for word in generated
                            if isinstance(word, dict)
                            and float(word.get("start", -1)) < end
                            and float(word.get("end", -1)) > start]
                cached_words.extend(selected)
                window_path = paths.get((start, end))
                if window_path:
                    window_signature = {"version": 1, "source": file_revision(video),
                                        "window": window, "model": WHISPER_MODEL,
                                        "compute": WHISPER_COMPUTE,
                                        "language": self.options.sub_lang}
                    save_checkpoint(window_path, window_signature, selected)

        words = sorted(cached_words, key=lambda word: float(word.get("start", 0)))
        if not words:
            raise RuntimeError("No subtitle words detected; source remains unprocessed. "
                               "Review the audio or explicitly use --no-subs.")
        if cache_path:
            save_checkpoint(cache_path, signature, words)
        return words

    def subtitle_words(self, video: Path, clips: list[dict],
                       transcript: list[dict], cache_path: Path,
                       duration: float | None = None) -> list[dict]:
        """Prefer timestamped source captions, falling back to selected Whisper."""
        if self.options.no_subs:
            return []
        if self.options.subtitle_source in {"auto", "source"}:
            if transcript:
                signature = {"version": 1, "source": file_revision(video),
                             "transcript": digest(transcript),
                             "subtitle_source": "source"}
                words = load_checkpoint(cache_path, signature)
                if not isinstance(words, list):
                    words = caption_words(transcript)
                    save_checkpoint(cache_path, signature, words)
                if words:
                    self.last_subtitle_source = "source"
                    print(f"[subs] Using {len(words)} words from source captions")
                    return words
                if self.options.subtitle_source == "source":
                    raise RuntimeError("Source captions were present but had no usable words; "
                                       "use --subtitle-source auto or whisper")
            elif self.options.subtitle_source == "source":
                raise RuntimeError("Source captions were requested but none were available; "
                                   "use --subtitle-source auto or whisper")
        words = self.transcribe_windows(video, clips, cache_path=cache_path,
                                        duration=duration)
        self.last_subtitle_source = "whisper"
        return words

    def run(self, video: Path, *, context: dict | None = None,
            source_url: str = "", queue_state: dict | None = None,
            analysis_path: Path | None = None,
            source_transcript: list[dict] | None = None) -> Job:
        started = time.perf_counter()
        o = self.options
        profile = PipelineProfile(o.profile)
        video = Path(video)
        ident = source_id(video, source_url)
        out_dir = o.out if o.out is not None else OUTPUT_DIR / ident
        revision = file_revision(video)
        with profile.stage("probe"):
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
        with profile.stage("selection"):
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
                profile.count("selection_cache_hits")
                print("[resume] Reusing selected highlights")
        if o.dry_run:
            atomic_json(out_dir / "selection.json", {
                "version": 1, "source": str(video), "source_url": source_url,
                "selection_evidence": "source captions" if transcript
                else "visual/audio fallback", "clips": clips,
            })
            profile.save(out_dir / "profile.json")
            return Job(video, clips=clips)

        # Source captions provide timing when configured; Whisper remains the
        # selected-window fallback. Both paths produce custom burned-in ASS.
        with profile.stage("subtitles"):
            words = self.subtitle_words(
                analysis_path or video, clips, transcript,
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
        with profile.stage("captions"):
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
        with profile.stage("render"):
            results = self.state["cut_all_clips"](
                video, clips, output_dir=out_dir, words=words, sub_style=o.sub_style,
                make_covers=o.make_covers)
        if len(results) != len(clips):
            raise RuntimeError("Renderer returned incomplete results; source remains unprocessed")
        manifest = {"version": 2, "source": str(video), "source_url": source_url,
                    "source_id": ident, "sub_style": None if o.no_subs else o.sub_style,
                    "subtitle_source": self.last_subtitle_source,
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
            with profile.stage("queue"):
                for item in job.clips:
                    enqueue_clips([item["path"]], source_url=source_url, state=queue_state,
                                  title=(context or {}).get("title", video.stem),
                                  caption=item["caption"], clip_id=item["clip_id"])
        profile.data["source"] = str(video)
        profile.data["clips"] = len(job.clips)
        profile.data["total_seconds"] = round(time.perf_counter() - started, 4)
        profile.save(out_dir / "profile.json")
        print(f"[timing] total pipeline: {time.perf_counter() - started:.1f}s")
        return job
