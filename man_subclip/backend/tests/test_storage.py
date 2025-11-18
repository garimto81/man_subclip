"""
Test Storage Service
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from uuid import uuid4

from src.services.storage import StorageService


@pytest.fixture
def temp_storage():
    """Create temporary storage directories for testing"""
    temp_dir = Path(tempfile.mkdtemp())
    original_path = temp_dir / "original"
    proxy_path = temp_dir / "proxy"
    clips_path = temp_dir / "clips"

    # Create storage service with temp paths
    storage = StorageService()
    storage.original_path = original_path
    storage.proxy_path = proxy_path
    storage.clips_path = clips_path
    storage._ensure_directories()

    yield storage

    # Cleanup
    shutil.rmtree(temp_dir)


def test_ensure_directories(temp_storage):
    """Test that directories are created"""
    assert temp_storage.original_path.exists()
    assert temp_storage.proxy_path.exists()
    assert temp_storage.clips_path.exists()


def test_save_uploaded_file(temp_storage):
    """Test saving uploaded file"""
    video_id = uuid4()
    filename = "test_video.mp4"
    file_content = b"fake video content"

    file_path = temp_storage.save_uploaded_file(file_content, filename, video_id)

    assert Path(file_path).exists()
    assert Path(file_path).read_bytes() == file_content
    assert str(video_id) in file_path
    assert file_path.endswith(".mp4")


def test_save_uploaded_file_preserves_extension(temp_storage):
    """Test that file extension is preserved"""
    video_id = uuid4()
    filename = "test_video.mov"
    file_content = b"fake mov content"

    file_path = temp_storage.save_uploaded_file(file_content, filename, video_id)

    assert file_path.endswith(".mov")


def test_get_file_path_original(temp_storage):
    """Test getting original file path"""
    filename = "test.mp4"
    path = temp_storage.get_file_path(filename, "original")

    assert path == temp_storage.original_path / filename


def test_get_file_path_proxy(temp_storage):
    """Test getting proxy file path"""
    filename = "test.m3u8"
    path = temp_storage.get_file_path(filename, "proxy")

    assert path == temp_storage.proxy_path / filename


def test_get_file_path_clip(temp_storage):
    """Test getting clip file path"""
    filename = "clip.mp4"
    path = temp_storage.get_file_path(filename, "clip")

    assert path == temp_storage.clips_path / filename


def test_get_file_path_invalid_type(temp_storage):
    """Test that invalid file type raises error"""
    with pytest.raises(ValueError):
        temp_storage.get_file_path("test.mp4", "invalid_type")


def test_delete_file(temp_storage):
    """Test deleting a file"""
    # Create a test file
    test_file = temp_storage.original_path / "test.mp4"
    test_file.write_bytes(b"test content")

    assert test_file.exists()

    # Delete the file
    result = temp_storage.delete_file(str(test_file))

    assert result is True
    assert not test_file.exists()


def test_delete_file_nonexistent(temp_storage):
    """Test deleting non-existent file"""
    result = temp_storage.delete_file("/nonexistent/file.mp4")

    assert result is False


def test_delete_directory(temp_storage):
    """Test deleting a directory"""
    # Create a test directory with files
    test_dir = temp_storage.proxy_path / "test_video"
    test_dir.mkdir()
    (test_dir / "segment1.ts").write_bytes(b"segment1")
    (test_dir / "segment2.ts").write_bytes(b"segment2")

    assert test_dir.exists()

    # Delete the directory
    result = temp_storage.delete_file(str(test_dir))

    assert result is True
    assert not test_dir.exists()


def test_delete_proxy_directory(temp_storage):
    """Test deleting proxy directory by video ID"""
    video_id = uuid4()
    proxy_dir = temp_storage.proxy_path / str(video_id)
    proxy_dir.mkdir()
    (proxy_dir / "index.m3u8").write_bytes(b"playlist")
    (proxy_dir / "segment.ts").write_bytes(b"segment")

    assert proxy_dir.exists()

    # Delete proxy directory
    result = temp_storage.delete_proxy_directory(video_id)

    assert result is True
    assert not proxy_dir.exists()


def test_get_file_size(temp_storage):
    """Test getting file size in MB"""
    test_file = temp_storage.original_path / "test.mp4"
    file_content = b"x" * (1024 * 1024)  # 1 MB
    test_file.write_bytes(file_content)

    size_mb = temp_storage.get_file_size(str(test_file))

    assert size_mb is not None
    assert 0.99 < size_mb < 1.01  # Allow small margin for rounding


def test_get_file_size_nonexistent(temp_storage):
    """Test getting size of non-existent file"""
    size_mb = temp_storage.get_file_size("/nonexistent/file.mp4")

    assert size_mb is None


def test_file_exists(temp_storage):
    """Test checking file existence"""
    test_file = temp_storage.original_path / "test.mp4"

    # File doesn't exist yet
    assert not temp_storage.file_exists(str(test_file))

    # Create file
    test_file.write_bytes(b"test")

    # File exists now
    assert temp_storage.file_exists(str(test_file))


def test_save_file_error_handling(temp_storage):
    """Test error handling when saving to invalid path"""
    # Make original path read-only (on Unix systems)
    import platform
    if platform.system() != "Windows":
        temp_storage.original_path.chmod(0o444)

        with pytest.raises(OSError):
            temp_storage.save_uploaded_file(
                b"content",
                "test.mp4",
                uuid4()
            )

        # Restore permissions
        temp_storage.original_path.chmod(0o755)
