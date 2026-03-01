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
- **Moderne GUI** – grafische Oberfläche mit Python

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

### GUI v2.0 – Stabilitätsverbesserungen

Die GUI wurde grundlegend stabiler gemacht. Folgende Probleme wurden behoben:

**Mehrfachklick-Schutz**
Alle Buttons werden automatisch gesperrt sobald ein Prozess läuft. Ein versehentlicher Doppelklick startet den Prozess nicht mehr mehrfach.

**Abbrechen-Button**
Während ein Prozess läuft erscheint automatisch ein roter "Abbrechen"-Button. Damit kann jede Aktion jederzeit sauber gestoppt werden.

**Sichere Thread-Kommunikation**
UI-Updates werden nur noch ausgeführt wenn das Fenster noch offen ist. Kein Absturz mehr beim schnellen Schließen des Programms während eine Aktion läuft.

**Automatische Windows Bash-Erkennung**
Das Programm sucht Git Bash automatisch in allen gängigen Windows-Installationspfaden. Falls Git Bash nicht gefunden wird, erscheint eine klare Fehlermeldung mit Installationslink.

**Encoding-Schutz**
Verhindert Abstürze bei Dateien mit Sonderzeichen oder Umlauten im Dateinamen.

**Bessere Fehlermeldungen**
Klare Fehlerdialoge wenn Bash, Script oder der gewählte Ordner nicht gefunden werden – statt eines Absturzes.

**Sicheres Beenden**
Wenn das Programm geschlossen wird während noch ein Prozess läuft, erscheint eine Sicherheitsfrage. Der Prozess wird sauber beendet bevor das Programm sich schließt.

**Startup-Diagnose**
Beim Start zeigt die GUI sofort an ob Bash und das Script gefunden wurden – so sieht man auf einen Blick ob alles bereit ist.

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
| GUI v1.0 | Grafische Oberfläche mit Python |
| GUI v2.0 | Stabilitätsverbesserungen |

---

## ⚙️ Voraussetzungen

- Linux, macOS oder Windows mit Git Bash
- Bash 4.0 oder höher
- Python 3 (nur für die GUI)

## 📄 Lizenz

MIT License – frei verwendbar und veränderbar.
