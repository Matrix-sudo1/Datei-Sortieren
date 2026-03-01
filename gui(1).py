#!/usr/bin/env python3
# ============================================
#  Datei-Sortierer GUI v3.0
#  Modernes Design mit Tabs, Drop-Zone & Tabelle
# ============================================

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
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
    "tab_hover":  "#2a3050",
    "akzent":     "#6c3fc5",
    "akzent2":    "#2d6bbf",
    "start":      "#e8435a",
    "gruen":      "#2ecc71",
    "gelb":       "#f39c12",
    "rot":        "#e8435a",
    "text":       "#e8eaf6",
    "text_dim":   "#6b7280",
    "border":     "#2a3050",
    "border_akt": "#6c3fc5",
    "tabelle_hd": "#1e2d4a",
    "tabelle_z1": "#161b2e",
    "tabelle_z2": "#1a2035",
    "drop":       "#1a2240",
    "drop_border":"#5a3db5",
}

FONT        = ("Segoe UI", 11)
FONT_BOLD   = ("Segoe UI", 11, "bold")
FONT_TITEL  = ("Segoe UI", 20, "bold")
FONT_KLEIN  = ("Segoe UI", 9)
FONT_TAB    = ("Segoe UI", 12, "bold")
FONT_BTN    = ("Segoe UI", 13, "bold")


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

        # Zustand
        self.ordner_pfad   = tk.StringVar(value="")
        self.kopieren_var  = tk.BooleanVar(value=False)
        self.unterordner_var = tk.BooleanVar(value=False)
        self.laeuft        = False
        self.aktiver_proc  = None
        self._zerstoert    = False
        self.aktiver_tab   = tk.StringVar(value="sortieren")

        self.script_pfad   = self._finde_script()
        self.bash_pfad     = self._finde_bash()

        self._baue_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._beenden)

    def _finde_script(self):
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
    #  UI AUFBAUEN
    # ------------------------------------------
    def _baue_ui(self):
        # Äußerer Rahmen
        aussen = tk.Frame(self.root, bg=F["bg"], padx=20, pady=16)
        aussen.pack(fill="both", expand=True)

        # Titelleiste (oben)
        self._baue_titelleiste(aussen)

        # Haupt-Karte
        karte = tk.Frame(aussen, bg=F["card"],
                         highlightbackground=F["border"],
                         highlightthickness=1)
        karte.pack(fill="both", expand=True)

        # macOS-Buttons
        self._baue_macos_buttons(karte)

        # Titel
        titel_rahmen = tk.Frame(karte, bg=F["card"], pady=16)
        titel_rahmen.pack(fill="x", padx=24)
        tk.Label(titel_rahmen, text="📁", font=("Segoe UI Emoji", 28),
                 bg=F["card"], fg=F["gelb"]).pack(side="left")
        tk.Label(titel_rahmen, text=" Datei-Sortierer",
                 font=FONT_TITEL, bg=F["card"], fg=F["text"]).pack(side="left")
        tk.Label(titel_rahmen, text="  v2.0",
                 font=("Segoe UI", 13), bg=F["card"],
                 fg=F["text_dim"]).pack(side="left", pady=6)

        # Tab-Navigation
        self._baue_tabs(karte)

        # Tab-Inhalte
        self.tab_inhalt = tk.Frame(karte, bg=F["card"])
        self.tab_inhalt.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        self._baue_tab_sortieren()
        self._baue_tab_statistiken()
        self._baue_tab_verlauf()

        self._tab_wechseln("sortieren")

        # Statusleiste
        self._baue_statusbar(aussen)

    def _baue_titelleiste(self, parent):
        leiste = tk.Frame(parent, bg=F["bg"], pady=6)
        leiste.pack(fill="x")
        tk.Label(leiste, text="🖥  DATEI-SORTIERER V2.0 – GUI VORSCHAU",
                 font=("Segoe UI", 13, "bold"),
                 bg=F["bg"], fg=F["text"]).pack(side="left")

    def _baue_macos_buttons(self, parent):
        leiste = tk.Frame(parent, bg=F["card"], pady=10, padx=16)
        leiste.pack(fill="x")
        for farbe, aktion in [("#e8435a", self._beenden),
                               ("#f39c12", lambda: None),
                               ("#2ecc71", lambda: None)]:
            btn = tk.Button(leiste, text="", width=2,
                            bg=farbe, activebackground=farbe,
                            relief="flat", cursor="hand2",
                            command=aktion, bd=0)
            btn.pack(side="left", padx=3)
        tk.Label(leiste, text="📁 Datei-Sortierer v2.0",
                 font=FONT, bg=F["card"], fg=F["text_dim"]).pack(side="left", padx=12)

    def _baue_tabs(self, parent):
        self.tab_rahmen = tk.Frame(parent, bg=F["card"], padx=24)
        self.tab_rahmen.pack(fill="x", pady=(0, 4))

        self.tab_buttons = {}
        tabs = [("sortieren", "🗂  Sortieren"),
                ("statistiken", "📊  Statistiken"),
                ("verlauf", "🕐  Verlauf")]

        for key, label in tabs:
            btn = tk.Button(
                self.tab_rahmen, text=label,
                font=FONT_TAB,
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
        self.aktiver_tab.set(key)
        for k, btn in self.tab_buttons.items():
            if k == key:
                btn.configure(bg=F["tab_aktiv"], fg=F["text"])
            else:
                btn.configure(bg=F["nav"], fg=F["text_dim"])

        for frame in [self.frame_sortieren, self.frame_statistiken, self.frame_verlauf]:
            frame.pack_forget()

        if key == "sortieren":
            self.frame_sortieren.pack(fill="both", expand=True)
        elif key == "statistiken":
            self.frame_statistiken.pack(fill="both", expand=True)
        elif key == "verlauf":
            self.frame_verlauf.pack(fill="both", expand=True)

    # ------------------------------------------
    #  TAB: SORTIEREN
    # ------------------------------------------
    def _baue_tab_sortieren(self):
        self.frame_sortieren = tk.Frame(self.tab_inhalt, bg=F["card"])

        # Drop-Zone
        self.drop_zone = tk.Frame(
            self.frame_sortieren, bg=F["drop"],
            highlightbackground=F["drop_border"],
            highlightthickness=2,
            cursor="hand2"
        )
        self.drop_zone.pack(fill="x", pady=(8, 12))

        self.drop_label = tk.Label(
            self.drop_zone,
            text="📁  Ordner hierher ziehen — oder klicken zum Auswählen",
            font=("Segoe UI", 13), bg=F["drop"], fg=F["text_dim"],
            pady=28
        )
        self.drop_label.pack()

        self.drop_zone.bind("<Button-1>", lambda e: self._ordner_waehlen())
        self.drop_label.bind("<Button-1>", lambda e: self._ordner_waehlen())
        self.drop_zone.bind("<Enter>", lambda e: self.drop_zone.configure(
            highlightbackground=F["akzent"], bg=F["card2"]))
        self.drop_zone.bind("<Leave>", lambda e: self.drop_zone.configure(
            highlightbackground=F["drop_border"], bg=F["drop"]))

        # Optionen
        opt = tk.Frame(self.frame_sortieren, bg=F["card"])
        opt.pack(fill="x", pady=(0, 12))

        self._checkbox(opt, "📋  Kopieren (Original bleibt)", self.kopieren_var).pack(
            side="left", padx=(0, 30))
        self._checkbox(opt, "🔄  Unterordner einbeziehen", self.unterordner_var).pack(
            side="left")

        # Vorschau-Tabelle
        tk.Label(self.frame_sortieren, text="VORSCHAU",
                 font=("Segoe UI", 9, "bold"),
                 bg=F["card"], fg=F["text_dim"]).pack(anchor="w", pady=(0, 4))

        tabelle_rahmen = tk.Frame(self.frame_sortieren, bg=F["tabelle_hd"],
                                   highlightbackground=F["border"],
                                   highlightthickness=1)
        tabelle_rahmen.pack(fill="both", expand=True)

        # Header
        header = tk.Frame(tabelle_rahmen, bg=F["tabelle_hd"])
        header.pack(fill="x")
        for text, breite in [("Dateiname", 220), ("Kategorie", 160), ("Ziel-Ordner", 200)]:
            tk.Label(header, text=text, font=FONT_BOLD,
                     bg=F["tabelle_hd"], fg=F["text"],
                     width=breite//8, anchor="w",
                     padx=12, pady=10).pack(side="left")

        # Tabellen-Inhalt
        self.tabelle_frame = tk.Frame(tabelle_rahmen, bg=F["tabelle_z1"])
        self.tabelle_frame.pack(fill="both", expand=True)

        self.tabelle_leer = tk.Label(
            self.tabelle_frame,
            text="Klicke auf die Drop-Zone um eine Vorschau zu laden...",
            font=("Segoe UI", 11), bg=F["tabelle_z1"], fg=F["text_dim"],
            pady=30
        )
        self.tabelle_leer.pack()

        # Status
        self.status_text = tk.Label(
            self.frame_sortieren,
            text="Wähle einen Ordner aus, um zu beginnen.",
            font=FONT, bg=F["card"], fg=F["gruen"],
            pady=10, anchor="w"
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
            relief="flat", cursor="hand2", pady=14,
            command=self._reset
        )
        self.reset_btn.pack(side="left", fill="x", expand=False, padx=0)
        self.reset_btn.configure(width=10)

    def _checkbox(self, parent, text, variable):
        rahmen = tk.Frame(parent, bg=F["card"])
        cb = tk.Checkbutton(
            rahmen, text=text, variable=variable,
            font=FONT, bg=F["card"], fg=F["text"],
            selectcolor=F["akzent"],
            activebackground=F["card"],
            activeforeground=F["text"],
            cursor="hand2", relief="flat",
            padx=0
        )
        cb.pack(side="left")
        return rahmen

    # ------------------------------------------
    #  TAB: STATISTIKEN
    # ------------------------------------------
    def _baue_tab_statistiken(self):
        self.frame_statistiken = tk.Frame(self.tab_inhalt, bg=F["card"])

        tk.Label(self.frame_statistiken,
                 text="📊  Statistiken",
                 font=FONT_TITEL, bg=F["card"], fg=F["text"],
                 pady=20).pack()

        self.stats_frame = tk.Frame(self.frame_statistiken, bg=F["card"])
        self.stats_frame.pack(fill="both", expand=True)

        self.stats_leer = tk.Label(
            self.stats_frame,
            text="Noch keine Sortierung durchgeführt.\nStarte eine Sortierung um Statistiken zu sehen.",
            font=FONT, bg=F["card"], fg=F["text_dim"],
            pady=40
        )
        self.stats_leer.pack()

    def _zeige_statistiken(self, kategorien_count):
        """Zeigt Statistiken nach einer Sortierung."""
        for w in self.stats_frame.winfo_children():
            w.destroy()

        tk.Label(self.stats_frame, text="Letzte Sortierung:",
                 font=FONT_BOLD, bg=F["card"], fg=F["text"],
                 pady=10).pack(anchor="w")

        gesamt = sum(kategorien_count.values())
        tk.Label(self.stats_frame, text=f"Gesamt sortiert: {gesamt} Datei(en)",
                 font=FONT, bg=F["card"], fg=F["gruen"]).pack(anchor="w", pady=(0, 8))

        for kat, anzahl in sorted(kategorien_count.items(),
                                   key=lambda x: x[1], reverse=True):
            zeile = tk.Frame(self.stats_frame, bg=F["card2"],
                             highlightbackground=F["border"],
                             highlightthickness=1)
            zeile.pack(fill="x", pady=2)

            tk.Label(zeile, text=f"  {kat}", font=FONT,
                     bg=F["card2"], fg=F["text"],
                     width=20, anchor="w", pady=8).pack(side="left")

            # Balken
            max_breite = 300
            breite = max(20, int(anzahl / gesamt * max_breite)) if gesamt > 0 else 20
            tk.Frame(zeile, bg=F["akzent"], width=breite, height=18).pack(
                side="left", padx=8, pady=8)

            tk.Label(zeile, text=f"{anzahl}x", font=FONT_BOLD,
                     bg=F["card2"], fg=F["akzent"]).pack(side="left")

    # ------------------------------------------
    #  TAB: VERLAUF
    # ------------------------------------------
    def _baue_tab_verlauf(self):
        self.frame_verlauf = tk.Frame(self.tab_inhalt, bg=F["card"])

        header = tk.Frame(self.frame_verlauf, bg=F["card"])
        header.pack(fill="x", pady=(10, 8))

        tk.Label(header, text="🕐  Verlauf",
                 font=FONT_TITEL, bg=F["card"], fg=F["text"]).pack(side="left")

        undo_btn = tk.Button(header, text="↩ Rückgängig",
                             font=FONT_BOLD, bg=F["akzent"], fg=F["text"],
                             activebackground="#4a2a9a",
                             activeforeground=F["text"],
                             relief="flat", cursor="hand2",
                             padx=16, pady=8,
                             command=self._undo)
        undo_btn.pack(side="right")

        self.verlauf_text = tk.Text(
            self.frame_verlauf,
            font=("Courier New", 10),
            bg=F["card2"], fg=F["text"],
            relief="flat", bd=8,
            state="disabled", wrap="word",
            cursor="arrow",
            highlightbackground=F["border"],
            highlightthickness=1
        )
        self.verlauf_text.pack(fill="both", expand=True)

        self.verlauf_text.tag_config("gruen",   foreground=F["gruen"])
        self.verlauf_text.tag_config("gelb",    foreground=F["gelb"])
        self.verlauf_text.tag_config("rot",     foreground=F["rot"])
        self.verlauf_text.tag_config("dim",     foreground=F["text_dim"])
        self.verlauf_text.tag_config("header",  foreground=F["akzent"],
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

    # ------------------------------------------
    #  STATUSBAR
    # ------------------------------------------
    def _baue_statusbar(self, parent):
        bar = tk.Frame(parent, bg=F["bg"], pady=8)
        bar.pack(fill="x")
        self.status_unten = tk.Label(
            bar,
            text="👆  Klicke auf die Tabs um zwischen den Ansichten zu wechseln"
                 " — und auf die Drop-Zone um die Demo zu starten",
            font=FONT_KLEIN, bg=F["bg"], fg=F["gelb"],
            wraplength=800, justify="left"
        )
        self.status_unten.pack(side="left")

    # ------------------------------------------
    #  AKTIONEN
    # ------------------------------------------
    def _ordner_waehlen(self):
        pfad = filedialog.askdirectory(
            title="Ordner wählen",
            initialdir=self.ordner_pfad.get() or str(Path.home())
        )
        if pfad:
            self.ordner_pfad.set(pfad)
            self.drop_label.configure(
                text=f"📁  {pfad}",
                fg=F["text"]
            )
            self.drop_zone.configure(highlightbackground=F["gruen"])
            self.status_text.configure(
                text=f"✅  Ordner ausgewählt. Klicke 'Vorschau laden' oder 'Sortieren starten'.",
                fg=F["gruen"]
            )

    def _tabelle_leeren(self):
        for w in self.tabelle_frame.winfo_children():
            w.destroy()

    def _tabelle_zeile(self, dateiname, kategorie, ziel, zeile_nr):
        bg = F["tabelle_z1"] if zeile_nr % 2 == 0 else F["tabelle_z2"]
        zeile = tk.Frame(self.tabelle_frame, bg=bg)
        zeile.pack(fill="x")
        for text, breite in [(dateiname, 220), (kategorie, 160), (ziel, 200)]:
            tk.Label(zeile, text=text, font=FONT,
                     bg=bg, fg=F["text"],
                     width=breite//8, anchor="w",
                     padx=12, pady=7).pack(side="left")

    def _vorschau_laden(self):
        if not self.ordner_pfad.get():
            self._ordner_waehlen()
            return
        if not self._vorbedingungen_pruefen():
            return

        self._tabelle_leeren()
        self.status_text.configure(text="🔍  Lade Vorschau...", fg=F["gelb"])

        kategorien = {
            "Bilder": ["jpg","jpeg","png","gif","bmp","svg","webp","tiff"],
            "Videos": ["mp4","mkv","avi","mov","wmv","flv","webm"],
            "Audio": ["mp3","wav","flac","aac","ogg","wma","m4a"],
            "Dokumente": ["pdf","doc","docx","odt","txt","rtf","md"],
            "Tabellen": ["xls","xlsx","csv","ods"],
            "Praesentation": ["ppt","pptx","odp"],
            "Archive": ["zip","tar","gz","bz2","rar","7z"],
            "Code": ["sh","py","js","ts","html","css","php","java","c","cpp"],
            "Ausfuehrbar": ["exe","dmg","deb","rpm"],
        }

        def _get_kategorie(dateiname):
            ext = dateiname.rsplit(".", 1)[-1].lower() if "." in dateiname else ""
            for kat, exts in kategorien.items():
                if ext in exts:
                    return kat, kat + "/"
            return "Sonstiges", "Sonstiges/"

        zeile_nr = 0
        gefunden = False
        try:
            for datei in os.listdir(self.ordner_pfad.get()):
                voller_pfad = os.path.join(self.ordner_pfad.get(), datei)
                if not os.path.isfile(voller_pfad):
                    continue
                if datei.startswith("."):
                    continue
                kat, ziel = _get_kategorie(datei)
                self._tabelle_zeile(datei, kat, ziel, zeile_nr)
                zeile_nr += 1
                gefunden = True

            if not gefunden:
                tk.Label(self.tabelle_frame,
                         text="Keine Dateien im Ordner gefunden.",
                         font=FONT, bg=F["tabelle_z1"], fg=F["text_dim"],
                         pady=20).pack()
                self.status_text.configure(
                    text="ℹ️  Keine Dateien gefunden.", fg=F["text_dim"])
            else:
                self.status_text.configure(
                    text=f"✅  {zeile_nr} Datei(en) gefunden. Bereit zum Sortieren.",
                    fg=F["gruen"])
        except PermissionError:
            self.status_text.configure(
                text="❌  Kein Zugriff auf diesen Ordner.", fg=F["rot"])

    def _sortieren_starten(self):
        if not self.ordner_pfad.get():
            self._ordner_waehlen()
            return
        if self.laeuft:
            return
        if not self._vorbedingungen_pruefen():
            return

        if not messagebox.askyesno("Sortieren starten",
                                    f"Dateien in folgendem Ordner sortieren?\n\n"
                                    f"{self.ordner_pfad.get()}"):
            return

        self.laeuft = True
        self.start_btn.configure(state="disabled", text="⏳  Läuft...")
        self.vorschau_btn.configure(state="disabled")
        self.status_text.configure(text="🚀  Sortierung läuft...", fg=F["gelb"])

        kategorien_count = {}

        def _thread():
            try:
                args = [self.ordner_pfad.get()]
                cmd = [self.bash_pfad, self.script_pfad] + args
                self.aktiver_proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace"
                )

                self.root.after(0, self._verlauf_schreiben,
                                f"\n── Sortierung gestartet ──\n", "header")
                self.root.after(0, self._verlauf_schreiben,
                                f"Ordner: {self.ordner_pfad.get()}\n", "dim")

                for zeile in self.aktiver_proc.stdout:
                    if self._zerstoert:
                        break
                    zeile_clean = zeile.strip()
                    if not zeile_clean:
                        continue

                    # Kategorie zählen für Statistiken
                    if "OK:" in zeile_clean and "->" in zeile_clean:
                        try:
                            kat = zeile_clean.split("->")[1].strip().rstrip("/")
                            kategorien_count[kat] = kategorien_count.get(kat, 0) + 1
                        except Exception:
                            pass

                    tag = "gruen" if "OK:" in zeile_clean or "Fertig" in zeile_clean \
                        else "gelb" if "Sonstiges" in zeile_clean \
                        else "rot" if "Fehler" in zeile_clean \
                        else None

                    self.root.after(0, self._verlauf_schreiben,
                                    f"  {zeile_clean}\n", tag)

                self.aktiver_proc.wait()
                returncode = self.aktiver_proc.returncode

            except Exception as e:
                returncode = -1
                self.root.after(0, self._verlauf_schreiben,
                                f"❌ Fehler: {e}\n", "rot")
            finally:
                self.aktiver_proc = None
                self.laeuft = False
                if not self._zerstoert:
                    if returncode == 0:
                        self.root.after(0, self.status_text.configure,
                                        {"text": "✅  Sortierung abgeschlossen!", "fg": F["gruen"]})
                        self.root.after(0, self._zeige_statistiken, kategorien_count)
                        self.root.after(0, self._vorschau_laden)
                    else:
                        self.root.after(0, self.status_text.configure,
                                        {"text": "❌  Fehler aufgetreten.", "fg": F["rot"]})
                    self.root.after(0, self.start_btn.configure,
                                    {"state": "normal", "text": "🚀  Sortieren starten"})
                    self.root.after(0, self.vorschau_btn.configure, {"state": "normal"})

        threading.Thread(target=_thread, daemon=True).start()

    def _reset(self):
        self.ordner_pfad.set("")
        self.drop_label.configure(
            text="📁  Ordner hierher ziehen — oder klicken zum Auswählen",
            fg=F["text_dim"]
        )
        self.drop_zone.configure(highlightbackground=F["drop_border"])
        self._tabelle_leeren()
        self.tabelle_leer = tk.Label(
            self.tabelle_frame,
            text="Klicke auf die Drop-Zone um eine Vorschau zu laden...",
            font=FONT, bg=F["tabelle_z1"], fg=F["text_dim"],
            pady=30
        )
        self.tabelle_leer.pack()
        self.status_text.configure(
            text="Wähle einen Ordner aus, um zu beginnen.", fg=F["gruen"])
        self.kopieren_var.set(False)
        self.unterordner_var.set(False)

    def _undo(self):
        if not self._vorbedingungen_pruefen():
            return
        if messagebox.askyesno("Rückgängig", "Letzte Sortierung rückgängig machen?"):
            self._script_schnell([self.ordner_pfad.get(), "--undo"])

    def _script_schnell(self, args):
        """Führt Script aus ohne UI-Sperre (für schnelle Aktionen)."""
        def _thread():
            try:
                cmd = [self.bash_pfad, self.script_pfad] + args
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace"
                )
                for zeile in proc.stdout:
                    z = zeile.strip()
                    if z:
                        self.root.after(0, self._verlauf_schreiben, f"  {z}\n")
                proc.wait()
            except Exception as e:
                self.root.after(0, self._verlauf_schreiben, f"❌ {e}\n", "rot")
        threading.Thread(target=_thread, daemon=True).start()

    def _vorbedingungen_pruefen(self):
        if not self.bash_pfad:
            messagebox.showerror("Bash nicht gefunden",
                                  "Git Bash wurde nicht gefunden!\n\n"
                                  "Bitte installiere Git Bash:\n"
                                  "https://git-scm.com/download/win")
            return False
        if not os.path.exists(self.script_pfad):
            messagebox.showerror("Script nicht gefunden",
                                  f"datei_sortieren.sh nicht gefunden!\n\n"
                                  f"Pfad: {self.script_pfad}\n\n"
                                  f"Lege datei_sortieren.sh in denselben Ordner wie gui.py.")
            return False
        return True

    def _beenden(self):
        if self.laeuft:
            if not messagebox.askyesno("Beenden", "Prozess läuft noch. Trotzdem beenden?"):
                return
            if self.aktiver_proc:
                try:
                    self.aktiver_proc.terminate()
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
