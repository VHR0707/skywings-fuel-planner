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

### Unités d'affichage
Litres (défaut), **kg** (densité réglable, défaut 0,72 kg/L = Avgas 100LL ; 0,80 pour du Jet A1),
**gallons US**, **gallons impériaux**. Choix dans une combobox (IHM et web) ou `--unit` (CLI).

### Avec l'exécutable (recommandé pour les pilotes)
`dist\SkyWingsFuelPlanner.exe` — double-clic → IHM graphique (choisir le fleet type,
saisir la distance en NM, ajuster la réserve en minutes, cliquer sur *Calculer*).
L'exe embarque Python + le logo + les données de démo : il interroge le site en ligne.

Ligne de commande depuis l'exe :
```
SkyWingsFuelPlanner.exe --cli --list
SkyWingsFuelPlanner.exe --cli --fleet "C172" --nm 150 --unit gal_us
SkyWingsFuelPlanner.exe --web --demo        # version web locale sur http://127.0.0.1:8765
```

### Version web locale (sans rien héberger sur le site)
Le plus simple : **double-clic sur `web.bat`** (à la racine du repo) → ouvre
http://127.0.0.1:8765 dans le navigateur. En ligne de commande :
```
python -m fuelplanner --web                 # ouvre http://127.0.0.1:8765 dans le navigateur
python -m fuelplanner --web --port 9000
web.bat --demo                              # hors-ligne (données fictives)
```
Le serveur tourne **sur ton poste uniquement** (127.0.0.1) : la page appelle des routes
locales (`/api/fuel_stats`, `/api/compute`) et c'est le serveur Python qui fait proxy vers
`https://www.skywings.ovh/api/api_fuel_stats.php`. Aucune donnée n'est envoyée ailleurs.
Astuce : `--demo` ou `--csv` pour tester sans accès au site.

### Depuis les sources (développeur)
Prérequis : Python 3.10+ (3.11 installé ici), aucune dépendance (`requirements.txt` est vide).
```
cd F:\GitHub\skywings-fuel-planner
python -m fuelplanner                                   # IHM
python -m fuelplanner --web                             # web local
python -m fuelplanner --demo                            # IHM hors-ligne (données fictives)
python -m fuelplanner --cli --list                      # liste les fleet_types (site réel)
python -m fuelplanner --cli --fleet "C172" --nm 150    # calcul
python -m fuelplanner --cli --fleet "C172" --nm 150 --unit kg --density 0.8
python -m fuelplanner --cli --fleet "C172" --nm 150 --json
python -m unittest discover -s tests -v                 # tests (55)
```

## 3. Publier sur Git sous VHR0707 (pas Skall34)

L'identité Git globale de la machine est déjà `VHR0707 <vhr0707@gmail.com>`
(`git config --global user.name` / `user.email`) — les commits partiront donc sous VHR0707.

### 3.1 Une fois : créer le dépôt sur GitHub (compte VHR0707) — FAIT en CLI
La machine a déjà un credential GitHub enregistré pour **VHR0707** (Git Credential Manager).
Méthode utilisée (sans rien installer) :
```bash
# 1. récupérer le token stocké (ne jamais l'afficher)
TOKEN=$(printf "protocol=https\nhost=github.com\n" | git credential fill | sed -n 's/^password=//p')
# 2. créer le dépôt public sous VHR0707
curl -s -X POST https://api.github.com/user/repos \
     -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" \
     -d '{"name":"skywings-fuel-planner","public":true}'
# 3. pousser
cd F:\GitHub\skywings-fuel-planner
git push -u origin main
```
Autres options : `gh auth login` puis `gh repo create VHR0707/skywings-fuel-planner --public --source . --push`,
ou github.com/new (connecté en VHR0707) → `skywings-fuel-planner`, Public, sans README.

> ✅ Le dépôt existe déjà : https://github.com/VHR0707/skywings-fuel-planner (public, main poussé).
> Dans GitHub Desktop, maintenant que le dépôt existe côté GitHub, le simple
> **Push origin** (Ctrl+P) fonctionnera — plus besoin de toucher au remote.

### 3.2 Remote local
```
cd F:\GitHub\skywings-fuel-planner
git remote add origin https://github.com/VHR0707/skywings-fuel-planner.git   # déjà fait
```
> Le `push` publie le code : c'est l'action à valider explicitement. Ne jamais faire
> `git push --force` sur `main`.

### 3.2 bis — Publier avec GitHub Desktop (ta méthode habituelle)
1. Ouvre **GitHub Desktop** → *File → Options → Accounts* → *Sign in* avec le compte
   **VHR0707** (github.com).
2. *File → Add local repository…* → `F:\GitHub\skywings-fuel-planner` → *Add Repository*.
3. Le dépôt a déjà un remote `origin` (posé en ligne de commande). Deux façons de créer
   le dépôt sur GitHub :
   - **100 % Desktop** : *Repository → Repository settings → Remote* → retire l'URL
     (bouton −) → OK. Le bouton **Publish repository** réapparaît en haut de la fenêtre :
     choisis le compte **VHR0707**, le nom `skywings-fuel-planner`, coche **Public**,
     clique **Publish Repository** → le dépôt est créé sur GitHub ET poussé d'un coup.
   - **Dépôt créé d'abord sur le web** (github.com/new en étant connecté VHR0707, nom
     `skywings-fuel-planner`, Public, rien d'autre) : reviens dans Desktop, fais
     *Fetch origin* (bouton en haut), puis **Push origin** (Ctrl+P).
4. Au quotidien dans Desktop : les fichiers modifiés apparaissent à gauche → remplis
   *Summary* (+ *Description*) → **Commit to main** → **Push origin** (Ctrl+P).
   Les commits seront signés **VHR0707** (identité globale de la machine).

### 3.3 Au quotidien
```
git status                          # voir ce qui a changé
git add -A                          # tout ajouter
git commit -m "un message court"        # commit signé VHR0707 automatiquement
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
