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
# ---- SET YOUR RECEIVER FIXED LOCATION HERE ----
RECEIVER_LAT = 17.087741
RECEIVER_LNG = 82.068771
# ------------------------------------------------
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

<<<<<<< HEAD
# Shared state
data_lock    = threading.Lock()
latest_data  = {}                                   # keyed by node_id for multi-node readiness
gps_history  = deque(maxlen=MAX_HISTORY)            # single-node history (node "default")
=======
# Shared state (protected by data_lock)
data_lock = threading.Lock()

latest_data = {
    "lat": "",
    "lng": "",
    "msg": "Waiting for LoRa data...",
    "rssi": "N/A",
    "seq": None,
    "dropped": 0,
}

gps_history = deque(maxlen=500)
MAX_HISTORY = 500
>>>>>>> 549e0e2108c186d6eadcec739bf2058fb919d1fb

# ---------------------------------------------------------------------------
# Packet helpers
# ---------------------------------------------------------------------------

<<<<<<< HEAD
def is_valid(line: str) -> bool:
=======

# =====================================================================
#  Packet parsing helpers
# =====================================================================

def is_valid(line):
>>>>>>> 549e0e2108c186d6eadcec739bf2058fb919d1fb
    """
    Return True when *line* is a well-formed DATA packet.

<<<<<<< HEAD
    Packet formats supported:
      Legacy  : lat,lng,msg,RSSI:val
      Sequence: seq,lat,lng,alt,speed,heading,msg,RSSI:val   (seq >= 0)

    Rejects negative sequence numbers immediately instead of letting
    the legacy-format path silently misinterpret them.
    """
    line = line.strip()
    if not line:
=======
    Accepts:
        DATA:<seq>,<lat>,<lng>,<msg>,RSSI:<value>
        DATA:<lat>,<lng>,<msg>,RSSI:<value>
    """

    if not isinstance(line, str) or not line.startswith("DATA:"):
        return False

    try:
        body = line[5:]

        if ",RSSI:" not in body:
            return False

        body, rssi_str = body.split(",RSSI:", 1)

        int(rssi_str.strip())

        parts = body.split(",", 3)

        has_seq = False

        if len(parts) >= 4:
            try:
                seq_val = int(parts[0])

                if seq_val >= 0:
                    has_seq = True

            except ValueError:
                has_seq = False

        if has_seq:
            lat_s, lng_s, msg_s = parts[1], parts[2], parts[3]
        else:
            if len(parts) < 3:
                return False

            lat_s, lng_s, msg_s = parts[0], parts[1], parts[2]

        lat = float(lat_s)
        lng = float(lng_s)

        return (
            (-90 <= lat <= 90)
            and (-180 <= lng <= 180)
            and len(msg_s.strip()) > 0
        )

    except Exception:
>>>>>>> 549e0e2108c186d6eadcec739bf2058fb919d1fb
        return False

    parts = line.split(",")

<<<<<<< HEAD
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
=======
def parse_packet(line):
    """
    Parse a validated DATA: line.
    Returns:
        {seq, lat, lng, msg, rssi}
    """

    body = line[5:]
    body, rssi_str = body.split(",RSSI:", 1)

    parts = body.split(",", 3)

    has_seq = False

    if len(parts) >= 4:
        try:
            int(parts[0])
            has_seq = True
        except ValueError:
            has_seq = False

    if has_seq:
        return {
            "seq": int(parts[0]),
            "lat": parts[1].strip(),
            "lng": parts[2].strip(),
            "msg": parts[3].strip(),
            "rssi": rssi_str.strip(),
        }
>>>>>>> 549e0e2108c186d6eadcec739bf2058fb919d1fb

    return {
        "seq": None,
        "lat": parts[0].strip(),
        "lng": parts[1].strip(),
        "msg": parts[2].strip(),
        "rssi": rssi_str.strip(),
    }


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
<<<<<<< HEAD
    return render_template("index.html",
                           receiver_lat=RECEIVER_LAT,
                           receiver_lng=RECEIVER_LNG)
=======
    return render_template(
        'index.html',
        rx_lat=RECEIVER_LAT,
        rx_lng=RECEIVER_LNG
    )
>>>>>>> 549e0e2108c186d6eadcec739bf2058fb919d1fb


@app.route("/data")
def data():
    with data_lock:
        return jsonify(dict(latest_data))


@app.route("/history")
def history():
    with data_lock:
        return jsonify(list(gps_history))


<<<<<<< HEAD
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
=======
@app.route('/route')
def get_route():

>>>>>>> 549e0e2108c186d6eadcec739bf2058fb919d1fb
    with data_lock:
        snap = dict(latest_data)

    if not snap:
        return jsonify({"error": "no_gps_yet",
                        "message": "Waiting for first GPS fix."}), 200

    lat, lng = snap.get("lat"), snap.get("lng")

    # Validate cached coordinates before hitting OSRM
    try:
<<<<<<< HEAD
        lat, lng = float(lat), float(lng)
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            raise ValueError
=======
        tx_lat = float(lat_s)
        tx_lng = float(lng_s)

>>>>>>> 549e0e2108c186d6eadcec739bf2058fb919d1fb
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_coordinates",
                        "message": "Cached GPS coordinates are out of range."}), 422

    url = (f"{OSRM_HOST}/route/v1/driving/"
           f"{lng},{lat};{RECEIVER_LNG},{RECEIVER_LAT}"
           f"?overview=full&geometries=geojson")
    try:
<<<<<<< HEAD
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
=======
        url = (
            f"http://router.project-osrm.org/route/v1/driving/"
            f"{tx_lng},{tx_lat};{RECEIVER_LNG},{RECEIVER_LAT}"
            f"?overview=full&geometries=geojson&steps=true"
        )

        resp = requests.get(url, timeout=15)
        resp.raise_for_status()

        result = resp.json()

    except requests.exceptions.Timeout:
        return jsonify({"error": "OSRM timeout - check internet connection"}), 200

    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Cannot reach OSRM (no internet?)"}), 200

    except requests.exceptions.HTTPError as e:
        return jsonify(
            {"error": f"OSRM HTTP error: {e.response.status_code}"}
        ), 200

    except ValueError:
        return jsonify({"error": "OSRM returned invalid JSON"}), 200

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Network error: {e}"}), 200

    try:
        if result.get('code') != 'Ok':
            return jsonify(
                {"error": "OSRM error: " + result.get('code', 'unknown')}
            ), 200

        if not result.get('routes'):
            return jsonify({"error": "OSRM returned no routes"}), 200

        route = result['routes'][0]

        dist_m = route['distance']
        dur_s = route['duration']

        dist_str = (
            f"{dist_m/1000:.1f} km"
            if dist_m >= 1000
            else f"{dist_m:.0f} m"
        )

        if dur_s >= 3600:
            dur_str = f"{int(dur_s//3600)}h {int((dur_s%3600)//60)}m"

        elif dur_s >= 60:
            dur_str = f"{int(dur_s//60)} min"

        else:
            dur_str = f"{int(dur_s)} sec"

        steps = []

        for leg in route.get('legs', []):
            for step in leg.get('steps', []):

                maneuver = step.get('maneuver', {})

                typ = maneuver.get('type', '')
                mod = maneuver.get('modifier', '')

                name = step.get('name', '')
                dist = step.get('distance', 0)

                if typ == 'depart':
                    txt = f"Start on {name}" if name else "Depart"

                elif typ == 'arrive':
                    txt = "Arrive at destination"

                elif mod:
                    txt = f"Turn {mod}"
                    if name:
                        txt += f" onto {name}"

                else:
                    txt = typ.capitalize()
                    if name:
                        txt += f" on {name}"

                if dist > 0:
                    d_str = (
                        f"{dist/1000:.1f} km"
                        if dist >= 1000
                        else f"{dist:.0f} m"
                    )

                    txt += f" ({d_str})"

                steps.append(txt)

        coords = route.get('geometry', {}).get('coordinates', [])

        geometry = [[c[1], c[0]] for c in coords]

        return jsonify({
            "distance": dist_str,
            "duration": dur_str,
            "steps": steps,
            "geometry": geometry,
            "tx_lat": tx_lat,
            "tx_lng": tx_lng,
        })

    except (KeyError, IndexError, TypeError, ValueError) as e:
        return jsonify({"error": f"Malformed OSRM response: {e}"}), 200
>>>>>>> 549e0e2108c186d6eadcec739bf2058fb919d1fb


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

<<<<<<< HEAD
if __name__ == "__main__":
    t = threading.Thread(target=read_serial, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=5000, debug=False)
=======
def _ingest_line(line):
    """
    Validate + parse a single line and update shared state.
    """

    if not line.startswith("DATA:"):
        return None

    if not is_valid(line):
        return None

    pkt = parse_packet(line)

    with data_lock:

        # ---- dropped-packet detection ----
        prev_seq = latest_data.get('seq')

        if pkt['seq'] is not None and prev_seq is not None:

            gap = pkt['seq'] - prev_seq - 1

            if gap > 0:
                latest_data['dropped'] += gap

        latest_data['lat'] = pkt['lat']
        latest_data['lng'] = pkt['lng']
        latest_data['msg'] = pkt['msg']
        latest_data['rssi'] = pkt['rssi']
        latest_data['seq'] = pkt['seq']

        try:
            gps_history.append([
                float(pkt['lat']),
                float(pkt['lng'])
            ])

        except ValueError:
            pass

    return pkt


def _autodetect_port():
    """
    Return the first matching USB serial port.
    """

    keywords = [
        'Arduino',
        'CH340',
        'CP210',
        'FTDI',
        'USB Serial',
        'wchusbserial',
        'ttyUSB',
        'ttyACM'
    ]

    for p in serial.tools.list_ports.comports():

        desc = (p.description or "") + " " + (p.device or "")

        if any(k.lower() in desc.lower() for k in keywords):
            return p.device

    return None


def _resolve_port(port_override=None):

    if port_override:
        return port_override

    env_port = os.environ.get('LORA_PORT')

    if env_port:
        return env_port

    return _autodetect_port()


def _list_available_ports():

    ports = list(serial.tools.list_ports.comports())

    if not ports:
        return "  (no serial devices currently visible to the OS)"

    return "\n".join(
        f"  - {p.device}  ({p.description or 'no description'})"
        for p in ports
    )


def read_serial(port_override=None):
    """
    Background thread:
    Reads packets from the receiver Arduino over USB.
    """

    PORT = _resolve_port(port_override)

    if PORT is None:

        print("=" * 60)
        print("  ERROR: Could not auto-detect the LoRa receiver.")
        print("  No port matched.")
        print()

        print("  Available serial ports right now:")
        print(_list_available_ports())
        print()

        print("  Fix one of these and restart:")
        print("    1. Plug in the Arduino and try again")
        print("    2. Set LORA_PORT manually")
        print()

        print("  The dashboard will keep running.")
        print("=" * 60)

        while True:

            time.sleep(10)

            PORT = _resolve_port(port_override)

            if PORT is not None:
                print(f"  ✓ Arduino detected on {PORT} - connecting...")
                break

            print("  Still waiting for Arduino...")

    print(f"Connecting to {PORT}...")

    consecutive_failures = 0

    while True:

        try:
            ser = serial.Serial(PORT, 9600, timeout=2)

            print(f"Connected to {PORT} - waiting for data...")

            consecutive_failures = 0

            while True:

                raw = ser.readline()

                # Detect graceful disconnect
                if raw == b'':
                    raise serial.SerialException(
                        "Port returned empty read — graceful disconnect detected"
                    )

                line = raw.decode(
                    'utf-8',
                    errors='ignore'
                ).strip()

                if not line:
                    continue

                pkt = _ingest_line(line)

                if pkt is None:

                    if line.startswith("DATA:"):
                        print(f"  Skipped (corrupted): {line}")

                    continue

                print(
                    f"  seq={pkt['seq']} "
                    f"lat={pkt['lat']} "
                    f"lng={pkt['lng']} "
                    f"rssi={pkt['rssi']} | "
                    f"history={len(gps_history)} pts "
                    f"dropped={latest_data['dropped']}"
                )

        except serial.SerialException as e:

            consecutive_failures += 1

            print(
                f"Serial error on {PORT}: {e} "
                f"- retry in 4s "
                f"(attempt {consecutive_failures})"
            )

            if consecutive_failures >= 5 and port_override is None:

                new_port = _resolve_port()

                if new_port and new_port != PORT:

                    print(f"  Re-detected port: {new_port} (was {PORT})")

                    PORT = new_port
                    consecutive_failures = 0

            time.sleep(4)


def _start_serial_thread():
    threading.Thread(
        target=read_serial,
        daemon=True
    ).start()


# =====================================================================
#  Main
# =====================================================================

if __name__ == '__main__':

    print("=" * 50)
    print("  LoRa Long Distance Tracker")
    print("  Open http://localhost:5000")
    print("=" * 50)

    host = os.environ.get('FLASK_HOST', '127.0.0.1')

    if host != '127.0.0.1':

        print(f"  WARNING: Binding to {host}")
        print("  Dashboard accessible on LAN")
        print("=" * 50)

    _start_serial_thread()

    app.run(
        host=host,
        port=5000,
        debug=False
    )
>>>>>>> 549e0e2108c186d6eadcec739bf2058fb919d1fb
