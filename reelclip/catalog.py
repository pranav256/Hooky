"""Durable, local source catalog for the terminal UI.

The catalog is deliberately separate from the existing command-line workflow.
It reads the project's line-oriented ``links.txt`` and ``channels.txt`` files,
but it does not rewrite them and it never performs network requests. Named
entries added through :class:`SourceCatalog` are stored in a small JSON file
under ``.reelclip-state`` (or ``STATE_DIR``) so a later CLI can opt into the
catalog without changing today's entry points.

Only source metadata is stored here: names, URLs/paths, safe source options,
and status. Credentials, environment variables, cookies, and session files
are intentionally outside the catalog API.
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit

from .config import PROJECT_ROOT


CATALOG_VERSION = 1
DEFAULT_CATALOG_NAME = "catalog.json"
STATE_DIR_NAME = ".ziv-state"
LEGACY_STATE_DIR_NAME = ".reelclip-state"
_KINDS = ("link", "channel")
_STATUSES = {"active", "done", "missing", "disabled"}
_SENSITIVE_OPTION_KEYS = {
    "api_key", "apikey", "cookie", "password", "passwd", "secret", "session",
    "token", "access_token", "refresh_token",
}
_SENSITIVE_FILE_NAMES = {
    ".env", ".ig_session", "cookies.txt", "catalog.json", "queue.json",
}
_REDACT_ASSIGNMENT = re.compile(
    r"(?i)(\b(?:api[_-]?key|password|passwd|secret|access[_-]?token|"
    r"refresh[_-]?token)\b\s*[:=]\s*)([^\s,;]+)"
)
_REDACT_URL_AUTH = re.compile(r"(https?://)([^/@\s]+):([^/@\s]+)@", re.I)


class CatalogError(RuntimeError):
    """The catalog is invalid or cannot be safely updated."""


def default_catalog_path() -> Path:
    """Return the default state path without reading credentials or ``.env``."""

    state_dir = Path(os.environ.get("STATE_DIR") or PROJECT_ROOT / STATE_DIR_NAME)
    return state_dir / DEFAULT_CATALOG_NAME


def _default_source_path(environment_key: str, filename: str) -> Path:
    return Path(os.environ.get(environment_key) or filename)


def _empty_state() -> dict[str, Any]:
    return {"version": CATALOG_VERSION, "links": [], "channels": []}


def _now() -> float:
    return round(time.time(), 3)


def _safe_name(name: str) -> str:
    value = str(name or "").strip()
    if not value or len(value) > 64 or any(ord(char) < 32 for char in value):
        raise CatalogError("names must be 1-64 characters without control characters")
    return value


def _safe_target(target: str) -> str:
    value = str(target or "").strip()
    if not value or any(ord(char) < 32 for char in value):
        raise CatalogError("source URLs and paths must be non-empty and plain text")
    try:
        parsed = urlsplit(value)
    except ValueError as exc:
        raise CatalogError("source URL is malformed") from exc
    if parsed.username or parsed.password:
        raise CatalogError("embedded URL credentials are not stored in the catalog")
    return value


def _safe_options(options: Mapping[str, Any] | None) -> dict[str, str]:
    if not options:
        return {}
    clean: dict[str, str] = {}
    for raw_key, raw_value in options.items():
        key = str(raw_key).strip().lower()
        if not key or key in _SENSITIVE_OPTION_KEYS:
            continue
        value = str(raw_value).strip()
        if value and not any(ord(char) < 32 for char in value):
            clean[key] = value
    return clean


def _parse_options(parts: Iterable[str]) -> dict[str, str]:
    options: dict[str, str] = {}
    for part in parts:
        for token in part.split():
            key, separator, value = token.partition("=")
            key = key.strip().lower()
            if not separator or not key or key in _SENSITIVE_OPTION_KEYS:
                continue
            value = value.strip()
            if value and not any(ord(char) < 32 for char in value):
                options[key] = value
    return options


def _done_target(line: str) -> tuple[str, bool]:
    """Extract a target and its DONE marker from either supported syntax."""

    stripped = line.strip()
    upper = stripped.upper()
    if upper.startswith("DONE "):
        return stripped[5:].strip(), True
    if upper.startswith("# DONE "):
        return stripped[7:].strip(), True
    marker = re.search(r"\s+#\s*DONE(?:\s|$)", stripped, re.I)
    if marker:
        return stripped[:marker.start()].strip(), True
    return stripped, False


def _parse_source_file(path: Path, kind: str) -> tuple[list[dict[str, Any]], int]:
    if kind not in _KINDS:
        raise CatalogError(f"unknown source kind: {kind}")
    if not path.exists():
        return [], 0
    entries: list[dict[str, Any]] = []
    skipped = 0
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#") and not line.upper().startswith("# DONE "):
            continue
        target_with_options, done = _done_target(line)
        pieces = [part.strip() for part in target_with_options.split("|")]
        target = pieces[0].strip()
        if not target:
            continue
        try:
            target = _safe_target(target)
        except CatalogError:
            # Do not copy a credential-bearing source into durable state.
            skipped += 1
            continue
        entries.append({
            "target": target,
            "options": _parse_options(pieces[1:]),
            "status": "done" if done else "active",
            "line_no": line_no,
        })
    return entries, skipped


def _copy_record(record: Mapping[str, Any], *, kind: str | None = None) -> dict[str, Any]:
    result = {
        "name": str(record.get("name", "")),
        "target": str(record.get("target", "")),
        "options": dict(record.get("options") or {}),
        "status": str(record.get("status", "active")),
        "origin": str(record.get("origin", "named")),
        "source_file": str(record.get("source_file", "")),
        "line_no": record.get("line_no"),
        "created_at": record.get("created_at", 0.0),
        "updated_at": record.get("updated_at", 0.0),
    }
    if kind:
        result["kind"] = kind
    return result


def _validate_record(raw: Any, kind: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise CatalogError(f"invalid {kind} record")
    name = _safe_name(raw.get("name", ""))
    target = _safe_target(raw.get("target", ""))
    status = str(raw.get("status", "active"))
    if status not in _STATUSES:
        raise CatalogError(f"invalid status for {kind} '{name}': {status}")
    origin = str(raw.get("origin", "named"))
    if origin not in {"named", "imported"}:
        raise CatalogError(f"invalid origin for {kind} '{name}'")
    line_no = raw.get("line_no")
    if line_no is not None and (isinstance(line_no, bool) or not isinstance(line_no, int)
                                or line_no < 1):
        raise CatalogError(f"invalid source line for {kind} '{name}'")
    return {
        "name": name,
        "target": target,
        "options": _safe_options(raw.get("options")),
        "status": status,
        "origin": origin,
        "source_file": str(raw.get("source_file", "")),
        "line_no": line_no,
        "created_at": float(raw.get("created_at", 0.0) or 0.0),
        "updated_at": float(raw.get("updated_at", 0.0) or 0.0),
    }


def _validate_state(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("version") != CATALOG_VERSION:
        raise CatalogError("unsupported or missing catalog version")
    state = _empty_state()
    for kind in _KINDS:
        records = raw.get(f"{kind}s", [])
        if not isinstance(records, list):
            raise CatalogError(f"invalid {kind} catalog")
        state[f"{kind}s"] = [_validate_record(item, kind) for item in records]
        names: set[str] = set()
        for record in state[f"{kind}s"]:
            if record["name"] in names:
                raise CatalogError(f"duplicate {kind} name: {record['name']}")
            names.add(record["name"])
    return state


@contextmanager
def _catalog_lock(path: Path):
    """Use a short advisory lock around catalog reads and atomic writes."""

    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as handle:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            except OSError:
                pass
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == "nt":
                import msvcrt
                handle.seek(0)
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return _empty_state()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        raise CatalogError(f"cannot read catalog {path}: {exc}") from exc
    return _validate_state(raw)


def _atomic_write(path: Path, state: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp",
                                           dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, ensure_ascii=False, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _redact(text: str) -> str:
    text = _REDACT_URL_AUTH.sub(r"\1[redacted]@", text)
    return _REDACT_ASSIGNMENT.sub(r"\1[redacted]", text)


class SourceCatalog:
    """Read and mutate a durable catalog without invoking any workflow.

    ``import_files`` is intentionally explicit. Constructing a catalog only
    reads its JSON state; it never scans the network or mutates source files.
    ``add_link`` and ``add_channel`` update the catalog JSON only. This keeps
    the object safe to embed in a future CLI command and easy to test offline.
    """

    def __init__(self, path: Path | str | None = None, *,
                 links_path: Path | str | None = None,
                 channels_path: Path | str | None = None):
        self.path = Path(path) if path is not None else default_catalog_path()
        self._legacy_path = PROJECT_ROOT / LEGACY_STATE_DIR_NAME / DEFAULT_CATALOG_NAME
        self.links_path = (Path(links_path) if links_path is not None
                           else _default_source_path("LINKS_FILE", "links.txt"))
        self.channels_path = (Path(channels_path) if channels_path is not None
                              else _default_source_path("CHANNELS_FILE", "channels.txt"))
        self._cpu_sample: tuple[int, int] | None = None
        if path is None and not self.path.exists() and self._legacy_path.exists():
            # Read legacy state once, then write all future mutations to the
            # Ziv location. The old state is never deleted or modified.
            self._state = _read_state(self._legacy_path)
        else:
            self._state = _read_state(self.path)

    def _reload(self) -> dict[str, Any]:
        if not self.path.exists() and self.path == default_catalog_path() \
                and self._legacy_path.exists():
            self._state = _read_state(self._legacy_path)
        else:
            self._state = _read_state(self.path)
        return self._state

    def _save(self) -> None:
        _atomic_write(self.path, self._state)

    def _mutate(self, callback):
        with _catalog_lock(self.path):
            self._reload()
            result = callback(self._state)
            self._save()
            return result

    @staticmethod
    def _records(state: dict[str, Any], kind: str) -> list[dict[str, Any]]:
        if kind not in _KINDS:
            raise CatalogError(f"unknown source kind: {kind}")
        return state[f"{kind}s"]

    def import_files(self, links_path: Path | str | None = None,
                     channels_path: Path | str | None = None) -> dict[str, int]:
        """Import the current source files and return an offline change report.

        Existing imported records that disappeared from a source file become
        ``missing`` instead of being deleted. A matching named record keeps its
        name, making it safe to import before or after a future CLI names it.
        DONE markers are represented as ``done`` and all other source lines as
        ``active``. No file is written by this method.
        """

        paths = {
            "link": Path(links_path) if links_path is not None else self.links_path,
            "channel": (Path(channels_path) if channels_path is not None
                         else self.channels_path),
        }
        parsed: dict[str, list[dict[str, Any]]] = {}
        skipped = 0
        for kind, source_path in paths.items():
            parsed[kind], count = _parse_source_file(source_path, kind)
            skipped += count

        report = {"added": 0, "updated": 0, "missing": 0, "skipped": skipped,
                  "links": len(parsed["link"]), "channels": len(parsed["channel"])}

        def apply(state: dict[str, Any]):
            for kind, source_path in paths.items():
                records = self._records(state, kind)
                source_key = str(source_path)
                fresh_targets = {entry["target"] for entry in parsed[kind]}
                for record in records:
                    if (record["origin"] == "imported"
                            and record["source_file"] == source_key
                            and record["target"] not in fresh_targets
                            and record["status"] != "missing"):
                        record["status"] = "missing"
                        record["updated_at"] = _now()
                        report["missing"] += 1

                for entry in parsed[kind]:
                    match = next((record for record in records
                                  if record["target"] == entry["target"]), None)
                    if match is None:
                        used = {record["name"] for record in records}
                        number = 1
                        while f"{kind}-{number:03d}" in used:
                            number += 1
                        now = _now()
                        records.append({
                            "name": f"{kind}-{number:03d}",
                            "target": entry["target"],
                            "options": entry["options"],
                            "status": entry["status"],
                            "origin": "imported",
                            "source_file": source_key,
                            "line_no": entry["line_no"],
                            "created_at": now,
                            "updated_at": now,
                        })
                        report["added"] += 1
                        continue
                    match.update({
                        "options": entry["options"],
                        "status": entry["status"],
                        "source_file": source_key,
                        "line_no": entry["line_no"],
                        "updated_at": _now(),
                    })
                    report["updated"] += 1

        self._mutate(apply)
        return report

    # A descriptive alias makes later CLI integration less coupled to the
    # current file names.
    import_sources = import_files

    def _add(self, kind: str, name: str, target: str,
             options: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if kind not in _KINDS:
            raise CatalogError(f"unknown source kind: {kind}")
        clean_name = _safe_name(name)
        clean_target = _safe_target(target)
        clean_options = _safe_options(options)

        def apply(state: dict[str, Any]):
            records = self._records(state, kind)
            same_name = next((record for record in records
                              if record["name"] == clean_name), None)
            if same_name is not None and same_name["target"] != clean_target:
                raise CatalogError(f"{kind} name already points to another source: {clean_name}")
            duplicate = next((record for record in records
                              if record["target"] == clean_target
                              and record["name"] != clean_name), None)
            if duplicate is not None:
                raise CatalogError(f"source already named '{duplicate['name']}'")
            now = _now()
            if same_name is None:
                same_name = {
                    "name": clean_name, "target": clean_target,
                    "options": clean_options, "status": "active",
                    "origin": "named", "source_file": "", "line_no": None,
                    "created_at": now, "updated_at": now,
                }
                records.append(same_name)
            else:
                same_name.update({"options": clean_options, "status": "active",
                                  "origin": "named", "updated_at": now})
            return _copy_record(same_name, kind=kind)

        return self._mutate(apply)

    def add_link(self, name: str, target: str,
                 options: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Add or update a named local file/video link in catalog state."""

        return self._add("link", name, target, options)

    def add_channel(self, name: str, target: str,
                    options: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Add or update a named channel without discovering or authenticating."""

        return self._add("channel", name, target, options)

    def set_status(self, kind: str, name: str, status: str) -> dict[str, Any]:
        """Set a local status marker for a future workflow integration."""

        if status not in _STATUSES:
            raise CatalogError(f"invalid status: {status}")

        def apply(state: dict[str, Any]):
            record = next((item for item in self._records(state, kind)
                           if item["name"] == name), None)
            if record is None:
                raise CatalogError(f"unknown {kind}: {name}")
            record["status"] = status
            record["updated_at"] = _now()
            return _copy_record(record, kind=kind)

        return self._mutate(apply)

    def get(self, kind: str, name: str) -> dict[str, Any]:
        """Return one display-safe source record by kind and friendly name."""

        record = next((item for item in self._records(self._state, kind)
                       if item["name"] == name), None)
        if record is None:
            raise CatalogError(f"unknown {kind}: {name}")
        return _copy_record(record, kind=kind)

    def delete(self, kind: str, name: str) -> dict[str, Any]:
        """Remove a catalog record without touching the source text files."""

        def apply(state: dict[str, Any]):
            records = self._records(state, kind)
            for index, record in enumerate(records):
                if record["name"] == name:
                    return _copy_record(records.pop(index), kind=kind)
            raise CatalogError(f"unknown {kind}: {name}")

        return self._mutate(apply)

    def materialize(self, kind: str, name: str) -> Path:
        """Append a named source to the legacy workflow file if it is absent.

        The JSON catalog remains authoritative for names/statuses, while this
        small bridge lets the existing downloader and channel scanner consume
        sources added from the TUI without duplicating an existing URL.
        """

        record = self.get(kind, name)
        path = self.links_path if kind == "link" else self.channels_path \
            if kind == "channel" else None
        if path is None:
            raise CatalogError(f"unknown source kind: {kind}")
        target = record["target"]
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        if any(target == line.strip().split("|", 1)[0].strip()
               for line in existing.splitlines()):
            return path
        options = record.get("options") or {}
        suffix = " | " + " ".join(f"{key}={value}" for key, value in options.items()) \
            if options else ""
        path.parent.mkdir(parents=True, exist_ok=True)
        with _catalog_lock(path):
            current = path.read_text(encoding="utf-8") if path.exists() else ""
            if not any(target == line.strip().split("|", 1)[0].strip()
                       for line in current.splitlines()):
                with path.open("a", encoding="utf-8") as handle:
                    if current and not current.endswith(("\n", "\r")):
                        handle.write("\n")
                    handle.write(target + suffix + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
        return path

    def statuses(self, kind: str | None = None) -> list[dict[str, Any]]:
        """Return stable, display-ready status records without sensitive fields."""

        self._reload()
        kinds = _KINDS if kind is None else (kind,)
        result: list[dict[str, Any]] = []
        for item_kind in kinds:
            for record in self._records(self._state, item_kind):
                result.append(_copy_record(record, kind=item_kind))
        return result

    list_statuses = statuses

    def status_summary(self) -> dict[str, int]:
        summary = {status: 0 for status in sorted(_STATUSES)}
        for record in self.statuses():
            summary[record["status"]] += 1
        return summary

    def queue_view(self, path: Path | str | None = None, *, limit: int = 50) -> dict[str, Any]:
        """Return a read-only, credential-free summary of queue state."""

        queue_path = Path(path) if path is not None else (
            Path(os.environ.get("STATE_DIR") or PROJECT_ROOT / STATE_DIR_NAME)
            / "queue.json")
        legacy_queue = PROJECT_ROOT / LEGACY_STATE_DIR_NAME / "queue.json"
        if path is None and not queue_path.exists() and legacy_queue.exists():
            queue_path = legacy_queue
        empty = {
            "available": False, "path": str(queue_path),
            "counts": {"pending": 0, "posted": 0, "failed": 0, "in_flight": 0},
            "pending": [], "posted": [], "failed": [], "holds": [],
            "next_post_at": 0.0,
        }
        if not queue_path.exists():
            return empty
        try:
            raw = json.loads(queue_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError) as exc:
            return {**empty, "available": False, "error": f"unreadable queue: {exc}"}
        if not isinstance(raw, dict):
            return {**empty, "error": "invalid queue state"}

        result = {**empty, "available": True,
                  "counts": {}, "next_post_at": raw.get("next_ok", 0.0)}
        for bucket in ("pending", "posted", "failed", "in_flight"):
            values = raw.get(bucket, {})
            if not isinstance(values, dict):
                values = {}
            result["counts"][bucket] = len(values)
            items = []
            for key, value in list(values.items())[:max(0, limit)]:
                entry = value if isinstance(value, dict) else {}
                item = {
                    "name": Path(str(key)).name,
                    "status": bucket,
                    "attempts": entry.get("attempts", 0),
                }
                if entry.get("title"):
                    item["title"] = _redact(str(entry["title"]))[:120]
                items.append(item)
            result[bucket] = items
        failed = raw.get("failed", {})
        if isinstance(failed, dict):
            result["holds"] = [Path(str(key)).name for key, entry in failed.items()
                                if isinstance(entry, dict) and entry.get("retryable") is False]
        return result

    def resource_view(self, root: Path | str | None = None, *, max_files: int = 2000) -> dict[str, Any]:
        """Return bounded Linux-friendly process/storage metrics and output size."""

        root_path = Path(root) if root is not None else self.links_path.parent
        try:
            usage = shutil.disk_usage(root_path)
            disk_percent = round((usage.used / usage.total) * 100, 1) if usage.total else 0.0
            disk = {"total_bytes": usage.total, "used_bytes": usage.used,
                    "free_bytes": usage.free, "percent": disk_percent}
        except OSError as exc:
            disk = {"error": str(exc)}
        try:
            load = [round(value, 2) for value in os.getloadavg()]
        except (AttributeError, OSError):
            load = []

        cpu: dict[str, Any] = {"percent": 0.0, "cores": os.cpu_count() or 1}
        stat_path = Path("/proc/stat")
        if stat_path.exists():
            try:
                fields = stat_path.read_text(encoding="ascii").splitlines()[0].split()[1:]
                numbers = [int(value) for value in fields[:8]]
                total = sum(numbers)
                idle = numbers[3] + numbers[4]
                previous = self._cpu_sample
                self._cpu_sample = (total, idle)
                if previous is not None:
                    total_delta = total - previous[0]
                    idle_delta = idle - previous[1]
                    if total_delta > 0:
                        cpu["percent"] = round(
                            max(0.0, min(100.0, 100 * (total_delta - idle_delta) / total_delta)), 1)
            except (OSError, ValueError, IndexError):
                pass

        memory: dict[str, Any] = {}
        meminfo = Path("/proc/meminfo")
        if meminfo.exists():
            try:
                values = {}
                for line in meminfo.read_text(encoding="ascii").splitlines():
                    key, separator, raw_value = line.partition(":")
                    if separator:
                        values[key] = int(raw_value.strip().split()[0]) * 1024
                total = values.get("MemTotal", 0)
                available = values.get("MemAvailable", values.get("MemFree", 0))
                memory = {
                    "total_bytes": total, "available_bytes": available,
                    "percent": round(((total - available) / total) * 100, 1)
                    if total else 0.0,
                }
            except (OSError, ValueError, IndexError):
                memory = {}

        output = root_path / "output"
        file_count = 0
        output_bytes = 0
        truncated = False
        if output.exists():
            try:
                for item in output.rglob("*"):
                    if item.name in _SENSITIVE_FILE_NAMES or any(
                             part in {".git", ".venv", ".reelclip-state", ".ziv-state"}
                             for part in item.parts):
                        continue
                    if item.is_file():
                        if file_count >= max_files:
                            truncated = True
                            break
                        file_count += 1
                        try:
                            output_bytes += item.stat().st_size
                        except OSError:
                            pass
            except OSError:
                truncated = True
        return {
            "root": str(root_path), "load": load, "cpu": cpu,
            "memory": memory, "disk": disk,
            "output": {"files": file_count, "bytes": output_bytes, "truncated": truncated},
        }

    def log_view(self, path: Path | str | None = None, *, limit: int = 30) -> dict[str, Any]:
        """Return the newest log lines with obvious credential assignments redacted."""

        log_path = Path(path) if path is not None else self.links_path.parent / "output" / "logbook.txt"
        if not log_path.exists():
            return {"available": False, "path": str(log_path), "lines": []}
        try:
            lines = log_path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as exc:
            return {"available": False, "path": str(log_path), "lines": [],
                    "error": f"unreadable log: {exc}"}
        count = max(0, int(limit))
        return {"available": True, "path": str(log_path),
                "lines": [_redact(line) for line in lines[-count:]]}

    def snapshot(self, *, queue_path: Path | str | None = None,
                 resource_root: Path | str | None = None,
                 log_path: Path | str | None = None) -> dict[str, Any]:
        """Build one consistent read-only payload for a TUI frame."""

        return {
            "refreshed_at": _now(),
            "statuses": self.statuses(),
            "summary": self.status_summary(),
            "queue": self.queue_view(queue_path),
            "resources": self.resource_view(resource_root),
            "logs": self.log_view(log_path),
        }


# Short public name for callers that prefer ``Catalog`` in integration code.
Catalog = SourceCatalog


__all__ = ["Catalog", "CatalogError", "SourceCatalog", "default_catalog_path"]
