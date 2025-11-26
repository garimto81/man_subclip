"""
Video Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class VideoCreate(BaseModel):
    """Video creation request (internal use)"""
    filename: str
    original_path: str


class VideoResponse(BaseModel):
    """Video response schema"""
    video_id: UUID
    filename: str
    original_path: str
    proxy_path: Optional[str] = None
    proxy_status: str
    duration_sec: Optional[float] = None
    fps: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    file_size_mb: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VideoListResponse(BaseModel):
    """Video list response schema"""
    total: int
    videos: list[VideoResponse]
