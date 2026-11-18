"""Version web locale du planificateur carburant.

`python -m fuelplanner.web` lance un petit serveur HTTP sur 127.0.0.1 (rien n'est hébergé
sur le site SkyWings) : la page appelle des routes locales, et le serveur fait proxy vers
l'endpoint public api_fuel_stats.php (ou lit un CSV / la démo en mode hors-ligne).

Routes :
  GET /                 -> page (web_static/index.html)
  GET /assets/logo.png  -> logo SkyWings
  GET /api/units        -> liste des unités d'affichage
  GET /api/fuel_stats   -> stats conso (proxy mis en cache 5 min)
  GET /api/compute?fleet=<label>&nm=<float>&reserve_min=<float>&unit=<L|kg|gal_us|gal_imp>&density=<float>
                        -> résultat du calcul en JSON
"""

from __future__ import annotations

import argparse
import json
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .calc import fuel_needed
from .cli import find_fleet
from .sources import DEFAULT_BASE_URL, SourceError, make_source
from .units import (DEFAULT_DENSITY_KG_PER_L, DEFAULT_UNIT, UNITS, convert_result,
                    unit_suffix)

STATIC_DIR = Path(__file__).resolve().parent / "web_static"
LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "logo.png"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
CACHE_TTL_S = 300


class _State:
    """Partagé entre les requêtes : source de données + cache des stats."""

    def __init__(self, source_kwargs: dict):
        self.source_kwargs = source_kwargs
        self._lock = threading.Lock()
        self._cache_ts = 0.0
        self._cache_data: dict | None = None

    def fuel_stats(self) -> dict:
        with self._lock:
            if self._cache_data is not None and time.time() - self._cache_ts < CACHE_TTL_S:
                return self._cache_data
            data = make_source(**self.source_kwargs).fetch()
            self._cache_data = data
            self._cache_ts = time.time()
            return data

    def invalidate(self) -> None:
        with self._lock:
            self._cache_data = None
            self._cache_ts = 0.0


def make_handler(state: _State):
    class Handler(BaseHTTPRequestHandler):
        server_version = "SkyWingsFuelPlanner/1.0"

        def log_message(self, *args):  # silencieux
            pass

        # ---------- helpers ----------
        def _send_json(self, obj, code=200):
            body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_file(self, path: Path, content_type: str, code=200):
            body = path.read_bytes()
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _error(self, code: int, message: str):
            self._send_json({"error": message}, code=code)

        # ---------- routes ----------
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            qs = urllib.parse.parse_qs(parsed.query)

            if path == "/":
                self._send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            elif path == "/assets/logo.png" and LOGO_PATH.exists():
                self._send_file(LOGO_PATH, "image/png")
            elif path == "/api/units":
                self._send_json({
                    "units": [{"code": c, "label": u["label"], "suffix": u["suffix"]}
                              for c, u in sorted(UNITS.items())],
                    "default_unit": DEFAULT_UNIT,
                    "default_density_kg_per_l": DEFAULT_DENSITY_KG_PER_L,
                })
            elif path == "/api/fuel_stats":
                try:
                    self._send_json(state.fuel_stats())
                except SourceError as e:
                    self._error(502, str(e))
            elif path == "/api/fuel_stats/refresh":
                state.invalidate()
                try:
                    self._send_json(state.fuel_stats())
                except SourceError as e:
                    self._error(502, str(e))
            elif path == "/api/compute":
                self._handle_compute(qs)
            else:
                self._error(404, f"Route inconnue : {path}")

        def _handle_compute(self, qs):
            def _get(name, default=None):
                v = qs.get(name)
                return v[0] if v else default

            fleet = _get("fleet", "")
            try:
                nm = float(str(_get("nm", "")).replace(",", "."))
            except ValueError:
                self._error(400, "Paramètre 'nm' invalide (nombre de NM attendu).")
                return
            try:
                reserve_min = float(_get("reserve_min", "30"))
            except ValueError:
                reserve_min = 30.0
            unit = _get("unit", DEFAULT_UNIT)
            if unit not in UNITS:
                self._error(400, f"Unité inconnue : {unit!r} (attendu : {sorted(UNITS)})")
                return
            try:
                density = float(str(_get("density", DEFAULT_DENSITY_KG_PER_L)).replace(",", "."))
            except ValueError:
                density = DEFAULT_DENSITY_KG_PER_L

            try:
                stats = state.fuel_stats()
            except SourceError as e:
                self._error(502, str(e))
                return

            ft = find_fleet(stats, fleet)
            if ft is None:
                self._error(404, f"fleet_type inconnu : {fleet!r}")
                return

            conso_nm, conso_h, used_global = ft["conso_l_per_nm"], ft["conso_l_per_h"], False
            if conso_nm is None or conso_nm <= 0:
                g = stats["global"]
                if not g.get("conso_l_per_nm"):
                    self._error(422, "Aucune conso disponible (ni fleet_type ni global).")
                    return
                conso_nm, conso_h, used_global = g["conso_l_per_nm"], g["conso_l_per_h"], True

            try:
                res = fuel_needed(nm, conso_nm, conso_h, reserve_min=reserve_min)
                res = convert_result(res, unit=unit, density=density)
            except ValueError as e:
                self._error(400, str(e))
                return

            res["fleet_type"] = ft["label"]
            res["fleet_type_id"] = ft["id"]
            res["nb_vols_reference"] = stats["global"]["nb_vols"] if used_global else ft["nb_vols"]
            res["source_fallback_global"] = used_global
            res["unit_suffix"] = unit_suffix(unit)
            if stats.get("prix_litre"):
                res["prix_litre"] = stats["prix_litre"]
                res["cout_estime"] = round(res["total_l"] * stats["prix_litre"], 2)
            self._send_json(res)

    return Handler


def build_server(host: str, port: int, source_kwargs: dict) -> ThreadingHTTPServer:
    state = _State(source_kwargs)
    return ThreadingHTTPServer((host, port), make_handler(state))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="fuelplanner.web",
        description="Lance la version web locale du planificateur carburant "
                    "(http://127.0.0.1:8765 par défaut — rien n'est hébergé sur le site).")
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--base-url", default=DEFAULT_BASE_URL, help="URL du site SkyWings")
    p.add_argument("--csv", help="CSV brut de vols (mode hors-ligne)")
    p.add_argument("--demo", action="store_true", help="Données de démonstration embarquées")
    p.add_argument("--no-browser", action="store_true", help="Ne pas ouvrir le navigateur")
    args = p.parse_args(argv)

    source_kwargs = {"base_url": args.base_url, "csv_path": args.csv, "demo": args.demo}
    server = build_server(args.host, args.port, source_kwargs)
    url = f"http://{args.host}:{args.port}/"
    print(f"SkyWings Fuel Planner (web local) : {url}")
    print("Source :", "démo embarquée" if args.demo else (args.csv or args.base_url))
    print("Ctrl+C pour arrêter.")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
