# 📂 Datei-Sortierer

Ein Bash-basierter Datei-Sortierer mit optionaler Tkinter-GUI. Version **v9.0.1** erweitert die stabile Automation-Basis um deterministische intelligente Klassifizierung und konzentriert sich auf Stabilität, sichere Pfadbehandlung, reproduzierbare Tests und eine gemeinsame Sortier-Engine für CLI und GUI.

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



## 🚀 Installation

Eine ausführliche Schritt-für-Schritt-Anleitung befindet sich unter **[docs/INSTALLATION.md](docs/INSTALLATION.md)**.

### Schnellstart unter Windows

1. Lade **v9.0.1** von der [GitHub Release-Seite](https://github.com/Matrix-sudo1/Datei-Sortieren/releases/tag/v9.0.1) herunter.
2. Entpacke das Repository bzw. das bereitgestellte Paket.
3. Installiere **Python 3** und **Git for Windows / Git Bash**.
4. Öffne **Git Bash** im Projektordner.
5. Prüfe Python:
   ```bash
   python --version
   ```
6. Starte die GUI:
   ```bash
   python gui.py
   ```

> **Hinweis:** Der aktuelle v9.0.1-Stand benötigt keine `requirements.txt`. Die optionale Bibliothek `tkinterdnd2` wird nur für natives Drag & Drop benötigt.

### Linux / macOS

Python 3 und Bash müssen installiert sein. Anschließend:

```bash
chmod +x datei_sortieren.sh
python3 gui.py
```

Für die CLI:

```bash
./datei_sortieren.sh ~/Downloads --dry-run
```

### Erste sichere Nutzung

Für die erste Sortierung empfiehlt sich zunächst eine Vorschau:

```bash
./datei_sortieren.sh ~/Downloads --dry-run
```

Bei intelligentem Sortieren sollte zuerst die Vorschau geprüft werden. Das **Confirmation Gate** verhindert eine unbeabsichtigte Ausführung ohne ausdrückliche Bestätigung.

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
python3 api.py intelligent-preview ~/Downloads
python3 api.py intelligent-preview ~/Downloads --recursive
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

## v9.0 Intelligent Sorting

v9.0 führt eine deterministische Klassifizierungsschicht ein. Sie schlägt für jede reguläre Datei eine Kategorie, eine Konfidenz, eine Begründung und die verwendete Signalquelle vor.

Priorität der Signale:

1. explizite Dateiendung aus der geladenen Konfiguration → **Konfidenz 1.00**
2. ermittelter MIME-Typ → **Konfidenz 0.85**
3. konservative Dateinamen-Signale → **Konfidenz bis 0.65**
4. kein belastbares Signal → **Sonstiges / Konfidenz 0.00**

Die Klassifizierung ist absichtlich nur eine Vorschlagsinstanz. Sie verschiebt, löscht oder benennt keine Dateien. Damit bleibt die bestehende Bash-Sortierengine die alleinige Autorität für reale Dateioperationen und das bestehende Undo-Journal bleibt vollständig wirksam.

Der JSON-Endpunkt ist:

    python3 api.py intelligent-preview ~/Downloads
    python3 api.py intelligent-preview ~/Downloads --recursive
    python3 api.py intelligent-preview ~/Downloads --profile buero
    python3 api.py intelligent-preview ~/Downloads --config meine.txt
    python3 api.py intelligent-sort ~/Downloads --confirm

Jedes Ereignis enthält mindestens source, category, confidence, reason und die Signalquelle. Dadurch kann eine spätere GUI- oder Automationsschicht Vorschläge anzeigen oder anhand definierter Konfidenzgrenzen bewerten, ohne direkt in den Sortierkern einzugreifen.


## v9.0 Phase 5 – Intelligent Sort mit Confirmation Gate

`intelligent-sort` ist bewusst nicht automatisch ausführbar. Ohne `--confirm` wird ausschließlich ein maschinenlesbarer Confirmation-Gate-Status ausgegeben und keine Datei verändert. Mit `--confirm` werden standardmäßig nur Vorschläge mit der Confidence-Policy `auto` verarbeitet; `review` und `leave` bleiben unangetastet.

Die freigegebenen Vorschläge werden als temporärer, NUL-delimitierter Plan an die bestehende Bash-Sortierengine übergeben. Die Engine prüft Quelle, Ziel und Dateisignatur erneut und schreibt erfolgreiche Moves in das bestehende Undo-Journal. Python enthält damit weiterhin keinen zweiten Datei-Move-Mechanismus.

Die GUI verlangt vor dem intelligenten Sortieren eine ausdrückliche Bestätigung und sortiert ebenfalls nur die sicheren Vorschläge.


## v9.0 Phase 6 – Interaktiver Intelligent-Sort-Workflow

Die GUI zeigt intelligente Vorschläge jetzt als explizite Auswahlliste. Vorschläge mit hoher Konfidenz (**🟢 Sicher**) sind standardmäßig vorgewählt, mittlere Konfidenzen (**🟡 Prüfen**) können bewusst ausgewählt werden und niedrige Konfidenzen (**🔴 Nicht automatisch**) sind gesperrt.

Vor der Ausführung erzeugt die API einen deterministischen Plan-Hash. Beim Sortieren werden die Auswahl, Klassifizierung und aktuellen Dateisignaturen erneut geprüft. Ein veralteter Plan wird abgelehnt. Dadurch bleibt die Benutzerentscheidung nachvollziehbar und die bestehende Bash-Sortierengine weiterhin die einzige Instanz für tatsächliche Dateioperationen.


## v9.0 Phase 7 – Intelligent Sort Reports

Intelligent Sort schreibt zusätzlich einen strukturierten Bericht unter `.datei-sortierer/intelligent-report.json`. Der Bericht enthält Plan-Hash, Zeitstempel, Klassifizierungen, Auswahl und Engine-Ergebnis. Der Bericht wird atomar geschrieben und mit restriktiven Dateirechten angelegt. Auch ein reiner Confirmation-Preview erzeugt einen Bericht, ohne Dateien zu verändern.


## v9.0 Phase 8 – Deterministische Lernregeln

Phase 8 ergänzt ein explizites Feedback-System für intelligente Klassifizierung. Eine vom Benutzer bestätigte Korrektur kann als lokale Regel gespeichert werden. Lernregeln sind getrennt von der normalen `config.txt` und werden vor Extension-, MIME- und Dateinamen-Signalen ausgewertet.

Unter `.datei-sortierer/learning-rules.json` werden Regeln mit restriktiven Dateirechten und atomarem Replace gespeichert. Jede Regel enthält eine ID, Quelle (`extension`, `mime` oder `filename_token`), Muster, Zielkategorie, Aktivierungsstatus und Erstellungszeitpunkt. Python verschiebt weiterhin keine Dateien; die Bash-Engine bleibt alleinige Autorität für reale Sortiervorgänge.

Beispiele:

```bash
python3 api.py intelligent-rule-add ~/Downloads --source extension --pattern xyz --category Code --id ext-xyz-code
python3 api.py intelligent-rules ~/Downloads
python3 api.py intelligent-rule-remove ~/Downloads --id ext-xyz-code
```

In der GUI kann ein intelligenter Vorschlag über **Als Regel übernehmen** als dauerhafte Korrektur gespeichert werden. Die nächste Intelligent-Vorschau verwendet die Regel deterministisch und weist das verwendete `rule_id` aus.


## v9.0 Phase 9 – Rule Management & Explainability

Die Lernregeln können jetzt vollständig verwaltet werden. Über die JSON-API lassen sich Regeln auflisten, aktivieren/deaktivieren und löschen:

```bash
python3 api.py intelligent-rules ~/Downloads
python3 api.py intelligent-rule-set ~/Downloads --id ext-xyz-code --enabled false
python3 api.py intelligent-rule-set ~/Downloads --id ext-xyz-code --enabled true
python3 api.py intelligent-rule-remove ~/Downloads --id ext-xyz-code
```

Die API verhindert außerdem widersprüchliche Regeln mit identischer Quelle und identischem Muster. Dadurch bleibt die Regelauflösung deterministisch.

Die GUI besitzt einen eigenen **Lernregeln**-Tab. Dort werden Status, Quelle, Muster und Zielkategorie angezeigt; Regeln können aktiviert, deaktiviert oder gelöscht werden. Die Intelligent-Vorschau kann anschließend sofort erneut ausgeführt werden.

Die Explainability-Daten sind ebenfalls Bestandteil der intelligenten Klassifizierung und damit der Phase-7-Reports: Bei einer angewendeten Lernregel werden `signal=learning_rule`, `rule_id`, `rule_source` und eine menschenlesbare Begründung gespeichert.


## v9.0 Phase 10 – Release Hardening

Die Automation wurde für den Release-Kandidaten weiter gehärtet:

- Der API-Status akzeptiert einen gespeicherten PID-Eintrag nur noch, wenn /proc/<pid>/cmdline weiterhin exakt auf die erwartete Watch-Engine, den Zielordner und --watch zeigt.
- Bei PID-Wiederverwendung oder einem nicht mehr passenden Prozess wird der Automation-Status verworfen.
- Das Automation-Intervall ist über API und GUI zwischen 1 und 86400 Sekunden konfigurierbar.
- Die GUI kann für die Automation optional Profil, Config-Datei und Ignore-Datei übergeben.
- Die GUI führt Statusabfragen nicht mehr doppelt aus.

Damit bleibt die Automation nach einem Neustart bzw. bei einer PID-Wiederverwendung fail-closed, bevor Steuerbefehle an einen fremden Prozess gesendet werden.
