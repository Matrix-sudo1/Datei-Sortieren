#!/usr/bin/env python3
# ============================================
#  Datei-Sortierer GUI v2.0
#  - Stabilitätsverbesserungen
#  - Kein Absturz bei Mehrfachklick
#  - Windows Git Bash Erkennung
#  - Sichere Thread-Kommunikation
#  - Prozess abbrechen möglich
# ============================================

import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import threading
import os
import sys
import shutil
from pathlib import Path

# ============================================
#  FARBEN & DESIGN
# ============================================
FARBEN = {
    "bg":        "#0f1117",
    "bg_card":   "#1a1d27",
    "bg_hover":  "#22263a",
    "akzent":    "#4f8ef7",
    "akzent2":   "#7c3aed",
    "gruen":     "#22c55e",
    "gelb":      "#f59e0b",
    "rot":       "#ef4444",
    "magenta":   "#ec4899",
    "text":      "#e2e8f0",
    "text_dim":  "#64748b",
    "border":    "#2d3248",
    "log_bg":    "#080a10",
    "deaktiv":   "#3a3f55",
}

SCHRIFT_GROSS  = ("Courier New", 20, "bold")
SCHRIFT_KLEIN  = ("Courier New", 11)
SCHRIFT_LOG    = ("Courier New", 10)


# ============================================
#  HAUPT-APP
# ============================================
class DateiSortiererApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Datei-Sortierer")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        self.root.configure(bg=FARBEN["bg"])

        # Zustandsvariablen
        self.ordner_pfad  = tk.StringVar(value=str(Path.home()))
        self.dryrun_var   = tk.BooleanVar(value=False)
        self.laeuft       = False        # True wenn ein Prozess läuft
        self.aktiver_proc = None         # Aktueller Subprocess
        self._zerstoert   = False        # True wenn Fenster geschlossen

        # Script & Bash finden
        self.script_pfad = self._finde_script()
        self.bash_pfad   = self._finde_bash()

        # UI aufbauen
        self.aktions_buttons = []        # Liste aller Aktions-Buttons
        self._baue_ui()

        # Sicheres Schließen
        self.root.protocol("WM_DELETE_WINDOW", self._beenden)

        # Startup-Info
        self._zeige_startinfo()

    # ------------------------------------------
    #  SYSTEM-ERKENNUNG
    # ------------------------------------------
    def _finde_script(self):
        """Sucht das Shell-Script."""
        basis = Path(__file__).parent
        kandidaten = [
            basis / "datei_sortieren.sh",
            Path.home() / "Datei-Sortieren" / "datei_sortieren.sh",
            Path.home() / "Downloads" / "datei_sortieren.sh",
        ]
        for p in kandidaten:
            if p.exists():
                return str(p)
        return str(basis / "datei_sortieren.sh")

    def _finde_bash(self):
        """Sucht bash auf dem System (wichtig für Windows)."""
        # 1. Systemweites bash (Linux/macOS)
        bash = shutil.which("bash")
        if bash:
            return bash

        # 2. Git Bash auf Windows (häufige Installationspfade)
        windows_pfade = [
            r"C:\Program Files\Git\bin\bash.exe",
            r"C:\Program Files (x86)\Git\bin\bash.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Git\bin\bash.exe"),
        ]
        for pfad in windows_pfade:
            if os.path.exists(pfad):
                return pfad

        return None  # Bash nicht gefunden

    # ------------------------------------------
    #  UI AUFBAUEN
    # ------------------------------------------
    def _baue_ui(self):
        # Header
        header = tk.Frame(self.root, bg=FARBEN["bg"], pady=20)
        header.pack(fill="x", padx=30)

        tk.Label(header, text="⬡", font=("Courier New", 28, "bold"),
                 bg=FARBEN["bg"], fg=FARBEN["akzent"]).pack(side="left")
        tk.Label(header, text=" DATEI-SORTIERER",
                 font=SCHRIFT_GROSS, bg=FARBEN["bg"],
                 fg=FARBEN["text"]).pack(side="left", padx=8)
        tk.Label(header, text="v5.0  |  GUI v2.0", font=SCHRIFT_KLEIN,
                 bg=FARBEN["bg"], fg=FARBEN["text_dim"]).pack(side="left", pady=6)

        # Trennlinie
        tk.Frame(self.root, bg=FARBEN["border"], height=1).pack(fill="x", padx=30)

        # Hauptbereich
        haupt = tk.Frame(self.root, bg=FARBEN["bg"])
        haupt.pack(fill="both", expand=True, padx=30, pady=20)

        links = tk.Frame(haupt, bg=FARBEN["bg"], width=340)
        links.pack(side="left", fill="both", expand=False, padx=(0, 15))
        links.pack_propagate(False)

        self._baue_ordner_auswahl(links)
        self._baue_optionen(links)
        self._baue_buttons(links)

        rechts = tk.Frame(haupt, bg=FARBEN["bg"])
        rechts.pack(side="left", fill="both", expand=True)
        self._baue_log(rechts)

        self._baue_statusbar()

    def _karte(self, parent, titel=None):
        rahmen = tk.Frame(parent, bg=FARBEN["bg_card"],
                          highlightbackground=FARBEN["border"],
                          highlightthickness=1)
        rahmen.pack(fill="x", pady=(0, 12))
        if titel:
            tk.Label(rahmen, text=titel, font=("Courier New", 9, "bold"),
                     bg=FARBEN["bg_card"], fg=FARBEN["text_dim"],
                     padx=16, pady=8).pack(anchor="w")
            tk.Frame(rahmen, bg=FARBEN["border"], height=1).pack(fill="x")
        return rahmen

    def _baue_ordner_auswahl(self, parent):
        karte = self._karte(parent, "ZIELORDNER")
        inner = tk.Frame(karte, bg=FARBEN["bg_card"], padx=16, pady=12)
        inner.pack(fill="x")

        eingabe_rahmen = tk.Frame(inner, bg=FARBEN["border"], padx=1, pady=1)
        eingabe_rahmen.pack(fill="x", pady=(0, 10))
        eingabe_bg = tk.Frame(eingabe_rahmen, bg=FARBEN["log_bg"])
        eingabe_bg.pack(fill="x")

        self.ordner_eingabe = tk.Entry(
            eingabe_bg, textvariable=self.ordner_pfad,
            font=SCHRIFT_LOG, bg=FARBEN["log_bg"],
            fg=FARBEN["text"], insertbackground=FARBEN["akzent"],
            relief="flat", bd=8
        )
        self.ordner_eingabe.pack(fill="x")

        btn = tk.Button(inner, text="  📁  ORDNER WÄHLEN  ",
                        font=("Courier New", 10, "bold"),
                        bg=FARBEN["bg_hover"], fg=FARBEN["akzent"],
                        activebackground=FARBEN["akzent"],
                        activeforeground=FARBEN["bg"],
                        relief="flat", cursor="hand2",
                        command=self._ordner_waehlen, pady=8)
        btn.pack(fill="x")
        self._hover(btn, FARBEN["bg_hover"], FARBEN["akzent"])

    def _baue_optionen(self, parent):
        karte = self._karte(parent, "OPTIONEN")
        inner = tk.Frame(karte, bg=FARBEN["bg_card"], padx=16, pady=12)
        inner.pack(fill="x")

        dry_rahmen = tk.Frame(inner, bg=FARBEN["bg_hover"],
                              highlightbackground=FARBEN["border"],
                              highlightthickness=1, pady=10, padx=12)
        dry_rahmen.pack(fill="x")

        tk.Checkbutton(
            dry_rahmen,
            text=" 👁  VORSCHAU-MODUS  (nichts wird verschoben)",
            variable=self.dryrun_var,
            font=("Courier New", 9),
            bg=FARBEN["bg_hover"], fg=FARBEN["text"],
            selectcolor=FARBEN["bg_card"],
            activebackground=FARBEN["bg_hover"],
            activeforeground=FARBEN["akzent"],
            cursor="hand2", relief="flat"
        ).pack(anchor="w")

    def _btn_erstellen(self, parent, text, farbe, command, symbol=""):
        rahmen = tk.Frame(parent, bg=farbe, padx=1, pady=1)
        rahmen.pack(fill="x", pady=(0, 8))
        btn = tk.Button(
            rahmen, text=f"  {symbol}  {text}  ",
            font=("Courier New", 11, "bold"),
            bg=FARBEN["bg_card"], fg=farbe,
            activebackground=farbe, activeforeground=FARBEN["bg"],
            relief="flat", cursor="hand2",
            command=command, pady=10
        )
        btn.pack(fill="x")
        self._hover(btn, FARBEN["bg_card"], farbe, farbe, FARBEN["bg"])
        self.aktions_buttons.append((btn, rahmen, farbe))
        return btn

    def _baue_buttons(self, parent):
        karte = self._karte(parent, "AKTIONEN")
        inner = tk.Frame(karte, bg=FARBEN["bg_card"], padx=16, pady=12)
        inner.pack(fill="x")

        self._btn_erstellen(inner, "NACH DATEITYP SORTIEREN",
                            FARBEN["akzent"], self._sortiere_typ, "⬡")
        self._btn_erstellen(inner, "NACH DATUM SORTIEREN",
                            FARBEN["akzent2"], self._sortiere_datum, "◷")
        self._btn_erstellen(inner, "DUPLIKATE SUCHEN",
                            FARBEN["magenta"], self._duplikate, "⬡")

        tk.Frame(inner, bg=FARBEN["border"], height=1).pack(fill="x", pady=8)

        zeile = tk.Frame(inner, bg=FARBEN["bg_card"])
        zeile.pack(fill="x")

        self.undo_btn = tk.Button(zeile, text="↩ UNDO",
                                   font=("Courier New", 10, "bold"),
                                   bg=FARBEN["bg_hover"], fg=FARBEN["gelb"],
                                   activebackground=FARBEN["gelb"],
                                   activeforeground=FARBEN["bg"],
                                   relief="flat", cursor="hand2",
                                   command=self._undo, pady=8)
        self.undo_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._hover(self.undo_btn, FARBEN["bg_hover"], FARBEN["gelb"])

        self.log_btn = tk.Button(zeile, text="📋 LOG",
                                  font=("Courier New", 10, "bold"),
                                  bg=FARBEN["bg_hover"], fg=FARBEN["gruen"],
                                  activebackground=FARBEN["gruen"],
                                  activeforeground=FARBEN["bg"],
                                  relief="flat", cursor="hand2",
                                  command=self._zeige_log, pady=8)
        self.log_btn.pack(side="left", fill="x", expand=True)
        self._hover(self.log_btn, FARBEN["bg_hover"], FARBEN["gruen"])

        # Abbrechen-Button (anfangs versteckt)
        self.abbruch_btn = tk.Button(inner, text="⬛ ABBRECHEN",
                                      font=("Courier New", 10, "bold"),
                                      bg=FARBEN["rot"], fg="white",
                                      activebackground="#c0392b",
                                      activeforeground="white",
                                      relief="flat", cursor="hand2",
                                      command=self._abbrechen, pady=8)

    def _baue_log(self, parent):
        header = tk.Frame(parent, bg=FARBEN["bg_card"],
                          highlightbackground=FARBEN["border"],
                          highlightthickness=1)
        header.pack(fill="x")

        tk.Label(header, text="AUSGABE", font=("Courier New", 9, "bold"),
                 bg=FARBEN["bg_card"], fg=FARBEN["text_dim"],
                 padx=16, pady=8).pack(side="left")

        tk.Button(header, text="✕ LEEREN",
                  font=("Courier New", 8),
                  bg=FARBEN["bg_card"], fg=FARBEN["text_dim"],
                  activebackground=FARBEN["rot"],
                  activeforeground="white",
                  relief="flat", cursor="hand2",
                  command=self._log_leeren,
                  padx=10).pack(side="right", pady=4, padx=8)

        tk.Frame(parent, bg=FARBEN["border"], height=1).pack(fill="x")

        log_rahmen = tk.Frame(parent, bg=FARBEN["log_bg"],
                              highlightbackground=FARBEN["border"],
                              highlightthickness=1)
        log_rahmen.pack(fill="both", expand=True)

        self.log_text = tk.Text(
            log_rahmen, font=SCHRIFT_LOG,
            bg=FARBEN["log_bg"], fg=FARBEN["text"],
            insertbackground=FARBEN["akzent"],
            relief="flat", bd=12,
            state="disabled", wrap="word",
            cursor="arrow"
        )
        scrollbar = tk.Scrollbar(log_rahmen, command=self.log_text.yview,
                                  bg=FARBEN["bg_card"],
                                  troughcolor=FARBEN["log_bg"],
                                  activebackground=FARBEN["akzent"])
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)

        # Farb-Tags
        self.log_text.tag_config("gruen",   foreground=FARBEN["gruen"])
        self.log_text.tag_config("rot",     foreground=FARBEN["rot"])
        self.log_text.tag_config("gelb",    foreground=FARBEN["gelb"])
        self.log_text.tag_config("blau",    foreground=FARBEN["akzent"])
        self.log_text.tag_config("magenta", foreground=FARBEN["magenta"])
        self.log_text.tag_config("dim",     foreground=FARBEN["text_dim"])
        self.log_text.tag_config("header",  foreground=FARBEN["akzent"],
                                 font=("Courier New", 11, "bold"))

    def _baue_statusbar(self):
        bar = tk.Frame(self.root, bg=FARBEN["bg_card"],
                       highlightbackground=FARBEN["border"],
                       highlightthickness=1, pady=6)
        bar.pack(fill="x", side="bottom")

        self.status_label = tk.Label(
            bar, text="● BEREIT",
            font=("Courier New", 9, "bold"),
            bg=FARBEN["bg_card"], fg=FARBEN["gruen"], padx=16
        )
        self.status_label.pack(side="left")

        self.bash_label = tk.Label(
            bar, text="",
            font=("Courier New", 8),
            bg=FARBEN["bg_card"], fg=FARBEN["text_dim"], padx=16
        )
        self.bash_label.pack(side="right")

        tk.Label(bar, text="GUI v2.0",
                 font=("Courier New", 8),
                 bg=FARBEN["bg_card"], fg=FARBEN["text_dim"],
                 padx=16).pack(side="right")

    # ------------------------------------------
    #  STARTUP INFO
    # ------------------------------------------
    def _zeige_startinfo(self):
        self._log_schreiben("⬡ DATEI-SORTIERER  v5.0  |  GUI v2.0\n", "header")
        self._log_schreiben("─" * 40 + "\n", "dim")

        # Bash Status
        if self.bash_pfad:
            self._log_schreiben(f"✅ Bash gefunden: {self.bash_pfad}\n", "gruen")
            self.bash_label.configure(text=f"bash: {Path(self.bash_pfad).name}",
                                       fg=FARBEN["gruen"])
        else:
            self._log_schreiben("❌ Bash nicht gefunden!\n", "rot")
            self._log_schreiben("   Bitte Git Bash installieren:\n", "rot")
            self._log_schreiben("   https://git-scm.com/download/win\n\n", "gelb")
            self.bash_label.configure(text="bash: NICHT GEFUNDEN", fg=FARBEN["rot"])

        # Script Status
        if os.path.exists(self.script_pfad):
            self._log_schreiben(f"✅ Script gefunden: {self.script_pfad}\n", "gruen")
        else:
            self._log_schreiben(f"❌ Script nicht gefunden: {self.script_pfad}\n", "rot")
            self._log_schreiben("   Lege datei_sortieren.sh in denselben Ordner.\n\n", "gelb")

        self._log_schreiben("\n  Wähle einen Ordner und starte eine Aktion.\n\n", "dim")

    # ------------------------------------------
    #  HILFSFUNKTIONEN
    # ------------------------------------------
    def _hover(self, widget, bg_normal, fg_normal, bg_hover=None, fg_hover=None):
        if bg_hover is None: bg_hover = fg_normal
        if fg_hover is None: fg_hover = FARBEN["bg"]
        widget.bind("<Enter>", lambda e: widget.configure(bg=bg_hover, fg=fg_hover)
                    if not self.laeuft or widget not in [b for b, _, _ in self.aktions_buttons] else None)
        widget.bind("<Leave>", lambda e: widget.configure(bg=bg_normal, fg=fg_normal)
                    if not self.laeuft or widget not in [b for b, _, _ in self.aktions_buttons] else None)

    def _sicher_ausfuehren(self, fn, *args):
        """Führt UI-Update nur aus wenn Fenster noch offen ist."""
        if not self._zerstoert:
            try:
                fn(*args)
            except tk.TclError:
                pass

    def _buttons_sperren(self, sperren: bool):
        """Deaktiviert/Aktiviert alle Aktions-Buttons während Prozess läuft."""
        zustand = "disabled" if sperren else "normal"
        cursor  = "watch"    if sperren else "hand2"

        for btn, rahmen, farbe in self.aktions_buttons:
            farbe_jetzt = FARBEN["deaktiv"] if sperren else farbe
            btn.configure(state=zustand, cursor=cursor,
                          fg=farbe_jetzt, bg=FARBEN["bg_card"])
            rahmen.configure(bg=farbe_jetzt)

        self.undo_btn.configure(state=zustand, cursor=cursor)
        self.log_btn.configure(state=zustand, cursor=cursor)
        self.ordner_eingabe.configure(state="disabled" if sperren else "normal")

        # Abbrechen-Button ein/ausblenden
        if sperren:
            self.abbruch_btn.pack(fill="x", pady=(8, 0))
        else:
            self.abbruch_btn.pack_forget()

    def _ordner_waehlen(self):
        pfad = filedialog.askdirectory(
            title="Ordner wählen",
            initialdir=self.ordner_pfad.get()
        )
        if pfad:
            self.ordner_pfad.set(pfad)
            self._log_schreiben(f"📁 Ordner: {pfad}\n", "blau")

    def _log_schreiben(self, text, tag=None):
        try:
            self.log_text.configure(state="normal")
            if tag:
                self.log_text.insert("end", text, tag)
            else:
                self.log_text.insert("end", text)
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        except tk.TclError:
            pass

    def _log_leeren(self):
        try:
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", "end")
            self.log_text.configure(state="disabled")
            self._log_schreiben("⬡ Log geleert.\n\n", "dim")
        except tk.TclError:
            pass

    def _status(self, text, farbe="gruen"):
        try:
            symbole  = {"gruen": "●", "gelb": "◐", "rot": "○", "blau": "◆"}
            farb_map = {"gruen": FARBEN["gruen"], "gelb": FARBEN["gelb"],
                        "rot":   FARBEN["rot"],   "blau": FARBEN["akzent"]}
            self.status_label.configure(
                text=f"{symbole.get(farbe,'●')} {text}",
                fg=farb_map.get(farbe, FARBEN["gruen"])
            )
        except tk.TclError:
            pass

    # ------------------------------------------
    #  SCRIPT AUSFÜHREN
    # ------------------------------------------
    def _vorbedingungen_pruefen(self):
        """Prüft ob alles vorhanden ist. Gibt True zurück wenn OK."""
        if not self.bash_pfad:
            messagebox.showerror(
                "Bash nicht gefunden",
                "Git Bash wurde nicht gefunden!\n\n"
                "Bitte installiere Git Bash:\n"
                "https://git-scm.com/download/win\n\n"
                "Nach der Installation bitte das Programm neu starten."
            )
            return False

        if not os.path.exists(self.script_pfad):
            messagebox.showerror(
                "Script nicht gefunden",
                f"datei_sortieren.sh wurde nicht gefunden!\n\n"
                f"Gesuchter Pfad:\n{self.script_pfad}\n\n"
                f"Lege datei_sortieren.sh in denselben Ordner wie gui.py."
            )
            return False

        ordner = self.ordner_pfad.get().strip()
        if not ordner or not os.path.isdir(ordner):
            messagebox.showerror(
                "Ordner nicht gefunden",
                f"Der gewählte Ordner existiert nicht:\n{ordner}\n\n"
                "Bitte wähle einen gültigen Ordner."
            )
            return False

        return True

    def _script_ausfuehren(self, args, titel):
        """Führt das Shell-Script sicher in einem Thread aus."""
        if self.laeuft:
            return  # Verhindert Mehrfach-Ausführung

        if not self._vorbedingungen_pruefen():
            return

        self.laeuft = True
        self._buttons_sperren(True)
        self._log_schreiben(f"\n{'─'*40}\n", "dim")
        self._log_schreiben(f"▶ {titel}\n", "header")
        self._log_schreiben(f"  Ordner: {self.ordner_pfad.get()}\n", "dim")
        self._status("LÄUFT...", "gelb")

        def _thread():
            try:
                cmd = [self.bash_pfad, self.script_pfad] + args
                self.aktiver_proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace"     # Verhindert Encoding-Absturz
                )

                for zeile in self.aktiver_proc.stdout:
                    if self._zerstoert:
                        break
                    zeile_clean = zeile.strip()
                    if not zeile_clean:
                        continue

                    # Farbe nach Inhalt
                    if any(w in zeile_clean for w in ["OK:", "Fertig", "Wiederhergestellt"]):
                        tag = "gruen"
                    elif "VORSCHAU" in zeile_clean:
                        tag = "blau"
                    elif any(w in zeile_clean for w in ["Sonstiges", "Tipp"]):
                        tag = "gelb"
                    elif any(w in zeile_clean for w in ["Fehler", "nicht gefunden", "ERROR"]):
                        tag = "rot"
                    elif "Duplikat" in zeile_clean:
                        tag = "magenta"
                    else:
                        tag = None

                    self.root.after(0, self._sicher_ausfuehren,
                                    self._log_schreiben, f"  {zeile_clean}\n", tag)

                self.aktiver_proc.wait()
                returncode = self.aktiver_proc.returncode

            except FileNotFoundError:
                returncode = -1
                self.root.after(0, self._sicher_ausfuehren,
                                self._log_schreiben,
                                "❌ Bash konnte nicht gestartet werden.\n", "rot")
            except Exception as e:
                returncode = -1
                self.root.after(0, self._sicher_ausfuehren,
                                self._log_schreiben, f"❌ Fehler: {e}\n", "rot")
            finally:
                self.aktiver_proc = None
                self.laeuft = False
                if not self._zerstoert:
                    if returncode == 0:
                        self.root.after(0, self._sicher_ausfuehren,
                                        self._status, "FERTIG", "gruen")
                    elif returncode == -2:  # Abgebrochen
                        self.root.after(0, self._sicher_ausfuehren,
                                        self._status, "ABGEBROCHEN", "gelb")
                    else:
                        self.root.after(0, self._sicher_ausfuehren,
                                        self._status, "FEHLER", "rot")
                    self.root.after(0, self._sicher_ausfuehren,
                                    self._buttons_sperren, False)

        threading.Thread(target=_thread, daemon=True).start()

    def _abbrechen(self):
        """Bricht den laufenden Prozess ab."""
        if self.aktiver_proc and self.laeuft:
            try:
                self.aktiver_proc.terminate()
                self._log_schreiben("\n⬛ Abgebrochen!\n", "gelb")
            except Exception:
                pass

    # ------------------------------------------
    #  AKTIONEN
    # ------------------------------------------
    def _sortiere_typ(self):
        args = [self.ordner_pfad.get()]
        if self.dryrun_var.get():
            args.append("--dry-run")
        self._script_ausfuehren(args, "SORTIERE NACH DATEITYP")

    def _sortiere_datum(self):
        args = [self.ordner_pfad.get(), "--nach-datum"]
        if self.dryrun_var.get():
            args.append("--dry-run")
        self._script_ausfuehren(args, "SORTIERE NACH DATUM")

    def _duplikate(self):
        if not self._vorbedingungen_pruefen():
            return
        self._script_ausfuehren([self.ordner_pfad.get(), "--duplikate"], "DUPLIKATE SUCHEN")

    def _undo(self):
        if not self._vorbedingungen_pruefen():
            return
        if messagebox.askyesno("Rückgängig", "Letzte Sortierung wirklich rückgängig machen?"):
            self._script_ausfuehren([self.ordner_pfad.get(), "--undo"], "UNDO")

    def _zeige_log(self):
        if not self._vorbedingungen_pruefen():
            return
        self._script_ausfuehren([self.ordner_pfad.get(), "--log"], "LOG ANZEIGEN")

    # ------------------------------------------
    #  SICHERES BEENDEN
    # ------------------------------------------
    def _beenden(self):
        """Sicheres Beenden – wartet auf laufende Prozesse."""
        if self.laeuft:
            if not messagebox.askyesno(
                "Beenden",
                "Ein Prozess läuft noch.\nTrotzdem beenden?"
            ):
                return
            self._abbrechen()

        self._zerstoert = True
        self.root.destroy()


# ============================================
#  START
# ============================================
if __name__ == "__main__":
    root = tk.Tk()
    root.resizable(True, True)

    try:
        root.iconbitmap("icon.ico")
    except Exception:
        pass

    app = DateiSortiererApp(root)
    root.mainloop()
