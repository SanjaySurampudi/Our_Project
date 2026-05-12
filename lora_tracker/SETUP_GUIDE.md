# LoRa GPS Tracker - Complete Setup Guide

## 🎯 What This Project Does

This is a complete GPS tracking system using LoRa (Long Range) radio:
- **Transmitter (TX)**: Arduino with GPS module that sends location wirelessly
- **Receiver (RX)**: Arduino with OLED display that receives and shows data
- **Web Dashboard**: Python Flask server showing live map with routes

## 📦 What's Included

```
lora_tracker/
├── server.py                    # Flask server (reads serial, serves web dashboard)
├── requirements.txt             # Python dependencies
├── SETUP_GUIDE.md              # This file!
├── README.md                    # Technical documentation
│
├── templates/
│   └── index.html              # Dashboard HTML template
│
├── static/
│   ├── style.css               # Dashboard styling
│   └── app.js                  # Dashboard JavaScript (map, routes, updates)
│
├── arduino/
│   ├── TX/
│   │   └── TX.ino              # Transmitter code (GPS + LoRa)
│   └── RX/
│       └── RX.ino              # Receiver code (LoRa + OLED + USB serial)
│
└── tests/
    ├── test_parser.py          # 29 parser tests
    ├── test_routes.py          # 13 Flask route tests
    └── test_integration_serial.py  # 13 integration tests
```

---

## ⚙️ Hardware Requirements

### Transmitter (TX) - Mobile Unit
- Arduino Uno/Nano/Mega
- LoRa module (SX1278, 433MHz)
- GPS module (NEO-6M or similar with TinyGPS++ support)
- Power source (battery, power bank, or 9V battery)

### Receiver (RX) - Fixed Base Station
- Arduino Uno/Nano/Mega
- LoRa module (SX1278, 433MHz)
- OLED display (128x64, SSD1306, I2C)
- USB cable to computer (stays connected)

### Computer
- Windows/Linux/macOS
- Python 3.7+
- Internet connection (for map tiles and route calculation)

---

## 🚀 Step-by-Step Setup

### **STEP 1: Extract Project Files**

1. Extract `lora_tracker_FINAL.zip` to your computer
2. You should have a folder: `lora_tracker/` with all files

---

### **STEP 2: Install Python Dependencies**

Open Command Prompt (Windows) or Terminal (Mac/Linux):

```bash
cd path/to/lora_tracker
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed flask-X.X.X pyserial-X.X.X requests-X.X.X
```

**If you get errors:**
- Windows: Make sure Python is in PATH
- Mac/Linux: Try `pip3` instead of `pip`
- If still fails: `python -m pip install -r requirements.txt`

---

### **STEP 3: Configure Your Receiver Location**

1. Open `server.py` in a text editor (Notepad, VS Code, etc.)
2. Find lines 42-44 near the top:

```python
RECEIVER_LAT = 17.087741
RECEIVER_LNG = 82.068771
```

3. **Change these to YOUR location:**
   - Open Google Maps
   - Right-click on your receiver's location
   - Copy the coordinates (example: `19.076090, 72.877426`)
   - First number = RECEIVER_LAT
   - Second number = RECEIVER_LNG

4. Save the file

---

### **STEP 4: Upload Transmitter Code**

1. **Open Arduino IDE**
2. **File → Open** → Navigate to `arduino/TX/TX.ino`
3. **Connect transmitter Arduino** via USB
4. **Tools → Board** → Select your Arduino model
5. **Tools → Port** → Select COM port (Windows) or /dev/ttyUSB0 (Linux)
6. **Click Upload** (➜ button)
7. Wait for "Done uploading"
8. ✅ **Transmitter is ready!**

**Verify it works:**
- Tools → Serial Monitor
- Select 9600 baud
- You should see: "Waiting for GPS fix..."

---

### **STEP 5: Upload Receiver Code**

1. **In Arduino IDE:**
2. **File → Open** → Navigate to `arduino/RX/RX.ino`
3. **Disconnect transmitter, connect receiver Arduino** via USB
4. **Tools → Board** → Select your Arduino model
5. **Tools → Port** → Select COM port
6. **Click Upload** (➜ button)
7. Wait for "Done uploading"
8. **⚠️ KEEP RECEIVER CONNECTED** - it needs to stay plugged in
9. ✅ **Receiver is ready!**

**Verify it works:**
- Tools → Serial Monitor
- Select 9600 baud
- You should see: "LoRa RX ready"
- OLED display should show: "Waiting for data..."

---

### **STEP 6: Start the Python Server**

**Open Command Prompt/Terminal:**

```bash
cd path/to/lora_tracker
python server.py
```

**Expected output:**
```
==================================================
  LoRa Long Distance Tracker
  Open http://localhost:5000
==================================================
Connecting to COM5...
Connected to COM5 - waiting for data...
```

**If it says "Could not auto-detect":**
```bash
# Windows
set LORA_PORT=COM5
python server.py

# Mac/Linux
export LORA_PORT=/dev/ttyUSB0
python server.py
```

⚠️ **Keep this window open!** Don't close it while using the tracker.

---

### **STEP 7: Open the Dashboard**

1. Open web browser (Chrome, Firefox, Edge, Safari)
2. Go to: `http://localhost:5000`
3. You should see:
   - A map with a blue dot (your receiver location)
   - Cards showing: "Waiting for LoRa data..."

---

### **STEP 8: Power Up Transmitter and Test**

1. **Disconnect transmitter from computer**
2. **Power it using:**
   - USB power bank, OR
   - 9V battery with adapter, OR
   - Any USB power source

3. **Take transmitter OUTSIDE**
   - GPS needs clear view of sky
   - Won't work indoors/under roof
   - Wait 1-3 minutes for GPS to lock

4. **Check Serial Monitor (optional):**
   - Reconnect transmitter to computer briefly
   - Open Serial Monitor (9600 baud)
   - You should see:
     ```
     Sending: 0,19.076090,72.877426,Hello Trainee! (GPS age=234ms)
     Sending: 1,19.076095,72.877430,Hello Trainee! (GPS age=189ms)
     ```

5. **Check Dashboard:**
   - Red dot appears on map (transmitter location)
   - Cards update with coordinates, RSSI, sequence number
   - Orange dashed line (straight distance)
   - Green solid line (road route with directions)
   - Blue dotted line (GPS track history)

---

## 🎛️ Dashboard Features

### **Map Elements:**
- 🔵 **Blue marker** = Receiver (your fixed location)
- 🔴 **Red marker** = Transmitter (live GPS location)
- 🟠 **Orange dashed line** = Straight-line distance
- 🟢 **Green solid line** = Road route with turn-by-turn directions
- 🔵 **Blue dotted line** = GPS track history (breadcrumb trail)

### **Information Cards:**
- **Coordinates**: Current lat/lng of transmitter
- **Message**: Custom text from transmitter
- **Signal**: RSSI (signal strength in dBm)
- **Track Points**: Number of GPS points recorded
- **Sequence**: Packet sequence number
- **Dropped**: Number of packets lost

### **Controls:**
- **Toggle Road Route**: Show/hide green road line
- **Toggle Straight Line**: Show/hide orange distance line
- **Toggle GPS Track**: Show/hide blue history trail
- **Recalculate Route**: Force immediate route update

---

## 🔧 Customization

### **Change Transmitter Message**

1. Connect transmitter to computer
2. Open Serial Monitor (9600 baud)
3. Type your message and press Enter
4. Message updates immediately

**Example:**
```
Status: Moving north
```

**Note:** Commas are automatically replaced with spaces. You'll see:
```
Message updated: Status: Moving north
  WARNING: Commas replaced with spaces to protect CSV format
```

### **Access Dashboard from Phone (Same WiFi)**

**Windows:**
```cmd
set FLASK_HOST=0.0.0.0
python server.py
```

**Mac/Linux:**
```bash
export FLASK_HOST=0.0.0.0
python server.py
```

Then on your phone:
1. Connect to same WiFi as computer
2. Find your computer's IP (ipconfig or ifconfig)
3. Open browser: `http://192.168.1.XXX:5000`

⚠️ **Warning:** This exposes your GPS data to anyone on your WiFi!

---

## ❓ Troubleshooting

### **Problem: "Could not auto-detect the LoRa receiver"**

**Solution 1 - Check USB connection:**
- Is receiver Arduino plugged in?
- Try a different USB cable
- Try a different USB port

**Solution 2 - Set port manually:**
```bash
# Find your port:
# Windows: Device Manager → Ports (COM & LPT)
# Mac/Linux: ls /dev/tty*

# Then set it:
set LORA_PORT=COM5    # Windows
export LORA_PORT=/dev/ttyUSB0    # Mac/Linux

python server.py
```

---

### **Problem: Dashboard shows "Waiting for LoRa data..." forever**

**Check these:**

1. **Is transmitter powered?**
   - Red LED should be on

2. **Does transmitter have GPS fix?**
   - Connect to Serial Monitor
   - Should see "Sending: ..." messages
   - If "Waiting for GPS fix..." → go outside

3. **Are both LoRa modules on same frequency?**
   - Both should be 433MHz (or same frequency)
   - Check TX.ino and RX.ino: `LoRa.begin(433E6)`

4. **Is receiver getting LoRa packets?**
   - Check receiver OLED display
   - Should show coordinates and RSSI
   - If blank → LoRa wiring issue

---

### **Problem: "GPS fix is stale" messages**

**Cause:** GPS module lost satellite signal

**Solutions:**
- Go to open area (away from buildings/trees)
- Check GPS antenna is connected
- Wait 2-3 minutes for GPS to re-lock
- GPS doesn't work indoors!

---

### **Problem: Map tiles don't load (gray squares)**

**Cause:** No internet connection

**What happens:**
- Yellow warning banner appears
- All features still work (markers, routes, data)
- Only background map tiles are missing

**Solution:**
- Connect to internet
- Refresh page
- Tiles will load automatically

---

### **Problem: High packet drops**

**Possible causes:**
1. **Transmitter too far away**
   - LoRa range: 500m-2km (open area)
   - Obstacles reduce range

2. **Interference**
   - Move away from WiFi routers
   - Avoid metal buildings

3. **Low transmitter power**
   - Check battery voltage
   - Use fresh batteries

---

### **Problem: OLED display blank**

**If receiver still works (data on dashboard):**
- OLED may have loose I2C connection
- Check SDA/SCL wires
- Receiver continues without display

**The code handles this gracefully:**
- Prints "OLED init failed - continuing without display"
- Retries every 30 seconds
- Serial data still flows to computer

---

## 📊 Understanding the Data

### **RSSI (Signal Strength)**
- Measured in dBm (negative numbers)
- **-30 to -60 dBm**: Excellent signal
- **-60 to -80 dBm**: Good signal  
- **-80 to -100 dBm**: Weak signal
- **Below -100 dBm**: Very weak, may lose packets

### **Sequence Numbers**
- Starts at 0, increments each packet
- Used to detect dropped packets
- Gap in sequence = lost packet
- Example: 0, 1, 2, 5, 6 → dropped 3 and 4

### **GPS Age**
- How old the GPS reading is (milliseconds)
- **< 2000ms**: Fresh, current location
- **> 2000ms**: Stale, transmitter rejects it

---

## 🧪 Testing (Optional)

Run the test suite to verify everything works:

```bash
cd lora_tracker
python -m unittest discover -s tests -v
```

**Expected output:**
```
test_dropped_packet_detection ... ok
test_first_packet_does_not_count_as_dropped ... ok
test_history_capped_at_max ... ok
... (51 tests total)

----------------------------------------------------------------------
Ran 51 tests in 0.5s

OK
```

---

## ✅ All Fixed Issues in This Version

This final version includes ALL 14 improvements:

1. ✅ HTML/CSS/JS extracted to separate files
2. ✅ 51 unit and integration tests
3. ✅ Packet format fixed (comma before RSSI, sequence numbers)
4. ✅ Port detection (no silent COM11 fallback)
5. ✅ Security (binds to 127.0.0.1 by default)
6. ✅ Smart route recalculation (only when moved >5 meters)
7. ✅ Comma replacement warning in TX.ino
8. ✅ Offline map tile fallback (warning banner)
9. ✅ Serial auto-reconnect (polls every 10 seconds)
10. ✅ RX.ino comment corrected (0-10 digits)
11. ✅ Performance: collections.deque for O(1) operations
12. ✅ Unified haversine function (no duplication)
13. ✅ OLED error handling (continues without display)
14. ✅ uint32_t wrap documented (136-year wrap)

---

## 📞 Quick Reference

### **Startup Sequence**
```bash
1. Upload TX.ino to transmitter Arduino
2. Upload RX.ino to receiver Arduino (keep connected)
3. Edit RECEIVER_LAT/RECEIVER_LNG in server.py
4. Run: python server.py
5. Open: http://localhost:5000
6. Power transmitter, go outside
7. Watch live tracking!
```

### **Important Ports**
- **Serial Monitor**: 9600 baud
- **Web Dashboard**: http://localhost:5000
- **LoRa Frequency**: 433 MHz (both TX and RX)

### **Pin Connections**
Check your Arduino + LoRa module documentation for exact pins.

**Common LoRa pins:**
- NSS/CS → D10
- RST → D9
- DIO0 → D2

**GPS (TX) SoftwareSerial:**
- GPS TX → Arduino D4
- GPS RX → Arduino D3

**OLED (RX) I2C:**
- SDA → A4 (Uno) or SDA pin
- SCL → A5 (Uno) or SCL pin

---

## 🎉 You're Ready!

Follow the 8 steps above, and you'll have a working GPS tracker with:
- Live web dashboard
- Real-time map updates
- Turn-by-turn route directions
- Signal strength monitoring
- Packet drop detection
- Complete error handling

**Enjoy your LoRa GPS Tracker!** 🚀
