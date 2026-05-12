"""
test_parser.py – unit tests for server.is_valid() and parse_packet()

Covers:
  • Legacy 4-field format
  • Sequence-number 8-field format
  • Negative sequence number (explicit rejection)
  • Boundary lat/lng values
  • Malformed RSSI
  • Extra commas / too-few fields
  • is_valid / parse_packet round-trip
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from server import is_valid, parse_packet

# ── is_valid: legacy format ───────────────────────────────────────────────

def test_valid_legacy_basic():
    assert is_valid("17.3850,78.4867,Hello,RSSI:-72") is True

def test_valid_legacy_empty_msg():
    assert is_valid("17.3850,78.4867,,RSSI:-72") is True

def test_valid_legacy_boundary_lat_max():
    assert is_valid("90.0,0.0,msg,RSSI:-50") is True

def test_valid_legacy_boundary_lat_min():
    assert is_valid("-90.0,0.0,msg,RSSI:-50") is True

def test_valid_legacy_boundary_lng_max():
    assert is_valid("0.0,180.0,msg,RSSI:-50") is True

def test_valid_legacy_boundary_lng_min():
    assert is_valid("0.0,-180.0,msg,RSSI:-50") is True

def test_invalid_legacy_lat_out_of_range():
    assert is_valid("91.0,78.0,msg,RSSI:-72") is False

def test_invalid_legacy_lng_out_of_range():
    assert is_valid("17.0,181.0,msg,RSSI:-72") is False

def test_invalid_legacy_too_few_fields():
    assert is_valid("17.0,78.0,RSSI:-72") is False

def test_invalid_legacy_no_rssi():
    assert is_valid("17.0,78.0,msg,badfield") is False

def test_invalid_legacy_rssi_not_integer():
    assert is_valid("17.0,78.0,msg,RSSI:-7.5") is False

def test_invalid_legacy_empty():
    assert is_valid("") is False

def test_invalid_legacy_whitespace_only():
    assert is_valid("   ") is False

# ── is_valid: sequence format ─────────────────────────────────────────────

def test_valid_seq_basic():
    assert is_valid("0,17.385,78.486,123.5,5.2,270.0,Hello,RSSI:-65") is True

def test_valid_seq_zero():
    assert is_valid("0,0.0,0.0,0.0,0.0,0.0,,RSSI:0") is True

def test_valid_seq_large():
    assert is_valid("99999,17.385,78.486,0.0,0.0,0.0,msg,RSSI:-90") is True

def test_invalid_seq_negative():
    """Negative sequence numbers must be explicitly rejected."""
    assert is_valid("-5,17.0,78.0,0,0,0,msg,RSSI:-50") is False

def test_invalid_seq_too_few_fields():
    assert is_valid("1,17.0,78.0,0,0,RSSI:-50") is False

def test_invalid_seq_bad_lat():
    assert is_valid("1,abc,78.0,0,0,0,msg,RSSI:-50") is False

# ── parse_packet: round-trip ──────────────────────────────────────────────

def test_parse_legacy_returns_correct_fields():
    p = parse_packet("17.3850,78.4867,Hello,RSSI:-72")
    assert p["lat"]     == pytest.approx(17.3850, rel=1e-4)
    assert p["lng"]     == pytest.approx(78.4867, rel=1e-4)
    assert p["msg"]     == "Hello"
    assert p["rssi"]    == -72
    assert p["node_id"] == "default"
    assert "timestamp"  in p

def test_parse_seq_returns_correct_fields():
    p = parse_packet("3,17.3850,78.4867,123.5,10.2,180.0,Emergency,RSSI:-55")
    assert p["seq"]     == 3
    assert p["lat"]     == pytest.approx(17.3850, rel=1e-4)
    assert p["alt"]     == pytest.approx(123.5,   rel=1e-2)
    assert p["speed"]   == pytest.approx(10.2,    rel=1e-2)
    assert p["heading"] == pytest.approx(180.0,   rel=1e-2)
    assert p["msg"]     == "Emergency"
    assert p["rssi"]    == -55
    assert p["node_id"] == "default"

def test_parse_preserves_node_id():
    p = parse_packet("1,10.0,20.0,0,0,0,test,RSSI:-80")
    assert p["node_id"] == "default"

def test_parse_msg_with_semicolons():
    """Messages may contain semicolons (comma-stripped by TX)."""
    p = parse_packet("0,17.0,78.0,0,0,0,Hello;World,RSSI:-60")
    assert p["msg"] == "Hello;World"

# ── Additional edge-case coverage ─────────────────────────────────────────

def test_is_valid_strips_whitespace():
    assert is_valid("  17.385,78.486,msg,RSSI:-70  ") is True

def test_is_valid_rssi_positive():
    """Some modules report positive RSSI near 0 dBm."""
    assert is_valid("17.385,78.486,msg,RSSI:0") is True

def test_is_valid_rssi_negative_large():
    assert is_valid("17.385,78.486,msg,RSSI:-120") is True
