"""
NAS Storage Service

Handles file operations for original videos, proxy files, and subclips
"""
import os
import shutil
from pathlib import Path
from typing import Optional
from uuid import UUID

from src.config import get_settings

settings = get_settings()


class StorageService:
    """
    File storage service for managing video files across NAS directories

    Directory structure:
    - /nas/original/: High-resolution original videos
    - /nas/proxy/: HLS proxy files (m3u8 + ts segments)
    - /nas/clips/: Extracted subclips
    """

    def __init__(self):
        self.original_path = Path(settings.nas_original_path)
        self.proxy_path = Path(settings.nas_proxy_path)
        self.clips_path = Path(settings.nas_clips_path)

        # Create directories if they don't exist
        self._ensure_directories()

    def _ensure_directories(self):
        """Create NAS directories if they don't exist"""
        for path in [self.original_path, self.proxy_path, self.clips_path]:
            path.mkdir(parents=True, exist_ok=True)

    def save_uploaded_file(
        self,
        file_content: bytes,
        filename: str,
        video_id: UUID
    ) -> str:
        """
        Save uploaded video file to original directory

        Args:
            file_content: Raw file bytes
            filename: Original filename
            video_id: UUID for the video

        Returns:
            Full path to saved file

        Raises:
            OSError: If file save fails
        """
        # Use video_id as filename to avoid conflicts
        file_extension = Path(filename).suffix
        safe_filename = f"{video_id}{file_extension}"
        file_path = self.original_path / safe_filename

        try:
            with open(file_path, "wb") as f:
                f.write(file_content)
            return str(file_path)
        except Exception as e:
            raise OSError(f"Failed to save file {safe_filename}: {str(e)}")

    def get_file_path(self, filename: str, file_type: str = "original") -> Path:
        """
        Get full path for a file

        Args:
            filename: Name of the file
            file_type: Type of file ("original", "proxy", "clip")

        Returns:
            Full Path object

        Raises:
            ValueError: If file_type is invalid
        """
        if file_type == "original":
            return self.original_path / filename
        elif file_type == "proxy":
            return self.proxy_path / filename
        elif file_type == "clip":
            return self.clips_path / filename
        else:
            raise ValueError(f"Invalid file_type: {file_type}")

    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from storage

        Args:
            file_path: Full path to the file

        Returns:
            True if deletion successful, False otherwise
        """
        try:
            path = Path(file_path)
            if path.exists():
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    shutil.rmtree(path)
                return True
            return False
        except Exception as e:
            print(f"Error deleting file {file_path}: {str(e)}")
            return False

    def delete_proxy_directory(self, video_id: UUID) -> bool:
        """
        Delete entire proxy directory for a video (HLS files)

        Args:
            video_id: UUID of the video

        Returns:
            True if deletion successful, False otherwise
        """
        proxy_dir = self.proxy_path / str(video_id)
        return self.delete_file(str(proxy_dir))

    def get_file_size(self, file_path: str) -> Optional[float]:
        """
        Get file size in MB

        Args:
            file_path: Full path to the file

        Returns:
            File size in MB, or None if file doesn't exist
        """
        try:
            path = Path(file_path)
            if path.exists() and path.is_file():
                size_bytes = path.stat().st_size
                return size_bytes / (1024 * 1024)  # Convert to MB
            return None
        except Exception:
            return None

    def file_exists(self, file_path: str) -> bool:
        """
        Check if file exists

        Args:
            file_path: Full path to the file

        Returns:
            True if file exists, False otherwise
        """
        return Path(file_path).exists()


# Singleton instance
storage_service = StorageService()


def get_storage_service() -> StorageService:
    """
    Get storage service instance

    Usage in FastAPI:
        @app.post("/upload")
        def upload_video(storage: StorageService = Depends(get_storage_service)):
            ...
    """
    return storage_service
