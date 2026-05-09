"""
flask_routes.py  —  All Flask route handlers for the LoRa Tracker web UI.

Improvements kept:
  1. Road routing uses offline Dijkstra on OSMnx graph (router.py).
     Returns real road geometry — draws the EXACT road path on the map.
  2. RSSI parsed from serial (serial_reader.py) and served via /data.
  3. All Flask routes and HTML in this one module (modular separation).
     All imports are standard top-level — no __import__() hacks.

Register with:
    from flask_routes import register_routes
    register_routes(app, router, receiver_lat, receiver_lng)
"""

import logging
from flask import jsonify, render_template_string
from serial_reader import latest_data, gps_history

log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
_HTML = """
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
  <div class="leg-item"><div class="leg-line" style="background:#1D9E75"></div> Road route (OSMnx + Dijkstra)</div>
  <div class="leg-item"><div class="leg-dashed"></div> Straight line</div>
  <div class="leg-item"><div class="leg-dotted"></div> GPS track history</div>
</div>

<script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
<script>

var RX_LAT = {{ rx_lat }};
var RX_LNG = {{ rx_lng }};

var map = L.map('map').setView([RX_LAT, RX_LNG], 7);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
  {attribution:'OpenStreetMap', maxZoom:19}).addTo(map);

var txIcon = L.divIcon({ className:'',
  html:'<div style="background:#e74c3c;width:14px;height:14px;border-radius:50%;border:2px solid white;box-shadow:0 1px 5px rgba(0,0,0,.4)"></div>',
  iconSize:[14,14], iconAnchor:[7,7] });

var rxIcon = L.divIcon({ className:'',
  html:'<div style="background:#3498db;width:14px;height:14px;border-radius:50%;border:2px solid white;box-shadow:0 1px 5px rgba(0,0,0,.4)"></div>',
  iconSize:[14,14], iconAnchor:[7,7] });

var rxMarker = L.marker([RX_LAT, RX_LNG], {icon: rxIcon})
  .addTo(map)
  .bindPopup('<b>Receiver (fixed)</b><br>Lat: ' + RX_LAT + '<br>Lng: ' + RX_LNG);

var txMarker  = null;
var roadLayer = null;
var lineLayer = null;
var histLayer = null;

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

// Road route — calls Python /route which runs Dijkstra on OSMnx graph
function recalcRoute() {
  fetch('/route')
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.error) {
        document.getElementById('r-steps').innerHTML = '<li>' + d.error + '</li>';
        document.getElementById('r-dist').textContent = '--';
        document.getElementById('r-time').textContent = '--';
        return;
      }
      document.getElementById('r-dist').textContent = d.distance;
      document.getElementById('r-time').textContent = d.duration;
      var html = d.steps.map(function(s, i) {
        return '<li>' + (i + 1) + '. ' + s + '</li>';
      }).join('');
      document.getElementById('r-steps').innerHTML = html || '<li>Route found</li>';

      if (roadLayer) { map.removeLayer(roadLayer); }
      if (d.geometry && d.geometry.length > 0) {
        roadLayer = L.polyline(d.geometry, {color:'#1D9E75', weight:5, opacity:.85});
        if (showRoad) { roadLayer.addTo(map); }
      }
    })
    .catch(function(e) {
      document.getElementById('r-steps').innerHTML = '<li>Route error: ' + e + '</li>';
    });
}

function updateStraightLine(txLat, txLng) {
  if (lineLayer) { map.removeLayer(lineLayer); }
  var dist = haversineKm(txLat, txLng, RX_LAT, RX_LNG);
  var distStr = dist >= 1 ? dist.toFixed(1) + ' km' : (dist * 1000).toFixed(0) + ' m';
  document.getElementById('r-line').textContent = distStr;
  lineLayer = L.polyline(
    [[txLat, txLng], [RX_LAT, RX_LNG]],
    {color:'#E08020', weight:2.5, dashArray:'10,6', opacity:.8}
  );
  if (showStraight) { lineLayer.addTo(map); }
}

function updateHistory(points) {
  if (histLayer) { map.removeLayer(histLayer); }
  if (points.length < 2) { return; }
  var latlngs = points.map(function(p) { return [p[0], p[1]]; });
  histLayer = L.polyline(latlngs,
    {color:'#378ADD', weight:3, dashArray:'1,8', lineCap:'round', opacity:.7});
  if (showHistory) { histLayer.addTo(map); }
  document.getElementById('c-pts').textContent = points.length;
  document.getElementById('hist-info').textContent =
    'GPS track history: ' + points.length + ' points recorded';
}

function update() {
  fetch('/data')
    .then(function(r) { return r.json(); })
    .then(function(d) {
      document.getElementById('c-lat').textContent  = d.lat  || '--';
      document.getElementById('c-lng').textContent  = d.lng  || '--';
      document.getElementById('c-msg').textContent  = d.msg  || '--';
      document.getElementById('c-rssi').textContent =
        (d.rssi && d.rssi !== 'N/A') ? d.rssi + ' dBm' : '--';
      document.getElementById('last-update').textContent =
        'Last update: ' + new Date().toLocaleTimeString();

      if (d.lat && d.lng) {
        var lat = parseFloat(d.lat);
        var lng = parseFloat(d.lng);
        if (!txMarker) {
          txMarker = L.marker([lat, lng], {icon: txIcon})
            .addTo(map)
            .bindPopup('<b>Transmitter (live GPS)</b><br>' + (d.msg || ''));
          map.fitBounds([[lat, lng], [RX_LAT, RX_LNG]], {padding:[60, 60]});
        } else {
          txMarker.setLatLng([lat, lng])
                  .setPopupContent('<b>Transmitter (live GPS)</b><br>' + (d.msg || ''));
        }
        updateStraightLine(lat, lng);
      }
    })
    .catch(function(e) { console.warn('Data fetch error:', e); });

  fetch('/history')
    .then(function(r) { return r.json(); })
    .then(function(d) { updateHistory(d.points); })
    .catch(function(e) { console.warn('History fetch error:', e); });
}

setInterval(update, 3000);
setInterval(recalcRoute, 15000);
update();
setTimeout(recalcRoute, 3000);
</script>
</body>
</html>
"""

# ──────────────────────────────────────────────────────────────────────────────

def register_routes(app, router, receiver_lat: float, receiver_lng: float) -> None:
    """
    Attach all URL routes to *app*.

    Parameters
    ----------
    app          : Flask application instance
    router       : OfflineRouter instance from router.py
    receiver_lat : fixed latitude of the LoRa receiver
    receiver_lng : fixed longitude of the LoRa receiver
    """

    @app.route("/")
    def index():
        return render_template_string(
            _HTML,
            rx_lat=receiver_lat,
            rx_lng=receiver_lng,
        )

    @app.route("/data")
    def data():
        return jsonify(latest_data)

    @app.route("/history")
    def history():
        return jsonify({"points": gps_history})

    @app.route("/route")
    def get_route():
        if not latest_data["lat"] or not latest_data["lng"]:
            return jsonify({"error": "No GPS data yet"})
        try:
            result = router.route(
                float(latest_data["lat"]),
                float(latest_data["lng"]),
                receiver_lat,
                receiver_lng,
            )
            return jsonify(result)
        except Exception as exc:
            log.exception("Route endpoint error")
            return jsonify({"error": str(exc)})
