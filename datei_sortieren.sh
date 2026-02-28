#!/bin/bash

# ============================================
#  Datei-Sortierer v2.0
#  - Sortiert nach Dateityp
#  - Vorschau-Modus (Dry Run)
#  - Rueckgaengig-Funktion (Undo)
# ============================================

# --- Farben ---
ROT='\033[0;31m'
GRUEN='\033[0;32m'
GELB='\033[1;33m'
BLAU='\033[0;34m'
RESET='\033[0m'

# --- Standardwerte ---
ZIEL="${1:-.}"
DRYRUN=false
UNDO=false
LOGDATEI="$ZIEL/.sortier_log.txt"

# --- Argumente auswerten ---
for ARG in "$@"; do
  case $ARG in
    --dry-run) DRYRUN=true ;;
    --undo)    UNDO=true ;;
  esac
done

# --- Verzeichnis pruefen ---
if [ ! -d "$ZIEL" ]; then
  echo -e "${ROT}Verzeichnis '$ZIEL' nicht gefunden.${RESET}"
  exit 1
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

  tac "$LOGDATEI" | while IFS='|' read -r QUELLE ZIELDATEI; do
    if [ -f "$ZIELDATEI" ]; then
      mv "$ZIELDATEI" "$QUELLE"
      echo -e "${GRUEN}Wiederhergestellt: $(basename "$QUELLE")${RESET}"
    else
      echo -e "${ROT}Nicht gefunden: $(basename "$ZIELDATEI")${RESET}"
    fi
  done

  # Leere Ordner loeschen
  find "$ZIEL" -mindepth 1 -type d -empty -delete

  rm -f "$LOGDATEI"
  echo "--------------------------------------------"
  echo -e "${GRUEN}Undo abgeschlossen!${RESET}"
  exit 0
fi

# ============================================
#  KATEGORIEN
# ============================================
declare -A KATEGORIEN=(
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

# ============================================
#  VORSCHAU oder SORTIEREN
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
          echo "$DATEI|$ZIELDATEI" >> "$LOGDATEI"
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
      echo "$DATEI|$ZIELDATEI" >> "$LOGDATEI"
      echo -e "${GELB}Sonstiges: $DATEINAME  ->  Sonstiges/${RESET}"
    fi

    UEBERSPRUNGEN=$((UEBERSPRUNGEN + 1))
  fi

done

echo "--------------------------------------------"
if $DRYRUN; then
  echo -e "${BLAU}Vorschau fertig: $VERSCHOBEN Datei(en) wuerden sortiert, $UEBERSPRUNGEN nach 'Sonstiges'.${RESET}"
  echo -e "${BLAU}Starte ohne --dry-run um wirklich zu sortieren.${RESET}"
else
  echo -e "${GRUEN}Fertig! $VERSCHOBEN Datei(en) sortiert, $UEBERSPRUNGEN in 'Sonstiges'.${RESET}"
  echo -e "${GELB}Tipp: Mit --undo kannst du alles rueckgaengig machen.${RESET}"
fi
