#!/usr/bin/env python3
"""Deterministic intelligent classification for Datei-Sortierer v9.0.

This module proposes categories only. It never moves, renames or deletes files.
The existing Bash engine remains authoritative for actual sorting.
"""
from __future__ import annotations

import mimetypes
import re
from pathlib import Path
from typing import Iterable


DEFAULT_CONFIG = Path(__file__).resolve().parent / "config.txt"
TOKEN_RE = re.compile(r"[a-z0-9]+")

# Confidence policy for intelligent proposals. This is deliberately proposal-only:
# no policy decision invokes the Bash sorting engine.
CONFIDENCE_AUTO = 0.85
CONFIDENCE_REVIEW = 0.65


def confidence_policy(confidence: float) -> dict[str, str]:
    """Map deterministic confidence to an explicit, non-destructive decision."""
    value = float(confidence)
    if value >= CONFIDENCE_AUTO:
        return {"decision": "auto", "confidence_band": "high", "policy": "high-confidence proposal; explicit confirmation still required"}
    if value >= CONFIDENCE_REVIEW:
        return {"decision": "review", "confidence_band": "medium", "policy": "review recommended before sorting"}
    return {"decision": "leave", "confidence_band": "low", "policy": "do not automatically sort"}


def decision_action(decision: str) -> str:
    """Return the only permitted next-step action for a policy decision."""
    actions = {
        "auto": "eligible_for_confirmation",
        "review": "requires_review",
        "leave": "leave_untouched",
    }
    try:
        return actions[decision]
    except KeyError as exc:
        raise ValueError(f"unknown decision: {decision}") from exc


def build_decision(result: dict) -> dict:
    """Attach an explicit action recommendation without performing file I/O."""
    policy = confidence_policy(result.get("confidence", 0.0))
    decision = dict(result)
    decision.update(policy)
    decision["action"] = decision_action(policy["decision"])
    return decision

# Conservative filename signals. They are only used when extension/MIME data
# does not already provide a stronger deterministic classification.
NAME_HINTS = {
    "Bilder": {"foto", "photo", "image", "img", "screenshot", "scan", "bild"},
    "Videos": {"video", "movie", "film", "clip", "aufnahme"},
    "Audio": {"audio", "song", "track", "musik", "music", "podcast", "recording"},
    "Dokumente": {"doc", "document", "dokument", "brief", "rechnung", "invoice", "vertrag", "report", "bericht", "notiz"},
    "Tabellen": {"table", "tabelle", "sheet", "spreadsheet", "budget", "rechnung", "liste"},
    "Praesentation": {"presentation", "praesentation", "presentation", "slides", "folien", "pitch"},
    "Archive": {"archive", "archiv", "backup", "compressed", "paket", "package"},
    "Code": {"code", "script", "source", "src", "api", "program", "projekt", "project", "config"},
    "Ausfuehrbar": {"installer", "setup", "binary", "executable", "app"},
    "Schriften": {"font", "schrift", "typeface"},
}

MIME_HINTS = {
    "image": "Bilder",
    "video": "Videos",
    "audio": "Audio",
    "font": "Schriften",
    "text": "Dokumente",
    "application/pdf": "Dokumente",
    "application/zip": "Archive",
    "application/x-7z-compressed": "Archive",
    "application/x-rar-compressed": "Archive",
    "application/gzip": "Archive",
    "application/x-tar": "Archive",
    "application/msword": "Dokumente",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Dokumente",
    "application/vnd.ms-excel": "Tabellen",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Tabellen",
    "application/vnd.ms-powerpoint": "Praesentation",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "Praesentation",
}

def load_categories(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, set[str]]:
    path = Path(config_path).expanduser()
    if not path.is_file():
        raise ValueError(f"config not found: {path}")
    categories: dict[str, set[str]] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, values = line.split("=", 1)
        name = name.strip()
        extensions = {x.lower().lstrip(".") for x in values.split() if x}
        if name and extensions:
            categories[name] = extensions
    if not categories:
        raise ValueError(f"config contains no categories: {path}")
    return categories

def _mime_category(mime: str | None, categories: dict[str, set[str]]) -> str | None:
    if not mime:
        return None
    for prefix, category in MIME_HINTS.items():
        if mime == prefix or mime.startswith(prefix + "/"):
            if category in categories:
                return category
    return None

def _name_category(name: str, categories: dict[str, set[str]]) -> tuple[str | None, int]:
    tokens = set(TOKEN_RE.findall(name.lower()))
    scores = {category: len(tokens & NAME_HINTS.get(category, set()))
              for category in categories}
    best = max(scores.values(), default=0)
    if best <= 0:
        return None, 0
    winners = [category for category, score in scores.items() if score == best]
    if len(winners) != 1:
        return None, 0
    return winners[0], best

def classify_file(path: str | Path, categories: dict[str, set[str]]) -> dict:
    file_path = Path(path).expanduser()
    if not file_path.is_file() or file_path.is_symlink():
        raise ValueError(f"not a regular file: {file_path}")

    suffix = file_path.suffix.lower().lstrip(".")
    if suffix:
        matches = [category for category, exts in categories.items() if suffix in exts]
        if len(matches) == 1:
            return {
                "category": matches[0],
                "confidence": 1.0,
                "reason": f"extension .{suffix} is explicitly mapped to {matches[0]}",
                "signal": "extension",
            }
        if len(matches) > 1:
            return {
                "category": "Sonstiges",
                "confidence": 0.0,
                "reason": f"extension .{suffix} is ambiguous in configuration",
                "signal": "fallback",
            }

    mime = mimetypes.guess_type(file_path.name, strict=False)[0]
    mime_category = _mime_category(mime, categories)
    if mime_category:
        return {
            "category": mime_category,
            "confidence": 0.85,
            "reason": f"MIME type {mime} suggests {mime_category}",
            "signal": "mime",
        }

    name_category, score = _name_category(file_path.stem, categories)
    if name_category:
        confidence = min(0.65, 0.45 + score * 0.10)
        return {
            "category": name_category,
            "confidence": round(confidence, 2),
            "reason": f"filename signals suggest {name_category}",
            "signal": "filename",
        }

    return {
        "category": "Sonstiges",
        "confidence": 0.0,
        "reason": "no deterministic extension, MIME or filename signal matched",
        "signal": "fallback",
    }

def iter_files(folder: str | Path, recursive: bool = False) -> Iterable[Path]:
    root = Path(folder).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"folder not found: {root}")
    iterator = root.rglob("*") if recursive else root.iterdir()
    for path in sorted(iterator, key=lambda p: str(p).lower()):
        if path.is_file() and not path.is_symlink():
            yield path

def classify_folder(folder: str | Path, categories: dict[str, set[str]], recursive: bool = False) -> list[dict]:
    results = []
    for path in iter_files(folder, recursive):
        result = classify_file(path, categories)
        result = build_decision(result)
        result["source"] = str(path)
        results.append(result)
    return results
