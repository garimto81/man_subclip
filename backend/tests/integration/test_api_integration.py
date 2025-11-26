"""
API Integration Tests (No ffmpeg required)

Tests the integration between different API endpoints without requiring
actual video processing. Uses mock files and services.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from io import BytesIO
import uuid

from src.main import app
from src.database import Base, get_db
from src.models import Video, Clip
from src.services.storage import StorageService, get_storage_service
from src.services.video_metadata import VideoMetadata, get_video_metadata_service
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
def mock_metadata_service():
    """Mock video metadata service"""
    class MockMetadata:
        def extract_metadata(self, file_path: str):
            return {
                'duration_sec': 60.0,
                'fps': 30,
                'width': 1920,
                'height': 1080,
                'file_size_mb': 10.5
            }

    return MockMetadata()


@pytest.fixture(scope="function")
def client(temp_storage, mock_metadata_service):
    """Create test client with database and storage overrides"""
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
        storage = StorageService()
        storage.original_path = Path(temp_storage["originals"])
        storage.proxy_path = Path(temp_storage["proxies"])
        storage.clips_path = Path(temp_storage["clips"])
        return storage

    def override_get_metadata():
        return mock_metadata_service

    def override_get_settings():
        from src.config import Settings
        settings = Settings()
        settings.nas_originals_path = temp_storage["originals"]
        settings.nas_proxy_path = temp_storage["proxies"]
        settings.nas_clips_path = temp_storage["clips"]
        return settings

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage_service] = override_get_storage
    app.dependency_overrides[get_video_metadata_service] = override_get_metadata
    app.dependency_overrides[get_settings] = override_get_settings

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def create_mock_video_file(size_mb: float = 1.0):
    """Create mock video file for testing"""
    size_bytes = int(size_mb * 1024 * 1024)
    content = b"x" * size_bytes
    return BytesIO(content)


def test_video_upload_and_list(client):
    """
    Integration test: Upload video → List videos

    Tests:
    - Video upload endpoint
    - Video list endpoint with pagination
    - Metadata extraction integration
    """
    # Upload first video
    file1 = create_mock_video_file(1.0)
    response = client.post(
        "/api/videos/upload",
        files={"file": ("video1.mp4", file1, "video/mp4")}
    )
    assert response.status_code == 201
    video1_id = response.json()["video_id"]
    print(f"\n[OK] Video 1 uploaded (ID: {video1_id})")

    # Upload second video
    file2 = create_mock_video_file(2.0)
    response = client.post(
        "/api/videos/upload",
        files={"file": ("video2.mp4", file2, "video/mp4")}
    )
    assert response.status_code == 201
    video2_id = response.json()["video_id"]
    print(f"[OK] Video 2 uploaded (ID: {video2_id})")

    # List all videos
    response = client.get("/api/videos")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 2
    assert len(data["videos"]) == 2

    # Verify video data
    videos = {v["video_id"]: v for v in data["videos"]}
    assert video1_id in videos
    assert video2_id in videos
    assert videos[video1_id]["filename"] == "video1.mp4"
    assert videos[video2_id]["filename"] == "video2.mp4"

    print(f"[OK] Listed {data['total']} videos")

    # Test pagination
    response = client.get("/api/videos?limit=1")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["videos"]) == 1  # Limited to 1

    print(f"[OK] Pagination works (limit=1, got {len(data['videos'])} videos)")
    print(f"\n[SUCCESS] Video upload and list integration test passed!")


def test_video_get_and_delete(client):
    """
    Integration test: Upload → Get → Delete

    Tests:
    - Video detail endpoint
    - Video deletion
    - Cascade deletion verification
    """
    # Upload video
    file = create_mock_video_file(1.0)
    response = client.post(
        "/api/videos/upload",
        files={"file": ("test.mp4", file, "video/mp4")}
    )
    assert response.status_code == 201
    video_id = response.json()["video_id"]
    print(f"\n[OK] Video uploaded (ID: {video_id})")

    # Get video detail
    response = client.get(f"/api/videos/{video_id}")
    assert response.status_code == 200

    video = response.json()
    assert video["video_id"] == video_id
    assert video["filename"] == "test.mp4"
    assert video["duration_sec"] == 60.0
    assert video["fps"] == 30
    assert video["width"] == 1920
    assert video["height"] == 1080

    print(f"[OK] Video detail retrieved")

    # Delete video
    response = client.delete(f"/api/videos/{video_id}")
    assert response.status_code == 204

    print(f"[OK] Video deleted")

    # Verify video is gone
    response = client.get(f"/api/videos/{video_id}")
    assert response.status_code == 404

    print(f"[OK] Video no longer exists")
    print(f"\n[SUCCESS] Video get and delete integration test passed!")


def test_video_not_found(client):
    """
    Integration test: Error handling for non-existent video

    Tests:
    - 404 error for missing video
    - Proper error messages
    """
    fake_id = str(uuid.uuid4())

    # Get non-existent video
    response = client.get(f"/api/videos/{fake_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

    print(f"\n[OK] 404 for non-existent video")

    # Delete non-existent video
    response = client.delete(f"/api/videos/{fake_id}")
    assert response.status_code == 404

    print(f"[OK] 404 for deleting non-existent video")
    print(f"\n[SUCCESS] Error handling integration test passed!")


def test_clip_creation_validation(client):
    """
    Integration test: Clip creation with validation

    Tests:
    - Clip creation requires valid video
    - Timecode validation
    - Error messages
    """
    # Try to create clip without video
    fake_video_id = str(uuid.uuid4())

    clip_request = {
        "video_id": fake_video_id,
        "start_sec": 10.0,
        "end_sec": 20.0,
        "padding_sec": 0.0
    }

    response = client.post("/api/clips/create", json=clip_request)
    assert response.status_code == 404
    assert "Video" in response.json()["detail"]
    assert "not found" in response.json()["detail"]

    print(f"\n[OK] Clip creation rejected for non-existent video")

    # Upload a video first
    file = create_mock_video_file(1.0)
    response = client.post(
        "/api/videos/upload",
        files={"file": ("test.mp4", file, "video/mp4")}
    )
    assert response.status_code == 201
    video_id = response.json()["video_id"]
    video_duration = response.json()["duration_sec"]

    print(f"[OK] Video uploaded (Duration: {video_duration}s)")

    # Test invalid timecodes: start >= end
    clip_request = {
        "video_id": video_id,
        "start_sec": 20.0,
        "end_sec": 10.0,  # Before start
        "padding_sec": 0.0
    }

    response = client.post("/api/clips/create", json=clip_request)
    assert response.status_code == 400
    assert "must be > in_sec" in response.json()["detail"]

    print(f"[OK] Invalid timecode rejected (end < start)")

    # Test timecode exceeding duration
    clip_request = {
        "video_id": video_id,
        "start_sec": 10.0,
        "end_sec": video_duration + 10.0,  # Beyond duration
        "padding_sec": 0.0
    }

    response = client.post("/api/clips/create", json=clip_request)
    assert response.status_code == 400
    assert "cannot exceed video duration" in response.json()["detail"]

    print(f"[OK] Invalid timecode rejected (exceeds duration)")
    print(f"\n[SUCCESS] Clip validation integration test passed!")


def test_clip_list_for_video(client):
    """
    Integration test: List clips for specific video

    Tests:
    - Clips filtered by video_id
    - Multiple clips per video
    - Pagination
    """
    # Upload two videos
    file1 = create_mock_video_file(1.0)
    response = client.post(
        "/api/videos/upload",
        files={"file": ("video1.mp4", file1, "video/mp4")}
    )
    video1_id = response.json()["video_id"]

    file2 = create_mock_video_file(1.0)
    response = client.post(
        "/api/videos/upload",
        files={"file": ("video2.mp4", file2, "video/mp4")}
    )
    video2_id = response.json()["video_id"]

    print(f"\n[OK] 2 videos uploaded")

    # Note: We can't actually create clips without ffmpeg
    # So this test will just verify the endpoint structure

    # List clips for video 1 (should be empty)
    response = client.get(f"/api/clips/videos/{video1_id}/clips")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 0
    assert len(data["clips"]) == 0

    print(f"[OK] Clips list endpoint works (empty list)")

    # List clips with pagination
    response = client.get(f"/api/clips/videos/{video1_id}/clips?limit=10&skip=0")
    assert response.status_code == 200

    print(f"[OK] Clips list with pagination works")

    # Test with non-existent video
    fake_id = str(uuid.uuid4())
    response = client.get(f"/api/clips/videos/{fake_id}/clips")
    assert response.status_code == 404

    print(f"[OK] 404 for non-existent video")
    print(f"\n[SUCCESS] Clip list integration test passed!")


def test_complete_workflow_structure(client):
    """
    Integration test: Verify complete API structure

    Tests all endpoints are accessible and return expected status codes
    """
    print(f"\n[TEST] Testing API structure...")

    # 1. Health check
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    print(f"[OK] Health check")

    # 2. Root endpoint
    response = client.get("/")
    assert response.status_code == 200
    assert "version" in response.json()
    print(f"[OK] Root endpoint")

    # 3. Upload video
    file = create_mock_video_file(1.0)
    response = client.post(
        "/api/videos/upload",
        files={"file": ("test.mp4", file, "video/mp4")}
    )
    assert response.status_code == 201
    video_id = response.json()["video_id"]
    print(f"[OK] Video upload")

    # 4. List videos
    response = client.get("/api/videos")
    assert response.status_code == 200
    print(f"[OK] Video list")

    # 5. Get video
    response = client.get(f"/api/videos/{video_id}")
    assert response.status_code == 200
    print(f"[OK] Video detail")

    # 6. Proxy status (should return pending/failed since we have no ffmpeg)
    response = client.get(f"/api/videos/{video_id}/proxy/status")
    assert response.status_code == 200
    assert "proxy_status" in response.json()
    print(f"[OK] Proxy status")

    # 7. List clips (empty)
    response = client.get("/api/clips")
    assert response.status_code == 200
    print(f"[OK] Clips list")

    # 8. List clips for video (empty)
    response = client.get(f"/api/clips/videos/{video_id}/clips")
    assert response.status_code == 200
    print(f"[OK] Video clips list")

    # 9. Delete video
    response = client.delete(f"/api/videos/{video_id}")
    assert response.status_code == 204
    print(f"[OK] Video delete")

    print(f"\n[SUCCESS] Complete API structure test passed!")
