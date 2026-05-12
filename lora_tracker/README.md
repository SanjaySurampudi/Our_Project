# LoRa GPS Tracker – Offline Emergency Communications System

> **PS-139 · VLSI** | Offline GPS tracking & short text messaging over ISM-band 433 MHz LoRa

---

## Overview

This project provides an **affordable, infrastructure-free GPS tracking and short text messaging system** built on the 433 MHz ISM band using LoRa radio.  It is designed for use cases where internet connectivity is unavailable – search and rescue, field surveys, disaster response, rural expeditions.

A transmitter node (Arduino + NEO-6M GPS + SX1278 LoRa) broadcasts its position every 2 seconds.  A receiver node (Arduino + SX1278 LoRa + SSD1306 OLED) receives the packets, stamps the RSSI, and forwards them over USB-Serial to a laptop running a Flask server.  A Leaflet-based web dashboard provides live map visualisation, RSSI chart, OSRM road-routing, and offline tile caching.

---

## In-Scope Features (Implemented)

| # | Feature | Evidence |
|---|---------|----------|
| 1 | **Offline GPS tracking** – position fix every 2 s | `TX.ino` – TinyGPS++ + SoftwareSerial loop |
| 2 | **Short text messaging** – arbitrary message field in CSV packet | `TX.ino` / `RX.ino` – CSV packet format |
| 3 | **ISM 433 MHz LoRa link** – no SIM card, no Wi-Fi required | `TX.ino` / `RX.ino` – `LoRa.begin(433E6)` |
| 4 | **OLED live display** – lat/lng + RSSI on receiver | `RX.ino` – Adafruit SSD1306, graceful-degradation retry |
| 5 | **Flask REST API** – `/data`, `/history`, `/route` | `server.py` |
| 6 | **Leaflet web dashboard** – live map, RSSI indicator, route | `templates/index.html` |
| 7 | **OSRM road routing** – driving route + distance + ETA | `server.py` `/route` endpoint |
| 8 | **Offline tile caching** – `leaflet.offline` bundled locally | `static/leaflet.offline.min.js` |
| 9 | **Auto port detection** – finds USB-serial without manual config | `server.py` `_autodetect_port()` |
| 10 | **Auto reconnect** – recovers from serial disconnects (5-failure threshold) | `server.py` `read_serial()` |
| 11 | **Packet validation** – range checks, RSSI format, seq/legacy detection | `server.py` `is_valid()` |
| 12 | **Stale GPS rejection** – skips transmit if fix age > 2 s | `TX.ino` – non-blocking `feedGPS()` wait |
| 13 | **GPS history deque** – rolling 500-point buffer | `server.py` `deque(maxlen=MAX_HISTORY)` |
| 14 | **51-test suite** – parser, routes, serial integration with FakeSerial | `tests/` |

---

## Out-of-Scope (Explicitly Excluded)

The following features are **not** implemented and are outside the current project boundary:

- **Bi-directional communication** – the system is one-way TX → RX.  Adding a downlink channel would require a second LoRa module on the transmitter side and a half-duplex protocol to avoid collision.
- **AES-128 packet encryption** – packets are plaintext CSV.  Encryption requires shared-key management, increases packet size, and adds latency; deferred to a future security sprint.
- **Kalman / particle filter smoothing** – raw GPS coordinates are used without statistical smoothing.  Filtered position estimation is non-trivial and outside scope.
- **SD-card data logging on receiver** – the receiver forwards data over USB-Serial only; persistent logging to SD is not implemented.
- **Multi-node / fleet tracking** – the current architecture stores one `latest_data` dict and one `gps_history` deque.  The packet format and `node_id` field are prepared (see Future Scope), but the server does not yet route per-node.
- **Mobile native app** – the dashboard is a web app served over localhost; a native iOS/Android app is out of scope.
- **Solar / battery optimisation firmware** – sleep modes and duty-cycling are not implemented.

---

## Future Scope & Enhancement Roadmap

### Near-term (1–2 sprints)

| Enhancement | What changes | Difficulty |
|-------------|-------------|------------|
| **Env-var configuration** ✅ | `RECEIVER_LAT`, `RECEIVER_LNG`, `MAX_HISTORY`, `SERIAL_BAUD` already externalised via `os.environ` | Done |
| **Altitude / speed / heading transmission** ✅ | Added to TX packet fields; displayed in dashboard | Done |
| **Proper HTTP status codes on `/route`** ✅ | 503 for OSRM errors, 422 for bad coords, 200 for soft errors | Done |
| **Bundled leaflet.offline** | Download `leaflet.offline.min.js` + `leaflet.min.js` + `leaflet.min.css` into `static/` so the dashboard loads with zero internet dependency | High priority |
| **Per-node GPS state** | Introduce `node_id` key (already in packet), change `latest_data` and `gps_history` to dicts keyed by `node_id` | 2–3 days |

### Medium-term (1 month)

| Enhancement | Description |
|-------------|-------------|
| **Bi-directional messaging** | Add a second LoRa on TX side; implement simple ACK/NAK half-duplex protocol.  Server gains a `/send` POST endpoint. |
| **AES-128 encryption** | Pre-shared 16-byte key on both Arduinos; encrypt payload before `LoRa.print()`, decrypt after `LoRa.read()`.  Minimal overhead at 128-byte packet sizes. |
| **SD-card logging** | `RX.ino` writes each received packet to `log.csv` on an SD module; provides offline audit trail without PC. |
| **Kalman filter position smoothing** | Server-side 2D Kalman filter applied before storing to history; reduces GPS jitter on the map. |

### Long-term (3+ months)

| Enhancement | Description |
|-------------|-------------|
| **Multi-node fleet tracking** | `node_id` field already in packet. Server refactored to `latest_data: dict[str, dict]`; dashboard shows per-node coloured markers and history. |
| **Battery / solar optimisation** | TX sleeps between transmissions using `LowPower.powerDown()`; configurable duty cycle via AT-command over Serial. |
| **Native mobile companion app** | React Native app connects to Flask server over local Wi-Fi hotspot; shows same Leaflet map on phone. |
| **Over-the-Air (OTA) config push** | Receiver can relay short config commands back to transmitter (once bi-directional link is implemented). |

---

## Architecture

```
┌──────────────────────────┐        433 MHz LoRa         ┌─────────────────────────┐
│  TX Node (Arduino)       │  ─────────────────────────► │  RX Node (Arduino)      │
│  NEO-6M GPS              │                              │  SSD1306 OLED display   │
│  SX1278 LoRa             │  CSV packet every 2 s        │  SX1278 LoRa            │
│  TX.ino                  │  seq,lat,lng,alt,spd,hdg,    │  RX.ino                 │
└──────────────────────────┘  msg,RSSI:<val>              └────────────┬────────────┘
                                                                        │ USB-Serial
                                                                        ▼
                                                          ┌─────────────────────────┐
                                                          │  PC – Flask server      │
                                                          │  server.py              │
                                                          │  /data /history /route  │
                                                          └────────────┬────────────┘
                                                                        │ HTTP
                                                                        ▼
                                                          ┌─────────────────────────┐
                                                          │  Web Dashboard          │
                                                          │  Leaflet + leaflet.off  │
                                                          │  OSRM routing           │
                                                          │  3-second auto-refresh  │
                                                          └─────────────────────────┘
```

---

## Setup

### Hardware

| Component | Part |
|-----------|------|
| Microcontroller (×2) | Arduino Uno R3 |
| GPS module | NEO-6M with UART |
| LoRa module (×2) | SX1278 / Ra-02 433 MHz |
| OLED display | SSD1306 128×64 I2C |

### Software prerequisites

```bash
pip install flask pyserial requests
```

### Run

```bash
# 1. Flash TX.ino to transmitter Arduino
# 2. Flash RX.ino to receiver Arduino
# 3. Connect receiver Arduino to PC via USB

# 4. (Optional) configure receiver location
export RECEIVER_LAT=17.3850
export RECEIVER_LNG=78.4867

# 5. Start server
cd lora_tracker
python server.py

# 6. Open browser → http://localhost:5000
```

### Run tests

```bash
cd lora_tracker
pytest tests/ -v
```

---

## Project Structure

```
lora_tracker/
├── server.py                   # Flask back-end + serial reader
├── templates/
│   └── index.html              # Leaflet dashboard (Jinja2)
├── static/
│   ├── leaflet.min.css         # Bundle locally for offline use
│   ├── leaflet.min.js
│   └── leaflet.offline.min.js  # Offline tile plugin (bundle locally)
├── arduino/
│   ├── TX/TX.ino               # Transmitter firmware
│   └── RX/RX.ino               # Receiver firmware
└── tests/
    ├── test_parser.py           # 29 is_valid / parse_packet tests
    ├── test_routes.py           # 13 Flask route tests (with HTTP status checks)
    └── test_integration_serial.py  # 13 serial loopback tests
```

---

## Known Limitations

1. `leaflet.offline.min.js` and Leaflet core CSS/JS are referenced from `static/` – **you must download them manually** (see Setup) or the dashboard will not load in a fully offline environment.
2. OSRM public API (`router.project-osrm.org`) requires internet access.  Set `OSRM_HOST` to a local OSRM Docker instance for fully offline routing.
3. Single-node architecture: only one tracker transmitter is supported by the current server state model.  See Future Scope for multi-node roadmap.

---

## Licence

MIT – free for educational and non-commercial use.
