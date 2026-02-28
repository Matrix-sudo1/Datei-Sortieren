# 📂 Datei-Sortieren

Ein einfaches Bash-Script, das Dateien automatisch nach Dateityp in Ordner sortiert.

## ✨ Features

- Sortiert Dateien in Kategorien wie Bilder, Videos, Dokumente, Audio, uvm.
- Unbekannte Dateitypen werden in `Sonstiges/` verschoben
- Unterstützt eigene Zielordner als Argument
- Verhindert das Überschreiben von Dateien bei Namenskonflikten

## 📁 Erstellte Ordner

| Ordner | Dateitypen |
|--------|-----------|
| `Bilder/` | jpg, png, gif, svg, webp, ... |
| `Videos/` | mp4, mkv, avi, mov, ... |
| `Audio/` | mp3, wav, flac, aac, ... |
| `Dokumente/` | pdf, doc, docx, txt, md, ... |
| `Tabellen/` | xls, xlsx, csv, ... |
| `Praesentation/` | ppt, pptx, ... |
| `Code/` | sh, py, js, html, css, ... |
| `Archive/` | zip, tar, rar, 7z, ... |
| `Ausfuehrbar/` | exe, dmg, deb, ... |
| `Sonstiges/` | alle unbekannten Typen |

## 🚀 Verwendung

```bash
# Ausführbar machen
chmod +x datei_sortieren.sh

# Aktuellen Ordner sortieren
./datei_sortieren.sh

# Bestimmten Ordner sortieren
./datei_sortieren.sh /home/user/Downloads
```

## 📋 Beispiel-Ausgabe

```
📂 Sortiere Dateien in: /home/user/Downloads
--------------------------------------------
✅ foto.jpg          →  Bilder/
✅ video.mp4         →  Videos/
✅ dokument.pdf      →  Dokumente/
✅ archiv.zip        →  Archive/
📦 unbekannt.xyz     →  Sonstiges/
--------------------------------------------
✅ Fertig! 4 Datei(en) sortiert, 1 in 'Sonstiges'.
```

## ⚙️ Voraussetzungen

- Linux oder macOS (oder Windows mit Git Bash)
- Bash 4.0 oder höher

## 📄 Lizenz

MIT License – frei verwendbar und veränderbar.
