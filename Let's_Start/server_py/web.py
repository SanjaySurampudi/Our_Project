import serial
import serial.tools.list_ports
import threading
import requests
import math
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

latest_data  = {"lat": "", "lng": "", "msg": "Waiting for LoRa data...", "rssi": "N/A"}
gps_history  = []          # stores all past TX coordinates
MAX_HISTORY  = 500         # keep last 500 points

# ---- SET YOUR RECEIVER FIXED LOCATION HERE ----
RECEIVER_LAT = 17.087741     # example: Hyderabad
RECEIVER_LNG = 82.068771
# ------------------------------------------------

HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>LoRa Long Distance Tracker</title>
  <meta charset="utf-8">
  <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css"/>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: sans-serif; background: #f0f2f5; }

    .topbar { display:flex; align-items:center; gap:10px; padding:14px 20px;
              background:white; border-bottom:1px solid #eee; }
    .topbar h2 { font-size:17px; font-weight:500; color:#222; flex:1; }
    .dot { width:10px; height:10px; background:#2ecc71; border-radius:50%;
           animation:pulse 1.5s infinite; flex-shrink:0; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }

    #map { height:500px; }

    .controls { display:flex; gap:8px; padding:12px 20px; background:white;
                border-bottom:1px solid #eee; flex-wrap:wrap; align-items:center; }
    .toggle-btn { padding:6px 14px; border-radius:20px; border:1.5px solid #ddd;
                  font-size:12px; cursor:pointer; background:white; color:#555;
                  transition:all .2s; }
    .toggle-btn.active { color:white; border-color:transparent; }
    .btn-road.active    { background:#1D9E75; }
    .btn-straight.active{ background:#E08020; }
    .btn-history.active { background:#378ADD; }
    .controls-label { font-size:12px; color:#888; margin-right:4px; }

    .cards { display:flex; gap:10px; padding:12px 20px; flex-wrap:wrap; background:#f8f8f8; }
    .card { background:white; padding:12px 16px; border-radius:10px; min-width:130px; }
    .card .lbl { font-size:11px; color:#888; text-transform:uppercase; margin-bottom:3px; }
    .card .val { font-size:16px; font-weight:500; color:#222; }

    .route-panel { background:white; margin:12px 20px; border-radius:10px; padding:16px 20px; }
    .route-panel h3 { font-size:14px; font-weight:500; margin-bottom:10px; color:#333; }
    .rstat { display:inline-block; margin-right:24px; font-size:13px; color:#555; }
    .rstat b { color:#1D9E75; }
    .rstat-line { display:inline-block; margin-right:24px; font-size:13px; color:#555; }
    .rstat-line b { color:#E08020; }
    .steps-list { margin-top:10px; max-height:130px; overflow-y:auto;
                  border-top:1px solid #eee; padding-top:8px; }
    .steps-list li { font-size:12px; color:#666; list-style:none; padding:3px 0;
                     border-bottom:1px solid #f5f5f5; }
    .history-info { font-size:12px; color:#888; margin-top:8px; }

    .legend { display:flex; gap:20px; padding:8px 20px 14px; flex-wrap:wrap; }
    .leg-item { display:flex; align-items:center; gap:6px; font-size:12px; color:#555; }
    .leg-dot { width:12px; height:12px; border-radius:50%; border:2px solid white;
               box-shadow:0 0 0 1px #ccc; }
    .leg-line { width:22px; height:3px; border-radius:2px; }
    .leg-dashed { width:22px; border-top:2.5px dashed #E08020; }
    .leg-dotted { width:22px; border-top:3px dotted #378ADD; }
  </style>
</head>
<body>

<div class="topbar">
  <div class="dot"></div>
  <h2>LoRa Long Distance Tracker — Live</h2>
  <span style="font-size:12px;color:#888" id="last-update">Waiting...</span>
</div>

<div id="map"></div>

<div class="controls">
  <span class="controls-label">Show on map:</span>
  <button class="toggle-btn btn-road active"     onclick="toggleLayer('road')">Road route</button>
  <button class="toggle-btn btn-straight active" onclick="toggleLayer('straight')">Straight line</button>
  <button class="toggle-btn btn-history active"  onclick="toggleLayer('history')">GPS track history</button>
  <button style="margin-left:auto;padding:6px 14px;border-radius:20px;border:none;
                 background:#1D9E75;color:white;font-size:12px;cursor:pointer"
          onclick="recalcRoute()">Recalculate route</button>
</div>

<div class="cards">
  <div class="card"><div class="lbl">TX Latitude</div><div class="val" id="c-lat">--</div></div>
  <div class="card"><div class="lbl">TX Longitude</div><div class="val" id="c-lng">--</div></div>
  <div class="card"><div class="lbl">Message</div><div class="val" id="c-msg" style="font-size:13px">--</div></div>
  <div class="card"><div class="lbl">RSSI</div><div class="val" id="c-rssi">--</div></div>
  <div class="card"><div class="lbl">Track points</div><div class="val" id="c-pts">0</div></div>
</div>

<div class="route-panel">
  <h3>Path information</h3>
  <span class="rstat">Road distance: <b id="r-dist">--</b></span>
  <span class="rstat">Drive time: <b id="r-time">--</b></span>
  <span class="rstat-line">Straight line: <b id="r-line">--</b></span>
  <ul class="steps-list" id="r-steps">
    <li>Waiting for GPS data to calculate route...</li>
  </ul>
  <div class="history-info" id="hist-info">GPS track history: 0 points recorded</div>
</div>

<div class="legend">
  <div class="leg-item"><div class="leg-dot" style="background:#e74c3c"></div> Transmitter (live)</div>
  <div class="leg-item"><div class="leg-dot" style="background:#3498db"></div> Receiver (fixed)</div>
  <div class="leg-item"><div class="leg-line" style="background:#1D9E75"></div> Road route (OSRM)</div>
  <div class="leg-item"><div class="leg-dashed"></div> Straight line</div>
  <div class="leg-item"><div class="leg-dotted"></div> GPS track history</div>
</div>

<script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
<script>

var map = L.map('map').setView([{{ cx }}, {{ cy }}], {{ zoom }});
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
  {attribution:'OpenStreetMap', maxZoom:19}).addTo(map);

var txIcon = L.divIcon({ className:'',
  html:'<div style="background:#e74c3c;width:14px;height:14px;border-radius:50%;border:2px solid white;box-shadow:0 1px 5px rgba(0,0,0,.4)"></div>',
  iconSize:[14,14], iconAnchor:[7,7] });

var rxIcon = L.divIcon({ className:'',
  html:'<div style="background:#3498db;width:14px;height:14px;border-radius:50%;border:2px solid white;box-shadow:0 1px 5px rgba(0,0,0,.4)"></div>',
  iconSize:[14,14], iconAnchor:[7,7] });

var rxMarker = L.marker([{{ rx_lat }}, {{ rx_lng }}], {icon: rxIcon})
  .addTo(map).bindPopup('<b>Receiver (fixed)</b><br>Lat: {{ rx_lat }}<br>Lng: {{ rx_lng }}');

var txMarker   = null;
var roadLayer  = null;
var lineLayer  = null;
var histLayer  = null;

var showRoad     = true;
var showStraight = true;
var showHistory  = true;

function toggleLayer(type) {
  if (type === 'road') {
    showRoad = !showRoad;
    document.querySelector('.btn-road').classList.toggle('active', showRoad);
    if (roadLayer) { showRoad ? roadLayer.addTo(map) : map.removeLayer(roadLayer); }
  } else if (type === 'straight') {
    showStraight = !showStraight;
    document.querySelector('.btn-straight').classList.toggle('active', showStraight);
    if (lineLayer) { showStraight ? lineLayer.addTo(map) : map.removeLayer(lineLayer); }
  } else if (type === 'history') {
    showHistory = !showHistory;
    document.querySelector('.btn-history').classList.toggle('active', showHistory);
    if (histLayer) { showHistory ? histLayer.addTo(map) : map.removeLayer(histLayer); }
  }
}

function haversineKm(lat1, lng1, lat2, lng2) {
  var R = 6371;
  var dLat = (lat2 - lat1) * Math.PI / 180;
  var dLng = (lng2 - lng1) * Math.PI / 180;
  var a = Math.sin(dLat/2)*Math.sin(dLat/2) +
          Math.cos(lat1*Math.PI/180)*Math.cos(lat2*Math.PI/180)*
          Math.sin(dLng/2)*Math.sin(dLng/2);
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}

function recalcRoute() {
  fetch('/route').then(r => r.json()).then(d => {
    if (d.error) {
      document.getElementById('r-steps').innerHTML = '<li>' + d.error + '</li>';
      document.getElementById('r-dist').textContent = '--';
      document.getElementById('r-time').textContent = '--';
      return;
    }
    document.getElementById('r-dist').textContent = d.distance;
    document.getElementById('r-time').textContent = d.duration;
    var html = d.steps.map((s,i) => '<li>' + (i+1) + '. ' + s + '</li>').join('');
    document.getElementById('r-steps').innerHTML = html || '<li>Route found</li>';

    if (roadLayer) map.removeLayer(roadLayer);
    if (d.geometry && d.geometry.length > 0) {
      roadLayer = L.polyline(d.geometry, {color:'#1D9E75', weight:4, opacity:.85});
      if (showRoad) roadLayer.addTo(map);
    }
  }).catch(e => {
    document.getElementById('r-steps').innerHTML = '<li>Route error: ' + e + '</li>';
  });
}

function updateStraightLine(txLat, txLng) {
  if (lineLayer) map.removeLayer(lineLayer);
  var dist = haversineKm(txLat, txLng, {{ rx_lat }}, {{ rx_lng }});
  var distStr = dist >= 1 ? dist.toFixed(1) + ' km' : (dist*1000).toFixed(0) + ' m';
  document.getElementById('r-line').textContent = distStr;
  lineLayer = L.polyline([[txLat, txLng],[{{ rx_lat }}, {{ rx_lng }}]],
    {color:'#E08020', weight:2.5, dashArray:'10,6', opacity:.8});
  if (showStraight) lineLayer.addTo(map);
}

function updateHistory(points) {
  if (histLayer) map.removeLayer(histLayer);
  if (points.length < 2) return;
  var latlngs = points.map(p => [p[0], p[1]]);
  histLayer = L.polyline(latlngs,
    {color:'#378ADD', weight:3, dashArray:'1,8', lineCap:'round', opacity:.7});
  if (showHistory) histLayer.addTo(map);
  document.getElementById('c-pts').textContent = points.length;
  document.getElementById('hist-info').textContent =
    'GPS track history: ' + points.length + ' points recorded';
}

function update() {
  fetch('/data').then(r => r.json()).then(d => {
    document.getElementById('c-lat').textContent  = d.lat  || '--';
    document.getElementById('c-lng').textContent  = d.lng  || '--';
    document.getElementById('c-msg').textContent  = d.msg;
    document.getElementById('c-rssi').textContent = d.rssi !== 'N/A' ? d.rssi + ' dBm' : '--';
    document.getElementById('last-update').textContent =
      'Last update: ' + new Date().toLocaleTimeString();

    if (d.lat && d.lng) {
      var lat = parseFloat(d.lat), lng = parseFloat(d.lng);
      var latlng = [lat, lng];
      if (!txMarker) {
        txMarker = L.marker(latlng, {icon: txIcon}).addTo(map)
          .bindPopup('<b>Transmitter (live GPS)</b><br>' + d.msg);
        map.setView(latlng, {{ zoom }});
      } else {
        txMarker.setLatLng(latlng).setPopupContent('<b>Transmitter (live GPS)</b><br>' + d.msg);
      }
      updateStraightLine(lat, lng);
    }
  });

  fetch('/history').then(r => r.json()).then(d => {
    updateHistory(d.points);
  });
}

setInterval(update, 3000);
setInterval(recalcRoute, 15000);
update();
setTimeout(recalcRoute, 3000);

</script>
</body>
</html>
"""

@app.route('/')
def index():
    cx  = (RECEIVER_LAT + 20) / 2
    cy  = (RECEIVER_LNG + 80) / 2
    return render_template_string(HTML,
        rx_lat=RECEIVER_LAT, rx_lng=RECEIVER_LNG,
        cx=cx, cy=cy, zoom=6)

@app.route('/data')
def data():
    return __import__('flask').jsonify(latest_data)

@app.route('/history')
def history():
    return __import__('flask').jsonify({"points": gps_history})

@app.route('/route')
def get_route():
    if not latest_data['lat'] or not latest_data['lng']:
        return __import__('flask').jsonify({"error": "No GPS data yet"})
    try:
        tx_lat = float(latest_data['lat'])
        tx_lng = float(latest_data['lng'])

        url = (
            f"http://router.project-osrm.org/route/v1/driving/"
            f"{tx_lng},{tx_lat};{RECEIVER_LNG},{RECEIVER_LAT}"
            f"?overview=full&geometries=geojson&steps=true"
        )
        resp   = requests.get(url, timeout=15)
        result = resp.json()

        if result.get('code') != 'Ok':
            return __import__('flask').jsonify({"error": "OSRM error: " + result.get('code','unknown')})

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
        for leg in route['legs']:
            for step in leg['steps']:
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

        coords   = route['geometry']['coordinates']
        geometry = [[c[1], c[0]] for c in coords]

        return __import__('flask').jsonify({
            "distance": dist_str,
            "duration": dur_str,
            "steps":    steps,
            "geometry": geometry
        })

    except requests.exceptions.Timeout:
        return __import__('flask').jsonify({"error": "OSRM timeout — check internet connection"})
    except Exception as e:
        return __import__('flask').jsonify({"error": str(e)})


def is_valid(line):
    try:
        c = line[5:]
        if ",RSSI:" in c: c = c.split(",RSSI:")[0]
        p = c.split(",", 2)
        if len(p) < 3: return False
        lat, lng = float(p[0]), float(p[1])
        return -90 <= lat <= 90 and -180 <= lng <= 180 and len(p[2].strip()) > 0
    except:
        return False

def read_serial():
    import time
    PORT = 'COM11'
    ports = serial.tools.list_ports.comports()
    for p in ports:
        if any(x in p.description for x in ['Arduino','CH340','USB Serial']):
            PORT = p.device; break

    print(f"Connecting to {PORT}...")
    while True:
        try:
            ser = serial.Serial(PORT, 9600, timeout=2)
            print(f"Connected to {PORT} — waiting for data...")
            while True:
                raw  = ser.readline()
                line = raw.decode('utf-8', errors='ignore').strip()
                if not line.startswith("DATA:"): continue
                if not is_valid(line):
                    print(f"  Skipped (corrupted): {line}"); continue

                c = line[5:]
                rssi = "N/A"
                if ",RSSI:" in c:
                    sp = c.split(",RSSI:"); rssi = sp[1]; c = sp[0]
                p = c.split(",", 2)
                lat = p[0].strip()
                lng = p[1].strip()
                msg = p[2].strip()

                latest_data.update({'lat':lat,'lng':lng,'msg':msg,'rssi':rssi})

                # Add to GPS track history
                gps_history.append([float(lat), float(lng)])
                if len(gps_history) > MAX_HISTORY:
                    gps_history.pop(0)

                print(f"  lat={lat} lng={lng} | history={len(gps_history)} pts")

        except serial.SerialException as e:
            print(f"Serial error: {e} — retry in 4s")
            time.sleep(4)

t = threading.Thread(target=read_serial, daemon=True)
t.start()

if __name__ == '__main__':
    print("="*50)
    print("  LoRa Long Distance Tracker")
    print("  Open http://localhost:5000")
    print("="*50)
    __import__('flask').Flask(__name__)
    app.run(host='0.0.0.0', port=5000, debug=False)