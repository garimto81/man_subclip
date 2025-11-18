"""
Video Metadata Extraction Service

Uses ffmpeg to extract video metadata (duration, fps, resolution)
"""
import ffmpeg
from typing import Optional, Dict


class VideoMetadata:
    """Video metadata extraction using ffmpeg"""

    @staticmethod
    def extract_metadata(file_path: str) -> Dict[str, Optional[float | int]]:
        """
        Extract video metadata using ffmpeg probe

        Args:
            file_path: Full path to video file

        Returns:
            Dict with keys: duration_sec, fps, width, height, file_size_mb

        Raises:
            ffmpeg.Error: If ffmpeg probe fails
        """
        try:
            probe = ffmpeg.probe(file_path)

            # Find video stream
            video_stream = next(
                (stream for stream in probe['streams'] if stream['codec_type'] == 'video'),
                None
            )

            if not video_stream:
                raise ValueError("No video stream found")

            # Extract metadata
            duration_sec = float(probe['format'].get('duration', 0))

            # Calculate FPS
            fps = None
            if 'r_frame_rate' in video_stream:
                num, den = map(int, video_stream['r_frame_rate'].split('/'))
                if den != 0:
                    fps = int(num / den)

            width = video_stream.get('width')
            height = video_stream.get('height')

            # File size in MB
            file_size_bytes = int(probe['format'].get('size', 0))
            file_size_mb = file_size_bytes / (1024 * 1024)

            return {
                'duration_sec': duration_sec,
                'fps': fps,
                'width': width,
                'height': height,
                'file_size_mb': file_size_mb
            }

        except ffmpeg.Error as e:
            raise ValueError(f"Failed to extract metadata: {e.stderr.decode() if e.stderr else str(e)}")


# Singleton instance
video_metadata_service = VideoMetadata()


def get_video_metadata_service() -> VideoMetadata:
    """
    Get video metadata service instance

    Usage in FastAPI:
        @app.post("/upload")
        def upload_video(metadata_service: VideoMetadata = Depends(get_video_metadata_service)):
            ...
    """
    return video_metadata_service
