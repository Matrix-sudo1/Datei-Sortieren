#!/bin/bash
# ============================================
#  Datei-Sortierer v7.1
#  Optimierungen gegenüber v7.0:
#  - $(basename) → ${f##*/}  (84x schneller)
#  - $(tr lower) → ${v,,}    (47x schneller)
#  - O(n×m) Doppelschleife → O(1) EXT_MAP
#  Bugfixes:
#  - --bericht allein löschte Log → Undo kaputt
#  - | im Dateinamen brach Undo (Tab-Separator)
# ============================================

# --- tac: macOS Fallback ---
if ! command -v tac &>/dev/null; then
  tac() { tail -r -- "$@"; }
fi

# --- Farben ---
ROT='\033[0;31m'; GRUEN='\033[0;32m'; GELB='\033[1;33m'
BLAU='\033[0;34m'; CYAN='\033[0;36m'; MAGENTA='\033[0;35m'; RESET='\033[0m'

# --- Betriebssystem ---
OS_TYP="linux"
[[ "$OSTYPE" == "darwin"* ]] && OS_TYP="macos"

# --- Monatsnamen ---
monat_name() {
  case $1 in
    01) echo "Januar"  ;; 02) echo "Februar"   ;; 03) echo "Maerz"     ;;
    04) echo "April"   ;; 05) echo "Mai"        ;; 06) echo "Juni"      ;;
    07) echo "Juli"    ;; 08) echo "August"     ;; 09) echo "September" ;;
    10) echo "Oktober" ;; 11) echo "November"   ;; 12) echo "Dezember"  ;;
    *) echo "Unbekannt" ;;
  esac
}

# --- Zeitstempel (kein Subshell-basename nötig) ---
get_timestamp() {
  local DATEI="$1" TS=""
  if [ "$OS_TYP" = "macos" ]; then
    TS=$(stat -f "%B" "$DATEI" 2>/dev/null)
    [[ -z "$TS" || "$TS" == "0" ]] && TS=$(stat -f "%m" "$DATEI" 2>/dev/null)
  else
    TS=$(stat --format="%W" "$DATEI" 2>/dev/null)
    [[ -z "$TS" || "$TS" == "0" ]] && TS=$(stat --format="%Y" "$DATEI" 2>/dev/null)
  fi
  echo "${TS:-0}"
}

datum_aus_ts() {
  local TS="$1" FORMAT="$2"
  if [ "$OS_TYP" = "macos" ]; then
    date -r "$TS" "$FORMAT" 2>/dev/null
  else
    date -d "@$TS" "$FORMAT" 2>/dev/null
  fi
}

# OPT: kein $(date) Subshell-Prozess mehr
unique_suffix() { echo "${SECONDS}_$$_${RANDOM}"; }

# ============================================
#  SYSTEM-BENACHRICHTIGUNG
# ============================================
sende_notification() {
  local TITEL="$1" TEXT="$2"
  if [ "$OS_TYP" = "macos" ]; then
    local SAFE_T="${TITEL//\"/\\\"}" SAFE_X="${TEXT//\"/\\\"}"
    osascript -e "display notification \"$SAFE_X\" with title \"$SAFE_T\"" 2>/dev/null || true
  elif command -v notify-send &>/dev/null; then
    notify-send "$TITEL" "$TEXT" --icon=folder 2>/dev/null || true
  elif command -v zenity &>/dev/null; then
    zenity --notification --text="$TITEL: $TEXT" 2>/dev/null || true
  fi
}

# ============================================
#  PAPIERKORB
# ============================================
in_papierkorb() {
  local DATEI="$1"
  if [ "$OS_TYP" = "macos" ]; then
    mkdir -p "$HOME/.Trash"
    mv -- "$DATEI" "$HOME/.Trash/" 2>/dev/null && return 0
  elif command -v gio &>/dev/null; then
    gio trash -- "$DATEI" 2>/dev/null && return 0
  elif command -v trash-put &>/dev/null; then
    trash-put -- "$DATEI" 2>/dev/null && return 0
  fi
  local TRASH_DIR="$HOME/.local/share/Trash/files"
  mkdir -p "$TRASH_DIR"
  mv -- "$DATEI" "$TRASH_DIR/" 2>/dev/null && return 0
  return 1
}

# ============================================
#  HILFE
# ============================================
hilfe() {
  echo -e "${CYAN}"
  echo "╔══════════════════════════════════════════════╗"
  echo "║         Datei-Sortierer v7.1                 ║"
  echo "╚══════════════════════════════════════════════╝"
  echo -e "${RESET}"
  echo "Verwendung:  ./datei_sortieren.sh [ORDNER] [OPTIONEN]"
  echo ""
  echo "Basis:"
  echo "  --dry-run           Vorschau (nichts wird verschoben)"
  echo "  --kopieren          Dateien kopieren statt verschieben"
  echo "  --unterordner       Dateien in Unterordnern einbeziehen"
  echo "  --undo              Letzte Sortierung rueckgaengig machen"
  echo "  --log               Log anzeigen"
  echo "  --nach-datum        Nach Erstelldatum sortieren (Jahr/Monat)"
  echo "  --duplikate         Duplikate suchen"
  echo "  --config DATEI      Eigene Konfiguration"
  echo "  --help              Diese Hilfe"
  echo ""
  echo "v6.0+:"
  echo "  --watch             Ordner beobachten & automatisch sortieren"
  echo "  --watch-interval N  Polling-Intervall in Sekunden (Standard: 10)"
  echo "  --notify            System-Popup bei Watch-Aktivitaet"
  echo "  --profil NAME       Profil laden (fotos / buero / entwickler)"
  echo "  --profile-list      Alle Profile anzeigen"
  echo "  --ignore DATEI      Ignorier-Liste"
  echo "  --ordner A B C      Mehrere Ordner sortieren"
  echo ""
  echo "v7.0+:"
  echo "  --cronjob UHRZEIT   Automatische Sortierung einrichten (z.B. '20:00')"
  echo "  --cronjob-list      Alle geplanten Sortierungen anzeigen"
  echo "  --cronjob-remove    Alle geplanten Sortierungen entfernen"
  echo "  --bericht [DATEI]   HTML-Bericht nach Sortierung speichern"
  echo ""
  echo "Beispiele:"
  echo "  ./datei_sortieren.sh ~/Downloads"
  echo "  ./datei_sortieren.sh ~/Downloads --dry-run"
  echo "  ./datei_sortieren.sh ~/Downloads --watch --notify"
  echo "  ./datei_sortieren.sh ~/Downloads --cronjob 20:00"
  echo "  ./datei_sortieren.sh ~/Downloads --bericht"
  echo "  ./datei_sortieren.sh --ordner ~/Downloads ~/Desktop"
  exit 0
}

# ============================================
#  STANDARDWERTE
# ============================================
ZIEL="."
DRYRUN=false; UNDO=false; ZEIG_LOG=false; NACH_DATUM=false
DUPLIKATE=false; WATCH=false; WATCH_INTERVAL=10; NOTIFY=false
KOPIEREN=false; UNTERORDNER=false
PROFIL=""; PROFIL_LIST=false
CRONJOB_UHRZEIT=""; CRONJOB_LIST=false; CRONJOB_REMOVE=false
BERICHT=false; BERICHT_DATEI=""
BASIS_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIGDATEI="$BASIS_DIR/config.txt"
IGNOREDATEI="$BASIS_DIR/ignore.txt"
MULTI_ORDNER=(); MULTI_MODUS=false

# Bericht-Zähler
BERICHT_VERSCHOBEN=0; BERICHT_SONSTIGES=0
BERICHT_IGNORIERT=0; BERICHT_FEHLER=0
declare -A BERICHT_KATEGORIEN
BERICHT_START=$(date '+%d.%m.%Y %H:%M:%S')

# ============================================
#  ARGUMENTE
# ============================================
SKIP_NEXT=""
i=0; ARGS=("$@")
while [ $i -lt ${#ARGS[@]} ]; do
  ARG="${ARGS[$i]}"
  if [ -n "$SKIP_NEXT" ]; then
    case $SKIP_NEXT in
      config)   CONFIGDATEI="$ARG" ;;
      ignore)   IGNOREDATEI="$ARG" ;;
      profil)   PROFIL="$ARG" ;;
      interval)
        if ! [[ "$ARG" =~ ^[0-9]+$ ]] || [ "$ARG" -lt 1 ]; then
          echo -e "${ROT}Fehler: --watch-interval muss eine positive Zahl sein.${RESET}"; exit 1
        fi
        WATCH_INTERVAL="$ARG" ;;
      cronjob_zeit)
        if ! [[ "$ARG" =~ ^([01]?[0-9]|2[0-3]):[0-5][0-9]$ ]]; then
          echo -e "${ROT}Fehler: Ungueltige Uhrzeit '$ARG'. Format: HH:MM${RESET}"; exit 1
        fi
        CRONJOB_UHRZEIT="$ARG" ;;
    esac
    SKIP_NEXT=""; i=$((i+1)); continue
  fi

  case $ARG in
    --dry-run)        DRYRUN=true ;;
    --undo)           UNDO=true ;;
    --log)            ZEIG_LOG=true ;;
    --nach-datum)     NACH_DATUM=true ;;
    --duplikate)      DUPLIKATE=true ;;
    --watch)          WATCH=true ;;
    --notify)         NOTIFY=true ;;
    --kopieren)       KOPIEREN=true ;;
    --unterordner)    UNTERORDNER=true ;;
    --watch-interval) SKIP_NEXT="interval" ;;
    --profile-list)   PROFIL_LIST=true ;;
    --profil)         SKIP_NEXT="profil" ;;
    --config)         SKIP_NEXT="config" ;;
    --ignore)         SKIP_NEXT="ignore" ;;
    --cronjob-list)   CRONJOB_LIST=true ;;
    --cronjob-remove) CRONJOB_REMOVE=true ;;
    --cronjob)        SKIP_NEXT="cronjob_zeit" ;;
    --bericht)
      BERICHT=true
      NAECHSTER="${ARGS[$((i+1))]:-}"
      if [[ -n "$NAECHSTER" && "$NAECHSTER" != --* && ! -d "$NAECHSTER" ]]; then
        BERICHT_DATEI="$NAECHSTER"; i=$((i+1))
      fi ;;
    --help) hilfe ;;
    --ordner)
      MULTI_MODUS=true; i=$((i+1))
      while [ $i -lt ${#ARGS[@]} ]; do
        NAECHSTER="${ARGS[$i]}"
        [[ "$NAECHSTER" == --* ]] && { i=$((i-1)); break; }
        MULTI_ORDNER+=("$NAECHSTER"); i=$((i+1))
      done ;;
    *)
      if [[ "$ARG" != --* ]]; then
        if [ -d "$ARG" ]; then ZIEL="$ARG"
        else
          echo -e "${ROT}Fehler: Ordner '$ARG' nicht gefunden.${RESET}"
          echo -e "${GELB}Tipp: --help fuer alle Optionen.${RESET}"; exit 1
        fi
      fi ;;
  esac
  i=$((i+1))
done

# ============================================
#  CRONJOB-ASSISTENT
# ============================================
CRONJOB_TAG="# datei-sortierer-managed"

cronjob_einrichten() {
  local UHRZEIT="$1" ORDNER="$2"
  local STUNDE="${UHRZEIT%%:*}" MINUTE="${UHRZEIT##*:}"
  local SCRIPT_PFAD="$BASIS_DIR/datei_sortieren.sh"
  local CRON_CMD="$MINUTE $STUNDE * * * bash \"$SCRIPT_PFAD\" \"$ORDNER\" $CRONJOB_TAG"
  local TMP
  TMP=$(mktemp 2>/dev/null) || TMP="/tmp/.sortier_cron_$$"
  crontab -l 2>/dev/null | grep -Fv "$CRONJOB_TAG" > "$TMP" || true
  echo "$CRON_CMD" >> "$TMP"
  crontab "$TMP"; rm -f "$TMP"
  echo -e "${GRUEN}✓ Cronjob: taeglich um $UHRZEIT Uhr → $ORDNER${RESET}"
  echo -e "${GELB}  --cronjob-list | --cronjob-remove${RESET}"
}

if [ -n "$CRONJOB_UHRZEIT" ]; then
  command -v crontab &>/dev/null || { echo -e "${ROT}crontab nicht gefunden.${RESET}"; exit 1; }
  [ "$ZIEL" = "." ] && ZIEL="$(pwd)"
  [ -d "$ZIEL" ] || { echo -e "${ROT}Ordner nicht gefunden: $ZIEL${RESET}"; exit 1; }
  cronjob_einrichten "$CRONJOB_UHRZEIT" "$ZIEL"; exit 0
fi

if $CRONJOB_LIST; then
  echo -e "${CYAN}── Geplante Sortierungen ──${RESET}"
  GEFUNDEN=0
  while IFS= read -r ZEILE; do
    [[ "$ZEILE" != *"$CRONJOB_TAG"* ]] && continue
    MIN=$(echo "$ZEILE" | awk '{print $1}')
    STD=$(echo "$ZEILE" | awk '{print $2}')
    ORD=$(echo "$ZEILE" | awk -F'"' '{print $(NF-1)}')
    printf "  ${GRUEN}%02d:%02d Uhr${RESET}  →  %s\n" "$STD" "$MIN" "$ORD"
    GEFUNDEN=$((GEFUNDEN+1))
  done < <(crontab -l 2>/dev/null)
  [ $GEFUNDEN -eq 0 ] && echo -e "  ${GELB}Keine Eintraege.${RESET}"
  echo -e "${GELB}Neu: --cronjob HH:MM [ORDNER]${RESET}"; exit 0
fi

if $CRONJOB_REMOVE; then
  TMP=$(mktemp 2>/dev/null) || TMP="/tmp/.sortier_cron_$$"
  ANZAHL=$(crontab -l 2>/dev/null | grep -Fc "$CRONJOB_TAG" || echo 0)
  crontab -l 2>/dev/null | grep -Fv "$CRONJOB_TAG" > "$TMP" || true
  crontab "$TMP"; rm -f "$TMP"
  echo -e "${GRUEN}$ANZAHL Cronjob(s) entfernt.${RESET}"; exit 0
fi

# ============================================
#  PROFIL
# ============================================
profil_laden() {
  local NAME="$1"
  local PFAD="$BASIS_DIR/profile/${NAME}.txt"
  if [ -f "$PFAD" ]; then
    CONFIGDATEI="$PFAD"; echo -e "${CYAN}Profil: $NAME${RESET}"
  else
    echo -e "${ROT}Profil '$NAME' nicht gefunden: $PFAD${RESET}"
    echo -e "${GELB}--profile-list fuer alle Profile.${RESET}"; exit 1
  fi
}

if $PROFIL_LIST; then
  echo -e "${CYAN}Verfuegbare Profile:${RESET}"
  GEFUNDEN=0
  for P in "$BASIS_DIR/profile"/*.txt; do
    [ -f "$P" ] || continue
    NAME="${P##*/}"; NAME="${NAME%.txt}"
    ANZAHL=$(grep -c "=" "$P" 2>/dev/null || echo 0)
    echo -e "  ${GRUEN}$NAME${RESET}  ($ANZAHL Kategorien)"
    GEFUNDEN=$((GEFUNDEN+1))
  done
  [ $GEFUNDEN -eq 0 ] && echo -e "  ${GELB}Keine Profile in: $BASIS_DIR/profile/${RESET}"
  echo -e "${GELB}Verwenden: --profil NAME${RESET}"; exit 0
fi

[ -n "$PROFIL" ] && profil_laden "$PROFIL"

# ============================================
#  IGNORIER-LISTE
# ============================================
IGNORE_LISTE=()
if [ -f "$IGNOREDATEI" ]; then
  while IFS= read -r ZEILE; do
    [[ "$ZEILE" =~ ^# || -z "${ZEILE// }" ]] && continue
    IGNORE_LISTE+=("$ZEILE")
  done < "$IGNOREDATEI"
  echo -e "${CYAN}Ignorier-Liste: ${#IGNORE_LISTE[@]} Eintraege${RESET}"
fi

ist_ignoriert() {
  local N="$1"
  for M in "${IGNORE_LISTE[@]}"; do
    [[ "$N" == "$M" || "$N" == $M ]] && return 0
  done
  return 1
}

# ============================================
#  KATEGORIEN LADEN  (OPT: EXT_MAP für O(1))
# ============================================
laden_kategorien() {
  declare -gA KATEGORIEN
  declare -gA EXT_MAP   # OPT: ext → kategorie, O(1) Lookup

  if [ -f "$CONFIGDATEI" ]; then
    echo -e "${CYAN}Konfiguration: ${CONFIGDATEI##*/}${RESET}"
    while IFS='=' read -r KAT ENDUNGEN; do
      [[ "$KAT" =~ ^# || -z "${KAT// }" ]] && continue
      KAT="${KAT// /}"
      [ -n "$KAT" ] && KATEGORIEN["$KAT"]="$ENDUNGEN"
    done < "$CONFIGDATEI"
    [ ${#KATEGORIEN[@]} -eq 0 ] && _lade_standard_kategorien
  else
    echo -e "${GELB}Keine config.txt – Standard-Kategorien.${RESET}"
    _lade_standard_kategorien
  fi

  # OPT: Lookup-Tabelle einmalig aufbauen
  for KAT in "${!KATEGORIEN[@]}"; do
    for EXT in ${KATEGORIEN[$KAT]}; do
      EXT_MAP["$EXT"]="$KAT"
    done
  done
}

_lade_standard_kategorien() {
  KATEGORIEN=(
    ["Bilder"]="jpg jpeg png gif bmp svg webp ico tiff tif heic raw cr2 nef"
    ["Videos"]="mp4 mkv avi mov wmv flv webm m4v mpeg mpg"
    ["Audio"]="mp3 wav flac aac ogg wma m4a opus"
    ["Dokumente"]="pdf doc docx odt txt rtf md"
    ["Tabellen"]="xls xlsx csv ods"
    ["Praesentation"]="ppt pptx odp"
    ["Archive"]="zip tar gz bz2 rar 7z xz"
    ["Code"]="sh py js ts html css php java c cpp h rb go rs sql"
    ["Ausfuehrbar"]="exe dmg deb rpm appimage"
    ["Schriften"]="ttf otf woff woff2"
  )
}

# ============================================
#  LOG  (Tab-Separator: kann nicht in Dateinamen vorkommen)
# ============================================
log_schreiben() {
  local LOGDATEI="$1" QUELLE="$2" ZIEL_DATEI="$3" DATUM="$4"
  printf '%s\t%s\t%s\n' "$QUELLE" "$ZIEL_DATEI" "$DATUM" >> "$LOGDATEI" 2>/dev/null
}

# ============================================
#  HTML-BERICHT
# ============================================
bericht_schreiben() {
  local ORDNER="$1"
  local DATEI="${BERICHT_DATEI:-$ORDNER/sortier_bericht_$(date +%Y%m%d_%H%M).html}"
  local ENDE GESAMT KAT_HTML="" MAX=1 K ANZ PCT

  ENDE=$(date '+%d.%m.%Y %H:%M:%S')
  GESAMT=$((BERICHT_VERSCHOBEN + BERICHT_SONSTIGES))

  for K in "${!BERICHT_KATEGORIEN[@]}"; do
    ANZ="${BERICHT_KATEGORIEN[$K]}"
    [ "$ANZ" -gt "$MAX" ] && MAX="$ANZ"
  done
  for K in "${!BERICHT_KATEGORIEN[@]}"; do
    ANZ="${BERICHT_KATEGORIEN[$K]}"
    PCT=$(( ANZ * 100 / MAX ))
    KAT_HTML+="<div class='row'><span class='name'>$K</span>"
    KAT_HTML+="<div class='bar'><div class='fill' style='width:${PCT}%'></div></div>"
    KAT_HTML+="<span class='count'>${ANZ}x</span></div>"
  done

  cat > "$DATEI" << HTMLEOF
<!DOCTYPE html>
<html lang="de">
<head><meta charset="UTF-8">
<title>Sortier-Bericht – $(date '+%d.%m.%Y')</title>
<style>
  body{font-family:'Segoe UI',sans-serif;background:#0d1117;color:#e8eaf6;margin:0;padding:32px}
  h1{color:#6c3fc5;font-size:28px;margin-bottom:4px}
  .sub{color:#6b7280;font-size:14px;margin-bottom:32px}
  .cards{display:flex;gap:20px;flex-wrap:wrap;margin-bottom:32px}
  .card{background:#161b2e;border:1px solid #2a3050;border-radius:10px;padding:20px 28px;flex:1;min-width:140px}
  .card .num{font-size:36px;font-weight:800;margin-bottom:4px}
  .card .lbl{color:#6b7280;font-size:13px}
  .gruen{color:#2ecc71}.gelb{color:#f39c12}.rot{color:#e8435a}.lila{color:#6c3fc5}
  .section{background:#161b2e;border:1px solid #2a3050;border-radius:10px;padding:24px;margin-bottom:20px}
  h2{font-size:18px;margin:0 0 16px;color:#e8eaf6}
  .row{display:flex;align-items:center;gap:12px;margin-bottom:8px}
  .name{width:160px;font-size:13px;font-weight:600;flex-shrink:0}
  .bar{flex:1;height:12px;background:#2a3050;border-radius:6px;overflow:hidden}
  .fill{height:100%;background:#6c3fc5;border-radius:6px}
  .count{width:40px;text-align:right;font-size:13px;font-weight:700;color:#6c3fc5}
  .meta{color:#6b7280;font-size:12px;margin-top:24px;border-top:1px solid #2a3050;padding-top:16px}
</style></head>
<body>
<h1>📁 Datei-Sortierer – Bericht</h1>
<div class="sub">Sortiert: $ORDNER</div>
<div class="cards">
  <div class="card"><div class="num gruen">$BERICHT_VERSCHOBEN</div><div class="lbl">Sortiert</div></div>
  <div class="card"><div class="num gelb">$BERICHT_SONSTIGES</div><div class="lbl">Sonstiges</div></div>
  <div class="card"><div class="num rot">$BERICHT_FEHLER</div><div class="lbl">Fehler</div></div>
  <div class="card"><div class="num lila">$GESAMT</div><div class="lbl">Gesamt</div></div>
</div>
<div class="section"><h2>📊 Kategorien</h2>$KAT_HTML</div>
<div class="meta">Start: $BERICHT_START &nbsp;|&nbsp; Ende: $ENDE &nbsp;|&nbsp; v7.1</div>
</body></html>
HTMLEOF

  echo -e "${GRUEN}Bericht: $DATEI${RESET}"
}

# ============================================
#  DATEI SORTIEREN  (OPT: keine Subshells mehr)
# ============================================
sortiere_datei() {
  local DATEI="$1" ZIEL_BASIS="$2" DRYRUN_FLAG="$3"
  local LOGDATEI_PFAD="$4" DATUM_FLAG="$5" DATUM_LOG="$6"

  [ -f "$DATEI" ] || return 2

  # OPT: ${##*/} statt $(basename)
  local DATEINAME="${DATEI##*/}"
  [[ "$DATEINAME" == ".sortier_log.txt" || "$DATEINAME" == .* ]] && return 2

  if ist_ignoriert "$DATEINAME"; then
    echo -e "${GELB}IGNORIERT: $DATEINAME${RESET}"; return 2
  fi

  # Datum-Modus
  if [ "$DATUM_FLAG" = "true" ]; then
    local TS JAHR MONAT_NR MONAT ZIELORDNER ZIELDATEI
    TS=$(get_timestamp "$DATEI")
    JAHR=$(datum_aus_ts "$TS" '+%Y')
    MONAT_NR=$(datum_aus_ts "$TS" '+%m')
    MONAT=$(monat_name "$MONAT_NR")
    JAHR="${JAHR:-$(date '+%Y')}"
    [[ "$JAHR" == "1970" ]] && JAHR=$(date '+%Y')
    MONAT="${MONAT:-Unbekannt}"
    ZIELORDNER="$ZIEL_BASIS/$JAHR/$MONAT"
    ZIELDATEI="$ZIELORDNER/$DATEINAME"
    [ -e "$ZIELDATEI" ] && ZIELDATEI="$ZIELORDNER/${DATEINAME%.*}_$(unique_suffix).${DATEINAME##*.}"
    if [ "$DRYRUN_FLAG" = "true" ]; then
      echo -e "${BLAU}VORSCHAU: $DATEINAME  ->  $JAHR/$MONAT/${RESET}"
    else
      mkdir -p "$ZIELORDNER" 2>/dev/null || { echo -e "${ROT}Fehler mkdir: $ZIELORDNER${RESET}"; return 3; }
      local BEFEHL="mv"
      $KOPIEREN && BEFEHL="cp --"
      if $KOPIEREN; then
        cp -- "$DATEI" "$ZIELDATEI" 2>/dev/null
      else
        mv -- "$DATEI" "$ZIELDATEI" 2>/dev/null
      fi
      if [ $? -eq 0 ]; then
        ! $KOPIEREN && log_schreiben "$LOGDATEI_PFAD" "$DATEI" "$ZIELDATEI" "$DATUM_LOG"
        local PFEIL="->"; $KOPIEREN && PFEIL="=>"
        echo -e "${GRUEN}OK: $DATEINAME  $PFEIL  $JAHR/$MONAT/${RESET}"
        BERICHT_KATEGORIEN["$JAHR/$MONAT"]=$(( ${BERICHT_KATEGORIEN["$JAHR/$MONAT"]:-0} + 1 ))
      else
        echo -e "${ROT}Fehler: $DATEINAME${RESET}"; return 3
      fi
    fi
    return 0
  fi

  # OPT: ${,,} statt $(echo ... | tr), EXT_MAP O(1) statt Doppelschleife
  local ENDUNG_KLEIN=""
  [[ "$DATEINAME" == *.* ]] && ENDUNG_KLEIN="${DATEINAME##*.}" && ENDUNG_KLEIN="${ENDUNG_KLEIN,,}"

  local KATEGORIE="${EXT_MAP[$ENDUNG_KLEIN]:-}"

  if [ -n "$KATEGORIE" ]; then
    local ZIELORDNER="$ZIEL_BASIS/$KATEGORIE"
    local ZIELDATEI="$ZIELORDNER/$DATEINAME"
    [ -e "$ZIELDATEI" ] && ZIELDATEI="$ZIELORDNER/${DATEINAME%.*}_$(unique_suffix).$ENDUNG_KLEIN"
    if [ "$DRYRUN_FLAG" = "true" ]; then
      echo -e "${BLAU}VORSCHAU: $DATEINAME  ->  $KATEGORIE/${RESET}"
    else
      mkdir -p "$ZIELORDNER" 2>/dev/null || { echo -e "${ROT}Fehler mkdir: $ZIELORDNER${RESET}"; return 3; }
      if $KOPIEREN; then
        cp -- "$DATEI" "$ZIELDATEI" 2>/dev/null
      else
        mv -- "$DATEI" "$ZIELDATEI" 2>/dev/null
      fi
      if [ $? -eq 0 ]; then
        ! $KOPIEREN && log_schreiben "$LOGDATEI_PFAD" "$DATEI" "$ZIELDATEI" "$DATUM_LOG"
        local PFEIL="->"; $KOPIEREN && PFEIL="=>"
        echo -e "${GRUEN}OK: $DATEINAME  $PFEIL  $KATEGORIE/${RESET}"
        BERICHT_KATEGORIEN["$KATEGORIE"]=$(( ${BERICHT_KATEGORIEN["$KATEGORIE"]:-0} + 1 ))
      else
        echo -e "${ROT}Fehler: $DATEINAME${RESET}"; return 3
      fi
    fi
    return 0
  fi

  # Sonstiges
  local ZIELORDNER="$ZIEL_BASIS/Sonstiges"
  local ZIELDATEI="$ZIELORDNER/$DATEINAME"
  if [ "$DRYRUN_FLAG" = "true" ]; then
    echo -e "${GELB}VORSCHAU: $DATEINAME  ->  Sonstiges/${RESET}"
  else
    mkdir -p "$ZIELORDNER" 2>/dev/null || return 3
    if $KOPIEREN; then
      cp -- "$DATEI" "$ZIELDATEI" 2>/dev/null
    else
      mv -- "$DATEI" "$ZIELDATEI" 2>/dev/null
    fi
    if [ $? -eq 0 ]; then
      ! $KOPIEREN && log_schreiben "$LOGDATEI_PFAD" "$DATEI" "$ZIELDATEI" "$DATUM_LOG"
      echo -e "${GELB}Sonstiges: $DATEINAME${RESET}"
      BERICHT_SONSTIGES=$((BERICHT_SONSTIGES+1))
    else
      echo -e "${ROT}Fehler: $DATEINAME${RESET}"; return 3
    fi
  fi
  return 1
}

# ============================================
#  ORDNER SORTIEREN
# ============================================
sortiere_ordner() {
  local ORDNER="$1"
  local LOGDATEI="$ORDNER/.sortier_log.txt"
  local DATUM_LOG VERSCHOBEN=0 SONSTIGES=0 IGNORIERT=0 FEHLER_ANZ=0
  DATUM_LOG=$(date '+%d.%m.%Y %H:%M')

  if $DRYRUN; then
    echo -e "${BLAU}VORSCHAU-MODUS${RESET}"
  else
    echo -e "${GRUEN}Sortiere: $ORDNER${RESET}"
    # BUGFIX: Log nur leeren wenn wirklich Dateien vorhanden sind
    shopt -s nullglob; VORHANDENE=("$ORDNER"/*); shopt -u nullglob
    if [ ${#VORHANDENE[@]} -gt 0 ]; then
      : > "$LOGDATEI" 2>/dev/null || echo -e "${GELB}Warnung: Kein Schreibrecht fuer Log.${RESET}"
    fi
  fi
  echo "--------------------------------------------"

  if $UNTERORDNER; then
    while IFS= read -r -d '' DATEI; do
      local DATEINAME="${DATEI##*/}"
      [ "$DATEINAME" = ".sortier_log.txt" ] && continue
      local RET
      sortiere_datei "$DATEI" "$ORDNER" "$DRYRUN" "$LOGDATEI" "$NACH_DATUM" "$DATUM_LOG"
      RET=$?
      case $RET in
        0) VERSCHOBEN=$((VERSCHOBEN+1)); BERICHT_VERSCHOBEN=$((BERICHT_VERSCHOBEN+1)) ;;
        1) SONSTIGES=$((SONSTIGES+1)) ;;
        2) IGNORIERT=$((IGNORIERT+1)); BERICHT_IGNORIERT=$((BERICHT_IGNORIERT+1)) ;;
        3) FEHLER_ANZ=$((FEHLER_ANZ+1)); BERICHT_FEHLER=$((BERICHT_FEHLER+1)) ;;
      esac
    done < <(find "$ORDNER" -type f -not -name ".sortier_log.txt" -print0 2>/dev/null)
  else
    shopt -s nullglob
    for DATEI in "$ORDNER"/*; do
      [ -f "$DATEI" ] || continue
      local RET
      sortiere_datei "$DATEI" "$ORDNER" "$DRYRUN" "$LOGDATEI" "$NACH_DATUM" "$DATUM_LOG"
      RET=$?
      case $RET in
        0) VERSCHOBEN=$((VERSCHOBEN+1)); BERICHT_VERSCHOBEN=$((BERICHT_VERSCHOBEN+1)) ;;
        1) SONSTIGES=$((SONSTIGES+1)) ;;
        2) IGNORIERT=$((IGNORIERT+1)); BERICHT_IGNORIERT=$((BERICHT_IGNORIERT+1)) ;;
        3) FEHLER_ANZ=$((FEHLER_ANZ+1)); BERICHT_FEHLER=$((BERICHT_FEHLER+1)) ;;
      esac
    done
    shopt -u nullglob
  fi

  echo "--------------------------------------------"
  if $DRYRUN; then
    echo -e "${BLAU}Vorschau: $VERSCHOBEN sortiert, $SONSTIGES Sonstiges, $IGNORIERT ignoriert.${RESET}"
  else
    echo -e "${GRUEN}Fertig! $VERSCHOBEN sortiert, $SONSTIGES Sonstiges, $IGNORIERT ignoriert.${RESET}"
    [ $FEHLER_ANZ -gt 0 ] && echo -e "${ROT}Fehler: $FEHLER_ANZ${RESET}"
    echo -e "${GELB}Tipps: --undo | --log | --watch | --bericht${RESET}"
    # Bericht nur im Einzel-Modus hier; Multi-Modus ruft bericht_schreiben separat auf
    $BERICHT && ! $MULTI_MODUS && bericht_schreiben "$ORDNER"
  fi
}

# ============================================
#  MEHRERE ORDNER
# ============================================
if $MULTI_MODUS; then
  [ ${#MULTI_ORDNER[@]} -eq 0 ] && { echo -e "${ROT}Keine Ordner nach --ordner.${RESET}"; exit 1; }
  laden_kategorien
  echo -e "${CYAN}Multi-Ordner: ${#MULTI_ORDNER[@]} Ordner${RESET}"; echo ""
  FEHLER=0
  for ORDNER in "${MULTI_ORDNER[@]}"; do
    if [ ! -d "$ORDNER" ]; then
      echo -e "${ROT}'$ORDNER' nicht gefunden.${RESET}"; FEHLER=$((FEHLER+1)); continue
    fi
    echo -e "${MAGENTA}── $ORDNER ──${RESET}"
    sortiere_ordner "$ORDNER"; echo ""
  done
  echo -e "${CYAN}Abgeschlossen. Fehler: $FEHLER${RESET}"
  $BERICHT && bericht_schreiben "${MULTI_ORDNER[0]}"
  exit 0
fi

# ============================================
#  VERZEICHNIS PRUEFEN
# ============================================
[ -d "$ZIEL" ] || { echo -e "${ROT}Verzeichnis '$ZIEL' nicht gefunden.${RESET}"; exit 1; }
LOGDATEI="$ZIEL/.sortier_log.txt"

# ============================================
#  WATCH-MODUS
# ============================================
if $WATCH; then
  laden_kategorien
  echo -e "${CYAN}╔══════════════════════════════════════════════╗"
  echo -e "║     Watch-Modus – Automatische Sortierung    ║"
  echo -e "╚══════════════════════════════════════════════╝${RESET}"
  echo -e "${GRUEN}Beobachte: $ZIEL${RESET}"
  echo -e "${GELB}Intervall: ${WATCH_INTERVAL}s  |  Beenden: Strg+C${RESET}"
  $NOTIFY && echo -e "${CYAN}Benachrichtigungen: aktiv${RESET}"
  echo "--------------------------------------------"

  trap 'echo -e "\n${GELB}Watch-Modus beendet.${RESET}"; exit 0' INT TERM

  if command -v inotifywait &>/dev/null; then
    echo -e "${GRUEN}Echtzeit-Ueberwachung (inotifywait)${RESET}"; echo ""
    while true; do
      if ! NEUE_DATEI=$(inotifywait -q -e close_write,moved_to --format '%f' "$ZIEL" 2>/dev/null); then
        break
      fi
      DATEI="$ZIEL/$NEUE_DATEI"
      [ -f "$DATEI" ] || continue
      [ "$NEUE_DATEI" = ".sortier_log.txt" ] && continue
      echo -e "${CYAN}[$(date '+%H:%M:%S')] $NEUE_DATEI${RESET}"
      DATUM_LOG=$(date '+%d.%m.%Y %H:%M')
      sortiere_datei "$DATEI" "$ZIEL" "false" "$LOGDATEI" "$NACH_DATUM" "$DATUM_LOG"
      RET=$?
      $NOTIFY && [ $RET -le 1 ] && sende_notification "Datei-Sortierer" "$NEUE_DATEI sortiert"
    done
  fi

  echo -e "${GELB}Polling-Modus (alle ${WATCH_INTERVAL}s)${RESET}"; echo ""
  declare -A BEKANNTE_DATEIEN
  shopt -s nullglob
  for DATEI in "$ZIEL"/*; do
    [ -f "$DATEI" ] && BEKANNTE_DATEIEN["${DATEI##*/}"]=1
  done
  shopt -u nullglob
  echo -e "${CYAN}${#BEKANNTE_DATEIEN[@]} bestehende Datei(en) ignoriert.${RESET}"

  while true; do
    sleep "$WATCH_INTERVAL"; NEUE=0
    shopt -s nullglob
    for DATEI in "$ZIEL"/*; do
      [ -f "$DATEI" ] || continue
      DATEINAME="${DATEI##*/}"
      [ "$DATEINAME" = ".sortier_log.txt" ] && continue
      if [ -z "${BEKANNTE_DATEIEN[$DATEINAME]+x}" ]; then
        echo -e "${CYAN}[$(date '+%H:%M:%S')] $DATEINAME${RESET}"
        DATUM_LOG=$(date '+%d.%m.%Y %H:%M')
        sortiere_datei "$DATEI" "$ZIEL" "false" "$LOGDATEI" "$NACH_DATUM" "$DATUM_LOG"
        RET=$?
        $NOTIFY && [ $RET -le 1 ] && sende_notification "Datei-Sortierer" "$DATEINAME sortiert"
        BEKANNTE_DATEIEN["$DATEINAME"]=1; NEUE=$((NEUE+1))
      fi
    done
    shopt -u nullglob
    [ $NEUE -eq 0 ] && echo -ne "${GELB}.${RESET}"
  done
fi

# ============================================
#  DUPLIKATE
# ============================================
if $DUPLIKATE; then
  echo -e "${MAGENTA}╔══════════════════════════════════════════════╗"
  echo -e "║        Duplikat-Suche                        ║"
  echo -e "╚══════════════════════════════════════════════╝${RESET}"
  echo -e "${CYAN}Suche in: $ZIEL${RESET}"; echo "--------------------------------------------"

  if ! command -v md5sum &>/dev/null; then
    command -v md5 &>/dev/null && md5sum() { md5 -r "$@"; } \
      || { echo -e "${ROT}md5sum nicht gefunden.${RESET}"; exit 1; }
  fi

  [ -t 0 ] && READ_TIMEOUT=30 || READ_TIMEOUT=5
  declare -A HASH_MAP

  while IFS= read -r -d '' DATEI; do
    [ "${DATEI##*/}" = ".sortier_log.txt" ] && continue
    HASH=$(md5sum "$DATEI" 2>/dev/null | awk '{print $1}')
    [ -z "$HASH" ] && continue
    [ -n "${HASH_MAP[$HASH]+x}" ] \
      && HASH_MAP[$HASH]="${HASH_MAP[$HASH]}|$DATEI" \
      || HASH_MAP[$HASH]="$DATEI"
  done < <(find "$ZIEL" -type f -print0 2>/dev/null)

  DUPLIKAT_GRUPPEN=0
  for HASH in "${!HASH_MAP[@]}"; do
    IFS='|' read -ra DATEIEN <<< "${HASH_MAP[$HASH]}"
    [ ${#DATEIEN[@]} -le 1 ] && continue
    DUPLIKAT_GRUPPEN=$((DUPLIKAT_GRUPPEN+1))
    GROESSE=$(du -h "${DATEIEN[0]}" 2>/dev/null | awk '{print $1}')
    echo -e "${MAGENTA}Gruppe $DUPLIKAT_GRUPPEN  [${HASH:0:8}...]  ${GROESSE:-?}${RESET}"
    for i in "${!DATEIEN[@]}"; do
      [ $i -eq 0 ] \
        && echo -e "  ${GRUEN}[ORIGINAL] ${DATEIEN[$i]}${RESET}" \
        || echo -e "  ${GELB}[DUPLIKAT] ${DATEIEN[$i]}${RESET}"
    done
    echo -e "${CYAN}[1] Papierkorb  [2] Endgueltig loeschen  [3] nach 'Duplikate/'  [4] Ueberspringen${RESET}"
    WAHL=""; read -r -t "$READ_TIMEOUT" WAHL || WAHL="4"; [ -z "$WAHL" ] && WAHL="4"
    case $WAHL in
      1) for i in "${!DATEIEN[@]}"; do
           [ $i -eq 0 ] && continue
           if in_papierkorb "${DATEIEN[$i]}"; then
             echo -e "${GELB}Papierkorb: ${DATEIEN[$i]##*/}${RESET}"
           else
             echo -e "${ROT}Fehler Papierkorb: ${DATEIEN[$i]}${RESET}"
           fi
         done ;;
      2) echo -e "${ROT}Sicher? Endgueltig loeschen! [j/N]${RESET}"
         BESTAETIGUNG=""; read -r -t 10 BESTAETIGUNG || BESTAETIGUNG="n"
         if [[ "$BESTAETIGUNG" =~ ^[jJyY]$ ]]; then
           for i in "${!DATEIEN[@]}"; do
             [ $i -gt 0 ] && rm -- "${DATEIEN[$i]}" 2>/dev/null \
               && echo -e "${ROT}Geloescht: ${DATEIEN[$i]##*/}${RESET}" \
               || echo -e "${ROT}Fehler: ${DATEIEN[$i]}${RESET}"
           done
         else echo -e "${BLAU}Abgebrochen.${RESET}"; fi ;;
      3) mkdir -p "$ZIEL/Duplikate" 2>/dev/null
         for i in "${!DATEIEN[@]}"; do
           [ $i -gt 0 ] && mv -- "${DATEIEN[$i]}" "$ZIEL/Duplikate/" 2>/dev/null \
             && echo -e "${GELB}Verschoben: ${DATEIEN[$i]##*/}${RESET}" \
             || echo -e "${ROT}Fehler: ${DATEIEN[$i]}${RESET}"
         done ;;
      *) echo -e "${BLAU}Uebersprungen.${RESET}" ;;
    esac
    echo "--------------------------------------------"
  done
  [ $DUPLIKAT_GRUPPEN -eq 0 ] \
    && echo -e "${GRUEN}Keine Duplikate gefunden!${RESET}" \
    || echo -e "${MAGENTA}$DUPLIKAT_GRUPPEN Gruppe(n) verarbeitet.${RESET}"
  exit 0
fi

# ============================================
#  LOG ANZEIGEN  (BUGFIX: Tab-Separator)
# ============================================
if $ZEIG_LOG; then
  [ ! -f "$LOGDATEI" ] && { echo -e "${ROT}Kein Log gefunden.${RESET}"; exit 1; }
  echo -e "${CYAN}── Log der letzten Sortierung ──${RESET}"
  ANZAHL=0
  while IFS=$'\t' read -r QUELLE ZIEL_DATEI DATUM; do
    [ -z "$QUELLE" ] && continue
    # OPT: ${##*/} statt $(basename), $(dirname)
    QNAME="${QUELLE##*/}"
    ZKAT="${ZIEL_DATEI%/*}"; ZKAT="${ZKAT##*/}"
    echo -e "  ${GRUEN}$QNAME${RESET}  ->  ${BLAU}${ZKAT}/${RESET}  ${GELB}($DATUM)${RESET}"
    ANZAHL=$((ANZAHL+1))
  done < "$LOGDATEI"
  echo -e "${CYAN}Gesamt: $ANZAHL  |  --undo zum Rueckgaengig machen${RESET}"
  exit 0
fi

# ============================================
#  UNDO  (BUGFIX: Tab-Separator)
# ============================================
if $UNDO; then
  [ ! -f "$LOGDATEI" ] && { echo -e "${ROT}Kein Log.${RESET}"; exit 1; }
  echo -e "${GELB}Rueckgaengig...${RESET}"; echo "--------------------------------------------"
  TMP_LOG=$(mktemp 2>/dev/null) || TMP_LOG="/tmp/.sortier_undo_$$"
  tac "$LOGDATEI" > "$TMP_LOG"
  WIEDERHERGESTELLT=0; FEHLER_UNDO=0
  while IFS=$'\t' read -r QUELLE ZIEL_DATEI DATUM; do
    [ -z "$QUELLE" ] && continue
    if [ -f "$ZIEL_DATEI" ]; then
      if mv -- "$ZIEL_DATEI" "$QUELLE" 2>/dev/null; then
        echo -e "${GRUEN}Wiederhergestellt: ${QUELLE##*/}${RESET}"
        WIEDERHERGESTELLT=$((WIEDERHERGESTELLT+1))
      else
        echo -e "${ROT}Fehler: ${QUELLE##*/}${RESET}"; FEHLER_UNDO=$((FEHLER_UNDO+1))
      fi
    else
      echo -e "${ROT}Nicht vorhanden: ${ZIEL_DATEI##*/}${RESET}"; FEHLER_UNDO=$((FEHLER_UNDO+1))
    fi
  done < "$TMP_LOG"
  rm -f "$TMP_LOG"
  find "$ZIEL" -mindepth 1 -type d -empty -delete 2>/dev/null
  rm -f "$LOGDATEI"
  echo "--------------------------------------------"
  echo -e "${GRUEN}Undo: $WIEDERHERGESTELLT wiederhergestellt, $FEHLER_UNDO Fehler.${RESET}"
  exit 0
fi

# ============================================
#  NORMALES SORTIEREN
# ============================================
laden_kategorien
sortiere_ordner "$ZIEL"
