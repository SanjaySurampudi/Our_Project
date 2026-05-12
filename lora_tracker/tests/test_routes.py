"""
test_routes.py – Flask route tests for server.py

Covers all /data /history /route scenarios including new HTTP status codes:
  • 503 for OSRM connectivity failures
  • 422 for invalid cached coordinates
  • 200 for soft errors (no GPS yet, route not found)
  • 200 for successful route
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch, MagicMock
import requests as req_lib

import server
from server import app, gps_history, data_lock

# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_state():
    """Reset shared state before each test."""
    with data_lock:
        server.latest_data.clear()
        gps_history.clear()
    yield
    with data_lock:
        server.latest_data.clear()
        gps_history.clear()


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _set_gps(lat=17.385, lng=78.486, rssi=-65):
    with data_lock:
        server.latest_data.update({"lat": lat, "lng": lng,
                                   "rssi": rssi, "msg": "test",
                                   "node_id": "default"})

# ── /data ─────────────────────────────────────────────────────────────────

def test_data_empty(client):
    r = client.get("/data")
    assert r.status_code == 200
    assert r.get_json() == {}

def test_data_populated(client):
    _set_gps()
    r = client.get("/data")
    d = r.get_json()
    assert d["lat"] == pytest.approx(17.385, rel=1e-4)
    assert d["rssi"] == -65

# ── /history ──────────────────────────────────────────────────────────────

def test_history_empty(client):
    r = client.get("/history")
    assert r.get_json() == []

def test_history_populated(client):
    with data_lock:
        gps_history.append({"lat": 17.0, "lng": 78.0, "rssi": -70})
        gps_history.append({"lat": 17.1, "lng": 78.1, "rssi": -68})
    r = client.get("/history")
    hist = r.get_json()
    assert len(hist) == 2
    assert hist[0]["lat"] == pytest.approx(17.0)

# ── /route – soft 200 errors ──────────────────────────────────────────────

def test_route_no_gps_returns_200(client):
    r = client.get("/route")
    assert r.status_code == 200
    assert r.get_json()["error"] == "no_gps_yet"

def test_route_not_found_osrm_returns_200(client):
    _set_gps()
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"code": "NoRoute", "routes": []}
    with patch("server.requests.get", return_value=mock_resp):
        r = client.get("/route")
    assert r.status_code == 200
    assert r.get_json()["error"] == "route_not_found"

# ── /route – 422 invalid coordinates ─────────────────────────────────────

def test_route_invalid_lat_returns_422(client):
    with data_lock:
        server.latest_data.update({"lat": 999, "lng": 78.0})
    r = client.get("/route")
    assert r.status_code == 422
    assert r.get_json()["error"] == "invalid_coordinates"

def test_route_invalid_lng_returns_422(client):
    with data_lock:
        server.latest_data.update({"lat": 17.0, "lng": -999})
    r = client.get("/route")
    assert r.status_code == 422

# ── /route – 503 OSRM failures ────────────────────────────────────────────

def test_route_osrm_timeout_returns_503(client):
    _set_gps()
    with patch("server.requests.get", side_effect=req_lib.exceptions.Timeout):
        r = client.get("/route")
    assert r.status_code == 503
    assert r.get_json()["error"] == "osrm_timeout"

def test_route_osrm_connection_error_returns_503(client):
    _set_gps()
    with patch("server.requests.get", side_effect=req_lib.exceptions.ConnectionError):
        r = client.get("/route")
    assert r.status_code == 503
    assert r.get_json()["error"] == "osrm_connection_error"

def test_route_osrm_http_error_returns_503(client):
    _set_gps()
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = req_lib.exceptions.HTTPError("404")
    with patch("server.requests.get", return_value=mock_resp):
        r = client.get("/route")
    assert r.status_code == 503
    assert r.get_json()["error"] == "osrm_http_error"

def test_route_osrm_json_error_returns_503(client):
    _set_gps()
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.side_effect = ValueError("bad JSON")
    with patch("server.requests.get", return_value=mock_resp):
        r = client.get("/route")
    assert r.status_code == 503
    assert r.get_json()["error"] == "osrm_json_error"

# ── /route – 200 success ──────────────────────────────────────────────────

def test_route_success_returns_200(client):
    _set_gps()
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "code": "Ok",
        "routes": [{
            "geometry": {"type": "LineString", "coordinates": [[78.486, 17.385], [78.487, 17.386]]},
            "distance": 1234.5,
            "duration": 300.0
        }]
    }
    with patch("server.requests.get", return_value=mock_resp):
        r = client.get("/route")
    assert r.status_code == 200
    data = r.get_json()
    assert "geometry" in data
    assert data["distance"] == pytest.approx(1234.5)
    assert data["duration"] == pytest.approx(300.0)
