#!/bin/bash

# ============================================
#  Datei-Sortierer v6.1
#  Stabilitaetsfixes:
#  - mv/mkdir mit Fehlerbehandlung
#  - macOS-kompatibler stat/date Fallback
#  - watch-interval Validierung
#  - md5sum Fehlerbehandlung
#  - read-Timeout bei Duplikaten
#  - Pipe-sichere Log-Felder (kein | in Pfaden)
#  - Log-Schreibrecht pruefen
#  - Undo robuster (keine Subshell-Probleme)
# ============================================

# set -o pipefail ist deaktiviert: bricht 'while read < file' (exit 1 am EOF)
# stattdessen: kritische Befehle einzeln prüfen

# --- tac: macOS Fallback ---
if ! command -v tac &>/dev/null; then
  tac() { tail -r -- "$@"; }
fi

# --- Farben ---
ROT='\033[0;31m'
GRUEN='\033[0;32m'
GELB='\033[1;33m'
BLAU='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
RESET='\033[0m'

# --- Betriebssystem erkennen ---
OS_TYP="linux"
if [[ "$OSTYPE" == "darwin"* ]]; then
  OS_TYP="macos"
fi

# --- Monatsnamen ---
monat_name() {
  case $1 in
    01) echo "Januar" ;; 02) echo "Februar" ;; 03) echo "Maerz" ;;
    04) echo "April" ;; 05) echo "Mai" ;; 06) echo "Juni" ;;
    07) echo "Juli" ;; 08) echo "August" ;; 09) echo "September" ;;
    10) echo "Oktober" ;; 11) echo "November" ;; 12) echo "Dezember" ;;
    *) echo "Unbekannt" ;;
  esac
}

# --- Datei-Zeitstempel holen (Linux + macOS) ---
get_timestamp() {
  local DATEI="$1"
  local TS=""
  if [ "$OS_TYP" = "macos" ]; then
    # macOS: stat -f "%B" = Geburtsdatum, "%m" = Änderungsdatum
    TS=$(stat -f "%B" "$DATEI" 2>/dev/null)
    [ -z "$TS" ] || [ "$TS" = "0" ] && TS=$(stat -f "%m" "$DATEI" 2>/dev/null)
  else
    # Linux: stat --format "%W" = Geburtsdatum
    TS=$(stat --format="%W" "$DATEI" 2>/dev/null)
    [ -z "$TS" ] || [ "$TS" = "0" ] && TS=$(stat --format="%Y" "$DATEI" 2>/dev/null)
  fi
  echo "${TS:-0}"
}

# --- Datum aus Timestamp (Linux + macOS) ---
datum_aus_ts() {
  local TS="$1" FORMAT="$2"
  if [ "$OS_TYP" = "macos" ]; then
    date -r "$TS" "$FORMAT" 2>/dev/null
  else
    date -d "@$TS" "$FORMAT" 2>/dev/null
  fi
}

# --- Eindeutigen Suffix erzeugen (kein %N auf macOS) ---
unique_suffix() {
  echo "$(date +%s)_$$_$RANDOM"
}

# --- Hilfe ---
hilfe() {
  echo -e "${CYAN}"
  echo "╔══════════════════════════════════════════════╗"
  echo "║         Datei-Sortierer v6.1                 ║"
  echo "╚══════════════════════════════════════════════╝"
  echo -e "${RESET}"
  echo "Verwendung:"
  echo "  ./datei_sortieren.sh [ORDNER] [OPTIONEN]"
  echo ""
  echo "Basis-Optionen:"
  echo "  --dry-run         Vorschau (nichts wird verschoben)"
  echo "  --undo            Letzte Sortierung rueckgaengig machen"
  echo "  --log             Log der letzten Sortierung anzeigen"
  echo "  --nach-datum      Nach Erstelldatum (Jahr/Monat) sortieren"
  echo "  --duplikate       Duplikate suchen und anzeigen"
  echo "  --config DATEI    Eigene Konfigurationsdatei angeben"
  echo "  --help            Diese Hilfe anzeigen"
  echo ""
  echo "v6.0+ Optionen:"
  echo "  --watch           Ordner beobachten & automatisch sortieren"
  echo "  --watch-interval N  Intervall in Sekunden (Standard: 10, min: 1)"
  echo "  --profil NAME     Profil laden (z.B. 'fotos', 'buero')"
  echo "  --profile-list    Alle verfuegbaren Profile anzeigen"
  echo "  --ignore DATEI    Ignorier-Liste angeben (Standard: ignore.txt)"
  echo "  --ordner A B C    Mehrere Ordner gleichzeitig sortieren"
  echo ""
  echo "Beispiele:"
  echo "  ./datei_sortieren.sh ~/Downloads"
  echo "  ./datei_sortieren.sh ~/Downloads --dry-run"
  echo "  ./datei_sortieren.sh ~/Downloads --watch --watch-interval 30"
  echo "  ./datei_sortieren.sh --profil fotos ~/Fotos"
  echo "  ./datei_sortieren.sh --profile-list"
  echo "  ./datei_sortieren.sh --ordner ~/Downloads ~/Desktop"
  exit 0
}

# ============================================
#  STANDARDWERTE
# ============================================
ZIEL="."
DRYRUN=false
UNDO=false
ZEIG_LOG=false
NACH_DATUM=false
DUPLIKATE=false
WATCH=false
WATCH_INTERVAL=10
PROFIL=""
PROFIL_LIST=false
BASIS_DIR="$(cd "$(dirname "$0")" && pwd)"  # FIX: absoluter Pfad
CONFIGDATEI="$BASIS_DIR/config.txt"
IGNOREDATEI="$BASIS_DIR/ignore.txt"
MULTI_ORDNER=()
MULTI_MODUS=false

# ============================================
#  ARGUMENTE AUSWERTEN
# ============================================
SKIP_NEXT=""
i=0
ARGS=("$@")
while [ $i -lt ${#ARGS[@]} ]; do
  ARG="${ARGS[$i]}"

  if [ -n "$SKIP_NEXT" ]; then
    case $SKIP_NEXT in
      config)   CONFIGDATEI="$ARG" ;;
      ignore)   IGNOREDATEI="$ARG" ;;
      profil)   PROFIL="$ARG" ;;
      interval)
        # FIX: Validierung des Intervalls
        if ! [[ "$ARG" =~ ^[0-9]+$ ]] || [ "$ARG" -lt 1 ]; then
          echo -e "${ROT}Fehler: --watch-interval muss eine positive Zahl sein (z.B. 10).${RESET}"
          exit 1
        fi
        WATCH_INTERVAL="$ARG"
        ;;
    esac
    SKIP_NEXT=""
    i=$((i+1)); continue
  fi

  case $ARG in
    --dry-run)         DRYRUN=true ;;
    --undo)            UNDO=true ;;
    --log)             ZEIG_LOG=true ;;
    --nach-datum)      NACH_DATUM=true ;;
    --duplikate)       DUPLIKATE=true ;;
    --watch)           WATCH=true ;;
    --watch-interval)  SKIP_NEXT="interval" ;;
    --profile-list)    PROFIL_LIST=true ;;
    --profil)          SKIP_NEXT="profil" ;;
    --config)          SKIP_NEXT="config" ;;
    --ignore)          SKIP_NEXT="ignore" ;;
    --help)            hilfe ;;
    --ordner)
      MULTI_MODUS=true
      i=$((i+1))
      while [ $i -lt ${#ARGS[@]} ]; do
        NAECHSTER="${ARGS[$i]}"
        if [[ "$NAECHSTER" == --* ]]; then
          i=$((i-1)); break
        fi
        MULTI_ORDNER+=("$NAECHSTER")
        i=$((i+1))
      done
      ;;
    *)
      if [[ "$ARG" != --* ]]; then
        if [ -d "$ARG" ]; then
          ZIEL="$ARG"
        else
          echo -e "${ROT}Fehler: Ordner '$ARG' nicht gefunden.${RESET}"
          echo -e "${GELB}Tipp: Nutze --help fuer alle Optionen.${RESET}"
          exit 1
        fi
      fi
      ;;
  esac
  i=$((i+1))
done

# ============================================
#  PROFIL LADEN
# ============================================
profil_laden() {
  local NAME="$1"
  local PFAD="$BASIS_DIR/profile/${NAME}.txt"
  if [ -f "$PFAD" ]; then
    CONFIGDATEI="$PFAD"
    echo -e "${CYAN}Profil geladen: $NAME${RESET}"
    return 0
  else
    echo -e "${ROT}Profil '$NAME' nicht gefunden: $PFAD${RESET}"
    echo -e "${GELB}Tipp: Nutze --profile-list fuer alle Profile.${RESET}"
    exit 1
  fi
}

# ============================================
#  PROFILE ANZEIGEN
# ============================================
if $PROFIL_LIST; then
  PROFIL_DIR="$BASIS_DIR/profile"
  echo -e "${CYAN}Verfuegbare Profile:${RESET}"
  echo "--------------------------------------------"
  if [ -d "$PROFIL_DIR" ]; then
    GEFUNDEN=0
    for P in "$PROFIL_DIR"/*.txt; do
      [ -f "$P" ] || continue
      NAME=$(basename "$P" .txt)
      ANZAHL=$(grep -c "=" "$P" 2>/dev/null || echo "0")
      echo -e "  ${GRUEN}$NAME${RESET}  ($ANZAHL Kategorien)"
      GEFUNDEN=$((GEFUNDEN+1))
    done
    [ $GEFUNDEN -eq 0 ] && echo -e "  ${GELB}Keine Profile gefunden in: $PROFIL_DIR${RESET}"
  else
    echo -e "  ${GELB}Profil-Ordner nicht vorhanden: $PROFIL_DIR${RESET}"
  fi
  echo ""
  echo -e "${GELB}Profil verwenden: --profil NAME${RESET}"
  exit 0
fi

[ -n "$PROFIL" ] && profil_laden "$PROFIL"

# ============================================
#  IGNORIER-LISTE LADEN
# ============================================
IGNORE_LISTE=()
if [ -f "$IGNOREDATEI" ]; then
  while IFS= read -r ZEILE; do
    [[ "$ZEILE" =~ ^#.*$ ]] && continue
    [[ -z "${ZEILE// }" ]] && continue   # FIX: auch Leerzeilen überspringen
    IGNORE_LISTE+=("$ZEILE")
  done < "$IGNOREDATEI"
  echo -e "${CYAN}Ignorier-Liste: ${#IGNORE_LISTE[@]} Eintraege${RESET}"
fi

ist_ignoriert() {
  local DATEINAME="$1"
  for MUSTER in "${IGNORE_LISTE[@]}"; do
    [ "$DATEINAME" = "$MUSTER" ] && return 0
    [[ "$DATEINAME" == $MUSTER ]] && return 0
  done
  return 1
}

# ============================================
#  KATEGORIEN LADEN
# ============================================
laden_kategorien() {
  declare -gA KATEGORIEN
  if [ -f "$CONFIGDATEI" ]; then
    echo -e "${CYAN}Konfiguration: $(basename "$CONFIGDATEI")${RESET}"
    while IFS='=' read -r KAT ENDUNGEN; do
      [[ "$KAT" =~ ^#.*$ ]] && continue
      [[ -z "${KAT// }" ]] && continue
      KAT="${KAT// /}"   # Leerzeichen am Rand entfernen
      [ -n "$KAT" ] && KATEGORIEN["$KAT"]="$ENDUNGEN"
    done < "$CONFIGDATEI"
    if [ ${#KATEGORIEN[@]} -eq 0 ]; then
      echo -e "${GELB}Warnung: config.txt ist leer – nutze Standard-Kategorien.${RESET}"
      _lade_standard_kategorien
    fi
  else
    echo -e "${GELB}Keine config.txt – nutze Standard-Kategorien.${RESET}"
    _lade_standard_kategorien
  fi
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
#  LOG SICHER SCHREIBEN
# ============================================
log_schreiben() {
  local LOGDATEI="$1" QUELLE="$2" ZIEL_DATEI="$3" DATUM="$4"
  # FIX: Pipe-Zeichen in Pfaden ersetzen damit Log-Format nicht bricht
  local Q="${QUELLE//|/___}"
  local Z="${ZIEL_DATEI//|/___}"
  echo "${Q}|${Z}|${DATUM}" >> "$LOGDATEI" 2>/dev/null
}

# ============================================
#  EINE DATEI SORTIEREN (Kernfunktion)
# ============================================
sortiere_datei() {
  local DATEI="$1"
  local ZIELORDNER_BASIS="$2"
  local DRYRUN_FLAG="$3"
  local LOGDATEI_PFAD="$4"
  local DATUM_FLAG="$5"
  local DATUM_LOG="$6"

  # FIX: Sicherstellen dass Datei noch existiert (Watch-Modus Timing)
  [ -f "$DATEI" ] || return 2

  local DATEINAME
  DATEINAME=$(basename "$DATEI")

  # Systemdateien & versteckte Dateien ueberspringen
  [ "$DATEINAME" = ".sortier_log.txt" ] && return 2
  [[ "$DATEINAME" == .* ]] && return 2

  # Ignorier-Liste pruefen
  if ist_ignoriert "$DATEINAME"; then
    echo -e "${GELB}IGNORIERT: $DATEINAME${RESET}"
    return 2
  fi

  # Datum-Modus
  if [ "$DATUM_FLAG" = "true" ]; then
    local TS JAHR MONAT_NR MONAT
    TS=$(get_timestamp "$DATEI")
    JAHR=$(datum_aus_ts "$TS" '+%Y')
    MONAT_NR=$(datum_aus_ts "$TS" '+%m')
    MONAT=$(monat_name "$MONAT_NR")

    # Fallback falls Datum-Abruf fehlschlug
    JAHR="${JAHR:-$(date '+%Y')}"
    MONAT="${MONAT:-Unbekannt}"

    local ZIELORDNER="$ZIELORDNER_BASIS/$JAHR/$MONAT"
    local ZIELDATEI="$ZIELORDNER/$DATEINAME"

    if [ -e "$ZIELDATEI" ]; then
      local BASE="${DATEINAME%.*}" EXT="${DATEINAME##*.}"
      ZIELDATEI="$ZIELORDNER/${BASE}_$(unique_suffix).$EXT"
    fi

    if [ "$DRYRUN_FLAG" = "true" ]; then
      echo -e "${BLAU}VORSCHAU: $DATEINAME  ->  $JAHR/$MONAT/${RESET}"
    else
      # FIX: mkdir und mv mit Fehlerprüfung
      if ! mkdir -p "$ZIELORDNER" 2>/dev/null; then
        echo -e "${ROT}Fehler: Kann Ordner nicht erstellen: $ZIELORDNER${RESET}"
        return 3
      fi
      if mv "$DATEI" "$ZIELDATEI" 2>/dev/null; then
        log_schreiben "$LOGDATEI_PFAD" "$DATEI" "$ZIELDATEI" "$DATUM_LOG"
        echo -e "${GRUEN}OK: $DATEINAME  ->  $JAHR/$MONAT/${RESET}"
      else
        echo -e "${ROT}Fehler beim Verschieben: $DATEINAME${RESET}"
        return 3
      fi
    fi
    return 0
  fi

  # Dateityp-Modus
  local ENDUNG ENDUNG_KLEIN GEFUNDEN=false

  # FIX: Dateien ohne Erweiterung direkt zu Sonstiges
  if [[ "$DATEINAME" != *.* ]]; then
    ENDUNG_KLEIN=""
  else
    ENDUNG="${DATEINAME##*.}"
    ENDUNG_KLEIN=$(echo "$ENDUNG" | tr '[:upper:]' '[:lower:]')
  fi

  if [ -n "$ENDUNG_KLEIN" ]; then
    for KATEGORIE in "${!KATEGORIEN[@]}"; do
      for EXT in ${KATEGORIEN[$KATEGORIE]}; do
        if [ "$ENDUNG_KLEIN" = "$EXT" ]; then
          local ZIELORDNER="$ZIELORDNER_BASIS/$KATEGORIE"
          local ZIELDATEI="$ZIELORDNER/$DATEINAME"
          if [ -e "$ZIELDATEI" ]; then
            local BASE="${DATEINAME%.*}"
            ZIELDATEI="$ZIELORDNER/${BASE}_$(unique_suffix).$ENDUNG_KLEIN"
          fi
          if [ "$DRYRUN_FLAG" = "true" ]; then
            echo -e "${BLAU}VORSCHAU: $DATEINAME  ->  $KATEGORIE/${RESET}"
          else
            # FIX: mkdir und mv mit Fehlerprüfung
            if ! mkdir -p "$ZIELORDNER" 2>/dev/null; then
              echo -e "${ROT}Fehler: Kann Ordner nicht erstellen: $ZIELORDNER${RESET}"
              return 3
            fi
            if mv "$DATEI" "$ZIELDATEI" 2>/dev/null; then
              log_schreiben "$LOGDATEI_PFAD" "$DATEI" "$ZIELDATEI" "$DATUM_LOG"
              echo -e "${GRUEN}OK: $DATEINAME  ->  $KATEGORIE/${RESET}"
            else
              echo -e "${ROT}Fehler beim Verschieben: $DATEINAME${RESET}"
              return 3
            fi
          fi
          GEFUNDEN=true
          break
        fi
      done
      $GEFUNDEN && break
    done
  fi

  # Sonstiges
  if ! $GEFUNDEN; then
    local ZIELORDNER="$ZIELORDNER_BASIS/Sonstiges"
    local ZIELDATEI="$ZIELORDNER/$DATEINAME"
    if [ "$DRYRUN_FLAG" = "true" ]; then
      echo -e "${GELB}VORSCHAU: $DATEINAME  ->  Sonstiges/${RESET}"
    else
      if ! mkdir -p "$ZIELORDNER" 2>/dev/null; then
        echo -e "${ROT}Fehler: Kann 'Sonstiges' nicht erstellen.${RESET}"
        return 3
      fi
      if mv "$DATEI" "$ZIELDATEI" 2>/dev/null; then
        log_schreiben "$LOGDATEI_PFAD" "$DATEI" "$ZIELDATEI" "$DATUM_LOG"
        echo -e "${GELB}Sonstiges: $DATEINAME  ->  Sonstiges/${RESET}"
      else
        echo -e "${ROT}Fehler beim Verschieben: $DATEINAME${RESET}"
        return 3
      fi
    fi
    return 1
  fi
  return 0
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
    # FIX: Pruefen ob Log geschrieben werden kann
    if ! : > "$LOGDATEI" 2>/dev/null; then
      echo -e "${ROT}Fehler: Kein Schreibrecht fuer Log: $LOGDATEI${RESET}"
      echo -e "${GELB}Sortierung wird trotzdem fortgesetzt (kein Undo moeglich).${RESET}"
    fi
  fi
  echo "--------------------------------------------"

  # FIX: nullglob verhindert Iteration über literal '*' wenn Ordner leer ist
  shopt -s nullglob
  for DATEI in "$ORDNER"/*; do
    shopt -u nullglob
    [ -f "$DATEI" ] || continue
    local RET
    sortiere_datei "$DATEI" "$ORDNER" "$DRYRUN" "$LOGDATEI" "$NACH_DATUM" "$DATUM_LOG"
    RET=$?
    case $RET in
      0) VERSCHOBEN=$((VERSCHOBEN + 1)) ;;
      1) SONSTIGES=$((SONSTIGES + 1)) ;;
      2) IGNORIERT=$((IGNORIERT + 1)) ;;
      3) FEHLER_ANZ=$((FEHLER_ANZ + 1)) ;;
    esac
  done

  echo "--------------------------------------------"
  if $DRYRUN; then
    echo -e "${BLAU}Vorschau: $VERSCHOBEN sortiert, $SONSTIGES Sonstiges, $IGNORIERT ignoriert.${RESET}"
  else
    echo -e "${GRUEN}Fertig! $VERSCHOBEN sortiert, $SONSTIGES Sonstiges, $IGNORIERT ignoriert.${RESET}"
    [ $FEHLER_ANZ -gt 0 ] && echo -e "${ROT}Fehler: $FEHLER_ANZ Datei(en) konnten nicht verschoben werden.${RESET}"
    echo -e "${GELB}Tipps: --undo | --log | --watch | --profil NAME${RESET}"
  fi
}

# ============================================
#  MEHRERE ORDNER
# ============================================
if $MULTI_MODUS; then
  if [ ${#MULTI_ORDNER[@]} -eq 0 ]; then
    echo -e "${ROT}Fehler: Keine Ordner nach --ordner angegeben.${RESET}"
    exit 1
  fi
  laden_kategorien
  echo -e "${CYAN}╔══════════════════════════════════════════════╗"
  echo -e "║     Multi-Ordner Sortierung                  ║"
  echo -e "╚══════════════════════════════════════════════╝${RESET}"
  echo -e "${CYAN}${#MULTI_ORDNER[@]} Ordner werden verarbeitet...${RESET}"
  echo ""
  FEHLER=0
  for ORDNER in "${MULTI_ORDNER[@]}"; do
    if [ ! -d "$ORDNER" ]; then
      echo -e "${ROT}Fehler: '$ORDNER' nicht gefunden – wird uebersprungen.${RESET}"
      FEHLER=$((FEHLER+1))
      continue
    fi
    echo -e "${MAGENTA}── $ORDNER ──${RESET}"
    sortiere_ordner "$ORDNER"
    echo ""
  done
  echo -e "${CYAN}Abgeschlossen. Fehler: $FEHLER${RESET}"
  exit 0
fi

# ============================================
#  VERZEICHNIS PRUEFEN
# ============================================
if [ ! -d "$ZIEL" ]; then
  echo -e "${ROT}Verzeichnis '$ZIEL' nicht gefunden.${RESET}"
  exit 1
fi

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
  echo "--------------------------------------------"

  trap 'echo -e "\n${GELB}Watch-Modus beendet.${RESET}"; exit 0' INT TERM

  if command -v inotifywait &>/dev/null; then
    echo -e "${GRUEN}Echtzeit-Ueberwachung aktiv (inotifywait)${RESET}"
    echo ""
    # FIX: Subshell-Trap Problem – inotifywait direkt ohne Pipe
    while true; do
      NEUE_DATEI=$(inotifywait -q -e close_write,moved_to \
                    --format '%f' "$ZIEL" 2>/dev/null)
      [ $? -ne 0 ] && break   # inotifywait Fehler → Polling-Fallback
      DATEI="$ZIEL/$NEUE_DATEI"
      [ -f "$DATEI" ] || continue
      [ "$NEUE_DATEI" = ".sortier_log.txt" ] && continue
      echo -e "${CYAN}[$(date '+%H:%M:%S')] Neue Datei: $NEUE_DATEI${RESET}"
      DATUM_LOG=$(date '+%d.%m.%Y %H:%M')
      sortiere_datei "$DATEI" "$ZIEL" "false" "$LOGDATEI" "$NACH_DATUM" "$DATUM_LOG"
    done
  fi

  # Polling-Modus (Fallback oder wenn inotifywait nicht verfuegbar)
  echo -e "${GELB}Polling-Modus aktiv (alle ${WATCH_INTERVAL}s)${RESET}"
  echo -e "${GELB}Tipp: 'sudo apt install inotify-tools' fuer Echtzeit.${RESET}"
  echo ""

  declare -A BEKANNTE_DATEIEN
  shopt -s nullglob
  for DATEI in "$ZIEL"/*; do
    shopt -u nullglob
    [ -f "$DATEI" ] && BEKANNTE_DATEIEN["$(basename "$DATEI")"]=1
  done
  shopt -u nullglob 2>/dev/null || true
  echo -e "${CYAN}${#BEKANNTE_DATEIEN[@]} bestehende Datei(en) werden ignoriert.${RESET}"

  while true; do
    sleep "$WATCH_INTERVAL"
    NEUE=0
    shopt -s nullglob
    for DATEI in "$ZIEL"/*; do
      shopt -u nullglob
      [ -f "$DATEI" ] || continue
      DATEINAME=$(basename "$DATEI")
      [ "$DATEINAME" = ".sortier_log.txt" ] && continue
      if [ -z "${BEKANNTE_DATEIEN[$DATEINAME]+gesetzt}" ]; then
        echo -e "${CYAN}[$(date '+%H:%M:%S')] Neue Datei: $DATEINAME${RESET}"
        DATUM_LOG=$(date '+%d.%m.%Y %H:%M')
        sortiere_datei "$DATEI" "$ZIEL" "false" "$LOGDATEI" "$NACH_DATUM" "$DATUM_LOG"
        BEKANNTE_DATEIEN["$DATEINAME"]=1
        NEUE=$((NEUE+1))
      fi
    done
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
  echo -e "${CYAN}Suche in: $ZIEL${RESET}"
  echo "--------------------------------------------"

  if ! command -v md5sum &>/dev/null; then
    # FIX: macOS hat md5, nicht md5sum
    if command -v md5 &>/dev/null; then
      md5sum() { md5 -r "$@"; }
    else
      echo -e "${ROT}md5sum/md5 nicht gefunden.${RESET}"; exit 1
    fi
  fi

  # FIX: Timeout fuer read bestimmen (TTY-Check)
  if [ -t 0 ]; then
    READ_TIMEOUT=30
  else
    READ_TIMEOUT=5   # Kurzer Timeout wenn kein TTY (z.B. GUI-Aufruf)
  fi

  declare -A HASH_MAP
  while IFS= read -r -d '' DATEI; do
    [ "$(basename "$DATEI")" = ".sortier_log.txt" ] && continue
    # FIX: md5sum Fehler bei nicht-lesbaren Dateien abfangen
    HASH=$(md5sum "$DATEI" 2>/dev/null | awk '{print $1}')
    [ -z "$HASH" ] && continue   # Nicht-lesbare Datei -> überspringen
    if [ -n "${HASH_MAP[$HASH]+gesetzt}" ]; then
      HASH_MAP[$HASH]="${HASH_MAP[$HASH]}|$DATEI"
    else
      HASH_MAP[$HASH]="$DATEI"
    fi
  done < <(find "$ZIEL" -type f -print0 2>/dev/null)

  DUPLIKAT_GRUPPEN=0
  for HASH in "${!HASH_MAP[@]}"; do
    IFS='|' read -ra DATEIEN <<< "${HASH_MAP[$HASH]}"
    if [ ${#DATEIEN[@]} -gt 1 ]; then
      DUPLIKAT_GRUPPEN=$((DUPLIKAT_GRUPPEN+1))
      GROESSE=$(du -h "${DATEIEN[0]}" 2>/dev/null | awk '{print $1}')
      echo -e "${MAGENTA}Gruppe $DUPLIKAT_GRUPPEN  [${HASH:0:8}...]  ${GROESSE:-?}${RESET}"
      for i in "${!DATEIEN[@]}"; do
        [ $i -eq 0 ] \
          && echo -e "  ${GRUEN}[ORIGINAL] ${DATEIEN[$i]}${RESET}" \
          || echo -e "  ${GELB}[DUPLIKAT] ${DATEIEN[$i]}${RESET}"
      done
      echo -e "${CYAN}[1] Loeschen  [2] nach 'Duplikate/' verschieben  [3] Ueberspringen${RESET}"
      # FIX: Timeout damit Script nicht ewig haengt (z.B. GUI-Aufruf)
      WAHL=""
      read -r -t "$READ_TIMEOUT" WAHL || WAHL="3"
      [ -z "$WAHL" ] && WAHL="3"
      case $WAHL in
        1) for i in "${!DATEIEN[@]}"; do
             if [ $i -gt 0 ]; then
               rm -- "${DATEIEN[$i]}" 2>/dev/null \
                 && echo -e "${ROT}Geloescht: ${DATEIEN[$i]}${RESET}" \
                 || echo -e "${ROT}Fehler beim Loeschen: ${DATEIEN[$i]}${RESET}"
             fi
           done ;;
        2) mkdir -p "$ZIEL/Duplikate" 2>/dev/null
           for i in "${!DATEIEN[@]}"; do
             if [ $i -gt 0 ]; then
               mv -- "${DATEIEN[$i]}" "$ZIEL/Duplikate/" 2>/dev/null \
                 && echo -e "${GELB}Verschoben: $(basename "${DATEIEN[$i]}")${RESET}" \
                 || echo -e "${ROT}Fehler beim Verschieben: ${DATEIEN[$i]}${RESET}"
             fi
           done ;;
        *) echo -e "${BLAU}Uebersprungen.${RESET}" ;;
      esac
      echo "--------------------------------------------"
    fi
  done
  [ $DUPLIKAT_GRUPPEN -eq 0 ] \
    && echo -e "${GRUEN}Keine Duplikate gefunden!${RESET}" \
    || echo -e "${MAGENTA}$DUPLIKAT_GRUPPEN Duplikat-Gruppe(n) verarbeitet.${RESET}"
  exit 0
fi

# ============================================
#  LOG ANZEIGEN
# ============================================
if $ZEIG_LOG; then
  if [ ! -f "$LOGDATEI" ]; then
    echo -e "${ROT}Kein Log gefunden. Noch keine Sortierung durchgefuehrt.${RESET}"
    exit 1
  fi
  echo -e "${CYAN}── Log der letzten Sortierung ──${RESET}"
  ANZAHL=0
  while IFS='|' read -r QUELLE ZIEL_DATEI DATUM; do
    [ -z "$QUELLE" ] && continue
    echo -e "  ${GRUEN}$(basename "$QUELLE")${RESET}  ->  ${BLAU}$(basename "$(dirname "$ZIEL_DATEI")")/${RESET}  ${GELB}($DATUM)${RESET}"
    ANZAHL=$((ANZAHL+1))
  done < "$LOGDATEI"
  echo ""
  echo -e "${CYAN}Gesamt: $ANZAHL Datei(en)  |  --undo zum Rueckgaengig machen${RESET}"
  exit 0
fi

# ============================================
#  UNDO
# ============================================
if $UNDO; then
  if [ ! -f "$LOGDATEI" ]; then
    echo -e "${ROT}Kein Log gefunden. Nichts zum Rueckgaengig machen.${RESET}"
    exit 1
  fi
  echo -e "${GELB}Mache Sortierung rueckgaengig...${RESET}"
  echo "--------------------------------------------"

  # FIX: Keine Subshell – tac in temporaere Datei lesen
  TMP_LOG=$(mktemp 2>/dev/null) || TMP_LOG="/tmp/.sortier_undo_$$"
  tac "$LOGDATEI" > "$TMP_LOG" 2>/dev/null

  WIEDERHERGESTELLT=0
  FEHLER_UNDO=0
  while IFS='|' read -r QUELLE ZIEL_DATEI DATUM; do
    [ -z "$QUELLE" ] && continue
    if [ -f "$ZIEL_DATEI" ]; then
      if mv -- "$ZIEL_DATEI" "$QUELLE" 2>/dev/null; then
        echo -e "${GRUEN}Wiederhergestellt: $(basename "$QUELLE")${RESET}"
        WIEDERHERGESTELLT=$((WIEDERHERGESTELLT+1))
      else
        echo -e "${ROT}Fehler: $(basename "$QUELLE") konnte nicht zurueckgeschoben werden.${RESET}"
        FEHLER_UNDO=$((FEHLER_UNDO+1))
      fi
    else
      echo -e "${ROT}Nicht mehr vorhanden: $(basename "$ZIEL_DATEI")${RESET}"
      FEHLER_UNDO=$((FEHLER_UNDO+1))
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
