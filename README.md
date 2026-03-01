# 📂 Datei-Sortierer

Ein Bash-Script mit moderner GUI, das Dateien automatisch sortiert – stabil, geprüft und macOS/Linux/Windows-kompatibel.

---

## ✨ Features

- Sortiert Dateien nach **Dateityp** in Kategorien
- Sortiert Dateien nach **Erstelldatum** (Jahr/Monat)
- **Vorschau-Modus** – zeigt was passieren würde, ohne etwas zu verschieben
- **Rückgängig-Funktion** – letzte Sortierung rückgängig machen
- **Log anzeigen** – was wurde zuletzt sortiert?
- **Duplikate erkennen** – doppelte Dateien finden und entscheiden
- **Eigene Kategorien** via `config.txt` konfigurierbar
- **Moderne GUI** – grafische Oberfläche mit Python (Tabs, Vorschau-Tabelle, Statistiken)
- **Watch-Modus** – Ordner automatisch beobachten und sortieren
- **Ignorier-Liste** – bestimmte Dateien dauerhaft überspringen
- **Profile** – verschiedene Konfigurationen für verschiedene Zwecke
- **Multi-Ordner** – mehrere Ordner in einem Befehl sortieren

---

## 🖥️ GUI starten (empfohlen)

### Voraussetzungen
- [Python 3](https://python.org/downloads) installiert
- [Git Bash](https://git-scm.com/download/win) installiert (Windows)

### Starten
```bash
# Alle Dateien müssen im selben Ordner sein!
python gui.py
```

---

## 💻 Terminal-Verwendung

```bash
# Ausführbar machen (einmalig)
chmod +x datei_sortieren.sh

# Aktuellen Ordner sortieren
./datei_sortieren.sh

# Bestimmten Ordner sortieren
./datei_sortieren.sh ~/Downloads

# Vorschau anzeigen (nichts wird verschoben)
./datei_sortieren.sh ~/Downloads --dry-run

# Nach Datum sortieren (Jahr/Monat)
./datei_sortieren.sh ~/Downloads --nach-datum

# Duplikate suchen
./datei_sortieren.sh ~/Downloads --duplikate

# Letzte Sortierung rückgängig machen
./datei_sortieren.sh ~/Downloads --undo

# Log der letzten Sortierung anzeigen
./datei_sortieren.sh ~/Downloads --log

# Ordner beobachten & automatisch sortieren
./datei_sortieren.sh ~/Downloads --watch

# Mit eigenem Intervall (alle 30 Sekunden)
./datei_sortieren.sh ~/Downloads --watch --watch-interval 30

# Profil verwenden
./datei_sortieren.sh ~/Fotos --profil fotos

# Alle verfügbaren Profile anzeigen
./datei_sortieren.sh --profile-list

# Mehrere Ordner auf einmal
./datei_sortieren.sh --ordner ~/Downloads ~/Desktop ~/Dokumente

# Eigene Konfiguration
./datei_sortieren.sh --config meine_config.txt

# Hilfe anzeigen
./datei_sortieren.sh --help
```

---

## 🆕 Features ab v6.0

### 👁️ Watch-Modus (Automatische Sortierung)

Der Watch-Modus beobachtet einen Ordner und sortiert neue Dateien **automatisch** sobald sie auftauchen.

```bash
./datei_sortieren.sh ~/Downloads --watch
./datei_sortieren.sh ~/Downloads --watch --watch-interval 30
./datei_sortieren.sh ~/Downloads --watch --nach-datum
# Beenden: Strg+C
```

Falls `inotifywait` installiert ist, arbeitet der Watch-Modus in Echtzeit. Andernfalls greift ein Polling-Fallback.

```bash
# inotifywait für Echtzeit-Modus (Linux)
sudo apt install inotify-tools
```

### 🚫 Ignorier-Liste

Dateien oder Muster die nie sortiert werden sollen – in `ignore.txt` eintragen:

```
.DS_Store
Thumbs.db
*.tmp
*.bak
README.md
```

```bash
./datei_sortieren.sh ~/Downloads                        # nutzt ignore.txt automatisch
./datei_sortieren.sh ~/Downloads --ignore andere.txt    # eigene Liste
```

### 🗂️ Profile / Vorlagen

Fertige Profile für verschiedene Anwendungsfälle:

| Profil | Beschreibung |
|--------|-------------|
| `fotos` | RAW, HEIC, PSD, Kameraformate |
| `buero` | Rechnungen, Verträge, Tabellen |
| `entwickler` | Python, JS, Shell, SQL, Configs |

```bash
./datei_sortieren.sh ~/Fotos --profil fotos
./datei_sortieren.sh --profile-list         # alle Profile anzeigen
```

**Eigenes Profil** – Datei `profile/meinprofil.txt`:
```
Rechnungen=pdf
Vertraege=doc docx
Tabellen=xlsx csv
```

### 📁 Mehrere Ordner gleichzeitig

```bash
./datei_sortieren.sh --ordner ~/Downloads ~/Desktop ~/Dokumente
./datei_sortieren.sh --ordner ~/Downloads ~/Desktop --dry-run
# Ungültige Ordner werden übersprungen, kein Abbruch
```

---

## 🔧 Stabilitäts-Changelog

### Script v6.1 – 8 Bugs behoben

**`set -o pipefail` deaktiviert**
`pipefail` ließ `while read` Schleifen mit Exit-Code 1 am EOF enden und brach dadurch das Laden der Ignorier-Liste und Konfiguration ab. Behoben durch Entfernung.

**`tac` macOS-Fallback**
`tac` existiert nicht auf macOS – der Undo-Befehl hing bei jedem macOS-Nutzer. Automatischer Fallback auf `tail -r` wenn `tac` nicht verfügbar ist.

**Nullglob für leere Ordner**
Bash iteriert bei `for DATEI in "$ORDNER"/*` über den Literal-String `*` wenn keine Dateien vorhanden sind. Mit `shopt -s nullglob` wird die Schleife korrekt übersprungen. Betrifft Sortierung und Watch-Modus.

**`mv` und `mkdir -p` mit Fehlerprüfung**
Fehler beim Verschieben (z. B. kein Speicherplatz, Rechte) wurden still ignoriert. Jetzt werden sie mit klarer Fehlermeldung ausgegeben und im Zähler erfasst.

**Log-Format bei `|` im Dateinamen**
Dateinamen mit Pipe-Zeichen (`|`) haben das Log-Format (spaltengetrennt mit `|`) korrumpiert und den Undo unbrauchbar gemacht. Pipe-Zeichen werden jetzt im Log escaped.

**`read`-Timeout bei Duplikaten**
Im Duplikat-Modus wartete `read` ewig auf Eingabe wenn kein Terminal vorhanden war (z. B. GUI-Aufruf, Cronjob). Jetzt wird nach 30 Sekunden (Terminal) oder 5 Sekunden (kein TTY) automatisch „Überspringen" gewählt.

**`md5sum` auf nicht-lesbaren Dateien**
Ein leerer Hash-Key in der Hash-Map führte zu einem assoziativen Array-Fehler. Nicht-lesbare Dateien werden jetzt explizit übersprungen.

**Undo ohne Subshell-Verlust**
`tac "$LOGDATEI" | while read` lief in einer Subshell – Variablen wurden nicht in den Hauptprozess übertragen. Behoben durch temporäre Datei statt Pipe.

---

### GUI v4.1 – 8 Bugs behoben

**Doppel-Thread bei Vorschau**
Schnelles Doppelklicken auf „Vorschau laden" startete zwei parallele Scan-Threads. Mit einem separaten `threading.Lock()` für den Vorschau-Zustand ist das ausgeschlossen.

**`_buttons_sperren` crashte beim ersten Aufruf**
`undo_btn` und `log_btn` werden erst beim Aufbau des Verlauf-Tabs erstellt. Wenn `_buttons_sperren` vorher aufgerufen wurde (z. B. direkt nach Start), gab es einen `AttributeError`. Behoben mit `getattr(..., None)`.

**`_script_aktion` ohne Encoding-Fallback**
Undo und Log-Anzeige hatten kein `cp1252`-Fallback für Windows-Systeme, nur die Haupt-Sortierung. Jetzt überall einheitlich.

**Verlauf-Log unbegrenztes Wachstum**
Das `Text`-Widget wuchs bei langen Sessions unbegrenzt und verbrauchte RAM. Jetzt werden ältere Zeilen automatisch gelöscht wenn das Limit von 2000 Zeilen überschritten wird.

**Widget-Referenz in `_nach` schon zerstört**
`self._nach(self.status_text.configure, ...)` übergab eine Referenz auf das Widget zum Zeitpunkt des Aufrufs aus dem Thread. Wenn das Fenster bis zur Ausführung geschlossen wurde, gab es einen `TclError`. Behoben durch `lambda: self._ui(...)`.

**Vorschau-Reload startete neuen Prozess**
Nach der Sortierung wurde `_vorschau_laden` aufgerufen, obwohl möglicherweise schon ein neuer Prozess gestartet war. Guard-Lambda verhindert jetzt den Reload wenn `laeuft=True`.

**Tab-Wechsel war blockiert**
Während einer Sortierung konnten keine Tabs gewechselt werden außer „Verlauf". Nach dem Ende kam man nicht mehr zurück zu „Sortieren". Jetzt sind alle Tabs immer frei zugänglich.

**`_undo` sperrte Buttons nicht**
Undo lief als leichtgewichtiger Script-Aufruf ohne Button-Sperre – ein zweites Klicken während Undo lief startete einen zweiten Prozess. Jetzt über `_script_aktion` mit vollständiger Button-Sperre.

---

### 🧪 Testergebnisse (aktuell)

| Test | Script v6.1 | GUI v4.1 |
|------|------------|---------|
| Syntax-Prüfung | ✅ | ✅ |
| Leerzeichen in Ordnerpfaden | ✅ | – |
| Sonderzeichen in Dateinamen | ✅ | – |
| Leerer Ordner (nullglob) | ✅ | – |
| watch-interval Validierung | ✅ | – |
| Log-Format bei `\|` in Dateinamen | ✅ | – |
| Sortierung + Undo vollständig | ✅ | – |
| Path-Traversal bei `--profil` | ✅ | – |
| Gleichzeitige Dry-Runs (3 parallel) | ✅ | – |
| Thread-Lock (20 parallele Zugriffe) | – | ✅ |
| Vorschau-Doppelklick-Schutz | – | ✅ |
| Encoding-Fallback cp1252 | – | ✅ |
| Log-Limit bei 2000 Zeilen | – | ✅ |
| hasattr-Schutz für UI-Buttons | – | ✅ |
| Lambda-Schutz Widget-Referenz | – | ✅ |

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

## ⚙️ config.txt anpassen

```
# Format: KategorieName=endung1 endung2 endung3
Spiele=rom iso nds gba
Bilder=jpg jpeg png gif heic raw
```

---

## 📋 Versions-Übersicht

| Version | Feature |
|---------|---------|
| v1.0 | Sortierung nach Dateityp |
| v2.0 | Vorschau-Modus + Undo |
| v3.0 | Config-Datei + Log anzeigen |
| v4.0 | Datum-Sortierung |
| v5.0 | Duplikate erkennen |
| v5.1 | Bugfix: Ungültige Ordnerpfade abgefangen |
| v6.0 | Watch-Modus, Ignorier-Liste, Profile, Multi-Ordner |
| **v6.1** | **8 Stabilitäts-Bugfixes: pipefail, tac, nullglob, mv-Fehler, Log-Format, read-Timeout, md5sum, Undo-Subshell** |
| GUI v1.0 | Grafische Oberfläche mit Python |
| GUI v2.0 | Stabilitätsverbesserungen |
| GUI v3.0 | Neues Design: Tabs, Vorschau-Tabelle, Statistiken |
| GUI v4.0 | Thread-Lock, returncode-Fix, Hintergrund-Vorschau, Undo-Schutz |
| **GUI v4.1** | **8 Stabilitäts-Bugfixes: Doppel-Thread, Button-Crash, Encoding, Log-Limit, Widget-Ref, Tab-Lock, Undo-Sperre** |

---

## 📦 Dateiübersicht

```
Datei-Sortierer/
├── datei_sortieren.sh   # Haupt-Script (v6.1)
├── gui.py               # Grafische Oberfläche (v4.1)
├── demo.html            # Browser-Demo (kein Python nötig)
├── config.txt           # Kategorie-Konfiguration
├── ignore.txt           # Ignorier-Liste
├── profile/
│   ├── fotos.txt        # Profil für Foto-Sammlungen
│   ├── buero.txt        # Profil für Büro-Dokumente
│   └── entwickler.txt   # Profil für Programmierer
└── README.md
```

---

## ⚙️ Voraussetzungen

- Linux, macOS oder Windows mit Git Bash
- Bash 4.0 oder höher
- Python 3 (nur für die GUI)
- `inotify-tools` optional – für Echtzeit Watch-Modus unter Linux (`sudo apt install inotify-tools`)

## 📄 Lizenz

MIT License – frei verwendbar und veränderbar.
