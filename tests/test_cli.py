"""Tests de la CLI en mode démo (aucun accès réseau)."""

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout

from fuelplanner import cli


class TestCliDemo(unittest.TestCase):
    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_list_demo(self):
        code, out, _ = self._run(["--demo", "--list"])
        self.assertEqual(code, 0)
        self.assertIn("Cessna 172 SP", out)
        self.assertIn("L/NM", out)
        self.assertIn("Global", out)

    def test_calculate_demo(self):
        code, out, _ = self._run(["--demo", "--fleet", "Cessna 172 SP", "--nm", "100"])
        self.assertEqual(code, 0)
        self.assertIn("TOTAL À EMBARQUER", out)
        # 100 NM x 0.1911 L/NM = 19.11 L + 30 min x 29.75 L/h = 14.875 L -> 34.0 L
        self.assertIn("34.00 L", out)

    def test_calculate_json(self):
        code, out, _ = self._run(["--demo", "--fleet", "Cessna 172 SP", "--nm", "100", "--json"])
        self.assertEqual(code, 0)
        res = json.loads(out)
        self.assertAlmostEqual(res["trip_l"], 19.1, places=1)
        self.assertAlmostEqual(res["reserve_l"], 14.9, places=1)
        self.assertEqual(res["total_l_ceil"], 34)
        self.assertFalse(res["source_fallback_global"])

    def test_fallback_global_when_fleet_has_no_data(self):
        code, out, _ = self._run(["--demo", "--fleet", "Planeur ASK21", "--nm", "50", "--json"])
        self.assertEqual(code, 0)
        res = json.loads(out)
        self.assertTrue(res["source_fallback_global"])
        self.assertAlmostEqual(res["conso_l_per_nm"], 2.7867, places=4)

    def test_unknown_fleet_fails(self):
        code, _, err = self._run(["--demo", "--fleet", "Xyz 999", "--nm", "100"])
        self.assertEqual(code, 2)
        self.assertIn("inconnu", err)

    def test_missing_args_fail(self):
        code, _, err = self._run(["--demo"])
        self.assertEqual(code, 2)
        self.assertIn("--fleet", err)

    def test_csv_mode(self):
        csv_path = "data/sample_flights.csv"
        code, out, _ = self._run(["--csv", csv_path, "--list"])
        self.assertEqual(code, 0)
        self.assertIn("Cessna 172 SP", out)
        self.assertIn("DC-3", out)


if __name__ == "__main__":
    unittest.main()
