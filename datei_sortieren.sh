#!/bin/bash

# ============================================
#  Datei-Sortierer v3.0
#  - Sortiert nach Dateityp
#  - Vorschau-Modus (--dry-run)
#  - Rueckgaengig-Funktion (--undo)
#  - Log anzeigen (--log)
#  - Eigene Kategorien via config.txt
# ============================================

# --- Farben ---
ROT='\033[0;31m'
GRUEN='\033[0;32m'
GELB='\033[1;33m'
BLAU='\033[0;34m'
CYAN='\033[0;36m'
RESET='\033[0m'

# --- Hilfe anzeigen ---
hilfe() {
  echo -e "${CYAN}"
  echo "╔══════════════════════════════════════════╗"
  echo "║        Datei-Sortierer v3.0              ║"
  echo "╚══════════════════════════════════════════╝"
  echo -e "${RESET}"
  echo "Verwendung:"
  echo "  ./datei_sortieren.sh [ORDNER] [OPTIONEN]"
  echo ""
  echo "Optionen:"
  echo "  --dry-run    Vorschau: zeigt was passieren wuerde"
  echo "  --undo       Letzte Sortierung rueckgaengig machen"
  echo "  --log        Log der letzten Sortierung anzeigen"
  echo "  --config     Pfad zur Konfigurationsdatei angeben"
  echo "  --help       Diese Hilfe anzeigen"
  echo ""
  echo "Beispiele:"
  echo "  ./datei_sortieren.sh"
  echo "  ./datei_sortieren.sh ~/Downloads"
  echo "  ./datei_sortieren.sh ~/Downloads --dry-run"
  echo "  ./datei_sortieren.sh --undo"
  echo "  ./datei_sortieren.sh --log"
  echo "  ./datei_sortieren.sh --config meine_config.txt"
  exit 0
}

# --- Standardwerte ---
ZIEL="."
DRYRUN=false
UNDO=false
ZEIG_LOG=false
CONFIGDATEI="$(dirname "$0")/config.txt"
LOGDATEI=""

# --- Argumente auswerten ---
for ARG in "$@"; do
  case $ARG in
    --dry-run) DRYRUN=true ;;
    --undo)    UNDO=true ;;
    --log)     ZEIG_LOG=true ;;
    --help)    hilfe ;;
    --config)  shift; CONFIGDATEI="$1" ;;
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

  WIEDERHERGESTELLT=0
  FEHLER=0

  tac "$LOGDATEI" | while IFS='|' read -r QUELLE ZIEL_DATEI DATUM; do
    if [ -f "$ZIEL_DATEI" ]; then
      mv "$ZIEL_DATEI" "$QUELLE"
      echo -e "${GRUEN}Wiederhergestellt: $(basename "$QUELLE")${RESET}"
    else
      echo -e "${ROT}Nicht gefunden: $(basename "$ZIEL_DATEI")${RESET}"
    fi
  done

  # Leere Ordner loeschen
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
    # Kommentare und leere Zeilen ueberspringen
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
#  SORTIEREN
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
DATUM=$(date '+%d.%m.%Y %H:%M')

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
          echo "$DATEI|$ZIELDATEI|$DATUM" >> "$LOGDATEI"
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
      echo "$DATEI|$ZIELDATEI|$DATUM" >> "$LOGDATEI"
      echo -e "${GELB}Sonstiges: $DATEINAME  ->  Sonstiges/${RESET}"
    fi

    UEBERSPRUNGEN=$((UEBERSPRUNGEN + 1))
  fi

done

echo "--------------------------------------------"
if $DRYRUN; then
  echo -e "${BLAU}Vorschau: $VERSCHOBEN Datei(en) wuerden sortiert, $UEBERSPRUNGEN nach 'Sonstiges'.${RESET}"
  echo -e "${BLAU}Starte ohne --dry-run um wirklich zu sortieren.${RESET}"
else
  echo -e "${GRUEN}Fertig! $VERSCHOBEN Datei(en) sortiert, $UEBERSPRUNGEN in 'Sonstiges'.${RESET}"
  echo -e "${GELB}Tipps: --undo zum Rueckgaengig machen | --log zum Anzeigen${RESET}"
fi
