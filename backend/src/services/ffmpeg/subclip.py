"""
FFmpeg Subclip Extraction Service

Extracts subclips from original video files with codec copy (lossless)

성능 최적화:
- Input Seeking: -ss를 -i 앞에 배치 (빠른 키프레임 점프)
- Double Seek: 대용량 파일에서 빠르고 정확한 추출
- Codec Copy: 재인코딩 없음 (무손실)
- Faststart: moov atom을 앞으로 (웹 재생 최적화)
"""
import ffmpeg
import subprocess
import os
import logging
from pathlib import Path
from typing import Dict, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


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

    def extract_subclip_double_seek(
        self,
        clip_id: UUID,
        input_path: str,
        start_sec: float,
        end_sec: float,
        output_extension: str = ".mp4",
        pre_seek_buffer: float = 10.0
    ) -> Dict[str, any]:
        """
        Double Seek 기법으로 대용량 파일에서 빠르고 정확하게 클립 추출

        대용량 파일(20GB+)에서 더 정확한 추출이 필요할 때 사용합니다.

        작동 원리:
        1. 첫 번째 -ss: 시작점 10초 전으로 빠르게 점프 (키프레임)
        2. 두 번째 -ss: 정확한 위치로 탐색

        Args:
            clip_id: UUID for the clip
            input_path: Path to original video file
            start_sec: Start time in seconds
            end_sec: End time in seconds
            output_extension: Output file extension (default: .mp4)
            pre_seek_buffer: 첫 번째 seek 버퍼 (default: 10초)

        Returns:
            Dict with 'file_path', 'file_size_mb', 'duration_sec', 'method'
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

        # Double Seek 계산
        # 첫 번째 seek: 시작점보다 pre_seek_buffer 초 전으로
        first_seek = max(0, start_sec - pre_seek_buffer)
        # 두 번째 seek: 첫 번째 seek 지점에서 실제 시작점까지
        second_seek = start_sec - first_seek
        # 추출 시간
        duration = end_sec - start_sec

        try:
            # Double Seek 명령어 구성
            # ffmpeg -ss {first_seek} -i input -ss {second_seek} -t {duration} -c copy output
            cmd = [
                "ffmpeg",
                "-ss", str(first_seek),      # 첫 번째 seek (빠른 점프)
                "-i", input_path,
                "-ss", str(second_seek),     # 두 번째 seek (정확한 위치)
                "-t", str(duration),
                "-c", "copy",
                "-avoid_negative_ts", "make_zero",
                "-movflags", "+faststart",
                "-y",
                str(output_path)
            ]

            logger.info(f"Double Seek extraction: first_ss={first_seek}, second_ss={second_seek}, duration={duration}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                raise Exception(f"ffmpeg failed: {result.stderr}")

            # Get file size
            file_size_bytes = output_path.stat().st_size
            file_size_mb = file_size_bytes / (1024 * 1024)

            return {
                'file_path': str(output_path),
                'file_size_mb': file_size_mb,
                'duration_sec': duration,
                'method': 'double_seek'
            }

        except Exception as e:
            # Cleanup on failure
            if output_path.exists():
                output_path.unlink()
            raise

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
