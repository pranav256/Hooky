"""Linux-first curses dashboard and source controller for Ziv.

The module has two deliberately separate layers:

* :class:`TuiModel` and :func:`render_frame` are pure terminal-state helpers
  that can be exercised with ordinary strings and fake screens.
* :func:`run_tui` is the very small curses adapter a future CLI can call.

The dashboard keeps terminal drawing separate from source mutations so it can
be tested without a real terminal. It can add/remove named sources and launch
one resumable local workflow at a time; authentication, CAPTCHA solving, and
access-control bypasses are never automated.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

from .catalog import SourceCatalog


VIEWS = ("sources", "queue", "resources", "logs")
VIEW_LABELS = {
    "sources": "SOURCES",
    "queue": "QUEUE",
    "resources": "RESOURCES",
    "logs": "LOGS",
}


def _clip(value: Any, width: int) -> str:
    text = str(value if value is not None else "")
    if width <= 0:
        return ""
    if len(text) <= width:
        return text.ljust(width)
    if width == 1:
        return text[:1]
    return text[:width - 1] + "…"


def _line(value: Any, width: int) -> str:
    return _clip(value, max(1, width))


def _human_bytes(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "?"
    units = ("B", "K", "M", "G", "T")
    unit = 0
    while abs(number) >= 1024 and unit < len(units) - 1:
        number /= 1024
        unit += 1
    return f"{number:.1f}{units[unit]}"


def _gauge(label: str, percent: Any, width: int = 18) -> str:
    try:
        value = max(0.0, min(100.0, float(percent)))
    except (TypeError, ValueError):
        value = 0.0
    filled = round(width * value / 100)
    return f"{label:<5} [{'#' * filled}{'-' * (width - filled)}] {value:5.1f}%"


def _header(width: int, active_view: str) -> list[str]:
    title = " ZIV // TERMINAL CONTROL "
    subtitle = "source console | safe resumable workflows"
    tabs = "  ".join(
        f"[{index} {VIEW_LABELS[name]}]" if name == active_view
        else f"  {index} {VIEW_LABELS[name]} "
        for index, name in enumerate(VIEWS, 1)
    )
    return [
        _line(title + " " + subtitle, width),
        _line(tabs, width),
        _line("-" * width, width),
    ]


def _sources_body(snapshot: dict[str, Any], width: int, selected: int) -> list[str]:
    statuses = list(snapshot.get("statuses") or [])
    summary = snapshot.get("summary") or {}
    left = max(32, width // 2)
    right = max(1, width - left - 3)
    lines = [
        _line(f"SOURCES  active={summary.get('active', 0)}  done={summary.get('done', 0)}  "
              f"missing={summary.get('missing', 0)}  disabled={summary.get('disabled', 0)}", width),
        _line("-" * left + "   " + "DETAILS", width),
    ]
    if not statuses:
        lines.append(_line("No sources in the catalog. Import links.txt/channels.txt or add a named source.", width))
        return lines
    for index, item in enumerate(statuses):
        marker = ">" if index == selected else " "
        kind = str(item.get("kind", "source")).upper()[:7]
        status = str(item.get("status", "?"))[:8]
        name = str(item.get("name", ""))
        target = str(item.get("target", ""))
        left_text = f"{marker} {kind:<7} {status:<8} {name}"
        if index == selected:
            detail = f"{item.get('kind', 'source')} '{name}' -> {target}"
        else:
            detail = ""
        lines.append(_line(_clip(left_text, left) + "   " + _clip(detail, right), width))
    return lines


def _queue_body(snapshot: dict[str, Any], width: int, selected: int) -> list[str]:
    queue = snapshot.get("queue") or {}
    counts = queue.get("counts") or {}
    lines = [
        _line("QUEUE  " + "  ".join(f"{key}={counts.get(key, 0)}"
                                   for key in ("pending", "posted", "failed", "in_flight")), width),
        _line(f"path: {queue.get('path', '(default)')}", width),
    ]
    if queue.get("error"):
        lines.append(_line(f"ERROR: {queue['error']}", width))
    holds = queue.get("holds") or []
    if holds:
        lines.append(_line("HOLDS: " + ", ".join(map(str, holds)), width))
    pending = list(queue.get("pending") or [])
    if not pending:
        lines.append(_line("Queue is empty or has no pending clips.", width))
        return lines
    lines.append(_line("PENDING", width))
    for index, item in enumerate(pending):
        marker = ">" if index == selected else " "
        title = f"  {item.get('title')}" if item.get("title") else ""
        lines.append(_line(f"{marker} {item.get('name', '')}  attempts={item.get('attempts', 0)}{title}", width))
    return lines


def _resources_body(snapshot: dict[str, Any], width: int) -> list[str]:
    resources = snapshot.get("resources") or {}
    cpu = resources.get("cpu") or {}
    memory = resources.get("memory") or {}
    disk = resources.get("disk") or {}
    load = resources.get("load") or []
    load_text = ", ".join(str(value) for value in load) or "unknown"
    output = resources.get("output") or {}
    lines = [
        _line("RESOURCES  bounded local metrics (no process control)", width),
        _line(_gauge("CPU", cpu.get("percent", 0)), width),
        _line(f"CORES   {cpu.get('cores', '?')}", width),
        _line(f"LOAD    {load_text}", width),
        _line(_gauge("MEM", memory.get("percent", 0)), width),
        _line(_gauge("DISK", disk.get("percent", 0)), width),
        _line(f"MEMORY  {_human_bytes(memory.get('available_bytes'))} available / "
              f"{_human_bytes(memory.get('total_bytes'))} total", width),
        _line(f"DISK    {_human_bytes(disk.get('free_bytes'))} free / "
              f"{_human_bytes(disk.get('total_bytes'))} total", width),
        _line(f"OUTPUT  {output.get('files', 0)} files, { _human_bytes(output.get('bytes')) }"
              + (" (scan bounded)" if output.get("truncated") else ""), width),
        _line(f"ROOT    {resources.get('root', '')}", width),
    ]
    return lines


def _logs_body(snapshot: dict[str, Any], width: int) -> list[str]:
    logs = snapshot.get("logs") or {}
    lines = [_line(f"LOGS  {logs.get('path', '(logbook)')}", width)]
    if logs.get("error"):
        lines.append(_line(f"ERROR: {logs['error']}", width))
    entries = list(logs.get("lines") or [])
    if not entries:
        lines.append(_line("Logbook is empty.", width))
    else:
        lines.extend(_line(entry, width) for entry in entries)
    return lines


def render_frame(snapshot: dict[str, Any], width: int = 100, height: int = 30,
                 active_view: str = "sources", selected: int = 0) -> list[str]:
    """Render a complete frame as strings, without importing or requiring curses."""

    width = max(24, int(width))
    height = max(6, int(height))
    if active_view not in VIEWS:
        active_view = VIEWS[0]
    lines = _header(width, active_view)
    if active_view == "sources":
        lines.extend(_sources_body(snapshot, width, selected))
    elif active_view == "queue":
        lines.extend(_queue_body(snapshot, width, selected))
    elif active_view == "resources":
        lines.extend(_resources_body(snapshot, width))
    else:
        lines.extend(_logs_body(snapshot, width))
    lines.extend([
        _line("-" * width, width),
        _line(str(snapshot.get("message") or "Ziv ready"), width),
        _line("1-4 view  Tab/h/l switch  j/k move  a link  c channel  R run  q quit", width),
    ])
    if len(lines) < height:
        lines.extend([" " * width] * (height - len(lines)))
    return lines[:height]


class TuiModel:
    """Terminal-independent state machine for the dashboard."""

    def __init__(self, catalog: SourceCatalog, *, initial_view: str = "sources"):
        self.catalog = catalog
        self.active_view = initial_view if initial_view in VIEWS else VIEWS[0]
        self.selected = 0
        self.snapshot: dict[str, Any] = {}
        self.message = "Ready. a add link  c add channel  R run  d delete  i import"
        self.pending_action: str | None = None
        self.job: subprocess.Popen | None = None
        self.job_name = ""
        self.refresh()

    def refresh(self) -> dict[str, Any]:
        self.poll_job()
        self.snapshot = self.catalog.snapshot()
        self.snapshot["message"] = self.message
        self.selected = min(self.selected, max(0, self._item_count() - 1))
        return self.snapshot

    def selected_source(self) -> dict[str, Any] | None:
        if self.active_view != "sources":
            return None
        records = list(self.snapshot.get("statuses") or [])
        return records[self.selected] if 0 <= self.selected < len(records) else None

    def poll_job(self) -> None:
        if self.job is None:
            return
        code = self.job.poll()
        if code is None:
            self.message = f"Running {self.job_name}; checkpoints remain safe"
            return
        self.message = (f"Finished {self.job_name} successfully"
                        if code == 0 else
                        f"{self.job_name} exited with code {code}; inspect logs")
        if code == 0:
            try:
                kind, name = self.job_name.split(":", 1)
                self.catalog.set_status(kind, name, "done")
            except Exception:
                pass
        self.job = None
        self.job_name = ""

    def launch_selected(self) -> bool:
        record = self.selected_source()
        if record is None:
            self.message = "Select a source before running it"
            return False
        if self.job is not None:
            self.message = "A workflow is already running"
            return False
        state_dir = self.catalog.path.parent
        state_dir.mkdir(parents=True, exist_ok=True)
        log_path = state_dir / "tui-job.log"
        log_handle = log_path.open("a", encoding="utf-8")
        command = [sys.executable, "-m", "ziv", "run-source",
                   record["kind"], record["name"]]
        try:
            self.job = subprocess.Popen(
                command, cwd=str(Path.cwd()), stdout=log_handle,
                stderr=subprocess.STDOUT, start_new_session=True)
        except OSError as exc:
            log_handle.close()
            self.message = f"Could not start workflow: {exc}"
            return False
        log_handle.close()
        self.job_name = f"{record['kind']}:{record['name']}"
        self.message = f"Started {self.job_name}; output is in {log_path}"
        return True

    def stop_job(self) -> None:
        if self.job is None or self.job.poll() is not None:
            self.message = "No running workflow"
            return
        self.job.terminate()
        self.message = f"Asked {self.job_name} to stop safely; checkpoints remain"

    def _item_count(self) -> int:
        if self.active_view == "sources":
            return len(self.snapshot.get("statuses") or [])
        if self.active_view == "queue":
            return len((self.snapshot.get("queue") or {}).get("pending") or [])
        if self.active_view == "logs":
            return len((self.snapshot.get("logs") or {}).get("lines") or [])
        return 0

    def _set_view(self, view: str) -> None:
        if view in VIEWS:
            self.active_view = view
            self.selected = 0

    def handle_key(self, key: Any) -> bool:
        """Apply one normalized key; return ``False`` only for a quit request."""

        if isinstance(key, int):
            key = {9: "TAB", 258: "KEY_DOWN", 259: "KEY_UP",
                   260: "KEY_LEFT", 261: "KEY_RIGHT"}.get(key, key)
            if isinstance(key, int) and 0 <= key < 256:
                key = chr(key)
        if key in {"q", "Q", "ESC", 27}:
            return False
        if key == "R":
            self.launch_selected()
        elif key == "r":
            self.refresh()
        elif key in {"a", "A"}:
            self.pending_action = "add_link"
        elif key in {"c", "C"}:
            self.pending_action = "add_channel"
        elif key in {"d", "D"}:
            self.pending_action = "delete"
        elif key in {"i", "I"}:
            self.pending_action = "import"
        elif key in {"x", "X"}:
            self.stop_job()
        elif key in {"TAB", "KEY_RIGHT", "l", "L"}:
            self._set_view(VIEWS[(VIEWS.index(self.active_view) + 1) % len(VIEWS)])
        elif key in {"KEY_LEFT", "h", "H"}:
            self._set_view(VIEWS[(VIEWS.index(self.active_view) - 1) % len(VIEWS)])
        elif key in {"KEY_UP", "k", "K"}:
            self.selected = max(0, self.selected - 1)
        elif key in {"KEY_DOWN", "j", "J"}:
            self.selected = min(max(0, self._item_count() - 1), self.selected + 1)
        elif isinstance(key, str) and key in {"1", "2", "3", "4"}:
            self._set_view(VIEWS[int(key) - 1])
        return True

    def render(self, width: int = 100, height: int = 30) -> list[str]:
        return render_frame(self.snapshot, width, height, self.active_view, self.selected)


def _normalize_curses_key(key: int, curses_module: Any) -> Any:
    names = {
        getattr(curses_module, "KEY_UP", -100): "KEY_UP",
        getattr(curses_module, "KEY_DOWN", -101): "KEY_DOWN",
        getattr(curses_module, "KEY_LEFT", -102): "KEY_LEFT",
        getattr(curses_module, "KEY_RIGHT", -103): "KEY_RIGHT",
    }
    return names.get(key, key if key >= 0 else "ESC")


def draw_frame(screen: Any, model: TuiModel) -> None:
    """Draw one model frame on a curses-compatible or fake screen."""

    height, width = screen.getmaxyx()
    frame = model.render(width=max(24, width), height=max(6, height))
    screen.erase()
    for row, text in enumerate(frame[:height]):
        try:
            screen.addnstr(row, 0, text, max(1, width - 1))
        except AttributeError:
            screen.addstr(row, 0, text[:max(1, width - 1)])
    screen.refresh()


def _prompt(screen: Any, prompt: str) -> str:
    """Read one short value without assuming curses is available in tests."""

    height, _ = screen.getmaxyx()
    try:
        import curses
        curses.echo()
        screen.addstr(max(0, height - 2), 0, prompt)
        screen.refresh()
        value = screen.getstr(max(0, height - 2), len(prompt), 255)
    except Exception:
        value = b""
    finally:
        try:
            curses.noecho()
        except Exception:
            pass
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").strip()
    return str(value).strip()


def _perform_action(screen: Any, model: TuiModel) -> None:
    action, model.pending_action = model.pending_action, None
    if action == "import":
        try:
            report = model.catalog.import_files()
            model.message = (f"Imported {report['added']} source(s); "
                             f"{report['skipped']} unsafe line(s) skipped")
        except Exception as exc:
            model.message = f"Import failed: {exc}"
        model.refresh()
        return
    if action == "delete":
        record = model.selected_source()
        if record is None:
            model.message = "Select a source before deleting it"
        else:
            try:
                model.catalog.delete(record["kind"], record["name"])
                model.message = f"Deleted {record['kind']}:{record['name']} from the Ziv catalog"
            except Exception as exc:
                model.message = f"Delete failed: {exc}"
        model.refresh()
        return
    if action not in {"add_link", "add_channel"}:
        return
    label = "link" if action == "add_link" else "channel"
    name = _prompt(screen, f"Name for {label}: ")
    target = _prompt(screen, f"URL or local path for {name}: ")
    if not name or not target:
        model.message = f"Cancelled {label} addition"
        return
    try:
        record = (model.catalog.add_link(name, target) if label == "link"
                  else model.catalog.add_channel(name, target))
        model.catalog.materialize(label, name)
        model.message = f"Added {record['kind']}:{record['name']}"
    except Exception as exc:
        model.message = f"Could not add {label}: {exc}"
    model.refresh()


def run(screen: Any, catalog: SourceCatalog | None = None) -> int:
    """Run one curses session; injectable ``screen`` keeps it offline-testable."""

    import curses

    model = TuiModel(catalog or SourceCatalog())
    if hasattr(screen, "keypad"):
        screen.keypad(True)
    if hasattr(screen, "timeout"):
        screen.timeout(1000)
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    while True:
        draw_frame(screen, model)
        key = screen.getch()
        if key == -1:
            model.refresh()
            continue
        if not model.handle_key(_normalize_curses_key(key, curses)):
            return 0
        if model.pending_action:
            _perform_action(screen, model)


def run_tui(catalog: SourceCatalog | None = None,
            *, wrapper: Callable[[Callable[[Any], int]], Any] | None = None) -> int:
    """Start curses, with an injectable wrapper for tests and later CLI wiring."""

    import curses

    runner = wrapper or curses.wrapper
    return int(runner(lambda screen: run(screen, catalog)))


__all__ = ["TuiModel", "VIEWS", "draw_frame", "render_frame", "run", "run_tui"]
