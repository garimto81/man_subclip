"""
Tests for gcs_auth utility
"""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from src.utils.gcs_auth import (
    get_credentials_from_file,
    get_gcs_client_with_validation,
    check_gcs_connection,
    generate_signed_url,
    GCSAuthenticationError
)


class TestGetCredentialsFromFile:
    """get_credentials_from_file() 테스트"""

    def test_file_not_found(self):
        """키 파일이 없는 경우"""
        with pytest.raises(GCSAuthenticationError) as exc_info:
            get_credentials_from_file("/nonexistent/path/key.json")

        assert "찾을 수 없습니다" in str(exc_info.value)
        assert "해결 방법" in str(exc_info.value)

    def test_invalid_json(self, tmp_path):
        """유효하지 않은 JSON 파일"""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("not valid json")

        with pytest.raises(GCSAuthenticationError) as exc_info:
            get_credentials_from_file(str(invalid_file))

        assert "유효하지 않습니다" in str(exc_info.value)


class TestCheckGcsConnection:
    """check_gcs_connection() 테스트"""

    def test_credentials_not_found(self):
        """키 파일이 없는 경우"""
        result = check_gcs_connection(
            project_id="test-project",
            credentials_path="/nonexistent/key.json",
            bucket_name="test-bucket"
        )

        assert result["status"] == "auth_error"
        assert "찾을 수 없습니다" in result["error"]

    def test_successful_connection(self, tmp_path):
        """성공적인 연결"""
        # Mock credentials file
        key_file = tmp_path / "key.json"
        key_file.write_text('{"type": "service_account"}')

        with patch('src.utils.gcs_auth.get_credentials_from_file') as mock_creds:
            mock_creds.return_value = MagicMock()

            with patch('src.utils.gcs_auth.storage.Client') as mock_client:
                mock_bucket = MagicMock()
                mock_bucket.exists.return_value = True
                mock_bucket.list_blobs.return_value = []
                mock_client.return_value.bucket.return_value = mock_bucket

                result = check_gcs_connection(
                    project_id="test-project",
                    credentials_path=str(key_file),
                    bucket_name="test-bucket"
                )

                assert result["status"] == "ok"
                assert result["bucket_exists"] is True
                assert result["can_list_objects"] is True

    def test_bucket_not_found(self, tmp_path):
        """버킷이 없는 경우"""
        key_file = tmp_path / "key.json"
        key_file.write_text('{"type": "service_account"}')

        with patch('src.utils.gcs_auth.get_credentials_from_file') as mock_creds:
            mock_creds.return_value = MagicMock()

            with patch('src.utils.gcs_auth.storage.Client') as mock_client:
                mock_bucket = MagicMock()
                mock_bucket.exists.return_value = False
                mock_client.return_value.bucket.return_value = mock_bucket

                result = check_gcs_connection(
                    project_id="test-project",
                    credentials_path=str(key_file),
                    bucket_name="nonexistent-bucket"
                )

                assert result["status"] == "bucket_not_found"
                assert "버킷을 찾을 수 없습니다" in result["error"]


class TestGenerateSignedUrl:
    """generate_signed_url() 테스트"""

    def test_signed_url_generation(self, tmp_path):
        """Signed URL 생성"""
        key_file = tmp_path / "key.json"
        key_file.write_text('{"type": "service_account"}')

        with patch('src.utils.gcs_auth.get_credentials_from_file') as mock_creds:
            mock_creds.return_value = MagicMock()

            with patch('src.utils.gcs_auth.storage.Client') as mock_client:
                mock_blob = MagicMock()
                mock_blob.generate_signed_url.return_value = "https://storage.googleapis.com/signed-url"
                mock_client.return_value.bucket.return_value.blob.return_value = mock_blob

                url = generate_signed_url(
                    bucket_name="test-bucket",
                    blob_name="video.mp4",
                    credentials_path=str(key_file),
                    expiration_minutes=10
                )

                assert url == "https://storage.googleapis.com/signed-url"
                mock_blob.generate_signed_url.assert_called_once()
