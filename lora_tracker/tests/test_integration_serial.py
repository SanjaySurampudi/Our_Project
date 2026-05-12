"""
test_integration_serial.py – serial-integration tests

Fixes:
  • read_serial() now accepts max_retries= so tests can drive it without
    an infinite loop.  We use max_retries=2 in the "no port found" test
    and assert the thread finishes quickly rather than hanging.
  • FakeSerial loopback simulation unchanged.
"""

import sys, os, io, threading, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch, MagicMock

import server
from server import (app, _ingest_line, is_valid, parse_packet,
                    gps_history, latest_data, data_lock, read_serial)

# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_state():
    with data_lock:
        server.latest_data.clear()
        gps_history.clear()
    yield
    with data_lock:
        server.latest_data.clear()
        gps_history.clear()

# ── FakeSerial ────────────────────────────────────────────────────────────

class FakeSerial:
    """Minimal serial.Serial substitute that emits pre-loaded lines."""

    def __init__(self, lines):
        self._buf = io.BytesIO(b"\n".join(l.encode() for l in lines) + b"\n")

    def readline(self):
        return self._buf.readline()

    def __enter__(self): return self
    def __exit__(self, *_): pass

# ── _ingest_line ──────────────────────────────────────────────────────────

def test_ingest_valid_legacy():
    _ingest_line("17.385,78.486,Hi,RSSI:-70")
    with data_lock:
        assert latest_data["lat"] == pytest.approx(17.385, rel=1e-4)
        assert latest_data["rssi"] == -70
        assert len(gps_history) == 1

def test_ingest_valid_seq():
    _ingest_line("5,17.385,78.486,100.0,3.0,90.0,SOS,RSSI:-55")
    with data_lock:
        assert latest_data["seq"] == 5
        assert latest_data["speed"] == pytest.approx(3.0, rel=1e-2)

def test_ingest_invalid_line_ignored():
    _ingest_line("garbage data here")
    with data_lock:
        assert latest_data == {}
        assert len(gps_history) == 0

def test_ingest_empty_line_ignored():
    _ingest_line("")
    with data_lock:
        assert latest_data == {}

def test_ingest_negative_seq_rejected():
    _ingest_line("-1,17.0,78.0,0,0,0,msg,RSSI:-50")
    with data_lock:
        assert latest_data == {}

def test_ingest_multiple_packets_history():
    for i in range(5):
        _ingest_line(f"{i},17.{i},78.{i},0,0,0,msg,RSSI:-{60+i}")
    with data_lock:
        assert len(gps_history) == 5

def test_ingest_history_bounded():
    """History deque must not exceed MAX_HISTORY."""
    original = server.MAX_HISTORY
    server.MAX_HISTORY = 3
    # Rebuild deque with the new limit
    from collections import deque
    server.gps_history = deque(maxlen=3)

    for i in range(10):
        _ingest_line(f"{i},17.0,78.0,0,0,0,msg,RSSI:-70")
    with data_lock:
        assert len(server.gps_history) <= 3

    server.MAX_HISTORY = original
    server.gps_history = deque(maxlen=original)

# ── read_serial – no port found ───────────────────────────────────────────

def test_read_serial_exits_when_no_port_and_max_retries_reached():
    """
    With no ports available and max_retries=2, read_serial() must return
    (not hang) within a reasonable time.  We run it in a thread with a
    timeout to catch regressions.
    """
    with patch("server._autodetect_port", return_value=None), \
         patch("server.time.sleep", return_value=None):   # fast-forward sleeps

        t = threading.Thread(target=read_serial,
                             kwargs={"max_retries": 2}, daemon=True)
        t.start()
        t.join(timeout=5)   # must finish within 5 s
        assert not t.is_alive(), "read_serial hung instead of returning"

# ── read_serial – FakeSerial loopback ────────────────────────────────────

def test_read_serial_ingests_via_fake_serial():
    lines = [
        "0,17.385,78.486,100.0,5.0,180.0,Test,RSSI:-65",
        "1,17.386,78.487,101.0,5.1,181.0,Test2,RSSI:-64",
    ]
    fake = FakeSerial(lines)

    with patch("server._autodetect_port", return_value="/dev/ttyFAKE"), \
         patch("server.serial.Serial", return_value=fake):
        # Run read_serial in a thread; it will exhaust the fake buffer and
        # then block on readline() returning b"" – we join with timeout.
        t = threading.Thread(target=read_serial,
                             kwargs={"port": "/dev/ttyFAKE"}, daemon=True)
        t.start()
        time.sleep(0.5)
        # At least one packet should be ingested
        with data_lock:
            assert len(gps_history) >= 1

def test_read_serial_ignores_invalid_lines_via_fake_serial():
    lines = ["garbage", "more garbage"]
    fake = FakeSerial(lines)

    with patch("server._autodetect_port", return_value="/dev/ttyFAKE"), \
         patch("server.serial.Serial", return_value=fake):
        t = threading.Thread(target=read_serial,
                             kwargs={"port": "/dev/ttyFAKE"}, daemon=True)
        t.start()
        time.sleep(0.3)
        with data_lock:
            assert len(gps_history) == 0
