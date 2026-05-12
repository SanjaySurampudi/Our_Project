"""
LoRa GPS Tracker – Flask back-end
Fixes applied:
  • RECEIVER_LAT/LNG exposed as env-vars (HIGH improvement)
  • /route returns proper HTTP status codes 503/422/200 (MEDIUM fix)
  • MAX_HISTORY drives deque maxlen (LOW fix)
  • Negative seq-number explicitly rejected (LOW fix)
  • node_id key added to packet for future multi-node support (future scope)
  • read_serial() accepts optional max_retries for testability (HIGH test fix)
"""

import os
import re
import time
import threading
import logging
from collections import deque

import serial
import serial.tools.list_ports
import requests
from flask import Flask, jsonify, render_template, request

# ---------------------------------------------------------------------------
# Configuration – override via environment variables for easy deployment
# ---------------------------------------------------------------------------
RECEIVER_LAT = float(os.environ.get("RECEIVER_LAT", "17.3850"))   # default Hyderabad
RECEIVER_LNG = float(os.environ.get("RECEIVER_LNG", "78.4867"))
MAX_HISTORY   = int(os.environ.get("MAX_HISTORY", "500"))
SERIAL_BAUD   = int(os.environ.get("SERIAL_BAUD", "9600"))
OSRM_HOST     = os.environ.get("OSRM_HOST", "http://router.project-osrm.org")
OSRM_TIMEOUT  = int(os.environ.get("OSRM_TIMEOUT", "5"))

# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)

# Shared state
data_lock    = threading.Lock()
latest_data  = {}                                   # keyed by node_id for multi-node readiness
gps_history  = deque(maxlen=MAX_HISTORY)            # single-node history (node "default")

# ---------------------------------------------------------------------------
# Packet helpers
# ---------------------------------------------------------------------------

def is_valid(line: str) -> bool:
    """
    Return True when *line* is a well-formed DATA packet.

    Packet formats supported:
      Legacy  : lat,lng,msg,RSSI:val
      Sequence: seq,lat,lng,alt,speed,heading,msg,RSSI:val   (seq >= 0)

    Rejects negative sequence numbers immediately instead of letting
    the legacy-format path silently misinterpret them.
    """
    line = line.strip()
    if not line:
        return False

    parts = line.split(",")

    # --- detect sequence-number prefix ---
    has_seq = False
    try:
        seq_val = int(parts[0])
        # Explicit rejection: negative integers are never valid seq numbers
        if seq_val < 0:
            log.debug("Rejected packet with negative seq: %s", line)
            return False
        has_seq = True
    except ValueError:
        pass  # no seq prefix → legacy format

    if has_seq:
        # seq, lat, lng, alt, speed, heading, msg, RSSI:val  → 8 fields minimum
        if len(parts) < 8:
            return False
        lat_idx, lng_idx, rssi_part = 1, 2, parts[-1]
    else:
        # lat, lng, msg, RSSI:val  → 4 fields minimum
        if len(parts) < 4:
            return False
        lat_idx, lng_idx, rssi_part = 0, 1, parts[-1]

    # Validate lat / lng ranges
    try:
        lat = float(parts[lat_idx])
        lng = float(parts[lng_idx])
    except ValueError:
        return False

    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        return False

    # Validate RSSI field  →  must end with  RSSI:<int>
    if not re.match(r"^RSSI:-?\d+$", rssi_part.strip()):
        return False

    return True


def parse_packet(line: str) -> dict:
    """Parse a validated DATA packet into a dict."""
    parts = line.strip().split(",")

    try:
        seq_val = int(parts[0])
        has_seq = seq_val >= 0
    except ValueError:
        has_seq = False

    rssi = int(parts[-1].split(":")[1])

    if has_seq:
        seq, lat, lng = int(parts[0]), float(parts[1]), float(parts[2])
        alt     = float(parts[3]) if parts[3] else None
        speed   = float(parts[4]) if parts[4] else None
        heading = float(parts[5]) if parts[5] else None
        msg     = ",".join(parts[6:-1])
        node_id = "default"
        return dict(seq=seq, lat=lat, lng=lng, alt=alt, speed=speed,
                    heading=heading, msg=msg, rssi=rssi,
                    node_id=node_id, timestamp=time.time())
    else:
        lat, lng = float(parts[0]), float(parts[1])
        msg = ",".join(parts[2:-1])
        return dict(lat=lat, lng=lng, msg=msg, rssi=rssi,
                    node_id="default", timestamp=time.time())


def _ingest_line(line: str) -> None:
    """Validate, parse, and store one serial line."""
    line = line.strip()
    if not line:
        return
    if not is_valid(line):
        log.debug("Ignored invalid line: %r", line)
        return
    packet = parse_packet(line)
    with data_lock:
        latest_data.update(packet)
        gps_history.append(packet)
    log.info("Ingested packet: %.5f, %.5f  RSSI=%d",
             packet["lat"], packet["lng"], packet["rssi"])


# ---------------------------------------------------------------------------
# Serial reader
# ---------------------------------------------------------------------------

def _autodetect_port() -> str | None:
    """Return first likely USB-serial port or None."""
    candidates = [
        p.device for p in serial.tools.list_ports.comports()
        if any(k in (p.description or "").lower()
               for k in ("usb", "uart", "ch340", "cp210", "ftdi", "arduino"))
    ]
    return candidates[0] if candidates else None


def read_serial(port: str = None, baud: int = SERIAL_BAUD,
                max_retries: int = None) -> None:
    """
    Background thread: continuously read from serial port.

    max_retries – if not None, stop polling after this many consecutive
                  port-not-found attempts (used in tests to avoid infinite loop).
    """
    fail_count  = 0
    retry_count = 0

    while True:
        resolved = port or _autodetect_port()
        if not resolved:
            log.warning("No serial port found; retrying in 10 s …")
            if max_retries is not None:
                retry_count += 1
                if retry_count >= max_retries:
                    log.info("read_serial: reached max_retries=%d, exiting.", max_retries)
                    return
            time.sleep(10)
            continue

        retry_count = 0   # reset on successful detection
        try:
            with serial.Serial(resolved, baud, timeout=2) as ser:
                log.info("Serial opened: %s @ %d", resolved, baud)
                fail_count = 0
                while True:
                    raw = ser.readline()
                    if raw:
                        _ingest_line(raw.decode("utf-8", errors="replace"))
        except serial.SerialException as exc:
            fail_count += 1
            log.error("Serial error (%d/5): %s", fail_count, exc)
            if fail_count >= 5:
                log.warning("5 consecutive failures – forcing port re-detection.")
                port = None
                fail_count = 0
            time.sleep(3)


# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html",
                           receiver_lat=RECEIVER_LAT,
                           receiver_lng=RECEIVER_LNG)


@app.route("/data")
def data():
    with data_lock:
        return jsonify(dict(latest_data))


@app.route("/history")
def history():
    with data_lock:
        return jsonify(list(gps_history))


@app.route("/route")
def route():
    """
    Return OSRM driving route from GPS position to receiver.

    HTTP status codes:
      200  – route found  OR  soft error the front-end should handle
             gracefully (no GPS fix yet, route not found by OSRM)
      422  – coordinates in cache are geometrically invalid
      503  – OSRM service is unreachable / timed-out / returned bad data
    """
    with data_lock:
        snap = dict(latest_data)

    if not snap:
        return jsonify({"error": "no_gps_yet",
                        "message": "Waiting for first GPS fix."}), 200

    lat, lng = snap.get("lat"), snap.get("lng")

    # Validate cached coordinates before hitting OSRM
    try:
        lat, lng = float(lat), float(lng)
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_coordinates",
                        "message": "Cached GPS coordinates are out of range."}), 422

    url = (f"{OSRM_HOST}/route/v1/driving/"
           f"{lng},{lat};{RECEIVER_LNG},{RECEIVER_LAT}"
           f"?overview=full&geometries=geojson")
    try:
        resp = requests.get(url, timeout=OSRM_TIMEOUT)
        resp.raise_for_status()
        osrm = resp.json()
    except requests.exceptions.Timeout:
        return jsonify({"error": "osrm_timeout",
                        "message": "OSRM request timed out."}), 503
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "osrm_connection_error",
                        "message": "Cannot reach OSRM server."}), 503
    except requests.exceptions.HTTPError as exc:
        return jsonify({"error": "osrm_http_error",
                        "message": str(exc)}), 503
    except ValueError:
        return jsonify({"error": "osrm_json_error",
                        "message": "OSRM returned non-JSON response."}), 503

    if osrm.get("code") != "Ok" or not osrm.get("routes"):
        return jsonify({"error": "route_not_found",
                        "message": "OSRM could not find a route."}), 200

    route_data = osrm["routes"][0]
    return jsonify({
        "geometry":  route_data["geometry"],
        "distance":  route_data["distance"],
        "duration":  route_data["duration"],
    }), 200


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    t = threading.Thread(target=read_serial, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=5000, debug=False)
