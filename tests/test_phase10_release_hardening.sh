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
mkdir -p "$TMP/automation/.datei-sortierer"
chmod 700 "$TMP/automation/.datei-sortierer"

python3 - "$TMP/automation/.datei-sortierer/automation.json" "$TMP/automation" "$$" <<'PY'
import json,sys
path,folder,pid=sys.argv[1],sys.argv[2],int(sys.argv[3])
state={
    "status":"running",
    "pid":pid,
    "folder":folder,
    "options":{"interval":2},
}
with open(path,"w",encoding="utf-8") as handle:
    json.dump(state,handle)
PY
chmod 600 "$TMP/automation/.datei-sortierer/automation.json"

python3 "$ROOT/api.py" automation-status "$TMP/automation" > "$TMP/stale.json"
python3 - "$TMP/stale.json" <<'PY'
import json,sys
p=json.load(open(sys.argv[1],encoding="utf-8"))
assert p["success"] and p["events"][0]["status"] == "stopped", p
assert "expected watch process" in p["events"][0]["message"], p
PY

python3 - "$ROOT" <<'PY'
import sys
sys.path.insert(0,sys.argv[1])
from api import automation_process_matches
assert automation_process_matches(1, "/tmp") is False
PY

python3 "$ROOT/api.py" automation-start "$TMP/automation" --interval 0 > "$TMP/bad-interval.json" || true
python3 - "$TMP/bad-interval.json" <<'PY'
import json,sys
p=json.load(open(sys.argv[1],encoding="utf-8"))
assert not p["success"] and p["exit_code"] == 2, p
PY

python3 "$ROOT/api.py" automation-start "$TMP/automation" --interval 86401 > "$TMP/bad-interval-high.json" || true
python3 - "$TMP/bad-interval-high.json" <<'PY'
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
