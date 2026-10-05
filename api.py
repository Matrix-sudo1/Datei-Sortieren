#!/usr/bin/env python3
"""Stable JSON adapter for Datei-Sortierer v9.0.

The Bash script remains the single source of truth for sorting behaviour.
This module exposes structured JSON for GUI and automation clients.
"""
from __future__ import annotations

import argparse
import re
import json
import hashlib
from datetime import datetime, timezone
import os
import subprocess
import sys
from pathlib import Path
import signal
import time

from intelligent import (classify_folder, load_categories, confidence_policy, load_learning_rules, add_learning_rule, remove_learning_rule, set_learning_rule_enabled, rules_path)

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
    if options.get("interval"):
        args.extend(["--watch-interval", str(options["interval"])])
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


def intelligent_report_path(folder: str) -> Path:
    root = Path(folder).expanduser().resolve()
    return root / ".datei-sortierer" / "intelligent-report.json"


def write_intelligent_report(folder: str, report: dict) -> Path:
    path = intelligent_report_path(folder)
    path.parent.mkdir(mode=0o700, exist_ok=True)
    tmp = path.with_name("." + path.name + "." + str(os.getpid()) + ".tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    return path

def intelligent_plan_hash(results: list[dict]) -> str:
    """Return a deterministic fingerprint for a freshly classified file set."""
    snapshot = []
    for item in results:
        source = Path(item["source"]).expanduser().resolve()
        if not source.is_file() or source.is_symlink():
            raise ValueError(f"invalid intelligent plan source: {source}")
        st = source.stat()
        snapshot.append({
            "source": str(source),
            "category": item.get("category", "Sonstiges"),
            "confidence": item.get("confidence", 0.0),
            "decision": item.get("decision", "leave"),
            "reason": item.get("reason", ""),
            "signature": f"{st.st_dev}:{st.st_ino}:{st.st_size}:{int(st.st_mtime)}",
        })
    encoded = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(description="JSON API for Datei-Sortierer v9.0")
    sub = parser.add_subparsers(dest="command", required=True)

    intelligent = sub.add_parser("intelligent-preview", help="deterministic intelligent classification preview")
    intelligent.add_argument("folder")
    intelligent.add_argument("--recursive", action="store_true")
    intelligent.add_argument("--profile")
    intelligent.add_argument("--config")
    intelligent_sort = sub.add_parser("intelligent-sort", help="sort confirmed high-confidence intelligent proposals")
    intelligent_sort.add_argument("folder")
    intelligent_sort.add_argument("--recursive", action="store_true")
    intelligent_sort.add_argument("--profile")
    intelligent_sort.add_argument("--config")
    intelligent_sort.add_argument("--confirm", action="store_true")
    intelligent_sort.add_argument("--include-review", action="store_true")
    intelligent_sort.add_argument("--select", action="append", default=[])
    intelligent_sort.add_argument("--plan-hash")

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
    automation.add_argument("--interval", type=int, default=10)

    for command in ("automation-status", "automation-stop", "automation-pause", "automation-resume"):
        action = sub.add_parser(command)
        action.add_argument("folder")

    rules = sub.add_parser("intelligent-rules", help="list deterministic learning rules")
    rules.add_argument("folder")
    rules.add_argument("--profile")
    rules.add_argument("--config")
    rule_add = sub.add_parser("intelligent-rule-add", help="add a deterministic learning rule")
    rule_add.add_argument("folder")
    rule_add.add_argument("--source", choices=["extension", "mime", "filename_token"], required=True)
    rule_add.add_argument("--pattern", required=True)
    rule_add.add_argument("--category", required=True)
    rule_add.add_argument("--id")
    rule_remove = sub.add_parser("intelligent-rule-remove", help="remove a deterministic learning rule")
    rule_remove.add_argument("folder")
    rule_remove.add_argument("--id", required=True)
    rule_set = sub.add_parser("intelligent-rule-set", help="enable or disable a deterministic learning rule")
    rule_set.add_argument("folder")
    rule_set.add_argument("--id", required=True)
    rule_set.add_argument("--enabled", choices=["true", "false"], required=True)

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

    if ns.command in {"intelligent-rules", "intelligent-rule-add", "intelligent-rule-remove"}:
        if not os.path.isdir(ns.folder):
            return json_response(False, 2, [{"event": "error", "status": "error", "message": f"folder not found: {ns.folder}"}])
        try:
            config_path = ns.config if getattr(ns, "config", None) else None
            profile = getattr(ns, "profile", None)
            if profile:
                if not CATEGORY_RE.fullmatch(profile):
                    raise ValueError("invalid profile name")
                config_path = str(ROOT / "profile" / f"{profile}.txt")
            categories = load_categories(config_path or str(ROOT / "config.txt"))
            if ns.command == "intelligent-rules":
                rules = load_learning_rules(ns.folder, categories)
                return json_response(True, 0, [{"event": "learning-rule", "status": "ok", **rule, "source_label": {"extension": "Dateiendung", "mime": "MIME-Typ", "filename_token": "Dateiname-Token"}.get(rule["source"], rule["source"])} for rule in rules])
            if ns.command == "intelligent-rule-add":
                rule_id = ns.id or f"{ns.source}-{ns.pattern.lower()}-{ns.category.lower()}".replace(" ", "-")
                rule, path = add_learning_rule(ns.folder, {
                    "id": rule_id,
                    "source": ns.source,
                    "pattern": ns.pattern,
                    "category": ns.category,
                    "enabled": True,
                }, categories)
                return json_response(True, 0, [{"event": "learning-rule", "status": "created", **rule, "path": str(path)}])
            if ns.command == "intelligent-rule-set":
                rule = set_learning_rule_enabled(ns.folder, ns.id, ns.enabled == "true", categories)
                return json_response(True, 0, [{"event": "learning-rule", "status": "updated", **rule, "path": str(rules_path(ns.folder))}])
            path = remove_learning_rule(ns.folder, ns.id, categories)
            return json_response(True, 0, [{"event": "learning-rule", "status": "removed", "id": ns.id, "path": str(path)}])
        except (OSError, ValueError) as exc:
            return json_response(False, 2, [{"event": "learning-rule", "status": "error", "message": str(exc)}])

    if ns.command == "intelligent-sort":
        if not os.path.isdir(ns.folder):
            return json_response(False, 2, [{"event": "error", "status": "error", "message": f"folder not found: {ns.folder}"}])
        try:
            config_path = ns.config
            if ns.profile:
                if not CATEGORY_RE.fullmatch(ns.profile):
                    raise ValueError("invalid profile name")
                config_path = str(ROOT / "profile" / f"{ns.profile}.txt")
            categories = load_categories(config_path or str(ROOT / "config.txt"))
            learning_rules = load_learning_rules(ns.folder, categories)
            results = classify_folder(ns.folder, categories, ns.recursive, learning_rules)
            plan_hash = intelligent_plan_hash(results)
            eligible = [r for r in results if r.get("decision") == "auto" or (ns.include_review and r.get("decision") == "review")]
            if ns.plan_hash and ns.plan_hash != plan_hash:
                return json_response(False, 2, [{"event": "intelligent-sort", "status": "stale_plan", "message": "Intelligent plan is stale; please refresh the preview."}])
            if not ns.confirm:
                report = {
                    "version": 1,
                    "mode": "intelligent-sort-preview",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "folder": str(Path(ns.folder).expanduser().resolve()),
                    "plan_hash": plan_hash,
                    "summary": {
                        "total": len(results),
                        "auto": sum(1 for r in results if r.get("decision") == "auto"),
                        "review": sum(1 for r in results if r.get("decision") == "review"),
                        "leave": sum(1 for r in results if r.get("decision") == "leave"),
                    },
                    "files": results,
                }
                report_path = write_intelligent_report(ns.folder, report)
                return json_response(True, 0, [{"event": "intelligent-sort", "status": "confirmation_required", "eligible": len(eligible), "review": sum(1 for r in results if r.get("decision") == "review"), "leave": sum(1 for r in results if r.get("decision") == "leave"), "report": str(report_path), "message": "Explicit confirmation required; no files changed."}])
            if ns.select:
                selected = {str(Path(value).expanduser().resolve()) for value in ns.select}
                eligible_by_source = {str(Path(item["source"]).expanduser().resolve()): item for item in eligible}
                if selected - set(eligible_by_source):
                    return json_response(False, 2, [{"event": "intelligent-sort", "status": "invalid_selection", "message": "Selection contains files that are no longer eligible."}])
                eligible = [eligible_by_source[source] for source in sorted(selected)]
            if not eligible:
                return json_response(True, 0, [{"event": "intelligent-sort", "status": "nothing_to_sort", "message": "No confirmed intelligent proposals eligible for sorting."}])
            import tempfile
            root = Path(ns.folder).expanduser().resolve()
            fd, plan_name = tempfile.mkstemp(prefix=".intelligent-plan-", dir=root)
            os.chmod(plan_name, 0o600)
            try:
                with os.fdopen(fd, "wb") as handle:
                    for item in eligible:
                        source = Path(item["source"]).expanduser().resolve()
                        if not source.is_file() or source.is_symlink():
                            raise ValueError(f"invalid intelligent plan source: {source}")
                        if not ns.recursive and source.parent != root:
                            raise ValueError("intelligent plan source is outside the target folder")
                        st = source.stat()
                        signature = f"{st.st_dev}:{st.st_ino}:{st.st_size}:{int(st.st_mtime)}"
                        handle.write(str(source).encode("utf-8") + b"\0" + item["category"].encode("utf-8") + b"\0" + signature.encode("ascii") + b"\0")
                    handle.flush()
                    os.fsync(handle.fileno())
                engine_args = [str(root), "--intelligent-plan", plan_name]
                if ns.recursive:
                    engine_args.append("--unterordner")
                rc = run_engine(engine_args)
                report = {
                    "version": 1,
                    "mode": "intelligent-sort",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "folder": str(root),
                    "plan_hash": plan_hash,
                    "selection": [str(Path(item["source"]).expanduser().resolve()) for item in eligible],
                    "summary": {
                        "selected": len(eligible),
                        "auto": sum(1 for item in eligible if item.get("decision") == "auto"),
                        "review": sum(1 for item in eligible if item.get("decision") == "review"),
                        "leave": sum(1 for item in results if item.get("decision") == "leave"),
                        "engine_exit_code": rc,
                    },
                    "classification": results,
                }
                write_intelligent_report(ns.folder, report)
                return rc
            finally:
                try:
                    os.unlink(plan_name)
                except FileNotFoundError:
                    pass
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            return json_response(False, 2, [{"event": "error", "status": "error", "message": str(exc)}])

    if ns.command == "intelligent-preview":
        if not os.path.isdir(ns.folder):
            return json_response(False, 2, [{"event": "error", "status": "error",
                                             "message": f"folder not found: {ns.folder}"}])
        try:
            config_path = ns.config
            if ns.profile:
                if not CATEGORY_RE.fullmatch(ns.profile):
                    raise ValueError("invalid profile name")
                config_path = str(ROOT / "profile" / f"{ns.profile}.txt")
            categories = load_categories(config_path or str(ROOT / "config.txt"))
            learning_rules = load_learning_rules(ns.folder, categories)
            results = classify_folder(ns.folder, categories, ns.recursive, learning_rules)
        except (OSError, ValueError) as exc:
            return json_response(False, 2, [{"event": "error", "status": "error", "message": str(exc)}])
        events = [{"event": "intelligent", "status": "ok", **item} for item in results]
        events.append({"event": "intelligent-plan", "status": "ready", "plan_hash": intelligent_plan_hash(results), "count": len(results)})
        return json_response(True, 0, events)

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
            if ns.command == "automation-start" and ns.interval < 1:
                raise ValueError("interval must be a positive integer")
            if ns.command == "automation-start":
                options = {
                    "recursive": ns.recursive,
                    "date": ns.date,
                    "copy": ns.copy,
                    "notify": ns.notify,
                    "profile": ns.profile,
                    "config": ns.config,
                    "ignore": ns.ignore,
                    "interval": ns.interval,
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
