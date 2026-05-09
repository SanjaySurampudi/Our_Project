"""
app.py  —  LoRa Long Distance Tracker  (entry point)

Start with:
    python app.py

Then open http://localhost:5000 in your browser.

Configuration
-------------
Edit the constants below (RECEIVER_LAT, RECEIVER_LNG, SERIAL_PORT, etc.)
before running.  All other logic lives in the three sibling modules:

    serial_reader.py   — serial port / DATA: packet parser
    router.py          — offline Dijkstra routing on OSM graph
    flask_routes.py    — Flask URL handlers + HTML template
"""

import logging
from flask import Flask

import serial_reader
from router import OfflineRouter
from flask_routes import register_routes

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
)
log = logging.getLogger(__name__)

# ── Configuration — edit these values ────────────────────────────────────────
RECEIVER_LAT  = 17.087741   # Fixed receiver latitude  (Peddāpuram area)
RECEIVER_LNG  = 82.068771   # Fixed receiver longitude

SERIAL_PORT   = None        # None = auto-detect; or e.g. "COM11" / "/dev/ttyUSB0"
SERIAL_BAUD   = 9600        # Must match Arduino sketch baud rate

# OSM graph download radius in metres.
# 50 000 m (50 km) covers most local routing needs without being too large.
# Increase to e.g. 150_000 for longer-range scenarios (uses more RAM & time).
OSM_RADIUS_M  = 50_000

FLASK_HOST    = "0.0.0.0"
FLASK_PORT    = 5000
# ─────────────────────────────────────────────────────────────────────────────

def create_app() -> Flask:
    app = Flask(__name__)

    # 1. Offline router (starts background OSM download immediately)
    router = OfflineRouter(
        center_lat=RECEIVER_LAT,
        center_lng=RECEIVER_LNG,
        radius_m=OSM_RADIUS_M,
        network_type="drive",
    )

    # 2. Register all URL routes
    register_routes(app, router, RECEIVER_LAT, RECEIVER_LNG)

    return app


if __name__ == "__main__":
    # 3. Start serial reader thread
    serial_reader.start(port=SERIAL_PORT, baud=SERIAL_BAUD)

    # 4. Create and run Flask app
    application = create_app()

    log.info("=" * 50)
    log.info("  LoRa Long Distance Tracker")
    log.info("  Open  http://localhost:%d", FLASK_PORT)
    log.info("  Receiver: %.6f, %.6f", RECEIVER_LAT, RECEIVER_LNG)
    log.info("=" * 50)

    application.run(host=FLASK_HOST, port=FLASK_PORT, debug=False)
