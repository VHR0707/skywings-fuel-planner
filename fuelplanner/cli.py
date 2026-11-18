"""Interface en ligne de commande du planificateur carburant."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from .calc import fuel_needed
from .sources import DEFAULT_BASE_URL, SourceError, make_source
from .units import (DEFAULT_DENSITY_KG_PER_L, DEFAULT_UNIT, UNITS, convert_result,
                    unit_suffix)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="fuelplanner",
        description="SkyWings Fuel Planner — carburant à embarquer, calculé depuis "
                    "l'historique des vols (CARNET_DE_VOL_GENERAL via api_fuel_stats.php).",
    )
    src = p.add_argument_group("source de données")
    src.add_argument("--base-url", default=DEFAULT_BASE_URL,
                     help=f"URL du site SkyWings (défaut : {DEFAULT_BASE_URL})")
    src.add_argument("--csv", help="CSV brut de vols, mode hors-ligne (colonnes : "
                                   "fleet_type_id,label,type,fuel_l,dist_nm,duree_s)")
    src.add_argument("--demo", action="store_true",
                     help="Utilise l'échantillon embarqué data/sample_fuel_stats.json (test hors-ligne)")
    p.add_argument("--list", action="store_true",
                   help="Liste les fleet_types et leurs consommations de référence, puis quitte")
    p.add_argument("--fleet", help='Label du fleet_type, ex. "Cessna 172 SP" (requis sans --list)')
    p.add_argument("--nm", type=float, help="Distance du vol en NM (requis sans --list)")
    p.add_argument("--reserve-min", type=float, default=30.0,
                   help="Réserve en minutes de vol (défaut : 30)")
    p.add_argument("--unit", default=DEFAULT_UNIT, choices=sorted(UNITS),
                   help="Unité d'affichage du carburant (défaut : L)")
    p.add_argument("--density", type=float, default=DEFAULT_DENSITY_KG_PER_L,
                   help="Densité kg/L pour la conversion en kg (défaut : 0.72, Avgas 100LL)")
    p.add_argument("--json", action="store_true", help="Sortie JSON brute")
    return p


def find_fleet(stats: dict, label: str) -> Optional[dict]:
    """Retrouve un fleet_type par label exact, puis par sous-chaîne (insensible à la casse)."""
    norm = label.strip().lower()
    for ft in stats["fleet_types"]:
        if ft["label"].strip().lower() == norm:
            return ft
    for ft in stats["fleet_types"]:
        if norm in ft["label"].strip().lower():
            return ft
    return None


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        stats = make_source(base_url=args.base_url, csv_path=args.csv, demo=args.demo).fetch()
    except SourceError as e:
        print(f"ERREUR source : {e}", file=sys.stderr)
        return 2

    if args.list:
        if args.json:
            print(json.dumps(stats, ensure_ascii=False, indent=2))
        else:
            print(f"{'ID':>4}  {'Fleet type':<30} {'Catégorie':<12} {'Vols':>6}  {'L/NM':>8}  {'L/h':>8}")
            for ft in stats["fleet_types"]:
                cnm = f"{ft['conso_l_per_nm']:.4f}" if ft["conso_l_per_nm"] else "-"
                ch = f"{ft['conso_l_per_h']:.2f}" if ft["conso_l_per_h"] else "-"
                print(f"{ft['id']:>4}  {ft['label']:<30.30} {ft['type']:<12.12} "
                      f"{ft['nb_vols']:>6}  {cnm:>8}  {ch:>8}")
            g = stats["global"]
            if g.get("conso_l_per_nm"):
                print(f"\nGlobal : {g['nb_vols']} vols, {g['conso_l_per_nm']:.4f} L/NM, "
                      f"{g['conso_l_per_h']:.2f} L/h")
            else:
                print("\nGlobal : pas de données de consommation.")
        return 0

    if not args.fleet or args.nm is None:
        print("ERREUR : --fleet et --nm sont requis (ou --list).", file=sys.stderr)
        return 2
    ft = find_fleet(stats, args.fleet)
    if ft is None:
        print(f"ERREUR : fleet_type inconnu : {args.fleet!r}. Lance avec --list pour voir les valeurs.",
              file=sys.stderr)
        return 2

    conso_nm, conso_h, used_global = ft["conso_l_per_nm"], ft["conso_l_per_h"], False
    if conso_nm is None or conso_nm <= 0:
        g = stats["global"]
        if not g.get("conso_l_per_nm"):
            print("ERREUR : aucune conso disponible (ni pour ce fleet_type, ni en global).",
                  file=sys.stderr)
            return 3
        conso_nm, conso_h, used_global = g["conso_l_per_nm"], g["conso_l_per_h"], True

    try:
        res = fuel_needed(args.nm, conso_nm, conso_h, reserve_min=args.reserve_min)
        res = convert_result(res, unit=args.unit, density=args.density)
    except ValueError as e:
        print(f"ERREUR : {e}", file=sys.stderr)
        return 2

    res["fleet_type"] = ft["label"]
    res["nb_vols_reference"] = stats["global"]["nb_vols"] if used_global else ft["nb_vols"]
    res["source_fallback_global"] = used_global

    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        suf = unit_suffix(args.unit)
        print(f"Fleet type         : {res['fleet_type']}"
              f" ({res['nb_vols_reference']} vols de référence"
              f"{' — repli sur la conso globale' if used_global else ''})")
        print(f"Distance           : {res['distance_nm']:.1f} NM")
        line = f"Conso de référence : {res['conso_l_per_nm']:.4f} L/NM"
        if res.get("conso_per_nm") and args.unit != "L":
            line += f"  ({res['conso_per_nm']:.4f} {suf}/NM)"
        if res["conso_l_per_h"]:
            line += f"  ({res['conso_l_per_h']:.2f} L/h"
            if res.get("conso_per_h") and args.unit != "L":
                line += f" — {res['conso_per_h']:.2f} {suf}/h"
            line += ")"
        print(line)
        print(f"Carburant trajet   : {res['trip']:.2f} {suf}"
              + (f"  ({res['trip_l']:.1f} L)" if args.unit != "L" else ""))
        print(f"Réserve {res['reserve_min']:.0f} min    : {res['reserve']:.2f} {suf}"
              + (f"  ({res['reserve_l']:.1f} L)" if args.unit != "L" else ""))
        print(f"TOTAL À EMBARQUER  : {res['total']:.2f} {suf}  (arrondi haut : {res['total_ceil']} {suf})"
              + (f"  = {res['total_l']:.1f} L" if args.unit != "L" else ""))
        if stats.get("prix_litre"):
            print(f"Coût estimé        : {res['total_l'] * stats['prix_litre']:.2f} € "
                  f"({stats['prix_litre']} €/L)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
