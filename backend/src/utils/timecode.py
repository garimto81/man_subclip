"""
Timecode Calculation Utilities
"""
from typing import Tuple


def calculate_clip_timecode(
    in_sec: float,
    out_sec: float,
    padding_sec: float,
    video_duration: float
) -> Tuple[float, float, float]:
    """
    Calculate actual clip timecode with padding

    Args:
        in_sec: In point in seconds
        out_sec: Out point in seconds
        padding_sec: Padding to add before/after
        video_duration: Total video duration in seconds

    Returns:
        Tuple of (start_sec, end_sec, duration_sec)

    Raises:
        ValueError: If timecodes are invalid

    Examples:
        >>> calculate_clip_timecode(10.0, 20.0, 3.0, 60.0)
        (7.0, 23.0, 16.0)

        >>> calculate_clip_timecode(2.0, 58.0, 5.0, 60.0)
        (0.0, 60.0, 60.0)  # Clamped to video bounds
    """
    # Validate inputs
    if in_sec < 0:
        raise ValueError(f"in_sec must be >= 0, got {in_sec}")

    if out_sec <= in_sec:
        raise ValueError(f"out_sec ({out_sec}) must be > in_sec ({in_sec})")

    if out_sec > video_duration:
        raise ValueError(
            f"out_sec ({out_sec}) cannot exceed video duration ({video_duration})"
        )

    if padding_sec < 0:
        raise ValueError(f"padding_sec must be >= 0, got {padding_sec}")

    # Calculate with padding
    start_sec = max(0, in_sec - padding_sec)
    end_sec = min(video_duration, out_sec + padding_sec)
    duration_sec = end_sec - start_sec

    return start_sec, end_sec, duration_sec


def format_timecode(seconds: float) -> str:
    """
    Format seconds as HH:MM:SS.mmm

    Args:
        seconds: Time in seconds

    Returns:
        Formatted timecode string

    Examples:
        >>> format_timecode(65.5)
        '00:01:05.500'

        >>> format_timecode(3661.123)
        '01:01:01.123'
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60

    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def parse_timecode(timecode: str) -> float:
    """
    Parse timecode string to seconds

    Args:
        timecode: Timecode in format HH:MM:SS.mmm or MM:SS.mmm or SS.mmm

    Returns:
        Time in seconds

    Raises:
        ValueError: If timecode format is invalid

    Examples:
        >>> parse_timecode("00:01:05.500")
        65.5

        >>> parse_timecode("01:30")
        90.0

        >>> parse_timecode("45.5")
        45.5
    """
    parts = timecode.strip().split(':')

    try:
        if len(parts) == 3:
            # HH:MM:SS.mmm
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds

        elif len(parts) == 2:
            # MM:SS.mmm
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds

        elif len(parts) == 1:
            # SS.mmm
            return float(parts[0])

        else:
            raise ValueError(f"Invalid timecode format: {timecode}")

    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid timecode format: {timecode}") from e
