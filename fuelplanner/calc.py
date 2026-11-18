"""Calculs purs (sans I/O) : haversine, agrégation des consommations, besoin carburant."""

from __future__ import annotations

import math
from typing import Iterable, Optional

# Même rayon terrestre que ComputeFlightDistance() côté simweb (includes/fonctions_importer_vol.php)
EARTH_RADIUS_NM = 3440.065

# Clés de stats normalisées échangées entre la source de données et l'IHM/CLI
STATS_KEYS = ("nb_vols", "total_fuel_l", "total_nm", "total_hours", "conso_l_per_nm", "conso_l_per_h")


def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance en miles nautiques entre deux points (formule de Haversine)."""
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2)
    a = min(1.0, max(0.0, a))
    return 2 * EARTH_RADIUS_NM * math.asin(math.sqrt(a))


def _quartiles(sorted_vals: list[float]) -> tuple[float, float]:
    """Quartiles Q1/Q3 (méthode des médianes de Tukey), même algo que le PHP."""
    n = len(sorted_vals)
    if n == 0:
        return 0.0, 0.0
    s = sorted(sorted_vals)

    def _median(a: list[float]) -> float:
        m = len(a)
        if m == 0:
            return 0.0
        mid = m // 2
        return a[mid] if m % 2 == 1 else (a[mid - 1] + a[mid]) / 2.0

    mid = n // 2
    lower = s[:mid]
    upper = s[mid + 1:] if n % 2 == 1 else s[mid:]
    return _median(lower), _median(upper)


def aggregate_fuel_rows(rows: Iterable[dict]) -> dict[int, dict]:
    """Agrège des lignes de vols en stats de conso par fleet_type.

    rows : dicts avec 'fleet_type_id', 'fuel_l', 'dist_nm', 'duree_s' (optionnel).
    Écarte les vols sans conso ou sans distance, puis trim IQR sur le ratio L/NM
    (identique à fuel_stats_aggregate_rows côté PHP).
    """
    groups: dict[int, list[tuple[float, float, float]]] = {}
    for r in rows:
        fuel = float(r.get("fuel_l") or 0)
        dist = float(r.get("dist_nm") or 0)
        duree = float(r.get("duree_s") or 0)
        if fuel <= 0 or dist <= 0:
            continue
        groups.setdefault(int(r["fleet_type_id"]), []).append((fuel, dist, duree))

    out: dict[int, dict] = {}
    for fid, items in groups.items():
        ratios = sorted(f / d for f, d, _ in items)
        q1, q3 = _quartiles(ratios)
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        kept = [(f, d, t) for f, d, t in items if lo <= f / d <= hi] or items
        total_fuel = sum(f for f, _, _ in kept)
        total_nm = sum(d for _, d, _ in kept)
        total_h = sum(t for _, _, t in kept) / 3600.0
        out[fid] = {
            "nb_vols": len(kept),
            "total_fuel_l": round(total_fuel, 2),
            "total_nm": round(total_nm, 1),
            "total_hours": round(total_h, 2),
            "conso_l_per_nm": round(total_fuel / total_nm, 4) if total_nm > 0 else None,
            "conso_l_per_h": round(total_fuel / total_h, 2) if total_h > 0 else None,
        }
    return out


def fuel_needed(distance_nm: float, conso_l_per_nm: Optional[float],
                conso_l_per_h: Optional[float] = None, reserve_min: float = 30.0) -> dict:
    """Carburant à embarquer : trajet (distance x conso/NM) + réserve (minutes x conso/h).

    Lève ValueError si la distance est invalide ou la conso inconnue.
    """
    if distance_nm is None or distance_nm <= 0:
        raise ValueError("La distance doit être un nombre de NM strictement positif.")
    if conso_l_per_nm is None or conso_l_per_nm <= 0:
        raise ValueError("Consommation inconnue pour ce fleet_type (pas de vols en base).")
    trip_l = distance_nm * conso_l_per_nm
    reserve_l = (reserve_min / 60.0) * conso_l_per_h if (conso_l_per_h and conso_l_per_h > 0) else 0.0
    total_l = trip_l + reserve_l
    return {
        "distance_nm": round(distance_nm, 1),
        "conso_l_per_nm": conso_l_per_nm,
        "conso_l_per_h": conso_l_per_h,
        "reserve_min": reserve_min,
        "trip_l": round(trip_l, 1),
        "reserve_l": round(reserve_l, 1),
        "total_l": round(total_l, 1),
        "total_l_ceil": int(math.ceil(total_l)),
    }
