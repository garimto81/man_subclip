"""
Google Cloud Storage Client

GCS 버킷에서 원본 영상을 다운로드하는 서비스
qwen_hand_analysis가 생성한 영상을 서브클립 추출에 사용
"""
import os
from pathlib import Path
from typing import Optional
from google.cloud import storage
from google.oauth2 import service_account

from ..config import get_settings

settings = get_settings()


def get_gcs_client() -> storage.Client:
    """
    GCS 클라이언트 생성

    Service Account 키 파일을 사용하여 인증
    """
    credentials = service_account.Credentials.from_service_account_file(
        settings.gcs_credentials_path
    )

    return storage.Client(
        project=settings.gcs_project_id,
        credentials=credentials
    )


def download_video_from_gcs(
    gcs_path: str,
    local_dest: Optional[str] = None
) -> str:
    """
    GCS 버킷에서 영상 다운로드

    Args:
        gcs_path: GCS 경로 (예: "2025/day5/table3.mp4")
        local_dest: 로컬 저장 경로 (None이면 임시 디렉토리 사용)

    Returns:
        str: 다운로드된 로컬 파일 경로

    Examples:
        >>> # qwen_hand_analysis에서 생성한 영상 다운로드
        >>> local_path = download_video_from_gcs("2025/day5/table3.mp4")
        >>> # /tmp/wsop_2025_day5_table3.mp4
    """
    if not settings.use_gcs:
        raise RuntimeError("GCS is disabled in settings")

    client = get_gcs_client()
    bucket = client.bucket(settings.gcs_bucket_name)
    blob = bucket.blob(gcs_path)

    # 로컬 저장 경로 결정
    if local_dest is None:
        # 임시 디렉토리 사용
        filename = Path(gcs_path).name
        local_dest = f"/tmp/{filename}"

    # 디렉토리 생성
    os.makedirs(os.path.dirname(local_dest), exist_ok=True)

    # 다운로드
    print(f"Downloading from GCS: gs://{settings.gcs_bucket_name}/{gcs_path}")
    blob.download_to_filename(local_dest)
    print(f"Downloaded to: {local_dest}")

    return local_dest


def get_gcs_video_uri(video_id: str, gcs_path: str) -> str:
    """
    GCS 영상의 URI 생성

    Args:
        video_id: 영상 ID
        gcs_path: GCS 경로

    Returns:
        str: GCS URI (gs://bucket/path)

    Examples:
        >>> uri = get_gcs_video_uri("wsop_2025_day5_table3", "2025/day5/table3.mp4")
        >>> # gs://wsop-archive-raw/2025/day5/table3.mp4
    """
    return f"gs://{settings.gcs_bucket_name}/{gcs_path}"


def check_gcs_access() -> bool:
    """
    GCS 접근 권한 테스트

    Returns:
        bool: 접근 가능 여부
    """
    try:
        client = get_gcs_client()
        bucket = client.bucket(settings.gcs_bucket_name)

        # 버킷 존재 확인
        exists = bucket.exists()

        if not exists:
            print(f"[ERROR] Bucket does not exist: {settings.gcs_bucket_name}")
            return False

        print(f"[OK] GCS access OK: gs://{settings.gcs_bucket_name}")
        return True

    except Exception as e:
        print(f"[ERROR] GCS access failed: {e}")
        return False


def list_gcs_videos(prefix: str = "") -> list[str]:
    """
    GCS 버킷의 영상 파일 목록 조회

    Args:
        prefix: 경로 프리픽스 (예: "2025/day5/")

    Returns:
        list[str]: 영상 파일 경로 목록

    Examples:
        >>> videos = list_gcs_videos("2025/day5/")
        >>> # ["2025/day5/table1.mp4", "2025/day5/table2.mp4", ...]
    """
    client = get_gcs_client()
    bucket = client.bucket(settings.gcs_bucket_name)

    # 영상 파일 확장자
    video_extensions = ('.mp4', '.mov', '.mxf', '.avi')

    blobs = bucket.list_blobs(prefix=prefix)

    videos = [
        blob.name
        for blob in blobs
        if blob.name.lower().endswith(video_extensions)
    ]

    return videos


# 테스트용 함수
if __name__ == "__main__":
    print("Testing GCS access...")

    if check_gcs_access():
        print("\nListing videos in bucket...")
        videos = list_gcs_videos()

        print(f"Found {len(videos)} videos:")
        for video in videos[:10]:  # 처음 10개만
            print(f"  - {video}")

        if len(videos) > 10:
            print(f"  ... and {len(videos) - 10} more")
    else:
        print("\nCannot access GCS bucket")
        print("Check:")
        print("  1. Service Account key file exists")
        print("  2. Service Account has 'Storage Object Viewer' role")
        print("  3. Bucket name is correct")
