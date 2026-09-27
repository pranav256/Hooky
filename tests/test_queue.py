"""Durable Instagram queue semantics; all state is temporary and offline."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from reelclip import config
from reelclip.core import queue as post_queue


@pytest.fixture(autouse=True)
def isolated_queue(tmp_path, monkeypatch):
    monkeypatch.setattr(post_queue, "QUEUE_FILE", tmp_path / "state" / "queue.json")
    monkeypatch.setattr(post_queue, "POST_HOURS", "")
    monkeypatch.setattr(post_queue, "IGNORE_WINDOW", False)
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setenv("STATE_DIR", str(tmp_path / "state"))


def test_enqueue_and_due(tmp_path: Path) -> None:
    qfile = tmp_path / "queue.json"
    state = post_queue.load_queue(qfile)
    clip = tmp_path / "reel_01.mp4"
    post_queue.enqueue_clips([clip], state=state, path=qfile,
                             title="title", caption="caption")
    assert str(clip.resolve()) in state["pending"]
    assert state["pending"][str(clip.resolve())]["caption"] == "caption"
    assert post_queue.post_due(state, now=1.0)


def test_successful_post_is_recorded_as_a_code(tmp_path: Path) -> None:
    qfile = tmp_path / "queue.json"
    clip = tmp_path / "reel.mp4"
    state = post_queue.load_queue(qfile)
    post_queue.enqueue_clips([clip], state=state, path=qfile)
    media = type("Media", (), {"code": "posted-code"})()
    post_queue.mark_posted(clip, state, result=media, path=qfile)
    reloaded = post_queue.load_queue(qfile)
    key = str(clip.resolve())
    assert key not in reloaded["pending"]
    assert reloaded["posted"][key]["result"] == "posted-code"
    assert post_queue.is_posted(clip, reloaded)


def test_failed_attempts_and_give_up(tmp_path: Path) -> None:
    clip = tmp_path / "reel.mp4"
    state = post_queue.enqueue_clips([clip])
    for _ in range(3):
        post_queue.mark_failed(clip, state, "boom")
    assert post_queue.attempts(clip, state) == 3
    assert post_queue.give_up(clip, state)
    post_queue.enqueue_clips([clip], state=state)
    assert post_queue.attempts(clip, state) == 3


def test_ignore_is_persistent_and_force_cannot_reset_safety_gap(tmp_path) -> None:
    clip = tmp_path / "reel.mp4"
    state = post_queue.enqueue_clips([clip])
    post_queue.ignore(clip, state)
    post_queue.enqueue_clips([clip], state=state)
    assert not post_queue.is_pending(clip, state)
    state["upload_not_before"] = 100.0
    post_queue.save_queue(state)
    post_queue.force_post_now(state)
    assert not post_queue.post_due(state, now=1.0)
    assert state["upload_not_before"] == 100.0
    assert 120 <= post_queue.force_gap() <= 300


def test_default_state_is_outside_output_and_env_is_lazy(tmp_path, monkeypatch):
    monkeypatch.setattr(post_queue, "QUEUE_FILE", None)
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)
    monkeypatch.delenv("STATE_DIR")
    assert post_queue.queue_path() == tmp_path / ".reelclip-state" / "queue.json"
    monkeypatch.setenv("STATE_DIR", str(tmp_path / "custom"))
    assert post_queue.queue_path() == tmp_path / "custom" / "queue.json"


def _legacy(tmp_path):
    clip = str(tmp_path / "posted.mp4")
    state = {"next_ok": 123.0, "pending": {str(tmp_path / "waiting.mp4"): {"caption": "kept"}},
             "posted": {clip: {"posted_at": 100, "results": {"instagram": "IGcode"}},
                        str(tmp_path / "old.mp4"): {"posted_at": 101, "ig_code": "older_code"}},
             "failed": {str(tmp_path / "waiting.mp4"): {"attempts": 2, "retryable": False}},
             "ignored": []}
    legacy = config.OUTPUT_DIR / "queue.json"
    legacy.parent.mkdir()
    legacy.write_text(json.dumps(state))
    return legacy, state


def test_legacy_migration_is_copy_only_and_preserves_history(tmp_path, monkeypatch):
    legacy, old = _legacy(tmp_path)
    original = legacy.read_bytes()
    monkeypatch.setattr(post_queue, "QUEUE_FILE", None)
    state = post_queue.load_queue()
    assert legacy.read_bytes() == original
    assert post_queue.queue_path().exists()
    assert state["pending"] == old["pending"]
    assert state["failed"] == old["failed"]
    assert state["next_ok"] == 123
    assert sorted(v["result"] for v in state["posted"].values()) == ["IGcode", "older_code"]
    assert post_queue.review_holds(state)
    # A later stale legacy edit must not replace authoritative durable history.
    legacy.write_text("broken")
    assert post_queue.load_queue()["posted"] == state["posted"]


def test_migration_holds_old_failures_without_presend_evidence(tmp_path, monkeypatch):
    legacy, old = _legacy(tmp_path)
    entry = next(iter(old["failed"].values()))
    entry["retryable"] = True
    legacy.write_text(json.dumps(old))
    original = legacy.read_bytes()
    monkeypatch.setattr(post_queue, "QUEUE_FILE", None)
    state = post_queue.load_queue()
    assert post_queue.review_holds(state)
    assert legacy.read_bytes() == original


def test_failed_migration_never_destroys_original(tmp_path, monkeypatch):
    legacy, _ = _legacy(tmp_path)
    original = legacy.read_bytes()
    monkeypatch.setattr(post_queue, "QUEUE_FILE", None)
    monkeypatch.setattr(post_queue, "_atomic_write", lambda *a: (_ for _ in ()).throw(OSError("full")))
    with pytest.raises(OSError):
        post_queue.load_queue()
    assert legacy.read_bytes() == original
    assert not post_queue.queue_path().exists()


def test_explicit_queue_path_never_reads_legacy(tmp_path, monkeypatch):
    monkeypatch.setattr(post_queue, "QUEUE_FILE", None)
    config.OUTPUT_DIR.mkdir()
    (config.OUTPUT_DIR / "queue.json").write_text("corrupt legacy")
    assert not post_queue.load_queue(tmp_path / "isolated.json")["posted"]
    assert not post_queue.queue_path().exists()


@pytest.mark.parametrize("bad", ["{", "null", "[]", "{}",
    '{"posted":[],"pending":{}}', '{"posted":{},"pending":{"clip":"bad"}}',
    '{"posted":{},"pending":{},"next_ok":NaN}',
    '{"posted":{},"pending":{},"ignored":{}}',
    '{"posted":{},"pending":{},"failed":{"clip":{"attempts":"broken"}}}',
    '{"posted":{},"pending":{},"in_flight":[]}',
    '{"posted":{},"pending":{},"posted":{}}'])
def test_corruption_fails_closed_on_read_and_write(tmp_path, bad):
    qfile = tmp_path / "broken.json"
    qfile.write_text(bad)
    with pytest.raises(post_queue.QueueError):
        post_queue.load_queue(qfile)
    with pytest.raises(post_queue.QueueError):
        post_queue.enqueue_clips([tmp_path / "new.mp4"], path=qfile)
    assert qfile.read_text() == bad


def test_mutations_merge_fresh_disk_not_stale_callers(tmp_path):
    a, b, c = [tmp_path / name for name in ("a.mp4", "b.mp4", "c.mp4")]
    maker = post_queue.enqueue_clips([a])
    poster = post_queue.load_queue()
    post_queue.enqueue_clips([b], state=maker)
    post_queue.mark_posted(a, poster, "posted-code")
    post_queue.enqueue_clips([c], state=maker)
    fresh = post_queue.load_queue()
    assert set(fresh["pending"]) == {str(b), str(c)}
    assert post_queue.is_posted(a, fresh)
    assert fresh["next_ok"] > 0
    # A manually saved old snapshot may not restore a posted pending entry.
    poster["next_ok"] = 0
    post_queue.save_queue(poster)
    assert set(post_queue.load_queue()["pending"]) == {str(b), str(c)}


def test_stable_id_dedupes_variants_and_binds_legacy_paths(tmp_path):
    a, b, c = [tmp_path / name for name in ("old.mp4", "variant.mp4", "new.mp4")]
    a.write_bytes(b"clip")
    state = post_queue.enqueue_clips([a])
    post_queue.mark_posted(a, state, "IG123")
    post_queue.enqueue_clips([a], state=state, clip_id="stable-window")
    post_queue.enqueue_clips([b, c], state=state, clip_id="stable-window")
    assert not state["pending"]
    assert len(state["posted"]) == 1
    assert post_queue.is_posted(b, state)
    assert state["posted"][str(a)]["clip_id"] == "stable-window"


def test_same_pending_id_recovers_missing_cache_without_duplicate(tmp_path):
    old, new = tmp_path / "gone.mp4", tmp_path / "regenerated.mp4"
    state = post_queue.enqueue_clips([old], clip_id="stable")
    new.write_bytes(b"new")
    post_queue.enqueue_clips([new], state=state, clip_id="stable")
    assert len(state["pending"]) == 1
    assert post_queue.is_pending(new, state)
    assert post_queue.is_pending(old, state)


def test_legacy_failed_attempts_survive_pending_path_recovery(tmp_path):
    old, new = tmp_path / "old.mp4", tmp_path / "new.mp4"
    state = post_queue.enqueue_clips([old])
    for _ in range(3):
        post_queue.mark_failed(old, state, "local failure")
    new.write_bytes(b"regenerated")
    post_queue.enqueue_clips([old], state=state, clip_id="stable")
    post_queue.enqueue_clips([new], state=state, clip_id="stable")
    assert post_queue.attempts(new, state) == 3
    assert post_queue.give_up(new, state)
    post_queue.retry_after_review(new, state)
    assert post_queue.attempts(new, state) == 0


def test_legacy_unknown_cannot_be_released_by_generic_mutations(tmp_path):
    clip = tmp_path / "clip.mp4"
    state = post_queue.enqueue_clips([clip])
    post_queue.mark_failed(clip, state, "legacy unknown", retryable=False)
    state["failed"][str(clip)]["retryable"] = True
    post_queue.save_queue(state)
    assert post_queue.review_holds(state)
    post_queue.mark_failed(clip, state, "another failure", retryable=True)
    assert post_queue.review_holds(state)


def test_orphan_legacy_hold_can_only_be_requeued_after_review(tmp_path):
    clip = tmp_path / "clip.mp4"
    state = post_queue.load_queue()
    state["failed"][str(clip)] = {"attempts": 1, "retryable": False}
    post_queue.save_queue(state)
    post_queue.enqueue_clips([clip], state=state)
    assert not state["pending"]
    post_queue.retry_after_review(clip, state)
    assert post_queue.is_pending(clip, state)
    assert not post_queue.review_holds(state)


def test_symlink_alias_does_not_duplicate(tmp_path):
    original, alias = tmp_path / "one.mp4", tmp_path / "alias.mp4"
    original.write_bytes(b"clip")
    try:
        alias.symlink_to(original)
    except OSError:
        pytest.skip("symlinks unavailable")
    state = post_queue.enqueue_clips([original, alias])
    assert len(state["pending"]) == 1


def test_hold_survives_stale_save_reset_and_ignore(tmp_path):
    clip = tmp_path / "reel.mp4"
    state = post_queue.enqueue_clips([clip])
    stale = post_queue.load_queue()
    post_queue.begin_upload(clip, state)
    post_queue.save_queue(stale)
    post_queue.force_post_now(stale)
    assert post_queue.review_holds(stale)
    assert not post_queue.post_due(stale, now=1e12)
    with pytest.raises(post_queue.QueueReviewRequired):
        post_queue.ignore(clip, stale)
    with pytest.raises(post_queue.QueueReviewRequired):
        post_queue.begin_upload(clip, stale)


def test_explicit_review_keeps_failure_history_and_can_confirm(tmp_path):
    clip = tmp_path / "reel.mp4"
    state = post_queue.enqueue_clips([clip], clip_id="stable")
    post_queue.begin_upload(clip, state)
    post_queue.mark_failed(clip, state, "timeout", retryable=False)
    post_queue.confirm_posted(clip, "VerifiedCode", state)
    assert not post_queue.review_holds(state)
    assert state["failed"][str(clip)]["last_error"] == "timeout"
    assert state["posted"][str(clip)]["clip_id"] == "stable"
    assert not state["pending"]


def test_explicit_retry_releases_hold_but_not_safety_delay(tmp_path):
    clip = tmp_path / "reel.mp4"
    state = post_queue.enqueue_clips([clip])
    post_queue.begin_upload(clip, state)
    post_queue.mark_failed(clip, state, "timeout", retryable=False)
    not_before = state["upload_not_before"]
    post_queue.retry_after_review(clip, state)
    assert not post_queue.review_holds(state)
    assert post_queue.is_pending(clip, state)
    assert state["upload_not_before"] == not_before
    assert state["failed"][str(clip)]["reviews"][0]["last_error"] == "timeout"


def test_atomic_replace_failure_leaves_old_state(tmp_path, monkeypatch):
    clip = tmp_path / "reel.mp4"
    state = post_queue.enqueue_clips([clip])
    original = state.path.read_bytes()
    monkeypatch.setattr(post_queue.os, "replace", lambda *a: (_ for _ in ()).throw(OSError("full")))
    with pytest.raises(OSError):
        post_queue.begin_upload(clip, state)
    assert state.path.read_bytes() == original
    assert not list(state.path.parent.glob("*.tmp"))


def _child_env(tmp_path):
    return {**os.environ, "OUTPUT_DIR": str(tmp_path / "output"),
            "STATE_DIR": str(tmp_path / "state"),
            "IG_SESSION_FILE": str(tmp_path / "session"),
            "LINKS_FILE": str(tmp_path / "links.txt")}


def test_cross_process_poster_lock_is_bounded_and_released(tmp_path):
    path = tmp_path / "subprocess.json"
    script = """
import sys
from pathlib import Path
from reelclip.core import queue as q
try:
    with q.poster_lock(path=Path(sys.argv[1])):
        pass
except q.QueueBusyError:
    sys.exit(9)
"""
    with post_queue.poster_lock(path=path):
        child = subprocess.run([sys.executable, "-c", script, str(path)],
                               env=_child_env(tmp_path), timeout=10, capture_output=True)
        assert child.returncode == 9, child.stderr
        # Queue mutation is independent of the long-held poster lock.
        post_queue.enqueue_clips([tmp_path / "while-posting.mp4"], path=path)
    child = subprocess.run([sys.executable, "-c", script, str(path)],
                           env=_child_env(tmp_path), timeout=10, capture_output=True)
    assert child.returncode == 0, child.stderr


def test_cross_process_mutations_do_not_lose_enqueues(tmp_path):
    path = tmp_path / "concurrent.json"
    script = """
import sys
from pathlib import Path
from reelclip.core import queue as q
path, prefix = Path(sys.argv[1]), sys.argv[2]
stale = q.load_queue(path)
for n in range(8):
    q.enqueue_clips([path.parent / f'{prefix}-{n}.mp4'], state=stale)
"""
    children = [subprocess.Popen([sys.executable, "-c", script, str(path), str(i)],
                env=_child_env(tmp_path), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                for i in range(3)]
    for child in children:
        _, stderr = child.communicate(timeout=15)
        assert child.returncode == 0, stderr
    assert len(post_queue.load_queue(path)["pending"]) == 24
def test_queue_limit_is_checked_against_fresh_state(tmp_path):
    from reelclip.core.queue import QueueFullError, enqueue_clips, load_queue
    import pytest

    path = tmp_path / "bounded.json"
    stale = load_queue(path)
    enqueue_clips([tmp_path / "first.mp4"], path=path, max_pending=1)
    with pytest.raises(QueueFullError):
        enqueue_clips([tmp_path / "second.mp4"], state=stale, max_pending=1)
    assert len(load_queue(path)["pending"]) == 1
