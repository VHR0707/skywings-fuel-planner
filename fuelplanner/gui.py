"""IHM tkinter du planificateur carburant SkyWings (couleurs + logo de la compagnie)."""

from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from .calc import fuel_needed
from .cli import find_fleet
from .sources import DEFAULT_BASE_URL, SourceError, make_source

# Palette SkyWings (simweb/css) + logo de la compagnie
COLOR_BG = "#f7fbff"
COLOR_PRIMARY = "#004080"
COLOR_DARK = "#1a3552"
COLOR_ACCENT = "#478ED4"
COLOR_WARN = "#d60000"
COLOR_OK = "#28a745"

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
LOGO_PATH = ASSETS_DIR / "logo.png"

DEFAULT_RESERVE_MIN = 30.0


def parse_nm(text: str) -> float:
    """Accepte '120' comme '120,5' (séparateur décimal FR)."""
    return float(str(text).strip().replace(",", "."))


class FuelPlannerApp:
    def __init__(self, root: tk.Tk, source_kwargs: dict):
        self.root = root
        self.source_kwargs = source_kwargs
        self.stats: dict | None = None
        self._queue: queue.Queue = queue.Queue()
        self._loading = False

        root.title("SkyWings — Planificateur carburant")
        root.geometry("620x660")
        root.minsize(560, 620)
        root.configure(bg=COLOR_BG)

        self._build_header()
        self._build_form()
        self._build_result()
        self._build_statusbar()

        self._load_stats_async()

    # ---------- construction IHM ----------

    def _build_header(self) -> None:
        header = tk.Frame(self.root, bg=COLOR_PRIMARY, height=86)
        header.pack(fill="x")
        header.pack_propagate(False)

        if LOGO_PATH.exists():
            try:
                img = tk.PhotoImage(file=str(LOGO_PATH))
                factor = max(1, img.width() // 64)
                self._logo = img.subsample(factor, factor)  # garder une référence
                tk.Label(header, image=self._logo, bg=COLOR_PRIMARY, bd=0).pack(side="left", padx=14, pady=10)
            except tk.TclError:
                self._logo = None

        titles = tk.Frame(header, bg=COLOR_PRIMARY)
        titles.pack(side="left", fill="x", expand=True, padx=6)
        tk.Label(titles, text="SkyWings", bg=COLOR_PRIMARY, fg="white",
                 font=("Helvetica", 20, "bold")).pack(anchor="w")
        tk.Label(titles, text="Planificateur carburant — conso moyenne issue de l'historique des vols",
                 bg=COLOR_PRIMARY, fg="#b3c6e0", font=("Helvetica", 10)).pack(anchor="w")

    def _build_form(self) -> None:
        form = tk.LabelFrame(self.root, text="Vol à planifier", bg=COLOR_BG, fg=COLOR_DARK,
                             font=("Helvetica", 11, "bold"), padx=12, pady=10)
        form.pack(fill="x", padx=14, pady=(12, 6))

        tk.Label(form, text="Fleet type :", bg=COLOR_BG, fg=COLOR_DARK,
                 font=("Helvetica", 10)).grid(row=0, column=0, sticky="w", pady=4)
        self.fleet_var = tk.StringVar()
        self.fleet_combo = ttk.Combobox(form, textvariable=self.fleet_var, state="readonly",
                                        width=38, font=("Helvetica", 10))
        self.fleet_combo.grid(row=0, column=1, sticky="ew", pady=4, padx=(8, 0))

        tk.Label(form, text="Distance (NM) :", bg=COLOR_BG, fg=COLOR_DARK,
                 font=("Helvetica", 10)).grid(row=1, column=0, sticky="w", pady=4)
        self.nm_var = tk.StringVar()
        tk.Entry(form, textvariable=self.nm_var, width=12, font=("Helvetica", 10),
                 highlightbackground=COLOR_ACCENT).grid(row=1, column=1, sticky="w", pady=4, padx=(8, 0))

        tk.Label(form, text="Réserve (min de vol) :", bg=COLOR_BG, fg=COLOR_DARK,
                 font=("Helvetica", 10)).grid(row=2, column=0, sticky="w", pady=4)
        self.reserve_var = tk.StringVar(value=str(int(DEFAULT_RESERVE_MIN)))
        tk.Spinbox(form, from_=0, to=180, increment=5, textvariable=self.reserve_var,
                   width=6, font=("Helvetica", 10)).grid(row=2, column=1, sticky="w", pady=4, padx=(8, 0))

        form.columnconfigure(1, weight=1)

        buttons = tk.Frame(self.root, bg=COLOR_BG)
        buttons.pack(fill="x", padx=14, pady=6)
        self.calc_btn = tk.Button(buttons, text="Calculer le carburant", command=self.on_calculate,
                                  bg=COLOR_PRIMARY, fg="white", activebackground=COLOR_DARK,
                                  font=("Helvetica", 11, "bold"), padx=18, pady=6, bd=0, cursor="hand2")
        self.calc_btn.pack(side="left")
        self.refresh_btn = tk.Button(buttons, text="Rafraîchir les stats", command=self._load_stats_async,
                                     bg=COLOR_ACCENT, fg="white", activebackground=COLOR_PRIMARY,
                                     font=("Helvetica", 10), padx=14, pady=6, bd=0, cursor="hand2")
        self.refresh_btn.pack(side="left", padx=10)

    def _build_result(self) -> None:
        box = tk.LabelFrame(self.root, text="Résultat", bg=COLOR_BG, fg=COLOR_DARK,
                            font=("Helvetica", 11, "bold"), padx=12, pady=10)
        box.pack(fill="both", expand=True, padx=14, pady=(6, 10))
        self.result = tk.Text(box, height=12, wrap="word", bg="white", fg=COLOR_DARK,
                              font=("Consolas", 10), relief="flat", padx=10, pady=8)
        self.result.pack(fill="both", expand=True)
        self.result.tag_config("total", foreground=COLOR_PRIMARY, font=("Consolas", 12, "bold"))
        self.result.tag_config("warn", foreground=COLOR_WARN, font=("Consolas", 10, "bold"))
        self.result.tag_config("ok", foreground=COLOR_OK)
        self.result.configure(state="disabled")

    def _build_statusbar(self) -> None:
        self.status_var = tk.StringVar(value="Chargement des statistiques…")
        bar = tk.Label(self.root, textvariable=self.status_var, bg=COLOR_DARK, fg="#b3c6e0",
                       font=("Helvetica", 9), anchor="w", padx=10, pady=4)
        bar.pack(fill="x", side="bottom")

    # ---------- chargement des stats (thread d'arrière-plan) ----------

    def _load_stats_async(self) -> None:
        if self._loading:
            return
        self._loading = True
        self._set_status("Chargement des statistiques de consommation…")
        self.refresh_btn.configure(state="disabled")

        def work():
            try:
                self._queue.put(("ok", make_source(**self.source_kwargs).fetch()))
            except SourceError as e:
                self._queue.put(("err", str(e)))
            except Exception as e:  # inattendu
                self._queue.put(("err", f"Erreur inattendue : {e}"))

        threading.Thread(target=work, daemon=True).start()
        self.root.after(100, self._poll_queue)

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, val = self._queue.get_nowait()
                if kind == "ok":
                    self._on_stats_loaded(val)
                else:
                    self._set_status(f"Erreur : {val} — lance avec --csv <fichier> ou --demo pour tester hors-ligne.")
        except queue.Empty:
            pass
        if self._loading:
            self.root.after(100, self._poll_queue)
        else:
            self.refresh_btn.configure(state="normal")

    def _on_stats_loaded(self, stats: dict) -> None:
        self._loading = False
        self.stats = stats
        labels = [f"{ft['label']}  ({ft['type']})" if ft["type"] else ft["label"]
                  for ft in stats["fleet_types"]]
        self._fleet_by_label = dict(zip(labels, stats["fleet_types"]))
        self.fleet_combo.configure(values=labels)
        if labels:
            self.fleet_combo.current(0)
        gen = stats.get("generated_at") or "n/a"
        src = self.source_kwargs.get("csv_path") or ("démo" if self.source_kwargs.get("demo")
                                                      else self.source_kwargs.get("base_url", DEFAULT_BASE_URL))
        self._set_status(f"Stats chargées ({len(labels)} fleet types, générées le {gen}) — source : {src}")

    # ---------- calcul ----------

    def on_calculate(self) -> None:
        if not self.stats:
            self._set_status("Statistiques non chargées — réessaie 'Rafraîchir les stats'.")
            return
        label = self.fleet_var.get()
        ft = self._fleet_by_label.get(label)
        if ft is None:
            self._set_status("Sélectionne un fleet type dans la liste.")
            return
        try:
            nm = parse_nm(self.nm_var.get())
        except ValueError:
            self._set_status("Distance invalide : saisis un nombre de NM (ex. 120 ou 120,5).")
            return
        try:
            reserve_min = float(self.reserve_var.get())
        except ValueError:
            reserve_min = DEFAULT_RESERVE_MIN

        conso_nm, conso_h, used_global = ft["conso_l_per_nm"], ft["conso_l_per_h"], False
        if conso_nm is None or conso_nm <= 0:
            g = self.stats["global"]
            if not g.get("conso_l_per_nm"):
                self._write_result([("Pas de données de consommation pour ce fleet_type\n"
                                     "et aucune conso globale disponible.", "warn")])
                return
            conso_nm, conso_h, used_global = g["conso_l_per_nm"], g["conso_l_per_h"], True

        try:
            res = fuel_needed(nm, conso_nm, conso_h, reserve_min=reserve_min)
        except ValueError as e:
            self._set_status(str(e))
            return

        nb_vols = self.stats["global"]["nb_vols"] if used_global else ft["nb_vols"]
        lines = []
        if used_global:
            lines.append(("Repli sur la conso globale (pas de vols pour ce fleet_type).\n", "warn"))
        lines += [
            (f"Fleet type         : {ft['label']}  ({nb_vols} vols de référence)\n", None),
            (f"Distance           : {res['distance_nm']:.1f} NM\n", None),
            (f"Conso de référence : {res['conso_l_per_nm']:.4f} L/NM", None),
        ]
        if res["conso_l_per_h"]:
            lines.append((f"  ({res['conso_l_per_h']:.2f} L/h)\n", None))
        else:
            lines.append(("\n", None))
        lines += [
            (f"Carburant trajet   : {res['trip_l']:.1f} L\n", None),
            (f"Réserve {res['reserve_min']:.0f} min    : {res['reserve_l']:.1f} L\n", None),
            (f"TOTAL À EMBARQUER  : {res['total_l']:.1f} L  (arrondi haut : {res['total_l_ceil']} L)\n", "total"),
        ]
        if self.stats.get("prix_litre"):
            lines.append((f"Coût estimé        : {res['total_l'] * self.stats['prix_litre']:.2f} € "
                          f"({self.stats['prix_litre']} €/L)\n", "ok"))
        self._write_result(lines)
        self._set_status("Calcul effectué.")

    # ---------- divers ----------

    def _write_result(self, lines) -> None:
        self.result.configure(state="normal")
        self.result.delete("1.0", "end")
        for text, tag in lines:
            self.result.insert("end", text, tag)
        self.result.configure(state="disabled")

    def _set_status(self, msg: str) -> None:
        self.status_var.set(msg)


def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser(prog="skywings-fuel-planner",
                                description="IHM SkyWings de calcul du carburant à embarquer.")
    p.add_argument("--base-url", default=DEFAULT_BASE_URL, help="URL du site SkyWings")
    p.add_argument("--csv", help="CSV brut de vols (mode hors-ligne)")
    p.add_argument("--demo", action="store_true", help="Données de démonstration embarquées")
    args = p.parse_args(argv)

    source_kwargs = {"base_url": args.base_url, "csv_path": args.csv, "demo": args.demo}
    root = tk.Tk()
    FuelPlannerApp(root, source_kwargs)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
