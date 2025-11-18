"""
Clip Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class ClipCreate(BaseModel):
    """Clip creation request"""
    video_id: UUID
    start_sec: float = Field(..., ge=0, description="Start time in seconds")
    end_sec: float = Field(..., gt=0, description="End time in seconds")
    padding_sec: float = Field(default=0, ge=0, description="Padding in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "video_id": "abc-123-def",
                "start_sec": 10.5,
                "end_sec": 45.8,
                "padding_sec": 3.0
            }
        }


class ClipResponse(BaseModel):
    """Clip response schema"""
    clip_id: UUID
    video_id: UUID
    start_sec: float
    end_sec: float
    padding_sec: float
    file_path: str
    file_size_mb: Optional[float] = None
    duration_sec: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ClipListResponse(BaseModel):
    """Clip list response schema"""
    total: int
    clips: list[ClipResponse]
