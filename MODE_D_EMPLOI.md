# Mode d'emploi — SkyWings Fuel Planner

## 1. La formule (pour être sûr)

```
carburant trajet  = distance saisie (NM) × conso moyenne du fleet_type (L/NM)
réserve           = 30 min de vol × conso horaire du fleet_type (L/h)
TOTAL À EMBARQUER = trajet + réserve        (affiché aussi arrondi au litre supérieur)
```

La conso moyenne est calculée **en direct sur le site SkyWings** à partir de
`CARNET_DE_VOL_GENERAL` (vols non annulés, conso = `fuel_depart - fuel_arrivee` en litres,
distance orthodromique en NM entre aéroports, trim IQR des outliers) :
`GET https://www.skywings.ovh/api/api_fuel_stats.php`.
Si un fleet_type n'a aucun vol en base, l'outil bascule sur la conso **globale** (indiqué).

## 2. Lancer l'outil

### Avec l'exécutable (recommandé pour les pilotes)
`dist\SkyWingsFuelPlanner.exe` — double-clic → IHM graphique (choisir le fleet type,
saisir la distance en NM, ajuster la réserve en minutes, cliquer sur *Calculer*).
L'exe embarque Python + le logo + les données de démo : il interroge le site en ligne.

Ligne de commande depuis l'exe :
```
SkyWingsFuelPlanner.exe --cli --list
SkyWingsFuelPlanner.exe --cli --fleet "C172" --nm 150
```

### Depuis les sources (développeur)
Prérequis : Python 3.10+ (3.11 installé ici), aucune dépendance (`requirements.txt` est vide).
```
cd F:\GitHub\skywings-fuel-planner
python -m fuelplanner                                   # IHM
python -m fuelplanner --demo                            # IHM hors-ligne (données fictives)
python -m fuelplanner --cli --list                      # liste les fleet_types (site réel)
python -m fuelplanner --cli --fleet "C172" --nm 150    # calcul
python -m fuelplanner --cli --fleet "C172" --nm 150 --json
python -m unittest discover -s tests -v                 # 32 tests
```

## 3. Publier sur Git sous VHR0707 (pas Skall34)

L'identité Git globale de la machine est déjà `VHR0707 <vhr0707@gmail.com>`
(`git config --global user.name` / `user.email`) — les commits partiront donc sous VHR0707.

### 3.1 Une fois : créer le dépôt vide sur GitHub (compte VHR0707)
Option A — en ligne de commande (GitHub CLI) :
```
gh auth login                        # se connecter avec le compte VHR0707
cd F:\GitHub\skywings-fuel-planner
gh repo create VHR0707/skywings-fuel-planner --public --source . --push
```
Option B — via le navigateur : connecté sur github.com en tant que **VHR0707**,
*New repository* → nom `skywings-fuel-planner`, **Public**, ne rien cocher d'autre
(pas de README/licence/gitignore automatiques), *Create repository*.

### 3.2 Une fois : brancher le remote local
```
cd F:\GitHub\skywings-fuel-planner
git remote add origin https://github.com/VHR0707/skywings-fuel-planner.git   # déjà fait ici
git push -u origin main
```
> Le `push` publie le code : c'est l'action à valider explicitement. Ne jamais faire
> `git push --force` sur `main`.

### 3.3 Au quotidien
```
git status                          # voir ce qui a changé
git add -A                          # tout ajouter
git commit -m " ungaea message court"   # commit signé VHR0707 automatiquement
git push                            # publier sur GitHub (VHR0707/skywings-fuel-planner)
git pull                            # récupérer les modifs des autres
```
Convention : un commit = un changement cohérent, message au présent, en français.

## 4. Fabriquer l'exécutable (.exe)

```
pip install pyinstaller             # une fois
build_exe.bat                       # ou : python -m PyInstaller --onefile --name SkyWingsFuelPlanner --add-data "assets;assets" --add-data "data;data" main.py
```
Résultat : `dist\SkyWingsFuelPlanner.exe` (~12 Mo, autonome). À distribuer tel quel
aux pilotes (ils n'ont besoin ni de Python ni de Git).

Pour distribuer l'exe via GitHub : sur la page du dépôt
`github.com/VHR0707/skywings-fuel-planner` → *Releases* → *Draft a new release* →
attacher `dist\SkyWingsFuelPlanner.exe` en asset → *Publish release*. Les pilotes
téléchargent juste l'exe depuis la release.
(`dist/` et `build/` sont ignorés par Git : le binaire n'est pas commité dans le dépôt.)

## 5. Dépannage

| Symptôme | Cause / solution |
|---|---|
| `ERREUR source : Endpoint injoignable` | Pas d'accès à skywings.ovh (VPN, proxy, hors-ligne) → tester avec `--demo` ou `--csv <fichier.csv>` |
| Un fleet_type affiche `-` en conso | Aucun vol en base pour ce type → l'outil bascule sur la conso globale (ligne « repli » affichée) |
| `tkinter` introuvable sous Linux | `sudo apt install python3-tk` |
| L'exe ne se lance pas | antivirus à désactiver temporairement (PyInstaller onefile), ou lancer depuis les sources |

## 6. Et la version web ?

L'endpoint `api_fuel_stats.php` étant public, une page web dans simweb (`pages/...`)
pourrait faire exactement le même calcul en JS — c'est un futur chantier séparé,
le contrat JSON est documenté dans `README.md`.
