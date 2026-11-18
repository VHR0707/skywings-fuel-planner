"""Tests des conversions d'unités (fuelplanner.units)."""

import math
import unittest

from fuelplanner.calc import fuel_needed
from fuelplanner.units import (DEFAULT_DENSITY_KG_PER_L, LITERS_PER_GAL_IMP,
                               LITERS_PER_GAL_US, UNITS, convert_from_liters,
                               convert_result, unit_suffix)


class TestConvertFromLiters(unittest.TestCase):
    def test_liters_identity(self):
        self.assertEqual(convert_from_liters(42.5, "L"), 42.5)

    def test_gallons_us(self):
        self.assertAlmostEqual(convert_from_liters(LITERS_PER_GAL_US, "gal_us"), 1.0, places=9)
        self.assertAlmostEqual(convert_from_liters(100.0, "gal_us"), 26.4172, places=3)

    def test_gallons_imperiaux(self):
        self.assertAlmostEqual(convert_from_liters(LITERS_PER_GAL_IMP, "gal_imp"), 1.0, places=9)
        self.assertAlmostEqual(convert_from_liters(100.0, "gal_imp"), 21.9969, places=3)

    def test_kg_avec_densite(self):
        self.assertAlmostEqual(convert_from_liters(100.0, "kg", density=0.72), 72.0)
        self.assertAlmostEqual(convert_from_liters(100.0, "kg"), 100.0 * DEFAULT_DENSITY_KG_PER_L)

    def test_unknown_unit_raises(self):
        with self.assertRaises(ValueError):
            convert_from_liters(1.0, "xyz")

    def test_kg_densite_invalide_raises(self):
        with self.assertRaises(ValueError):
            convert_from_liters(1.0, "kg", density=0.0)

    def test_unit_suffix(self):
        self.assertEqual(unit_suffix("L"), "L")
        self.assertEqual(unit_suffix("kg"), "kg")
        self.assertEqual(unit_suffix("gal_us"), "gal US")
        self.assertEqual(unit_suffix("gal_imp"), "gal imp")
        with self.assertRaises(ValueError):
            unit_suffix("xyz")


class TestConvertResult(unittest.TestCase):
    def setUp(self):
        # 100 NM x 0.2 L/NM = 20 L ; réserve 30 min x 30 L/h = 15 L ; total 35 L
        self.res = fuel_needed(100.0, 0.2, 30.0, reserve_min=30.0)

    def test_liters_unchanged(self):
        out = convert_result(self.res, unit="L")
        self.assertEqual(out["total"], 35.0)
        self.assertEqual(out["total_ceil"], 35)
        self.assertEqual(out["unit"], "L")

    def test_gal_us(self):
        out = convert_result(self.res, unit="gal_us")
        self.assertAlmostEqual(out["total"], 35.0 / LITERS_PER_GAL_US, places=2)
        self.assertEqual(out["total_ceil"], math.ceil(35.0 / LITERS_PER_GAL_US))
        self.assertAlmostEqual(out["conso_per_nm"], 0.2 / LITERS_PER_GAL_US, places=4)
        self.assertAlmostEqual(out["conso_per_h"], 30.0 / LITERS_PER_GAL_US, places=2)
        self.assertEqual(out["total_l"], 35.0)  # litres toujours présents

    def test_kg(self):
        out = convert_result(self.res, unit="kg", density=0.8)
        self.assertAlmostEqual(out["total"], 28.0, places=2)
        self.assertEqual(out["density_kg_per_l"], 0.8)


if __name__ == "__main__":
    unittest.main()
