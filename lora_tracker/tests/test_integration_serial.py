"""
Integration tests for the serial reader path.

These tests don\'t require a real Arduino. They use a fake serial port
(FakeSerial) plus monkey-patching of `serial.Serial` to simulate the
receiver Arduino streaming DATA packets to the Python server.

Also includes a unit-level test of the sequence-number-based dropped
packet detector in _ingest_line().

Run:
    python -m pytest tests/test_integration_serial.py -v
"""

import os
import sys
import io
import unittest
from unittest.mock import patch

import serial as pyserial   # real pyserial module (used for SerialException)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import server


class FakeSerial:
    """
    A drop-in replacement for serial.Serial that returns pre-loaded lines.
    After all lines are exhausted it raises SerialException so the
    read_serial() loop exits cleanly during tests.
    """
    def __init__(self, lines):
        self._buf = io.BytesIO(b"".join(l.encode() + b"\n" for l in lines))
        self._exhausted = False

    # mimic the pyserial constructor signature so it can replace it
    @classmethod
    def factory(cls, lines):
        def _make(*args, **kwargs):
            return cls(lines)
        return _make

    def readline(self):
        if self._exhausted:
            raise pyserial.SerialException("end of fake stream")
        line = self._buf.readline()
        if not line:
            self._exhausted = True
            raise pyserial.SerialException("end of fake stream")
        return line

    def close(self):
        pass


class IngestLineTests(unittest.TestCase):
    """Direct tests of _ingest_line (no serial port involved)."""

    def setUp(self):
        with server.data_lock:
            server.latest_data.update({
                "lat": "", "lng": "",
                "msg": "Waiting for LoRa data...",
                "rssi": "N/A", "seq": None, "dropped": 0,
            })
            server.gps_history.clear()

    def test_ingest_valid_packet_updates_state(self):
        pkt = server._ingest_line("DATA:1,17.0,78.0,hello,RSSI:-80")
        self.assertIsNotNone(pkt)
        self.assertEqual(server.latest_data["lat"], "17.0")
        self.assertEqual(server.latest_data["seq"], 1)
        self.assertEqual(len(server.gps_history), 1)

    def test_ingest_invalid_packet_skipped(self):
        pkt = server._ingest_line("DATA:bogus,xx,yy")
        self.assertIsNone(pkt)
        self.assertEqual(server.latest_data["lat"], "")
        self.assertEqual(len(server.gps_history), 0)

    def test_ingest_non_data_line_skipped(self):
        self.assertIsNone(server._ingest_line("LoRa RX ready"))
        self.assertIsNone(server._ingest_line(""))

    def test_dropped_packet_detection(self):
        server._ingest_line("DATA:5,17.0,78.0,m,RSSI:-80")
        self.assertEqual(server.latest_data["dropped"], 0)
        # next packet jumps to 8 -> 2 dropped (6 and 7)
        server._ingest_line("DATA:8,17.0,78.0,m,RSSI:-80")
        self.assertEqual(server.latest_data["dropped"], 2)
        # consecutive packet, no new drops
        server._ingest_line("DATA:9,17.0,78.0,m,RSSI:-80")
        self.assertEqual(server.latest_data["dropped"], 2)

    def test_first_packet_does_not_count_as_dropped(self):
        server._ingest_line("DATA:1000,17.0,78.0,m,RSSI:-80")
        self.assertEqual(server.latest_data["dropped"], 0)

    def test_history_capped_at_max(self):
        server.MAX_HISTORY = 3
        for i in range(5):
            server._ingest_line(f"DATA:{i},17.{i},78.{i},m,RSSI:-80")
        self.assertEqual(len(server.gps_history), 3)
        # oldest should have been dropped
        self.assertEqual(server.gps_history[0], [17.2, 78.2])
        server.MAX_HISTORY = 500   # restore


class SerialLoopbackTests(unittest.TestCase):
    """
    Integration-level tests that patch serial.Serial to feed a stream of
    bytes into read_serial() exactly as the real Arduino would.
    """

    def setUp(self):
        with server.data_lock:
            server.latest_data.update({
                "lat": "", "lng": "",
                "msg": "Waiting for LoRa data...",
                "rssi": "N/A", "seq": None, "dropped": 0,
            })
            server.gps_history.clear()

    def test_loopback_processes_valid_stream(self):
        lines = [
            "LoRa RX ready",
            "DATA:1,17.385,78.486,Hello Trainee!,RSSI:-80",
            "DATA:2,17.386,78.487,Hello Trainee!,RSSI:-81",
            "garbage line",
            "DATA:5,17.390,78.490,Hello Trainee!,RSSI:-85",  # gap -> 2 dropped
        ]
        with patch("server.serial.Serial", FakeSerial.factory(lines)):
            # read_serial loops forever, but our fake serial raises
            # SerialException after the stream is exhausted, which makes
            # read_serial enter its retry sleep. We run it in a thread and
            # check state after a short delay.
            import threading, time
            t = threading.Thread(
                target=server.read_serial,
                args=("FAKE",),
                daemon=True,
            )
            t.start()
            time.sleep(0.5)

        self.assertEqual(server.latest_data["seq"], 5)
        self.assertEqual(server.latest_data["lat"], "17.390")
        self.assertEqual(server.latest_data["dropped"], 2)
        self.assertEqual(len(server.gps_history), 3)


if __name__ == "__main__":
    unittest.main()
