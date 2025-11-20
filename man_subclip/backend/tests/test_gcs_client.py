"""
Test GCS Client Service

Testing GCS bucket access for downloading videos from qwen_hand_analysis ecosystem.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from google.cloud import storage

from src.services.gcs_client import (
    get_gcs_client,
    download_video_from_gcs,
    get_gcs_video_uri,
    check_gcs_access,
    list_gcs_videos
)


@pytest.fixture
def mock_gcs_client():
    """Mock GCS client for testing"""
    with patch('src.services.gcs_client.storage.Client') as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_credentials():
    """Mock service account credentials"""
    with patch('src.services.gcs_client.service_account.Credentials.from_service_account_file') as mock_creds:
        mock_creds.return_value = MagicMock()
        yield mock_creds


def test_get_gcs_client_creates_client_with_credentials(mock_credentials):
    """Test that GCS client is created with Service Account credentials"""
    with patch('src.services.gcs_client.storage.Client') as mock_client:
        get_gcs_client()

        # Should load credentials from file
        mock_credentials.assert_called_once()

        # Should create client with project and credentials
        mock_client.assert_called_once()
        call_kwargs = mock_client.call_args[1]
        assert 'project' in call_kwargs
        assert 'credentials' in call_kwargs


def test_check_gcs_access_returns_true_when_bucket_exists(mock_gcs_client, mock_credentials):
    """Test GCS access check returns True when bucket is accessible"""
    # Mock bucket exists
    mock_bucket = MagicMock()
    mock_bucket.exists.return_value = True
    mock_gcs_client.bucket.return_value = mock_bucket

    result = check_gcs_access()

    assert result is True
    mock_gcs_client.bucket.assert_called_once()
    mock_bucket.exists.assert_called_once()


def test_check_gcs_access_returns_false_when_bucket_not_exists(mock_gcs_client, mock_credentials):
    """Test GCS access check returns False when bucket doesn't exist"""
    # Mock bucket doesn't exist
    mock_bucket = MagicMock()
    mock_bucket.exists.return_value = False
    mock_gcs_client.bucket.return_value = mock_bucket

    result = check_gcs_access()

    assert result is False


def test_check_gcs_access_returns_false_on_exception(mock_credentials):
    """Test GCS access check returns False on exception"""
    with patch('src.services.gcs_client.get_gcs_client') as mock_get_client:
        mock_get_client.side_effect = Exception("Auth failed")

        result = check_gcs_access()

        assert result is False


def test_list_gcs_videos_returns_video_files(mock_gcs_client, mock_credentials):
    """Test listing video files from GCS bucket"""
    # Mock blobs with video extensions
    mock_blob1 = MagicMock()
    mock_blob1.name = "2025/day1/table1.mp4"

    mock_blob2 = MagicMock()
    mock_blob2.name = "2025/day1/table2.mov"

    mock_blob3 = MagicMock()
    mock_blob3.name = "2025/day1/notes.txt"  # Should be filtered out

    mock_bucket = MagicMock()
    mock_bucket.list_blobs.return_value = [mock_blob1, mock_blob2, mock_blob3]
    mock_gcs_client.bucket.return_value = mock_bucket

    videos = list_gcs_videos()

    assert len(videos) == 2
    assert "2025/day1/table1.mp4" in videos
    assert "2025/day1/table2.mov" in videos
    assert "2025/day1/notes.txt" not in videos


def test_list_gcs_videos_with_prefix(mock_gcs_client, mock_credentials):
    """Test listing videos with specific prefix"""
    mock_bucket = MagicMock()
    mock_bucket.list_blobs.return_value = []
    mock_gcs_client.bucket.return_value = mock_bucket

    list_gcs_videos(prefix="2025/day5/")

    mock_bucket.list_blobs.assert_called_once_with(prefix="2025/day5/")


def test_download_video_from_gcs_to_temp(mock_gcs_client, mock_credentials, tmp_path):
    """Test downloading video to temporary location"""
    gcs_path = "2025/day1/table1.mp4"

    # Mock blob download
    mock_blob = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_gcs_client.bucket.return_value = mock_bucket

    # Mock download to create temp file
    def mock_download(dest):
        Path(dest).write_bytes(b"fake video content")

    mock_blob.download_to_filename.side_effect = mock_download

    with patch('src.services.gcs_client.os.makedirs'):
        local_path = download_video_from_gcs(gcs_path)

    # Should download to /tmp by default
    assert local_path == "/tmp/table1.mp4"
    mock_blob.download_to_filename.assert_called_once()


def test_download_video_from_gcs_to_custom_dest(mock_gcs_client, mock_credentials, tmp_path):
    """Test downloading video to custom destination"""
    gcs_path = "2025/day1/table1.mp4"
    custom_dest = str(tmp_path / "custom" / "video.mp4")

    # Mock blob download
    mock_blob = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_gcs_client.bucket.return_value = mock_bucket

    def mock_download(dest):
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        Path(dest).write_bytes(b"fake video content")

    mock_blob.download_to_filename.side_effect = mock_download

    with patch('src.services.gcs_client.os.makedirs'):
        local_path = download_video_from_gcs(gcs_path, local_dest=custom_dest)

    assert local_path == custom_dest


def test_download_video_raises_error_when_gcs_disabled(mock_credentials):
    """Test that download raises error when GCS is disabled in settings"""
    with patch('src.services.gcs_client.settings') as mock_settings:
        mock_settings.use_gcs = False

        with pytest.raises(RuntimeError, match="GCS is disabled"):
            download_video_from_gcs("test.mp4")


def test_get_gcs_video_uri_returns_correct_format(mock_credentials):
    """Test GCS URI generation"""
    with patch('src.services.gcs_client.settings') as mock_settings:
        mock_settings.gcs_bucket_name = "wsop-archive-raw"

        uri = get_gcs_video_uri("video_123", "2025/day1/table1.mp4")

        assert uri == "gs://wsop-archive-raw/2025/day1/table1.mp4"


def test_list_gcs_videos_filters_by_extension(mock_gcs_client, mock_credentials):
    """Test that only video extensions are returned"""
    # Mock blobs with various extensions
    mock_blobs = [
        MagicMock(name="video.mp4"),
        MagicMock(name="video.mov"),
        MagicMock(name="video.mxf"),
        MagicMock(name="video.avi"),
        MagicMock(name="document.pdf"),
        MagicMock(name="image.jpg"),
        MagicMock(name="text.txt"),
    ]

    mock_bucket = MagicMock()
    mock_bucket.list_blobs.return_value = mock_blobs
    mock_gcs_client.bucket.return_value = mock_bucket

    videos = list_gcs_videos()

    # Should only return video files
    assert len(videos) == 4
    assert all(v.endswith(('.mp4', '.mov', '.mxf', '.avi')) for v in videos)


def test_download_creates_parent_directories(mock_gcs_client, mock_credentials):
    """Test that download creates parent directories if they don't exist"""
    gcs_path = "2025/day1/table1.mp4"
    custom_dest = "/nas/downloads/2025/day1/table1.mp4"

    mock_blob = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_gcs_client.bucket.return_value = mock_bucket

    with patch('src.services.gcs_client.os.makedirs') as mock_makedirs:
        with patch.object(mock_blob, 'download_to_filename'):
            download_video_from_gcs(gcs_path, local_dest=custom_dest)

        # Should create parent directory
        mock_makedirs.assert_called_once()
        call_args = mock_makedirs.call_args[0][0]
        assert call_args == "/nas/downloads/2025/day1"
