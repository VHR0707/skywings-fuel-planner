"""Point d'entrée : `python -m fuelplanner` lance l'IHM, `python -m fuelplanner --cli ...` la CLI."""

import sys

if __name__ == "__main__":
    if "--cli" in sys.argv:
        sys.argv.remove("--cli")
        from . import cli
        raise SystemExit(cli.main())
    if "--web" in sys.argv:
        sys.argv.remove("--web")
        from . import web
        raise SystemExit(web.main())
    from . import gui
    raise SystemExit(gui.main())
