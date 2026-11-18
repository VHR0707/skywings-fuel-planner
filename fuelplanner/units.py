"""Unités d'affichage du carburant.

Interne : tout est en litres (L), comme dans CARNET_DE_VOL_GENERAL.
Affichage : L, kg (via densité), gallons US, gallons impériaux.
"""

from __future__ import annotations

import math
from typing import Optional

# Densité par défaut : Avgas 100LL ≈ 0,72 kg/L (le site facture au litre d'essence).
# Jet A1 ≈ 0,80 kg/L si besoin.
DEFAULT_DENSITY_KG_PER_L = 0.72
JETA1_DENSITY_KG_PER_L = 0.80

LITERS_PER_GAL_US = 3.785411784
LITERS_PER_GAL_IMP = 4.54609

# facteur de conversion depuis les litres (None = dépend de la densité, cas kg)
UNITS = {
    "L":       {"label": "Litres (L)",          "suffix": "L",       "factor_from_l": 1.0},
    "kg":      {"label": "Kilogrammes (kg)",    "suffix": "kg",      "factor_from_l": None},
    "gal_us":  {"label": "Gallons US",          "suffix": "gal US",  "factor_from_l": 1.0 / LITERS_PER_GAL_US},
    "gal_imp": {"label": "Gallons impériaux",   "suffix": "gal imp", "factor_from_l": 1.0 / LITERS_PER_GAL_IMP},
}
DEFAULT_UNIT = "L"


def convert_from_liters(value_l: float, unit: str = DEFAULT_UNIT,
                        density: float = DEFAULT_DENSITY_KG_PER_L) -> float:
    """Convertit une quantité de litres vers l'unité d'affichage choisie."""
    if unit == "kg":
        if density <= 0:
            raise ValueError("La densité (kg/L) doit être strictement positive.")
        return value_l * density
    u = UNITS.get(unit)
    if u is None:
        raise ValueError(f"Unité inconnue : {unit!r} (attendu : {sorted(UNITS)})")
    return value_l * u["factor_from_l"]


def unit_suffix(unit: str) -> str:
    if unit == "kg":
        return "kg"
    u = UNITS.get(unit)
    if u is None:
        raise ValueError(f"Unité inconnue : {unit!r}")
    return u["suffix"]


def convert_result(res: dict, unit: str = DEFAULT_UNIT,
                   density: float = DEFAULT_DENSITY_KG_PER_L) -> dict:
    """Enrichit un résultat fuel_needed() avec les valeurs converties dans l'unité choisie.

    Ajoute : unit, trip, reserve, total, total_ceil, conso_per_nm, conso_per_h
    (les champs *_l en litres restent présents).
    """
    out = dict(res)
    out["unit"] = unit
    out["density_kg_per_l"] = density if unit == "kg" else None
    for src, dst in (("trip_l", "trip"), ("reserve_l", "reserve"), ("total_l", "total")):
        out[dst] = round(convert_from_liters(res[src], unit, density), 2)
    out["total_ceil"] = int(math.ceil(convert_from_liters(res["total_l"], unit, density)))
    if res.get("conso_l_per_nm"):
        out["conso_per_nm"] = round(convert_from_liters(res["conso_l_per_nm"], unit, density), 4)
    if res.get("conso_l_per_h"):
        out["conso_per_h"] = round(convert_from_liters(res["conso_l_per_h"], unit, density), 2)
    return out
