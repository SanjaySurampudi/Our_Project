# LoRa Long Distance Tracker

Live GPS tracker over LoRa with a Flask web dashboard (map, road route,
straight-line distance, GPS history, packet sequence/drop counters).

## Folder hierarchy

```
lora_tracker/
├── server.py                    # Flask server + serial reader + parser
├── requirements.txt
├── README.md
│
├── templates/
│   └── index.html               # Jinja2 template (extracted from server.py)
│
├── static/
│   ├── style.css                # extracted CSS
│   └── app.js                   # extracted dashboard JS (seq/drop tracking)
│
├── arduino/
│   ├── TX/
│   │   └── TX.ino               # transmitter sketch — adds sequence number
│   └── RX/
│       └── RX.ino               # receiver sketch — emits documented format
│
└── tests/
    ├── __init__.py
    ├── test_parser.py           # unit tests for is_valid() / parse_packet()
    ├── test_routes.py           # Flask endpoint tests (OSRM mocked)
    └── test_integration_serial.py  # serial loopback integration tests
```

## Packet format

Over LoRa (TX → RX):
```
<seq>,<lat>,<lng>,<message>
```

Over USB serial (RX → Python server):
```
DATA:<seq>,<lat>,<lng>,<message>,RSSI:<value>
```

Example:
```
DATA:42,17.385000,78.486700,Hello Trainee!,RSSI:-87
```

The server also accepts legacy packets without a sequence number.

## Run the server

```bash
pip install -r requirements.txt
python server.py
# open http://localhost:5000
```

Set `RECEIVER_LAT` / `RECEIVER_LNG` near the top of `server.py` to your
fixed receiver location.

### Security note

By default, the server binds to `127.0.0.1` (localhost only) so only
your computer can access the dashboard. If you want to view it from
another device on the same WiFi (e.g., your phone), set:

```bash
# Linux/macOS
export FLASK_HOST=0.0.0.0
python server.py

# Windows
set FLASK_HOST=0.0.0.0
python server.py
```

**Warning:** This exposes GPS coordinates and message content to anyone
on your local network without authentication. Only use this in trusted
networks.

### Selecting the serial port

The server picks the port in this order:

1. **`LORA_PORT` environment variable** — explicit override:
   ```bash
   # Linux/macOS
   export LORA_PORT=/dev/ttyUSB0
   # Windows
   set LORA_PORT=COM11
   ```
2. **Auto-detection** by USB descriptor keyword (Arduino, CH340, CP210,
   FTDI, USB Serial, ttyUSB, ttyACM).
3. If neither finds a port, the server prints a clear error listing
   available ports and the dashboard keeps running with
   "Waiting for LoRa data...". No more silent infinite retries on a
   non-existent `COM11`.

## Run the tests

```bash
# everything
python -m unittest discover -s tests -v

# or with pytest
pip install pytest
pytest tests/ -v

# individual files
python -m unittest tests.test_parser -v
python -m unittest tests.test_routes -v
python -m unittest tests.test_integration_serial -v
```

The tests do **not** need an Arduino plugged in. The integration tests
patch `serial.Serial` with a `FakeSerial` that streams pre-recorded
lines, simulating a loopback device. OSRM is mocked with
`unittest.mock`.

## What changed (vs. the original)

1. **Template extracted.** The 200-line HTML string is now
   `templates/index.html`, with CSS in `static/style.css` and JS in
   `static/app.js`. `server.py` uses `render_template` instead of
   `render_template_string`. Easier to maintain and supports template
   inheritance.

2. **Tests added.**
   - `test_parser.py` — 25+ cases for `is_valid()` / `parse_packet()`:
     valid new/legacy formats, out-of-range coords, missing fields,
     non-string input, empty messages, truncated lines, etc.
   - `test_routes.py` — Flask `/data`, `/history`, and every `/route`
     error path (no GPS, invalid cache, timeout, connection error,
     HTTP error, invalid JSON, NoRoute, malformed payload, success).
   - `test_integration_serial.py` — patches `serial.Serial` with
     `FakeSerial` to feed a real byte stream through `read_serial()`,
     plus direct `_ingest_line` tests for dropped-packet detection
     and history cap. Includes port-resolution tests.

3. **Consistent packet format.**
   - `RX.ino` now prints `,RSSI:<value>` (comma before `RSSI:`)
     matching the documented `DATA:<…>,RSSI:<value>` format, with
     improved sequence number detection (validates length 1-10 digits).
   - `TX.ino` prepends a monotonically increasing `<seq>` field and
     checks `gps.location.age() < 2000` to avoid transmitting stale
     coordinates after GPS signal loss.
   - The server tracks `seq` and `dropped` in `latest_data`, and the
     dashboard shows both as cards. Drops are detected by gaps in the
     sequence number.

4. **Port detection fixed.** No more silent `COM11` fallback. Priority:
   `LORA_PORT` env var → auto-detection (Arduino/CH340/CP210/FTDI/
   ttyUSB/ttyACM) → clear error listing available ports.

5. **Security improved.** Server binds to `127.0.0.1` (localhost only)
   by default instead of `0.0.0.0`. Set `FLASK_HOST=0.0.0.0` if you
   need LAN access (dashboard accessible from phone on same WiFi).

6. **Route recalculation optimized.** Dashboard now only fetches a new
   OSRM route when the transmitter moves >5 meters (instead of every 15
   seconds regardless), reducing bandwidth and avoiding rate limits.

7. **TX.ino warns about comma replacement.** When updating the message
   via Serial Monitor, if the user's text contains commas, TX now prints
   a warning explaining they were replaced with spaces to protect the
   CSV packet format.

8. **Offline map tile fallback.** Dashboard displays a warning banner when
   OpenStreetMap tiles are unreachable (no internet), allowing markers and
   routes to continue working without the map background.

9. **Serial auto-reconnect with periodic retry.** If no Arduino is detected
   at startup, server now polls every 10 seconds instead of exiting,
   automatically connecting when the Arduino is plugged in.

10. **RX.ino comment corrected.** Updated "1-10 digits" to "0-10 digits
    (including zero)" to match the actual sequence number validation logic.

11. **Performance: collections.deque for gps_history.** Replaced list with
    `deque(maxlen=500)` for O(1) append operations instead of O(n) pop(0).

12. **Unified haversine function in app.js.** Merged `haversineMeters()` and
    `haversineKm()` into single `haversine(lat1, lng1, lat2, lng2, unit)`
    function to eliminate code duplication.

13. **OLED error handling in RX.ino.** If display.begin() fails, receiver
    continues operating without display and periodically retries
    initialization every 30 seconds instead of hanging forever.

14. **uint32_t wrap behavior documented.** Added comment in TX.ino noting
    that sequence wraps to 0 after 4,294,967,295 (~136 years at 2-second
    intervals), which is expected behavior.
