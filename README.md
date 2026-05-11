# 📡 LoRa Long-Distance GPS Tracker

> **Offline-to-Online Communication System using LoRa SX1278**
> A low-cost, long-range, infrastructure-free GPS tracking and messaging system
> that works without internet, GSM, or any cellular network at the link itself.

[![Platform](https://img.shields.io/badge/Platform-Arduino%20Uno-00979D?logo=arduino)](https://www.arduino.cc/)
[![Radio](https://img.shields.io/badge/Radio-LoRa%20SX1278%20%40%20433%20MHz-orange)](https://www.semtech.com/products/wireless-rf/lora-core/sx1278)
[![Language](https://img.shields.io/badge/Language-C%2B%2B%20%7C%20Python-blue)](https://www.python.org/)
[![Frontend](https://img.shields.io/badge/Frontend-Leaflet.js%20%2B%20OSM-success)](https://leafletjs.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 📖 Table of Contents

1. [Overview](#-overview)
2. [Key Features](#-key-features)
3. [System Architecture](#-system-architecture)
4. [Hardware Requirements](#-hardware-requirements)
5. [Software Requirements](#-software-requirements)
6. [Wiring Diagram](#-wiring-diagram)
7. [Installation & Setup](#-installation--setup)
8. [Usage](#-usage)
9. [Packet Format](#-packet-format)
10. [Project Structure](#-project-structure)
11. [How It Works](#-how-it-works)
12. [Performance & Range](#-performance--range)
13. [Troubleshooting](#-troubleshooting)
14. [Future Enhancements](#-future-enhancements)
15. [Limitations](#-limitations)
16. [Contributing](#-contributing)
17. [License](#-license)
18. [Acknowledgements](#-acknowledgements)

---

## 🌍 Overview

This project implements a **long-range, offline-capable communication and GPS
tracking system** using LoRa (Long Range) radio technology operating in the
433 MHz ISM band.

The system consists of **two nodes**:

- 🛰️ **Transmitter (offline):** An Arduino Uno equipped with a NEO-6M GPS
  module and an SX1278 LoRa transceiver. It acquires the current GPS
  coordinates, packages them with a short text message, and broadcasts the
  packet over LoRa every 2 seconds — without any internet or cellular
  connectivity.

- 📡 **Receiver (offline + optional online):** A second Arduino Uno with an
  SX1278 LoRa transceiver and a 0.96″ SSD1306 OLED display. It receives the
  packets, displays them locally on the OLED (works **fully offline**), and
  forwards them over USB-serial to a Python Flask server that renders a live
  web dashboard with maps, road routing, signal strength, and GPS track
  history.

The **communication link between transmitter and receiver is 100 % offline**
(pure radio-frequency). Internet is **optional** — used only on the receiver
host PC for OpenStreetMap tiles and OSRM road-routing.

### 🎯 Real-World Use Cases

- Asset and personnel tracking in remote / rural / off-grid areas
- Search-and-rescue operations in disaster zones
- Wildlife and livestock monitoring
- Hiker, trekker, and expedition safety
- Drone and UAV telemetry beyond cellular coverage
- Agricultural / industrial telemetry
- Educational LoRa & embedded-systems demonstrations

---

## ✨ Key Features

| Feature | Description |
|--------|-------------|
| 📶 **Long-range RF link** | ~2–10 km line-of-sight at SF10, 433 MHz, 20 dBm |
| 🔌 **Fully offline TX** | No internet, GSM, or Wi-Fi required at transmitter |
| 📺 **Dual output at RX** | Local OLED display + optional web dashboard |
| 🗺️ **Live web map** | Leaflet.js + OpenStreetMap, auto-refreshing every 3 s |
| 🛣️ **Road routing** | OSRM-powered turn-by-turn directions between TX & RX |
| 📏 **Distance calculation** | Haversine straight-line + actual road distance |
| 📈 **Signal quality** | Live RSSI and SNR for link-budget analysis |
| 🧭 **GPS track history** | Last 500 de-duplicated points plotted on the map |
| 🔢 **Packet sequencing** | Sequence numbers enable packet-loss tracking |
| 🛡️ **Hardware CRC** | LoRa-level CRC drops corrupt packets automatically |
| 🧪 **Indoor test mode** | Jumper to send fake GPS data without satellite lock |
| ♻️ **Auto-reconnect** | Python server reconnects automatically if Arduino unplugs |

---

## 🏗️ System Architecture

```
┌─────────────────────────── TRANSMITTER (Fully Offline) ────────────────────────────┐
│                                                                                     │
│   ┌──────────────┐   SoftSerial    ┌────────────────┐    SPI    ┌────────────────┐ │
│   │  NEO-6M GPS  │ ──────────────▶ │  Arduino Uno   │ ────────▶ │   SX1278 LoRa  │ │
│   │  (Satellites)│   9600 baud     │  (TinyGPS++)   │ 10/9/2/13 │     433 MHz    │ │
│   └──────▲───────┘                 └────────────────┘ 12/11     └───────┬────────┘ │
│          │ GPS L1 signal                                                  │         │
└──────────┼──────────────────────────────────────────────────────────────  │ ────────┘
           │                                                                │
           │                              📡  RF LINK  (Offline, up to ~10 km LOS)
           │                                                                │
┌──────────┼──────────────────────────────── RECEIVER ──────────────────────│─────────┐
│          │                                                                ▼          │
│   GPS Satellites                                                ┌──────────────────┐ │
│   (TX uses)                                                     │   SX1278 LoRa    │ │
│                                                                 │       RX         │ │
│                                                                 └────────┬─────────┘ │
│                                                            SPI 10/9/2/13/12/11      │
│                                                                          ▼          │
│   ┌────────────────┐    I²C    ┌─────────────────────┐                              │
│   │  OLED SSD1306  │ ◀──────── │    Arduino Uno      │ ── USB Serial (9600) ──┐    │
│   │   128 × 64     │   0x3C    │  (Parse + Display)  │                         │    │
│   └────────────────┘  SDA/SCL  └─────────────────────┘                         │    │
│        [Offline Mode — works without any internet]                              ▼    │
│                                                                ┌──────────────────────┐
│                                                                │     Host PC          │
│                                                                │  ┌────────────────┐  │
│                                                                │  │ Python Flask   │  │
│                                                                │  │  + PySerial    │  │
│                                                                │  └───────┬────────┘  │
│                                                                │          │           │
│                                                                │   /data /history     │
│                                                                │        /route        │
│                                                                │          │           │
│                                                                │  ┌───────▼────────┐  │
│                                                                │  │ Leaflet Map    │  │
│                                                                │  │ OSM + OSRM API │  │
│                                                                │  └────────────────┘  │
│                                                                └──────────────────────┘
│                                                                  [Online Mode]        │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

**Data flow:**
`GPS Satellites → NEO-6M → Arduino TX → SX1278 TX → 📡 (Offline RF 433 MHz) → SX1278 RX → Arduino RX → {OLED Display} + {USB Serial → Python Flask → Web Dashboard}`

---

## 🔧 Hardware Requirements

### Transmitter Side
| Component | Quantity | Notes |
|----------|----------|-------|
| Arduino Uno | 1 | ATmega328P, 5 V |
| SX1278 LoRa module | 1 | 433 MHz variant |
| NEO-6M GPS module | 1 | With external active antenna |
| 433 MHz antenna | 1 | Spring or whip antenna |
| Jumper wires & breadboard | — | For prototyping |
| 5 V power supply / power bank | 1 | USB or barrel jack |

### Receiver Side
| Component | Quantity | Notes |
|----------|----------|-------|
| Arduino Uno | 1 | ATmega328P, 5 V |
| SX1278 LoRa module | 1 | 433 MHz variant |
| SSD1306 OLED display | 1 | 128 × 64, I²C, address 0x3C |
| 433 MHz antenna | 1 | Spring or whip antenna |
| Jumper wires & breadboard | — | For prototyping |
| USB cable | 1 | To host PC |
| Host PC | 1 | Windows / Linux / macOS |

> 💡 **Tip:** Use 3.3 V regulators / level shifters for SX1278 if your Uno
> provides only 5 V on its logic pins. Many SX1278 breakouts include onboard
> regulation and level-shifting — check your specific board.

---

## 💻 Software Requirements

### Arduino IDE Libraries
Install the following from **Sketch → Include Library → Manage Libraries…**

- `LoRa` by Sandeep Mistry
- `TinyGPSPlus` by Mikal Hart
- `Adafruit GFX Library`
- `Adafruit SSD1306`
- `SoftwareSerial` *(built-in)*
- `Wire` *(built-in)*
- `SPI` *(built-in)*

### Python Dependencies (host PC)
- Python **3.8+**
- See [`requirements.txt`](requirements.txt)

```
pyserial>=3.5
flask>=2.0
requests>=2.28
```

---

## 🔌 Wiring Diagram

### Transmitter (Arduino Uno)

**SX1278 LoRa → Arduino Uno**
| LoRa Pin | Uno Pin |
|---------|---------|
| VCC | 3.3 V |
| GND | GND |
| MISO | D12 |
| MOSI | D11 |
| SCK | D13 |
| NSS / CS | D10 |
| RESET | D9 |
| DIO0 | D2 |

**NEO-6M GPS → Arduino Uno**
| GPS Pin | Uno Pin |
|--------|---------|
| VCC | 5 V (or 3.3 V depending on module) |
| GND | GND |
| TX | D4 *(SoftwareSerial RX)* |
| RX | D3 *(SoftwareSerial TX)* |

**Optional:** D5 → GND jumper enables **Indoor Test Mode**.

### Receiver (Arduino Uno)

**SX1278 LoRa → Arduino Uno** *(same as transmitter)*

**SSD1306 OLED → Arduino Uno**
| OLED Pin | Uno Pin |
|---------|---------|
| VCC | 5 V |
| GND | GND |
| SDA | A4 |
| SCL | A5 |

---

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/<your-username>/lora-gps-tracker.git
cd lora-gps-tracker
```

### 2. Upload Transmitter Firmware
1. Open `tx/tx.ino` in Arduino IDE
2. Select **Board → Arduino Uno** and the correct **Port**
3. Install all required libraries (see [Software Requirements](#-software-requirements))
4. Click **Upload**
5. Open Serial Monitor at **9600 baud** to confirm `LoRa TX ready`

### 3. Upload Receiver Firmware
1. Open `rx/rx.ino` in Arduino IDE
2. Select **Board → Arduino Uno** and the correct **Port**
3. Click **Upload**
4. Confirm the OLED shows `LoRa RX ready / Waiting for data...`

### 4. Configure the Python Server
Edit the **CONFIG** block at the top of `server/server.py`:
```python
RECEIVER_LAT   = 17.087741       # ← your real receiver latitude
RECEIVER_LNG   = 82.068771       # ← your real receiver longitude
PREFERRED_PORT = "COM11"         # ← e.g. "/dev/ttyUSB0" on Linux
```

### 5. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 6. Run the Server
```bash
python server/server.py
```
Then open your browser to **http://localhost:5000**

---

## 🎮 Usage

### Normal Operation
1. Power the **transmitter** outdoors (so GPS can lock — takes 1–5 minutes on cold start)
2. Power the **receiver** and connect it to your PC via USB
3. Run `python server/server.py`
4. Open `http://localhost:5000`
5. Watch the transmitter marker move on the map in real time!

### Sending a Custom Message
1. Open the **Arduino IDE Serial Monitor** on the transmitter (9600 baud)
2. Type any message and press **Enter**
3. The transmitter starts broadcasting the new message immediately
4. The new message appears on the receiver OLED and on the web dashboard

### Indoor Test Mode (No GPS Required)
1. Power the transmitter **off**
2. Connect a jumper wire between **D5 and GND**
3. Power on the transmitter — it now sends **fake GPS coordinates**
4. Verify the receiver, OLED, and web dashboard all work
5. Remove the jumper for real outdoor testing

---

## 📦 Packet Format

### Over-the-air (LoRa → CSV)
```
<seq>,<lat>,<lng>,<message>
```
**Example:**
```
42,17.385012,78.486710,Hello Trainee!
```

### USB Serial (RX Arduino → Python server)
```
DATA:<seq>,<lat>,<lng>,<message>,RSSI:<rssi>,SNR:<snr>
```
**Example:**
```
DATA:42,17.385012,78.486710,Hello Trainee!,RSSI:-87,SNR:9.25
```

| Field | Type | Description |
|------|------|-------------|
| `seq` | uint32 | Monotonic packet counter from transmitter |
| `lat` | float (6 dp) | Latitude, decimal degrees |
| `lng` | float (6 dp) | Longitude, decimal degrees |
| `message` | string ≤ 40 chars | User text (commas stripped) |
| `RSSI` | int (dBm) | Received Signal Strength Indicator |
| `SNR` | float (dB) | Signal-to-Noise Ratio |

---

## 📁 Project Structure

```
lora-gps-tracker/
├── tx/
│   └── tx.ino              # Transmitter firmware (Arduino Uno)
├── rx/
│   └── rx.ino              # Receiver firmware (Arduino Uno)
├── server/
│   └── server.py           # Flask web server + serial reader
├── docs/
│   ├── architecture.png    # System architecture diagram
│   ├── wiring-tx.png       # TX wiring diagram
│   ├── wiring-rx.png       # RX wiring diagram
│   └── screenshots/        # Web dashboard screenshots
├── requirements.txt        # Python dependencies
├── .gitignore
├── LICENSE
└── README.md
```

---

## ⚙️ How It Works

### 🛰️ Transmitter Workflow
1. **Boot:** Initialise LoRa (433 MHz, SF10, BW 125 kHz, CR 4/8, CRC on, 20 dBm) and start GPS serial.
2. **GPS parsing:** Continuously feed NMEA sentences from NEO-6M into TinyGPS++.
3. **Trigger:** Every 2 seconds, if a valid GPS fix is available, build a packet.
4. **Transmit:** Broadcast the CSV packet via LoRa.
5. **Idle:** During the 2-second window, accept new text messages from USB-serial.

### 📡 Receiver Workflow
1. **Boot:** Initialise LoRa with matching radio parameters and the SSD1306 OLED.
2. **Listen:** Continuously poll `LoRa.parsePacket()` for incoming packets.
3. **Capture RSSI/SNR:** Immediately on reception, while values are still accurate.
4. **Parse:** Split CSV by commas, validate lat/lng ranges, update internal state.
5. **Display:** Refresh the OLED with lat, lng, message, RSSI, SNR, packet stats.
6. **Forward:** Print structured `DATA:` line over USB-serial for the Python server.
7. **Stale-link detection:** If no packet for > 10 s, show `** No signal **` on OLED.

### 🐍 Python Server Workflow
1. **Auto-detect** the Arduino COM port (Windows/Linux/macOS).
2. **Serial reader thread** continuously reads lines, parses, and updates shared state under a lock.
3. **GPS history** is de-duplicated — only points > 5 m from the last are stored (max 500).
4. **Flask routes:**
   - `GET /` → render the live dashboard
   - `GET /data` → latest packet (JSON)
   - `GET /history` → all GPS history points (JSON)
   - `GET /route` → OSRM road route between TX and RX (JSON)
5. **Frontend** polls every 3 s and re-renders the map, cards, and route panel.

---

## 📈 Performance & Range

### LoRa Radio Configuration

| Parameter | Value | Notes |
|----------|-------|-------|
| Frequency | 433 MHz | ISM band |
| Spreading Factor | SF10 | Balance of range vs. speed |
| Bandwidth | 125 kHz | Standard LoRa BW |
| Coding Rate | 4/8 | Maximum forward-error correction |
| TX Power | 20 dBm | 100 mW via PA_BOOST |
| CRC | Enabled | Hardware CRC drops corrupt packets |
| Air-time per packet | ≈ 350 ms | For ~40-byte payload |
| Theoretical bitrate | ≈ 290 bps | After overhead |

### Expected Range
- **Urban / dense:** 1–3 km
- **Suburban:** 3–5 km
- **Line-of-sight, elevated antennas:** 5–10+ km
- **Heavily obstructed (buildings, hills):** < 1 km

> ⚠️ **Range depends heavily on antennas.** A proper 433 MHz tuned antenna
> (helical, dipole, or yagi) with a clean ground plane is the single biggest
> factor for achievable distance.

---

## 🛠️ Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `LoRa init failed!` | Wrong wiring / SPI pins | Re-check NSS, RESET, DIO0 |
| OLED is blank | Wrong I²C address (`0x3D` instead of `0x3C`) | Change `OLED_I2C_ADDR` in `rx.ino` |
| GPS never gets a fix indoors | NEO-6M needs sky view | Test outdoors or use indoor test mode |
| Receiver sees nothing | TX and RX LoRa params mismatch | Confirm SF, BW, CR, CRC match exactly |
| Python: "could not open port" | Wrong COM port | Update `PREFERRED_PORT` in `server.py` |
| Map tiles don't load | No internet on host PC | OLED still works; map needs internet |
| `OSRM error` on route panel | OSRM public server temporarily down | Wait or self-host OSRM |
| Garbled serial output | Baud rate mismatch | Both ends must be **9600 baud** |
| Frequent missed packets | Antenna mismatch / interference | Use proper 433 MHz antennas, move away from Wi-Fi routers |

---

## 🔮 Future Enhancements

- 🔁 **Bi-directional communication** — RX → TX ACKs and commands
- 🔒 **AES-128 encryption** of LoRa payloads
- 🌐 **LoRaWAN gateway** integration for multi-node coverage
- 🔋 **Deep-sleep modes** on TX for week-long battery life
- 💾 **SD-card logging** at the receiver for offline archival
- 📱 **Mobile app** (Flutter / React Native)
- 🗂️ **Multi-transmitter support** with unique node IDs
- 🚨 **Geofencing alerts** via SMS or email
- 📡 **Adaptive SF / TX power** based on RSSI/SNR
- 🆘 **Hardware SOS button** with priority packet flag
- ⚡ **Migration to ESP32** for built-in Wi-Fi uplink and faster MCU
- 🗺️ **Offline cached map tiles** so the dashboard works fully offline
- 🧭 **Kalman filter** to smooth noisy GPS readings
- 📊 **Altitude, speed, heading** in the transmitted packet

---

## 🚧 Limitations

- 🚫 **One-way only** — communication is strictly TX → RX in this version
- 🚫 **No encryption** — packets are sent in plain text over the air
- 🚫 **No mesh / multi-hop** — single transmitter to single receiver
- 🚫 **GPS-only positioning** — won't work indoors / underground
- 🚫 **Low bandwidth** — voice, images, or large files are not feasible on LoRa
- 🚫 **No collision avoidance** — multiple transmitters on the same channel will interfere
- ⚠️ **Regulatory note (India):** 433 MHz is technically allocated to amateur
  radio. For unlicensed LoRa deployment in India, the legal band is
  **865–867 MHz**. This project uses 433 MHz for educational / experimental
  purposes only.

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

For major changes, please open an issue first to discuss what you would like to change.

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgements

- **Sandeep Mistry** — for the excellent [LoRa Arduino library](https://github.com/sandeepmistry/arduino-LoRa)
- **Mikal Hart** — for [TinyGPSPlus](https://github.com/mikalhart/TinyGPSPlus)
- **Adafruit** — for the [GFX](https://github.com/adafruit/Adafruit-GFX-Library) and [SSD1306](https://github.com/adafruit/Adafruit_SSD1306) libraries
- **OpenStreetMap** contributors — for free, open map data
- **OSRM Project** — for the open-source routing engine
- **Leaflet.js** — for the elegant interactive map library
- **Semtech** — for the LoRa modulation technology

---

<div align="center">

### ⭐ If you found this project useful, please consider giving it a star! ⭐

**Built with ❤️ for the maker, IoT, and LoRa communities**

</div>
