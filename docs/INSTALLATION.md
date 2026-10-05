# 📦 Datei-Sortierer v9.0.0 – Installation

Diese Anleitung zeigt die Installation des **Datei-Sortierers v9.0.0** Schritt für Schritt.

> **Wichtig:** Der Release v9.0.0 enthält aktuell den Quellcode als GitHub-Download. Es gibt kein separates Windows-.exe-Installationsprogramm. Unter Windows wird deshalb **Python 3 + Git Bash** verwendet.

---

## 🖥️ 1. Release öffnen

Öffne die offizielle Release-Seite:

**https://github.com/Matrix-sudo1/Datei-Sortieren/releases/tag/v9.0.0**

Dort findest du den aktuellen Stable Release:

**Datei-Sortierer v9.0.0**

### Was herunterladen?

Unter **Assets** stehen die automatisch erzeugten GitHub-Archive:

- **Source code (zip)** → empfohlen für Windows
- **Source code (tar.gz)** → alternativ für Linux/macOS

---

## 📥 2. ZIP-Datei herunterladen

Unter **Assets** auf **Source code (zip)** klicken.

Die Datei wird normalerweise im Ordner **Downloads** gespeichert.

---

## 📂 3. ZIP-Datei entpacken

1. Öffne den Downloads-Ordner.
2. Rechtsklick auf die ZIP-Datei.
3. **Alle extrahieren…** auswählen.
4. Einen gut erreichbaren Ordner auswählen, z. B. den Desktop.

Danach befindet sich der Projektordner auf deinem Rechner.

---

## 🪟 4. Windows vorbereiten

Für die Windows-Nutzung werden benötigt:

### Python 3

Python herunterladen:

**https://www.python.org/downloads/**

Bei der Windows-Installation unbedingt:

**☑ Add Python to PATH**

aktivieren.

### Git Bash

Git for Windows herunterladen:

**https://git-scm.com/download/win**

Git Bash wird benötigt, weil die eigentliche Sortierengine ein **Bash-Skript** ist.

---

## 💻 5. Git Bash im Projektordner öffnen

Öffne den entpackten Datei-Sortierer-Ordner.

Am einfachsten:

1. Ordner öffnen.
2. In die Adressleiste klicken.
3. **cmd** eingeben und Enter drücken.

Alternativ kann **Git Bash Here** verwendet werden, wenn diese Option bei deiner Git-Installation vorhanden ist.

---

## 🔎 6. Python überprüfen

Im Terminal:

~~~~bash
python --version
~~~~

Es sollte eine Python-3-Version angezeigt werden, zum Beispiel:

~~~~text
Python 3.12.x
~~~~

Falls **python** nicht gefunden wird, prüfe alternativ:

~~~~bash
python3 --version
~~~~

---

## 🧩 7. Abhängigkeiten

Der aktuelle v9.0.0-Stand benötigt **keine requirements.txt und keine externen Python-Pakete für den normalen Betrieb**.

Die GUI verwendet Tkinter, das bei einer normalen Windows-Python-Installation üblicherweise enthalten ist.

**Optional:** tkinterdnd2 kann für natives Drag & Drop installiert werden:

~~~~bash
python -m pip install tkinterdnd2
~~~~

Wenn du Drag & Drop nicht benötigst, kannst du diesen Schritt überspringen.

---

## ▶️ 8. GUI starten

Im Projektordner:

~~~~bash
python gui.py
~~~~

Falls dein System **python3** verwendet:

~~~~bash
python3 gui.py
~~~~

Jetzt sollte sich die grafische Oberfläche des **Datei-Sortierers v9.0** öffnen.

---

## 📁 9. Ersten Ordner auswählen

In der GUI:

1. Zielordner auswählen.
2. Vorschau/Analyse starten.
3. Ergebnisse kontrollieren.
4. Beim intelligenten Sortieren die vorgeschlagenen Aktionen prüfen.
5. Erst danach die Sortierung bestätigen.

### 🛡️ Wichtig

Der Datei-Sortierer besitzt ein **Confirmation Gate**.

Die intelligente Sortierung soll nicht einfach blind Dateien verschieben. Vorschläge werden zunächst bewertet und angezeigt. Dadurch kannst du die Entscheidung vor der tatsächlichen Dateioperation kontrollieren.

---

## 🧪 10. Erste CLI-Vorschau

Wer lieber über die Kommandozeile arbeitet, kann zunächst einen sicheren Dry-Run durchführen:

~~~~bash
./datei_sortieren.sh ~/Downloads --dry-run
~~~~

Dabei werden keine Dateien tatsächlich verschoben.

Eine normale Sortierung kann anschließend beispielsweise so gestartet werden:

~~~~bash
./datei_sortieren.sh ~/Downloads
~~~~

---

## 🧠 11. Intelligent Sorting

Für eine intelligente Vorschau:

~~~~bash
python3 api.py intelligent-preview ~/Downloads
~~~~

Mit Unterordnern:

~~~~bash
python3 api.py intelligent-preview ~/Downloads --recursive
~~~~

Intelligente Vorschläge enthalten unter anderem:

- Kategorie
- Confidence
- Begründung
- Signalquelle

Die Bash-Sortierengine bleibt die alleinige Instanz für tatsächliche Dateioperationen.

---

## 📊 12. Reports

Intelligente Sortierungen können einen strukturierten Bericht unter:

~~~~text
.datei-sortierer/intelligent-report.json
~~~~

erzeugen.

Dieser Bericht enthält unter anderem:

- Plan-Hash
- Zeitstempel
- Klassifizierungen
- Auswahl
- Ergebnis der Sortierengine

---

## 🧠 13. Lernregeln

Bestätigte Korrekturen können als lokale Lernregeln gespeichert werden.

Die Regeln liegen unter:

~~~~text
.datei-sortierer/learning-rules.json
~~~~

Beispiel:

~~~~bash
python3 api.py intelligent-rules ~/Downloads
~~~~

---

## 🔐 14. Sicherheit

Der Datei-Sortierer wurde für v9.0.0 umfangreich gehärtet.

Besonders wichtig:

- Dry-Run / Vorschau
- Confirmation Gate
- erneute Validierung vor Dateioperationen
- Symlink-Schutz
- Undo-Journal
- deterministische Klassifizierung
- Plan-Hash für intelligente Sortierung
- gehärtete Automation-PID-Prüfung
- Regressionstests

**Trotzdem gilt:** Bei wichtigen Dateien immer zuerst eine Vorschau durchführen und ein Backup behalten.

---

## ❓ 15. Häufige Probleme

### **python: command not found**

Python ist nicht korrekt installiert oder nicht im PATH.

Prüfen:

~~~~bash
python --version
python3 --version
~~~~

---

### **bash: ./datei_sortieren.sh: Permission denied**

Unter Linux/macOS:

~~~~bash
chmod +x datei_sortieren.sh
~~~~

Danach:

~~~~bash
./datei_sortieren.sh ~/Downloads --dry-run
~~~~

---

### **GUI startet nicht**

Zuerst Python prüfen:

~~~~bash
python --version
~~~~

Danach:

~~~~bash
python gui.py
~~~~

Unter Linux kann zusätzlich das Tkinter-Systempaket benötigt werden.

---

### **Drag & Drop funktioniert nicht**

Drag & Drop ist optional.

Installiere bei Bedarf:

~~~~bash
python -m pip install tkinterdnd2
~~~~

Die GUI kann auch ohne diese Erweiterung verwendet werden.

---

## 🆘 Hilfe

Wenn ein Problem auftritt, öffne ein GitHub Issue:

**https://github.com/Matrix-sudo1/Datei-Sortieren/issues**

Füge möglichst hinzu:

- Betriebssystem
- Python-Version
- verwendeten Befehl
- vollständige Fehlermeldung
- relevanten Screenshot

---

## ✅ Installation abgeschlossen

Wenn die GUI startet und du einen Ordner analysieren kannst, ist der **Datei-Sortierer v9.0.0** einsatzbereit.

**Stable Release:** v9.0.0

**Release:** https://github.com/Matrix-sudo1/Datei-Sortieren/releases/tag/v9.0.0
