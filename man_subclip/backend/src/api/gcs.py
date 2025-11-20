"""
GCS Integration API Endpoints

Phase 2: 독립 실행 모드 - GCS 버킷에서 직접 영상 가져오기
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
import uuid
import os

from src.database import get_db
from src.models import Video
from src.schemas.video import VideoResponse
from src.services.storage import StorageService, get_storage_service
from src.services.video_metadata import VideoMetadata, get_video_metadata_service
from src.services.gcs_client import list_gcs_videos, download_video_from_gcs, get_gcs_video_uri
from src.tasks.proxy import proxy_conversion_task
from src.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/gcs", tags=["gcs"])


@router.get("/videos")
def list_gcs_videos_endpoint():
    """
    GCS 버킷의 영상 목록 조회

    qwen_hand_analysis가 업로드한 영상 목록을 가져옵니다.

    Returns:
        Dict with 'videos' list and 'total' count

    Example response:
        {
            "videos": [
                {
                    "gcs_path": "2025/day1/table1.mp4",
                    "filename": "table1.mp4",
                    "bucket": "wsop-archive-raw",
                    "uri": "gs://wsop-archive-raw/2025/day1/table1.mp4"
                }
            ],
            "total": 5
        }

    Example:
        GET /api/gcs/videos
    """
    if not settings.use_gcs:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GCS integration is disabled"
        )

    try:
        videos = list_gcs_videos()

        video_list = [
            {
                "gcs_path": video,
                "filename": video.split('/')[-1],
                "bucket": settings.gcs_bucket_name,
                "uri": f"gs://{settings.gcs_bucket_name}/{video}"
            }
            for video in videos
        ]

        return {
            "videos": video_list,
            "total": len(video_list)
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list GCS videos: {str(e)}"
        )


@router.post("/import", response_model=VideoResponse, status_code=status.HTTP_202_ACCEPTED)
async def import_from_gcs(
    gcs_path: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
    metadata_service: VideoMetadata = Depends(get_video_metadata_service)
):
    """
    GCS 영상을 다운로드하고 Proxy 렌더링 시작

    Args:
        gcs_path: GCS 경로 (예: "2025/day1/table1.mp4")

    Returns:
        Video object with proxy_status='processing'

    Workflow:
        1. GCS에서 원본 다운로드 → /nas/original/
        2. 메타데이터 추출 (ffmpeg)
        3. DB에 영상 등록
        4. Proxy 렌더링 작업 큐에 추가 (Background)

    Example:
        POST /api/gcs/import?gcs_path=2025/day1/table1.mp4

        Response:
        {
            "video_id": "550e8400-e29b-41d4-a716-446655440000",
            "filename": "table1.mp4",
            "proxy_status": "processing",
            ...
        }
    """
    if not settings.use_gcs:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GCS integration is disabled"
        )

    # Generate video_id
    video_id = uuid.uuid4()
    original_path = None

    try:
        # 1. Download from GCS
        filename = gcs_path.split('/')[-1]
        local_dest = os.path.join(settings.nas_original_path, f"{video_id}_{filename}")

        original_path = download_video_from_gcs(gcs_path, local_dest=local_dest)

        # 2. Extract metadata
        metadata = metadata_service.extract_metadata(original_path)

        # 3. Create database record
        gcs_uri = get_gcs_video_uri(str(video_id), gcs_path)

        video = Video(
            video_id=video_id,
            filename=filename,
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

        # 4. Start proxy conversion in background
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

    except ValueError as e:
        # Cleanup on metadata extraction error
        if original_path and os.path.exists(original_path):
            storage.delete_file(original_path)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to extract metadata: {str(e)}"
        )

    except Exception as e:
        # Cleanup and rollback on any error
        if original_path and os.path.exists(original_path):
            storage.delete_file(original_path)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import from GCS: {str(e)}"
        )
