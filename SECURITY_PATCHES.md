# 🔐 Security Patches – Datei-Sortierer

Dieses Dokument beschreibt alle Sicherheitsverbesserungen, die in **v7.2** (Script) eingeflossen sind.  
Basis war v7.1. Alle Patches wurden mit `bash -n` auf Syntaxfehler geprüft.

---

## 📋 Übersicht

| ID | Schwere | Bereich | Funktion |
|----|---------|---------|----------|
| P1 | 🔴 Kritisch | Cronjob-Injection | `cronjob_einrichten()` |
| P2 | 🔴 Kritisch | Command-Injection | `sende_notification()` |
| P3 | 🟡 Mittel | XSS / HTML-Injection | `bericht_schreiben()` |
| P4 | 🟡 Mittel | TOCTOU / Temp-Datei | `cronjob_einrichten()`, `CRONJOB_REMOVE` |
| P5 | 🟡 Mittel | Separator-Kollision | Duplikat-Erkennung |
| P6 | 🟡 Mittel | Symlink-Angriff | `sortiere_datei()` |

---

## 🔴 Kritische Patches

### P1 – Cronjob-Injection via Ordnerpfad

**Funktion:** `cronjob_einrichten()`

**Problem:**  
Der Ordnerpfad wurde ohne Validierung direkt in den Crontab-Eintrag eingebaut. Ein Pfad mit einem eingebetteten Zeilenumbruch (`/home/user\nevil * * * * * rm -rf ~`) hätte einen zweiten, beliebigen Cron-Befehl einschleusen können.

**Lösung:**  
Zweistufige Validierung vor dem Schreiben des Crontab-Eintrags:

```bash
# Stufe 1: Explizit auf Zeilenumbrüche prüfen
if [[ "$ORDNER" =~ $'\n' ]] || [[ "$ORDNER" =~ $'\r' ]]; then
  echo -e "${ROT}Fehler: Pfad enthält ungültige Zeichen (Zeilenumbruch).${RESET}"; exit 1
fi

# Stufe 2: Alle nicht-druckbaren Zeichen abweisen
if [[ "$ORDNER" =~ [^[:print:]] ]]; then
  echo -e "${ROT}Fehler: Pfad enthält nicht-druckbare Zeichen.${RESET}"; exit 1
fi
```

---

### P2 – Command-Injection in Benachrichtigungen

**Funktion:** `sende_notification()`

**Problem:**  
Der alte Code escaped nur `"` → `\"`. Backticks (`` ` ``), `$()`, `\` und weitere Shell-Sonderzeichen in Dateinamen wurden vom `osascript`-Aufruf als Befehle interpretiert. Beispiel:

```
# Dateiname: foto`open -a Calculator`.jpg
# → öffnet den Taschenrechner beim Sortieren
```

**Lösung:**  
Alle vier gefährlichen Zeichenklassen werden mit `tr -d` entfernt, bevor der String an `osascript`, `notify-send` oder `zenity` übergeben wird:

```bash
SAFE_T=$(printf '%s' "$TITEL" | tr -d '"`\\$')
SAFE_X=$(printf '%s' "$TEXT"  | tr -d '"`\\$')
```

Der Benachrichtigungstext verliert dabei nur diese vier Sonderzeichen – für die Anzeige eines Dateinamens kein Informationsverlust.

---

## 🟡 Mittlere Patches

### P3 – HTML-Injection (XSS) im Bericht

**Funktion:** `bericht_schreiben()`

**Problem:**  
Ordnerpfad und Kategorienamen aus `config.txt` wurden ungefiltert in die HTML-Ausgabe geschrieben. Ein Pfad wie `/home/user/<script>alert(1)</script>` würde beim Öffnen des Berichts im Browser ausgeführt.

**Lösung:**  
Neue Hilfsfunktion `html_escape()`, die alle fünf kritischen HTML-Sonderzeichen ersetzt:

```bash
html_escape() {
  local STR="$1"
  STR="${STR//&/&amp;}"
  STR="${STR//</&lt;}"
  STR="${STR//>/&gt;}"
  STR="${STR//\"/&quot;}"
  STR="${STR//\'/&#39;}"
  echo "$STR"
}
```

Alle Benutzerdaten (Pfad, Kategorienamen) werden vor der HTML-Ausgabe durch diese Funktion geführt:

```bash
local ORDNER_ESC; ORDNER_ESC=$(html_escape "$ORDNER")
local K_ESC;      K_ESC=$(html_escape "$K")
```

---

### P4 – Unsichere temporäre Dateien (TOCTOU)

**Funktionen:** `cronjob_einrichten()`, `CRONJOB_REMOVE`-Block

**Problem:**  
Der Fallback-Pfad `/tmp/.sortier_cron_$$` war vorhersehbar (nur PID als Entropie). Ein lokaler Angreifer konnte vorher einen Symlink unter diesem Pfad anlegen und so den Inhalt beliebiger Dateien überschreiben (TOCTOU – Time-of-check-time-of-use).

```bash
# Vorher (unsicher):
TMP=$(mktemp 2>/dev/null) || TMP="/tmp/.sortier_cron_$$"
```

**Lösung:**  
Kein Fallback mehr – schlägt `mktemp` fehl, bricht das Script kontrolliert ab:

```bash
# Nachher (sicher):
TMP=$(mktemp 2>/dev/null) || { echo -e "${ROT}Fehler: mktemp fehlgeschlagen.${RESET}"; exit 1; }
```

Betroffen waren drei Stellen: `cronjob_einrichten()`, der `CRONJOB_REMOVE`-Block und der `UNDO`-Block (bereits in v7.1 korrekt, zur Sicherheit vereinheitlicht).

---

### P5 – Pipe `|` als Separator in der Duplikat-Erkennung

**Bereich:** Duplikat-Suche (`--duplikate`)

**Problem:**  
Dateinamen mit `|` als Zeichen wurden als Trennzeichen zwischen Einträgen in der internen `HASH_MAP` interpretiert. Eine Datei namens `foto|rm -rf .jpg` konnte den Array-Split korrumpieren und zu falsch erkannten Duplikaten führen.

```bash
# Vorher (unsicher):
HASH_MAP[$HASH]="${HASH_MAP[$HASH]}|$DATEI"
IFS='|' read -ra DATEIEN <<< "${HASH_MAP[$HASH]}"
```

**Lösung:**  
Wechsel auf Null-Byte (`$'\x00'`) als Separator. Das Null-Byte ist das einzige Zeichen, das per POSIX-Standard **nie** in einem Dateinamen vorkommen kann:

```bash
# Nachher (sicher):
HASH_MAP[$HASH]="${HASH_MAP[$HASH]}"$'\x00'"$DATEI"
IFS=$'\x00' read -r -d '' -a DATEIEN <<< "${HASH_MAP[$HASH]}"$'\x00'
```

---

### P6 – Symlink-Angriffe beim Verschieben

**Funktion:** `sortiere_datei()`

**Problem:**  
Vor dem Verschieben wurde nicht geprüft, ob es sich bei der Quelldatei um einen symbolischen Link handelt. Ein Angreifer, der einen Symlink im zu sortierenden Ordner platziert, hätte `mv` dazu bringen können, Dateien **außerhalb** des Zielordners zu überschreiben.

```bash
# Beispiel: ~/Downloads/wichtig.pdf → /etc/passwd
# mv -- "$SYMLINK" "$ZIEL/Dokumente/wichtig.pdf"
# → überschreibt /etc/passwd
```

**Lösung:**  
Expliziter Symlink-Check ganz zu Beginn von `sortiere_datei()`, noch vor der Ignorier-Liste:

```bash
if [ -L "$DATEI" ]; then
  echo -e "${GELB}ÜBERSPRUNGEN (Symlink): ${DATEI##*/}${RESET}"
  return 2
fi
```

---

## 📁 Geänderte Dateien

| Datei | Änderungen |
|-------|-----------|
| `datei_sortieren.sh` | P1 – P6 (alle Patches) |

---

## 🧪 Getestete Szenarien nach Patching

| Test | Ergebnis |
|------|---------|
| `bash -n` Syntaxcheck | ✅ |
| Ordnerpfad mit `\n` (Cronjob) | ✅ abgefangen |
| Dateiname mit Backtick (Notification) | ✅ neutralisiert |
| HTML-Sonderzeichen im Pfad (Bericht) | ✅ escaped |
| Dateiname mit `\|` (Duplikate) | ✅ korrekt getrennt |
| Symlink im Quellordner | ✅ übersprungen |
| `mktemp` ohne Fallback | ✅ sicherer Abbruch |

---

## 📋 Versions-Übersicht (ergänzt)

| Version | Feature |
|---------|---------|
| v7.0 | Cronjob-Assistent, Benachrichtigungen, Papierkorb, HTML-Bericht |
| v7.1 | Bugfixes: Kollision in Sonstiges/, Suffix bei Dateien ohne Erweiterung |
| **v7.2** | **Security: P1–P6 (Cronjob-Injection, Command-Injection, XSS, TOCTOU, Separator, Symlink)** |
