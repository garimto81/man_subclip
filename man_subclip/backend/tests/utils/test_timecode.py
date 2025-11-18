"""
Test Timecode Utilities
"""
import pytest
from src.utils.timecode import (
    calculate_clip_timecode,
    format_timecode,
    parse_timecode
)


def test_calculate_clip_timecode_no_padding():
    """Test timecode calculation without padding"""
    start, end, duration = calculate_clip_timecode(
        in_sec=10.0,
        out_sec=20.0,
        padding_sec=0.0,
        video_duration=60.0
    )

    assert start == 10.0
    assert end == 20.0
    assert duration == 10.0


def test_calculate_clip_timecode_with_padding():
    """Test timecode calculation with padding"""
    start, end, duration = calculate_clip_timecode(
        in_sec=10.0,
        out_sec=20.0,
        padding_sec=3.0,
        video_duration=60.0
    )

    assert start == 7.0
    assert end == 23.0
    assert duration == 16.0


def test_calculate_clip_timecode_clamped_to_start():
    """Test that padding doesn't go below 0"""
    start, end, duration = calculate_clip_timecode(
        in_sec=2.0,
        out_sec=10.0,
        padding_sec=5.0,
        video_duration=60.0
    )

    assert start == 0.0  # Clamped
    assert end == 15.0
    assert duration == 15.0


def test_calculate_clip_timecode_clamped_to_end():
    """Test that padding doesn't exceed video duration"""
    start, end, duration = calculate_clip_timecode(
        in_sec=50.0,
        out_sec=58.0,
        padding_sec=5.0,
        video_duration=60.0
    )

    assert start == 45.0
    assert end == 60.0  # Clamped
    assert duration == 15.0


def test_calculate_clip_timecode_invalid_in_sec():
    """Test that negative in_sec raises error"""
    with pytest.raises(ValueError, match="in_sec must be >= 0"):
        calculate_clip_timecode(-1.0, 10.0, 0.0, 60.0)


def test_calculate_clip_timecode_invalid_out_sec():
    """Test that out_sec <= in_sec raises error"""
    with pytest.raises(ValueError, match="out_sec.*must be > in_sec"):
        calculate_clip_timecode(10.0, 10.0, 0.0, 60.0)

    with pytest.raises(ValueError, match="out_sec.*must be > in_sec"):
        calculate_clip_timecode(10.0, 5.0, 0.0, 60.0)


def test_calculate_clip_timecode_exceeds_duration():
    """Test that out_sec > duration raises error"""
    with pytest.raises(ValueError, match="cannot exceed video duration"):
        calculate_clip_timecode(10.0, 70.0, 0.0, 60.0)


def test_calculate_clip_timecode_negative_padding():
    """Test that negative padding raises error"""
    with pytest.raises(ValueError, match="padding_sec must be >= 0"):
        calculate_clip_timecode(10.0, 20.0, -1.0, 60.0)


def test_format_timecode_basic():
    """Test basic timecode formatting"""
    assert format_timecode(65.5) == "00:01:05.500"
    assert format_timecode(0) == "00:00:00.000"
    assert format_timecode(3661.123) == "01:01:01.123"


def test_format_timecode_hours():
    """Test timecode with hours"""
    assert format_timecode(3600) == "01:00:00.000"
    assert format_timecode(7265.5) == "02:01:05.500"


def test_parse_timecode_hh_mm_ss():
    """Test parsing HH:MM:SS format"""
    assert parse_timecode("00:01:05.500") == 65.5
    assert parse_timecode("01:01:01.123") == 3661.123
    assert parse_timecode("00:00:00") == 0


def test_parse_timecode_mm_ss():
    """Test parsing MM:SS format"""
    assert parse_timecode("01:30") == 90.0
    assert parse_timecode("02:05.5") == 125.5


def test_parse_timecode_ss():
    """Test parsing SS format"""
    assert parse_timecode("45.5") == 45.5
    assert parse_timecode("120") == 120.0


def test_parse_timecode_invalid():
    """Test that invalid timecode raises error"""
    with pytest.raises(ValueError, match="Invalid timecode format"):
        parse_timecode("invalid")

    with pytest.raises(ValueError, match="Invalid timecode format"):
        parse_timecode("1:2:3:4")


def test_parse_format_roundtrip():
    """Test that format and parse are inverses"""
    original = 3661.5
    formatted = format_timecode(original)
    parsed = parse_timecode(formatted)

    assert abs(parsed - original) < 0.001  # Allow small floating point error
