"""
Tests for the Flask endpoints in server.py
- /data, /history, /route (including error paths)
The OSRM HTTP request is mocked so tests are network-free.

Run:
    python -m pytest tests/test_routes.py -v
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import server


def osrm_ok_response():
    return {
        "code": "Ok",
        "routes": [{
            "distance": 12345.0,
            "duration": 678.0,
            "legs": [{
                "steps": [
                    {"maneuver": {"type": "depart"}, "name": "Main St", "distance": 500},
                    {"maneuver": {"type": "turn", "modifier": "left"}, "name": "2nd Ave", "distance": 1200},
                    {"maneuver": {"type": "arrive"}, "name": "", "distance": 0},
                ]
            }],
            "geometry": {"coordinates": [[78.0, 17.0], [78.1, 17.1], [78.2, 17.2]]},
        }],
    }


class FlaskRouteTests(unittest.TestCase):

    def setUp(self):
        server.app.config["TESTING"] = True
        self.client = server.app.test_client()
        with server.data_lock:
            server.latest_data.update({
                "lat": "", "lng": "",
                "msg": "Waiting for LoRa data...",
                "rssi": "N/A", "seq": None, "dropped": 0,
            })
            server.gps_history.clear()

    def test_data_returns_initial_state(self):
        resp = self.client.get("/data")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["lat"], "")
        self.assertEqual(body["rssi"], "N/A")
        self.assertEqual(body["dropped"], 0)
        self.assertIsNone(body["seq"])

    def test_history_empty(self):
        resp = self.client.get("/history")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"points": []})

    def test_history_after_ingest(self):
        server._ingest_line("DATA:1,17.0,78.0,hello,RSSI:-80")
        server._ingest_line("DATA:2,17.1,78.1,hello,RSSI:-81")
        resp = self.client.get("/history")
        points = resp.get_json()["points"]
        self.assertEqual(len(points), 2)
        self.assertEqual(points[0], [17.0, 78.0])

    def test_route_no_gps_yet(self):
        resp = self.client.get("/route")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["error"], "No GPS data yet")

    def test_route_invalid_cached_coords(self):
        with server.data_lock:
            server.latest_data["lat"] = "not-a-number"
            server.latest_data["lng"] = "78.0"
        resp = self.client.get("/route")
        self.assertIn("Invalid GPS coordinates", resp.get_json()["error"])

    @patch("server.requests.get")
    def test_route_osrm_timeout(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout()
        with server.data_lock:
            server.latest_data.update({"lat": "17.0", "lng": "78.0"})
        resp = self.client.get("/route")
        self.assertIn("timeout", resp.get_json()["error"].lower())

    @patch("server.requests.get")
    def test_route_osrm_connection_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError()
        with server.data_lock:
            server.latest_data.update({"lat": "17.0", "lng": "78.0"})
        resp = self.client.get("/route")
        self.assertIn("Cannot reach OSRM", resp.get_json()["error"])

    @patch("server.requests.get")
    def test_route_osrm_http_error(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_resp)
        mock_get.return_value = mock_resp
        with server.data_lock:
            server.latest_data.update({"lat": "17.0", "lng": "78.0"})
        resp = self.client.get("/route")
        self.assertIn("HTTP error", resp.get_json()["error"])

    @patch("server.requests.get")
    def test_route_osrm_invalid_json(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.side_effect = ValueError("not json")
        mock_get.return_value = mock_resp
        with server.data_lock:
            server.latest_data.update({"lat": "17.0", "lng": "78.0"})
        resp = self.client.get("/route")
        self.assertIn("invalid JSON", resp.get_json()["error"])

    @patch("server.requests.get")
    def test_route_osrm_no_route_found(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"code": "NoRoute"}
        mock_get.return_value = mock_resp
        with server.data_lock:
            server.latest_data.update({"lat": "17.0", "lng": "78.0"})
        resp = self.client.get("/route")
        self.assertIn("NoRoute", resp.get_json()["error"])

    @patch("server.requests.get")
    def test_route_osrm_malformed_payload(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"code": "Ok"}
        mock_get.return_value = mock_resp
        with server.data_lock:
            server.latest_data.update({"lat": "17.0", "lng": "78.0"})
        resp = self.client.get("/route")
        self.assertIn("no routes", resp.get_json()["error"])

    @patch("server.requests.get")
    def test_route_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = osrm_ok_response()
        mock_get.return_value = mock_resp
        with server.data_lock:
            server.latest_data.update({"lat": "17.0", "lng": "78.0"})
        resp = self.client.get("/route")
        body = resp.get_json()
        self.assertNotIn("error", body)
        self.assertEqual(body["distance"], "12.3 km")
        self.assertEqual(body["duration"], "11 min")
        self.assertGreaterEqual(len(body["steps"]), 3)
        self.assertEqual(body["geometry"][0], [17.0, 78.0])


if __name__ == "__main__":
    unittest.main()
