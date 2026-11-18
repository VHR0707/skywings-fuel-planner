"""Lanceur packagé (exe) : GUI par défaut, `--cli` pour la ligne de commande.

Utilisé comme point d'entrée par PyInstaller (build_exe.bat) ; en source,
`python -m fuelplanner` fait la même chose via fuelplanner/__main__.py.
"""

import sys

if __name__ == "__main__":
    if "--cli" in sys.argv:
        sys.argv.remove("--cli")
        from fuelplanner import cli
        raise SystemExit(cli.main())
    from fuelplanner import gui
    raise SystemExit(gui.main())
