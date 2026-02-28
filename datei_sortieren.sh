#!/bin/bash

# ============================================
#  Datei-Sortierer - Sortiert nach Dateityp
# ============================================

# Zielverzeichnis: aktuelles Verzeichnis oder als Argument übergeben
ZIEL="${1:-.}"

if [ ! -d "$ZIEL" ]; then
  echo "❌ Verzeichnis '$ZIEL' nicht gefunden."
  exit 1
fi

echo "📂 Sortiere Dateien in: $ZIEL"
echo "--------------------------------------------"

# Kategorien und ihre Dateiendungen
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

VERSCHOBEN=0
UEBERSPRUNGEN=0

# Alle Dateien im Zielverzeichnis durchgehen (keine Unterordner)
for DATEI in "$ZIEL"/*; do
  # Nur Dateien verarbeiten (keine Ordner)
  [ -f "$DATEI" ] || continue

  DATEINAME=$(basename "$DATEI")
  ENDUNG="${DATEINAME##*.}"
  ENDUNG_KLEIN=$(echo "$ENDUNG" | tr '[:upper:]' '[:lower:]')

  GEFUNDEN=false

  for KATEGORIE in "${!KATEGORIEN[@]}"; do
    for EXT in ${KATEGORIEN[$KATEGORIE]}; do
      if [ "$ENDUNG_KLEIN" = "$EXT" ]; then
        # Zielordner erstellen falls nicht vorhanden
        ZIELORDNER="$ZIEL/$KATEGORIE"
        mkdir -p "$ZIELORDNER"

        # Datei verschieben (bei Namenskonflikt: Nummer anhängen)
        ZIELDATEI="$ZIELORDNER/$DATEINAME"
        if [ -e "$ZIELDATEI" ]; then
          BASENAME="${DATEINAME%.*}"
          ZIELDATEI="$ZIELORDNER/${BASENAME}_$(date +%s%N).$ENDUNG_KLEIN"
        fi

        mv "$DATEI" "$ZIELDATEI"
        echo "✅ $DATEINAME  →  $KATEGORIE/"
        VERSCHOBEN=$((VERSCHOBEN + 1))
        GEFUNDEN=true
        break
      fi
    done
    $GEFUNDEN && break
  done

  if ! $GEFUNDEN; then
    # Unbekannte Dateitypen in "Sonstiges"
    ZIELORDNER="$ZIEL/Sonstiges"
    mkdir -p "$ZIELORDNER"
    mv "$DATEI" "$ZIELORDNER/$DATEINAME"
    echo "📦 $DATEINAME  →  Sonstiges/"
    UEBERSPRUNGEN=$((UEBERSPRUNGEN + 1))
  fi

done

echo "--------------------------------------------"
echo "✅ Fertig! $VERSCHOBEN Datei(en) sortiert, $UEBERSPRUNGEN in 'Sonstiges'."
