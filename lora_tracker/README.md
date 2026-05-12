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
     and history cap.

3. **Consistent packet format.**
   - `RX.ino` now prints `,RSSI:<value>` (comma before `RSSI:`)
     matching the documented `DATA:<…>,RSSI:<value>` format.
   - `TX.ino` prepends a monotonically increasing `<seq>` field.
   - The server tracks `seq` and `dropped` in `latest_data`, and the
     dashboard shows both as cards. Drops are detected by gaps in the
     sequence number.
