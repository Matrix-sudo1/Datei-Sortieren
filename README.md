# 📂 Datei-Sortierer

Ein Bash-Script mit moderner GUI, das Dateien automatisch sortiert.

## ✨ Features

- Sortiert Dateien nach **Dateityp** in Kategorien
- Sortiert Dateien nach **Erstelldatum** (Jahr/Monat)
- **Vorschau-Modus** – zeigt was passieren würde, ohne etwas zu verschieben
- **Rückgängig-Funktion** – letzte Sortierung rückgängig machen
- **Log anzeigen** – was wurde zuletzt sortiert?
- **Duplikate erkennen** – doppelte Dateien finden und manuell entscheiden
- **Eigene Kategorien** via `config.txt` konfigurierbar
- **Moderne GUI** – grafische Oberfläche mit Python (Tabs, Vorschau-Tabelle, Statistiken)

---

## 🖥️ GUI starten (empfohlen)

### Voraussetzungen
- [Python 3](https://python.org/downloads) installiert
- [Git Bash](https://git-scm.com/download/win) installiert (Windows)

### Starten
```bash
# Beide Dateien müssen im selben Ordner sein!
python gui.py
```

### GUI v4.0 – Stabilitätsverbesserungen

Die GUI wurde in mehreren Iterationen grundlegend stabiler gemacht. Alle bekannten Absturzursachen wurden behoben:

**Mehrfachklick-Schutz**
Alle Buttons werden automatisch gesperrt sobald ein Prozess läuft. Ein versehentlicher Doppelklick startet den Prozess nicht mehr mehrfach.

**Abbrechen-Button**
Während ein Prozess läuft erscheint automatisch ein roter "Abbrechen"-Button. Damit kann jede Aktion jederzeit sauber gestoppt werden.

**Thread-Lock gegen Race Conditions**
Der `laeuft`-Zustand wird über eine thread-sichere Property mit `threading.Lock()` geschützt. Gleichzeitige Zugriffe aus mehreren Threads können den Zustand nicht mehr korrumpieren.

**`returncode` immer definiert**
Vorher konnte der Rückgabewert des Prozesses undefiniert sein wenn eine Exception vor `proc.wait()` auftrat. Jetzt wird er immer auf `-1` initialisiert.

**Vorschau läuft im Hintergrund**
Das Laden der Vorschau-Tabelle bei großen Ordnern lief vorher im Hauptthread und fror die GUI ein. Jetzt läuft es im Hintergrund-Thread.

**Sichere Thread-Kommunikation**
UI-Updates werden nur noch ausgeführt wenn das Fenster noch offen ist. Kein Absturz mehr beim schnellen Schließen während eine Aktion läuft.

**Automatische Windows Bash-Erkennung**
Das Programm sucht Git Bash automatisch in allen gängigen Windows-Installationspfaden. Falls Git Bash nicht gefunden wird, erscheint eine klare Fehlermeldung mit Installationslink.

**Encoding-Schutz**
Verhindert Abstürze bei Dateien mit Sonderzeichen oder Umlauten im Dateinamen.

**Undo-Schutz bei leerem Pfad**
Undo stürzte ab wenn kein Ordner ausgewählt war. Jetzt erscheint eine Warnung.

**Scrollbare Vorschau-Tabelle**
Die Tabelle hat jetzt eine Scrollbar und ein Speicherleck beim Neuladen wurde behoben.

**Sicheres Beenden mit Timeout**
Wenn das Programm geschlossen wird während noch ein Prozess läuft, erscheint eine Sicherheitsfrage. Das Programm wartet bis zu 3 Sekunden auf sauberes Beenden, danach wird der Prozess hart beendet.

**Bash-Status in der Statusleiste**
Unten rechts zeigt die GUI permanent an ob Git Bash gefunden wurde.

---

### 🧪 Testergebnisse (GUI v4.0)

Alle kritischen Funktionen wurden automatisch getestet:

| Test | Ergebnis |
|------|---------|
| Python Syntax | ✅ Keine Fehler |
| Kategorie-Erkennung (14 Tests) | ✅ Alle bestanden |
| Bash & Script Erkennung | ✅ Gefunden |
| Thread-Lock (20 parallele Zugriffe) | ✅ Keine Race Condition |
| Dry-Run (Vorschau) | ✅ Nichts verschoben |
| Sortierung (9 Dateien) | ✅ Alle korrekt sortiert |
| Undo | ✅ Alle Dateien wiederhergestellt |
| Datum-Sortierung | ✅ Korrekt (Jahr/Monat) |
| Fehlerbehandlung | ✅ Klare Fehlermeldungen |
| Statische Code-Analyse | ✅ Keine gefährlichen Muster |

---

## 💻 Terminal-Verwendung

```bash
# Ausführbar machen (einmalig)
chmod +x datei_sortieren.sh

# Aktuellen Ordner sortieren
./datei_sortieren.sh

# Bestimmten Ordner sortieren
./datei_sortieren.sh /home/user/Downloads

# Vorschau anzeigen (nichts wird verschoben)
./datei_sortieren.sh --dry-run

# Nach Datum sortieren (Jahr/Monat)
./datei_sortieren.sh --nach-datum

# Duplikate suchen
./datei_sortieren.sh --duplikate

# Letzte Sortierung rückgängig machen
./datei_sortieren.sh --undo

# Log der letzten Sortierung anzeigen
./datei_sortieren.sh --log

# Eigene Konfiguration verwenden
./datei_sortieren.sh --config meine_config.txt

# Hilfe anzeigen
./datei_sortieren.sh --help
```

---

## 🐛 Bugfixes (Script v5.1)

**Ungültige Ordnerpfade werden korrekt abgefangen**
Vorher ignorierte das Script einen ungültigen Ordnerpfad still und lief stattdessen im aktuellen Verzeichnis weiter. Jetzt bricht das Script sofort mit einer klaren Fehlermeldung ab:

```
Fehler: Ordner '/pfad/existiert/nicht' nicht gefunden.
Tipp: Nutze --help fuer alle Optionen.
```

---

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

---

## ⚙️ config.txt anpassen

Eigene Kategorien einfach in der `config.txt` definieren:
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
| GUI v1.0 | Grafische Oberfläche mit Python |
| GUI v2.0 | Stabilitätsverbesserungen |
| GUI v3.0 | Neues Design: Tabs, Vorschau-Tabelle, Statistiken |
| GUI v4.0 | Alle Absturzursachen behoben, vollständig getestet |

---

## ⚙️ Voraussetzungen

- Linux, macOS oder Windows mit Git Bash
- Bash 4.0 oder höher
- Python 3 (nur für die GUI)

## 📄 Lizenz

MIT License – frei verwendbar und veränderbar.
