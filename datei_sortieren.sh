#!/bin/bash

# ============================================
#  Datei-Sortierer v5.0
#  - Sortiert nach Dateityp
#  - Sortiert nach Datum (Jahr/Monat)
#  - Vorschau-Modus (--dry-run)
#  - Rueckgaengig-Funktion (--undo)
#  - Log anzeigen (--log)
#  - Eigene Kategorien via config.txt
#  - Duplikate erkennen (--duplikate)
# ============================================

# --- Farben ---
ROT='\033[0;31m'
GRUEN='\033[0;32m'
GELB='\033[1;33m'
BLAU='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
RESET='\033[0m'

# --- Monatsnamen ---
monat_name() {
  case $1 in
    01) echo "Januar" ;; 02) echo "Februar" ;; 03) echo "Maerz" ;;
    04) echo "April" ;; 05) echo "Mai" ;; 06) echo "Juni" ;;
    07) echo "Juli" ;; 08) echo "August" ;; 09) echo "September" ;;
    10) echo "Oktober" ;; 11) echo "November" ;; 12) echo "Dezember" ;;
  esac
}

# --- Hilfe anzeigen ---
hilfe() {
  echo -e "${CYAN}"
  echo "╔══════════════════════════════════════════╗"
  echo "║        Datei-Sortierer v5.0              ║"
  echo "╚══════════════════════════════════════════╝"
  echo -e "${RESET}"
  echo "Verwendung:"
  echo "  ./datei_sortieren.sh [ORDNER] [OPTIONEN]"
  echo ""
  echo "Optionen:"
  echo "  --dry-run      Vorschau: zeigt was passieren wuerde"
  echo "  --undo         Letzte Sortierung rueckgaengig machen"
  echo "  --log          Log der letzten Sortierung anzeigen"
  echo "  --nach-datum   Nach Erstelldatum sortieren (Jahr/Monat)"
  echo "  --duplikate    Duplikate suchen und anzeigen"
  echo "  --config DATEI Eigene Konfigurationsdatei angeben"
  echo "  --help         Diese Hilfe anzeigen"
  echo ""
  echo "Beispiele:"
  echo "  ./datei_sortieren.sh"
  echo "  ./datei_sortieren.sh ~/Downloads --dry-run"
  echo "  ./datei_sortieren.sh --nach-datum"
  echo "  ./datei_sortieren.sh --duplikate"
  echo "  ./datei_sortieren.sh ~/Downloads --duplikate"
  echo "  ./datei_sortieren.sh --undo"
  echo "  ./datei_sortieren.sh --log"
  exit 0
}

# --- Standardwerte ---
ZIEL="."
DRYRUN=false
UNDO=false
ZEIG_LOG=false
NACH_DATUM=false
DUPLIKATE=false
CONFIGDATEI="$(dirname "$0")/config.txt"

# --- Argumente auswerten ---
SKIP_NEXT=false
for ARG in "$@"; do
  if $SKIP_NEXT; then
    CONFIGDATEI="$ARG"
    SKIP_NEXT=false
    continue
  fi
  case $ARG in
    --dry-run)    DRYRUN=true ;;
    --undo)       UNDO=true ;;
    --log)        ZEIG_LOG=true ;;
    --nach-datum) NACH_DATUM=true ;;
    --duplikate)  DUPLIKATE=true ;;
    --help)       hilfe ;;
    --config)     SKIP_NEXT=true ;;
    *)
      if [ -d "$ARG" ]; then
        ZIEL="$ARG"
      fi
      ;;
  esac
done

LOGDATEI="$ZIEL/.sortier_log.txt"

# --- Verzeichnis pruefen ---
if [ ! -d "$ZIEL" ]; then
  echo -e "${ROT}Verzeichnis '$ZIEL' nicht gefunden.${RESET}"
  exit 1
fi

# ============================================
#  DUPLIKATE ERKENNEN
# ============================================
if $DUPLIKATE; then
  echo -e "${MAGENTA}╔══════════════════════════════════════════╗"
  echo -e "║        Duplikat-Suche                    ║"
  echo -e "╚══════════════════════════════════════════╝${RESET}"
  echo -e "${CYAN}Suche in: $ZIEL (inkl. Unterordner)${RESET}"
  echo "--------------------------------------------"

  # md5sum pruefen
  if ! command -v md5sum &>/dev/null; then
    echo -e "${ROT}md5sum nicht gefunden. Bitte installieren.${RESET}"
    exit 1
  fi

  # Alle Dateien hashen und nach Hash gruppieren
  declare -A HASH_MAP

  while IFS= read -r -d '' DATEI; do
    [ "$(basename "$DATEI")" = ".sortier_log.txt" ] && continue
    HASH=$(md5sum "$DATEI" | awk '{print $1}')
    if [ -n "${HASH_MAP[$HASH]}" ]; then
      HASH_MAP[$HASH]="${HASH_MAP[$HASH]}|$DATEI"
    else
      HASH_MAP[$HASH]="$DATEI"
    fi
  done < <(find "$ZIEL" -type f -print0)

  DUPLIKAT_GRUPPEN=0
  DUPLIKAT_DATEIEN=0

  for HASH in "${!HASH_MAP[@]}"; do
    IFS='|' read -ra DATEIEN <<< "${HASH_MAP[$HASH]}"

    # Nur anzeigen wenn mehr als eine Datei denselben Hash hat
    if [ ${#DATEIEN[@]} -gt 1 ]; then
      DUPLIKAT_GRUPPEN=$((DUPLIKAT_GRUPPEN + 1))
      GROESSE=$(du -h "${DATEIEN[0]}" | awk '{print $1}')

      echo -e "${MAGENTA}Duplikat-Gruppe $DUPLIKAT_GRUPPEN  [Hash: ${HASH:0:8}...]  Groesse: $GROESSE${RESET}"

      INDEX=1
      for DATEI in "${DATEIEN[@]}"; do
        if [ $INDEX -eq 1 ]; then
          echo -e "  ${GRUEN}[ORIGINAL]  $DATEI${RESET}"
        else
          echo -e "  ${GELB}[DUPLIKAT]  $DATEI${RESET}"
          DUPLIKAT_DATEIEN=$((DUPLIKAT_DATEIEN + 1))
        fi
        INDEX=$((INDEX + 1))
      done

      # Interaktiv fragen was tun
      echo ""
      echo -e "${CYAN}Was moechtest du tun?${RESET}"
      echo "  [1] Duplikate loeschen"
      echo "  [2] Duplikate in 'Duplikate/' verschieben"
      echo "  [3] Ueberspringen"
      echo -n "Deine Wahl (1/2/3): "
      read -r WAHL

      case $WAHL in
        1)
          for i in "${!DATEIEN[@]}"; do
            if [ $i -gt 0 ]; then
              rm "${DATEIEN[$i]}"
              echo -e "${ROT}Geloescht: ${DATEIEN[$i]}${RESET}"
            fi
          done
          ;;
        2)
          DUPORDNER="$ZIEL/Duplikate"
          mkdir -p "$DUPORDNER"
          for i in "${!DATEIEN[@]}"; do
            if [ $i -gt 0 ]; then
              mv "${DATEIEN[$i]}" "$DUPORDNER/"
              echo -e "${GELB}Verschoben: $(basename "${DATEIEN[$i]}")  ->  Duplikate/${RESET}"
            fi
          done
          ;;
        *)
          echo -e "${BLAU}Uebersprungen.${RESET}"
          ;;
      esac
      echo "--------------------------------------------"
    fi
  done

  if [ $DUPLIKAT_GRUPPEN -eq 0 ]; then
    echo -e "${GRUEN}Keine Duplikate gefunden!${RESET}"
  else
    echo -e "${MAGENTA}Gefunden: $DUPLIKAT_GRUPPEN Gruppe(n) mit $DUPLIKAT_DATEIEN Duplikat(en).${RESET}"
  fi
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

  echo -e "${CYAN}╔══════════════════════════════════════════╗"
  echo -e "║        Log der letzten Sortierung        ║"
  echo -e "╚══════════════════════════════════════════╝${RESET}"
  echo ""

  ANZAHL=0
  while IFS='|' read -r QUELLE ZIEL_DATEI DATUM; do
    DATEINAME=$(basename "$QUELLE")
    KATEGORIE=$(basename "$(dirname "$ZIEL_DATEI")")
    echo -e "${GRUEN}$DATEINAME${RESET}  ->  ${BLAU}$KATEGORIE/${RESET}  ${GELB}($DATUM)${RESET}"
    ANZAHL=$((ANZAHL + 1))
  done < "$LOGDATEI"

  echo ""
  echo -e "${CYAN}Gesamt: $ANZAHL Datei(en) verschoben.${RESET}"
  echo -e "${GELB}Tipp: Mit --undo alles rueckgaengig machen.${RESET}"
  exit 0
fi

# ============================================
#  UNDO-FUNKTION
# ============================================
if $UNDO; then
  if [ ! -f "$LOGDATEI" ]; then
    echo -e "${ROT}Kein Log gefunden. Nichts zum Rueckgaengig machen.${RESET}"
    exit 1
  fi

  echo -e "${GELB}Mache letzte Sortierung rueckgaengig...${RESET}"
  echo "--------------------------------------------"

  tac "$LOGDATEI" | while IFS='|' read -r QUELLE ZIEL_DATEI DATUM; do
    if [ -f "$ZIEL_DATEI" ]; then
      mv "$ZIEL_DATEI" "$QUELLE"
      echo -e "${GRUEN}Wiederhergestellt: $(basename "$QUELLE")${RESET}"
    else
      echo -e "${ROT}Nicht gefunden: $(basename "$ZIEL_DATEI")${RESET}"
    fi
  done

  find "$ZIEL" -mindepth 1 -type d -empty -delete 2>/dev/null
  rm -f "$LOGDATEI"
  echo "--------------------------------------------"
  echo -e "${GRUEN}Undo abgeschlossen!${RESET}"
  exit 0
fi

# ============================================
#  KATEGORIEN LADEN (aus config.txt)
# ============================================
declare -A KATEGORIEN

if [ -f "$CONFIGDATEI" ]; then
  echo -e "${CYAN}Konfiguration geladen: $CONFIGDATEI${RESET}"
  while IFS='=' read -r KATEGORIE ENDUNGEN; do
    [[ "$KATEGORIE" =~ ^#.*$ ]] && continue
    [ -z "$KATEGORIE" ] && continue
    KATEGORIEN["$KATEGORIE"]="$ENDUNGEN"
  done < "$CONFIGDATEI"
else
  echo -e "${GELB}Keine config.txt gefunden - nutze Standard-Kategorien.${RESET}"
  KATEGORIEN=(
    ["Bilder"]="jpg jpeg png gif bmp svg webp ico tiff tif"
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
fi

# ============================================
#  DATUM-SORTIERUNG
# ============================================
if $NACH_DATUM; then
  if $DRYRUN; then
    echo -e "${BLAU}VORSCHAU-MODUS - Es wird nichts verschoben!${RESET}"
  else
    echo -e "${GRUEN}Sortiere nach Datum in: $ZIEL${RESET}"
    > "$LOGDATEI"
  fi
  echo "--------------------------------------------"

  VERSCHOBEN=0
  DATUM_LOG=$(date '+%d.%m.%Y %H:%M')

  for DATEI in "$ZIEL"/*; do
    [ -f "$DATEI" ] || continue
    [ "$(basename "$DATEI")" = ".sortier_log.txt" ] && continue

    DATEINAME=$(basename "$DATEI")
    BIRTH=$(stat --format="%W" "$DATEI" 2>/dev/null)
    if [ -z "$BIRTH" ] || [ "$BIRTH" = "0" ]; then
      BIRTH=$(stat --format="%Y" "$DATEI")
    fi

    JAHR=$(date -d "@$BIRTH" '+%Y')
    MONAT_NR=$(date -d "@$BIRTH" '+%m')
    MONAT=$(monat_name "$MONAT_NR")

    ZIELORDNER="$ZIEL/$JAHR/$MONAT"
    ZIELDATEI="$ZIELORDNER/$DATEINAME"

    if [ -e "$ZIELDATEI" ]; then
      BASENAME="${DATEINAME%.*}"
      ENDUNG="${DATEINAME##*.}"
      ZIELDATEI="$ZIELORDNER/${BASENAME}_$(date +%s%N).$ENDUNG"
    fi

    if $DRYRUN; then
      echo -e "${BLAU}VORSCHAU: $DATEINAME  ->  $JAHR/$MONAT/${RESET}"
    else
      mkdir -p "$ZIELORDNER"
      mv "$DATEI" "$ZIELDATEI"
      echo "$DATEI|$ZIELDATEI|$DATUM_LOG" >> "$LOGDATEI"
      echo -e "${GRUEN}OK: $DATEINAME  ->  $JAHR/$MONAT/${RESET}"
    fi
    VERSCHOBEN=$((VERSCHOBEN + 1))
  done

  echo "--------------------------------------------"
  if $DRYRUN; then
    echo -e "${BLAU}Vorschau: $VERSCHOBEN Datei(en) wuerden nach Datum sortiert.${RESET}"
  else
    echo -e "${GRUEN}Fertig! $VERSCHOBEN Datei(en) nach Datum sortiert.${RESET}"
    echo -e "${GELB}Tipps: --undo | --log | --duplikate${RESET}"
  fi
  exit 0
fi

# ============================================
#  NACH DATEITYP SORTIEREN
# ============================================
if $DRYRUN; then
  echo -e "${BLAU}VORSCHAU-MODUS - Es wird nichts verschoben!${RESET}"
else
  echo -e "${GRUEN}Sortiere Dateien in: $ZIEL${RESET}"
  > "$LOGDATEI"
fi
echo "--------------------------------------------"

VERSCHOBEN=0
UEBERSPRUNGEN=0
DATUM_LOG=$(date '+%d.%m.%Y %H:%M')

for DATEI in "$ZIEL"/*; do
  [ -f "$DATEI" ] || continue
  [ "$(basename "$DATEI")" = ".sortier_log.txt" ] && continue

  DATEINAME=$(basename "$DATEI")
  ENDUNG="${DATEINAME##*.}"
  ENDUNG_KLEIN=$(echo "$ENDUNG" | tr '[:upper:]' '[:lower:]')
  GEFUNDEN=false

  for KATEGORIE in "${!KATEGORIEN[@]}"; do
    for EXT in ${KATEGORIEN[$KATEGORIE]}; do
      if [ "$ENDUNG_KLEIN" = "$EXT" ]; then
        ZIELORDNER="$ZIEL/$KATEGORIE"
        ZIELDATEI="$ZIELORDNER/$DATEINAME"

        if [ -e "$ZIELDATEI" ]; then
          BASENAME="${DATEINAME%.*}"
          ZIELDATEI="$ZIELORDNER/${BASENAME}_$(date +%s%N).$ENDUNG_KLEIN"
        fi

        if $DRYRUN; then
          echo -e "${BLAU}VORSCHAU: $DATEINAME  ->  $KATEGORIE/${RESET}"
        else
          mkdir -p "$ZIELORDNER"
          mv "$DATEI" "$ZIELDATEI"
          echo "$DATEI|$ZIELDATEI|$DATUM_LOG" >> "$LOGDATEI"
          echo -e "${GRUEN}OK: $DATEINAME  ->  $KATEGORIE/${RESET}"
        fi

        VERSCHOBEN=$((VERSCHOBEN + 1))
        GEFUNDEN=true
        break
      fi
    done
    $GEFUNDEN && break
  done

  if ! $GEFUNDEN; then
    ZIELORDNER="$ZIEL/Sonstiges"
    ZIELDATEI="$ZIELORDNER/$DATEINAME"

    if $DRYRUN; then
      echo -e "${GELB}VORSCHAU: $DATEINAME  ->  Sonstiges/${RESET}"
    else
      mkdir -p "$ZIELORDNER"
      mv "$DATEI" "$ZIELDATEI"
      echo "$DATEI|$ZIELDATEI|$DATUM_LOG" >> "$LOGDATEI"
      echo -e "${GELB}Sonstiges: $DATEINAME  ->  Sonstiges/${RESET}"
    fi
    UEBERSPRUNGEN=$((UEBERSPRUNGEN + 1))
  fi
done

echo "--------------------------------------------"
if $DRYRUN; then
  echo -e "${BLAU}Vorschau: $VERSCHOBEN sortiert, $UEBERSPRUNGEN nach 'Sonstiges'.${RESET}"
  echo -e "${BLAU}Starte ohne --dry-run um wirklich zu sortieren.${RESET}"
else
  echo -e "${GRUEN}Fertig! $VERSCHOBEN Datei(en) sortiert, $UEBERSPRUNGEN in 'Sonstiges'.${RESET}"
  echo -e "${GELB}Tipps: --undo | --log | --nach-datum | --duplikate${RESET}"
fi
