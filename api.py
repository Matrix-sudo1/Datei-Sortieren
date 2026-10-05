#!/usr/bin/env python3
"""Stable JSON adapter for Datei-Sortierer v8.8.

The Bash script remains the single source of truth for sorting behaviour.
This module exposes structured JSON for GUI and automation clients.
"""
from __future__ import annotations

import argparse
import re
import json
import os
import subprocess
import sys
from pathlib import Path
import signal
import time

API_VERSION = "1"
ROOT = Path(__file__).resolve().parent
ENGINE = ROOT / "datei_sortieren.sh"

MAX_CONFIG_SIZE = 1024 * 1024
CATEGORY_RE = re.compile(r"^[A-Za-z0-9_-]+$")
EXT_RE = re.compile(r"^[A-Za-z0-9]+$")


def read_config(path: str) -> tuple[list[dict], list[str]]:
    file_path = Path(path).expanduser()
    if not file_path.is_file():
        raise ValueError(f"config not found: {file_path}")
    if file_path.stat().st_size > MAX_CONFIG_SIZE:
        raise ValueError("config file is too large")
    categories = []
    errors = []
    text = file_path.read_text(encoding="utf-8")
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            errors.append(f"line {number}: missing '='")
            continue
        name, extensions = line.split("=", 1)
        name = name.strip()
        exts = extensions.split()
        if not CATEGORY_RE.fullmatch(name) or name in {".", ".."}:
            errors.append(f"line {number}: invalid category '{name}'")
            continue
        if not exts or any(not EXT_RE.fullmatch(ext) for ext in exts):
            errors.append(f"line {number}: invalid extensions for '{name}'")
            continue
        categories.append({"category": name, "extensions": exts})
    if not categories and not errors:
        errors.append("config contains no categories")
    return categories, errors


def save_config(path: str, content: str) -> tuple[list[dict], list[str]]:
    if len(content.encode("utf-8")) > MAX_CONFIG_SIZE:
        raise ValueError("config content is too large")
    target = Path(path).expanduser()
    if target.is_symlink():
        raise ValueError(f"refusing to replace symlink: {target}")
    parent = target.parent
    if not parent.is_dir():
        raise ValueError(f"config directory not found: {parent}")

    import tempfile
    fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        categories, errors = read_config(str(tmp))
        if errors:
            return categories, errors
        os.replace(tmp, target)
        try:
            dir_fd = os.open(parent, os.O_DIRECTORY)
        except (AttributeError, OSError):
            dir_fd = None
        if dir_fd is not None:
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        return categories, []
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


class JsonArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that keeps API failures machine-readable."""

    def error(self, message: str) -> None:
        raise ValueError(message)


def json_response(success: bool, exit_code: int, events: list[dict]) -> int:
    print(json.dumps({
        "api_version": API_VERSION,
        "success": success,
        "exit_code": exit_code,
        "events": events,
    }, ensure_ascii=False))
    return 0 if success else 1


def parse_events(stdout: str) -> list[dict]:
    events = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "event" in value:
            events.append(value)
    return events


def run_engine(args: list[str]) -> int:
    if not ENGINE.is_file():
        return json_response(
            False,
            127,
            [{"event": "error", "status": "error",
              "message": f"Engine not found: {ENGINE}"}],
        )

    try:
        proc = subprocess.run(
            ["bash", str(ENGINE), *args, "--json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        return json_response(
            False,
            126,
            [{"event": "error", "status": "error", "message": str(exc)}],
        )

    events = parse_events(proc.stdout)
    if not events and proc.returncode != 0:
        events = [{
            "event": "error",
            "status": "error",
            "message": proc.stdout.strip() or "Sortier-Engine fehlgeschlagen.",
        }]

    return json_response(proc.returncode == 0, proc.returncode, events)


AUTOMATION_DIR_NAME = ".datei-sortierer"
AUTOMATION_STATE = "automation.json"


def automation_paths(folder: str) -> tuple[Path, Path]:
    root = Path(folder).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"folder not found: {root}")
    state_dir = root / AUTOMATION_DIR_NAME
    return state_dir, state_dir / AUTOMATION_STATE


def write_state(path: Path, state: dict) -> None:
    path.parent.mkdir(mode=0o700, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def read_state(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def automation_status(folder: str) -> dict:
    _, state_path = automation_paths(folder)
    state = read_state(state_path)
    if not state:
        return {"status": "stopped", "message": "no automation state"}

    pid = int(state.get("pid", 0) or 0)
    if not pid_alive(pid):
        try:
            state_path.unlink()
        except FileNotFoundError:
            pass
        return {"status": "stopped", "message": "automation process is not running"}

    return {
        "status": state.get("status", "running"),
        "pid": pid,
        "folder": state.get("folder"),
        "options": state.get("options", {}),
        "started_at": state.get("started_at"),
    }


def automation_start(folder: str, options: dict) -> tuple[bool, dict]:
    _, state_path = automation_paths(folder)
    current = automation_status(folder)
    if current.get("status") in {"running", "paused"}:
        return False, current

    root = str(Path(folder).expanduser().resolve())
    args = [str(ENGINE), root, "--watch"]
    if options.get("recursive"):
        args.append("--unterordner")
    if options.get("date"):
        args.append("--nach-datum")
    if options.get("copy"):
        args.append("--kopieren")
    if options.get("notify"):
        args.append("--notify")
    for key, flag in (("profile", "--profil"), ("config", "--config"), ("ignore", "--ignore")):
        if options.get(key):
            args.extend([flag, str(options[key])])

    log_path = Path(root) / AUTOMATION_DIR_NAME / "automation.log"
    log_path.parent.mkdir(mode=0o700, exist_ok=True)
    log_handle = open(log_path, "a", encoding="utf-8")
    try:
        proc = subprocess.Popen(
            ["bash", *args],
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
        )
    except OSError as exc:
        log_handle.close()
        return False, {"status": "error", "message": str(exc)}
    finally:
        log_handle.close()

    state = {
        "status": "running",
        "pid": proc.pid,
        "folder": root,
        "options": options,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    write_state(state_path, state)
    return True, state


def automation_signal(folder: str, action: str) -> tuple[bool, dict]:
    _, state_path = automation_paths(folder)
    state = read_state(state_path)
    if not state:
        return False, {"status": "stopped", "message": "no automation state"}
    pid = int(state.get("pid", 0) or 0)
    if not pid_alive(pid):
        try:
            state_path.unlink()
        except FileNotFoundError:
            pass
        return False, {"status": "stopped", "message": "automation process is not running"}

    signals = {"stop": signal.SIGTERM, "pause": signal.SIGSTOP, "resume": signal.SIGCONT}
    os.kill(pid, signals[action])
    if action == "stop":
        try:
            state_path.unlink()
        except FileNotFoundError:
            pass
        return True, {"status": "stopped", "pid": pid}
    state["status"] = "paused" if action == "pause" else "running"
    write_state(state_path, state)
    return True, state


def automation_profiles() -> list[dict]:
    profile_dir = ROOT / "profile"
    result = []
    if not profile_dir.is_dir():
        return result
    for path in sorted(profile_dir.glob("*.txt")):
        try:
            categories, errors = read_config(str(path))
        except (OSError, ValueError):
            continue
        result.append({
            "profile": path.stem,
            "categories": len(categories),
            "valid": not errors,
        })
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(description="JSON API for Datei-Sortierer v8.8")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("folder")
        p.add_argument("--recursive", action="store_true")
        p.add_argument("--date", action="store_true")
        p.add_argument("--copy", action="store_true")
        p.add_argument("--profile")
        p.add_argument("--config")
        p.add_argument("--ignore")
        p.add_argument("--notify", action="store_true")

    preview = sub.add_parser("preview", help="preview without changing files")
    common(preview)

    sort = sub.add_parser("sort", help="sort files")
    common(sort)
    sort.add_argument("--report", action="store_true")

    undo = sub.add_parser("undo", help="undo the last sort")
    undo.add_argument("folder")

    log = sub.add_parser("log", help="read the last journal")
    log.add_argument("folder")

    config = sub.add_parser("config", help="read and validate a config file")
    config.add_argument("file")

    config_save = sub.add_parser("config-save", help="validate and atomically save a config file")
    config_save.add_argument("file")
    config_save.add_argument("--content", required=True)

    automation = sub.add_parser("automation-start", help="start managed watch automation")
    automation.add_argument("folder")
    automation.add_argument("--recursive", action="store_true")
    automation.add_argument("--date", action="store_true")
    automation.add_argument("--copy", action="store_true")
    automation.add_argument("--profile")
    automation.add_argument("--config")
    automation.add_argument("--ignore")
    automation.add_argument("--notify", action="store_true")

    for command in ("automation-status", "automation-stop", "automation-pause", "automation-resume"):
        action = sub.add_parser(command)
        action.add_argument("folder")

    sub.add_parser("profiles", help="list available profiles")
    return parser


def main() -> int:
    parser = build_parser()
    try:
        ns = parser.parse_args()
    except ValueError as exc:
        return json_response(
            False,
            2,
            [{"event": "error", "status": "error", "message": str(exc)}],
        )

    if ns.command in {"preview", "sort"}:
        if not os.path.isdir(ns.folder):
            return json_response(
                False,
                2,
                [{"event": "error", "status": "error",
                  "message": f"folder not found: {ns.folder}"}],
            )
        args = [ns.folder]
        if ns.command == "preview":
            args.append("--dry-run")
        if ns.recursive:
            args.append("--unterordner")
        if ns.date:
            args.append("--nach-datum")
        if ns.copy:
            args.append("--kopieren")
        if ns.profile:
            args.extend(["--profil", ns.profile])
        if ns.config:
            args.extend(["--config", ns.config])
        if ns.ignore:
            args.extend(["--ignore", ns.ignore])
        if ns.notify:
            args.append("--notify")
        if ns.command == "sort" and ns.report:
            args.append("--bericht")
        return run_engine(args)

    if ns.command == "profiles":
        events = [{"event": "profile", "status": "ok", **item} for item in automation_profiles()]
        return json_response(True, 0, events)

    if ns.command.startswith("automation-"):
        try:
            if ns.command == "automation-start":
                options = {
                    "recursive": ns.recursive,
                    "date": ns.date,
                    "copy": ns.copy,
                    "notify": ns.notify,
                    "profile": ns.profile,
                    "config": ns.config,
                    "ignore": ns.ignore,
                }
                ok, value = automation_start(ns.folder, options)
            elif ns.command == "automation-status":
                value = automation_status(ns.folder)
                ok = value.get("status") != "error"
            else:
                action = ns.command.removeprefix("automation-")
                ok, value = automation_signal(ns.folder, action)
        except (OSError, ValueError, KeyError) as exc:
            ok, value = False, {"status": "error", "message": str(exc)}
        event = {"event": "automation", **value}
        return json_response(ok, 0 if ok else 2, [event])

    if ns.command == "config":
        try:
            categories, errors = read_config(ns.file)
        except (OSError, ValueError) as exc:
            return json_response(False, 2, [{"event": "error", "status": "error", "message": str(exc)}])
        if errors:
            return json_response(False, 2, [{"event": "config", "status": "error", "message": error} for error in errors])
        events = [{"event": "config", "status": "ok", "category": item["category"], "message": " ".join(item["extensions"])} for item in categories]
        return json_response(True, 0, events)

    if ns.command == "config-save":
        try:
            categories, errors = save_config(ns.file, ns.content)
        except (OSError, ValueError) as exc:
            return json_response(False, 2, [{"event": "error", "status": "error", "message": str(exc)}])
        if errors:
            return json_response(False, 2, [{"event": "config", "status": "error", "message": error} for error in errors])
        return json_response(True, 0, [{"event": "config", "status": "saved", "message": f"{len(categories)} categories saved"}])

    if ns.command in {"undo", "log"}:
        if not os.path.isdir(ns.folder):
            return json_response(
                False,
                2,
                [{"event": "error", "status": "error",
                  "message": f"folder not found: {ns.folder}"}],
            )
        return run_engine([ns.folder, "--" + ns.command])

    return json_response(
        False,
        2,
        [{"event": "error", "status": "error", "message": "unsupported command"}],
    )


if __name__ == "__main__":
    sys.exit(main())
