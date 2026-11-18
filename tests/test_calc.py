"""Tests unitaires des calculs purs (fuelplanner.calc)."""

import math
import unittest

from fuelplanner.calc import aggregate_fuel_rows, fuel_needed, haversine_nm


class TestHaversine(unittest.TestCase):
    def test_one_degree_lon_at_equator_is_60_nm(self):
        # 1 degre de longitude a l'equateur = 1/360 du cercle = ~60 NM
        d = haversine_nm(0.0, 0.0, 0.0, 1.0)
        self.assertAlmostEqual(d, 60.04, places=2)

    def test_one_degree_lat(self):
        d = haversine_nm(0.0, 0.0, 1.0, 0.0)
        self.assertAlmostEqual(d, 60.04, places=2)

    def test_same_point_is_zero(self):
        self.assertEqual(haversine_nm(45.0, 4.0, 45.0, 4.0), 0.0)

    def test_quarter_globe(self):
        d = haversine_nm(0.0, 0.0, 90.0, 0.0)
        self.assertAlmostEqual(d, math.pi / 2 * 3440.065, places=1)

    def test_symmetry(self):
        a = haversine_nm(48.85, 2.35, 43.63, 1.38)  # Paris -> Montpellier
        b = haversine_nm(43.63, 1.38, 48.85, 2.35)
        self.assertAlmostEqual(a, b, places=9)
        self.assertTrue(300 < a < 350)  # Paris-Montpellier ~ 320 NM


class TestAggregateFuelRows(unittest.TestCase):
    def _rows_fleet1(self):
        rows = [{"fleet_type_id": 1, "fuel_l": 30.0, "dist_nm": 150.0, "duree_s": 3600.0}
                for _ in range(5)]
        rows.append({"fleet_type_id": 1, "fuel_l": 500.0, "dist_nm": 150.0, "duree_s": 3600.0})  # outlier
        return rows

    def test_outlier_trimmed_and_conso(self):
        stats = aggregate_fuel_rows(self._rows_fleet1())
        s = stats[1]
        self.assertEqual(s["nb_vols"], 5)  # l'outlier 500L est rejeté par le trim IQR
        self.assertAlmostEqual(s["conso_l_per_nm"], 0.2, places=4)
        self.assertAlmostEqual(s["conso_l_per_h"], 30.0, places=2)
        self.assertEqual(s["total_fuel_l"], 150.0)
        self.assertEqual(s["total_nm"], 750.0)

    def test_invalid_rows_skipped(self):
        rows = [
            {"fleet_type_id": 3, "fuel_l": 0.0, "dist_nm": 100.0, "duree_s": 3600.0},   # fuel <= 0
            {"fleet_type_id": 3, "fuel_l": 40.0, "dist_nm": 0.0, "duree_s": 3600.0},    # dist <= 0
            {"fleet_type_id": 3, "fuel_l": 40.0, "dist_nm": None, "duree_s": 3600.0},   # dist null
            {"fleet_type_id": 3, "fuel_l": -5.0, "dist_nm": 100.0, "duree_s": 3600.0},  # fuel negative
        ]
        self.assertEqual(aggregate_fuel_rows(rows), {})

    def test_empty(self):
        self.assertEqual(aggregate_fuel_rows([]), {})

    def test_multiple_groups(self):
        rows = self._rows_fleet1() + [
            {"fleet_type_id": 2, "fuel_l": 120.0, "dist_nm": 200.0, "duree_s": 5400.0},
            {"fleet_type_id": 2, "fuel_l": 110.0, "dist_nm": 190.0, "duree_s": 5100.0},
        ]
        stats = aggregate_fuel_rows(rows)
        self.assertEqual(set(stats), {1, 2})
        self.assertAlmostEqual(stats[2]["conso_l_per_nm"], 230.0 / 390.0, places=4)

    def test_no_duree_means_no_hourly_conso(self):
        rows = [{"fleet_type_id": 1, "fuel_l": 30.0, "dist_nm": 150.0}]  # pas de duree_s
        s = aggregate_fuel_rows(rows)[1]
        self.assertAlmostEqual(s["conso_l_per_nm"], 0.2, places=4)
        self.assertIsNone(s["conso_l_per_h"])


class TestFuelNeeded(unittest.TestCase):
    def test_trip_plus_reserve(self):
        res = fuel_needed(100.0, 0.2, 30.0, reserve_min=30.0)
        self.assertAlmostEqual(res["trip_l"], 20.0)
        self.assertAlmostEqual(res["reserve_l"], 15.0)  # 30 min = 0,5 h x 30 L/h
        self.assertAlmostEqual(res["total_l"], 35.0)
        self.assertEqual(res["total_l_ceil"], 35)

    def test_ceil_rounds_up(self):
        res = fuel_needed(101.0, 0.2, 30.0, reserve_min=30.0)
        self.assertAlmostEqual(res["total_l"], 35.2)
        self.assertEqual(res["total_l_ceil"], 36)

    def test_without_hourly_conso_reserve_is_zero(self):
        res = fuel_needed(100.0, 0.2, None, reserve_min=30.0)
        self.assertEqual(res["reserve_l"], 0.0)
        self.assertAlmostEqual(res["total_l"], 20.0)

    def test_zero_reserve(self):
        res = fuel_needed(50.0, 0.2, 30.0, reserve_min=0.0)
        self.assertEqual(res["reserve_l"], 0.0)
        self.assertAlmostEqual(res["total_l"], 10.0)

    def test_invalid_distance_raises(self):
        with self.assertRaises(ValueError):
            fuel_needed(0.0, 0.2, 30.0)
        with self.assertRaises(ValueError):
            fuel_needed(-10.0, 0.2, 30.0)

    def test_unknown_conso_raises(self):
        with self.assertRaises(ValueError):
            fuel_needed(100.0, None, 30.0)
        with self.assertRaises(ValueError):
            fuel_needed(100.0, 0.0, 30.0)


if __name__ == "__main__":
    unittest.main()
