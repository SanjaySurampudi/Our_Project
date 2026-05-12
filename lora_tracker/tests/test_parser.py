"""
Unit tests for the packet parser in server.py

Run from the project root:
    python -m pytest tests/test_parser.py -v
or:
    python -m unittest tests/test_parser.py
"""

import os
import sys
import unittest

# Allow running tests directly: add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server import is_valid, parse_packet


class TestIsValid(unittest.TestCase):
    # -------- valid packets --------
    def test_valid_new_format_with_seq(self):
        self.assertTrue(is_valid("DATA:1,17.385000,78.486700,Hello Trainee!,RSSI:-87"))

    def test_valid_new_format_seq_zero(self):
        self.assertTrue(is_valid("DATA:0,17.0,78.0,msg,RSSI:-50"))

    def test_valid_large_sequence_number(self):
        self.assertTrue(is_valid("DATA:99999,10.5,20.5,m,RSSI:-100"))

    def test_valid_legacy_format(self):
        self.assertTrue(is_valid("DATA:17.385,78.486,Hello,RSSI:-87"))

    def test_valid_negative_coords(self):
        self.assertTrue(is_valid("DATA:5,-89.9,-179.9,south,RSSI:-95"))

    def test_valid_extreme_coords(self):
        self.assertTrue(is_valid("DATA:5,90,180,edge,RSSI:-100"))
        self.assertTrue(is_valid("DATA:5,-90,-180,edge,RSSI:-100"))

    def test_valid_message_with_spaces(self):
        self.assertTrue(is_valid("DATA:7,17.0,78.0,Hello World From LoRa,RSSI:-70"))

    def test_valid_positive_rssi(self):
        # Some boards rarely report positive RSSI, but it's a valid int
        self.assertTrue(is_valid("DATA:1,17.0,78.0,m,RSSI:5"))

    # -------- invalid packets --------
    def test_missing_prefix(self):
        self.assertFalse(is_valid("17.385,78.486,Hello,RSSI:-87"))

    def test_wrong_prefix(self):
        self.assertFalse(is_valid("DATX:1,17.0,78.0,m,RSSI:-50"))

    def test_missing_rssi(self):
        self.assertFalse(is_valid("DATA:1,17.385,78.486,Hello"))

    def test_rssi_not_integer(self):
        self.assertFalse(is_valid("DATA:1,17.0,78.0,m,RSSI:abc"))

    def test_lat_out_of_range(self):
        self.assertFalse(is_valid("DATA:1,91.0,78.0,m,RSSI:-50"))
        self.assertFalse(is_valid("DATA:1,-91.0,78.0,m,RSSI:-50"))

    def test_lng_out_of_range(self):
        self.assertFalse(is_valid("DATA:1,17.0,181.0,m,RSSI:-50"))
        self.assertFalse(is_valid("DATA:1,17.0,-181.0,m,RSSI:-50"))

    def test_non_numeric_coords(self):
        self.assertFalse(is_valid("DATA:1,abc,78.0,m,RSSI:-50"))
        self.assertFalse(is_valid("DATA:1,17.0,xyz,m,RSSI:-50"))

    def test_empty_message(self):
        self.assertFalse(is_valid("DATA:1,17.0,78.0,,RSSI:-50"))

    def test_whitespace_only_message(self):
        self.assertFalse(is_valid("DATA:1,17.0,78.0,    ,RSSI:-50"))

    def test_empty_string(self):
        self.assertFalse(is_valid(""))

    def test_only_prefix(self):
        self.assertFalse(is_valid("DATA:"))

    def test_none_input(self):
        self.assertFalse(is_valid(None))

    def test_non_string_input(self):
        self.assertFalse(is_valid(12345))
        self.assertFalse(is_valid(["DATA:", "1", "17", "78"]))

    def test_truncated_packet(self):
        self.assertFalse(is_valid("DATA:1,17.0"))
        self.assertFalse(is_valid("DATA:1,17.0,78.0"))


class TestParsePacket(unittest.TestCase):
    def test_parse_new_format(self):
        pkt = parse_packet("DATA:42,17.385000,78.486700,Hello Trainee!,RSSI:-87")
        self.assertEqual(pkt['seq'], 42)
        self.assertEqual(pkt['lat'], "17.385000")
        self.assertEqual(pkt['lng'], "78.486700")
        self.assertEqual(pkt['msg'], "Hello Trainee!")
        self.assertEqual(pkt['rssi'], "-87")

    def test_parse_legacy_format(self):
        pkt = parse_packet("DATA:17.385,78.486,Hello,RSSI:-87")
        self.assertIsNone(pkt['seq'])
        self.assertEqual(pkt['lat'], "17.385")
        self.assertEqual(pkt['lng'], "78.486")
        self.assertEqual(pkt['msg'], "Hello")
        self.assertEqual(pkt['rssi'], "-87")

    def test_message_with_spaces_preserved(self):
        pkt = parse_packet("DATA:1,17.0,78.0,Hello World From LoRa,RSSI:-70")
        self.assertEqual(pkt['msg'], "Hello World From LoRa")

    def test_seq_zero_recognised(self):
        pkt = parse_packet("DATA:0,17.0,78.0,m,RSSI:-50")
        self.assertEqual(pkt['seq'], 0)


if __name__ == '__main__':
    unittest.main()
