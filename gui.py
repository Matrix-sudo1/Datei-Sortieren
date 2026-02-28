#!/usr/bin/env python3
# ============================================
#  Datei-Sortierer GUI v1.0
#  Moderne Desktop-App fuer den Datei-Sortierer
# ============================================

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import os
import sys
from pathlib import Path

# ============================================
#  FARBEN & DESIGN
# ============================================
FARBEN = {
    "bg":           "#0f1117",
    "bg_card":      "#1a1d27",
    "bg_hover":     "#22263a",
    "akzent":       "#4f8ef7",
    "akzent2":      "#7c3aed",
    "gruen":        "#22c55e",
    "gelb":         "#f59e0b",
    "rot":          "#ef4444",
    "magenta":      "#ec4899",
    "text":         "#e2e8f0",
    "text_dim":     "#64748b",
    "border":       "#2d3248",
    "log_bg":       "#080a10",
}

SCHRIFT_GROSS  = ("Courier New", 20, "bold")
SCHRIFT_MITTEL = ("Courier New", 13, "bold")
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

        self.ordner_pfad = tk.StringVar(value=str(Path.home()))
        self.dryrun_var  = tk.BooleanVar(value=False)
        self.script_pfad = self._finde_script()

        self._baue_ui()

    def _finde_script(self):
        """Sucht das Shell-Script im selben Ordner wie diese Python-Datei."""
        basis = Path(__file__).parent
        kandidaten = [
            basis / "datei_sortieren.sh",
            Path.home() / "Datei-Sortieren" / "datei_sortieren.sh",
        ]
        for p in kandidaten:
            if p.exists():
                return str(p)
        return str(basis / "datei_sortieren.sh")

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
                 font=SCHRIFT_GROSS, bg=FARBEN["bg"], fg=FARBEN["text"]).pack(side="left", padx=8)
        tk.Label(header, text="v5.0", font=SCHRIFT_KLEIN,
                 bg=FARBEN["bg"], fg=FARBEN["text_dim"]).pack(side="left", pady=6)

        # Trennlinie
        tk.Frame(self.root, bg=FARBEN["border"], height=1).pack(fill="x", padx=30)

        # Hauptbereich (links + rechts)
        haupt = tk.Frame(self.root, bg=FARBEN["bg"])
        haupt.pack(fill="both", expand=True, padx=30, pady=20)

        # Linke Spalte
        links = tk.Frame(haupt, bg=FARBEN["bg"])
        links.pack(side="left", fill="both", expand=False, padx=(0, 15))
        links.configure(width=340)
        links.pack_propagate(False)

        self._baue_ordner_auswahl(links)
        self._baue_optionen(links)
        self._baue_buttons(links)

        # Rechte Spalte - Log
        rechts = tk.Frame(haupt, bg=FARBEN["bg"])
        rechts.pack(side="left", fill="both", expand=True)
        self._baue_log(rechts)

        # Statusbar
        self._baue_statusbar()

    def _karte(self, parent, titel=None):
        """Erstellt eine stilvolle Karte."""
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

        cb = tk.Checkbutton(
            dry_rahmen,
            text=" 👁  VORSCHAU-MODUS  (nichts wird verschoben)",
            variable=self.dryrun_var,
            font=("Courier New", 9),
            bg=FARBEN["bg_hover"], fg=FARBEN["text"],
            selectcolor=FARBEN["bg_card"],
            activebackground=FARBEN["bg_hover"],
            activeforeground=FARBEN["akzent"],
            cursor="hand2", relief="flat"
        )
        cb.pack(anchor="w")

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

        undo_btn = tk.Button(zeile, text="↩ UNDO",
                             font=("Courier New", 10, "bold"),
                             bg=FARBEN["bg_hover"], fg=FARBEN["gelb"],
                             activebackground=FARBEN["gelb"],
                             activeforeground=FARBEN["bg"],
                             relief="flat", cursor="hand2",
                             command=self._undo, pady=8)
        undo_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._hover(undo_btn, FARBEN["bg_hover"], FARBEN["gelb"])

        log_btn = tk.Button(zeile, text="📋 LOG",
                            font=("Courier New", 10, "bold"),
                            bg=FARBEN["bg_hover"], fg=FARBEN["gruen"],
                            activebackground=FARBEN["gruen"],
                            activeforeground=FARBEN["bg"],
                            relief="flat", cursor="hand2",
                            command=self._zeige_log, pady=8)
        log_btn.pack(side="left", fill="x", expand=True)
        self._hover(log_btn, FARBEN["bg_hover"], FARBEN["gruen"])

    def _baue_log(self, parent):
        header = tk.Frame(parent, bg=FARBEN["bg_card"],
                          highlightbackground=FARBEN["border"],
                          highlightthickness=1)
        header.pack(fill="x")

        tk.Label(header, text="AUSGABE", font=("Courier New", 9, "bold"),
                 bg=FARBEN["bg_card"], fg=FARBEN["text_dim"],
                 padx=16, pady=8).pack(side="left")

        clear_btn = tk.Button(header, text="✕ LEEREN",
                              font=("Courier New", 8),
                              bg=FARBEN["bg_card"], fg=FARBEN["text_dim"],
                              activebackground=FARBEN["rot"],
                              activeforeground="white",
                              relief="flat", cursor="hand2",
                              command=self._log_leeren, padx=10)
        clear_btn.pack(side="right", pady=4, padx=8)

        tk.Frame(parent, bg=FARBEN["border"], height=1).pack(fill="x")

        log_rahmen = tk.Frame(parent, bg=FARBEN["log_bg"],
                              highlightbackground=FARBEN["border"],
                              highlightthickness=1)
        log_rahmen.pack(fill="both", expand=True, pady=(0, 0))

        self.log_text = tk.Text(
            log_rahmen, font=SCHRIFT_LOG,
            bg=FARBEN["log_bg"], fg=FARBEN["text"],
            insertbackground=FARBEN["akzent"],
            relief="flat", bd=12,
            state="disabled", wrap="word",
            cursor="arrow"
        )

        scrollbar = tk.Scrollbar(log_rahmen, command=self.log_text.yview,
                                  bg=FARBEN["bg_card"], troughcolor=FARBEN["log_bg"],
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

        self._log_schreiben("⬡ Datei-Sortierer bereit.\n", "header")
        self._log_schreiben("  Wähle einen Ordner und starte eine Aktion.\n\n", "dim")

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

        tk.Label(bar, text="Datei-Sortierer v5.0  |  GUI v1.0",
                 font=("Courier New", 8),
                 bg=FARBEN["bg_card"], fg=FARBEN["text_dim"],
                 padx=16).pack(side="right")

    # ------------------------------------------
    #  HILFSFUNKTIONEN
    # ------------------------------------------
    def _hover(self, widget, bg_normal, fg_normal, bg_hover=None, fg_hover=None):
        if bg_hover is None: bg_hover = fg_normal
        if fg_hover is None: fg_hover = FARBEN["bg"]
        widget.bind("<Enter>", lambda e: widget.configure(bg=bg_hover, fg=fg_hover))
        widget.bind("<Leave>", lambda e: widget.configure(bg=bg_normal, fg=fg_normal))

    def _ordner_waehlen(self):
        pfad = filedialog.askdirectory(title="Ordner wählen",
                                       initialdir=self.ordner_pfad.get())
        if pfad:
            self.ordner_pfad.set(pfad)
            self._log_schreiben(f"📁 Ordner gewählt: {pfad}\n", "blau")

    def _log_schreiben(self, text, tag=None):
        self.log_text.configure(state="normal")
        if tag:
            self.log_text.insert("end", text, tag)
        else:
            self.log_text.insert("end", text)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _log_leeren(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self._log_schreiben("⬡ Log geleert.\n\n", "dim")

    def _status(self, text, farbe="gruen"):
        symbole = {"gruen": "●", "gelb": "◐", "rot": "○", "blau": "◆"}
        symbol = symbole.get(farbe, "●")
        farb_map = {"gruen": FARBEN["gruen"], "gelb": FARBEN["gelb"],
                    "rot": FARBEN["rot"], "blau": FARBEN["akzent"]}
        self.status_label.configure(text=f"{symbol} {text}",
                                     fg=farb_map.get(farbe, FARBEN["gruen"]))

    def _script_ausfuehren(self, args, titel):
        """Fuehrt das Shell-Script in einem Thread aus."""
        if not os.path.exists(self.script_pfad):
            self._log_schreiben(f"❌ Script nicht gefunden: {self.script_pfad}\n", "rot")
            self._log_schreiben("   Lege datei_sortieren.sh in denselben Ordner.\n", "rot")
            return

        self._log_schreiben(f"\n{'─'*40}\n", "dim")
        self._log_schreiben(f"▶ {titel}\n", "header")
        self._log_schreiben(f"  Ordner: {self.ordner_pfad.get()}\n", "dim")
        self._status("LÄUFT...", "gelb")

        def _thread():
            try:
                cmd = ["bash", self.script_pfad] + args
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, text=True
                )
                for zeile in proc.stdout:
                    zeile_clean = zeile.strip()
                    if not zeile_clean:
                        continue
                    # Farbe nach Inhalt bestimmen
                    if "OK:" in zeile_clean or "Fertig" in zeile_clean or "Wiederhergestellt" in zeile_clean:
                        tag = "gruen"
                    elif "VORSCHAU" in zeile_clean:
                        tag = "blau"
                    elif "Sonstiges" in zeile_clean or "Tipp" in zeile_clean:
                        tag = "gelb"
                    elif "Fehler" in zeile_clean or "nicht gefunden" in zeile_clean.lower():
                        tag = "rot"
                    elif "Duplikat" in zeile_clean:
                        tag = "magenta"
                    else:
                        tag = None
                    self.root.after(0, self._log_schreiben, f"  {zeile_clean}\n", tag)

                proc.wait()
                if proc.returncode == 0:
                    self.root.after(0, self._status, "FERTIG", "gruen")
                else:
                    self.root.after(0, self._status, "FEHLER", "rot")

            except Exception as e:
                self.root.after(0, self._log_schreiben, f"❌ Fehler: {e}\n", "rot")
                self.root.after(0, self._status, "FEHLER", "rot")

        threading.Thread(target=_thread, daemon=True).start()

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
        messagebox.showinfo(
            "Duplikate suchen",
            "Die Duplikat-Suche ist interaktiv und läuft im Terminal.\n\n"
            "Öffne Git Bash und tippe:\n"
            f"bash \"{self.script_pfad}\" \"{self.ordner_pfad.get()}\" --duplikate"
        )

    def _undo(self):
        if messagebox.askyesno("Rückgängig", "Letzte Sortierung rückgängig machen?"):
            self._script_ausfuehren([self.ordner_pfad.get(), "--undo"], "UNDO")

    def _zeige_log(self):
        self._script_ausfuehren([self.ordner_pfad.get(), "--log"], "LOG ANZEIGEN")


# ============================================
#  START
# ============================================
if __name__ == "__main__":
    root = tk.Tk()
    root.resizable(True, True)

    # Icon setzen (falls vorhanden)
    try:
        root.iconbitmap("icon.ico")
    except:
        pass

    app = DateiSortiererApp(root)
    root.mainloop()
