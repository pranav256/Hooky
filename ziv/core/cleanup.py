"""Explicit disposable-media cleanup with conservative path guards."""
from __future__ import annotations

import json
import os
from pathlib import Path

from ..config import (CHANNELS_FILE, DELETE_POSTED_CLIPS,
                      DELETE_SOURCE_AFTER_CLIP, LINKS_FILE, PROJECT_ROOT,
                      SESSION_FILE)


def _protected_paths() -> set[Path]:
    state_dir = Path(os.environ.get("STATE_DIR") or PROJECT_ROOT / ".ziv-state")
    return {
        PROJECT_ROOT / ".env",
        PROJECT_ROOT / ".git",
        LINKS_FILE.resolve(),
        CHANNELS_FILE.resolve(),
        SESSION_FILE.resolve(),
        state_dir.resolve(),
    }


def _can_remove(path: Path) -> bool:
    """Prevent cleanup from targeting project control files or directories."""
    if path in _protected_paths() or path.resolve() in _protected_paths():
        return False
    return path.is_file() or path.is_symlink()


def _unlink(path: Path, removed: list[Path]) -> None:
    if not _can_remove(path):
        return
    path.unlink()
    removed.append(path)


def delete_clip_artifacts(clip_path: Path, *, enabled: bool = DELETE_POSTED_CLIPS) -> list[Path]:
    """Remove a confirmed-post clip and its generated sidecars.

    The queue must be durably marked posted before this function is called.
    It never removes manifests, checkpoints, queue history, or directories.
    """
    if not enabled:
        return []
    clip_path = Path(clip_path)
    removed: list[Path] = []
    _unlink(clip_path, removed)
    _unlink(clip_path.with_suffix(".ass"), removed)
    _unlink(clip_path.with_name(clip_path.stem + ".caption.txt"), removed)
    _unlink(clip_path.with_name(clip_path.stem + "_cover.jpg"), removed)
    return removed


def delete_source_artifacts(video_path: Path, *, enabled: bool = DELETE_SOURCE_AFTER_CLIP) -> list[Path]:
    """Remove a successfully processed source and disposable download siblings."""
    if not enabled:
        return []
    video_path = Path(video_path)
    removed: list[Path] = []
    _unlink(video_path, removed)

    # A downloaded source may have an analysis twin and metadata/caption cache.
    # Local source sidecars are deliberately preserved because they may be
    # independently useful to the user.
    _unlink(video_path.with_name(video_path.stem + "_analysis.mp4"), removed)
    if video_path.parent.name == "downloads":
        metadata_path = video_path.with_suffix(".json")
        caption_paths: list[Path] = []
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            value = metadata.get("source_captions", "") if isinstance(metadata, dict) else ""
            if value:
                caption_paths.append(Path(value))
        except (OSError, ValueError, TypeError):
            pass
        for caption_path in caption_paths:
            if caption_path.parent == video_path.parent:
                _unlink(caption_path, removed)
        _unlink(metadata_path, removed)
    return removed
