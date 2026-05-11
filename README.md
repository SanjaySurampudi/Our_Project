# 📡 LoRa Long-Range Offline-to-Online Communication & GPS Tracking System

> A two-node LoRa-based GPS tracking and messaging system that operates **100% offline** over an RF link and optionally enriches data on a live web dashboard when internet is available.

---

## 📋 Table of Contents

1. [Description](#description)
2. [Requirements](#requirements)
3. [Problem Statement](#problem-statement)
4. [Proposed Solution](#proposed-solution)
5. [Technologies Used](#technologies-used)
6. [System Architecture](#system-architecture)
7. [In-Scope](#in-scope)
8. [Out-of-Scope](#out-of-scope)
9. [Project Structure](#project-structure)
10. [Getting Started](#getting-started)
11. [Usage](#usage)
12. [Future Enhancements](#future-enhancements)
13. [Conclusion](#conclusion)

---

## 📖 Description

This project implements a **long-range, offline-capable communication and GPS tracking system** using LoRa (Long Range) radio technology operating at **433 MHz**.

- The **transmitter unit** functions completely offline in remote areas without any internet or cellular connectivity. It captures live GPS coordinates via a NEO-6M module and broadcasts them along with a text message over LoRa radio waves.
- The **receiver unit**, located up to several kilometres away, captures these packets through its own LoRa module and displays the data on a local OLED screen *(offline mode)*.
- When internet is available at the receiver side, the same data is simultaneously pushed to a **Flask-based web dashboard** that:
  - Plots the transmitter's live position on an OpenStreetMap interface
  - Draws the road route via OSRM
  - Calculates straight-line (Haversine) distance
  - Maintains a GPS track history of up to **500 points**
  - Displays LoRa signal strength (RSSI)

> **The communication link between transmitter and receiver is 100% offline (purely RF-based).** Internet is optional and used only for map visualisation enrichment at the receiver end.

---

## 🛠️ Requirements

### Hardware Requirements

| Component | Quantity | Notes |
|-----------|----------|-------|
| Arduino Uno | ×2 | One for TX, one for RX |
| LoRa SX1278 Module | ×2 | 433 MHz transceiver |
| NEO-6M GPS Module | ×1 | Transmitter side only |
| SSD1306 OLED Display (128×64, I²C) | ×1 | Receiver side |
| 433 MHz Antennas | ×2 | Tuned for 433 MHz |
| Jumper wires, breadboards | — | — |
| 5V power supply / battery pack | — | — |
| USB cable | ×1 | Connecting RX Arduino to host PC |

### Software Requirements

- **Arduino IDE** with the following libraries:
  - `LoRa`
  - `TinyGPS++`
  - `SoftwareSerial`
  - `Adafruit_GFX`
  - `Adafruit_SSD1306`
  - `Wire`
  - `SPI`
- **Python 3.x** with packages:
  - `pyserial`
  - `flask`
  - `requests`
- **Web Browser** — Chrome / Firefox / Edge (with Leaflet.js support)
- **Internet** *(optional)* — only at receiver host for map tiles & OSRM routing
- OpenStreetMap tile service & OSRM public routing API

### Functional Requirements

- Offline RF communication between TX and RX
- Real-time GPS acquisition and transmission every **2 seconds**
- Reliable packet parsing with corruption filtering
- Dual-mode receiver output: OLED display + Web Dashboard
- RSSI logging for signal-strength analysis

---

## ❗ Problem Statement

In remote, rural, disaster-hit, or infrastructure-poor regions, conventional communication systems such as GSM, 4G/5G, and Wi-Fi are either unavailable or unreliable. This creates critical gaps in:

- **Tracking personnel or assets** (trekkers, soldiers, livestock, vehicles, drones) in cellular dead zones.
- **Sending short emergency / status messages** when internet and mobile networks fail (floods, earthquakes, forest fires).
- **Affordable long-range telemetry** — existing satellite-based solutions (GPS trackers with GSM/satellite uplink) are expensive and carry recurring costs.
- **Lack of an offline backbone** between two distant points where neither side has internet access at the link itself.
- **No flexible visualisation** — many off-the-shelf trackers store data locally and lack a live map with route, distance, and signal-quality feedback.

> A low-cost, license-free (ISM-band 433 MHz), low-power, long-range communication system is needed that operates **independently of any internet/cellular infrastructure**.

---

## 💡 Proposed Solution

A two-node LoRa-based GPS tracking and messaging system with the following design:

1. **Transmitter Node** — Arduino Uno reads live latitude/longitude from a NEO-6M GPS via SoftwareSerial, parses it using TinyGPS++, packages the coordinates with a text message into a CSV-style packet (`lat,lng,message`), and transmits it via the SX1278 LoRa module at 433 MHz every 2 seconds — **completely offline**.

2. **Receiver Node** — Arduino Uno with an SX1278 LoRa module listens for incoming packets, captures the RSSI immediately on reception, displays parsed `lat/lng/message/RSSI` on a 0.96″ SSD1306 OLED, and forwards the packet over USB serial in the format:
   ```
   DATA:<lat>,<lng>,<msg>,RSSI:<value>
   ```

3. **Python–Flask Backend** — Runs on the host PC, reads the serial stream in a background thread, validates and parses packets, maintains GPS history (up to 500 points), and exposes `/data`, `/history`, and `/route` JSON endpoints.

4. **Web Dashboard (Leaflet.js + OpenStreetMap)** — Shows the transmitter and receiver as markers, draws the road route via the OSRM public API, overlays a dashed Haversine straight-line, plots GPS track history, and refreshes every **3 seconds**.

5. **Graceful Offline Fallback** — If the receiver host has no internet, the OLED still shows all data; the web dashboard simply omits map tiles and route info.

---

## 🔧 Technologies Used

| Layer | Technologies |
|-------|-------------|
| Firmware | Arduino (C/C++), SPI, I²C, SoftwareSerial |
| RF Communication | LoRa SX1278 — 433 MHz |
| GPS | NEO-6M, TinyGPS++ |
| Display | Adafruit GFX, Adafruit SSD1306 |
| Backend | Python 3, Flask, PySerial, Threading |
| Frontend | HTML5, CSS3, JavaScript, Leaflet.js |
| Mapping | OpenStreetMap, OSRM Routing API |
| Algorithms | Haversine Formula |
| Data Format | CSV packets, JSON, REST API |

---

## 🏗️ System Architecture

```
┌──────────────────────── TRANSMITTER (Fully Offline) ────────────────────────┐
│                                                                              │
│   ┌──────────────┐   SoftSerial    ┌────────────────┐    SPI    ┌─────────┐ │
│   │  NEO-6M GPS  │ ──────────────▶ │  Arduino Uno   │ ────────▶ │ SX1278  │ │
│   │  (Satellites)│   9600 baud     │  (TinyGPS++)   │  10/9/2   │  LoRa   │ │
│   └──────────────┘                 └────────────────┘           │ 433 MHz │ │
│          ▲                                                       └────┬────┘ │
│          │ GPS L1 signal                                              │      │
└──────────┼──────────────────────────────────────────────────────────  │ ─────┘
           │                                                            │
           │                   RF LINK (Offline, up to several km)
           │                                                            │
┌──────────┼──────────────────────────── RECEIVER ─────────────────────│──────┐
│          │                                                            ▼      │
│   GPS Satellites (TX uses)                                  ┌──────────────┐ │
│                                                              │   SX1278     │ │
│                                                              │   LoRa RX    │ │
│                                                              └──────┬───────┘ │
│                                                            SPI │ 10/9/2       │
│                                                                  ▼            │
│   ┌─────────────┐   I²C    ┌──────────────────┐                              │
│   │ OLED SSD1306│ ◀─────── │   Arduino Uno    │ ── USB Serial (9600) ───┐   │
│   │  128×64     │  0x3C    │ (Parse + Display)│                          │   │
│   └─────────────┘          └──────────────────┘                          │   │
│   [Offline Mode]                                                          ▼   │
│                                                              ┌──────────────────┐
│                                                              │  Host PC         │
│                                                              │  ┌────────────┐  │
│                                                              │  │Python      │  │
│                                                              │  │Flask Server│  │
│                                                              │  │+ PySerial  │  │
│                                                              │  └─────┬──────┘  │
│                                                              │        │         │
│                                                              │  /data /history  │
│                                                              │       /route     │
│                                                              │        │         │
│                                                              │  ┌─────▼──────┐  │
│                                                              │  │Leaflet Map │  │
│                                                              │  │OSM + OSRM  │  │
│                                                              │  └────────────┘  │
│                                                              └──────────────────┘
│                                                              [Online Mode]      │
└──────────────────────────────────────────────────────────────────────────────────┘
```

**Data Flow:**
```
GPS Satellites → NEO-6M → Arduino TX → SX1278 TX
  → (Offline RF 433 MHz)
    → SX1278 RX → Arduino RX → {OLED Display}
                              + {Serial → Python Flask → Web Dashboard}
```

---

## ✅ In-Scope

- Real-time GPS coordinate transmission from a moving/fixed transmitter unit
- One-way short text messaging from TX to RX (default `"Hello Trainee!"` or custom via Serial input)
- Fully offline RF communication using ISM band 433 MHz LoRa
- Local visualisation on a 0.96″ OLED at the receiver (works without any internet)
- Web-based live map with transmitter/receiver markers and live position updates
- Road-route generation between TX and RX via OSRM
- Haversine straight-line distance calculation
- GPS track history rendering (last **500 points**)
- RSSI (signal strength) display for link-quality monitoring
- Automatic Arduino COM port detection on the Python server
- Packet corruption filtering / validation on the server side
- Auto-reconnect to serial port on disconnection

---

## 🚫 Out-of-Scope

- Two-way / bi-directional communication (current design is TX → RX only)
- Encryption / authentication of LoRa packets (data is sent in plain text)
- Mesh networking, multi-node relaying, or LoRaWAN gateway operation
- Cellular (GSM/4G/5G) or satellite uplinks at the transmitter side
- Cloud database storage or long-term historical analytics
- Mobile app (Android/iOS) interface
- Indoor positioning where GPS signal is unavailable
- Voice, image, or large file transfer (LoRa bandwidth is far too low)
- Real-time collision avoidance between multiple transmitters on the same frequency
- Regulatory licensing / spectrum-management beyond ISM band guidelines
- Battery-life optimisation and low-power sleep modes
- Weatherproof / ruggedised hardware enclosure design

---

## 📁 Project Structure

```
LoRa-GPS-Tracker/
│
├── transmitter/
│   └── transmitter.ino          # Arduino TX — reads GPS, sends LoRa packets
│
├── receiver/
│   └── receiver.ino             # Arduino RX — receives packets, drives OLED
│
├── server/
│   └── server.py                # Python Flask server + PySerial reader
│
└── README.md
```

---

## 🚀 Getting Started

### 1. Wiring

**Transmitter (Arduino Uno)**

| SX1278 Pin | Arduino Pin |
|-----------|-------------|
| NSS / CS  | D10         |
| RESET     | D9          |
| DIO0      | D2          |
| MOSI      | D11         |
| MISO      | D12         |
| SCK       | D13         |

| NEO-6M Pin | Arduino Pin |
|-----------|-------------|
| TX        | D4 (SoftSerial RX) |
| RX        | D3 (SoftSerial TX) |
| VCC       | 3.3 V / 5 V |
| GND       | GND         |

**Receiver (Arduino Uno)**

| SX1278 Pin | Arduino Pin |
|-----------|-------------|
| NSS / CS  | D10         |
| RESET     | D9          |
| DIO0      | D2          |

| SSD1306 Pin | Arduino Pin |
|------------|-------------|
| SDA        | A4          |
| SCL        | A5          |
| VCC        | 3.3 V       |
| GND        | GND         |

---

### 2. Flash Arduino Firmware

1. Open **Arduino IDE**.
2. Install required libraries via *Sketch → Include Library → Manage Libraries*:
   - `LoRa` by Sandeep Mistry
   - `TinyGPS++` by Mikal Hart
   - `Adafruit SSD1306`
   - `Adafruit GFX Library`
3. Open `transmitter/transmitter.ino` → select the correct board & port → **Upload**.
4. Open `receiver/receiver.ino` → select the correct board & port → **Upload**.

---

### 3. Configure & Run the Python Server

```bash
# Install dependencies
pip install pyserial flask requests

# Edit server.py — set your receiver's fixed GPS coordinates
RECEIVER_LAT = 17.087741   # ← change to your location
RECEIVER_LNG = 82.068771   # ← change to your location

# Run the server
python server.py
```

> The server auto-detects the Arduino COM port. If auto-detection fails, manually set `PORT = 'COMx'` (Windows) or `PORT = '/dev/ttyUSBx'` (Linux/macOS) in `server.py`.

---

### 4. Open the Dashboard

Navigate to **http://localhost:5000** in your browser.

---

## 📡 Usage

### Transmitter
- Power on the TX unit outdoors (GPS requires clear sky view).
- Wait for the serial monitor to show `"LoRa TX ready"`.
- The unit will print `"Waiting for GPS fix..."` until a valid fix is acquired.
- Once fixed, packets are transmitted every **2 seconds**.
- To change the message text, type a new message in the Serial Monitor and press Enter.
  > Commas are automatically stripped from the message to protect the CSV parser.

### Receiver — OLED Mode (No Internet Required)
- The OLED displays: **Latitude**, **Longitude**, **Message**, and **RSSI**.
- Works completely offline — no PC or internet needed.

### Receiver — Web Dashboard Mode
- Connect the RX Arduino to a PC via USB.
- Run `server.py`.
- Open `http://localhost:5000`.
- The dashboard auto-refreshes every **3 seconds** and recalculates the road route every **15 seconds**.

### Dashboard Controls

| Control | Description |
|---------|-------------|
| **Road route** button | Toggle OSRM road route overlay |
| **Straight line** button | Toggle Haversine straight-line overlay |
| **GPS track history** button | Toggle the last 500-point GPS trail |
| **Recalculate route** button | Manually trigger a fresh OSRM route fetch |

### Serial Packet Format

```
DATA:<lat>,<lng>,<message>,RSSI:<value>
```

Example:
```
DATA:17.123456,82.654321,Hello Trainee!,RSSI:-87
```

---

## 🔮 Future Enhancements

- **Bi-directional communication** — allow the receiver to acknowledge packets or send commands back to the transmitter.
- **AES-128 encryption** on LoRa packets for secure data transfer.
- **LoRa Mesh / LoRaWAN gateway** integration for multi-node coverage and internet bridging.
- **Battery-powered TX** with deep-sleep modes for week-long field deployments.
- **SD-card logging** at the receiver for offline data archival.
- **Mobile companion app** (Flutter / React Native) for on-the-go monitoring.
- **Multiple transmitter support** with unique node IDs and a fleet-tracking dashboard.
- **Geofencing & SMS / email alerts** when the transmitter enters or leaves predefined zones.
- **Adaptive spreading factor (SF)** and TX power based on RSSI/SNR for optimal range vs. battery trade-off.
- **Emergency SOS button** on TX that flags the packet as high-priority.
- **Migration to ESP32** for built-in Wi-Fi/Bluetooth uplink and faster MCU.
- **Offline map tiles** (cached OSM tiles) so the dashboard works even when the receiver host has no internet.
- **Kalman filtering** of GPS data to smoothen the track and reject outliers.
- **Altitude, speed, and heading** transmission using additional GPS fields.

---

## 🏁 Conclusion

This project successfully demonstrates that **reliable, long-range, infrastructure-free communication** is achievable using affordable, license-free LoRa technology. By combining a GPS-enabled offline transmitter with a dual-mode receiver (OLED for pure-offline operation and a Flask-driven web dashboard for enriched online visualisation), the system bridges the gap between remote field operations and centralised monitoring **without depending on cellular or satellite networks for the link itself**.

The architecture is simple, low-cost, low-power, and easily extensible — making it suitable for:

- 🏔️ Asset tracking in cellular dead zones
- 🚨 Disaster response communication
- 🌾 Agricultural telemetry
- 🦁 Wildlife monitoring
- 🎓 Educational demonstrations of RF communication

The use of widely available open-source libraries (`TinyGPS++`, `LoRa`, `Flask`, `Leaflet`, `OSRM`) ensures reproducibility, while the modular design leaves clear pathways for the future enhancements outlined above.

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).

---

<div align="center">
  <sub>Built with ❤️ using LoRa · Arduino · Python · Flask · Leaflet.js</sub>
</div>
