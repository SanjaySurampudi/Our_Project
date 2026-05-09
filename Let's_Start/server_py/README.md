# LoRa Long Distance Tracker — Improved

## Project structure

```
lora_tracker/
├── app.py              ← entry point  (python app.py)
├── serial_reader.py    ← serial port thread + shared state
├── router.py           ← offline Dijkstra routing on OSM graph
├── flask_routes.py     ← Flask URL handlers + HTML template
├── rx.ino              ← Arduino RX sketch (fixed RSSI serial output)
└── requirements.txt
```

---

## Improvements made

### 1 — Offline routing (router.py)
- Replaces the `OSRM` internet API with a **local Dijkstra's algorithm** running
  on a road graph downloaded once from OpenStreetMap via `osmnx`.
- The graph is downloaded in a background thread on startup so the UI is
  immediately available.
- If `osmnx` is not installed, or the graph hasn't finished loading yet, the
  router transparently falls back to a straight-line result with a clear note.
- Adjust `OSM_RADIUS_M` in `app.py` to control the area covered
  (default 50 km radius around the receiver).

### 2 — RSSI in serial output (rx.ino)
- `LoRa.packetRssi()` is now appended to the `DATA:` line:
  ```
  DATA:<lat>,<lng>,<message>,RSSI:<value>
  ```
- `serial_reader.py` parses the `,RSSI:` suffix and stores it in `latest_data`.
- The web dashboard now shows the real RSSI value instead of `N/A`.

### 3 — Modular separation (Python files)
- `serial_reader.py` — all serial / packet-parsing logic + shared state dict
- `router.py`        — all routing / graph logic
- `flask_routes.py`  — all Flask routes and the HTML template
- `app.py`           — thin entry point that wires the modules together
- All `__import__('flask')` hacks replaced with proper top-level imports.

---

## Installation

```bash
pip install flask pyserial requests osmnx networkx
```

> `osmnx` and `networkx` are required for offline road routing.
> Without them the system still works using straight-line distances.

---

## Running

1. Flash `rx.ino` to the Arduino receiver.
2. Edit the constants at the top of `app.py`:
   - `RECEIVER_LAT` / `RECEIVER_LNG` — your fixed receiver GPS location
   - `SERIAL_PORT` — leave `None` for auto-detect, or set e.g. `"COM11"`
   - `OSM_RADIUS_M` — radius of the road graph to cache (metres)
3. Run:
   ```bash
   python app.py
   ```
4. Open **http://localhost:5000** in your browser.

On first run the OSM graph downloads in the background (takes 10–60 seconds
depending on radius and internet speed). During that time the map shows
straight-line routing with a note; once the graph is ready it switches to
road routing automatically.
