"""Tests de non-régression de l'IHM tkinter (montée réelle de la fenêtre, source démo).

Skippés si pas d'affichage (CI headless) : tk.TclError -> skipTest.
"""

import unittest

try:
    import tkinter as tk
    from fuelplanner.gui import FuelPlannerApp
    from fuelplanner.sources import SampleSource
    TK_AVAILABLE = True
except Exception:
    TK_AVAILABLE = False


@unittest.skipUnless(TK_AVAILABLE, "tkinter indisponible")
class TestGuiUnits(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest(f"pas d'affichage : {e}")
        self.root.withdraw()
        self.app = FuelPlannerApp(self.root, {"base_url": "https://www.skywings.ovh",
                                              "csv_path": None, "demo": True})
        self.app._on_stats_loaded(SampleSource().fetch())
        self.root.update()

    def tearDown(self):
        self.root.destroy()

    def _calculate(self):
        self.app.fleet_combo.current(0)
        self.app.nm_var.set("100")
        self.app.reserve_var.set("30")
        self.app.on_calculate()
        self.root.update()
        return self.app.result.get("1.0", "end"), self.app.status_var.get()

    def test_calculate_default_unit_liters(self):
        """Régression : la combobox affichait un label, le calcul plantait ('Unité inconnue')."""
        content, status = self._calculate()
        self.assertIn("TOTAL", content)
        self.assertIn("34.00 L", content)
        self.assertNotIn("inconnue", status)

    def test_calculate_kg_shows_kg_and_liters(self):
        self.app.unit_var.set("Kilogrammes (kg)")  # label affiché dans la combobox
        self.app._on_unit_changed()
        self.app.density_var.set("0.72")
        self.root.update()
        self.assertEqual(self.app.density_entry.winfo_manager(), "grid")
        content, status = self._calculate()
        self.assertIn("kg", content)
        self.assertIn("34.0 L", content)  # équivalent litres entre parenthèses
        self.assertNotIn("inconnue", status)

    def test_calculate_gal_us(self):
        self.app.unit_var.set("Gallons US")
        self.app._on_unit_changed()
        self.root.update()
        self.assertEqual(self.app.density_entry.winfo_manager(), "")
        content, _ = self._calculate()
        self.assertIn("gal US", content)
        self.assertIn("34.0 L", content)

    def test_bad_nm_shows_status_error_not_crash(self):
        self.app.fleet_combo.current(0)
        self.app.nm_var.set("abc")
        self.app.on_calculate()
        self.root.update()
        self.assertIn("invalide", self.app.status_var.get())


if __name__ == "__main__":
    unittest.main()
