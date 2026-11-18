"""Lanceur packagé (exe) : GUI par défaut, `--cli` / `--web` pour la ligne de commande.

Utilisé comme point d'entrée par PyInstaller (build_exe.bat, mode --noconsole) ;
en source, `python -m fuelplanner` fait la même chose via fuelplanner/__main__.py.
"""

import sys


def _ensure_console() -> None:
    """En exe fenêtré (--noconsole), réalloue une console pour les modes --cli/--web,
    afin que leurs logs restent visibles (double-clic sur un raccourci avec --cli)."""
    if sys.stdout is not None:
        return  # déjà dans une console (lancement depuis cmd)
    try:
        import ctypes
        ctypes.windll.kernel32.AllocConsole()
        sys.stdout = open("CONOUT$", "w", encoding="utf-8", buffering=1)
        sys.stderr = open("CONOUT$", "w", encoding="utf-8", buffering=1)
    except Exception:
        pass  # pas de console dispo : on continue sans logs


if __name__ == "__main__":
    if "--cli" in sys.argv or "--web" in sys.argv:
        _ensure_console()
    if "--cli" in sys.argv:
        sys.argv.remove("--cli")
        from fuelplanner import cli
        raise SystemExit(cli.main())
    if "--web" in sys.argv:
        sys.argv.remove("--web")
        from fuelplanner import web
        raise SystemExit(web.main())
    from fuelplanner import gui
    raise SystemExit(gui.main())
