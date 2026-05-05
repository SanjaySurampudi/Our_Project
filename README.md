<div align="center">

# 📡 LoRa GPS Emergency Communication System

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=22&pause=1000&color=1D9E75&center=true&vCenter=true&width=600&lines=Wireless+GPS+Tracker+via+LoRa+SX1278;No+Internet.+No+SIM.+Just+Radio+Waves.;Real-Time+Map+%2B+OLED+Display;Built+with+Arduino+UNO+%26+Python" alt="Typing SVG" />

<br/>

[![Arduino](https://img.shields.io/badge/Arduino-UNO-00979D?style=for-the-badge&logo=arduino&logoColor=white)](https://www.arduino.cc/)
[![Python](https://img.shields.io/badge/Python-Flask-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://flask.palletsprojects.com/)
[![LoRa](https://img.shields.io/badge/LoRa-SX1278_433MHz-1D9E75?style=for-the-badge)](https://www.semtech.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-SanjaySurampudi-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/SanjaySurampudi)

<br/>

> **Transmit GPS coordinates and text messages wirelessly over 2–5 km**  
> No internet. No SIM card. No infrastructure needed.  
> Built as a B.Tech ECE project at **Aditya University, Surampalem** 🎓

<br/>

---

</div>

## 🗺️ Live Demo

<div align="center">

| 🌐 Web Dashboard | 📟 OLED Display |
|:---:|:---:|
| ![Website](assets/website_screenshot.png) | ![OLED](assets/oled_display.png) |
| Real-time map with live GPS marker | Coordinates + Message + RSSI |

</div>

---

## ✨ Features

| Feature | Details |
|---|---|
| 📡 **Wireless Range** | 2–5 km line of sight at 433 MHz |
| 🛰️ **GPS Tracking** | Real coordinates from NEO-6M module |
| 💬 **Text Messaging** | Send custom text alongside GPS data |
| 🌐 **Live Web Dashboard** | Interactive OpenStreetMap with moving marker |
| 📟 **OLED Display** | Shows data on receiver side instantly |
| 🔌 **No Internet Needed** | Pure LoRa RF — works in disaster zones |
| 🐍 **Python Server** | Lightweight Flask server, runs on any laptop |
| 🛡️ **Packet Filtering** | Corrupted LoRa packets auto-filtered |

---

## 🏗️ System Architecture

```
╔══════════════════════════════╗                ╔══════════════════════════════╗
║       TRANSMITTER SIDE       ║                ║        RECEIVER SIDE         ║
║                              ║                ║                              ║
║  ┌─────────┐                 ║                ║        ┌──────────────────┐  ║
║  │ NEO-6M  │  UART (pins3,4) ║                ║        │  OLED SSD1306    │  ║
║  │   GPS   │──────────────►  ║                ║        │  (I2C · A4/A5)   │  ║
║  └─────────┘                 ║                ║        └──────────────────┘  ║
║       │                      ║                ║                ▲             ║
║       ▼                      ║                ║                │             ║
║  ┌───────────┐               ║                ║       ┌────────────────┐     ║
║  │  Arduino  │               ║   433 MHz RF   ║       │  Arduino UNO   │     ║
║  │    UNO    │               ║ ◄════════════► ║       │   (Receiver)   │     ║
║  └───────────┘               ║                ║       └────────────────┘     ║
║       │ SPI                  ║                ║                │ SPI         ║
║       ▼                      ║                ║                ▼             ║
║  ┌──────────┐                ║                ║       ┌────────────────┐     ║
║  │  LoRa    │  =====════════════════════════════====► │  LoRa SX1278   │     ║
║  │ SX1278   │                ║                ║       │  (RX Module)   │     ║
║  └──────────┘                ║                ║       └────────────────┘     ║
╚══════════════════════════════╝                ║                │ USB Serial  ║
                                                ║                ▼             ║
                                                ║       ┌────────────────┐     ║
                                                ║       │  Python Flask  │     ║
                                                ║       │    Server      │     ║
                                                ║       └────────────────┘     ║
                                                ║                │             ║
                                                ║                ▼             ║
                                                ║       ┌────────────────┐     ║
                                                ║       │  Web Browser   │     ║
                                                ║       │  (Live Map)    │     ║
                                                ║       └────────────────┘     ║
                                                ╚══════════════════════════════╝
```

---

## 🛒 Hardware Required

### 📤 Transmitter Side
| Component | Qty | Notes |
|---|---|---|
| Arduino UNO | 1 | Any clone works |
| GPS NEO-6M | 1 | Include antenna |
| LoRa SX1278 433 MHz | 1 | Include antenna |
| Breadboard + Jumper Wires | — | Male-to-male |

### 📥 Receiver Side
| Component | Qty | Notes |
|---|---|---|
| Arduino UNO | 1 | Any clone works |
| LoRa SX1278 433 MHz | 1 | Include antenna |
| OLED 0.96" SSD1306 I2C | 1 | 128×64 pixels |
| Breadboard + Jumper Wires | — | — |
| PC / Laptop | 1 | Runs Flask server |

---

## 🔌 Pin Connections

### LoRa SX1278 → Arduino UNO *(both TX and RX boards)*

> ⚠️ **Critical:** Power LoRa from **3.3V only**. Connecting to 5V will permanently damage the module!

| LoRa Pin | Arduino Pin |
|---|---|
| VCC | **3.3V** ⚠️ |
| GND | GND |
| SCK | 13 |
| MISO | 12 |
| MOSI | 11 |
| NSS (CS) | 10 |
| RST | 9 |
| DIO0 | 2 |

### GPS NEO-6M → Arduino UNO *(TX side only)*

| GPS Pin | Arduino Pin |
|---|---|
| VCC | 5V |
| GND | GND |
| TX | Pin 4 |
| RX | Pin 3 |

### OLED SSD1306 → Arduino UNO *(RX side only)*

| OLED Pin | Arduino Pin |
|---|---|
| VCC | 3.3V or 5V |
| GND | GND |
| SDA | A4 |
| SCL | A5 |

---

## 💾 Software Setup

### 1️⃣ Arduino Libraries

Open Arduino IDE → `Sketch → Include Library → Manage Libraries` and install:

```
✅ TinyGPS++          by Mikal Hart
✅ LoRa               by Sandeep Mistry
✅ Adafruit SSD1306   by Adafruit
✅ Adafruit GFX       by Adafruit
✅ SoftwareSerial     (built-in — no install needed)
```

### 2️⃣ Python Dependencies

```bash
pip install flask pyserial
```

---

## 📂 Project Structure

```
lora-gps-tracker/
│
├── 📁 transmitter/
│   └── transmitter.ino        # Upload to TX Arduino (GPS side)
│
├── 📁 receiver/
│   └── receiver.ino           # Upload to RX Arduino (OLED side)
│
├── 📁 server/
│   └── server.py              # Run on PC — serves live web dashboard
│
├── 📁 assets/
│   ├── website_screenshot.png
│   ├── oled_display.png
│   └── hardware_setup.png
│
└── README.md
```

---

## 🚀 How to Run

### Step 1 — Upload Arduino Code

```bash
# 1. Open transmitter/transmitter.ino in Arduino IDE
# 2. Connect TX Arduino via USB → Tools → Port → select COM port
# 3. Click Upload → wait for "Done uploading"
# 4. Disconnect TX, connect RX Arduino
# 5. Open receiver/receiver.ino → Upload
```

> ⚠️ Always close Arduino Serial Monitor before running server.py — they cannot share the same COM port!

### Step 2 — Start the Web Server

```bash
cd server
python server.py
```

Expected terminal output:
```
========================================
  Server starting...
  Open http://localhost:5000 in your browser
========================================
Auto-detected Arduino on: COM11
Connected! Waiting for data...

RECEIVED: DATA:17.087742,82.068771,Hello from tracker!
  ✓ Website updated: lat=17.087742 lng=82.068771
```

### Step 3 — Open the Dashboard

```
http://localhost:5000
```

🎉 A live map appears with a pin at your GPS location — updating every 2 seconds!

---

## 📦 Data Packet Format

Simple, lightweight CSV format over LoRa:

```
Transmitter → LoRa:       17.087742,82.068771,Hello from tracker!
Receiver   → Serial: DATA:17.087742,82.068771,Hello from tracker!,RSSI:-65
```

| Field | Example | Description |
|---|---|---|
| Latitude | `17.087742` | GPS latitude (6 decimal places) |
| Longitude | `82.068771` | GPS longitude (6 decimal places) |
| Message | `Hello from tracker!` | Custom text payload |
| RSSI | `-65` | Signal strength in dBm |

---

## 🧪 Testing Without GPS / OLED

Test the full LoRa → Website pipeline with just two Arduinos and two LoRa modules using hardcoded coordinates:

```cpp
// In transmitter.ino — replace GPS with fake coordinates
float lat = 17.0877;
float lng = 82.0688;
String textMessage = "Test message from LoRa!";
```

The website and server.py work identically with real or simulated GPS data.

---

## 🐛 Troubleshooting

| ❌ Problem | ✅ Fix |
|---|---|
| `Access is denied` on COM port | Close Serial Monitor and stop server.py before uploading |
| `LoRa init failed!` | Check wiring — VCC must be **3.3V not 5V** |
| Website shows "Waiting for LoRa data..." | Serial Monitor must be closed while server.py is running |
| Garbage `DATA:?` lines | Normal — server.py auto-filters corrupted packets |
| GPS no fix | Take module outdoors or near window — cold fix takes 1–2 min |
| OLED showing nothing | Try I2C address `0x3D` instead of `0x3C` in receiver.ino |
| Modules not communicating | Confirm both set to `433E6` frequency in code |

---

## 📊 Project Stats

| Metric | Value |
|---|---|
| LoRa Frequency | 433 MHz |
| Wireless Range | 2–5 km (line of sight) |
| Update Interval | Every 2–3 seconds |
| Data Packet Size | ~40–60 bytes |
| TX Arduino Flash Used | 53% (17410 / 32256 bytes) |
| TX Arduino RAM Used | 33% (690 / 2048 bytes) |
| End-to-end Latency | ~2 seconds |

---

## 🔮 Future Improvements

- [ ] 🔐 AES-128 encryption for secure transmissions
- [ ] 📶 ESP8266/ESP32 for standalone WiFi dashboard (no PC needed)
- [ ] 🗺️ Multi-node tracking — monitor several transmitters on one map
- [ ] 💾 SQLite database to store and replay GPS track history
- [ ] 📱 Mobile app (Flutter/React Native) for field use
- [ ] 🔋 Solar-powered transmitter for remote deployment
- [ ] 📲 SMS alert via GSM when tracker exits a geofence

---

## 🎯 Use Cases

```
🚨 Disaster Relief     — Works when cell towers are down
🌲 Forest Rangers      — Track personnel in remote areas
🎓 IoT Education       — Learn LoRa, GPS, Arduino, Flask together
🚗 Anti-theft Tracking — Vehicle tracking in rural/offline zones
🏕️ Trekking Safety    — Emergency beacon for hikers
⚡ Zero Infrastructure — Works anywhere on Earth
```

---

## 📚 References & Libraries

- [TinyGPS++](https://github.com/mikalhart/TinyGPSPlus) — GPS NMEA parser by Mikal Hart
- [Arduino LoRa](https://github.com/sandeepmistry/arduino-LoRa) — LoRa driver by Sandeep Mistry
- [Adafruit SSD1306](https://github.com/adafruit/Adafruit_SSD1306) — OLED display library
- [Leaflet.js](https://leafletjs.com/) — Open-source interactive map library
- [OpenStreetMap](https://www.openstreetmap.org/) — Free map tile provider
- [Flask](https://flask.palletsprojects.com/) — Lightweight Python web framework

---

## 📄 License

```
MIT License — Free to use, modify, and distribute with attribution.
```

---

<div align="center">


<br/>

[![GitHub](https://img.shields.io/badge/GitHub-SanjaySurampudi-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/SanjaySurampudi)

<br/>

*Built with ❤️, Arduino UNO, LoRa SX1278, GPS NEO-6M, and a lot of debugging*

<br/>

---

### ⭐ If this project helped you, please give it a star on GitHub! ⭐

*Your support motivates further development* 🙏

</div>
