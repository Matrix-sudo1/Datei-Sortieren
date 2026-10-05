# 📂 Datei-Sortierer

Ein Bash-basierter Datei-Sortierer mit optionaler Tkinter-GUI. Version **v8.8** konzentriert sich auf Stabilität, sichere Pfadbehandlung, reproduzierbare Tests und eine gemeinsame Sortier-Engine für CLI und GUI.

## Kernfunktionen

- Sortierung nach Dateityp
- Sortierung nach Datum
- Dry-Run / Vorschau
- Undo der letzten Sortierung
- Protokollierung
- Duplikaterkennung
- eigene Kategorien über `config.txt`
- Profile: `fotos`, `buero`, `entwickler`
- Ignorier-Liste
- rekursive Sortierung
- mehrere Ordner
- Watch-Modus und Benachrichtigungen
- Cronjob-Verwaltung auf Linux/macOS
- HTML-Bericht
- optionale Tkinter-GUI mit Drag & Drop und Dark/Light Theme

## CLI

```bash
chmod +x datei_sortieren.sh

./datei_sortieren.sh ~/Downloads
./datei_sortieren.sh ~/Downloads --dry-run
./datei_sortieren.sh ~/Downloads --nach-datum
./datei_sortieren.sh ~/Downloads --unterordner
./datei_sortieren.sh ~/Downloads --undo
./datei_sortieren.sh ~/Downloads --duplikate

./datei_sortieren.sh ~/Fotos --profil fotos
./datei_sortieren.sh ~/Dokumente --profil buero
./datei_sortieren.sh ~/Projekt --profil entwickler
./datei_sortieren.sh --profile-list

./datei_sortieren.sh ~/Downloads --config meine.txt
./datei_sortieren.sh ~/Downloads --ignore meine_ignore.txt

./datei_sortieren.sh --ordner ~/Downloads ~/Desktop
./datei_sortieren.sh ~/Downloads --watch --notify
./datei_sortieren.sh ~/Downloads --cronjob 20:00
./datei_sortieren.sh --cronjob-list
./datei_sortieren.sh --cronjob-remove
./datei_sortieren.sh ~/Downloads --bericht
./datei_sortieren.sh --help
```

## Konfiguration

Eigene Kategorien verwenden das Format:

```text
Bilder=jpg jpeg png gif
Dokumente=pdf doc docx txt
Code=py js ts sh
```

Kategorien werden validiert, damit keine absoluten Pfade, Pfadtrenner oder andere ungültige Kategorienamen als Zielverzeichnisse verwendet werden.

Die mitgelieferten Profile verwenden dasselbe Format und werden von der Bash-Engine direkt geladen.

## JSON-API

v8.8 erweitert den stabilen Maschinenzugang über `api.py`. Die API verwendet die Bash-Engine weiterhin als einzige Sortierlogik und liefert strukturierte JSON-Antworten mit Ereignissen.

```bash
python3 api.py preview ~/Downloads
python3 api.py sort ~/Downloads --recursive
python3 api.py undo ~/Downloads
python3 api.py log ~/Downloads
python3 api.py config config.txt
python3 api.py profiles
python3 api.py automation-start ~/Downloads --recursive
python3 api.py automation-status ~/Downloads
python3 api.py automation-pause ~/Downloads
python3 api.py automation-resume ~/Downloads
python3 api.py automation-stop ~/Downloads
python3 api.py config-save config.txt --content 'Bilder=jpg png\nDokumente=pdf txt'
```

Die Engine kann dafür optionale NDJSON-Ereignisse über `--json` ausgeben. Dadurch muss die GUI keine menschenlesbare CLI-Ausgabe mehr parsen.

## GUI

```bash
python gui.py
```

Voraussetzungen:

- Python 3
- Bash
- unter Windows: Git Bash
- optional `tkinterdnd2` für natives Drag & Drop

### Engine-basierte Vorschau

Die GUI berechnet die Vorschau nicht mehr mit einer eigenen Kopie der Kategorien. Sie ruft die eigentliche Sortier-Engine im `--dry-run` auf.

Seit v8.5 laufen auch Sortieren, Undo und Log der GUI über `api.py`. Seit v8.6 gibt es zusätzlich einen validierten Konfigurationseditor in der GUI; Lesen, Validieren und Speichern laufen ebenfalls über die JSON-API. Damit ist die GUI vollständig vom menschenlesbaren Bash-Output entkoppelt. Vorschau und reale Sortierung verwenden dieselbe Engine und dieselbe JSON-Schnittstelle.

Damit verwenden Vorschau und reale Sortierung dieselbe:

- Kategoriezuordnung
- Konfiguration
- Kollisionslogik
- Ignore-Logik
- rekursive Behandlung

Das verhindert, dass GUI und CLI unterschiedliche Ergebnisse anzeigen.

## Sicherheit

v8.0 behandelt insbesondere folgende Bereiche als sicherheitsrelevant:

- Cronjob-Shell-Quoting
- Pfad- und Kategorienvalidierung
- Symlink-Behandlung
- temporäre Dateien
- HTML-Escaping
- Benachrichtigungsparameter
- Undo-Verhalten

Die Anwendung verändert keine Symlinks als Quelldateien. Cronjob-Pfade werden vor dem Eintrag in `crontab` shell-sicher quotiert.

## Tests

Automatisierte Regressionstests befinden sich unter:

```text
tests/test_regression.sh
```

GitHub Actions führt sie bei Pushes auf `main` sowie bei Pull Requests gegen `main` aus.

Der Testumfang umfasst aktuell:

- Bash- und Python-Syntax
- Standardsortierung
- Profile
- rekursive Sortierung
- Schutz gegen erneute Verarbeitung erzeugter Zielordner
- maschinenlesbare JSON-Fehlerfälle
- Konfigurationsvalidierung und crash-sicheres atomisches Speichern
- Pending-Journal und Integritaetspruefung beim Undo
- TOCTOU-/Race-Schutz fuer Quelldateien und Symlink-Ablehnung beim Undo
- GUI-Konfigurationseditor über die JSON-API
- Watch-Engine mit Event- und Polling-Fallback
- verwaltete Automation mit Start/Stop/Pause/Fortsetzen/Status
- Profil-Liste über die JSON-API

Zusätzlich werden die JSON-API, Sonderzeichen im Journal, Pending-Journals, beschaedigte Journals und der NUL-delimitierte Log-Reader regressionsgeprüft.

## Projektstruktur

```text
Datei-Sortierer/
├── datei_sortieren.sh
├── gui.py
├── api.py
├── config.txt
├── ignore.txt
├── profile/
│   ├── fotos.txt
│   ├── buero.txt
│   └── entwickler.txt
├── tests/
│   └── test_regression.sh
├── .github/
│   └── workflows/
│       └── tests.yml
├── SECURITY.md
├── SECURITY_PATCHES.md
└── README.md
```

## Plattformen

- Linux
- macOS
- Windows mit Git Bash

Watch-Funktionen und Cronjobs hängen von den jeweiligen Betriebssystemwerkzeugen ab. Unter Windows sollte die Aufgabenplanung für geplante Sortierungen verwendet werden.

## Lizenz

MIT License.


## v8.7 Security & Reliability

v8.7 fuehrt ein zweistufiges Journal ein: Eine laufende Sortierung schreibt zuerst in `.sortier_log.txt.pending`. Erst nach dem Sortierlauf wird dieses Journal atomar als aktives Undo-Journal uebernommen. Dadurch wird ein bestehendes funktionierendes Journal bei einem Prozessabbruch nicht vorzeitig zerstoert.

Vor einer Dateioperation wird die Quelldatei erneut auf Existenz, Symlink-Status und eine Signatur aus Device/Inode/Groesse/mtime geprueft. Aenderungen zwischen Erkennung und Operation fuehren zum Abbruch der betreffenden Datei.

Undo und Log-Anzeige validieren das NUL-delimitierte Journal und lehnen unvollstaendige Datensaetze ab. Symlinks werden beim Undo nicht als wiederherzustellende Quelldateien akzeptiert.

Die JSON-API speichert Konfigurationen weiterhin atomar, verwendet dafuer aber einen eindeutigen temporaeren Dateinamen im Zielverzeichnis, synchronisiert den Inhalt vor dem Replace und verweigert das direkte Ersetzen eines bestehenden Config-Symlinks.


## v8.8 Automation

Die JSON-API kann den Watch-Modus als verwalteten Hintergrundprozess starten und kontrollieren. Der Prozess erhält eine eigene Session, schreibt sein Laufzeitprotokoll unter `.datei-sortierer/automation.log` und seinen Zustand unter `.datei-sortierer/automation.json`.

Beispiele:

```bash
python3 api.py automation-start ~/Downloads --recursive
python3 api.py automation-status ~/Downloads
python3 api.py automation-pause ~/Downloads
python3 api.py automation-resume ~/Downloads
python3 api.py automation-stop ~/Downloads
```

Die GUI enthält dafür einen eigenen **Automation**-Tab. Der bestehende Sortierkern bleibt unverändert die zentrale Quelle für Sortierentscheidungen.

Die Zustandsdatei enthält nur PID, Status, Zielordner, Optionen und Startzeit. Sie wird mit restriktiven Dateirechten geschrieben und atomar ersetzt.
