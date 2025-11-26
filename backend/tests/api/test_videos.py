"""
Test Video API Endpoints
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from io import BytesIO
import uuid

from src.main import app
from src.database import Base, get_db
from src.models import Video, Clip  # Import models to register them with Base
from src.services.storage import StorageService, get_storage_service
from src.services.video_metadata import VideoMetadata, get_video_metadata_service

# Test database
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def test_storage():
    """Create temporary storage"""
    temp_dir = Path(tempfile.mkdtemp())
    original_path = temp_dir / "original"
    proxy_path = temp_dir / "proxy"
    clips_path = temp_dir / "clips"

    storage = StorageService()
    storage.original_path = original_path
    storage.proxy_path = proxy_path
    storage.clips_path = clips_path
    storage._ensure_directories()

    yield storage

    shutil.rmtree(temp_dir)


@pytest.fixture
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


@pytest.fixture
def client(test_storage, mock_metadata_service):
    """Create test client with dependencies"""
    # Create new engine and session for each test
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
        return test_storage

    def override_get_metadata():
        return mock_metadata_service

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage_service] = override_get_storage
    app.dependency_overrides[get_video_metadata_service] = override_get_metadata

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def create_test_video_file(filename: str = "test.mp4", size_mb: float = 1.0):
    """Create fake video file for testing"""
    size_bytes = int(size_mb * 1024 * 1024)
    content = b"x" * size_bytes
    return BytesIO(content), filename


def test_upload_video_success(client):
    """Test successful video upload"""
    file_content, filename = create_test_video_file("test.mp4", 1.0)

    response = client.post(
        "/api/videos/upload",
        files={"file": (filename, file_content, "video/mp4")}
    )

    assert response.status_code == 201
    data = response.json()

    assert "video_id" in data
    assert data["filename"] == filename
    assert data["proxy_status"] == "pending"
    assert data["duration_sec"] == 60.0
    assert data["fps"] == 30
    assert data["width"] == 1920
    assert data["height"] == 1080


def test_upload_video_invalid_extension(client):
    """Test upload with invalid file extension"""
    file_content, _ = create_test_video_file("test.avi", 1.0)

    response = client.post(
        "/api/videos/upload",
        files={"file": ("test.avi", file_content, "video/avi")}
    )

    assert response.status_code == 400
    assert "Invalid file extension" in response.json()["detail"]


def test_upload_video_too_large(client):
    """Test upload with file exceeding size limit"""
    # Create 11GB file (exceeds 10GB limit)
    file_content, filename = create_test_video_file("large.mp4", 11 * 1024)

    response = client.post(
        "/api/videos/upload",
        files={"file": (filename, file_content, "video/mp4")}
    )

    assert response.status_code == 413
    assert "File too large" in response.json()["detail"]


def test_list_videos_empty(client):
    """Test listing videos when none exist"""
    response = client.get("/api/videos")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["videos"] == []


def test_list_videos_with_pagination(client):
    """Test listing videos with pagination"""
    # Upload 3 videos
    for i in range(3):
        file_content, _ = create_test_video_file(f"test{i}.mp4", 1.0)
        client.post(
            "/api/videos/upload",
            files={"file": (f"test{i}.mp4", file_content, "video/mp4")}
        )

    # Get all videos
    response = client.get("/api/videos")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["videos"]) == 3

    # Get with pagination
    response = client.get("/api/videos?skip=1&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["videos"]) == 2


def test_get_video_by_id(client):
    """Test getting video by ID"""
    # Upload video
    file_content, filename = create_test_video_file("test.mp4", 1.0)
    upload_response = client.post(
        "/api/videos/upload",
        files={"file": (filename, file_content, "video/mp4")}
    )
    video_id = upload_response.json()["video_id"]

    # Get video
    response = client.get(f"/api/videos/{video_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["video_id"] == video_id
    assert data["filename"] == filename


def test_get_video_not_found(client):
    """Test getting non-existent video"""
    fake_id = str(uuid.uuid4())
    response = client.get(f"/api/videos/{fake_id}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_delete_video(client):
    """Test deleting video"""
    # Upload video
    file_content, filename = create_test_video_file("test.mp4", 1.0)
    upload_response = client.post(
        "/api/videos/upload",
        files={"file": (filename, file_content, "video/mp4")}
    )
    video_id = upload_response.json()["video_id"]

    # Delete video
    response = client.delete(f"/api/videos/{video_id}")
    assert response.status_code == 204

    # Verify deleted
    get_response = client.get(f"/api/videos/{video_id}")
    assert get_response.status_code == 404


def test_delete_video_not_found(client):
    """Test deleting non-existent video"""
    fake_id = str(uuid.uuid4())
    response = client.delete(f"/api/videos/{fake_id}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_upload_mov_file(client):
    """Test uploading MOV file"""
    file_content, _ = create_test_video_file("test.mov", 1.0)

    response = client.post(
        "/api/videos/upload",
        files={"file": ("test.mov", file_content, "video/quicktime")}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "test.mov"


def test_upload_mxf_file(client):
    """Test uploading MXF file"""
    file_content, _ = create_test_video_file("test.mxf", 1.0)

    response = client.post(
        "/api/videos/upload",
        files={"file": ("test.mxf", file_content, "application/mxf")}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "test.mxf"
