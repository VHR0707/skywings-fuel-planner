"""Sources de données des statistiques de consommation (API SkyWings, CSV hors-ligne, échantillon)."""

from __future__ import annotations

import csv
import json
import urllib.request
from pathlib import Path
from typing import Optional, Union

from .calc import STATS_KEYS, aggregate_fuel_rows

DEFAULT_BASE_URL = "https://www.skywings.ovh"
API_PATH = "/api/api_fuel_stats.php"


class SourceError(Exception):
    """Levée quand la source de données est indisponible ou illisible."""


def _empty_stats() -> dict:
    return {k: (0 if k == "nb_vols" else (0.0 if k.startswith("total") else None)) for k in STATS_KEYS}


def normalize_payload(payload: dict) -> dict:
    """Valide/normalise le JSON de l'API (ou d'un échantillon) vers le modèle interne."""
    if not isinstance(payload, dict) or "fleet_types" not in payload:
        raise SourceError("Payload invalide : clé 'fleet_types' manquante.")
    fleet_types = []
    for ft in payload["fleet_types"]:
        entry = {
            "id": int(ft["id"]),
            "label": str(ft.get("label") or f"Fleet #{ft['id']}"),
            "type": str(ft.get("type") or ""),
            "nb_appareils": int(ft.get("nb_appareils") or 0),
        }
        entry.update({k: ft.get(k) for k in STATS_KEYS})
        fleet_types.append(entry)
    g = payload.get("global") or {}
    glob = {k: g.get(k) for k in STATS_KEYS}
    if not glob.get("nb_vols"):
        glob = _empty_stats()
    return {
        "prix_litre": payload.get("prix_litre"),
        "units": payload.get("units") or {"fuel": "L", "distance": "NM"},
        "generated_at": payload.get("generated_at"),
        "fleet_types": fleet_types,
        "global": glob,
    }


class HttpSource:
    """Interroge l'endpoint api_fuel_stats.php du site SkyWings (HTTPS, lecture seule)."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def fetch(self) -> dict:
        url = self.base_url + API_PATH
        try:
            req = urllib.request.Request(
                url,
                headers={"Accept": "application/json",
                         "User-Agent": "skywings-fuel-planner/1.0"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            raise SourceError(f"Endpoint injoignable ({url}) : {e}") from e
        if isinstance(payload, dict) and "error" in payload:
            raise SourceError(f"L'API a renvoyé une erreur : {payload['error']}")
        return normalize_payload(payload)


class CsvSource:
    """Source hors-ligne : CSV brut de vols, agrégé localement (mêmes règles que l'API).

    Colonnes attendues : fleet_type_id,label,type,fuel_l,dist_nm,duree_s
    """

    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)

    def fetch(self) -> dict:
        if not self.path.exists():
            raise SourceError(f"Fichier CSV introuvable : {self.path}")
        rows = []
        fleet_meta: dict[int, dict] = {}
        with self.path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            required = {"fleet_type_id", "fuel_l", "dist_nm"}
            if not required.issubset(set(reader.fieldnames or [])):
                raise SourceError(
                    f"CSV invalide : colonnes requises {sorted(required)}, trouvées {reader.fieldnames}")
            for r in reader:
                fid = int(r["fleet_type_id"])
                rows.append({
                    "fleet_type_id": fid,
                    "fuel_l": r["fuel_l"],
                    "dist_nm": r["dist_nm"],
                    "duree_s": r.get("duree_s") or 0,
                })
                fleet_meta[fid] = {
                    "label": r.get("label") or f"Fleet #{fid}",
                    "type": r.get("type") or "",
                }
        stats = aggregate_fuel_rows(rows)
        fleet_types = []
        for fid in sorted(fleet_meta):
            entry = {"id": fid, "nb_appareils": 0, **fleet_meta[fid]}
            entry.update(stats.get(fid, _empty_stats()))
            fleet_types.append(entry)
        tot_fuel = sum(f["total_fuel_l"] for f in fleet_types)
        tot_nm = sum(f["total_nm"] for f in fleet_types)
        tot_h = sum(f["total_hours"] for f in fleet_types)
        glob = {
            "nb_vols": sum(f["nb_vols"] for f in fleet_types),
            "total_fuel_l": round(tot_fuel, 2),
            "total_nm": round(tot_nm, 1),
            "total_hours": round(tot_h, 2),
            "conso_l_per_nm": round(tot_fuel / tot_nm, 4) if tot_nm > 0 else None,
            "conso_l_per_h": round(tot_fuel / tot_h, 2) if tot_h > 0 else None,
        }
        return {
            "prix_litre": None,
            "units": {"fuel": "L", "distance": "NM"},
            "generated_at": None,
            "fleet_types": fleet_types,
            "global": glob,
        }


class SampleSource:
    """Données de démonstration embarquées (data/sample_fuel_stats.json), pour tester sans le site."""

    def __init__(self, path: Optional[Union[str, Path]] = None):
        if path is None:
            path = Path(__file__).resolve().parent.parent / "data" / "sample_fuel_stats.json"
        self.path = Path(path)

    def fetch(self) -> dict:
        if not self.path.exists():
            raise SourceError(f"Échantillon introuvable : {self.path}")
        return normalize_payload(json.loads(self.path.read_text(encoding="utf-8")))


def make_source(base_url: Optional[str] = None, csv_path: Optional[str] = None, demo: bool = False):
    """Fabrique la source demandée : démo > CSV > API HTTP du site."""
    if demo:
        return SampleSource()
    if csv_path:
        return CsvSource(csv_path)
    return HttpSource(base_url or DEFAULT_BASE_URL)
