#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

echo "[1/1] v9.0 Phase 10 Release Hardening"
mkdir -p "$TMP/automation"

python3 "$ROOT/api.py" automation-start "$TMP/automation" --interval 2 > "$TMP/start.json" || true
python3 - "$TMP/start.json" <<'PY'
import json,sys
p=json.load(open(sys.argv[1],encoding="utf-8"))
assert p["success"] and p["events"][0]["status"] == "running", p
with open(sys.argv[1] + ".pid","w",encoding="utf-8") as handle:
    handle.write(str(p["events"][0]["pid"]))
PY
read -r AUTO_PID < "$TMP/start.json.pid"

STATE="$TMP/automation/.datei-sortierer/automation.json"
python3 - "$STATE" "$$" <<'PY'
import json,sys
path,pid=sys.argv[1],int(sys.argv[2])
state=json.load(open(path,encoding="utf-8"))
state["pid"]=pid
with open(path,"w",encoding="utf-8") as handle:
    json.dump(state,handle)
PY

python3 "$ROOT/api.py" automation-status "$TMP/automation" > "$TMP/stale.json"
python3 - "$TMP/stale.json" <<'PY'
import json,sys
p=json.load(open(sys.argv[1],encoding="utf-8"))
assert p["success"] and p["events"][0]["status"] == "stopped", p
PY

kill "$AUTO_PID" 2>/dev/null || true
rm -f "$STATE"

python3 "$ROOT/api.py" automation-start "$TMP/automation" --interval 0 > "$TMP/bad-interval.json" || true
python3 - "$TMP/bad-interval.json" <<'PY'
import json,sys
p=json.load(open(sys.argv[1],encoding="utf-8"))
assert not p["success"] and p["exit_code"] == 2, p
PY

python3 -m py_compile "$ROOT/api.py" "$ROOT/gui.py" "$ROOT/intelligent.py"
grep -Fq 'automation_process_matches' "$ROOT/api.py" || fail "Automation PID-Härtung fehlt"
grep -Fq 'automation_interval_var' "$ROOT/gui.py" || fail "GUI Intervall fehlt"
grep -Fq 'automation_config_var' "$ROOT/gui.py" || fail "GUI Config-Auswahl fehlt"
grep -Fq 'automation_ignore_var' "$ROOT/gui.py" || fail "GUI Ignore-Auswahl fehlt"

echo "PASS: v9.0 Phase 10 release hardening"
