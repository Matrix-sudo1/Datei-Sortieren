#!/usr/bin/env python3
# ============================================
#  Datei-Sortierer GUI v5.0
#  NEU:
#  - Drag & Drop (Ordner ins Fenster ziehen)
#  - Dark / Light Theme Umschalter
#  - Geplante Sortierung (Cronjob-Tab)
# ============================================

import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess, threading, os, shutil, platform, re
from pathlib import Path

# ANSI-Escape-Codes aus Script-Ausgabe entfernen
_ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')

# ============================================
#  THEMES
# ============================================
THEMES = {
    "dark": {
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
        "btn_text":   "#ffffff",
        "scrollbar":  "#2a3050",
    },
    "light": {
        "bg":         "#f0f2f8",
        "card":       "#ffffff",
        "card2":      "#f5f7ff",
        "nav":        "#e8eaf6",
        "tab_aktiv":  "#6c3fc5",
        "akzent":     "#6c3fc5",
        "akzent2":    "#2d6bbf",
        "start":      "#e8435a",
        "gruen":      "#27ae60",
        "gelb":       "#e67e22",
        "rot":        "#e8435a",
        "text":       "#1a1a2e",
        "text_dim":   "#6b7280",
        "border":     "#d0d5e8",
        "tabelle_hd": "#e0e5f5",
        "tabelle_z1": "#ffffff",
        "tabelle_z2": "#f5f7ff",
        "drop":       "#eef0fc",
        "drop_border":"#9b7fe8",
        "btn_text":   "#ffffff",
        "scrollbar":  "#d0d5e8",
    }
}

FONT       = ("Segoe UI", 11)
FONT_BOLD  = ("Segoe UI", 11, "bold")
FONT_TITEL = ("Segoe UI", 20, "bold")
FONT_KLEIN = ("Segoe UI", 9)
FONT_TAB   = ("Segoe UI", 12, "bold")
FONT_BTN   = ("Segoe UI", 12, "bold")

KATEGORIEN_PYTHON = {
    "Bilder":        ["jpg","jpeg","png","gif","bmp","svg","webp","tiff","tif","ico","heic","raw","cr2","nef"],
    "Videos":        ["mp4","mkv","avi","mov","wmv","flv","webm","m4v","mpeg","mpg"],
    "Audio":         ["mp3","wav","flac","aac","ogg","wma","m4a","opus"],
    "Dokumente":     ["pdf","doc","docx","odt","txt","rtf","md"],
    "Tabellen":      ["xls","xlsx","csv","ods"],
    "Praesentation": ["ppt","pptx","odp"],
    "Archive":       ["zip","tar","gz","bz2","rar","7z","xz"],
    "Code":          ["sh","py","js","ts","html","css","php","java","c","cpp","h","rb","go","rs","sql"],
    "Ausfuehrbar":   ["exe","dmg","deb","rpm","appimage"],
    "Schriften":     ["ttf","otf","woff","woff2"],
}

def get_kategorie(name):
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    kat = _EXT_TO_KAT.get(ext, "Sonstiges")
    return kat, kat + "/"

# Vorgebaut für O(1)-Lookup (statt O(n×m)-Schleife bei jedem Aufruf)
_EXT_TO_KAT = {
    ext: kat
    for kat, exts in KATEGORIEN_PYTHON.items()
    for ext in exts
}


# ============================================
#  DRAG & DROP HELPER
# ============================================
def setup_drag_drop(widget, callback):
    """Plattformübergreifendes Drag & Drop via tkinterdnd2 (optional)
       Fallback: Clipboard-basiert oder einfacher Klick-Dialog."""
    try:
        import tkinterdnd2 as dnd  # type: ignore
        widget.drop_target_register(dnd.DND_FILES)
        widget.dnd_bind("<<Drop>>", lambda e: callback(_parse_drop(e.data)))
        return True
    except Exception:
        return False

def _parse_drop(data):
    """Extrahiert Pfad aus Drop-Event ('{/pfad/mit leerzeichen}' Format)."""
    data = data.strip()
    if data.startswith("{"):
        data = data[1:data.rfind("}")]
    return data.split("} {")[0]  # nur erstes Element


# ============================================
#  HAUPT-APP
# ============================================
class DateiSortiererApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Datei-Sortierer v5.0")
        self.root.geometry("900x780")
        self.root.minsize(800, 660)
        self.root.resizable(True, True)

        # Zustand
        self.ordner_pfad     = tk.StringVar(value="")
        self.kopieren_var    = tk.BooleanVar(value=False)
        self.unterordner_var = tk.BooleanVar(value=False)
        self.notify_var      = tk.BooleanVar(value=False)
        self.bericht_var     = tk.BooleanVar(value=False)
        self._theme_name     = "dark"
        self._aktiver_tab    = "sortieren"   # Fix 5: Tab-Tracking für Theme
        self._zerstoert      = False

        self._lock            = threading.Lock()
        self._laeuft          = False
        self.aktiver_proc     = None
        self._vorschau_laeuft = False
        self._vorschau_lock   = threading.Lock()
        self._log_zeilen      = 0   # Instanz-Variable (nicht Klassen-Variable!)
        self._last_kat_count  = {}  # für Theme-Wechsel: Statistiken neu rendern

        self.script_pfad = self._finde_script()
        self.bash_pfad   = self._finde_bash()

        self._F = dict(THEMES["dark"])   # aktives Theme
        self._alle_widgets = []           # für Theme-Neuanwendung
        self._checkbuttons = []           # für Checkbutton-Theme-Updates

        self._baue_ui()
        self._drop_setup()
        self.root.protocol("WM_DELETE_WINDOW", self._beenden)

    # ------------------------------------------
    #  PROPERTIES
    # ------------------------------------------
    @property
    def laeuft(self):
        with self._lock: return self._laeuft
    @laeuft.setter
    def laeuft(self, w):
        with self._lock: self._laeuft = w

    def F(self, key):
        return self._F.get(key, "#888888")

    # ------------------------------------------
    #  SYSTEM
    # ------------------------------------------
    def _finde_script(self):
        basis = Path(__file__).parent
        for p in [basis / "datei_sortieren.sh",
                  Path.home() / "Datei-Sortieren" / "datei_sortieren.sh"]:
            if p.exists(): return str(p)
        return str(basis / "datei_sortieren.sh")

    def _finde_bash(self):
        bash = shutil.which("bash")
        if bash: return bash
        for p in [r"C:\Program Files\Git\bin\bash.exe",
                  r"C:\Program Files (x86)\Git\bin\bash.exe"]:
            if os.path.exists(p): return p
        return None

    # ------------------------------------------
    #  UI SICHER
    # ------------------------------------------
    def _ui(self, fn, *a, **kw):
        if not self._zerstoert:
            try: fn(*a, **kw)
            except tk.TclError: pass

    def _nach(self, fn, *a, **kw):
        if not self._zerstoert:
            self.root.after(0, lambda: self._ui(fn, *a, **kw))

    # ------------------------------------------
    #  THEME
    # ------------------------------------------
    def _theme_umschalten(self):
        self._theme_name = "light" if self._theme_name == "dark" else "dark"
        self._F = dict(THEMES[self._theme_name])
        self._theme_anwenden()

    def _theme_anwenden(self):
        """Wendet das aktuelle Theme auf alle registrierten Widgets an."""
        F = self._F

        # Root
        self.root.configure(bg=F["bg"])

        # Registrierte Frames/Labels (bg + fg fuer Labels)
        for widget, rolle in self._alle_widgets:
            try:
                bg = F.get(rolle, F["card"])
                widget.configure(bg=bg)
                if isinstance(widget, tk.Label):
                    try: widget.configure(fg=F["text"])
                    except tk.TclError: pass
            except Exception:
                pass

        # Theme-Button
        try:
            lbl = "☀️  Light" if self._theme_name == "dark" else "🌙  Dark"
            self.theme_btn.configure(text=lbl,
                                      bg=F["nav"], fg=F["text_dim"],
                                      activebackground=F["tab_aktiv"],
                                      activeforeground=F["text"])
        except Exception:
            pass

        # drop_zone + drop_label
        try:
            hat_ordner = bool(self.ordner_pfad.get())
            rand = F["gruen"] if hat_ordner else F["drop_border"]
            self.drop_zone.configure(bg=F["drop"], highlightbackground=rand)
            self.drop_label.configure(bg=F["drop"],
                                       fg=F["text"] if hat_ordner else F["text_dim"])
        except Exception:
            pass

        # verlauf_text + Tag-Farben
        try:
            self.verlauf_text.configure(bg=F["card2"], fg=F["text"],
                                         highlightbackground=F["border"])
            self.verlauf_text.tag_config("gruen",  foreground=F["gruen"])
            self.verlauf_text.tag_config("gelb",   foreground=F["gelb"])
            self.verlauf_text.tag_config("rot",    foreground=F["rot"])
            self.verlauf_text.tag_config("dim",    foreground=F["text_dim"])
            self.verlauf_text.tag_config("header", foreground=F["akzent"])
        except Exception:
            pass

        # Tab-Buttons (korrekt via _aktiver_tab)
        try:
            for k, btn in self.tab_buttons.items():
                aktiv = (k == self._aktiver_tab)
                btn.configure(bg=F["tab_aktiv"] if aktiv else F["nav"],
                              fg=F["text"] if aktiv else F["text_dim"],
                              activebackground=F["tab_aktiv"],
                              activeforeground=F["text"])
        except Exception:
            pass

        # Fix 5: Rahmenfarben (highlightbackground) fuer gerahmte Widgets
        for attr in ("karte_rahmen", "tabelle_aussen_rahmen"):
            w = getattr(self, attr, None)
            if w:
                try: w.configure(highlightbackground=F["border"])
                except Exception: pass

        # Fix 6: Checkbutton-Farben
        for cb in getattr(self, "_checkbuttons", []):
            try:
                cb.configure(bg=F["card"], fg=F["text"],
                              selectcolor=F["akzent"],
                              activebackground=F["card"],
                              activeforeground=F["text"])
            except Exception: pass

        # Fix 7: Vorschau-Tabelle Canvas + Zeilen
        try:
            self.tabelle_canvas.configure(bg=F["tabelle_z1"])
            self.tabelle_frame.configure(bg=F["tabelle_z1"])
            for idx, row in enumerate(self.tabelle_frame.winfo_children()):
                if isinstance(row, tk.Label): continue
                bg = F["tabelle_z1"] if idx % 2 == 0 else F["tabelle_z2"]
                try:
                    row.configure(bg=bg)
                    for child in row.winfo_children():
                        child.configure(bg=bg, fg=F["text"])
                except Exception: pass
        except Exception:
            pass

        # Fix 8: status_unten behaelt eigene Farbe (Gelb)
        try:
            self.status_unten.configure(fg=F["gelb"], bg=F["bg"])
        except Exception:
            pass

        # status_text bg aktualisieren (fg bleibt wie zuletzt gesetzt)
        try:
            self.status_text.configure(bg=F["card"])
        except Exception:
            pass

        # Bug 10: Statistiken mit neuen Theme-Farben neu rendern
        if self._last_kat_count:
            try: self._zeige_statistiken(self._last_kat_count)
            except Exception: pass

        # Bug 11: App-Titel Labels mit eigenen fg-Farben aktualisieren
        for attr, fg_key in [("titel_icon_lbl", "gelb"),
                              ("titel_name_lbl", "text"),
                              ("titel_version_lbl", "text_dim")]:
            w = getattr(self, attr, None)
            if w:
                try: w.configure(bg=F["card"], fg=F[fg_key])
                except Exception: pass

        # Bug 12: Verlauf-Tab Buttons mit Theme-Farben aktualisieren
        for attr, bg_key, fg_key in [
            ("undo_btn",           "akzent", "btn_text"),
            ("log_btn",            "nav",    "text_dim"),
            ("verlauf_leeren_btn", "nav",    "text_dim"),
        ]:
            w = getattr(self, attr, None)
            if w:
                try: w.configure(bg=F[bg_key], fg=F[fg_key],
                                  activebackground=F["tab_aktiv"],
                                  activeforeground=F["text"])
                except Exception: pass

    def _reg(self, widget, rolle="card"):
        """Widget für Theme-Updates registrieren."""
        self._alle_widgets.append((widget, rolle))
        return widget

    # ------------------------------------------
    #  DRAG & DROP
    # ------------------------------------------
    def _drop_setup(self):
        ok = setup_drag_drop(self.root, self._drop_empfangen)
        if ok:
            self._drop_label_aktualisieren("📁  Ordner hier ablegen oder klicken")
        else:
            self._drop_label_aktualisieren("📁  Klicken zum Ordner auswählen")

    def _drop_empfangen(self, pfad):
        pfad = pfad.strip()
        if os.path.isdir(pfad):
            self.ordner_pfad.set(pfad)
            kurz = pfad if len(pfad) < 55 else "..." + pfad[-52:]
            self._drop_label_aktualisieren(f"📁  {kurz}")
            try:
                self.drop_zone.configure(highlightbackground=self._F["gruen"])
                self.drop_label.configure(fg=self._F["text"])
            except Exception: pass
            self.status_text.configure(
                text="✅  Ordner ausgewählt. Vorschau laden oder Sortieren starten.",
                fg=self._F["gruen"])
        else:
            messagebox.showwarning("Kein Ordner", f"'{pfad}' ist kein gültiger Ordner.")

    def _drop_label_aktualisieren(self, text):
        try: self.drop_label.configure(text=text)
        except Exception: pass

    # ------------------------------------------
    #  UI AUFBAUEN
    # ------------------------------------------
    def _baue_ui(self):
        F = self._F
        aussen = tk.Frame(self.root, bg=F["bg"], padx=20, pady=16)
        aussen.pack(fill="both", expand=True)
        self._reg(aussen, "bg")

        self._baue_titelleiste(aussen)

        karte = tk.Frame(aussen, bg=F["card"],
                         highlightbackground=F["border"],
                         highlightthickness=1)
        karte.pack(fill="both", expand=True)
        self._reg(karte, "card")
        self.karte_rahmen = karte  # für highlightbackground im Theme-Wechsel

        self._baue_macos_buttons(karte)
        self._baue_app_titel(karte)
        self._baue_tabs(karte)

        self.tab_inhalt = tk.Frame(karte, bg=F["card"])
        self.tab_inhalt.pack(fill="both", expand=True, padx=24, pady=(0, 16))
        self._reg(self.tab_inhalt, "card")

        self._baue_tab_sortieren()
        self._baue_tab_statistiken()
        self._baue_tab_verlauf()
        self._baue_tab_cronjob()

        self._tab_wechseln("sortieren")
        self._baue_statusbar(aussen)

    def _baue_titelleiste(self, parent):
        F = self._F
        leiste = tk.Frame(parent, bg=F["bg"], pady=6)
        leiste.pack(fill="x")
        self._reg(leiste, "bg")
        tk.Label(leiste, text="🖥  DATEI-SORTIERER – GUI v5.0",
                 font=("Segoe UI", 13, "bold"),
                 bg=F["bg"], fg=F["text"]).pack(side="left")
        # Theme-Button oben rechts
        self.theme_btn = tk.Button(
            leiste, text="☀️  Light",
            font=FONT_KLEIN, bg=F["nav"], fg=F["text_dim"],
            activebackground=F["tab_aktiv"], activeforeground=F["text"],
            relief="flat", cursor="hand2", padx=10, pady=4,
            command=self._theme_umschalten)
        self.theme_btn.pack(side="right")

    def _baue_macos_buttons(self, parent):
        F = self._F
        leiste = tk.Frame(parent, bg=F["card"], pady=10, padx=16)
        leiste.pack(fill="x")
        self._reg(leiste, "card")
        for farbe, cmd in [("#e8435a", self._beenden),
                            ("#f39c12", lambda: None),
                            ("#2ecc71", lambda: None)]:
            tk.Button(leiste, text="", width=2, bg=farbe,
                      activebackground=farbe, relief="flat",
                      cursor="hand2", command=cmd, bd=0).pack(side="left", padx=3)
        tk.Label(leiste, text="📁 Datei-Sortierer v5.0",
                 font=FONT, bg=F["card"], fg=F["text_dim"]).pack(side="left", padx=12)

    def _baue_app_titel(self, parent):
        F = self._F
        r = tk.Frame(parent, bg=F["card"], pady=12)
        r.pack(fill="x", padx=24)
        self._reg(r, "card")
        self.titel_icon_lbl = tk.Label(r, text="📁", font=("Segoe UI Emoji", 26),
                 bg=F["card"], fg=F["gelb"])
        self.titel_icon_lbl.pack(side="left")
        self.titel_name_lbl = tk.Label(r, text=" Datei-Sortierer",
                 font=FONT_TITEL, bg=F["card"], fg=F["text"])
        self.titel_name_lbl.pack(side="left")
        self.titel_version_lbl = tk.Label(r, text="  v5.0", font=("Segoe UI", 13),
                 bg=F["card"], fg=F["text_dim"])
        self.titel_version_lbl.pack(side="left", pady=4)

    def _baue_tabs(self, parent):
        F = self._F
        self.tab_rahmen = tk.Frame(parent, bg=F["card"], padx=24)
        self.tab_rahmen.pack(fill="x", pady=(0, 4))
        self._reg(self.tab_rahmen, "card")
        self.tab_buttons = {}
        tabs = [("sortieren",   "🗂  Sortieren"),
                ("statistiken", "📊  Statistiken"),
                ("verlauf",     "🕐  Verlauf"),
                ("cronjob",     "⏰  Geplant")]
        for key, label in tabs:
            btn = tk.Button(
                self.tab_rahmen, text=label, font=FONT_TAB,
                bg=F["nav"], fg=F["text_dim"],
                activebackground=F["tab_aktiv"], activeforeground=F["text"],
                relief="flat", cursor="hand2", padx=18, pady=10,
                command=lambda k=key: self._tab_wechseln(k))
            btn.pack(side="left", padx=(0, 5))
            self.tab_buttons[key] = btn

    def _tab_wechseln(self, key):
        F = self._F
        self._aktiver_tab = key
        try:
            for k, btn in self.tab_buttons.items():
                btn.configure(
                    bg=F["tab_aktiv"] if k == key else F["nav"],
                    fg=F["text"] if k == key else F["text_dim"])
            for frame in [self.frame_sortieren, self.frame_statistiken,
                          self.frame_verlauf, self.frame_cronjob]:
                frame.pack_forget()
            {"sortieren":   self.frame_sortieren,
             "statistiken": self.frame_statistiken,
             "verlauf":     self.frame_verlauf,
             "cronjob":     self.frame_cronjob}[key].pack(fill="both", expand=True)
        except tk.TclError:
            pass

    # ------------------------------------------
    #  TAB: SORTIEREN
    # ------------------------------------------
    def _baue_tab_sortieren(self):
        F = self._F
        self.frame_sortieren = tk.Frame(self.tab_inhalt, bg=F["card"])
        self._reg(self.frame_sortieren, "card")

        # Drop-Zone
        self.drop_zone = tk.Frame(
            self.frame_sortieren, bg=F["drop"],
            highlightbackground=F["drop_border"],
            highlightthickness=2, cursor="hand2")
        self.drop_zone.pack(fill="x", pady=(8, 12))
        self.drop_label = tk.Label(
            self.drop_zone,
            text="📁  Ordner hier ablegen oder klicken",
            font=("Segoe UI", 13), bg=F["drop"], fg=F["text_dim"], pady=26)
        self.drop_label.pack()
        for w in [self.drop_zone, self.drop_label]:
            w.bind("<Button-1>", lambda e: self._ordner_waehlen())
            w.bind("<Enter>",    lambda e: self._drop_hover(True))
            w.bind("<Leave>",    lambda e: self._drop_hover(False))

        # Optionen
        opt = tk.Frame(self.frame_sortieren, bg=F["card"])
        opt.pack(fill="x", pady=(0, 10))
        self._reg(opt, "card")
        self._checkbox(opt, "📋  Kopieren", self.kopieren_var).pack(side="left", padx=(0,20))
        self._checkbox(opt, "🔄  Unterordner", self.unterordner_var).pack(side="left", padx=(0,20))
        self._checkbox(opt, "🔔  Benachrichtigen", self.notify_var).pack(side="left", padx=(0,20))
        self._checkbox(opt, "📄  HTML-Bericht", self.bericht_var).pack(side="left")

        # Vorschau-Tabelle
        tk.Label(self.frame_sortieren, text="VORSCHAU",
                 font=("Segoe UI", 9, "bold"),
                 bg=F["card"], fg=F["text_dim"]).pack(anchor="w", pady=(0, 4))

        tabelle_aussen = tk.Frame(self.frame_sortieren, bg=F["tabelle_hd"],
                                   highlightbackground=F["border"],
                                   highlightthickness=1)
        self.tabelle_aussen_rahmen = tabelle_aussen  # Theme-Update
        tabelle_aussen.pack(fill="both", expand=True)

        header = tk.Frame(tabelle_aussen, bg=F["tabelle_hd"])
        header.pack(fill="x")
        for text, breite in [("Dateiname", 28), ("Kategorie", 18), ("Ziel", 20)]:
            tk.Label(header, text=text, font=FONT_BOLD,
                     bg=F["tabelle_hd"], fg=F["text"],
                     width=breite, anchor="w", padx=12, pady=8).pack(side="left")

        c_rahmen = tk.Frame(tabelle_aussen, bg=F["tabelle_z1"])
        c_rahmen.pack(fill="both", expand=True)
        self.tabelle_canvas = tk.Canvas(c_rahmen, bg=F["tabelle_z1"],
                                         highlightthickness=0)
        scrollbar = tk.Scrollbar(c_rahmen, orient="vertical",
                                  command=self.tabelle_canvas.yview)
        self.tabelle_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tabelle_canvas.pack(side="left", fill="both", expand=True)
        self.tabelle_frame = tk.Frame(self.tabelle_canvas, bg=F["tabelle_z1"])
        self._tabelle_win = self.tabelle_canvas.create_window(
            (0,0), window=self.tabelle_frame, anchor="nw")
        self.tabelle_frame.bind("<Configure>", self._tabelle_scroll)
        self.tabelle_canvas.bind("<Configure>", self._tabelle_breite)
        self._tabelle_reset_leer()

        self.status_text = tk.Label(
            self.frame_sortieren,
            text="Wähle einen Ordner aus, um zu beginnen.",
            font=FONT, bg=F["card"], fg=F["gruen"], pady=8, anchor="w")
        self.status_text.pack(fill="x")

        btn_leiste = tk.Frame(self.frame_sortieren, bg=F["card"])
        btn_leiste.pack(fill="x", pady=(4, 0))
        self._reg(btn_leiste, "card")

        self.vorschau_btn = tk.Button(
            btn_leiste, text="🔍  Vorschau",
            font=FONT_BTN, bg=F["akzent2"], fg=F["btn_text"],
            activebackground="#1a4a8a", activeforeground=F["btn_text"],
            relief="flat", cursor="hand2", pady=12,
            command=self._vorschau_laden)
        self.vorschau_btn.pack(side="left", fill="x", expand=True, padx=(0,6))

        self.start_btn = tk.Button(
            btn_leiste, text="🚀  Sortieren starten",
            font=FONT_BTN, bg=F["start"], fg=F["btn_text"],
            activebackground="#c0392b", activeforeground=F["btn_text"],
            relief="flat", cursor="hand2", pady=12,
            command=self._sortieren_starten)
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0,6))

        self.reset_btn = tk.Button(
            btn_leiste, text="🗑  Reset",
            font=FONT_BTN, bg=F["nav"], fg=F["text_dim"],
            activebackground=F["border"], activeforeground=F["text"],
            relief="flat", cursor="hand2", pady=12, width=9,
            command=self._reset)
        self.reset_btn.pack(side="left")

        self.abbruch_btn = tk.Button(
            btn_leiste, text="⬛  Abbrechen",
            font=FONT_BTN, bg=F["rot"], fg=F["btn_text"],
            activebackground="#c0392b", activeforeground=F["btn_text"],
            relief="flat", cursor="hand2", pady=12,
            command=self._abbrechen)

    def _tabelle_scroll(self, e=None):
        try: self.tabelle_canvas.configure(scrollregion=self.tabelle_canvas.bbox("all"))
        except tk.TclError: pass

    def _tabelle_breite(self, e):
        try: self.tabelle_canvas.itemconfig(self._tabelle_win, width=e.width)
        except tk.TclError: pass

    def _tabelle_leeren(self):
        try:
            for w in self.tabelle_frame.winfo_children(): w.destroy()
        except tk.TclError: pass

    def _tabelle_reset_leer(self):
        self._tabelle_leeren()
        try:
            tk.Label(self.tabelle_frame,
                     text="Ordner auswählen oder Vorschau laden...",
                     font=FONT, bg=self._F["tabelle_z1"],
                     fg=self._F["text_dim"], pady=28).pack()
        except tk.TclError: pass

    def _tabelle_zeile(self, dateiname, kategorie, ziel, i):
        F = self._F
        try:
            bg = F["tabelle_z1"] if i % 2 == 0 else F["tabelle_z2"]
            zeile = tk.Frame(self.tabelle_frame, bg=bg)
            zeile.pack(fill="x")
            for text, breite in [(dateiname, 28), (kategorie, 18), (ziel, 20)]:
                tk.Label(zeile, text=text, font=FONT, bg=bg, fg=F["text"],
                         width=breite, anchor="w", padx=12, pady=6).pack(side="left")
        except tk.TclError: pass

    def _drop_hover(self, aktiv):
        F = self._F
        try:
            if aktiv:
                self.drop_zone.configure(highlightbackground=F["akzent"], bg=F["card2"])
                self.drop_label.configure(bg=F["card2"])
            else:
                farbe = F["gruen"] if self.ordner_pfad.get() else F["drop_border"]
                self.drop_zone.configure(highlightbackground=farbe, bg=F["drop"])
                self.drop_label.configure(bg=F["drop"])
        except tk.TclError: pass

    def _checkbox(self, parent, text, variable):
        F = self._F
        r = tk.Frame(parent, bg=F["card"])
        self._reg(r, "card")
        cb = tk.Checkbutton(r, text=text, variable=variable, font=FONT,
                             bg=F["card"], fg=F["text"], selectcolor=F["akzent"],
                             activebackground=F["card"], activeforeground=F["text"],
                             cursor="hand2", relief="flat")
        cb.pack(side="left")
        self._checkbuttons.append(cb)  # für Theme-Updates
        return r

    def _buttons_sperren(self, sperren):
        F = self._F
        try:
            zustand = "disabled" if sperren else "normal"
            for attr in ["vorschau_btn","start_btn","reset_btn","undo_btn","log_btn"]:
                btn = getattr(self, attr, None)
                if btn:
                    try: btn.configure(state=zustand)
                    except tk.TclError: pass
            if sperren:
                self.start_btn.configure(text="⏳  Läuft...")
                self.abbruch_btn.pack(side="left", fill="x", expand=True, padx=(6,0))
            else:
                self.start_btn.configure(text="🚀  Sortieren starten")
                try: self.abbruch_btn.pack_forget()
                except tk.TclError: pass
        except tk.TclError: pass

    # ------------------------------------------
    #  TAB: STATISTIKEN
    # ------------------------------------------
    def _baue_tab_statistiken(self):
        F = self._F
        self.frame_statistiken = tk.Frame(self.tab_inhalt, bg=F["card"])
        self._reg(self.frame_statistiken, "card")
        tk.Label(self.frame_statistiken, text="📊  Statistiken",
                 font=FONT_TITEL, bg=F["card"], fg=F["text"], pady=16).pack()
        self.stats_frame = tk.Frame(self.frame_statistiken, bg=F["card"])
        self.stats_frame.pack(fill="both", expand=True, padx=16)
        self._reg(self.stats_frame, "card")
        tk.Label(self.stats_frame, text="Noch keine Sortierung.",
                 font=FONT, bg=F["card"], fg=F["text_dim"], pady=30).pack()

    def _zeige_statistiken(self, kat_count):
        self._last_kat_count = dict(kat_count)
        F = self._F
        try:
            for w in self.stats_frame.winfo_children(): w.destroy()
            gesamt = sum(kat_count.values())
            if not gesamt:
                tk.Label(self.stats_frame, text="Keine Dateien sortiert.",
                         font=FONT, bg=F["card"], fg=F["text_dim"], pady=20).pack()
                return
            tk.Label(self.stats_frame, text=f"Letzte Sortierung: {gesamt} Datei(en)",
                     font=FONT_BOLD, bg=F["card"], fg=F["gruen"], pady=8).pack(anchor="w")
            for kat, anz in sorted(kat_count.items(), key=lambda x: x[1], reverse=True):
                zeile = tk.Frame(self.stats_frame, bg=F["card2"],
                                  highlightbackground=F["border"], highlightthickness=1)
                zeile.pack(fill="x", pady=2)
                tk.Label(zeile, text=f"  {kat}", font=FONT, bg=F["card2"],
                         fg=F["text"], width=22, anchor="w", pady=7).pack(side="left")
                breite = max(20, int(anz / gesamt * 260))
                tk.Frame(zeile, bg=F["akzent"], width=breite, height=16).pack(
                    side="left", padx=8, pady=8)
                tk.Label(zeile, text=f"{anz}x", font=FONT_BOLD,
                         bg=F["card2"], fg=F["akzent"]).pack(side="left")
        except tk.TclError: pass

    # ------------------------------------------
    #  TAB: VERLAUF
    # ------------------------------------------
    def _baue_tab_verlauf(self):
        F = self._F
        self.frame_verlauf = tk.Frame(self.tab_inhalt, bg=F["card"])
        self._reg(self.frame_verlauf, "card")

        header = tk.Frame(self.frame_verlauf, bg=F["card"])
        header.pack(fill="x", pady=(10, 8))
        self._reg(header, "card")
        tk.Label(header, text="🕐  Verlauf",
                 font=FONT_TITEL, bg=F["card"], fg=F["text"]).pack(side="left")

        btn_gruppe = tk.Frame(header, bg=F["card"])
        btn_gruppe.pack(side="right")
        self._reg(btn_gruppe, "card")

        self.undo_btn = tk.Button(
            btn_gruppe, text="↩ Rückgängig", font=FONT_BOLD,
            bg=F["akzent"], fg=F["btn_text"],
            activebackground="#4a2a9a", activeforeground=F["btn_text"],
            relief="flat", cursor="hand2", padx=14, pady=7,
            command=self._undo)
        self.undo_btn.pack(side="left", padx=(0,5))

        self.log_btn = tk.Button(
            btn_gruppe, text="📋 Log", font=FONT_BOLD,
            bg=F["nav"], fg=F["text_dim"],
            activebackground=F["gruen"], activeforeground=F["btn_text"],
            relief="flat", cursor="hand2", padx=14, pady=7,
            command=self._zeige_log)
        self.log_btn.pack(side="left", padx=(0,5))

        self.verlauf_leeren_btn = tk.Button(
            btn_gruppe, text="✕ Leeren", font=FONT_BOLD,
            bg=F["nav"], fg=F["text_dim"],
            activebackground=F["rot"], activeforeground=F["btn_text"],
            relief="flat", cursor="hand2", padx=14, pady=7,
            command=self._verlauf_leeren)
        self.verlauf_leeren_btn.pack(side="left")

        self.verlauf_text = tk.Text(
            self.frame_verlauf, font=("Courier New", 10),
            bg=F["card2"], fg=F["text"], relief="flat", bd=8,
            state="disabled", wrap="word", cursor="arrow",
            highlightbackground=F["border"], highlightthickness=1)
        sb = tk.Scrollbar(self.frame_verlauf, command=self.verlauf_text.yview)
        self.verlauf_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.verlauf_text.pack(side="left", fill="both", expand=True)

        for tag, farbe in [("gruen", F["gruen"]), ("gelb", F["gelb"]),
                           ("rot", F["rot"]), ("dim", F["text_dim"]),
                           ("header", F["akzent"])]:
            self.verlauf_text.tag_config(tag, foreground=farbe)

        self._verlauf_schreiben("── Datei-Sortierer GUI v5.0 bereit ──\n", "header")
        self._verlauf_schreiben("Warte auf Aktion...\n\n", "dim")

    _LOG_MAX_ZEILEN = 2000

    def _verlauf_schreiben(self, text, tag=None):
        try:
            self.verlauf_text.configure(state="normal")
            if tag: self.verlauf_text.insert("end", text, tag)
            else:   self.verlauf_text.insert("end", text)
            self._log_zeilen += text.count("\n")
            if self._log_zeilen > self._LOG_MAX_ZEILEN:
                zu_loeschen = self._log_zeilen - self._LOG_MAX_ZEILEN
                self.verlauf_text.delete("1.0", f"{zu_loeschen + 1}.0")
                self._log_zeilen = self._LOG_MAX_ZEILEN
            self.verlauf_text.see("end")
            self.verlauf_text.configure(state="disabled")
        except tk.TclError: pass

    def _verlauf_leeren(self):
        try:
            self.verlauf_text.configure(state="normal")
            self.verlauf_text.delete("1.0", "end")
            self.verlauf_text.configure(state="disabled")
            self._log_zeilen = 0
            self._verlauf_schreiben("── Verlauf geleert ──\n", "dim")
        except tk.TclError: pass

    # ------------------------------------------
    #  TAB: CRONJOB (Geplante Sortierung)
    # ------------------------------------------
    def _baue_tab_cronjob(self):
        F = self._F
        self.frame_cronjob = tk.Frame(self.tab_inhalt, bg=F["card"])
        self._reg(self.frame_cronjob, "card")

        tk.Label(self.frame_cronjob, text="⏰  Geplante Sortierung",
                 font=FONT_TITEL, bg=F["card"], fg=F["text"], pady=16).pack()
        tk.Label(self.frame_cronjob,
                 text="Richtet einen Cronjob ein – Sortierung läuft täglich automatisch.",
                 font=FONT, bg=F["card"], fg=F["text_dim"]).pack(pady=(0,20))

        # Uhrzeit-Auswahl
        uhrzeit_rahmen = tk.Frame(self.frame_cronjob, bg=F["card2"],
                                   highlightbackground=F["border"],
                                   highlightthickness=1)
        uhrzeit_rahmen.pack(fill="x", padx=40, pady=(0,16))
        self._reg(uhrzeit_rahmen, "card2")

        zeile1 = tk.Frame(uhrzeit_rahmen, bg=F["card2"], pady=20, padx=24)
        zeile1.pack(fill="x")
        self._reg(zeile1, "card2")
        tk.Label(zeile1, text="🕐  Uhrzeit:", font=FONT_BOLD,
                 bg=F["card2"], fg=F["text"], width=14, anchor="w").pack(side="left")

        self.cron_stunde = tk.StringVar(value="20")
        self.cron_minute = tk.StringVar(value="00")

        stunden_spin = tk.Spinbox(zeile1, from_=0, to=23,
                                   textvariable=self.cron_stunde,
                                   format="%02.0f", width=4, font=FONT_BOLD,
                                   bg=F["nav"], fg=F["text"], relief="flat",
                                   buttonbackground=F["nav"],
                                   insertbackground=F["text"])
        stunden_spin.pack(side="left", padx=(0,4))
        tk.Label(zeile1, text=":", font=FONT_BOLD,
                 bg=F["card2"], fg=F["text"]).pack(side="left")
        minuten_spin = tk.Spinbox(zeile1, from_=0, to=59,
                                   textvariable=self.cron_minute,
                                   format="%02.0f", width=4, font=FONT_BOLD,
                                   bg=F["nav"], fg=F["text"], relief="flat",
                                   buttonbackground=F["nav"],
                                   insertbackground=F["text"])
        minuten_spin.pack(side="left", padx=(4,12))
        tk.Label(zeile1, text="Uhr  (täglich)", font=FONT,
                 bg=F["card2"], fg=F["text_dim"]).pack(side="left")

        zeile2 = tk.Frame(uhrzeit_rahmen, bg=F["card2"], pady=(0,16), padx=24)
        zeile2.pack(fill="x")
        self._reg(zeile2, "card2")
        tk.Label(zeile2, text="📁  Ordner:", font=FONT_BOLD,
                 bg=F["card2"], fg=F["text"], width=14, anchor="w").pack(side="left")
        tk.Label(zeile2, text="(wird vom Sortieren-Tab übernommen)",
                 font=FONT, bg=F["card2"], fg=F["text_dim"]).pack(side="left")

        # Buttons
        cron_btns = tk.Frame(self.frame_cronjob, bg=F["card"])
        cron_btns.pack(fill="x", padx=40, pady=(0,16))
        self._reg(cron_btns, "card")

        tk.Button(cron_btns, text="✅  Cronjob einrichten",
                  font=FONT_BTN, bg=F["gruen"], fg=F["btn_text"],
                  activebackground="#1e8449", activeforeground=F["btn_text"],
                  relief="flat", cursor="hand2", pady=12,
                  command=self._cronjob_einrichten).pack(side="left", fill="x", expand=True, padx=(0,8))

        tk.Button(cron_btns, text="📋  Alle anzeigen",
                  font=FONT_BTN, bg=F["akzent2"], fg=F["btn_text"],
                  activebackground="#1a4a8a", activeforeground=F["btn_text"],
                  relief="flat", cursor="hand2", pady=12,
                  command=self._cronjob_liste).pack(side="left", fill="x", expand=True, padx=(0,8))

        tk.Button(cron_btns, text="🗑  Alle entfernen",
                  font=FONT_BTN, bg=F["rot"], fg=F["btn_text"],
                  activebackground="#c0392b", activeforeground=F["btn_text"],
                  relief="flat", cursor="hand2", pady=12,
                  command=self._cronjob_entfernen).pack(side="left", fill="x", expand=True)

        # Status-Feld
        self.cron_status = tk.Label(
            self.frame_cronjob, text="",
            font=FONT, bg=F["card"], fg=F["text_dim"],
            wraplength=600, justify="left", pady=10)
        self.cron_status.pack(fill="x", padx=40)
        self._reg(self.cron_status, "card")

        # Info-Box
        info = tk.Frame(self.frame_cronjob, bg=F["card2"],
                         highlightbackground=F["border"],
                         highlightthickness=1)
        info.pack(fill="x", padx=40, pady=(8,0))
        self._reg(info, "card2")
        tk.Label(info, text="ℹ️  Hinweise",
                 font=FONT_BOLD, bg=F["card2"], fg=F["akzent"],
                 anchor="w", padx=16, pady=8).pack(fill="x")
        hinweise = (
            "• Cronjobs funktionieren auf Linux und macOS.\n"
            "• Auf Windows: Aufgabenplanung manuell einrichten.\n"
            "• Der Ordner muss vorher im Sortieren-Tab ausgewählt sein.\n"
            "• Bereits eingerichtete Sortierungen bleiben beim Hinzufügen erhalten.\n"
            "• 'Alle entfernen' löscht nur von diesem Tool erstellte Cronjobs."
        )
        tk.Label(info, text=hinweise, font=FONT, bg=F["card2"],
                 fg=F["text_dim"], anchor="w", justify="left",
                 padx=16, pady=10).pack(fill="x")

    def _cronjob_einrichten(self):
        if platform.system() == "Windows":
            messagebox.showinfo("Windows", 
                "Cronjobs werden auf Windows nicht unterstützt.\n\n"
                "Bitte nutze die Windows Aufgabenplanung (taskschd.msc).")
            return
        ordner = self.ordner_pfad.get()
        if not ordner or not os.path.isdir(ordner):
            messagebox.showwarning("Kein Ordner",
                "Bitte zuerst einen Ordner im 'Sortieren'-Tab auswählen.")
            return
        if not self._vorbedingungen_pruefen(): return
        try:
            stunde = int(self.cron_stunde.get())
            minute = int(self.cron_minute.get())
            if not (0 <= stunde <= 23 and 0 <= minute <= 59):
                raise ValueError
        except ValueError:
            messagebox.showerror("Ungültige Zeit", "Bitte gültige Uhrzeit eingeben (00:00–23:59).")
            return
        uhrzeit = f"{stunde:02d}:{minute:02d}"
        self._script_aktion([ordner, f"--cronjob", uhrzeit], "CRONJOB",
                             callback=lambda: self._nach(
                                 self.cron_status.configure,
                                 text=f"✅  Cronjob eingerichtet: täglich um {uhrzeit} Uhr für {ordner}",
                                 fg=self._F["gruen"]))

    def _cronjob_liste(self):
        if platform.system() == "Windows":
            messagebox.showinfo("Windows", "Cronjobs nicht verfügbar auf Windows.")
            return
        if not self._vorbedingungen_pruefen(): return
        self._script_aktion(["--cronjob-list"], "CRONJOB-LISTE")
        self._tab_wechseln("verlauf")

    def _cronjob_entfernen(self):
        if platform.system() == "Windows":
            messagebox.showinfo("Windows", "Cronjobs nicht verfügbar auf Windows.")
            return
        if not self._vorbedingungen_pruefen(): return
        if not messagebox.askyesno("Cronjobs entfernen",
                                    "Alle geplanten Sortierungen entfernen?"):
            return
        self._script_aktion(["--cronjob-remove"], "CRONJOB-REMOVE",
                             callback=lambda: self._nach(
                                 self.cron_status.configure,
                                 text="🗑  Alle geplanten Sortierungen entfernt.",
                                 fg=self._F["gelb"]))

    # ------------------------------------------
    #  STATUSBAR
    # ------------------------------------------
    def _baue_statusbar(self, parent):
        F = self._F
        bar = tk.Frame(parent, bg=F["bg"], pady=8)
        bar.pack(fill="x")
        self._reg(bar, "bg")
        self.status_unten = tk.Label(
            bar, text="GUI v5.0 – Drag & Drop  |  Dark/Light  |  Cronjob  |  Benachrichtigungen",
            font=FONT_KLEIN, bg=F["bg"], fg=F["gelb"])
        self.status_unten.pack(side="left")
        self._reg(self.status_unten, "bg")
        bash_ok = self.bash_pfad is not None
        tk.Label(bar, text=f"bash: {'✅' if bash_ok else '❌'}",
                 font=FONT_KLEIN, bg=F["bg"],
                 fg=F["gruen"] if bash_ok else F["rot"], padx=8).pack(side="right")
        tk.Label(bar, text="GUI v5.0",
                 font=FONT_KLEIN, bg=F["bg"], fg=F["text_dim"], padx=8).pack(side="right")

    # ------------------------------------------
    #  AKTIONEN
    # ------------------------------------------
    def _ordner_waehlen(self):
        if self.laeuft: return
        try:
            pfad = filedialog.askdirectory(
                title="Ordner wählen",
                initialdir=self.ordner_pfad.get() or str(Path.home()))
            if pfad:
                self._drop_empfangen(pfad)
        except tk.TclError: pass

    def _vorschau_laden(self):
        if not self.ordner_pfad.get():
            self._ordner_waehlen(); return
        if self.laeuft: return
        with self._vorschau_lock:
            if self._vorschau_laeuft: return
            self._vorschau_laeuft = True

        pfad = self.ordner_pfad.get()
        if not os.path.isdir(pfad):
            with self._vorschau_lock: self._vorschau_laeuft = False
            messagebox.showerror("Fehler", f"Ordner nicht gefunden:\n{pfad}"); return

        self.status_text.configure(text="🔍  Lade Vorschau...", fg=self._F["gelb"])
        self.vorschau_btn.configure(state="disabled")
        self._tabelle_leeren()

        def _t():
            zeilen, fehler = [], None
            try:
                for datei in sorted(os.listdir(pfad)):
                    if not os.path.isfile(os.path.join(pfad, datei)): continue
                    if datei.startswith("."): continue
                    kat, ziel = get_kategorie(datei)
                    zeilen.append((datei, kat, ziel))
            except PermissionError: fehler = "❌  Kein Zugriff."
            except Exception as e: fehler = f"❌  Fehler: {e}"
            finally:
                with self._vorschau_lock: self._vorschau_laeuft = False

            def _upd():
                if self._zerstoert: return
                try:
                    self._tabelle_leeren()
                    if fehler:
                        tk.Label(self.tabelle_frame, text=fehler, font=FONT,
                                 bg=self._F["tabelle_z1"], fg=self._F["rot"], pady=20).pack()
                        self.status_text.configure(text=fehler, fg=self._F["rot"])
                    elif not zeilen:
                        tk.Label(self.tabelle_frame, text="Keine Dateien.",
                                 font=FONT, bg=self._F["tabelle_z1"],
                                 fg=self._F["text_dim"], pady=20).pack()
                        self.status_text.configure(text="ℹ️  Keine Dateien.", fg=self._F["text_dim"])
                    else:
                        for i, (d, k, z) in enumerate(zeilen):
                            self._tabelle_zeile(d, k, z, i)
                        self.status_text.configure(
                            text=f"✅  {len(zeilen)} Datei(en) – Bereit.", fg=self._F["gruen"])
                    self.vorschau_btn.configure(state="normal")
                except tk.TclError: pass
            self._nach(_upd)
        threading.Thread(target=_t, daemon=True).start()

    def _sortieren_starten(self):
        if not self.ordner_pfad.get():
            self._ordner_waehlen(); return
        if self.laeuft: return
        if not self._vorbedingungen_pruefen(): return
        pfad = self.ordner_pfad.get()
        if not os.path.isdir(pfad):
            messagebox.showerror("Fehler", f"Ordner nicht gefunden:\n{pfad}"); return
        if not messagebox.askyesno("Sortieren starten",
                                    f"Dateien sortieren in:\n\n{pfad}"): return

        cmd_args = [pfad]
        if self.kopieren_var.get():    cmd_args.append("--kopieren")
        if self.unterordner_var.get(): cmd_args.append("--unterordner")
        if self.notify_var.get():      cmd_args.append("--notify")
        if self.bericht_var.get():     cmd_args.append("--bericht")

        self.laeuft = True
        self._buttons_sperren(True)
        self.status_text.configure(text="🚀  Sortierung läuft...", fg=self._F["gelb"])
        self._tab_wechseln("verlauf")
        kat_count = {}

        def _t():
            returncode = -1
            try:
                cmd = [self.bash_pfad, self.script_pfad] + cmd_args
                self.aktiver_proc = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, encoding="utf-8", errors="replace")

                self._nach(self._verlauf_schreiben, f"\n── Sortierung gestartet ──\n", "header")
                self._nach(self._verlauf_schreiben, f"  Ordner: {pfad}\n", "dim")

                for zeile in self.aktiver_proc.stdout:
                    if self._zerstoert: break
                    z = _ANSI_RE.sub("", zeile).strip()
                    if not z: continue
                    if "OK:" in z and "->" in z:
                        try:
                            kat = _ANSI_RE.sub("", z.split("->")[1]).strip().rstrip("/")
                            if kat:
                                kat_count[kat] = kat_count.get(kat, 0) + 1
                        except Exception: pass
                    tag = ("gruen" if any(w in z for w in ["OK:","Fertig","Wiederhergestellt"])
                           else "gelb" if any(w in z for w in ["Sonstiges","IGNORIERT","Tipp","Bericht"])
                           else "rot"  if any(w in z for w in ["Fehler","ERROR"])
                           else None)
                    self._nach(self._verlauf_schreiben, f"  {z}\n", tag)

                self.aktiver_proc.wait()
                returncode = self.aktiver_proc.returncode
            except FileNotFoundError:
                self._nach(self._verlauf_schreiben, "❌ Bash nicht gefunden.\n", "rot")
            except Exception as e:
                self._nach(self._verlauf_schreiben, f"❌ {e}\n", "rot")
            finally:
                self.aktiver_proc = None
                self.laeuft = False
                if not self._zerstoert:
                    if returncode == 0:
                        self._nach(lambda: self._ui(
                            self.status_text.configure, text="✅  Fertig!", fg=self._F["gruen"]))
                        self._nach(self._zeige_statistiken, kat_count)
                        self._nach(lambda: None if self.laeuft else self._vorschau_laden())
                    else:
                        self._nach(lambda: self._ui(
                            self.status_text.configure,
                            text="❌  Fehler oder abgebrochen.", fg=self._F["rot"]))
                    self._nach(self._buttons_sperren, False)

        threading.Thread(target=_t, daemon=True).start()

    def _abbrechen(self):
        if self.aktiver_proc and self.laeuft:
            try:
                self.aktiver_proc.terminate()
                self._verlauf_schreiben("\n⬛ Abgebrochen!\n", "gelb")
            except Exception: pass

    def _reset(self):
        if self.laeuft: return
        try:
            self.ordner_pfad.set("")
            self.drop_label.configure(
                text="📁  Ordner hier ablegen oder klicken", fg=self._F["text_dim"])
            self.drop_zone.configure(
                highlightbackground=self._F["drop_border"], bg=self._F["drop"])
            self.drop_label.configure(bg=self._F["drop"])
            self._tabelle_reset_leer()
            self.status_text.configure(
                text="Wähle einen Ordner aus, um zu beginnen.", fg=self._F["gruen"])
            self.kopieren_var.set(False)
            self.unterordner_var.set(False)
            self.notify_var.set(False)
            self.bericht_var.set(False)
        except tk.TclError: pass

    def _undo(self):
        if not self.ordner_pfad.get() or not os.path.isdir(self.ordner_pfad.get()):
            messagebox.showwarning("Kein Ordner", "Bitte zuerst Ordner auswählen."); return
        if self.laeuft: return
        if not self._vorbedingungen_pruefen(): return
        if messagebox.askyesno("Rückgängig", "Letzte Sortierung rückgängig machen?"):
            self._script_aktion([self.ordner_pfad.get(), "--undo"], "UNDO")

    def _zeige_log(self):
        if not self.ordner_pfad.get() or not os.path.isdir(self.ordner_pfad.get()):
            messagebox.showwarning("Kein Ordner", "Bitte zuerst Ordner auswählen."); return
        if self.laeuft: return
        if not self._vorbedingungen_pruefen(): return
        self._script_aktion([self.ordner_pfad.get(), "--log"], "LOG")

    def _script_aktion(self, args, label, callback=None):
        if self.laeuft: return
        self.laeuft = True
        self._buttons_sperren(True)
        self._nach(self._verlauf_schreiben, f"\n── {label} ──\n", "header")
        returncode = -1

        def _t():
            nonlocal returncode
            try:
                cmd = [self.bash_pfad, self.script_pfad] + args
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace")
                for zeile in proc.stdout:
                    z = _ANSI_RE.sub("", zeile).strip()
                    if z:
                        tag = ("gruen" if any(w in z for w in ["Wiederhergestellt","OK:","eingerichtet","entfernt"])
                               else "rot" if any(w in z for w in ["Fehler","ERROR"])
                               else None)
                        self._nach(self._verlauf_schreiben, f"  {z}\n", tag)
                proc.wait()
                returncode = proc.returncode
            except Exception as e:
                self._nach(self._verlauf_schreiben, f"❌ {e}\n", "rot")
            finally:
                self.laeuft = False
                if not self._zerstoert:
                    if returncode == 0:
                        self._nach(self._verlauf_schreiben,
                                   f"✅ {label} abgeschlossen.\n", "gruen")
                        if callback: self._nach(callback)
                    self._nach(self._buttons_sperren, False)

        threading.Thread(target=_t, daemon=True).start()

    def _vorbedingungen_pruefen(self):
        if not self.bash_pfad:
            messagebox.showerror("Bash nicht gefunden",
                "Git Bash nicht gefunden!\nhttps://git-scm.com/download/win"); return False
        if not os.path.exists(self.script_pfad):
            messagebox.showerror("Script nicht gefunden",
                f"datei_sortieren.sh fehlt!\n{self.script_pfad}"); return False
        return True

    def _beenden(self):
        if self.laeuft:
            if not messagebox.askyesno("Beenden", "Prozess läuft noch.\nTrotzdem beenden?"): return
            if self.aktiver_proc:
                try:
                    self.aktiver_proc.terminate()
                    self.aktiver_proc.wait(timeout=3)
                except Exception:
                    try: self.aktiver_proc.kill()
                    except Exception: pass
        self._zerstoert = True
        self.root.destroy()


# ============================================
#  START
# ============================================
if __name__ == "__main__":
    # tkinterdnd2 wenn vorhanden für echtes Drag & Drop
    try:
        import tkinterdnd2 as dnd  # type: ignore
        root = dnd.Tk()
    except ImportError:
        root = tk.Tk()

    try: root.iconbitmap("icon.ico")
    except Exception: pass

    app = DateiSortiererApp(root)
    root.mainloop()
