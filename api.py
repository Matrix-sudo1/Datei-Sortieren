#!/usr/bin/env python3
"""Stable JSON adapter for Datei-Sortierer v8.4.

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


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(description="JSON API for Datei-Sortierer v8.4")
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
        if ns.command == "sort" and ns.report:
            args.append("--bericht")
        return run_engine(args)

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
