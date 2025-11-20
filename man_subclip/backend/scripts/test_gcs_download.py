"""
GCS 다운로드 테스트 스크립트

qwen_hand_analysis가 업로드한 영상을 다운로드하여 서브클립 추출에 사용
"""
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.gcs_client import (
    check_gcs_access,
    list_gcs_videos,
    download_video_from_gcs,
    get_gcs_video_uri
)


def main():
    """GCS 다운로드 테스트"""
    print("=" * 60)
    print("GCS Download Test")
    print("=" * 60)

    # 1. GCS 접근 확인
    print("\n[Step 1] Checking GCS access...")
    if not check_gcs_access():
        print("[ERROR] Cannot access GCS bucket")
        return

    # 2. 영상 목록 조회
    print("\n[Step 2] Listing videos in bucket...")
    videos = list_gcs_videos()

    if not videos:
        print("[WARNING] No videos found in bucket")
        return

    print(f"Found {len(videos)} videos:")
    for i, video in enumerate(videos[:5], 1):
        print(f"  {i}. {video}")

    # 3. 첫 번째 영상 다운로드 (테스트)
    test_video = videos[0]
    print(f"\n[Step 3] Downloading test video: {test_video}")

    try:
        local_path = download_video_from_gcs(test_video)
        print(f"[OK] Downloaded to: {local_path}")

        # 파일 크기 확인
        file_size_mb = os.path.getsize(local_path) / (1024 * 1024)
        print(f"[OK] File size: {file_size_mb:.2f} MB")

        # GCS URI 생성
        gcs_uri = get_gcs_video_uri("test_video_id", test_video)
        print(f"[OK] GCS URI: {gcs_uri}")

        # 테스트 파일 삭제
        os.remove(local_path)
        print(f"[OK] Cleaned up test file")

    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        return

    print("\n" + "=" * 60)
    print("GCS Download Test: SUCCESS")
    print("=" * 60)


if __name__ == "__main__":
    main()
