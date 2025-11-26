"""
Video Model
"""
from sqlalchemy import Column, String, Float, Integer, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from src.database import Base
from src.models.types import GUID


class Video(Base):
    """
    Video metadata table

    Stores information about uploaded videos and their proxy status
    """
    __tablename__ = "videos"

    video_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    original_path = Column(Text, nullable=False)
    proxy_path = Column(Text, nullable=True)
    proxy_status = Column(
        String(20),
        nullable=False,
        default="pending"
    )  # pending | processing | completed | failed

    duration_sec = Column(Float, nullable=True)
    fps = Column(Integer, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    file_size_mb = Column(Float, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    clips = relationship("Clip", back_populates="video", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Video(video_id={self.video_id}, filename={self.filename}, proxy_status={self.proxy_status})>"
