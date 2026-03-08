# 📂 Datei-Sortierer

Ein Bash-Script mit moderner GUI, das Dateien automatisch sortiert – stabil, getestet, plattformkompatibel.

---

## ✨ Features

| Feature | Script | GUI |
|---------|--------|-----|
| Sortierung nach Dateityp | ✅ | ✅ |
| Sortierung nach Datum | ✅ | ✅ |
| Vorschau-Modus (Dry-Run) | ✅ | ✅ |
| Rückgängig (Undo) | ✅ | ✅ |
| Log anzeigen | ✅ | ✅ |
| Duplikate erkennen (mit Papierkorb) | ✅ | – |
| Eigene Kategorien (config.txt) | ✅ | ✅ |
| Profile (fotos / buero / entwickler) | ✅ | ✅ |
| Ignorier-Liste | ✅ | ✅ |
| Mehrere Ordner gleichzeitig | ✅ | – |
| Watch-Modus (automatisch sortieren) | ✅ | ✅ |
| **Benachrichtigungen bei Watch** | ✅ v7.0 | ✅ v5.0 |
| **Geplante Sortierung (Cronjob)** | ✅ v7.0 | ✅ v5.0 |
| **HTML-Bericht nach Sortierung** | ✅ v7.0 | ✅ v5.0 |
| **Drag & Drop** | – | ✅ v5.0 |
| **Dark / Light Theme** | – | ✅ v5.0 |

---

## 🖥️ GUI starten

```bash
python gui.py
```

**Voraussetzungen:**
- Python 3
- Git Bash (Windows): https://git-scm.com/download/win
- Optional: `pip install tkinterdnd2` für echtes Drag & Drop

---

## 💻 Terminal – alle Befehle

```bash
chmod +x datei_sortieren.sh       # einmalig ausführbar machen

# Basis
./datei_sortieren.sh ~/Downloads
./datei_sortieren.sh ~/Downloads --dry-run
./datei_sortieren.sh ~/Downloads --nach-datum
./datei_sortieren.sh ~/Downloads --undo
./datei_sortieren.sh ~/Downloads --log
./datei_sortieren.sh ~/Downloads --duplikate

# Profile & Konfiguration
./datei_sortieren.sh ~/Fotos --profil fotos
./datei_sortieren.sh --profile-list
./datei_sortieren.sh ~/Downloads --config meine.txt
./datei_sortieren.sh ~/Downloads --ignore meine_ignore.txt

# Mehrere Ordner
./datei_sortieren.sh --ordner ~/Downloads ~/Desktop ~/Dokumente

# Watch-Modus
./datei_sortieren.sh ~/Downloads --watch
./datei_sortieren.sh ~/Downloads --watch --watch-interval 30
./datei_sortieren.sh ~/Downloads --watch --notify

# NEU v7.0
./datei_sortieren.sh ~/Downloads --bericht
./datei_sortieren.sh ~/Downloads --bericht /pfad/zum/bericht.html
./datei_sortieren.sh ~/Downloads --cronjob 20:00
./datei_sortieren.sh --cronjob-list
./datei_sortieren.sh --cronjob-remove

./datei_sortieren.sh --help
```

---

## 🆕 Neue Features v7.0

### ⏰ Geplante Sortierung (Cronjob-Assistent)

Sortierung einmal einrichten – läuft danach täglich automatisch ohne manuellen Eingriff.

```bash
# Täglich um 20:00 Uhr sortieren
./datei_sortieren.sh ~/Downloads --cronjob 20:00

# Alle geplanten Sortierungen anzeigen
./datei_sortieren.sh --cronjob-list

# Alle geplanten Sortierungen entfernen
./datei_sortieren.sh --cronjob-remove
```

Funktioniert auf Linux und macOS über `crontab`. Auf Windows: Windows Aufgabenplanung (`taskschd.msc`).

In der **GUI** gibt es einen eigenen Tab „⏰ Geplant" mit Uhrzeit-Auswahl per Spinbox und den drei Aktionen als Buttons.

---

### 🔔 Benachrichtigungen

Beim Watch-Modus erscheint nach jeder automatisch sortierten Datei ein System-Popup.

```bash
./datei_sortieren.sh ~/Downloads --watch --notify
```

- **macOS:** via `osascript`
- **Linux:** via `notify-send` (GNOME/KDE) oder `zenity`
- In der **GUI:** Checkbox „🔔 Benachrichtigen" im Sortieren-Tab

---

### 🗑️ Papierkorb statt Löschen

Beim Duplikat-Entfernen gibt es jetzt vier Optionen statt zwei:

```
[1] Papierkorb          – sicher, wiederherstellbar
[2] Endgültig löschen   – mit Bestätigungsdialog
[3] nach 'Duplikate/'   – Ordner im selben Verzeichnis
[4] Überspringen
```

- **macOS:** `~/.Trash`
- **Linux:** `gio trash` → `~/.local/share/Trash/files` (Fallback)

---

### 📄 HTML-Bericht

Nach der Sortierung wird eine übersichtliche HTML-Datei mit Statistiken erstellt.

```bash
# Automatischer Dateiname (sortier_bericht_DATUM_UHRZEIT.html)
./datei_sortieren.sh ~/Downloads --bericht

# Eigener Dateiname
./datei_sortieren.sh ~/Downloads --bericht /pfad/bericht.html
```

Der Bericht enthält: Anzahl sortierter Dateien, Fehler, Kategorien-Balkendiagramm, Zeitstempel. In der **GUI:** Checkbox „📄 HTML-Bericht" im Sortieren-Tab.

---

## 🆕 GUI v5.0 – Neue Features

### 🖱️ Drag & Drop

Ordner direkt ins Fenster ziehen statt Datei-Dialog. Für natives Drag & Drop:

```bash
pip install tkinterdnd2
```

Ohne `tkinterdnd2` funktioniert der Klick-Dialog wie bisher.

---

### 🌙 Dark / Light Theme

Oben rechts im Fenster: **„☀️ Light"** / **„🌙 Dark"** Umschalter. Wechselt sofort alle Farben ohne Neustart.

---

### ⏰ Cronjob-Tab in der GUI

Eigener Tab „⏰ Geplant" mit:
- Uhrzeit-Auswahl per Spinbox (Stunden / Minuten)
- Buttons: Einrichten, Alle anzeigen, Alle entfernen
- Info-Box mit Hinweisen zur Plattform-Kompatibilität

---

## 🧪 Testergebnisse (v7.1 / GUI v5.1)

| Test | Ergebnis |
|------|---------|
| Script Syntax (bash -n) | ✅ |
| GUI Python Syntax (py_compile) | ✅ |
| Kollision in Sonstiges/ verhindert | ✅ |
| Suffix bei Datei ohne Erweiterung korrekt | ✅ |
| Statistiken bei --kopieren (=>) | ✅ |
| Theme-Wechsel: alle Labels korrekt | ✅ |
| Theme-Wechsel: Spinboxen korrekt | ✅ |
| Dry-Run | ✅ |
| HTML-Bericht erstellt | ✅ |
| Drag & Drop Setup | ✅ |
| Dark/Light Theme | ✅ |
| Cronjob-Tab vorhanden | ✅ |
| tkinterdnd2 Fallback | ✅ |
| Benachrichtigung Checkbox | ✅ |

---

## 📁 Erstellte Ordner

| Ordner | Dateitypen |
|--------|-----------|
| `Bilder/` | jpg, png, gif, svg, webp, heic, raw, cr2, nef, ... |
| `Videos/` | mp4, mkv, avi, mov, ... |
| `Audio/` | mp3, wav, flac, aac, ... |
| `Dokumente/` | pdf, doc, docx, txt, md, ... |
| `Tabellen/` | xls, xlsx, csv, ... |
| `Praesentation/` | ppt, pptx, ... |
| `Code/` | sh, py, js, html, css, ... |
| `Archive/` | zip, tar, rar, 7z, ... |
| `Ausfuehrbar/` | exe, dmg, deb, ... |
| `Schriften/` | ttf, otf, woff, ... |
| `Sonstiges/` | alle unbekannten Typen |

---

## 🐛 Bugfixes v7.1 / GUI v5.1

### Script v7.1

| # | Typ | Beschreibung |
|---|-----|-------------|
| S1 | Cleanup | Toter Code entfernt: `local BEFEHL` wurde gesetzt aber nie verwendet |
| S2 | Kritisch | **Sonstiges-Ordner**: gleichnamige Dateien wurden lautlos überschrieben – jetzt Kollisionsprüfung mit eindeutigem Suffix |
| S3 | Bug | **Kollisions-Suffix** bei Dateien ohne Erweiterung (z.B. `Makefile`) erzeugte fehlerhaften Namen `Makefile_123.Makefile` → jetzt korrekt `Makefile_123` |

### GUI v5.1

| # | Typ | Beschreibung |
|---|-----|-------------|
| G4 | Kritisch | **Statistiken bei `--kopieren` leer**: Script gibt `=>` statt `->` aus – Parser erkennt jetzt beide Pfeile |
| G5 | Medium | **Theme-Wechsel**: 6 unregistrierte Labels (Titelleiste, macOS-Leiste, Vorschau-Label, Tabellen-Header, Statusbar) behielten alte Hintergrundfarbe |
| G6 | Medium | **Spinboxen** (Stunde/Minute im Cronjob-Tab) wurden beim Theme-Wechsel nicht eingefärbt |

---

## 📋 Versions-Übersicht

| Version | Feature |
|---------|---------|
| v1.0 | Sortierung nach Dateityp |
| v2.0 | Vorschau-Modus + Undo |
| v3.0 | Config-Datei + Log |
| v4.0 | Datum-Sortierung |
| v5.0 | Duplikate erkennen |
| v5.1 | Bugfix: Ungültige Ordnerpfade |
| v6.0 | Watch-Modus, Ignorier-Liste, Profile, Multi-Ordner |
| v6.1 | 8 Stabilitäts-Bugfixes |
| **v7.0** | **Cronjob-Assistent, Benachrichtigungen, Papierkorb, HTML-Bericht** |
| **v7.1** | **Bugfixes: Kollision in Sonstiges, Suffix bei Dateien ohne Erweiterung, toter Code entfernt** |
| GUI v1.0 | Grafische Oberfläche |
| GUI v2.0 | Stabilitätsverbesserungen |
| GUI v3.0 | Tabs, Vorschau-Tabelle, Statistiken |
| GUI v4.0 | Thread-Lock, Hintergrund-Vorschau, alle Crashes behoben |
| GUI v4.1 | 8 weitere Stabilitäts-Bugfixes |
| **GUI v5.0** | **Drag & Drop, Dark/Light Theme, Cronjob-Tab** |
| **GUI v5.1** | **Bugfixes: Statistiken bei --kopieren, Theme-Wechsel für Labels & Spinboxen** |

---

## 📦 Dateiübersicht

```
Datei-Sortierer/
├── datei_sortieren.sh   # Haupt-Script (v7.1)
├── gui.py               # Grafische Oberfläche (v5.1)
├── demo.html            # Browser-Demo
├── config.txt           # Kategorie-Konfiguration
├── ignore.txt           # Ignorier-Liste
├── profile/
│   ├── fotos.txt
│   ├── buero.txt
│   └── entwickler.txt
└── README.md
```

---

## ⚙️ Voraussetzungen

- Linux, macOS oder Windows mit Git Bash
- Bash 4.0+
- Python 3 (für GUI)
- `pip install tkinterdnd2` – optional, für echtes Drag & Drop
- `sudo apt install inotify-tools` – optional, für Echtzeit Watch-Modus (Linux)
- `sudo apt install libnotify-bin` – optional, für Benachrichtigungen (Linux)

## 📄 Lizenz

MIT License – frei verwendbar und veränderbar.
