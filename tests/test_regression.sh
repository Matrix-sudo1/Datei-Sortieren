#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$ROOT/datei_sortieren.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
assert_file() { [ -f "$1" ] || fail "Datei fehlt: $1"; }
assert_not_file() { [ ! -f "$1" ] || fail "Datei unerwartet vorhanden: $1"; }

echo "[1/8] Bash-Syntax"
bash -n "$SCRIPT"
python3 -m py_compile "$ROOT/gui.py"
rm -rf "$ROOT/__pycache__"

echo "[2/8] Standard-Sortierung"
mkdir -p "$TMP/basic"
printf 'bild' > "$TMP/basic/foto.jpg"
printf 'text' > "$TMP/basic/notiz.txt"
bash "$SCRIPT" "$TMP/basic" >/dev/null
assert_file "$TMP/basic/Bilder/foto.jpg"
assert_file "$TMP/basic/Dokumente/notiz.txt"
assert_not_file "$TMP/basic/foto.jpg"

echo "[3/8] Profile"
mkdir -p "$TMP/profiles"
printf 'foto' > "$TMP/profiles/bild.png"
bash "$SCRIPT" "$TMP/profiles" --profil fotos >/dev/null
assert_file "$TMP/profiles/Bilder/bild.png"

mkdir -p "$TMP/profiles-office"
printf 'office' > "$TMP/profiles-office/dokument.docx"
bash "$SCRIPT" "$TMP/profiles-office" --profil buero >/dev/null
assert_file "$TMP/profiles-office/Dokumente/dokument.docx"

mkdir -p "$TMP/profiles-dev"
printf 'code' > "$TMP/profiles-dev/app.py"
bash "$SCRIPT" "$TMP/profiles-dev" --profil entwickler >/dev/null
assert_file "$TMP/profiles-dev/Code/app.py"

echo "[4/8] Rekursiver Snapshot"
mkdir -p "$TMP/recursive/nested"
printf 'code' > "$TMP/recursive/nested/tool.py"
bash "$SCRIPT" "$TMP/recursive" --unterordner >/dev/null
assert_file "$TMP/recursive/Code/tool.py"
assert_not_file "$TMP/recursive/Code/Code/tool.py"

echo "[5/8] Spezialnamen und Dry-Run"
mkdir -p "$TMP/special"
printf "safe" > "$TMP/special/hello world.txt"
printf "dry" > "$TMP/special/preview.pdf"
before=$(find "$TMP/special" -type f | sort | sha256sum)
bash "$SCRIPT" "$TMP/special" --dry-run >/dev/null
after=$(find "$TMP/special" -type f | sort | sha256sum)
[ "$before" = "$after" ] || fail "Dry-Run hat Dateien veraendert"
assert_file "$TMP/special/hello world.txt"
assert_file "$TMP/special/preview.pdf"

echo "[6/8] Symlink-Zielschutz"
mkdir -p "$TMP/symlink-target" "$TMP/symlink"
ln -s "$TMP/symlink-target" "$TMP/symlink/Bilder"
printf "image" > "$TMP/symlink/photo.jpg"
bash "$SCRIPT" "$TMP/symlink" >/dev/null 2>&1 || true
assert_file "$TMP/symlink/photo.jpg"


echo "[7/8] Undo-Journal mit Sonderzeichen"
mkdir -p "$TMP/undo"
printf 'undo' > "$TMP/undo/file with spaces.txt"
printf 'tab' > "$TMP/undo/file	with	tabs.txt"
bash "$SCRIPT" "$TMP/undo" >/dev/null
assert_file "$TMP/undo/Dokumente/file with spaces.txt"
assert_file "$TMP/undo/Dokumente/file	with	tabs.txt"
bash "$SCRIPT" "$TMP/undo" --undo >/dev/null
assert_file "$TMP/undo/file with spaces.txt"
assert_file "$TMP/undo/file	with	tabs.txt"

echo "[8/8] JSON-API und Journal-Reader"
python3 -m py_compile "$ROOT/api.py"
mkdir -p "$TMP/api"
printf 'quote' > "$TMP/api/quote-name.txt"
printf 'tab' > "$TMP/api/file	with	tabs.txt"
printf 'line' > "$TMP/api/file
with
newline.txt"

API_OUTPUT=$(python3 "$ROOT/api.py" preview "$TMP/api" --recursive)
printf '%s' "$API_OUTPUT" | python3 -c '
import json, sys
payload = json.load(sys.stdin)
assert payload["success"] is True, payload
events = [e for e in payload["events"] if e["event"] == "preview"]
assert len(events) == 3, payload
assert any("\t" in e["source"] for e in events)
assert any("\n" in e["source"] for e in events)
'

bash "$SCRIPT" "$TMP/api" >/dev/null
LOG_OUTPUT=$(python3 "$ROOT/api.py" log "$TMP/api")
printf '%s' "$LOG_OUTPUT" | python3 -c '
import json, sys
payload = json.load(sys.stdin)
assert payload["success"] is True, payload
events = [e for e in payload["events"] if e["event"] == "log"]
assert len(events) == 3, payload
'

echo "PASS: v8.2 regression tests"
