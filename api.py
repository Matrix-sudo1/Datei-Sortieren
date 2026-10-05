#!/usr/bin/env python3
"""Stable JSON adapter for Datei-Sortierer v8.2.

The Bash script remains the single source of truth for sorting behaviour.
This module exposes structured JSON for GUI and automation clients.
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
        print(json.dumps({
            "api_version": API_VERSION,
            "success": False,
            "exit_code": 127,
            "events": [{"event": "error", "status": "error",
                        "message": f"Engine not found: {ENGINE}"}],
        }, ensure_ascii=False))
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
        print(json.dumps({
            "api_version": API_VERSION,
            "success": False,
            "exit_code": 126,
            "events": [{"event": "error", "status": "error", "message": str(exc)}],
        }, ensure_ascii=False))
        return 1

    result = {
        "api_version": API_VERSION,
        "success": proc.returncode == 0,
        "exit_code": proc.returncode,
        "events": parse_events(proc.stdout),
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if proc.returncode == 0 else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="JSON API for Datei-Sortierer v8.2")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("folder")
        p.add_argument("--recursive", action="store_true")
        p.add_argument("--date", action="store_true")
        p.add_argument("--copy", action="store_true")
        p.add_argument("--profile")
        p.add_argument("--config")
        p.add_argument("--ignore")

    preview = sub.add_parser("preview", help="preview without changing files")
    common(preview)

    sort = sub.add_parser("sort", help="sort files")
    common(sort)
    sort.add_argument("--report", action="store_true")

    undo = sub.add_parser("undo", help="undo the last sort")
    undo.add_argument("folder")

    log = sub.add_parser("log", help="read the last journal")
    log.add_argument("folder")
    return parser


def main() -> int:
    parser = build_parser()
    ns = parser.parse_args()

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

    if ns.command in {"undo", "log"}:
        if not os.path.isdir(ns.folder):
            parser.error(f"folder not found: {ns.folder}")
        return run_engine([ns.folder, "--" + ns.command])

    parser.error("unsupported command")
    return 2


if __name__ == "__main__":
    sys.exit(main())
