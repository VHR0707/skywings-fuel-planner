# SkyWings Fuel Planner

Outil desktop (et CLI) qui calcule **le carburant à embarquer** pour un vol, à partir de la
**consommation moyenne réelle** constatée dans l'historique des vols de la compagnie
(table `CARNET_DE_VOL_GENERAL` du site SkyWings), par `fleet_type`.

- **IHM graphique** en Python + tkinter (aucune dépendance externe, Python 3.10+ suffit)
- Aux **couleurs de SkyWings** (`#004080` / `#1a3552` / `#478ED4`) avec le **logo** (`assets/logo.png`)
- **Source de données** : l'endpoint read-only `api/api_fuel_stats.php` du site
  (`https://www.skywings.ovh` par défaut), qui agrège `CARNET_DE_VOL_GENERAL`
  (conso en **L/NM** et **L/h**, trim IQR des outliers, repli sur la conso globale)
- Mode **hors-ligne** : `--csv` (export brut de vols) ou `--demo` (échantillon embarqué)

## Formule

```
carburant trajet = distance (NM) × conso moyenne (L/NM) du fleet_type
réserve          = 30 min de vol × conso horaire (L/h) du fleet_type   (configurable)
TOTAL à embarquer = trajet + réserve
```

## Lancement

```bash
# IHM graphique (interroge le site par défaut)
python -m fuelplanner

# IHM avec un autre site / un CSV / la démo embarquée
python -m fuelplanner --demo
python -m fuelplanner --csv data/sample_flights.csv
python -m fuelplanner --base-url http://localhost

# CLI
python -m fuelplanner --cli --demo --list                          # liste les fleet_types et leurs consos
python -m fuelplanner --cli --fleet "Cessna 172 SP" --nm 120       # calcul (site réel)
python -m fuelplanner --cli --demo --fleet "Cessna 172 SP" --nm 120 --json
python -m fuelplanner --cli --demo --fleet "Cessna 172 SP" --nm 120 --reserve-min 45
```

Dans l'IHM : choisir le **fleet type** dans la liste déroulante, saisir la **distance en NM**
(`120` ou `120,5`), ajuster la **réserve en minutes**, cliquer sur **Calculer le carburant**.

## Tests

```bash
python -m unittest discover -s tests -v
```

Couvre : haversine (valeurs de référence), agrégation + trim IQR, formule du carburant,
sources CSV/HTTP (mocké)/échantillon, CLI en mode démo. Aucun accès réseau requis.

## Contrat de l'API (api/api_fuel_stats.php côté simweb)

`GET {base_url}/api/api_fuel_stats.php` → JSON :

```json
{
  "generated_at": "...", "units": {"fuel": "L", "distance": "NM"}, "prix_litre": 0.88,
  "fleet_types": [{"id": 1, "label": "Cessna 172 SP", "type": "Monomoteur", "nb_appareils": 4,
                   "nb_vols": 812, "total_nm": 96540.2, "total_fuel_l": 18450.8, "total_hours": 620.5,
                   "conso_l_per_nm": 0.1911, "conso_l_per_h": 29.75}],
  "global": {"nb_vols": 1458, "conso_l_per_nm": 2.7867, "conso_l_per_h": 653.52, "...": "..."}
}
```

`conso_l_per_nm` / `conso_l_per_h` sont `null` si le fleet_type n'a aucun vol en base
(l'IHM/CLI bascule alors sur `global`).

## Note pour le futur plugin SimAddon

Le même endpoint `api_fuel_stats.php` pourra être appelé par un plugin SimAddon pour
pré-remplir le carburant à embarquer directement dans l'ACARS — aucune BDD à toucher
côté client, un simple GET HTTPS suffit.

## Arborescence

```
skywings-fuel-planner/
├── fuelplanner/
│   ├── __init__.py
│   ├── __main__.py      # python -m fuelplanner (IHM) / --cli (CLI)
│   ├── calc.py          # calculs purs : haversine, agrégation, fuel_needed
│   ├── sources.py       # HttpSource (API), CsvSource (hors-ligne), SampleSource (démo)
│   ├── cli.py           # interface ligne de commande
│   └── gui.py           # IHM tkinter aux couleurs SkyWings
├── assets/logo.png      # logo SkyWings (copié depuis simweb/assets/images)
├── data/
│   ├── sample_fuel_stats.json   # échantillon format API (démo/tests)
│   └── sample_flights.csv       # échantillon brut pour --csv
├── tests/               # unittest : calc, sources, cli
└── README.md
```
