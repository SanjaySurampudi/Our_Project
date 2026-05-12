"""
LoRa Long Distance Tracker - Flask Server

Reads LoRa packets from the receiver Arduino over USB serial and renders
a live web dashboard with map, road route, straight-line distance, and
GPS track history.

Packet format (new, with sequence number):
    DATA:<seq>,<lat>,<lng>,<msg>,RSSI:<value>

Legacy format (still accepted):
    DATA:<lat>,<lng>,<msg>,RSSI:<value>

Dependencies:
    pip install pyserial flask requests

Run:
    python server.py
    Open http://localhost:5000

Security note:
    By default, the server binds to 127.0.0.1 (localhost only) for
    local development. If you need LAN access (e.g., viewing the
    dashboard from a phone on the same WiFi), set the environment
    variable FLASK_HOST=0.0.0.0 before running. Be aware that this
    exposes /data and /history endpoints without authentication to
    anyone on your local network.

Selecting the serial port (priority order):
    1. LORA_PORT environment variable (highest priority - explicit override):
         Linux/macOS:  export LORA_PORT=/dev/ttyUSB0
         Windows:      set LORA_PORT=COM11
    2. Auto-detection by USB descriptor (Arduino / CH340 / CP210 /
       FTDI / USB Serial / ttyUSB / ttyACM).
    3. If neither yields a port, the server prints a clear error
       listing the available ports and the web dashboard keeps
       running (showing "Waiting for LoRa data...").
"""
# ---- SET YOUR RECEIVER FIXED LOCATION HERE ----
RECEIVER_LAT = 17.087741
RECEIVER_LNG = 82.068771
# ------------------------------------------------
import os
import threading
import time
import serial
import serial.tools.list_ports
import requests
from collections import deque
from flask import Flask, render_template, jsonify

app = Flask(__name__)

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

# ---- SET YOUR RECEIVER FIXED LOCATION HERE ----
RECEIVER_LAT = 17.087741
RECEIVER_LNG = 82.068771
# ------------------------------------------------


# =====================================================================
#  Packet parsing helpers
# =====================================================================

def is_valid(line):
    """
    Validate a DATA: line before parsing.

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
        return False


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

    return {
        "seq": None,
        "lat": parts[0].strip(),
        "lng": parts[1].strip(),
        "msg": parts[2].strip(),
        "rssi": rssi_str.strip(),
    }


# =====================================================================
#  Flask routes
# =====================================================================

@app.route('/')
def index():
    return render_template(
        'index.html',
        rx_lat=RECEIVER_LAT,
        rx_lng=RECEIVER_LNG
    )


@app.route('/data')
def data():
    with data_lock:
        return jsonify(latest_data)


@app.route('/history')
def history():
    with data_lock:
        return jsonify({"points": list(gps_history)})


@app.route('/route')
def get_route():

    with data_lock:
        lat_s = latest_data['lat']
        lng_s = latest_data['lng']

    if not lat_s or not lng_s:
        return jsonify({"error": "No GPS data yet"}), 200

    try:
        tx_lat = float(lat_s)
        tx_lng = float(lng_s)

    except (TypeError, ValueError):
        return jsonify({"error": "Invalid GPS coordinates in cache"}), 200

    try:
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


# =====================================================================
#  Serial reader thread
# =====================================================================

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
