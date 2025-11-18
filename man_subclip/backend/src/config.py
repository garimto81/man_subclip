"""
Application Configuration
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # App
    app_name: str = "Video Proxy & Subclip Platform"
    app_version: str = "0.1.0"
    debug: bool = True

    # Database
    database_url: str = "postgresql://user:password@localhost:5432/video_archive"

    # NAS Storage
    nas_original_path: str = "/nas/original"
    nas_proxy_path: str = "/nas/proxy"
    nas_clips_path: str = "/nas/clips"

    # ffmpeg
    ffmpeg_path: str = "ffmpeg"
    ffmpeg_threads: int = 4
    ffmpeg_preset: str = "fast"
    ffmpeg_crf: int = 23

    # Task Queue
    task_queue: str = "fastapi"  # or "celery"
    celery_broker_url: str = "redis://localhost:6379/0"

    # API
    cors_origins: list = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
