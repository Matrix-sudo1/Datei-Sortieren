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
CONFIG_CONTENT=$(printf 'Bilder=jpg png\nDokumente=pdf txt\n')
SAVE_OUTPUT=$(python3 "$ROOT/api.py" config-save "$TMP/config/saved.txt" --content "$CONFIG_CONTENT")
printf '%s' "$SAVE_OUTPUT" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"], p'
grep -q 'Bilder=jpg png' "$TMP/config/saved.txt" || fail "Config-Speichern fehlgeschlagen"
grep -Fq 'def _baue_tab_config(self):' "$ROOT/gui.py" || fail "Config-GUI fehlt"
grep -Fq 'self._config_api(["config", self._config_datei()])' "$ROOT/gui.py" || fail "Config-GUI nutzt API nicht"
grep -Fq 'config-save' "$ROOT/gui.py" || fail "Config-GUI Save fehlt"



echo "[13/13] v8.7 Journal-Crashschutz und beschaedigte Journals"
mkdir -p "$TMP/journal"
printf 'old-source\0old-target\0old-date\0' > "$TMP/journal/.sortier_log.txt"
printf 'broken-source\0broken-target\0' >> "$TMP/journal/.sortier_log.txt"
if bash "$SCRIPT" "$TMP/journal" --undo >/dev/null 2>&1; then
  fail "Beschaedigtes Journal wurde akzeptiert"
fi
[ -s "$TMP/journal/.sortier_log.txt" ] || fail "Beschaedigtes Journal wurde geloescht"
printf 'pending-source\0pending-target\0pending-date\0' > "$TMP/journal/.sortier_log.txt.pending"
UNDO_PENDING_OUTPUT=$(bash "$SCRIPT" "$TMP/journal" --undo 2>&1 || true)
printf '%s' "$UNDO_PENDING_OUTPUT" | grep -q "Nicht vorhanden" || fail "Pending-Journal wurde nicht als aktives Journal erkannt"
assert_file "$TMP/journal/.sortier_log.txt.pending"

echo "[14/14] v8.7 Config-Symlink-Schutz"
mkdir -p "$TMP/config-symlink"
printf 'Bilder=jpg\n' > "$TMP/config-symlink/real.txt"
ln -s "$TMP/config-symlink/real.txt" "$TMP/config-symlink/link.txt"
SYMLINK_SAVE=$(python3 "$ROOT/api.py" config-save "$TMP/config-symlink/link.txt" --content 'Bilder=png' || true)
printf '%s' "$SYMLINK_SAVE" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert not p["success"] and p["exit_code"] == 2, p'
grep -q 'Bilder=jpg' "$TMP/config-symlink/real.txt" || fail "Symlink-Ziel wurde beim Config-Save veraendert"



echo "[15/15] v8.8 Profile-API"
PROFILE_OUTPUT=$(python3 "$ROOT/api.py" profiles)
printf '%s' "$PROFILE_OUTPUT" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"], p; names={e["profile"] for e in p["events"]}; assert {"fotos","buero","entwickler"} <= names, p'

echo "[16/16] v8.8 Automation Lifecycle"
mkdir -p "$TMP/automation"
AUTO_START=$(python3 "$ROOT/api.py" automation-start "$TMP/automation" --interval 1)
printf '%s' "$AUTO_START" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"], p; assert p["events"][0]["status"] == "running", p'
AUTO_STATUS=$(python3 "$ROOT/api.py" automation-status "$TMP/automation")
printf '%s' "$AUTO_STATUS" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"], p; assert p["events"][0]["status"] == "running", p'
AUTO_PAUSE=$(python3 "$ROOT/api.py" automation-pause "$TMP/automation")
printf '%s' "$AUTO_PAUSE" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"], p; assert p["events"][0]["status"] == "paused", p'
AUTO_RESUME=$(python3 "$ROOT/api.py" automation-resume "$TMP/automation")
printf '%s' "$AUTO_RESUME" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"], p; assert p["events"][0]["status"] == "running", p'
sleep 2
printf 'automation' > "$TMP/automation/test.txt"
for _ in 1 2 3 4 5 6; do
  [ -f "$TMP/automation/Dokumente/test.txt" ] && break
  sleep 1
done
assert_file "$TMP/automation/Dokumente/test.txt"
AUTO_STOP=$(python3 "$ROOT/api.py" automation-stop "$TMP/automation")
printf '%s' "$AUTO_STOP" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"] and p["events"][0]["status"] == "stopped", p'


echo "[17/17] v9.0 Deterministische Intelligent-Sorting-Klassifizierung"
mkdir -p "$TMP/intelligent"
printf 'jpg' > "$TMP/intelligent/foto.jpg"
printf 'pdf' > "$TMP/intelligent/rechnung.pdf"
printf 'unknown' > "$TMP/intelligent/project_code.zzz"
printf 'unknown' > "$TMP/intelligent/mystery.zzz"
INTELLIGENT_OUTPUT=$(python3 "$ROOT/api.py" intelligent-preview "$TMP/intelligent")
printf '%s' "$INTELLIGENT_OUTPUT" | python3 -c '
import json,sys
p=json.load(sys.stdin)
assert p["success"], p
events=[e for e in p["events"] if e["event"]=="intelligent"]
assert len(events)==4, p
by_name={e["source"].split("/")[-1]:e for e in events}
assert by_name["foto.jpg"]["category"]=="Bilder" and by_name["foto.jpg"]["confidence"]==1.0, p
assert by_name["rechnung.pdf"]["category"]=="Dokumente" and by_name["rechnung.pdf"]["signal"]=="extension", p
assert by_name["project_code.zzz"]["category"]=="Code" and by_name["project_code.zzz"]["signal"]=="filename", p
assert by_name["mystery.zzz"]["category"]=="Sonstiges" and by_name["mystery.zzz"]["confidence"]==0.0 and by_name["mystery.zzz"]["signal"]=="fallback", p
'
before=$(find "$TMP/intelligent" -type f -print | sort | sha256sum)
python3 "$ROOT/api.py" intelligent-preview "$TMP/intelligent" >/dev/null
after=$(find "$TMP/intelligent" -type f -print | sort | sha256sum)
[ "$before" = "$after" ] || fail "Intelligent Preview hat Dateien veraendert"

echo "[18/18] v9.0 GUI Intelligent Preview"
grep -Fq 'def _intelligent_vorschau(self):' "$ROOT/gui.py" || fail "GUI Intelligent Preview fehlt"
grep -Fq 'intelligent-preview' "$ROOT/gui.py" || fail "GUI nutzt Intelligent-Preview API nicht"
grep -Fq 'self.intelligent_btn' "$ROOT/gui.py" || fail "GUI Intelligent Button fehlt"
grep -Fq 'confidence' "$ROOT/gui.py" || fail "GUI zeigt Konfidenz nicht an"
grep -Fq 'reason' "$ROOT/gui.py" || fail "GUI zeigt Klassifizierungsgrund nicht an"

echo "[19/19] v9.0 Confidence-Policy Grenzwerte"
python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); from intelligent import confidence_policy; assert confidence_policy(1.0)["decision"] == "auto"; assert confidence_policy(0.85)["decision"] == "auto"; assert confidence_policy(0.84)["decision"] == "review"; assert confidence_policy(0.65)["decision"] == "review"; assert confidence_policy(0.64)["decision"] == "leave"; assert confidence_policy(0.0)["decision"] == "leave"' "$ROOT"
POLICY_OUTPUT=$(python3 "$ROOT/api.py" intelligent-preview "$TMP/intelligent")
printf '%s' "$POLICY_OUTPUT" | python3 -c 'import json,sys; p=json.load(sys.stdin); events=[e for e in p["events"] if e["event"]=="intelligent"]; by_name={e["source"].split("/")[-1]:e for e in events}; assert by_name["foto.jpg"]["decision"]=="auto" and by_name["foto.jpg"]["confidence_band"]=="high", p; assert by_name["project_code.zzz"]["decision"]=="review" and by_name["project_code.zzz"]["confidence_band"]=="medium", p; assert by_name["mystery.zzz"]["decision"]=="leave" and by_name["mystery.zzz"]["confidence_band"]=="low", p'
grep -Fq 'Nicht automatisch' "$ROOT/gui.py" || fail "GUI zeigt Leave-Policy nicht an"
grep -Fq 'Prüfen' "$ROOT/gui.py" || fail "GUI zeigt Review-Policy nicht an"

echo "[20/20] v9.0 Decision-Engine Aktionen"
python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); from intelligent import build_decision; assert build_decision({"confidence":1.0,"category":"Dokumente"})["action"]=="eligible_for_confirmation"; assert build_decision({"confidence":0.65,"category":"Code"})["action"]=="requires_review"; assert build_decision({"confidence":0.0,"category":"Sonstiges"})["action"]=="leave_untouched"; assert "action" in build_decision({"confidence":0.85,"category":"Bilder"})' "$ROOT"
grep -Fq 'decision_action' "$ROOT/intelligent.py" || fail "Decision Engine fehlt"

echo "[21/21] v9.0 Intelligent Confirmation Gate"
mkdir -p "$TMP/intelligent-sort"
printf 'jpg' > "$TMP/intelligent-sort/confirmed.jpg"
printf 'unknown' > "$TMP/intelligent-sort/mystery.zzz"
NO_CONFIRM=$(python3 "$ROOT/api.py" intelligent-sort "$TMP/intelligent-sort")
printf '%s' "$NO_CONFIRM" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"] and p["events"][0]["status"]=="confirmation_required", p'
assert_file "$TMP/intelligent-sort/confirmed.jpg"
CONFIRM=$(python3 "$ROOT/api.py" intelligent-sort "$TMP/intelligent-sort" --confirm)
printf '%s' "$CONFIRM" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"], p; assert any(e.get("event")=="move" and e.get("status")=="ok" for e in p["events"]), p'
assert_file "$TMP/intelligent-sort/Bilder/confirmed.jpg"
assert_file "$TMP/intelligent-sort/mystery.zzz"
UNDO_INT=$(python3 "$ROOT/api.py" undo "$TMP/intelligent-sort")
printf '%s' "$UNDO_INT" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"], p'
assert_file "$TMP/intelligent-sort/confirmed.jpg"
[ ! -e "$TMP/intelligent-sort/Bilder/confirmed.jpg" ] || fail "Intelligent sort undo failed"

echo "[22/22] v9.0 Intelligent Confirmation GUI"
grep -Fq 'def _intelligent_sortieren(self):' "$ROOT/gui.py" || fail "GUI Intelligent Sort fehlt"
grep -Fq 'intelligent-sort' "$ROOT/gui.py" || fail "GUI nutzt Intelligent Sort API nicht"
grep -Fq 'self.intelligent_sort_btn' "$ROOT/gui.py" || fail "GUI Confirmation Button fehlt"

echo "PASS: v9.0 decision engine tests"

echo "PASS: v9.0 intelligent sorting tests"

echo "[23/23] v9.0 Intelligent Selection Workflow"
mkdir -p "$TMP/intelligent-selection"
printf 'jpg' > "$TMP/intelligent-selection/auto.jpg"
printf 'unknown' > "$TMP/intelligent-selection/project_code.zzz"
printf 'unknown' > "$TMP/intelligent-selection/mystery.zzz"
PREVIEW_SELECTION=$(python3 "$ROOT/api.py" intelligent-preview "$TMP/intelligent-selection")
printf '%s' "$PREVIEW_SELECTION" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"], p; events=p["events"]; assert any(e.get("event")=="intelligent-plan" and e.get("plan_hash") for e in events), p'
PLAN_HASH=$(printf '%s' "$PREVIEW_SELECTION" | python3 -c 'import json,sys; p=json.load(sys.stdin); print(next(e["plan_hash"] for e in p["events"] if e.get("event")=="intelligent-plan") )'
AUTO_SOURCE="$TMP/intelligent-selection/auto.jpg"
REVIEW_SOURCE="$TMP/intelligent-selection/project_code.zzz"
SELECTED=$(python3 "$ROOT/api.py" intelligent-sort "$TMP/intelligent-selection" --confirm --plan-hash "$PLAN_HASH" --select "$AUTO_SOURCE")
printf '%s' "$SELECTED" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"], p'
assert_file "$TMP/intelligent-selection/Bilder/auto.jpg"
assert_file "$TMP/intelligent-selection/project_code.zzz"
assert_file "$TMP/intelligent-selection/mystery.zzz"

mkdir -p "$TMP/intelligent-selection-review"
printf 'unknown' > "$TMP/intelligent-selection-review/project_code.zzz"
PREVIEW_REVIEW=$(python3 "$ROOT/api.py" intelligent-preview "$TMP/intelligent-selection-review")
REVIEW_HASH=$(printf '%s' "$PREVIEW_REVIEW" | python3 -c 'import json,sys; p=json.load(sys.stdin); print(next(e["plan_hash"] for e in p["events"] if e.get("event")=="intelligent-plan") )')
REVIEW_SOURCE="$TMP/intelligent-selection-review/project_code.zzz"
REVIEW_RESULT=$(python3 "$ROOT/api.py" intelligent-sort "$TMP/intelligent-selection-review" --confirm --include-review --plan-hash "$REVIEW_HASH" --select "$REVIEW_SOURCE")
printf '%s' "$REVIEW_RESULT" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"], p'
assert_file "$TMP/intelligent-selection-review/Code/project_code.zzz"

mkdir -p "$TMP/intelligent-selection-stale"
printf 'jpg' > "$TMP/intelligent-selection-stale/stale.jpg"
PREVIEW_STALE=$(python3 "$ROOT/api.py" intelligent-preview "$TMP/intelligent-selection-stale")
STALE_HASH=$(printf '%s' "$PREVIEW_STALE" | python3 -c 'import json,sys; p=json.load(sys.stdin); print(next(e["plan_hash"] for e in p["events"] if e.get("event")=="intelligent-plan") )')
printf 'changed' >> "$TMP/intelligent-selection-stale/stale.jpg"
STALE_RESULT=$(python3 "$ROOT/api.py" intelligent-sort "$TMP/intelligent-selection-stale" --confirm --plan-hash "$STALE_HASH" --select "$TMP/intelligent-selection-stale/stale.jpg" || true)
printf '%s' "$STALE_RESULT" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert not p["success"] and any(e.get("status")=="stale_plan" for e in p["events"]), p'
assert_file "$TMP/intelligent-selection-stale/stale.jpg"

echo "[24/24] v9.0 Intelligent GUI Selection"
grep -Fq 'self._intelligent_rows = []' "$ROOT/gui.py" || fail "GUI selection state fehlt"
grep -Fq 'self._intelligent_plan_hash = None' "$ROOT/gui.py" || fail "GUI plan hash state fehlt"
grep -Fq '--select' "$ROOT/gui.py" || fail "GUI übergibt Auswahl nicht"
grep -Fq '--plan-hash' "$ROOT/gui.py" || fail "GUI übergibt Plan-Hash nicht"
grep -Fq 'state="disabled"' "$ROOT/gui.py" || fail "GUI Leave-Auswahl ist nicht gesperrt"
grep -Fq 'decision == "auto"' "$ROOT/gui.py" || fail "GUI Auto-Vorauswahl fehlt"

echo "PASS: v9.0 Phase 6 intelligent GUI workflow"

INVALID_PROFILE_OUTPUT=$(python3 "$ROOT/api.py" intelligent-preview "$TMP/intelligent" --profile ../config || true)
printf "%s" "$INVALID_PROFILE_OUTPUT" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert not p["success"] and p["exit_code"]==2, p'

echo "[25/25] v9.0 Intelligent Sort Report"
mkdir -p "$TMP/intelligent-report"
printf "jpg" > "$TMP/intelligent-report/report.jpg"
REPORT_PREVIEW=$(python3 "$ROOT/api.py" intelligent-sort "$TMP/intelligent-report")
printf "%s" "$REPORT_PREVIEW" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"], p; e=p["events"][0]; assert e["status"]=="confirmation_required" and e.get("report"), p'
assert_file "$TMP/intelligent-report/.datei-sortierer/intelligent-report.json"
python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); assert p["mode"]=="intelligent-sort-preview"; assert p["summary"]["auto"]==1; assert len(p["files"])==1' "$TMP/intelligent-report/.datei-sortierer/intelligent-report.json"
REPORT_CONFIRM=$(python3 "$ROOT/api.py" intelligent-sort "$TMP/intelligent-report" --confirm)
printf "%s" "$REPORT_CONFIRM" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"], p'
assert_file "$TMP/intelligent-report/Bilder/report.jpg"
python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); assert p["mode"]=="intelligent-sort"; assert p["summary"]["selected"]==1; assert p["summary"]["engine_exit_code"]==0; assert p["plan_hash"]' "$TMP/intelligent-report/.datei-sortierer/intelligent-report.json"
echo "PASS: v9.0 intelligent sort report"

echo "[26/26] v9.0 Learning Rules – deterministic correction"
mkdir -p "$TMP/learning-rules"
printf "unknown" > "$TMP/learning-rules/notes.zzz"
RULE_ADD=$(python3 "$ROOT/api.py" intelligent-rule-add "$TMP/learning-rules" --source extension --pattern zzz --category Code --id ext-zzz-code)
printf "%s" "$RULE_ADD" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"], p; assert p["events"][0]["status"]=="created", p'
assert_file "$TMP/learning-rules/.datei-sortierer/learning-rules.json"
RULE_PREVIEW=$(python3 "$ROOT/api.py" intelligent-preview "$TMP/learning-rules")
printf "%s" "$RULE_PREVIEW" | python3 -c 'import json,sys; p=json.load(sys.stdin); e=next(e for e in p["events"] if e.get("event")=="intelligent"); assert e["category"]=="Code" and e["confidence"]==1.0 and e["signal"]=="learning_rule" and e["rule_id"]=="ext-zzz-code", p'
RULE_LIST=$(python3 "$ROOT/api.py" intelligent-rules "$TMP/learning-rules")
printf "%s" "$RULE_LIST" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"] and p["events"][0]["id"]=="ext-zzz-code", p'
RULE_REMOVE=$(python3 "$ROOT/api.py" intelligent-rule-remove "$TMP/learning-rules" --id ext-zzz-code)
printf "%s" "$RULE_REMOVE" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"] and p["events"][0]["status"]=="removed", p'
RULE_FALLBACK=$(python3 "$ROOT/api.py" intelligent-preview "$TMP/learning-rules")
printf "%s" "$RULE_FALLBACK" | python3 -c 'import json,sys; p=json.load(sys.stdin); e=next(e for e in p["events"] if e.get("event")=="intelligent"); assert e["category"]=="Sonstiges" and e["signal"]=="fallback", p'

mkdir -p "$TMP/learning-rules-mime"
printf "unknown" > "$TMP/learning-rules-mime/manual.txt"
RULE_MIME=$(python3 "$ROOT/api.py" intelligent-rule-add "$TMP/learning-rules-mime" --source mime --pattern text/plain --category Dokumente --id mime-text-code)
printf "%s" "$RULE_MIME" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"], p'
MIME_PREVIEW=$(python3 "$ROOT/api.py" intelligent-preview "$TMP/learning-rules-mime")
printf "%s" "$MIME_PREVIEW" | python3 -c 'import json,sys; p=json.load(sys.stdin); e=next(e for e in p["events"] if e.get("event")=="intelligent"); assert e["category"]=="Dokumente" and e["rule_id"]=="mime-text-code", p'

mkdir -p "$TMP/learning-rules-invalid"
INVALID_RULE=$(python3 "$ROOT/api.py" intelligent-rule-add "$TMP/learning-rules-invalid" --source extension --pattern '../x' --category Code || true)
printf "%s" "$INVALID_RULE" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert not p["success"] and p["exit_code"]==2, p'
grep -Fq 'Als Regel übernehmen' "$ROOT/gui.py" || fail "GUI Lernregel-Aktion fehlt"
grep -Fq 'learning-rule' "$ROOT/api.py" || fail "Learning-Rule API fehlt"
grep -Fq 'load_learning_rules' "$ROOT/intelligent.py" || fail "Learning Rules werden nicht angewendet"
echo "PASS: v9.0 Phase 8 learning rules"

echo "[27/27] v9.0 Phase 9 Rule Management & Explainability"
mkdir -p "$TMP/learning-rules-management"
printf "unknown" > "$TMP/learning-rules-management/custom.zzz"
ADD_MGMT=$(python3 "$ROOT/api.py" intelligent-rule-add "$TMP/learning-rules-management" --source extension --pattern zzz --category Code --id mgmt-rule)
printf "%s" "$ADD_MGMT" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"], p'
DISABLE_MGMT=$(python3 "$ROOT/api.py" intelligent-rule-set "$TMP/learning-rules-management" --id mgmt-rule --enabled false)
printf "%s" "$DISABLE_MGMT" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"] and p["events"][0]["enabled"] is False, p'
DISABLED_PREVIEW=$(python3 "$ROOT/api.py" intelligent-preview "$TMP/learning-rules-management")
printf "%s" "$DISABLED_PREVIEW" | python3 -c 'import json,sys; p=json.load(sys.stdin); e=next(e for e in p["events"] if e.get("event")=="intelligent"); assert e["signal"]=="fallback", p'
ENABLE_MGMT=$(python3 "$ROOT/api.py" intelligent-rule-set "$TMP/learning-rules-management" --id mgmt-rule --enabled true)
printf "%s" "$ENABLE_MGMT" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"] and p["events"][0]["enabled"] is True, p'
ENABLED_PREVIEW=$(python3 "$ROOT/api.py" intelligent-preview "$TMP/learning-rules-management")
printf "%s" "$ENABLED_PREVIEW" | python3 -c 'import json,sys; p=json.load(sys.stdin); e=next(e for e in p["events"] if e.get("event")=="intelligent"); assert e["signal"]=="learning_rule" and e["rule_id"]=="mgmt-rule" and e["category"]=="Code", p'
CONFLICT=$(python3 "$ROOT/api.py" intelligent-rule-add "$TMP/learning-rules-management" --source extension --pattern zzz --category Bilder --id conflicting-rule || true)
printf "%s" "$CONFLICT" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert not p["success"] and p["exit_code"]==2, p'
REPORT_MGMT=$(python3 "$ROOT/api.py" intelligent-sort "$TMP/learning-rules-management")
printf "%s" "$REPORT_MGMT" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"], p'
python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); e=p["files"][0]; assert e["signal"]=="learning_rule" and e["rule_id"]=="mgmt-rule" and "explicitly maps" in e["reason"]' "$TMP/learning-rules-management/.datei-sortierer/intelligent-report.json"
grep -Fq 'intelligent-rule-set' "$ROOT/api.py" || fail "Rule enable/disable API fehlt"
grep -Fq 'Lernregeln' "$ROOT/gui.py" || fail "GUI Lernregelverwaltung fehlt"
echo "PASS: v9.0 Phase 9 rule management"

echo "[28/28] v9.0 Phase 10 Release Hardening"
mkdir -p "$TMP/automation-hardening"
AUTO_HARDEN=$(python3 "$ROOT/api.py" automation-start "$TMP/automation-hardening" --interval 2)
printf "%s" "$AUTO_HARDEN" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"] and p["events"][0]["status"]=="running", p'
AUTO_PID=$(printf "%s" "$AUTO_HARDEN" | python3 -c 'import json,sys; p=json.load(sys.stdin); print(p["events"][0]["pid"])')
AUTO_STATE="$TMP/automation-hardening/.datei-sortierer/automation.json"
python3 - "$AUTO_STATE" "$$" <<'PY'
import json,sys
path,pid=sys.argv[1],int(sys.argv[2])
state=json.load(open(path,encoding="utf-8"))
state["pid"]=pid
with open(path,"w",encoding="utf-8") as handle:
    json.dump(state,handle)
PY
STALE_PID=$(python3 "$ROOT/api.py" automation-status "$TMP/automation-hardening")
printf "%s" "$STALE_PID" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["success"] and p["events"][0]["status"]=="stopped", p'
kill "$AUTO_PID" 2>/dev/null || true
rm -f "$AUTO_STATE"
BAD_INTERVAL=$(python3 "$ROOT/api.py" automation-start "$TMP/automation-hardening" --interval 0 || true)
printf "%s" "$BAD_INTERVAL" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert not p["success"] and p["exit_code"]==2, p'
grep -Fq 'automation_process_matches' "$ROOT/api.py" || fail "Automation PID-Härtung fehlt"
grep -Fq 'automation_interval_var' "$ROOT/gui.py" || fail "GUI Intervall fehlt"
grep -Fq 'automation_config_var' "$ROOT/gui.py" || fail "GUI Config-Auswahl fehlt"
grep -Fq 'automation_ignore_var' "$ROOT/gui.py" || fail "GUI Ignore-Auswahl fehlt"
echo "PASS: v9.0 Phase 10 release hardening"
