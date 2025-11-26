"""
Video API Endpoints
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import uuid
import os

from src.database import get_db
from src.models import Video
from src.schemas.video import VideoResponse, VideoListResponse
from src.services.storage import StorageService, get_storage_service
from src.services.video_metadata import VideoMetadata, get_video_metadata_service
from src.tasks.proxy import proxy_conversion_task
from src.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/videos", tags=["videos"])

# Allowed video extensions
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mxf"}
MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024  # 10GB in bytes


@router.post("/upload", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
    metadata_service: VideoMetadata = Depends(get_video_metadata_service)
):
    """
    Upload a video file

    - Validates file extension (MP4, MOV, MXF only)
    - Validates file size (max 10GB)
    - Saves to NAS /nas/original/
    - Extracts metadata with ffmpeg
    - Creates database record with proxy_status='pending'
    """
    # Validate file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Read file content
    file_content = await file.read()
    file_size_bytes = len(file_content)

    # Validate file size
    if file_size_bytes > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: 10GB"
        )

    # Generate video_id
    video_id = uuid.uuid4()

    try:
        # Save file to NAS
        original_path = storage.save_uploaded_file(file_content, file.filename, video_id)

        # Extract metadata with ffmpeg
        metadata = metadata_service.extract_metadata(original_path)

        # Create database record
        video = Video(
            video_id=video_id,
            filename=file.filename,
            original_path=original_path,
            proxy_status="pending",
            duration_sec=metadata.get('duration_sec'),
            fps=metadata.get('fps'),
            width=metadata.get('width'),
            height=metadata.get('height'),
            file_size_mb=metadata.get('file_size_mb')
        )

        db.add(video)
        db.commit()
        db.refresh(video)

        return video

    except ValueError as e:
        # Cleanup file if metadata extraction failed
        if original_path:
            storage.delete_file(original_path)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        # Cleanup and rollback on any error
        if original_path:
            storage.delete_file(original_path)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload video: {str(e)}"
        )


@router.get("", response_model=VideoListResponse)
def list_videos(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get list of videos

    - Supports pagination with skip and limit
    - Returns total count and video list
    """
    videos = db.query(Video).offset(skip).limit(limit).all()
    total = db.query(Video).count()

    return VideoListResponse(total=total, videos=videos)


@router.get("/{video_id}", response_model=VideoResponse)
def get_video(
    video_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Get video by ID

    - Returns 404 if video not found
    """
    video = db.query(Video).filter(Video.video_id == video_id).first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video {video_id} not found"
        )

    return video


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(
    video_id: uuid.UUID,
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service)
):
    """
    Delete video by ID

    - Deletes video from database (cascades to clips)
    - Deletes original file from NAS
    - Deletes proxy directory from NAS (if exists)
    - Returns 404 if video not found
    """
    video = db.query(Video).filter(Video.video_id == video_id).first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video {video_id} not found"
        )

    try:
        # Delete files from storage
        storage.delete_file(video.original_path)
        if video.proxy_path:
            storage.delete_proxy_directory(video_id)

        # Delete from database (cascades to clips)
        db.delete(video)
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete video: {str(e)}"
        )


@router.post("/{video_id}/proxy", response_model=VideoResponse)
def create_proxy(
    video_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start proxy conversion for a video

    - Starts background task to convert video to HLS proxy
    - Updates proxy_status: pending → processing → completed/failed
    - Returns updated video immediately (status will be 'processing')
    """
    video = db.query(Video).filter(Video.video_id == video_id).first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video {video_id} not found"
        )

    # Check if proxy already exists or is processing
    if video.proxy_status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Proxy already exists"
        )

    if video.proxy_status == "processing":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Proxy conversion already in progress"
        )

    # Start background conversion task
    background_tasks.add_task(
        proxy_conversion_task,
        video_id=video_id,
        proxy_base_path=settings.nas_proxy_path
    )

    # Update status to processing
    video.proxy_status = "processing"
    db.commit()
    db.refresh(video)

    return video


@router.get("/{video_id}/proxy/status")
def get_proxy_status(
    video_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Get proxy conversion status

    Returns:
        Dict with 'status' (pending/processing/completed/failed) and 'proxy_path'
    """
    video = db.query(Video).filter(Video.video_id == video_id).first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video {video_id} not found"
        )

    return {
        "video_id": str(video_id),
        "proxy_status": video.proxy_status,
        "proxy_path": video.proxy_path,
        "filename": video.filename
    }
