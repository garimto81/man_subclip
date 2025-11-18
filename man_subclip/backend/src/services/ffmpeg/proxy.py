"""
FFmpeg Proxy Conversion Service

Converts video files to HLS (HTTP Live Streaming) format for browser playback
"""
import ffmpeg
import os
from pathlib import Path
from typing import Optional, Dict
from uuid import UUID


class ProxyConverter:
    """
    Convert video files to HLS proxy format

    Output format:
    - Video: H.264, 1280x720, CRF 23
    - Audio: AAC, 128kbps
    - HLS: 10 second segments
    """

    def __init__(self, proxy_base_path: str):
        """
        Initialize proxy converter

        Args:
            proxy_base_path: Base directory for proxy files (e.g., /nas/proxy/)
        """
        self.proxy_base_path = Path(proxy_base_path)

    def convert_to_hls(
        self,
        video_id: UUID,
        input_path: str,
        scale: str = "1280:720",
        preset: str = "fast",
        crf: int = 23,
        audio_bitrate: str = "128k",
        hls_time: int = 10
    ) -> Dict[str, str]:
        """
        Convert video to HLS format

        Args:
            video_id: UUID of the video
            input_path: Path to original video file
            scale: Video resolution (default: 1280:720)
            preset: ffmpeg encoding preset (default: fast)
            crf: Constant Rate Factor for quality (default: 23)
            audio_bitrate: Audio bitrate (default: 128k)
            hls_time: HLS segment duration in seconds (default: 10)

        Returns:
            Dict with 'proxy_path' (m3u8 file path) and 'proxy_dir' (directory)

        Raises:
            ffmpeg.Error: If conversion fails
            ValueError: If input file doesn't exist
        """
        # Validate input
        if not os.path.exists(input_path):
            raise ValueError(f"Input file not found: {input_path}")

        # Create proxy directory for this video
        proxy_dir = self.proxy_base_path / str(video_id)
        proxy_dir.mkdir(parents=True, exist_ok=True)

        # Output path
        output_path = proxy_dir / "master.m3u8"

        try:
            # Build ffmpeg command
            stream = ffmpeg.input(input_path)

            # Video processing
            video = stream.video.filter('scale', scale)

            # Audio processing
            audio = stream.audio

            # Output with HLS
            output = ffmpeg.output(
                video,
                audio,
                str(output_path),
                format='hls',
                vcodec='libx264',
                preset=preset,
                crf=crf,
                acodec='aac',
                audio_bitrate=audio_bitrate,
                hls_time=hls_time,
                hls_list_size=0,  # Include all segments in playlist
                hls_segment_filename=str(proxy_dir / "segment_%03d.ts")
            )

            # Run conversion
            ffmpeg.run(output, capture_stdout=True, capture_stderr=True, overwrite_output=True)

            return {
                'proxy_path': str(output_path),
                'proxy_dir': str(proxy_dir)
            }

        except ffmpeg.Error as e:
            # Cleanup on failure
            if proxy_dir.exists():
                import shutil
                shutil.rmtree(proxy_dir)

            error_message = e.stderr.decode() if e.stderr else str(e)
            raise ffmpeg.Error(
                f"Failed to convert video to HLS: {error_message}",
                e.stdout,
                e.stderr
            )

    def get_conversion_progress(self, video_id: UUID) -> Optional[float]:
        """
        Get conversion progress (0.0 to 1.0)

        Note: This is a placeholder. Real implementation would need to
        parse ffmpeg progress output in real-time.

        Args:
            video_id: UUID of the video

        Returns:
            Progress as float (0.0 to 1.0), or None if not converting
        """
        # TODO: Implement real-time progress tracking
        # This would require running ffmpeg with progress output
        # and parsing lines like "frame=1234 fps=30 time=00:00:41.40"
        return None

    def cancel_conversion(self, video_id: UUID) -> bool:
        """
        Cancel ongoing conversion

        Args:
            video_id: UUID of the video

        Returns:
            True if cancelled, False if not found
        """
        # TODO: Implement cancellation
        # This would require keeping track of running ffmpeg processes
        # and sending SIGTERM to terminate them
        return False


def get_proxy_converter(proxy_base_path: str) -> ProxyConverter:
    """
    Factory function for ProxyConverter

    Args:
        proxy_base_path: Base directory for proxy files

    Returns:
        ProxyConverter instance
    """
    return ProxyConverter(proxy_base_path)
