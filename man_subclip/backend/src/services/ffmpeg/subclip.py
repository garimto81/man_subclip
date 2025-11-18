"""
FFmpeg Subclip Extraction Service

Extracts subclips from original video files with codec copy (lossless)
"""
import ffmpeg
import os
from pathlib import Path
from typing import Dict
from uuid import UUID


class SubclipExtractor:
    """
    Extract subclips from video files using codec copy (no re-encoding)

    Features:
    - Codec copy for lossless extraction
    - Precise timecode accuracy
    - Fast extraction (no re-encoding)
    - Web-optimized output (faststart)
    """

    def __init__(self, clips_base_path: str):
        """
        Initialize subclip extractor

        Args:
            clips_base_path: Base directory for clip files (e.g., /nas/clips/)
        """
        self.clips_base_path = Path(clips_base_path)
        self.clips_base_path.mkdir(parents=True, exist_ok=True)

    def extract_subclip(
        self,
        clip_id: UUID,
        input_path: str,
        start_sec: float,
        end_sec: float,
        output_extension: str = ".mp4"
    ) -> Dict[str, any]:
        """
        Extract subclip from video using codec copy

        Args:
            clip_id: UUID for the clip
            input_path: Path to original video file
            start_sec: Start time in seconds
            end_sec: End time in seconds
            output_extension: Output file extension (default: .mp4)

        Returns:
            Dict with 'file_path', 'file_size_mb', and 'duration_sec'

        Raises:
            ffmpeg.Error: If extraction fails
            ValueError: If input file doesn't exist or timecodes are invalid
        """
        # Validate input
        if not os.path.exists(input_path):
            raise ValueError(f"Input file not found: {input_path}")

        if start_sec < 0:
            raise ValueError(f"start_sec must be >= 0, got {start_sec}")

        if end_sec <= start_sec:
            raise ValueError(f"end_sec ({end_sec}) must be > start_sec ({start_sec})")

        # Output path
        output_filename = f"{clip_id}{output_extension}"
        output_path = self.clips_base_path / output_filename

        try:
            # Build ffmpeg command with codec copy
            # Use -ss before -i for faster seeking
            # Use -to instead of -t for absolute end time
            stream = ffmpeg.input(input_path, ss=start_sec, to=end_sec)

            output = ffmpeg.output(
                stream,
                str(output_path),
                c='copy',  # Codec copy (no re-encoding)
                avoid_negative_ts='make_zero',  # Fix timestamp issues
                movflags='+faststart'  # Web optimization (moov atom at start)
            )

            # Run extraction
            ffmpeg.run(output, capture_stdout=True, capture_stderr=True, overwrite_output=True)

            # Get file size
            file_size_bytes = output_path.stat().st_size
            file_size_mb = file_size_bytes / (1024 * 1024)

            # Calculate duration
            duration_sec = end_sec - start_sec

            return {
                'file_path': str(output_path),
                'file_size_mb': file_size_mb,
                'duration_sec': duration_sec
            }

        except ffmpeg.Error as e:
            # Cleanup on failure
            if output_path.exists():
                output_path.unlink()

            error_message = e.stderr.decode() if e.stderr else str(e)
            raise ffmpeg.Error(
                f"Failed to extract subclip: {error_message}",
                e.stdout,
                e.stderr
            )

    def estimate_clip_size(
        self,
        video_bitrate_mbps: float,
        duration_sec: float
    ) -> float:
        """
        Estimate clip file size based on bitrate

        Args:
            video_bitrate_mbps: Video bitrate in Mbps
            duration_sec: Clip duration in seconds

        Returns:
            Estimated file size in MB

        Example:
            >>> extractor.estimate_clip_size(8.0, 60.0)
            60.0  # 8 Mbps * 60s / 8 bits per byte = 60 MB
        """
        # bitrate (Mbps) * duration (s) / 8 (bits to bytes) = size (MB)
        return (video_bitrate_mbps * duration_sec) / 8


def get_subclip_extractor(clips_base_path: str) -> SubclipExtractor:
    """
    Factory function for SubclipExtractor

    Args:
        clips_base_path: Base directory for clip files

    Returns:
        SubclipExtractor instance
    """
    return SubclipExtractor(clips_base_path)
