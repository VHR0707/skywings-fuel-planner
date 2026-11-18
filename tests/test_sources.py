"""Tests des sources de données (CSV hors-ligne, HTTP mocké, échantillon embarqué)."""

import io
import json
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

from fuelplanner.sources import (CsvSource, HttpSource, SampleSource, SourceError,
                                 normalize_payload)

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_JSON = REPO_ROOT / "data" / "sample_fuel_stats.json"

CSV_OK = """fleet_type_id,label,type,fuel_l,dist_nm,duree_s
1,Cessna 172 SP,Monomoteur,30.0,150.0,3600
1,Cessna 172 SP,Monomoteur,31.0,155.0,3660
2,DC-3,Bimoteur,120.0,200.0,5400
"""

CSV_BAD = """fleet_type_id,fuel_l
1,30.0
"""


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TestNormalizePayload(unittest.TestCase):
    def test_missing_fleet_types_raises(self):
        with self.assertRaises(SourceError):
            normalize_payload({"foo": 1})

    def test_sample_file_shape(self):
        stats = normalize_payload(json.loads(SAMPLE_JSON.read_text(encoding="utf-8")))
        self.assertIn("fleet_types", stats)
        self.assertIn("global", stats)
        self.assertTrue(stats["fleet_types"])
        for ft in stats["fleet_types"]:
            for k in ("nb_vols", "total_fuel_l", "total_nm", "total_hours",
                      "conso_l_per_nm", "conso_l_per_h"):
                self.assertIn(k, ft)
        # le planeur de l'échantillon n'a aucune donnée -> conso null
        planeur = next(f for f in stats["fleet_types"] if f["label"] == "Planeur ASK21")
        self.assertIsNone(planeur["conso_l_per_nm"])


class TestCsvSource(unittest.TestCase):
    def test_aggregates_locally(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as f:
            f.write(CSV_OK)
            path = f.name
        stats = CsvSource(path).fetch()
        self.assertEqual(len(stats["fleet_types"]), 2)
        c172 = next(f for f in stats["fleet_types"] if f["id"] == 1)
        self.assertEqual(c172["label"], "Cessna 172 SP")
        self.assertEqual(c172["nb_vols"], 2)
        self.assertAlmostEqual(c172["conso_l_per_nm"], (61.0 / 305.0), places=4)
        self.assertAlmostEqual(c172["conso_l_per_h"], 61.0 / (7260.0 / 3600.0), places=2)
        g = stats["global"]
        self.assertEqual(g["nb_vols"], 3)
        self.assertAlmostEqual(g["conso_l_per_nm"], (181.0 / 505.0), places=4)

    def test_missing_file_raises(self):
        with self.assertRaises(SourceError):
            CsvSource("/chemin/inexistant.csv").fetch()

    def test_bad_header_raises(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as f:
            f.write(CSV_BAD)
            path = f.name
        with self.assertRaises(SourceError):
            CsvSource(path).fetch()


class TestHttpSource(unittest.TestCase):
    def test_fetch_parses_api_json(self):
        payload = SAMPLE_JSON.read_bytes()
        with mock.patch.object(urllib.request, "urlopen",
                               return_value=_FakeResponse(payload)) as m:
            stats = HttpSource("https://www.skywings.ovh").fetch()
        self.assertTrue(m.called)
        url = m.call_args[0][0].full_url
        self.assertEqual(url, "https://www.skywings.ovh/api/api_fuel_stats.php")
        self.assertEqual(len(stats["fleet_types"]), 5)
        self.assertEqual(stats["prix_litre"], 0.88)

    def test_api_error_payload_raises(self):
        with mock.patch.object(urllib.request, "urlopen",
                               return_value=_FakeResponse(json.dumps({"error": "boom"}).encode())):
            with self.assertRaises(SourceError):
                HttpSource("https://x").fetch()

    def test_network_failure_raises_source_error(self):
        with mock.patch.object(urllib.request, "urlopen", side_effect=OSError("no route")):
            with self.assertRaises(SourceError):
                HttpSource("https://x").fetch()


class TestSampleSource(unittest.TestCase):
    def test_loads_embedded_sample(self):
        stats = SampleSource().fetch()
        self.assertGreaterEqual(len(stats["fleet_types"]), 4)
        self.assertIsNotNone(stats["global"]["conso_l_per_nm"])


if __name__ == "__main__":
    unittest.main()
