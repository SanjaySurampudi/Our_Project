"""
serial_reader.py  —  Background thread that reads LoRa DATA: packets from
                     the Arduino RX over serial and updates shared state.

Packet format expected on serial:
    DATA:<lat>,<lng>,<message>,RSSI:<value>

Example:
    DATA:17.3850,78.4867,Hello World,RSSI:-87
"""

import serial
import serial.tools.list_ports
import threading
import logging

log = logging.getLogger(__name__)

# ── Shared state (written by reader thread, read by Flask routes) ─────────────
latest_data: dict = {
    "lat":  "",
    "lng":  "",
    "msg":  "Waiting for LoRa data...",
    "rssi": "N/A",
}

gps_history: list = []   # list of [lat, lng] floats
MAX_HISTORY = 500


# ──────────────────────────────────────────────────────────────────────────────

def _is_valid(line: str) -> bool:
    """Return True if the DATA: line has parseable lat, lng, and message."""
    try:
        payload = line[5:]                          # strip "DATA:"
        if ",RSSI:" in payload:
            payload = payload.split(",RSSI:")[0]
        parts = payload.split(",", 2)
        if len(parts) < 3:
            return False
        lat, lng = float(parts[0]), float(parts[1])
        return -90 <= lat <= 90 and -180 <= lng <= 180 and len(parts[2].strip()) > 0
    except Exception:
        return False


def _parse(line: str) -> dict:
    """
    Parse a validated DATA: line and return a dict with lat, lng, msg, rssi.
    """
    payload = line[5:]   # strip "DATA:"
    rssi    = "N/A"

    if ",RSSI:" in payload:
        payload, rssi_raw = payload.split(",RSSI:", 1)
        rssi = rssi_raw.strip()

    parts = payload.split(",", 2)
    return {
        "lat":  parts[0].strip(),
        "lng":  parts[1].strip(),
        "msg":  parts[2].strip(),
        "rssi": rssi,
    }


def _auto_detect_port() -> str:
    """Return the first COM port that looks like an Arduino / CH340."""
    for p in serial.tools.list_ports.comports():
        if any(k in p.description for k in ("Arduino", "CH340", "USB Serial", "CP210")):
            log.info("Auto-detected serial port: %s (%s)", p.device, p.description)
            return p.device
    return "COM11"   # fallback


def _reader_loop(port: str, baud: int) -> None:
    """Inner loop — reconnects on serial errors."""
    import time

    log.info("Connecting to %s at %d baud …", port, baud)
    while True:
        try:
            with serial.Serial(port, baud, timeout=2) as ser:
                log.info("Connected to %s — listening for DATA: packets", port)
                while True:
                    raw  = ser.readline()
                    line = raw.decode("utf-8", errors="ignore").strip()

                    if not line.startswith("DATA:"):
                        continue

                    if not _is_valid(line):
                        log.debug("Skipped (invalid): %s", line)
                        continue

                    parsed = _parse(line)
                    latest_data.update(parsed)

                    gps_history.append([float(parsed["lat"]), float(parsed["lng"])])
                    if len(gps_history) > MAX_HISTORY:
                        gps_history.pop(0)

                    log.debug("RX  lat=%s lng=%s rssi=%s | history=%d pts",
                              parsed["lat"], parsed["lng"],
                              parsed["rssi"], len(gps_history))

        except serial.SerialException as exc:
            log.error("Serial error: %s — retrying in 4 s", exc)
            time.sleep(4)


def start(port: str | None = None, baud: int = 9600) -> None:
    """
    Start the serial reader in a daemon thread.

    Parameters
    ----------
    port : str or None
        Serial port (e.g. 'COM11', '/dev/ttyUSB0').
        If None, the port is auto-detected.
    baud : int
        Baud rate (must match the Arduino sketch).
    """
    chosen_port = port or _auto_detect_port()
    t = threading.Thread(
        target=_reader_loop,
        args=(chosen_port, baud),
        daemon=True,
        name="serial-reader",
    )
    t.start()
    log.info("Serial reader thread started (port=%s, baud=%d)", chosen_port, baud)
