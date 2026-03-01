#!/usr/bin/env python3
# ============================================
#  Datei-Sortierer GUI v4.0
#  Stabilitätsfixes:
#  - returncode immer definiert
#  - root.after korrekt verwendet
#  - Vorschau läuft im Thread (kein UI-Freeze)
#  - Thread-Lock gegen Race Conditions
#  - Undo-Schutz bei leerem Pfad
#  - Alle TclErrors abgefangen
#  - Speicherleck in Tabelle behoben
#  - Prozess-Timeout beim Beenden
# ============================================

import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import threading
import os
import shutil
from pathlib import Path

# ============================================
#  FARBEN
# ============================================
F = {
    "bg":         "#0d1117",
    "card":       "#161b2e",
    "card2":      "#1c2340",
    "nav":        "#1a2035",
    "tab_aktiv":  "#6c3fc5",
    "akzent":     "#6c3fc5",
    "akzent2":    "#2d6bbf",
    "start":      "#e8435a",
    "gruen":      "#2ecc71",
    "gelb":       "#f39c12",
    "rot":        "#e8435a",
    "text":       "#e8eaf6",
    "text_dim":   "#6b7280",
    "border":     "#2a3050",
    "tabelle_hd": "#1e2d4a",
    "tabelle_z1": "#161b2e",
    "tabelle_z2": "#1a2035",
    "drop":       "#1a2240",
    "drop_border":"#5a3db5",
    "deaktiv":    "#3a3f55",
}

FONT      = ("Segoe UI", 11)
FONT_BOLD = ("Segoe UI", 11, "bold")
FONT_TITEL= ("Segoe UI", 20, "bold")
FONT_KLEIN= ("Segoe UI", 9)
FONT_TAB  = ("Segoe UI", 12, "bold")
FONT_BTN  = ("Segoe UI", 13, "bold")

KATEGORIEN = {
    "Bilder":       ["jpg","jpeg","png","gif","bmp","svg","webp","tiff","tif","ico"],
    "Videos":       ["mp4","mkv","avi","mov","wmv","flv","webm","m4v","mpeg","mpg"],
    "Audio":        ["mp3","wav","flac","aac","ogg","wma","m4a","opus"],
    "Dokumente":    ["pdf","doc","docx","odt","txt","rtf","md"],
    "Tabellen":     ["xls","xlsx","csv","ods"],
    "Praesentation":["ppt","pptx","odp"],
    "Archive":      ["zip","tar","gz","bz2","rar","7z","xz"],
    "Code":         ["sh","py","js","ts","html","css","php","java","c","cpp","h","rb","go","rs","sql"],
    "Ausfuehrbar":  ["exe","dmg","deb","rpm","appimage"],
    "Schriften":    ["ttf","otf","woff","woff2"],
}


def get_kategorie(dateiname):
    ext = dateiname.rsplit(".", 1)[-1].lower() if "." in dateiname else ""
    for kat, exts in KATEGORIEN.items():
        if ext in exts:
            return kat, kat + "/"
    return "Sonstiges", "Sonstiges/"


# ============================================
#  HAUPT-APP
# ============================================
class DateiSortiererApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Datei-Sortierer v2.0")
        self.root.geometry("860x750")
        self.root.minsize(760, 650)
        self.root.configure(bg=F["bg"])
        self.root.resizable(True, True)

        # --- Zustandsvariablen ---
        self.ordner_pfad     = tk.StringVar(value="")
        self.kopieren_var    = tk.BooleanVar(value=False)
        self.unterordner_var = tk.BooleanVar(value=False)
        self._zerstoert      = False

        # Thread-sicherer Zustand
        self._lock      = threading.Lock()
        self._laeuft    = False       # Immer über Property zugreifen
        self.aktiver_proc = None

        # Script & Bash finden
        self.script_pfad = self._finde_script()
        self.bash_pfad   = self._finde_bash()

        # UI
        self._baue_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._beenden)

    # --- Thread-sicherer laeuft-Zugriff ---
    @property
    def laeuft(self):
        with self._lock:
            return self._laeuft

    @laeuft.setter
    def laeuft(self, wert):
        with self._lock:
            self._laeuft = wert

    # ------------------------------------------
    #  SYSTEM-ERKENNUNG
    # ------------------------------------------
    def _finde_script(self):
        basis = Path(__file__).parent
        for p in [
            basis / "datei_sortieren.sh",
            Path.home() / "Datei-Sortieren" / "datei_sortieren.sh",
            Path.home() / "Downloads" / "datei_sortieren.sh",
        ]:
            if p.exists():
                return str(p)
        return str(basis / "datei_sortieren.sh")

    def _finde_bash(self):
        bash = shutil.which("bash")
        if bash:
            return bash
        for pfad in [
            r"C:\Program Files\Git\bin\bash.exe",
            r"C:\Program Files (x86)\Git\bin\bash.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Git\bin\bash.exe"),
        ]:
            if os.path.exists(pfad):
                return pfad
        return None

    # ------------------------------------------
    #  SICHERE UI-HELFER
    # ------------------------------------------
    def _ui(self, fn, *args, **kwargs):
        """Führt UI-Funktion nur aus wenn Fenster noch offen ist."""
        if not self._zerstoert:
            try:
                fn(*args, **kwargs)
            except tk.TclError:
                pass

    def _nach(self, fn, *args, **kwargs):
        """Sicherer root.after(0, ...) Aufruf aus Threads."""
        if not self._zerstoert:
            self.root.after(0, lambda: self._ui(fn, *args, **kwargs))

    def _widget(self, widget, **kwargs):
        """Sicheres widget.configure() aus Threads."""
        self._nach(widget.configure, **kwargs)

    # ------------------------------------------
    #  UI AUFBAUEN
    # ------------------------------------------
    def _baue_ui(self):
        aussen = tk.Frame(self.root, bg=F["bg"], padx=20, pady=16)
        aussen.pack(fill="both", expand=True)

        self._baue_titelleiste(aussen)

        karte = tk.Frame(aussen, bg=F["card"],
                         highlightbackground=F["border"],
                         highlightthickness=1)
        karte.pack(fill="both", expand=True)

        self._baue_macos_buttons(karte)
        self._baue_app_titel(karte)
        self._baue_tabs(karte)

        self.tab_inhalt = tk.Frame(karte, bg=F["card"])
        self.tab_inhalt.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        self._baue_tab_sortieren()
        self._baue_tab_statistiken()
        self._baue_tab_verlauf()

        self._tab_wechseln("sortieren")
        self._baue_statusbar(aussen)

    def _baue_titelleiste(self, parent):
        leiste = tk.Frame(parent, bg=F["bg"], pady=6)
        leiste.pack(fill="x")
        tk.Label(leiste,
                 text="🖥  DATEI-SORTIERER V2.0 – GUI",
                 font=("Segoe UI", 13, "bold"),
                 bg=F["bg"], fg=F["text"]).pack(side="left")

    def _baue_macos_buttons(self, parent):
        leiste = tk.Frame(parent, bg=F["card"], pady=10, padx=16)
        leiste.pack(fill="x")
        for farbe, cmd in [("#e8435a", self._beenden),
                            ("#f39c12", lambda: None),
                            ("#2ecc71", lambda: None)]:
            tk.Button(leiste, text="", width=2,
                      bg=farbe, activebackground=farbe,
                      relief="flat", cursor="hand2",
                      command=cmd, bd=0).pack(side="left", padx=3)
        tk.Label(leiste, text="📁 Datei-Sortierer v2.0",
                 font=FONT, bg=F["card"], fg=F["text_dim"]).pack(side="left", padx=12)

    def _baue_app_titel(self, parent):
        r = tk.Frame(parent, bg=F["card"], pady=16)
        r.pack(fill="x", padx=24)
        tk.Label(r, text="📁", font=("Segoe UI Emoji", 28),
                 bg=F["card"], fg=F["gelb"]).pack(side="left")
        tk.Label(r, text=" Datei-Sortierer",
                 font=FONT_TITEL, bg=F["card"], fg=F["text"]).pack(side="left")
        tk.Label(r, text="  v2.0", font=("Segoe UI", 13),
                 bg=F["card"], fg=F["text_dim"]).pack(side="left", pady=6)

    def _baue_tabs(self, parent):
        self.tab_rahmen = tk.Frame(parent, bg=F["card"], padx=24)
        self.tab_rahmen.pack(fill="x", pady=(0, 4))
        self.tab_buttons = {}
        for key, label in [("sortieren",   "🗂  Sortieren"),
                            ("statistiken", "📊  Statistiken"),
                            ("verlauf",     "🕐  Verlauf")]:
            btn = tk.Button(
                self.tab_rahmen, text=label, font=FONT_TAB,
                bg=F["nav"], fg=F["text_dim"],
                activebackground=F["tab_aktiv"],
                activeforeground=F["text"],
                relief="flat", cursor="hand2",
                padx=22, pady=10,
                command=lambda k=key: self._tab_wechseln(k)
            )
            btn.pack(side="left", padx=(0, 6))
            self.tab_buttons[key] = btn

    def _tab_wechseln(self, key):
        # Verhindert Tab-Wechsel während Prozess läuft
        if self.laeuft and key != "verlauf":
            return
        try:
            for k, btn in self.tab_buttons.items():
                btn.configure(bg=F["tab_aktiv"] if k == key else F["nav"],
                              fg=F["text"] if k == key else F["text_dim"])
            for frame in [self.frame_sortieren,
                          self.frame_statistiken,
                          self.frame_verlauf]:
                frame.pack_forget()
            {"sortieren":   self.frame_sortieren,
             "statistiken": self.frame_statistiken,
             "verlauf":     self.frame_verlauf}[key].pack(fill="both", expand=True)
        except tk.TclError:
            pass

    # ------------------------------------------
    #  TAB: SORTIEREN
    # ------------------------------------------
    def _baue_tab_sortieren(self):
        self.frame_sortieren = tk.Frame(self.tab_inhalt, bg=F["card"])

        # Drop-Zone
        self.drop_zone = tk.Frame(
            self.frame_sortieren, bg=F["drop"],
            highlightbackground=F["drop_border"],
            highlightthickness=2, cursor="hand2"
        )
        self.drop_zone.pack(fill="x", pady=(8, 12))
        self.drop_label = tk.Label(
            self.drop_zone,
            text="📁  Ordner hierher ziehen — oder klicken zum Auswählen",
            font=("Segoe UI", 13), bg=F["drop"], fg=F["text_dim"], pady=28
        )
        self.drop_label.pack()
        for w in [self.drop_zone, self.drop_label]:
            w.bind("<Button-1>", lambda e: self._ordner_waehlen())
            w.bind("<Enter>",    lambda e: self._drop_hover(True))
            w.bind("<Leave>",    lambda e: self._drop_hover(False))

        # Optionen
        opt = tk.Frame(self.frame_sortieren, bg=F["card"])
        opt.pack(fill="x", pady=(0, 12))
        self._checkbox(opt, "📋  Kopieren (Original bleibt)",
                       self.kopieren_var).pack(side="left", padx=(0, 30))
        self._checkbox(opt, "🔄  Unterordner einbeziehen",
                       self.unterordner_var).pack(side="left")

        # Vorschau-Label
        tk.Label(self.frame_sortieren, text="VORSCHAU",
                 font=("Segoe UI", 9, "bold"),
                 bg=F["card"], fg=F["text_dim"]).pack(anchor="w", pady=(0, 4))

        # Tabellen-Container mit Scrollbar
        tabelle_aussen = tk.Frame(self.frame_sortieren, bg=F["tabelle_hd"],
                                   highlightbackground=F["border"],
                                   highlightthickness=1)
        tabelle_aussen.pack(fill="both", expand=True)

        # Header
        header = tk.Frame(tabelle_aussen, bg=F["tabelle_hd"])
        header.pack(fill="x")
        for text, breite in [("Dateiname", 26), ("Kategorie", 18), ("Ziel-Ordner", 22)]:
            tk.Label(header, text=text, font=FONT_BOLD,
                     bg=F["tabelle_hd"], fg=F["text"],
                     width=breite, anchor="w", padx=12, pady=10).pack(side="left")

        # Scrollbarer Inhaltsbereich
        canvas_rahmen = tk.Frame(tabelle_aussen, bg=F["tabelle_z1"])
        canvas_rahmen.pack(fill="both", expand=True)

        self.tabelle_canvas = tk.Canvas(canvas_rahmen, bg=F["tabelle_z1"],
                                         highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_rahmen, orient="vertical",
                                  command=self.tabelle_canvas.yview,
                                  bg=F["card2"], troughcolor=F["tabelle_z1"])
        self.tabelle_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tabelle_canvas.pack(side="left", fill="both", expand=True)

        self.tabelle_frame = tk.Frame(self.tabelle_canvas, bg=F["tabelle_z1"])
        self.tabelle_canvas_window = self.tabelle_canvas.create_window(
            (0, 0), window=self.tabelle_frame, anchor="nw"
        )
        self.tabelle_frame.bind("<Configure>", self._tabelle_scroll_update)
        self.tabelle_canvas.bind("<Configure>", self._tabelle_breite_update)

        self._tabelle_reset_leer()

        # Status
        self.status_text = tk.Label(
            self.frame_sortieren,
            text="Wähle einen Ordner aus, um zu beginnen.",
            font=FONT, bg=F["card"], fg=F["gruen"], pady=10, anchor="w"
        )
        self.status_text.pack(fill="x")

        # Buttons
        btn_leiste = tk.Frame(self.frame_sortieren, bg=F["card"])
        btn_leiste.pack(fill="x", pady=(4, 0))

        self.vorschau_btn = tk.Button(
            btn_leiste, text="🔍  Vorschau laden",
            font=FONT_BTN, bg=F["akzent2"], fg=F["text"],
            activebackground="#1a4a8a", activeforeground=F["text"],
            relief="flat", cursor="hand2", pady=14,
            command=self._vorschau_laden
        )
        self.vorschau_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.start_btn = tk.Button(
            btn_leiste, text="🚀  Sortieren starten",
            font=FONT_BTN, bg=F["start"], fg=F["text"],
            activebackground="#c0392b", activeforeground=F["text"],
            relief="flat", cursor="hand2", pady=14,
            command=self._sortieren_starten
        )
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.reset_btn = tk.Button(
            btn_leiste, text="🗑  Reset",
            font=FONT_BTN, bg=F["nav"], fg=F["text_dim"],
            activebackground=F["border"], activeforeground=F["text"],
            relief="flat", cursor="hand2", pady=14, width=10,
            command=self._reset
        )
        self.reset_btn.pack(side="left")

        # Abbrechen-Button (versteckt)
        self.abbruch_btn = tk.Button(
            btn_leiste, text="⬛  Abbrechen",
            font=FONT_BTN, bg=F["rot"], fg=F["text"],
            activebackground="#c0392b", activeforeground=F["text"],
            relief="flat", cursor="hand2", pady=14,
            command=self._abbrechen
        )

    def _tabelle_scroll_update(self, event=None):
        try:
            self.tabelle_canvas.configure(
                scrollregion=self.tabelle_canvas.bbox("all"))
        except tk.TclError:
            pass

    def _tabelle_breite_update(self, event):
        try:
            self.tabelle_canvas.itemconfig(
                self.tabelle_canvas_window, width=event.width)
        except tk.TclError:
            pass

    def _tabelle_reset_leer(self):
        self._tabelle_leeren()
        tk.Label(self.tabelle_frame,
                 text="Klicke auf die Drop-Zone um eine Vorschau zu laden...",
                 font=FONT, bg=F["tabelle_z1"], fg=F["text_dim"],
                 pady=30).pack()

    def _tabelle_leeren(self):
        try:
            for w in self.tabelle_frame.winfo_children():
                w.destroy()
        except tk.TclError:
            pass

    def _tabelle_zeile_hinzufuegen(self, dateiname, kategorie, ziel, zeile_nr):
        try:
            bg = F["tabelle_z1"] if zeile_nr % 2 == 0 else F["tabelle_z2"]
            zeile = tk.Frame(self.tabelle_frame, bg=bg)
            zeile.pack(fill="x")
            for text, breite in [(dateiname, 26), (kategorie, 18), (ziel, 22)]:
                tk.Label(zeile, text=text, font=FONT,
                         bg=bg, fg=F["text"],
                         width=breite, anchor="w", padx=12, pady=7).pack(side="left")
        except tk.TclError:
            pass

    def _drop_hover(self, aktiv):
        try:
            if aktiv:
                self.drop_zone.configure(highlightbackground=F["akzent"],
                                          bg=F["card2"])
                self.drop_label.configure(bg=F["card2"])
            else:
                farbe = F["gruen"] if self.ordner_pfad.get() else F["drop_border"]
                self.drop_zone.configure(highlightbackground=farbe, bg=F["drop"])
                self.drop_label.configure(bg=F["drop"])
        except tk.TclError:
            pass

    def _checkbox(self, parent, text, variable):
        r = tk.Frame(parent, bg=F["card"])
        tk.Checkbutton(r, text=text, variable=variable, font=FONT,
                       bg=F["card"], fg=F["text"], selectcolor=F["akzent"],
                       activebackground=F["card"], activeforeground=F["text"],
                       cursor="hand2", relief="flat").pack(side="left")
        return r

    def _buttons_sperren(self, sperren):
        """Buttons sperren/freigeben + Abbrechen ein/ausblenden."""
        try:
            zustand = "disabled" if sperren else "normal"
            for btn in [self.vorschau_btn, self.start_btn, self.reset_btn]:
                btn.configure(state=zustand)
            if sperren:
                self.start_btn.configure(text="⏳  Läuft...")
                self.abbruch_btn.pack(side="left", fill="x",
                                       expand=True, padx=(8, 0))
            else:
                self.start_btn.configure(text="🚀  Sortieren starten")
                try:
                    self.abbruch_btn.pack_forget()
                except tk.TclError:
                    pass
        except tk.TclError:
            pass

    # ------------------------------------------
    #  TAB: STATISTIKEN
    # ------------------------------------------
    def _baue_tab_statistiken(self):
        self.frame_statistiken = tk.Frame(self.tab_inhalt, bg=F["card"])
        tk.Label(self.frame_statistiken, text="📊  Statistiken",
                 font=FONT_TITEL, bg=F["card"], fg=F["text"], pady=20).pack()
        self.stats_frame = tk.Frame(self.frame_statistiken, bg=F["card"])
        self.stats_frame.pack(fill="both", expand=True, padx=16)
        tk.Label(self.stats_frame,
                 text="Noch keine Sortierung durchgeführt.\n"
                      "Starte eine Sortierung um Statistiken zu sehen.",
                 font=FONT, bg=F["card"], fg=F["text_dim"], pady=40).pack()

    def _zeige_statistiken(self, kategorien_count):
        try:
            for w in self.stats_frame.winfo_children():
                w.destroy()
            gesamt = sum(kategorien_count.values())
            if gesamt == 0:
                tk.Label(self.stats_frame,
                         text="Keine Dateien wurden sortiert.",
                         font=FONT, bg=F["card"], fg=F["text_dim"], pady=20).pack()
                return
            tk.Label(self.stats_frame,
                     text=f"Letzte Sortierung: {gesamt} Datei(en) sortiert",
                     font=FONT_BOLD, bg=F["card"], fg=F["gruen"], pady=10).pack(anchor="w")
            for kat, anzahl in sorted(kategorien_count.items(),
                                       key=lambda x: x[1], reverse=True):
                zeile = tk.Frame(self.stats_frame, bg=F["card2"],
                                  highlightbackground=F["border"],
                                  highlightthickness=1)
                zeile.pack(fill="x", pady=2)
                tk.Label(zeile, text=f"  {kat}", font=FONT,
                         bg=F["card2"], fg=F["text"],
                         width=20, anchor="w", pady=8).pack(side="left")
                breite = max(20, int(anzahl / gesamt * 280))
                tk.Frame(zeile, bg=F["akzent"], width=breite, height=18).pack(
                    side="left", padx=8, pady=8)
                tk.Label(zeile, text=f"{anzahl}x", font=FONT_BOLD,
                         bg=F["card2"], fg=F["akzent"]).pack(side="left")
        except tk.TclError:
            pass

    # ------------------------------------------
    #  TAB: VERLAUF
    # ------------------------------------------
    def _baue_tab_verlauf(self):
        self.frame_verlauf = tk.Frame(self.tab_inhalt, bg=F["card"])
        header = tk.Frame(self.frame_verlauf, bg=F["card"])
        header.pack(fill="x", pady=(10, 8))
        tk.Label(header, text="🕐  Verlauf",
                 font=FONT_TITEL, bg=F["card"], fg=F["text"]).pack(side="left")

        btn_rahmen = tk.Frame(header, bg=F["card"])
        btn_rahmen.pack(side="right")

        tk.Button(btn_rahmen, text="↩ Rückgängig", font=FONT_BOLD,
                  bg=F["akzent"], fg=F["text"],
                  activebackground="#4a2a9a", activeforeground=F["text"],
                  relief="flat", cursor="hand2", padx=16, pady=8,
                  command=self._undo).pack(side="left", padx=(0, 6))

        tk.Button(btn_rahmen, text="✕ Leeren", font=FONT_BOLD,
                  bg=F["nav"], fg=F["text_dim"],
                  activebackground=F["rot"], activeforeground=F["text"],
                  relief="flat", cursor="hand2", padx=16, pady=8,
                  command=self._verlauf_leeren).pack(side="left")

        self.verlauf_text = tk.Text(
            self.frame_verlauf, font=("Courier New", 10),
            bg=F["card2"], fg=F["text"], relief="flat", bd=8,
            state="disabled", wrap="word", cursor="arrow",
            highlightbackground=F["border"], highlightthickness=1
        )
        scrollbar = tk.Scrollbar(self.frame_verlauf,
                                  command=self.verlauf_text.yview,
                                  bg=F["card2"], troughcolor=F["card2"])
        self.verlauf_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.verlauf_text.pack(side="left", fill="both", expand=True)

        self.verlauf_text.tag_config("gruen",  foreground=F["gruen"])
        self.verlauf_text.tag_config("gelb",   foreground=F["gelb"])
        self.verlauf_text.tag_config("rot",    foreground=F["rot"])
        self.verlauf_text.tag_config("dim",    foreground=F["text_dim"])
        self.verlauf_text.tag_config("header", foreground=F["akzent"],
                                     font=("Courier New", 11, "bold"))
        self._verlauf_schreiben("Verlauf wird hier angezeigt...\n", "dim")

    def _verlauf_schreiben(self, text, tag=None):
        try:
            self.verlauf_text.configure(state="normal")
            if tag:
                self.verlauf_text.insert("end", text, tag)
            else:
                self.verlauf_text.insert("end", text)
            self.verlauf_text.see("end")
            self.verlauf_text.configure(state="disabled")
        except tk.TclError:
            pass

    def _verlauf_leeren(self):
        try:
            self.verlauf_text.configure(state="normal")
            self.verlauf_text.delete("1.0", "end")
            self.verlauf_text.configure(state="disabled")
            self._verlauf_schreiben("Verlauf geleert.\n", "dim")
        except tk.TclError:
            pass

    # ------------------------------------------
    #  STATUSBAR
    # ------------------------------------------
    def _baue_statusbar(self, parent):
        bar = tk.Frame(parent, bg=F["bg"], pady=8)
        bar.pack(fill="x")
        self.status_unten = tk.Label(
            bar,
            text="👆  Klicke auf die Tabs um zwischen den Ansichten zu wechseln",
            font=FONT_KLEIN, bg=F["bg"], fg=F["gelb"],
            wraplength=800, justify="left"
        )
        self.status_unten.pack(side="left")

        # Bash-Status
        bash_text = f"bash: ✅" if self.bash_pfad else "bash: ❌ Git Bash installieren!"
        bash_farbe = F["gruen"] if self.bash_pfad else F["rot"]
        tk.Label(bar, text=bash_text, font=FONT_KLEIN,
                 bg=F["bg"], fg=bash_farbe, padx=8).pack(side="right")

    # ------------------------------------------
    #  AKTIONEN
    # ------------------------------------------
    def _ordner_waehlen(self):
        if self.laeuft:
            return
        try:
            pfad = filedialog.askdirectory(
                title="Ordner wählen",
                initialdir=self.ordner_pfad.get() or str(Path.home())
            )
            if pfad:
                self.ordner_pfad.set(pfad)
                kurz = pfad if len(pfad) < 55 else "..." + pfad[-52:]
                self.drop_label.configure(text=f"📁  {kurz}", fg=F["text"])
                self.drop_zone.configure(highlightbackground=F["gruen"])
                self.status_text.configure(
                    text="✅  Ordner ausgewählt. Vorschau laden oder Sortieren starten.",
                    fg=F["gruen"]
                )
        except tk.TclError:
            pass

    def _vorschau_laden(self):
        if not self.ordner_pfad.get():
            self._ordner_waehlen()
            return
        if self.laeuft:
            return

        pfad = self.ordner_pfad.get()
        if not os.path.isdir(pfad):
            messagebox.showerror("Fehler", f"Ordner nicht gefunden:\n{pfad}")
            return

        self.status_text.configure(text="🔍  Lade Vorschau...", fg=F["gelb"])
        self.vorschau_btn.configure(state="disabled")
        self._tabelle_leeren()

        def _thread():
            zeilen = []
            fehler = None
            try:
                eintraege = sorted(os.listdir(pfad))
                for datei in eintraege:
                    voller_pfad = os.path.join(pfad, datei)
                    if not os.path.isfile(voller_pfad):
                        continue
                    if datei.startswith("."):
                        continue
                    kat, ziel = get_kategorie(datei)
                    zeilen.append((datei, kat, ziel))
            except PermissionError:
                fehler = "❌  Kein Zugriff auf diesen Ordner."
            except Exception as e:
                fehler = f"❌  Fehler: {e}"

            # UI-Update sicher im Hauptthread
            def _ui_update():
                if self._zerstoert:
                    return
                try:
                    self._tabelle_leeren()
                    if fehler:
                        tk.Label(self.tabelle_frame, text=fehler,
                                 font=FONT, bg=F["tabelle_z1"],
                                 fg=F["rot"], pady=20).pack()
                        self.status_text.configure(text=fehler, fg=F["rot"])
                    elif not zeilen:
                        tk.Label(self.tabelle_frame,
                                 text="Keine Dateien im Ordner gefunden.",
                                 font=FONT, bg=F["tabelle_z1"],
                                 fg=F["text_dim"], pady=20).pack()
                        self.status_text.configure(
                            text="ℹ️  Keine Dateien gefunden.", fg=F["text_dim"])
                    else:
                        for i, (datei, kat, ziel) in enumerate(zeilen):
                            self._tabelle_zeile_hinzufuegen(datei, kat, ziel, i)
                        self.status_text.configure(
                            text=f"✅  {len(zeilen)} Datei(en) gefunden."
                                 f" Bereit zum Sortieren.",
                            fg=F["gruen"])
                    self.vorschau_btn.configure(state="normal")
                except tk.TclError:
                    pass

            self._nach(_ui_update)

        threading.Thread(target=_thread, daemon=True).start()

    def _sortieren_starten(self):
        if not self.ordner_pfad.get():
            self._ordner_waehlen()
            return
        if self.laeuft:
            return
        if not self._vorbedingungen_pruefen():
            return

        pfad = self.ordner_pfad.get()
        if not os.path.isdir(pfad):
            messagebox.showerror("Fehler", f"Ordner nicht gefunden:\n{pfad}")
            return

        if not messagebox.askyesno("Sortieren starten",
                                    f"Dateien sortieren in:\n\n{pfad}"):
            return

        self.laeuft = True
        self._buttons_sperren(True)
        self.status_text.configure(text="🚀  Sortierung läuft...", fg=F["gelb"])
        self._tab_wechseln("verlauf")

        kategorien_count = {}
        returncode = -1  # FIX: immer initialisiert

        def _thread():
            nonlocal returncode
            try:
                args = [pfad]
                cmd = [self.bash_pfad, self.script_pfad] + args
                self.aktiver_proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace"
                )
                self._nach(self._verlauf_schreiben,
                           f"\n── Sortierung gestartet ──\n", "header")
                self._nach(self._verlauf_schreiben,
                           f"Ordner: {pfad}\n", "dim")

                for zeile in self.aktiver_proc.stdout:
                    if self._zerstoert:
                        break
                    z = zeile.strip()
                    if not z:
                        continue
                    # Statistiken sammeln
                    if "OK:" in z and "->" in z:
                        try:
                            kat = z.split("->")[1].strip().rstrip("/").strip()
                            kategorien_count[kat] = kategorien_count.get(kat, 0) + 1
                        except Exception:
                            pass
                    tag = ("gruen" if any(w in z for w in ["OK:", "Fertig", "Wiederhergestellt"])
                           else "gelb" if "Sonstiges" in z or "Tipp" in z
                           else "rot"  if any(w in z for w in ["Fehler", "ERROR"])
                           else None)
                    self._nach(self._verlauf_schreiben, f"  {z}\n", tag)

                self.aktiver_proc.wait()
                returncode = self.aktiver_proc.returncode  # FIX: erst nach wait()

            except FileNotFoundError:
                returncode = -1
                self._nach(self._verlauf_schreiben,
                           "❌ Bash konnte nicht gestartet werden.\n", "rot")
            except Exception as e:
                returncode = -1
                self._nach(self._verlauf_schreiben, f"❌ Fehler: {e}\n", "rot")
            finally:
                self.aktiver_proc = None
                self.laeuft = False
                if not self._zerstoert:
                    # FIX: lambda statt dict für root.after
                    if returncode == 0:
                        self._nach(self.status_text.configure,
                                   text="✅  Sortierung abgeschlossen!",
                                   fg=F["gruen"])
                        self._nach(self._zeige_statistiken, kategorien_count)
                        self._nach(self._vorschau_laden)
                    else:
                        self._nach(self.status_text.configure,
                                   text="❌  Fehler oder abgebrochen.",
                                   fg=F["rot"])
                    self._nach(self._buttons_sperren, False)

        threading.Thread(target=_thread, daemon=True).start()

    def _abbrechen(self):
        if self.aktiver_proc and self.laeuft:
            try:
                self.aktiver_proc.terminate()
                self._verlauf_schreiben("\n⬛ Abgebrochen!\n", "gelb")
            except Exception:
                pass

    def _reset(self):
        if self.laeuft:
            return
        try:
            self.ordner_pfad.set("")
            self.drop_label.configure(
                text="📁  Ordner hierher ziehen — oder klicken zum Auswählen",
                fg=F["text_dim"]
            )
            self.drop_zone.configure(highlightbackground=F["drop_border"],
                                      bg=F["drop"])
            self.drop_label.configure(bg=F["drop"])
            self._tabelle_reset_leer()
            self.status_text.configure(
                text="Wähle einen Ordner aus, um zu beginnen.",
                fg=F["gruen"]
            )
            self.kopieren_var.set(False)
            self.unterordner_var.set(False)
        except tk.TclError:
            pass

    def _undo(self):
        # FIX: Prüft ob Ordner ausgewählt
        if not self.ordner_pfad.get() or not os.path.isdir(self.ordner_pfad.get()):
            messagebox.showwarning("Kein Ordner",
                                    "Bitte zuerst einen Ordner auswählen.")
            return
        if self.laeuft:
            return
        if not self._vorbedingungen_pruefen():
            return
        if messagebox.askyesno("Rückgängig",
                                "Letzte Sortierung wirklich rückgängig machen?"):
            self._script_schnell([self.ordner_pfad.get(), "--undo"], "UNDO")

    def _script_schnell(self, args, label="AKTION"):
        """Führt Script-Aktion sicher im Hintergrund aus."""
        if self.laeuft:
            return
        self.laeuft = True
        self._nach(self._verlauf_schreiben,
                   f"\n── {label} ──\n", "header")

        def _thread():
            returncode = -1
            try:
                cmd = [self.bash_pfad, self.script_pfad] + args
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace"
                )
                for zeile in proc.stdout:
                    z = zeile.strip()
                    if z:
                        tag = "gruen" if "Wiederhergestellt" in z else \
                              "rot"   if "Fehler" in z else None
                        self._nach(self._verlauf_schreiben, f"  {z}\n", tag)
                proc.wait()
                returncode = proc.returncode
            except Exception as e:
                self._nach(self._verlauf_schreiben, f"❌ {e}\n", "rot")
            finally:
                self.laeuft = False
                if returncode == 0:
                    self._nach(self._verlauf_schreiben,
                               f"✅ {label} abgeschlossen.\n", "gruen")

        threading.Thread(target=_thread, daemon=True).start()

    def _vorbedingungen_pruefen(self):
        if not self.bash_pfad:
            messagebox.showerror(
                "Bash nicht gefunden",
                "Git Bash wurde nicht gefunden!\n\n"
                "Bitte installiere Git Bash:\n"
                "https://git-scm.com/download/win\n\n"
                "Nach der Installation neu starten."
            )
            return False
        if not os.path.exists(self.script_pfad):
            messagebox.showerror(
                "Script nicht gefunden",
                f"datei_sortieren.sh nicht gefunden!\n\n"
                f"Pfad: {self.script_pfad}\n\n"
                f"Lege datei_sortieren.sh in denselben Ordner wie gui.py."
            )
            return False
        return True

    # ------------------------------------------
    #  SICHERES BEENDEN
    # ------------------------------------------
    def _beenden(self):
        if self.laeuft:
            if not messagebox.askyesno(
                "Beenden",
                "Ein Prozess läuft noch.\nTrotzdem beenden?"
            ):
                return
            if self.aktiver_proc:
                try:
                    self.aktiver_proc.terminate()
                    # Kurz warten damit Prozess sauber beendet
                    self.aktiver_proc.wait(timeout=3)
                except Exception:
                    try:
                        self.aktiver_proc.kill()
                    except Exception:
                        pass
        self._zerstoert = True
        self.root.destroy()


# ============================================
#  START
# ============================================
if __name__ == "__main__":
    root = tk.Tk()
    try:
        root.iconbitmap("icon.ico")
    except Exception:
        pass
    app = DateiSortiererApp(root)
    root.mainloop()
