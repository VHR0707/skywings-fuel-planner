"""Tests du serveur web local (source démo, aucune réseau)."""

import http.client
import json
import threading
import unittest

from fuelplanner.web import build_server


class TestWebServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = build_server("127.0.0.1", 0,
                                  {"base_url": "https://www.skywings.ovh",
                                   "csv_path": None, "demo": True})
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def _get(self, path):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path)
        r = conn.getresponse()
        body = r.read()
        conn.close()
        return r.status, body

    def test_index_served_with_logo(self):
        status, body = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn(b"/assets/logo.png", body)
        self.assertIn("Planificateur carburant".encode("utf-8"), body)

    def test_logo_png(self):
        status, body = self._get("/assets/logo.png")
        self.assertEqual(status, 200)
        self.assertTrue(body.startswith(b"\x89PNG"))

    def test_units_endpoint(self):
        status, body = self._get("/api/units")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual([u["code"] for u in data["units"]], ["L", "gal_imp", "gal_us", "kg"])
        self.assertEqual(data["default_unit"], "L")
        self.assertEqual(data["default_density_kg_per_l"], 0.72)

    def test_fuel_stats_demo(self):
        status, body = self._get("/api/fuel_stats")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertIn("fleet_types", data)
        self.assertIn("global", data)

    def test_compute_liters(self):
        status, body = self._get("/api/compute?fleet=Cessna%20172%20SP&nm=100&unit=L")
        self.assertEqual(status, 200)
        res = json.loads(body)
        self.assertEqual(res["unit"], "L")
        self.assertEqual(res["unit_suffix"], "L")
        self.assertAlmostEqual(res["total_l"], 34.0, places=1)
        self.assertEqual(res["total_ceil"], 34)
        self.assertFalse(res["source_fallback_global"])

    def test_compute_gal_us(self):
        status, body = self._get("/api/compute?fleet=Cessna%20172%20SP&nm=100&unit=gal_us")
        self.assertEqual(status, 200)
        res = json.loads(body)
        self.assertAlmostEqual(res["total"], res["total_l"] / 3.785411784, places=1)
        self.assertEqual(res["unit_suffix"], "gal US")

    def test_compute_kg_density(self):
        status, body = self._get("/api/compute?fleet=Cessna%20172%20SP&nm=100&unit=kg&density=0.8")
        self.assertEqual(status, 200)
        res = json.loads(body)
        self.assertAlmostEqual(res["total"], round(res["total_l"] * 0.8, 2), places=1)

    def test_compute_comma_decimal(self):
        status, body = self._get("/api/compute?fleet=Cessna%20172%20SP&nm=100,5&unit=L")
        self.assertEqual(status, 200)
        res = json.loads(body)
        self.assertAlmostEqual(res["distance_nm"], 100.5, places=1)

    def test_compute_fallback_global(self):
        status, body = self._get("/api/compute?fleet=Planeur%20ASK21&nm=50&unit=L")
        self.assertEqual(status, 200)
        res = json.loads(body)
        self.assertTrue(res["source_fallback_global"])

    def test_compute_bad_nm(self):
        status, _ = self._get("/api/compute?fleet=Cessna&nm=abc")
        self.assertEqual(status, 400)

    def test_compute_unknown_fleet(self):
        status, _ = self._get("/api/compute?fleet=Nope&nm=100")
        self.assertEqual(status, 404)

    def test_compute_bad_unit(self):
        status, _ = self._get("/api/compute?fleet=Cessna&nm=100&unit=xyz")
        self.assertEqual(status, 400)

    def test_unknown_route_404(self):
        status, _ = self._get("/nope")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
