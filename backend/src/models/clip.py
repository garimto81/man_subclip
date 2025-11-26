"""
Clip Model
"""
from sqlalchemy import Column, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from src.database import Base
from src.models.types import GUID


class Clip(Base):
    """
    Subclip metadata table

    Stores information about extracted subclips
    """
    __tablename__ = "clips"

    clip_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    video_id = Column(GUID, ForeignKey("videos.video_id", ondelete="CASCADE"), nullable=False)

    start_sec = Column(Float, nullable=False)
    end_sec = Column(Float, nullable=False)
    padding_sec = Column(Float, nullable=False, default=0)

    file_path = Column(Text, nullable=False)
    file_size_mb = Column(Float, nullable=True)
    duration_sec = Column(Float, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship
    video = relationship("Video", back_populates="clips")

    def __repr__(self):
        return f"<Clip(clip_id={self.clip_id}, video_id={self.video_id}, start_sec={self.start_sec}, end_sec={self.end_sec})>"
