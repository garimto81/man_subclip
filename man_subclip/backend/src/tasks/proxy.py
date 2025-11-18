"""
Proxy Conversion Background Tasks
"""
from uuid import UUID
from sqlalchemy.orm import Session
import logging

from src.models import Video
from src.services.ffmpeg.proxy import ProxyConverter
from src.database import SessionLocal

logger = logging.getLogger(__name__)


def proxy_conversion_task(video_id: UUID, proxy_base_path: str):
    """
    Background task for proxy conversion

    Args:
        video_id: UUID of the video to convert
        proxy_base_path: Base path for proxy files (e.g., /nas/proxy/)

    Updates video.proxy_status:
    - pending → processing → completed (on success)
    - pending → processing → failed (on error)
    """
    db: Session = SessionLocal()
    converter = ProxyConverter(proxy_base_path)

    try:
        # Get video from database
        video = db.query(Video).filter(Video.video_id == video_id).first()
        if not video:
            logger.error(f"Video {video_id} not found")
            return

        # Update status to processing
        video.proxy_status = "processing"
        db.commit()

        logger.info(f"Starting proxy conversion for video {video_id}")

        # Convert to HLS
        result = converter.convert_to_hls(
            video_id=video_id,
            input_path=video.original_path
        )

        # Update video with proxy path and status
        video.proxy_path = result['proxy_path']
        video.proxy_status = "completed"
        db.commit()

        logger.info(f"Proxy conversion completed for video {video_id}")

    except Exception as e:
        logger.error(f"Proxy conversion failed for video {video_id}: {str(e)}")

        # Update status to failed
        try:
            video = db.query(Video).filter(Video.video_id == video_id).first()
            if video:
                video.proxy_status = "failed"
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update status for video {video_id}: {str(db_error)}")

    finally:
        db.close()


def retry_failed_conversion(video_id: UUID, proxy_base_path: str, max_retries: int = 3):
    """
    Retry failed proxy conversion

    Args:
        video_id: UUID of the video
        proxy_base_path: Base path for proxy files
        max_retries: Maximum number of retry attempts

    Returns:
        True if retry started, False if max retries exceeded
    """
    db: Session = SessionLocal()

    try:
        video = db.query(Video).filter(Video.video_id == video_id).first()
        if not video:
            logger.error(f"Video {video_id} not found for retry")
            return False

        # TODO: Track retry count in database
        # For now, just reset to pending and trigger conversion
        video.proxy_status = "pending"
        db.commit()

        logger.info(f"Retrying proxy conversion for video {video_id}")
        proxy_conversion_task(video_id, proxy_base_path)

        return True

    except Exception as e:
        logger.error(f"Failed to retry conversion for video {video_id}: {str(e)}")
        return False

    finally:
        db.close()
