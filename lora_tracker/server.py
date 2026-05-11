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
"""

import threading
import time
import serial
import serial.tools.list_ports
import requests
from flask import Flask, render_template, jsonify

app = Flask(__name__)

# Shared state (protected by data_lock)
data_lock   = threading.Lock()
latest_data = {
    "lat":     "",
    "lng":     "",
    "msg":     "Waiting for LoRa data...",
    "rssi":    "N/A",
    "seq":     None,
    "dropped": 0,
}
gps_history = []        # past TX coordinates
MAX_HISTORY = 500       # keep last 500 points

# ---- SET YOUR RECEIVER FIXED LOCATION HERE ----
RECEIVER_LAT = 17.087741
RECEIVER_LNG = 82.068771
# ------------------------------------------------


# =====================================================================
#  Packet parsing helpers (importable for unit tests)
# =====================================================================

def is_valid(line):
    """
    Validate a DATA: line before parsing.

    Accepts:
        DATA:<seq>,<lat>,<lng>,<msg>,RSSI:<value>     (new)
        DATA:<lat>,<lng>,<msg>,RSSI:<value>           (legacy)
    """
    if not isinstance(line, str) or not line.startswith("DATA:"):
        return False
    try:
        body = line[5:]

        # RSSI suffix is mandatory; strip it before splitting fields
        if ",RSSI:" not in body:
            return False
        body, rssi_str = body.split(",RSSI:", 1)
        int(rssi_str.strip())            # RSSI must be integer

        # Split into at most 4 fields so the message can contain spaces
        parts = body.split(",", 3)

        # Detect whether a sequence number is present (1st field is int)
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
        return (-90 <= lat <= 90) and (-180 <= lng <= 180) and len(msg_s.strip()) > 0

    except Exception:
        return False


def parse_packet(line):
    """
    Parse a validated DATA: line. Returns dict:
        {seq, lat, lng, msg, rssi}
    seq is int or None (legacy packets).
    Caller MUST ensure is_valid(line) is True.
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
            "seq":  int(parts[0]),
            "lat":  parts[1].strip(),
            "lng":  parts[2].strip(),
            "msg":  parts[3].strip(),
            "rssi": rssi_str.strip(),
        }
    else:
        return {
            "seq":  None,
            "lat":  parts[0].strip(),
            "lng":  parts[1].strip(),
            "msg":  parts[2].strip(),
            "rssi": rssi_str.strip(),
        }


# =====================================================================
#  Flask routes
# =====================================================================

@app.route('/')
def index():
    return render_template('index.html', rx_lat=RECEIVER_LAT, rx_lng=RECEIVER_LNG)


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
        return jsonify({"error": f"OSRM HTTP error: {e.response.status_code}"}), 200
    except ValueError:
        return jsonify({"error": "OSRM returned invalid JSON"}), 200
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Network error: {e}"}), 200

    try:
        if result.get('code') != 'Ok':
            return jsonify({"error": "OSRM error: " + result.get('code', 'unknown')}), 200

        if not result.get('routes'):
            return jsonify({"error": "OSRM returned no routes"}), 200

        route  = result['routes'][0]
        dist_m = route['distance']
        dur_s  = route['duration']

        dist_str = f"{dist_m/1000:.1f} km" if dist_m >= 1000 else f"{dist_m:.0f} m"

        if dur_s >= 3600:
            dur_str = f"{int(dur_s//3600)}h {int((dur_s%3600)//60)}m"
        elif dur_s >= 60:
            dur_str = f"{int(dur_s//60)} min"
        else:
            dur_str = f"{int(dur_s)} sec"

        steps = []
        for leg in route.get('legs', []):
            for step in leg.get('steps', []):
                m    = step.get('maneuver', {})
                typ  = m.get('type', '')
                mod  = m.get('modifier', '')
                name = step.get('name', '')
                dist = step.get('distance', 0)
                if typ == 'depart':
                    txt = f"Start on {name}" if name else "Depart"
                elif typ == 'arrive':
                    txt = "Arrive at destination"
                elif mod:
                    txt = f"Turn {mod}" + (f" onto {name}" if name else "")
                else:
                    txt = typ.capitalize() + (f" on {name}" if name else "")
                if dist > 0:
                    d_str = f"{dist/1000:.1f} km" if dist >= 1000 else f"{dist:.0f} m"
                    txt  += f" ({d_str})"
                steps.append(txt)

        coords   = route.get('geometry', {}).get('coordinates', [])
        geometry = [[c[1], c[0]] for c in coords]

        return jsonify({
            "distance": dist_str,
            "duration": dur_str,
            "steps":    steps,
            "geometry": geometry,
        })

    except (KeyError, IndexError, TypeError, ValueError) as e:
        return jsonify({"error": f"Malformed OSRM response: {e}"}), 200


# =====================================================================
#  Serial reader thread
# =====================================================================

def _ingest_line(line):
    """
    Validate + parse a single line and update shared state.
    Separated from read_serial() so unit/integration tests can call it
    without needing a real serial port.
    Returns the parsed packet dict, or None if the line was skipped.
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

        latest_data['lat']  = pkt['lat']
        latest_data['lng']  = pkt['lng']
        latest_data['msg']  = pkt['msg']
        latest_data['rssi'] = pkt['rssi']
        latest_data['seq']  = pkt['seq']

        try:
            gps_history.append([float(pkt['lat']), float(pkt['lng'])])
            if len(gps_history) > MAX_HISTORY:
                gps_history.pop(0)
        except ValueError:
            pass

    return pkt


def read_serial(port_override=None):
    """Background thread: reads packets from the receiver Arduino over USB."""
    PORT = port_override or 'COM11'
    if port_override is None:
        for p in serial.tools.list_ports.comports():
            if any(x in (p.description or "") for x in ['Arduino', 'CH340', 'USB Serial']):
                PORT = p.device
                break

    print(f"Connecting to {PORT}...")
    while True:
        try:
            ser = serial.Serial(PORT, 9600, timeout=2)
            print(f"Connected to {PORT} - waiting for data...")
            while True:
                raw  = ser.readline()
                line = raw.decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                pkt = _ingest_line(line)
                if pkt is None:
                    if line.startswith("DATA:"):
                        print(f"  Skipped (corrupted): {line}")
                    continue
                print(f"  seq={pkt['seq']} lat={pkt['lat']} lng={pkt['lng']} "
                      f"rssi={pkt['rssi']} | history={len(gps_history)} pts "
                      f"dropped={latest_data['dropped']}")

        except serial.SerialException as e:
            print(f"Serial error: {e} - retry in 4s")
            time.sleep(4)


def _start_serial_thread():
    threading.Thread(target=read_serial, daemon=True).start()


if __name__ == '__main__':
    print("=" * 50)
    print("  LoRa Long Distance Tracker")
    print("  Open http://localhost:5000")
    print("=" * 50)
    _start_serial_thread()
    app.run(host='0.0.0.0', port=5000, debug=False)
