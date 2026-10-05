#!/usr/bin/env python3
"""Machine-readable API for Datei-Sortierer v8.2.

The Bash engine remains the single source of truth. This adapter adds a stable
JSON response for GUI and automation clients without duplicating sort rules.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


API_VERSION = "1"
ROOT = Path(__file__).resolve().parent
ENGINE = ROOT / "datei_sortieren.sh"


def parse_events(stdout: str) -> list[dict]:
    events: list[dict] = []
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
        result = {
            "api_version": API_VERSION,
            "success": False,
            "exit_code": 127,
            "events": [{"event": "error", "status": "error",
                        "message": f"Engine not found: {ENGINE}"}],
        }
        print(json.dumps(result, ensure_ascii=False))
        return 1

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
        result = {
            "api_version": API_VERSION,
            "success": False,
            "exit_code": 126,
            "events": [{"event": "error", "status": "error", "message": str(exc)}],
        }
        print(json.dumps(result, ensure_ascii=False))
        return 1

    events = parse_events(proc.stdout)
    success = proc.returncode == 0
    result = {
        "api_version": API_VERSION,
        "success": success,
        "exit_code": proc.returncode,
        "events": events,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if success else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="JSON API adapter for Datei-Sortierer v8.2"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("folder", help="folder to process")
        p.add_argument("--recursive", action="store_true", help="include subfolders")
        p.add_argument("--date", action="store_true", help="sort by date")
        p.add_argument("--copy", action="store_true", help="copy instead of move")
        p.add_argument("--profile", help="profile name")
        p.add_argument("--config", help="configuration file")
        p.add_argument("--ignore", help="ignore file")

    p_preview = sub.add_parser("preview", help="preview a sort without changes")
    common(p_preview)

    p_sort = sub.add_parser("sort", help="sort a folder")
    common(p_sort)
    p_sort.add_argument("--report", action="store_true")

    p_undo = sub.add_parser("undo", help="undo the last sort")
    p_undo.add_argument("folder")

    p_log = sub.add_parser("log", help="read the last sort journal")
    p_log.add_argument("folder")

    return parser


def main() -> int:
    parser = build_parser()
    ns = parser.parse_args()

    if not ENGINE.is_file():
        return run_engine([])

    if ns.command in {"preview", "sort"}:
        if not os.path.isdir(ns.folder):
            parser.error(f"folder not found: {ns.folder}")
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
        if ns.command == "sort" and ns.report:
            args.append("--bericht")
        return run_engine(args)

    if ns.command == "undo":
        if not os.path.isdir(ns.folder):
            parser.error(f"folder not found: {ns.folder}")
        return run_engine([ns.folder, "--undo"])

    if ns.command == "log":
        if not os.path.isdir(ns.folder):
            parser.error(f"folder not found: {ns.folder}")
        return run_engine([ns.folder, "--log"])

    parser.error("unsupported command")
    return 2


if __name__ == "__main__":
    sys.exit(main())
