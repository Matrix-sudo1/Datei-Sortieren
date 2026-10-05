#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$ROOT/datei_sortieren.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
assert_file() { [ -f "$1" ] || fail "Datei fehlt: $1"; }
assert_not_file() { [ ! -f "$1" ] || fail "Datei unerwartet vorhanden: $1"; }

echo "[1/4] Bash-Syntax"
bash -n "$SCRIPT"

echo "[2/4] Standard-Sortierung"
mkdir -p "$TMP/basic"
printf 'bild' > "$TMP/basic/foto.jpg"
printf 'text' > "$TMP/basic/notiz.txt"
bash "$SCRIPT" "$TMP/basic" >/dev/null
assert_file "$TMP/basic/Bilder/foto.jpg"
assert_file "$TMP/basic/Dokumente/notiz.txt"
assert_not_file "$TMP/basic/foto.jpg"

echo "[3/4] Profile"
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

echo "[4/4] Rekursiver Snapshot"
mkdir -p "$TMP/recursive/nested"
printf 'code' > "$TMP/recursive/nested/tool.py"
bash "$SCRIPT" "$TMP/recursive" --unterordner >/dev/null
assert_file "$TMP/recursive/Code/tool.py"
assert_not_file "$TMP/recursive/Code/Code/tool.py"

echo "PASS: v8.0 smoke tests"
