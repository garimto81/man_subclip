"""
Clip API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import os

from src.database import get_db
from src.models import Video, Clip
from src.schemas.clip import ClipCreate, ClipResponse, ClipListResponse
from src.services.ffmpeg.subclip import SubclipExtractor, get_subclip_extractor
from src.services.gcs_streaming import extract_clip_from_gcs_streaming
from src.utils.timecode import calculate_clip_timecode
from src.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/clips", tags=["clips"])


@router.post("/create", response_model=ClipResponse, status_code=status.HTTP_201_CREATED)
def create_clip(
    clip_data: ClipCreate,
    db: Session = Depends(get_db)
):
    """
    Create a subclip from original video

    - Validates timecodes
    - Extracts subclip with codec copy (lossless)
    - Saves to NAS /nas/clips/
    - Creates database record

    Process:
    1. Validate video exists
    2. Calculate timecode with padding
    3. Extract subclip using ffmpeg (codec copy)
    4. Save clip metadata to database
    """
    # Get video
    video = db.query(Video).filter(Video.video_id == clip_data.video_id).first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video {clip_data.video_id} not found"
        )

    # Check if original file exists
    if not os.path.exists(video.original_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Original video file not found: {video.original_path}"
        )

    try:
        # Calculate timecode with padding
        start_sec, end_sec, duration_sec = calculate_clip_timecode(
            in_sec=clip_data.start_sec,
            out_sec=clip_data.end_sec,
            padding_sec=clip_data.padding_sec,
            video_duration=video.duration_sec
        )

        # Generate clip ID
        clip_id = uuid.uuid4()

        # Extract subclip
        extractor = get_subclip_extractor(settings.nas_clips_path)
        result = extractor.extract_subclip(
            clip_id=clip_id,
            input_path=video.original_path,
            start_sec=start_sec,
            end_sec=end_sec
        )

        # Create database record
        clip = Clip(
            clip_id=clip_id,
            video_id=clip_data.video_id,
            start_sec=clip_data.start_sec,
            end_sec=clip_data.end_sec,
            padding_sec=clip_data.padding_sec,
            file_path=result['file_path'],
            file_size_mb=result['file_size_mb'],
            duration_sec=result['duration_sec']
        )

        db.add(clip)
        db.commit()
        db.refresh(clip)

        return clip

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create clip: {str(e)}"
        )


@router.get("", response_model=ClipListResponse)
def list_clips(
    video_id: uuid.UUID = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get list of clips

    - Optionally filter by video_id
    - Supports pagination with skip and limit
    - Returns total count and clip list
    """
    query = db.query(Clip)

    if video_id:
        query = query.filter(Clip.video_id == video_id)

    clips = query.offset(skip).limit(limit).all()
    total = query.count()

    return ClipListResponse(total=total, clips=clips)


@router.get("/{clip_id}", response_model=ClipResponse)
def get_clip(
    clip_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Get clip by ID

    - Returns 404 if clip not found
    """
    clip = db.query(Clip).filter(Clip.clip_id == clip_id).first()

    if not clip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clip {clip_id} not found"
        )

    return clip


@router.get("/{clip_id}/download")
def download_clip(
    clip_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Download clip file

    - Returns clip file as attachment
    - Sets proper Content-Disposition header
    - Returns 404 if clip not found or file missing
    """
    clip = db.query(Clip).filter(Clip.clip_id == clip_id).first()

    if not clip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clip {clip_id} not found"
        )

    if not os.path.exists(clip.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clip file not found: {clip.file_path}"
        )

    # Get video for filename
    video = db.query(Video).filter(Video.video_id == clip.video_id).first()
    original_filename = os.path.splitext(video.filename)[0] if video else "clip"

    # Generate download filename
    download_filename = f"{original_filename}_clip_{clip_id}.mp4"

    return FileResponse(
        path=clip.file_path,
        filename=download_filename,
        media_type="video/mp4"
    )


@router.delete("/{clip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_clip(
    clip_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Delete clip by ID

    - Deletes clip from database
    - Deletes clip file from NAS
    - Returns 404 if clip not found
    """
    clip = db.query(Clip).filter(Clip.clip_id == clip_id).first()

    if not clip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clip {clip_id} not found"
        )

    try:
        # Delete file from storage
        if os.path.exists(clip.file_path):
            os.remove(clip.file_path)

        # Delete from database
        db.delete(clip)
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete clip: {str(e)}"
        )


@router.get("/videos/{video_id}/clips", response_model=ClipListResponse)
def get_video_clips(
    video_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get all clips for a specific video

    - Returns clips ordered by creation time (newest first)
    - Supports pagination
    """
    # Check if video exists
    video = db.query(Video).filter(Video.video_id == video_id).first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video {video_id} not found"
        )

    clips = db.query(Clip).filter(
        Clip.video_id == video_id
    ).order_by(
        Clip.created_at.desc()
    ).offset(skip).limit(limit).all()

    total = db.query(Clip).filter(Clip.video_id == video_id).count()

    return ClipListResponse(total=total, clips=clips)


# ============================================================
# GCS Streaming Endpoints (NEW)
# ============================================================

@router.post("/create-from-gcs", status_code=status.HTTP_201_CREATED)
def create_clip_from_gcs_streaming(
    gcs_path: str,
    start_sec: float,
    end_sec: float,
    padding_sec: float = 0.0,
    db: Session = Depends(get_db)
):
    """
    🚀 Create subclip directly from GCS (NO full download!)

    **Performance**:
    - 20GB video → 5 sec clip: ~10 seconds, ~50MB transfer
    - vs full download: ~5 minutes, 20GB transfer
    - 99.75% cost & time reduction

    **How it works**:
    1. Generate GCS Signed URL
    2. ffmpeg HTTP Range Request (reads only needed bytes)
    3. Extract subclip with codec copy (lossless)
    4. Save to /nas/clips/
    5. Return download URL

    **Args**:
        gcs_path: GCS file path (e.g., "Archive-MAM_Sample.mp4")
        start_sec: Start timecode in seconds
        end_sec: End timecode in seconds
        padding_sec: Padding seconds (default: 0)

    **Returns**:
        {
            "clip_id": "uuid",
            "file_path": "/nas/clips/...",
            "file_size_mb": 12.5,
            "duration_sec": 11.0,
            "download_url": "/api/clips/{clip_id}/download",
            "method": "streaming"  # NOT full download
        }
    """
    try:
        # Validate timecodes
        if start_sec < 0 or end_sec <= start_sec:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid timecodes: start={start_sec}, end={end_sec}"
            )

        # Find or create temporary Video record for GCS file
        gcs_uri = f"gs://{settings.gcs_bucket_name}/{gcs_path}"
        video = db.query(Video).filter(Video.original_path == gcs_uri).first()

        if not video:
            # Create temporary Video record for GCS file
            video = Video(
                video_id=uuid.uuid4(),
                filename=os.path.basename(gcs_path),
                original_path=gcs_uri,  # Store GCS URI
                proxy_path=None,
                proxy_status="pending"
            )
            db.add(video)
            db.flush()  # Get video_id without committing

        # Generate clip ID
        clip_id = uuid.uuid4()
        output_path = os.path.join(settings.nas_clips_path, f"{clip_id}.mp4")

        # Extract clip from GCS (streaming, no full download)
        result = extract_clip_from_gcs_streaming(
            gcs_path=gcs_path,
            start_sec=start_sec,
            end_sec=end_sec,
            output_path=output_path,
            padding_sec=padding_sec
        )

        # Create database record with video_id
        clip = Clip(
            clip_id=clip_id,
            video_id=video.video_id,  # Use temporary Video record
            start_sec=start_sec,
            end_sec=end_sec,
            padding_sec=padding_sec,
            file_path=output_path,
            file_size_mb=result['file_size_mb'],
            duration_sec=result['duration_sec']
        )

        db.add(clip)
        db.commit()
        db.refresh(clip)

        return {
            "clip_id": str(clip.clip_id),
            "video_id": str(video.video_id),
            "file_path": clip.file_path,
            "file_size_mb": clip.file_size_mb,
            "duration_sec": clip.duration_sec,
            "download_url": f"/api/clips/{clip.clip_id}/download",
            "method": result['method'],  # "streaming"
            "message": result['message'],
            "gcs_path": gcs_path
        }

    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create clip from GCS: {str(e)}"
        )
