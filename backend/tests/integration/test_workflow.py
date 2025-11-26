"""
E2E Integration Test - Complete Backend Workflow

Tests the complete workflow:
1. Upload video → metadata extraction
2. Trigger proxy rendering → HLS conversion
3. Extract subclip → codec copy extraction
4. Download subclip
5. Cleanup
"""
import pytest
import time
import os
import tempfile
import subprocess
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.main import app
from src.database import Base, get_db
from src.models import Video, Clip  # Import models to register them
from src.services.storage import get_storage_service
from src.config import get_settings

# Test database setup
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def temp_storage(tmp_path):
    """Create temporary storage directories"""
    originals = tmp_path / "originals"
    proxies = tmp_path / "proxies"
    clips = tmp_path / "clips"

    originals.mkdir()
    proxies.mkdir()
    clips.mkdir()

    return {
        "originals": str(originals),
        "proxies": str(proxies),
        "clips": str(clips)
    }


@pytest.fixture(scope="function")
def client(temp_storage):
    """Create test client with database and storage overrides"""
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_get_storage():
        from src.services.storage import StorageService
        storage = StorageService()
        storage.original_path = Path(temp_storage["originals"])
        storage.proxy_path = Path(temp_storage["proxies"])
        storage.clips_path = Path(temp_storage["clips"])
        return storage

    def override_get_settings():
        from src.config import Settings
        settings = Settings()
        settings.nas_originals_path = temp_storage["originals"]
        settings.nas_proxy_path = temp_storage["proxies"]
        settings.nas_clips_path = temp_storage["clips"]
        return settings

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage_service] = override_get_storage
    app.dependency_overrides[get_settings] = override_get_settings

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(client):
    """Get database session for direct queries"""
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    yield TestSessionLocal()


@pytest.fixture(scope="function")
def test_video_file():
    """
    Generate a test video file using ffmpeg

    Creates a 10-second video with:
    - 1280x720 resolution
    - 30 fps
    - Test pattern with timecode overlay
    """
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        output_path = tmp.name

    try:
        # Generate test video with ffmpeg
        cmd = [
            "ffmpeg",
            "-f", "lavfi",
            "-i", "testsrc=duration=10:size=1280x720:rate=30",
            "-f", "lavfi",
            "-i", "sine=frequency=1000:duration=10",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-c:a", "aac",
            "-y",
            output_path
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                pytest.skip(f"ffmpeg not available or failed: {result.stderr}")

        except FileNotFoundError:
            pytest.skip("ffmpeg not found in PATH. Please install ffmpeg to run integration tests.")

        yield output_path

    finally:
        # Cleanup
        if os.path.exists(output_path):
            os.remove(output_path)


def test_complete_workflow(client, db_session, test_video_file):
    """
    E2E test: Upload → Proxy → Subclip → Download

    Workflow:
    1. Upload video file
    2. Verify metadata extraction (duration, fps, resolution)
    3. Trigger proxy rendering
    4. Poll proxy status until completed
    5. Verify proxy files exist (m3u8 + ts segments)
    6. Extract subclip with padding
    7. Verify clip file exists
    8. Download clip
    9. Cleanup
    """

    # ===========================
    # Step 1: Upload Video
    # ===========================

    with open(test_video_file, "rb") as f:
        files = {"file": ("test_video.mp4", f, "video/mp4")}
        response = client.post("/api/videos/upload", files=files)

    assert response.status_code == 201, f"Upload failed: {response.json()}"

    video_data = response.json()
    video_id = video_data["video_id"]

    # Verify metadata extraction
    assert video_data["filename"] == "test_video.mp4"
    assert video_data["duration_sec"] is not None
    assert video_data["duration_sec"] > 9.5  # ~10 seconds (allow small variance)
    assert video_data["duration_sec"] < 10.5
    assert video_data["fps"] == 30
    assert video_data["width"] == 1280
    assert video_data["height"] == 720
    assert video_data["file_size_mb"] > 0
    assert video_data["proxy_status"] == "pending"

    print(f"\n✅ Step 1: Video uploaded (ID: {video_id})")
    print(f"   Duration: {video_data['duration_sec']:.2f}s, FPS: {video_data['fps']}, "
          f"Resolution: {video_data['width']}x{video_data['height']}")

    # ===========================
    # Step 2: Trigger Proxy Rendering
    # ===========================

    response = client.post(f"/api/videos/{video_id}/proxy")
    assert response.status_code == 202, f"Proxy trigger failed: {response.json()}"

    print(f"✅ Step 2: Proxy rendering triggered")

    # ===========================
    # Step 3: Poll Proxy Status
    # ===========================

    max_wait = 60  # 60 seconds timeout
    start_time = time.time()
    proxy_completed = False

    while time.time() - start_time < max_wait:
        response = client.get(f"/api/videos/{video_id}/proxy/status")
        assert response.status_code == 200

        status_data = response.json()
        proxy_status = status_data["proxy_status"]

        print(f"   Proxy status: {proxy_status}")

        if proxy_status == "completed":
            proxy_completed = True
            assert status_data["proxy_path"] is not None
            print(f"✅ Step 3: Proxy rendering completed")
            print(f"   Proxy path: {status_data['proxy_path']}")
            break
        elif proxy_status == "failed":
            pytest.fail(f"Proxy rendering failed: {status_data}")

        time.sleep(2)  # Poll every 2 seconds

    if not proxy_completed:
        pytest.fail(f"Proxy rendering timeout after {max_wait} seconds")

    # Verify proxy files exist
    video = db_session.query(Video).filter(Video.video_id == video_id).first()
    assert video is not None
    assert video.proxy_path is not None

    proxy_path = Path(video.proxy_path)
    assert proxy_path.exists(), f"Proxy m3u8 file not found: {proxy_path}"

    # Check for .ts segments
    proxy_dir = proxy_path.parent
    ts_files = list(proxy_dir.glob("*.ts"))
    assert len(ts_files) > 0, "No .ts segment files found"

    print(f"   Found {len(ts_files)} HLS segments")

    # ===========================
    # Step 4: Extract Subclip
    # ===========================

    clip_request = {
        "video_id": video_id,
        "start_sec": 2.0,
        "end_sec": 6.0,
        "padding_sec": 1.0
    }

    response = client.post("/api/clips/create", json=clip_request)
    assert response.status_code == 201, f"Clip creation failed: {response.json()}"

    clip_data = response.json()
    clip_id = clip_data["clip_id"]

    # Verify clip metadata
    assert clip_data["video_id"] == video_id
    assert clip_data["start_sec"] == 2.0
    assert clip_data["end_sec"] == 6.0
    assert clip_data["padding_sec"] == 1.0

    # Duration should be ~6 seconds (1 to 7 with padding)
    expected_duration = 6.0  # (2-1) to (6+1) = 1 to 7 = 6 seconds
    assert abs(clip_data["duration_sec"] - expected_duration) < 0.5

    assert clip_data["file_path"] is not None
    assert clip_data["file_size_mb"] > 0

    print(f"✅ Step 4: Subclip extracted (ID: {clip_id})")
    print(f"   Duration: {clip_data['duration_sec']:.2f}s, Size: {clip_data['file_size_mb']:.2f}MB")

    # Verify clip file exists
    clip_path = Path(clip_data["file_path"])
    assert clip_path.exists(), f"Clip file not found: {clip_path}"

    # ===========================
    # Step 5: Download Subclip
    # ===========================

    response = client.get(f"/api/clips/{clip_id}/download")
    assert response.status_code == 200
    assert response.headers["content-type"] == "video/mp4"
    assert "content-disposition" in response.headers
    assert ".mp4" in response.headers["content-disposition"]

    # Verify file content is not empty
    assert len(response.content) > 0

    print(f"✅ Step 5: Subclip downloaded ({len(response.content)} bytes)")

    # ===========================
    # Step 6: List Clips for Video
    # ===========================

    response = client.get(f"/api/clips/videos/{video_id}/clips")
    assert response.status_code == 200

    clips_list = response.json()
    assert clips_list["total"] == 1
    assert len(clips_list["clips"]) == 1
    assert clips_list["clips"][0]["clip_id"] == clip_id

    print(f"✅ Step 6: Clips listed for video (total: {clips_list['total']})")

    # ===========================
    # Step 7: Cleanup - Delete Clip
    # ===========================

    response = client.delete(f"/api/clips/{clip_id}")
    assert response.status_code == 204

    # Verify clip deleted from database
    clip = db_session.query(Clip).filter(Clip.clip_id == clip_id).first()
    assert clip is None

    # Verify clip file deleted
    assert not clip_path.exists(), "Clip file should be deleted"

    print(f"✅ Step 7: Clip deleted")

    # ===========================
    # Step 8: Cleanup - Delete Video
    # ===========================

    response = client.delete(f"/api/videos/{video_id}")
    assert response.status_code == 204

    # Verify video deleted from database
    video = db_session.query(Video).filter(Video.video_id == video_id).first()
    assert video is None

    print(f"✅ Step 8: Video deleted")

    print(f"\n🎉 Complete workflow test passed!")


def test_parallel_clip_extraction(client, db_session, test_video_file):
    """
    Test extracting multiple clips from the same video

    Verifies:
    - Multiple clips can be created from one video
    - Clip timecodes don't overlap or conflict
    - All clips are stored correctly
    """

    # Upload video
    with open(test_video_file, "rb") as f:
        files = {"file": ("test_video.mp4", f, "video/mp4")}
        response = client.post("/api/videos/upload", files=files)

    assert response.status_code == 201
    video_id = response.json()["video_id"]

    print(f"\n📹 Video uploaded (ID: {video_id})")

    # Create 3 clips with different timecodes
    clip_requests = [
        {"video_id": video_id, "start_sec": 1.0, "end_sec": 3.0, "padding_sec": 0.5},
        {"video_id": video_id, "start_sec": 4.0, "end_sec": 6.0, "padding_sec": 0.5},
        {"video_id": video_id, "start_sec": 7.0, "end_sec": 9.0, "padding_sec": 0.5},
    ]

    clip_ids = []

    for i, clip_request in enumerate(clip_requests, 1):
        response = client.post("/api/clips/create", json=clip_request)
        assert response.status_code == 201, f"Clip {i} creation failed"

        clip_data = response.json()
        clip_ids.append(clip_data["clip_id"])

        # Verify file exists
        clip_path = Path(clip_data["file_path"])
        assert clip_path.exists()

        print(f"✅ Clip {i} created (ID: {clip_data['clip_id']}, "
              f"Duration: {clip_data['duration_sec']:.2f}s)")

    # Verify all clips are listed
    response = client.get(f"/api/clips/videos/{video_id}/clips")
    assert response.status_code == 200

    clips_list = response.json()
    assert clips_list["total"] == 3

    print(f"✅ All 3 clips listed for video")

    # Cleanup
    for clip_id in clip_ids:
        response = client.delete(f"/api/clips/{clip_id}")
        assert response.status_code == 204

    response = client.delete(f"/api/videos/{video_id}")
    assert response.status_code == 204

    print(f"✅ Cleanup completed")
    print(f"\n🎉 Parallel clip extraction test passed!")


def test_invalid_timecode_handling(client, db_session, test_video_file):
    """
    Test error handling for invalid timecodes

    Verifies:
    - start_sec >= end_sec rejected
    - end_sec > video duration rejected
    - Negative values rejected
    - Appropriate error messages returned
    """

    # Upload video
    with open(test_video_file, "rb") as f:
        files = {"file": ("test_video.mp4", f, "video/mp4")}
        response = client.post("/api/videos/upload", files=files)

    assert response.status_code == 201
    video_id = response.json()["video_id"]
    video_duration = response.json()["duration_sec"]

    print(f"\n📹 Video uploaded (Duration: {video_duration:.2f}s)")

    # Test 1: start_sec >= end_sec
    clip_request = {
        "video_id": video_id,
        "start_sec": 5.0,
        "end_sec": 5.0,  # Equal
        "padding_sec": 0.0
    }

    response = client.post("/api/clips/create", json=clip_request)
    assert response.status_code == 400
    assert "must be > in_sec" in response.json()["detail"]
    print(f"✅ Test 1: start_sec >= end_sec rejected")

    # Test 2: end_sec > video duration
    clip_request = {
        "video_id": video_id,
        "start_sec": 5.0,
        "end_sec": video_duration + 10.0,  # Exceeds duration
        "padding_sec": 0.0
    }

    response = client.post("/api/clips/create", json=clip_request)
    assert response.status_code == 400
    assert "cannot exceed video duration" in response.json()["detail"]
    print(f"✅ Test 2: end_sec > duration rejected")

    # Test 3: Negative start_sec (should be caught by Pydantic validation)
    clip_request = {
        "video_id": video_id,
        "start_sec": -1.0,  # Negative
        "end_sec": 5.0,
        "padding_sec": 0.0
    }

    response = client.post("/api/clips/create", json=clip_request)
    assert response.status_code == 422  # Pydantic validation error
    print(f"✅ Test 3: Negative start_sec rejected")

    # Test 4: Negative padding_sec
    clip_request = {
        "video_id": video_id,
        "start_sec": 2.0,
        "end_sec": 5.0,
        "padding_sec": -1.0  # Negative
    }

    response = client.post("/api/clips/create", json=clip_request)
    assert response.status_code == 422  # Pydantic validation error
    print(f"✅ Test 4: Negative padding_sec rejected")

    # Cleanup
    response = client.delete(f"/api/videos/{video_id}")
    assert response.status_code == 204

    print(f"\n🎉 Invalid timecode handling test passed!")
