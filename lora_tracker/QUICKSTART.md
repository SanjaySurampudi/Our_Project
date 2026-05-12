# 🚀 QUICK START - LoRa GPS Tracker

## ⚡ 8 Steps to Live Tracking

### 1️⃣ Install Dependencies
```bash
cd lora_tracker
pip install -r requirements.txt
```

### 2️⃣ Set Your Location
Edit `server.py` lines 42-44:
```python
RECEIVER_LAT = 19.076090  # Your latitude
RECEIVER_LNG = 72.877426  # Your longitude
```

### 3️⃣ Upload TX Code
- Arduino IDE → Open `arduino/TX/TX.ino`
- Connect transmitter → Upload

### 4️⃣ Upload RX Code  
- Arduino IDE → Open `arduino/RX/RX.ino`
- Connect receiver → Upload
- ⚠️ Keep receiver plugged in!

### 5️⃣ Start Server
```bash
python server.py
```

### 6️⃣ Open Dashboard
```
http://localhost:5000
```

### 7️⃣ Power Transmitter
- Disconnect from computer
- Connect to battery/power bank
- Take outside for GPS signal

### 8️⃣ Watch Live!
- Red dot = Transmitter
- Blue dot = Receiver
- Green line = Road route
- Orange line = Direct distance

---

## 🆘 Quick Fixes

### No serial port detected?
```bash
set LORA_PORT=COM5          # Windows
export LORA_PORT=/dev/ttyUSB0   # Mac/Linux
python server.py
```

### No GPS fix?
- Go outside (GPS doesn't work indoors!)
- Wait 2-3 minutes
- Check GPS antenna connection

### Dashboard from phone?
```bash
set FLASK_HOST=0.0.0.0     # Windows
export FLASK_HOST=0.0.0.0  # Mac/Linux
python server.py
# Then: http://YOUR_COMPUTER_IP:5000
```

---

## 📱 Serial Monitor Commands

**Baud Rate:** 9600

**Change message:**
```
Type your message and press Enter
Example: Status: Moving
```

---

## ✅ Checklist

- [ ] Python dependencies installed
- [ ] Receiver coordinates set in server.py
- [ ] TX.ino uploaded to transmitter
- [ ] RX.ino uploaded to receiver (stays connected)
- [ ] server.py running
- [ ] Dashboard open at localhost:5000
- [ ] Transmitter powered and outside

---

## 🎯 What You Should See

**Server terminal:**
```
Connected to COM5 - waiting for data...
  seq=0 lat=19.076 lng=72.877 rssi=-85 | history=1 pts dropped=0
  seq=1 lat=19.077 lng=72.878 rssi=-84 | history=2 pts dropped=0
```

**Dashboard:**
- Map with red marker (TX) and blue marker (RX)
- Coordinates updating every 2-3 seconds
- RSSI signal strength
- Route with turn-by-turn directions

**Receiver OLED:**
```
GPS Tracker RX
Seq: 5
Lat: 19.076090
Lng: 72.877426
Msg: Hello Trainee!
RSSI: -85 dBm
```

---

📖 **Need more help?** See SETUP_GUIDE.md for detailed troubleshooting!
