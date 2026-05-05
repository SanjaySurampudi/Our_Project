import serial
import serial.tools.list_ports
import threading
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)
# Store latest LoRa data (lat, lng, message, RSSI)
latest_data = {"lat": "", "lng": "", "msg": "Waiting for LoRa data...", "rssi": "N/A"}

# HTML template for live tracker dashboard
HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>LoRa GPS Tracker</title>
  <meta charset="utf-8">
  <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css"/>
  <style>
    /* Basic styling for dashboard */
    body { font-family: sans-serif; margin: 0; background: #f0f2f5; }
    h2 { padding: 20px 20px 0; color: #333; }
    #map { height: 420px; margin: 15px 20px; border-radius: 12px; }
    .cards { display: flex; gap: 15px; padding: 0 20px 20px; flex-wrap: wrap; }
    .card { background: white; padding: 16px 20px; border-radius: 10px; min-width: 160px; }
    .card .label { font-size: 12px; color: #888; margin-bottom: 4px; }
    .card .value { font-size: 18px; font-weight: 500; color: #222; }
    .dot { display:inline-block; width:10px; height:10px; background:#2ecc71;
           border-radius:50%; margin-right:8px; animation: pulse 1.5s infinite; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
  </style>
</head>
<body>
  <h2><span class="dot"></span>LoRa Tracker — Live</h2>
  <div id="map"></div>
  <div class="cards">
    <!-- Cards showing live data -->
    <div class="card"><div class="label">Latitude</div><div class="value" id="lat">--</div></div>
    <div class="card"><div class="label">Longitude</div><div class="value" id="lng">--</div></div>
    <div class="card" style="flex:1;min-width:260px">
      <div class="label">Message</div>
      <div class="value" id="msg" style="font-size:15px">--</div>
    </div>
    <div class="card"><div class="label">RSSI (signal)</div><div class="value" id="rssi">--</div></div>
  </div>
  <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
  <script>
    // Initialize map centered at default coordinates
    var map = L.map('map').setView([17.08, 82.06], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      {attribution: 'OpenStreetMap'}).addTo(map);
    var marker = null;

    // Function to update map and cards with latest data
    function update() {
      fetch('/data').then(r => r.json()).then(d => {
        document.getElementById('lat').textContent = d.lat || '--';
        document.getElementById('lng').textContent = d.lng || '--';
        document.getElementById('msg').textContent = d.msg;
        document.getElementById('rssi').textContent = d.rssi !== 'N/A' ? d.rssi + ' dBm' : '--';

        if (d.lat && d.lng) {
          var latlng = [parseFloat(d.lat), parseFloat(d.lng)];
          if (!marker) {
            // Place marker first time
            marker = L.marker(latlng).addTo(map)
              .bindPopup('<b>' + d.msg + '</b>').openPopup();
            map.setView(latlng, 14);
          } else {
            // Update marker position and popup
            marker.setLatLng(latlng).setPopupContent('<b>' + d.msg + '</b>');
          }
        }
      });
    }
    setInterval(update, 2000); // Refresh every 2 seconds
    update();
  </script>
</body>
</html>
"""

@app.route('/')
def index():
    # Serve dashboard page
    return render_template_string(HTML)

@app.route('/data')
def data():
    # Endpoint to return latest LoRa data as JSON
    return jsonify(latest_data)

def is_valid_packet(line):
    """Check if incoming packet is valid (lat,lng,msg format)"""
    try:
        content = line[5:]  # remove "DATA:" prefix
        # Remove RSSI part if present
        if ",RSSI:" in content:
            content = content.split(",RSSI:")[0]
        parts = content.split(",", 2)
        if len(parts) < 3:
            return False
        # Validate lat/lng
        lat = float(parts[0])
        lng = float(parts[1])
        msg = parts[2].strip()
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            return False
        if len(msg) == 0:  # message must not be empty
            return False
        return True
    except:
        return False

def find_arduino_port():
    """Auto-detect Arduino COM port by description"""
    ports = serial.tools.list_ports.comports()
    for p in ports:
        if 'Arduino' in p.description or 'CH340' in p.description or 'USB Serial' in p.description:
            return p.device
    return None

def read_serial():
    # ---- CHANGE THIS to your COM port (e.g. COM4, COM5, COM6) ----
    PORT = 'COM11'
    # --------------------------------------------------------------

    # Try auto-detect if COM11 fails
    auto = find_arduino_port()
    if auto:
        print(f"Auto-detected Arduino on: {auto}")
        PORT = auto

    print(f"Connecting to {PORT} at 9600 baud...")
    print("Make sure Arduino Serial Monitor is CLOSED!")

    while True:  # Keep retrying if port disconnects
        try:
            ser = serial.Serial(PORT, 9600, timeout=2)
            print(f"Connected! Waiting for data...")
            while True:
                raw = ser.readline()
                line = raw.decode('utf-8', errors='ignore').strip()

                if not line.startswith("DATA:"):
                    continue

                print(f"Raw: {line}")

                if not is_valid_packet(line):
                    print("  -> Skipped (corrupted packet)")
                    continue

                # Parse valid packet
                content = line[5:]
                rssi_val = "N/A"
                if ",RSSI:" in content:
                    parts_rssi = content.split(",RSSI:")
                    rssi_val = parts_rssi[1]
                    content = parts_rssi[0]

                parts = content.split(",", 2)
                latest_data['lat'] = parts[0].strip()
                latest_data['lng'] = parts[1].strip()
                latest_data['msg'] = parts[2].strip()
                latest_data['rssi'] = rssi_val
                print(f"  -> Updated: lat={latest_data['lat']} lng={latest_data['lng']} msg={latest_data['msg']}")

        except serial.SerialException as e:
            # Handle serial errors and retry
            print(f"Serial error: {e}")
            print("Retrying in 3 seconds... (close Serial Monitor if open!)")
            import time
            time.sleep(3)

# Run serial reader in background thread
t = threading.Thread(target=read_serial, daemon=True)
t.start()

if __name__ == '__main__':
    print("="*40)
    print("Server starting...")
    print("Open http://localhost:5000 in your browser")
    print("="*40)
    # Start Flask server
    app.run(host='0.0.0.0', port=5000, debug=False)
