#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$ROOT/datei_sortieren.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
assert_file() { [ -f "$1" ] || fail "Datei fehlt: $1"; }
assert_not_file() { [ ! -f "$1" ] || fail "Datei unerwartet vorhanden: $1"; }

echo "[1/10] Bash- und Python-Syntax"
bash -n "$SCRIPT"
python3 -m py_compile "$ROOT/gui.py" "$ROOT/api.py"
rm -rf "$ROOT/__pycache__"

echo "[2/10] Standard-Sortierung"
mkdir -p "$TMP/basic"
printf 'bild' > "$TMP/basic/foto.jpg"
printf 'text' > "$TMP/basic/notiz.txt"
bash "$SCRIPT" "$TMP/basic" >/dev/null
assert_file "$TMP/basic/Bilder/foto.jpg"
assert_file "$TMP/basic/Dokumente/notiz.txt"
assert_not_file "$TMP/basic/foto.jpg"

echo "[3/10] Profile"
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

echo "[4/10] Rekursiver Snapshot"
mkdir -p "$TMP/recursive/nested"
printf 'code' > "$TMP/recursive/nested/tool.py"
bash "$SCRIPT" "$TMP/recursive" --unterordner >/dev/null
assert_file "$TMP/recursive/Code/tool.py"
assert_not_file "$TMP/recursive/Code/Code/tool.py"

echo "[5/10] Spezialnamen und Dry-Run"
mkdir -p "$TMP/special"
printf "safe" > "$TMP/special/hello world.txt"
printf "dry" > "$TMP/special/preview.pdf"
before=$(find "$TMP/special" -type f | sort | sha256sum)
bash "$SCRIPT" "$TMP/special" --dry-run >/dev/null
after=$(find "$TMP/special" -type f | sort | sha256sum)
[ "$before" = "$after" ] || fail "Dry-Run hat Dateien veraendert"
assert_file "$TMP/special/hello world.txt"
assert_file "$TMP/special/preview.pdf"

echo "[6/10] Symlink-Zielschutz"
mkdir -p "$TMP/symlink-target" "$TMP/symlink"
ln -s "$TMP/symlink-target" "$TMP/symlink/Bilder"
printf "image" > "$TMP/symlink/photo.jpg"
bash "$SCRIPT" "$TMP/symlink" >/dev/null 2>&1 || true
assert_file "$TMP/symlink/photo.jpg"


echo "[7/10] Undo-Journal mit Sonderzeichen"
mkdir -p "$TMP/undo"
printf 'undo' > "$TMP/undo/file with spaces.txt"
printf 'tab' > "$TMP/undo/file	with	tabs.txt"
bash "$SCRIPT" "$TMP/undo" >/dev/null
assert_file "$TMP/undo/Dokumente/file with spaces.txt"
assert_file "$TMP/undo/Dokumente/file	with	tabs.txt"
if ! bash "$SCRIPT" "$TMP/undo" --undo >"$TMP/undo-output.txt" 2>&1; then
  cat "$TMP/undo-output.txt" >&2
  fail "Undo fehlgeschlagen"
fi
assert_file "$TMP/undo/file with spaces.txt"
assert_file "$TMP/undo/file	with	tabs.txt"

echo "[8/10] JSON-API und Journal-Reader"
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

echo "[10/10] Watch-Engine Struktur und Event-Fallback"
grep -q 'watch_inotify()' "$SCRIPT" || fail "Watch-Engine fehlt"
grep -q 'read -r -t 1 EVENT_PATH EVENT_TYPE' "$SCRIPT" || fail "Watch-Debounce fehlt"
grep -q 'inotifywait -q -m -r' "$SCRIPT" || fail "Rekursiver inotify-Watcher fehlt"
grep -q 'watch_polling()' "$SCRIPT" || fail "Polling-Fallback fehlt"

# Echtes Event-Smoketest mit einem kleinen inotifywait-Mock. Der Mock liefert
# genau ein CREATE-Ereignis; danach muss der Watcher sauber auf Polling fallen.
mkdir -p "$TMP/watch" "$TMP/watch-bin"
printf 'watch' > "$TMP/watch/new.txt"
cat > "$TMP/watch-bin/inotifywait" <<'MOCK'
#!/usr/bin/env bash
ROOT="${@: -1}"
printf '%s|CLOSE_WRITE\n' "$ROOT/new.txt"
MOCK
chmod +x "$TMP/watch-bin/inotifywait"

# Die Datei muss zunächst im Watch-Root liegen. Der Mock liefert das Event,
# danach wird der Event-Handler nach der Debounce-Zeit ausgeführt.
PATH="$TMP/watch-bin:$PATH" timeout 4 bash "$SCRIPT" "$TMP/watch" --watch >/dev/null 2>&1 || true
assert_file "$TMP/watch/Dokumente/new.txt"

echo "[9/10] JSON-API Fehler bleiben maschinenlesbar"
INVALID_FOLDER_OUTPUT=$(python3 "$ROOT/api.py" preview "$TMP/does-not-exist" || true)
printf '%s' "$INVALID_FOLDER_OUTPUT" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"] is False and p["exit_code"] == 2 and p["events"][0]["event"] == "error", p'
INVALID_ARGS_OUTPUT=$(python3 "$ROOT/api.py" preview || true)
printf '%s' "$INVALID_ARGS_OUTPUT" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"] is False and p["exit_code"] == 2 and p["events"][0]["event"] == "error", p'

echo "[11/11] GUI/API-Entkopplung"
grep -q 'def _api_aktion(self, args, label, callback=None):' "$ROOT/gui.py" || fail "GUI API-Aktionsadapter fehlt"
grep -q 'self._api_aktion(args, "SORTIERUNG"' "$ROOT/gui.py" || fail "GUI-Sortierung nutzt nicht die JSON API"
grep -q 'self._api_aktion(["undo", self.ordner_pfad.get()]' "$ROOT/gui.py" || fail "GUI-Undo nutzt nicht die JSON API"
grep -q 'self._api_aktion(["log", self.ordner_pfad.get()]' "$ROOT/gui.py" || fail "GUI-Log nutzt nicht die JSON API"
grep -q 'p.add_argument("--notify", action="store_true")' "$ROOT/api.py" || fail "API-Notify fehlt"

echo "[12/12] Konfigurations-API und GUI-Editor"
mkdir -p "$TMP/config"
cat > "$TMP/config/custom.txt" <<'CFG'
# custom
Bilder=jpg jpeg png
Dokumente=pdf txt
CFG
CONFIG_OUTPUT=$(python3 "$ROOT/api.py" config "$TMP/config/custom.txt")
printf '%s' "$CONFIG_OUTPUT" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"] and len(p["events"]) == 2, p'
INVALID_CONFIG="$TMP/config/invalid.txt"
printf 'Bad/Name=txt\n' > "$INVALID_CONFIG"
INVALID_CONFIG_OUTPUT=$(python3 "$ROOT/api.py" config "$INVALID_CONFIG" || true)
printf '%s' "$INVALID_CONFIG_OUTPUT" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert not p["success"] and p["exit_code"] == 2, p'
CONFIG_CONTENT="Bilder=jpg png\nDokumente=pdf txt\n"
SAVE_OUTPUT=$(python3 "$ROOT/api.py" config-save "$TMP/config/saved.txt" --content "$CONFIG_CONTENT")
printf '%s' "$SAVE_OUTPUT" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"], p'
grep -q 'Bilder=jpg png' "$TMP/config/saved.txt" || fail "Config-Speichern fehlgeschlagen"
grep -q 'def _baue_tab_config(self):' "$ROOT/gui.py" || fail "Config-GUI fehlt"
grep -q 'self._config_api(["config", self._config_datei()])' "$ROOT/gui.py" || fail "Config-GUI nutzt API nicht"
grep -q 'config-save' "$ROOT/gui.py" || fail "Config-GUI Save fehlt"

echo "PASS: v8.6 configuration hardening tests"
