"""Durable Instagram history, atomic mutations, and pre-upload safety holds.

State lives outside disposable render caches. A separate, OS-owned poster lock
covers a whole posting pass; short mutation locks never cover network requests.
"""
from __future__ import annotations

import copy
import errno
import json
import math
import os
import random
import re
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

from ..config import POST_HOURS, QUEUE_MAX_ATTEMPTS, QUEUE_MAX_GAP, QUEUE_MIN_GAP

FORCE_MIN_GAP = 120
FORCE_MAX_GAP = 300
IGNORE_WINDOW = False  # legacy API; force posting itself does not change this
QUEUE_FILE: Path | None = None


class QueueError(RuntimeError):
    """State cannot safely be used; never replace it with empty history."""


class QueueBusyError(QueueError):
    """Another process owns the queue/posting lock."""


class QueueFullError(QueueError):
    """The maker must resume after publishing frees queue capacity."""


class QueueReviewRequired(QueueError):
    """An upload may have succeeded and requires a human decision."""


class QueueState(dict):
    """Carry the originating path and snapshot without serializing them."""

    def __init__(self, data: dict, path: Path):
        super().__init__(data)
        self.path = path
        self.baseline = copy.deepcopy(data)


def queue_path() -> Path:
    if QUEUE_FILE is not None:
        return Path(QUEUE_FILE)
    from ..config import PROJECT_ROOT
    return Path(os.environ.get("STATE_DIR") or PROJECT_ROOT / ".hooky-state") / "queue.json"


def state_path(state: dict | None = None, path: Path | None = None) -> Path:
    return Path(path or getattr(state, "path", None) or queue_path()).resolve()


@contextmanager
def file_lock(path: Path, timeout: float = 10.0):
    """Bounded advisory lock using flock on POSIX or msvcrt on Windows.

    Never unlink lock files: waiters must keep locking the same inode. The OS
    releases a lock on exit/crash, unlike lock files based only on PID presence.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                if os.name == "nt":
                    import msvcrt
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise
                if time.monotonic() >= deadline:
                    raise QueueBusyError(f"Queue is busy ({path.name}); try later") from exc
                time.sleep(min(0.05, max(0, deadline - time.monotonic())))
        try:
            yield
        finally:
            if os.name == "nt":
                import msvcrt
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def poster_lock(state: dict | None = None, path: Path | None = None):
    return file_lock(state_path(state, path).with_suffix(".post.lock"), timeout=0)


def _empty_state() -> dict:
    return {"next_ok": 0.0, "posted": {}, "failed": {}, "pending": {},
            "ignored": [], "in_flight": {}, "upload_not_before": 0.0}


def _validate(data: object) -> dict:
    if not isinstance(data, dict) or not {"posted", "pending"}.issubset(data):
        raise ValueError("missing queue history")
    data = copy.deepcopy(data)
    for bucket in ("posted", "failed", "pending", "in_flight"):
        values = data.setdefault(bucket, {})
        if not isinstance(values, dict) or any(
                not isinstance(k, str) or not k or not isinstance(v, dict)
                for k, v in values.items()):
            raise ValueError(f"invalid {bucket} history")
        for entry in values.values():
            for field in ("added_at", "posted_at", "last_at", "started_at", "attempts"):
                if field in entry and (isinstance(entry[field], bool)
                        or not isinstance(entry[field], (int, float))
                        or not math.isfinite(entry[field]) or entry[field] < 0):
                    raise ValueError(f"invalid {bucket}.{field}")
            if "retryable" in entry and not isinstance(entry["retryable"], bool):
                raise ValueError("invalid retryable flag")
            if "clip_id" in entry and not isinstance(entry["clip_id"], str):
                raise ValueError("invalid clip ID")
            if "aliases" in entry and (not isinstance(entry["aliases"], list)
                    or any(not isinstance(alias, str) for alias in entry["aliases"])):
                raise ValueError("invalid path aliases")
    ignored = data.setdefault("ignored", [])
    if not isinstance(ignored, list) or any(not isinstance(k, str) for k in ignored):
        raise ValueError("invalid ignored history")
    for field in ("next_ok", "upload_not_before"):
        value = data.setdefault(field, 0.0)
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value < 0):
            raise ValueError(f"invalid {field}")
    # Keep old fields as evidence, while exposing one normalized result field.
    for entry in data["posted"].values():
        if not entry.get("result"):
            results = entry.get("results", {})
            old = results.get("instagram", "") if isinstance(results, dict) else ""
            if isinstance(old, dict):
                old = old.get("code") or old.get("ig_code") or old.get("result", "")
            entry["result"] = old or entry.get("ig_code", "")
    return data


def _unique_object(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_state(path: Path) -> dict:
    for attempt in range(5):
        try:
            return _validate(json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object))
        except FileNotFoundError:
            return _empty_state()
        except PermissionError:
            if attempt == 4:
                raise QueueError(f"Cannot read queue history {path}; refusing to reset it: permission denied")
            time.sleep(0.02)
        except (OSError, ValueError, TypeError) as exc:
            raise QueueError(f"Cannot read queue history {path}; refusing to reset it: {exc}") from exc
    return _empty_state()


def _atomic_write(path: Path, data: dict) -> None:
    data = _validate(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())
        for attempt in range(5):
            try:
                os.replace(temp, path)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.02)
        if os.name != "nt":
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        temp.unlink(missing_ok=True)


def load_queue(path: Path | None = None) -> dict:
    qpath = state_path(path=path)
    with file_lock(qpath.with_suffix(".lock")):
        # Migrate the pre-state-dir queue once without deleting the original.
        # Explicit paths (including QUEUE_FILE test overrides) never inspect
        # the old output location.
        if not qpath.exists() and path is None and QUEUE_FILE is None:
            from ..config import OUTPUT_DIR
            legacy = OUTPUT_DIR / "queue.json"
            if legacy.resolve() != qpath and legacy.exists():
                migrated = _read_state(legacy)
                # Older queues had no pre-send journal. An old retryable flag
                # alone is not proof that a failed request never reached IG.
                for entry in migrated["failed"].values():
                    if entry.get("attempts", 0) and entry.get("phase") != "before_send":
                        entry["retryable"] = False
                _atomic_write(qpath, migrated)
        return QueueState(_read_state(qpath), qpath)


def _refresh(state: dict | None, fresh: dict, path: Path) -> dict:
    if state is None:
        return QueueState(fresh, path)
    state.clear()
    state.update(fresh)
    if isinstance(state, QueueState):
        state.path = path
        state.baseline = copy.deepcopy(dict(fresh))
    return state


def _mutate(state: dict | None, path: Path | None, change) -> dict:
    qpath = state_path(state, path)
    # Migrate first only when operating on the default queue for the first time.
    if state is None and path is None:
        load_queue()
    with file_lock(qpath.with_suffix(".lock")):
        fresh = _read_state(qpath)
        change(fresh)
        _atomic_write(qpath, fresh)
        return _refresh(state, fresh, qpath)


def save_queue(state: dict, path: Path | None = None) -> None:
    """Compatibility save: merge changes, never overwrite concurrent history.

    Safety/posted records cannot be removed by a stale snapshot. Use explicit
    mutation/review functions to remove pending entries or release a hold.
    """
    wanted = _validate(state)
    baseline = getattr(state, "baseline", _empty_state())

    def change(fresh):
        for bucket in ("pending", "posted", "failed", "in_flight"):
            for key, entry in wanted[bucket].items():
                if baseline[bucket].get(key) == entry:
                    continue
                if bucket == "pending" and _matching_key(key, fresh["posted"], entry.get("clip_id", "")):
                    continue
                if (bucket == "failed" and fresh[bucket].get(key, {}).get("retryable") is False
                        and entry.get("retryable") is not False):
                    continue  # legacy unknown outcomes also need explicit review
                if key not in fresh[bucket] or fresh[bucket][key] == baseline[bucket].get(key):
                    fresh[bucket][key] = entry
        fresh["ignored"] = list(dict.fromkeys(fresh["ignored"] + wanted["ignored"]))
        # A generic/stale save must not shorten either safety cooldown.
        for field in ("next_ok", "upload_not_before"):
            fresh[field] = max(fresh[field], wanted[field])
    _mutate(state, path, change)


def _key(clip_path: Path | str) -> str:
    return str(Path(clip_path).resolve())


def _matching_key(clip_path: Path | str, entries: dict, clip_id: str = "") -> str | None:
    norm = os.path.normcase(_key(clip_path))
    for old, entry in entries.items():
        if (norm == os.path.normcase(old) or norm in {os.path.normcase(p) for p in entry.get("aliases", [])}
                or (clip_id and entry.get("clip_id") == clip_id)):
            return old
    return None


def enqueue_clips(clip_paths: list[Path], source_url: str = "",
                  state: dict | None = None, path: Path | None = None,
                  title: str = "", caption: str = "", clip_id: str = "",
                  max_pending: int | None = None) -> dict:
    def change(fresh):
        for clip in clip_paths:
            key = _key(clip)
            existing = None
            for bucket in ("posted", "in_flight", "pending", "failed"):
                match = _matching_key(clip, fresh[bucket], clip_id)
                if match:
                    existing = fresh[bucket][match]
                    # Bind a stable ID when recovering an old path-only entry.
                    if clip_id and not existing.get("clip_id"):
                        existing["clip_id"] = clip_id
                    # Preserve attempt counts when upgrading a legacy pending
                    # path to a stable ID / regenerated cache path.
                    failed_key = _matching_key(match, fresh["failed"])
                    if failed_key:
                        failure = fresh["failed"][failed_key]
                        if clip_id and not failure.get("clip_id"):
                            failure["clip_id"] = clip_id
                        if key != failed_key and key not in failure.setdefault("aliases", []):
                            failure["aliases"].append(key)
                    if key != match and key not in existing.setdefault("aliases", []):
                        existing["aliases"].append(key)
                    # A regenerated pending file can replace a vanished cache
                    # path, but must retain failed/held/posted history.
                    if bucket == "pending" and not Path(match).exists() and Path(key).is_file():
                        existing.setdefault("aliases", []).append(match)
                        fresh["pending"][key] = fresh["pending"].pop(match)
                    break
            if existing is not None or os.path.normcase(key) in {os.path.normcase(p) for p in fresh["ignored"]}:
                continue
            if max_pending is not None and len(fresh["pending"]) >= max_pending:
                raise QueueFullError("Posting queue is full; remaining clips are saved for resume")
            fresh["pending"][key] = {
                "added_at": time.time(), "source_url": source_url,
                "title": (title or "")[:200], "caption": (caption or "")[:4000],
                "clip_id": clip_id,
            }
    return _mutate(state, path, change)


def is_posted(clip_path: Path, state: dict, clip_id: str = "") -> bool:
    return _matching_key(clip_path, state["posted"], clip_id) is not None


def is_pending(clip_path: Path, state: dict, clip_id: str = "") -> bool:
    return _matching_key(clip_path, state["pending"], clip_id) is not None


def result_token(result: object) -> str:
    value = result if isinstance(result, str) else getattr(result, "code", "")
    if (not isinstance(value, str) or value.lower() in {"none", "null"}
            or not re.fullmatch(r"[A-Za-z0-9_-]+", value)):
        raise ValueError("Instagram returned no valid media code")
    return value


def review_holds(state: dict) -> dict:
    held = dict(state.get("in_flight", {}))
    for key, entry in state["failed"].items():
        if entry.get("retryable") is False:
            held.setdefault(key, entry)
    return held


def begin_upload(clip_path: Path, state: dict, path: Path | None = None) -> dict:
    """Commit the safety hold before a single remote upload can be attempted."""
    def change(fresh):
        if review_holds(fresh):
            raise QueueReviewRequired("Unresolved upload outcome; review Instagram first")
        key = _matching_key(clip_path, fresh["pending"])
        if key is None or is_posted(clip_path, fresh, fresh["pending"][key].get("clip_id", "")):
            raise QueueError("Clip is no longer pending")
        if give_up(clip_path, fresh):
            raise QueueError("Clip has exhausted retries; review before retrying")
        if upload_wait(fresh) > 0:
            raise QueueError("Upload safety gap has not elapsed")
        fresh["in_flight"][key] = {
            **fresh["pending"][key], "started_at": time.time(), "status": "in_flight",
        }
        fresh["upload_not_before"] = time.time() + force_gap()
    return _mutate(state, path, change)


def mark_posted(clip_path: Path, state: dict, result: object = "",
                path: Path | None = None) -> dict:
    token = result_token(result)

    def change(fresh):
        key, entry = _key(clip_path), {}
        for bucket in ("pending", "in_flight", "posted", "failed"):
            match = _matching_key(clip_path, fresh[bucket])
            if match:
                key, entry = match, fresh[bucket][match]
                break
        fresh["posted"][key] = {**entry, "posted_at": time.time(), "result": token}
        clip_id = entry.get("clip_id", "")
        for bucket in ("pending", "in_flight"):
            matches = [k for k, v in fresh[bucket].items()
                       if _matching_key(clip_path, {k: v}, clip_id)]
            for match in matches:
                fresh[bucket].pop(match)
        # Preserve failure evidence, but confirmation resolves its retry block.
        match = _matching_key(clip_path, fresh["failed"], clip_id)
        if match:
            fresh["failed"][match]["retryable"] = True
            fresh["failed"][match]["resolved"] = "confirmed_posted"
        fresh["next_ok"] = time.time() + QUEUE_MIN_GAP + random.uniform(
            0, max(0.0, QUEUE_MAX_GAP - QUEUE_MIN_GAP))
        fresh["upload_not_before"] = max(fresh["upload_not_before"], time.time() + force_gap())
    return _mutate(state, path, change)


def mark_failed(clip_path: Path, state: dict, error: str,
                path: Path | None = None, retryable: bool = True) -> dict:
    def change(fresh):
        key = _matching_key(clip_path, fresh["pending"]) or _key(clip_path)
        clip_id = fresh["pending"].get(key, {}).get("clip_id", "")
        failed_key = _matching_key(clip_path, fresh["failed"], clip_id) or key
        entry = fresh["failed"].setdefault(failed_key, {"attempts": 0})
        entry.update({"attempts": int(entry.get("attempts", 0)) + 1,
                      "last_error": str(error)[:300], "last_at": time.time(),
                      "clip_id": clip_id or entry.get("clip_id", ""),
                      "phase": "unknown" if key in fresh["in_flight"] or not retryable else "before_send",
                      "retryable": (bool(retryable) and entry.get("retryable") is not False
                                    and key not in fresh["in_flight"])})
        if key in fresh["in_flight"]:
            fresh["in_flight"][key].update(status="unknown", last_error=str(error)[:300])
            fresh["upload_not_before"] = max(fresh["upload_not_before"], time.time() + force_gap())
    return _mutate(state, path, change)


def cancel_before_send(clip_path: Path, state: dict, error: str,
                       path: Path | None = None) -> dict:
    """Release a hold only for a proven local/preflight failure, never a timeout."""
    def change(fresh):
        key = _matching_key(clip_path, fresh["in_flight"])
        if key is not None:
            fresh["in_flight"].pop(key)
    _mutate(state, path, change)
    return mark_failed(clip_path, state, error, path=path, retryable=True)


def attempts(clip_path: Path, state: dict) -> int:
    pending = _matching_key(clip_path, state["pending"])
    clip_id = state["pending"].get(pending, {}).get("clip_id", "")
    key = _matching_key(clip_path, state["failed"], clip_id)
    return int(state["failed"].get(key, {}).get("attempts", 0))


def give_up(clip_path: Path, state: dict) -> bool:
    pending = _matching_key(clip_path, state["pending"])
    clip_id = state["pending"].get(pending, {}).get("clip_id", "")
    return (_matching_key(clip_path, review_holds(state), clip_id) is not None
            or attempts(clip_path, state) >= QUEUE_MAX_ATTEMPTS)


def confirm_posted(clip_path: Path, code: str, state: dict,
                   path: Path | None = None) -> dict:
    with poster_lock(state, path):
        fresh = load_queue(state_path(state, path))
        if not _matching_key(clip_path, review_holds(fresh)):
            raise QueueError("No held upload for this clip")
        mark_posted(clip_path, fresh, result=code)
        return _refresh(state, fresh, state_path(state, path))


def retry_after_review(clip_path: Path, state: dict, path: Path | None = None) -> dict:
    def change(fresh):
        key = _matching_key(clip_path, fresh["pending"])
        if key is None:
            key = _matching_key(clip_path, review_holds(fresh))
            if key is None:
                raise QueueError("Clip is not pending or held; it cannot be retried")
            held = review_holds(fresh)[key]
            if is_posted(clip_path, fresh, held.get("clip_id", "")):
                raise QueueError("Clip is already recorded posted; confirm the hold instead")
            # Older queues occasionally removed failed clips from pending.
            # Only an explicit review may reconstruct one of those entries.
            fresh["pending"][key] = {
                "added_at": held.get("added_at", time.time()),
                **{field: held.get(field, "") for field in ("source_url", "title", "caption", "clip_id")},
                "aliases": held.get("aliases", []),
            }
        clip_id = fresh["pending"][key].get("clip_id", "")
        if is_posted(clip_path, fresh, clip_id):
            raise QueueError("Clip is already recorded posted; confirm the hold instead")
        for held_key in list(fresh["in_flight"]):
            if _matching_key(clip_path, {held_key: fresh["in_flight"][held_key]}, clip_id):
                fresh["in_flight"].pop(held_key)
        failed_key = _matching_key(clip_path, fresh["failed"], clip_id) or key
        entry = fresh["failed"].setdefault(failed_key, {})
        entry.setdefault("reviews", []).append({
            "reviewed_at": time.time(), "action": "retry_after_review",
            "attempts": entry.get("attempts", 0), "last_error": entry.get("last_error", ""),
        })
        entry.update(attempts=0, retryable=True, resolved="retry_after_review")
    with poster_lock(state, path):
        return _mutate(state, path, change)


def ignore(clip_path: Path, state: dict, path: Path | None = None) -> dict:
    def change(fresh):
        if _matching_key(clip_path, review_holds(fresh)):
            raise QueueReviewRequired("Cannot ignore an uncertain upload; confirm or retry after review")
        key = _matching_key(clip_path, fresh["pending"]) or _key(clip_path)
        if key not in fresh["ignored"]:
            fresh["ignored"].append(key)
        fresh["pending"].pop(key, None)
    return _mutate(state, path, change)


def force_post_now(state: dict, path: Path | None = None) -> dict:
    """Reset only the schedule, never safety holds or the minimum upload gap."""
    def change(fresh):
        fresh["next_ok"] = 0.0
    return _mutate(state, path, change)


def force_gap() -> float:
    return random.uniform(FORCE_MIN_GAP, FORCE_MAX_GAP)


def upload_wait(state: dict, now: float | None = None) -> float:
    return max(0.0, state.get("upload_not_before", 0.0) - (time.time() if now is None else now))


def _post_window() -> tuple[int, int] | None:
    match = re.fullmatch(r"(\d{1,2})\s*-\s*(\d{1,2})", (POST_HOURS or "").strip())
    if not match:
        return None
    start, end = int(match.group(1)), int(match.group(2))
    return (start, end) if start != end and 0 <= start <= 23 and 0 <= end <= 23 else None


def in_post_window(now: float | None = None) -> bool:
    window = _post_window()
    if IGNORE_WINDOW or window is None:
        return True
    hour = time.localtime(time.time() if now is None else now).tm_hour
    start, end = window
    return start <= hour < end if start < end else hour >= start or hour < end


def _seconds_until_window(now: float) -> float:
    window = _post_window()
    if window is None or in_post_window(now):
        return 0.0
    local = time.localtime(now)
    hours_ahead = (window[0] - local.tm_hour) % 24 or 24
    return hours_ahead * 3600 - (local.tm_min * 60 + local.tm_sec)


def post_due(state: dict, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    return (not review_holds(state) and now >= state.get("next_ok", 0)
            and upload_wait(state, now) <= 0 and in_post_window(now))


def wait_seconds(state: dict, now: float | None = None) -> float:
    now = time.time() if now is None else now
    return max(0.0, state.get("next_ok", 0) - now,
               upload_wait(state, now), _seconds_until_window(now))


def status_line(state: dict) -> str:
    if review_holds(state):
        return "BLOCKED: review uncertain upload on Instagram before confirming/retrying"
    if post_due(state):
        return "ready to post"
    hours, remainder = divmod(wait_seconds(state), 3600)
    return f"next post in {int(hours)}h {int(remainder // 60):02d}m"


def format_posted_at(entry: dict) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(entry.get("posted_at", 0)))

