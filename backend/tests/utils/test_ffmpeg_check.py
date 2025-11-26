"""
Tests for ffmpeg_check utility
"""
import pytest
from unittest.mock import patch, MagicMock
from src.utils.ffmpeg_check import (
    check_ffmpeg_installation,
    get_ffmpeg_version,
    verify_ffmpeg_capabilities,
    validate_ffmpeg_for_proxy,
    FFmpegNotFoundError
)


class TestCheckFFmpegInstallation:
    """check_ffmpeg_installation() 테스트"""

    def test_ffmpeg_found(self):
        """ffmpeg가 설치된 경우"""
        with patch('shutil.which') as mock_which:
            mock_which.side_effect = lambda x: f"/usr/bin/{x}" if x in ["ffmpeg", "ffprobe"] else None
            with patch('src.utils.ffmpeg_check.get_ffmpeg_version', return_value="ffmpeg version 8.0"):
                result = check_ffmpeg_installation()

                assert result["ffmpeg_path"] == "/usr/bin/ffmpeg"
                assert result["ffprobe_path"] == "/usr/bin/ffprobe"
                assert result["version"] == "ffmpeg version 8.0"

    def test_ffmpeg_not_found(self):
        """ffmpeg가 없는 경우"""
        with patch('shutil.which', return_value=None):
            with pytest.raises(FFmpegNotFoundError) as exc_info:
                check_ffmpeg_installation()

            assert "ffmpeg를 찾을 수 없습니다" in str(exc_info.value)
            assert "winget install" in str(exc_info.value)

    def test_ffprobe_missing(self):
        """ffprobe만 없는 경우 (경고만)"""
        with patch('shutil.which') as mock_which:
            mock_which.side_effect = lambda x: "/usr/bin/ffmpeg" if x == "ffmpeg" else None
            with patch('src.utils.ffmpeg_check.get_ffmpeg_version', return_value="ffmpeg version 8.0"):
                result = check_ffmpeg_installation()

                assert result["ffmpeg_path"] == "/usr/bin/ffmpeg"
                assert result["ffprobe_path"] == "Not found"


class TestGetFFmpegVersion:
    """get_ffmpeg_version() 테스트"""

    def test_version_success(self):
        """버전 정보 추출 성공"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "ffmpeg version 8.0-full_build-www.gyan.dev\nbuilt with gcc"

        with patch('subprocess.run', return_value=mock_result):
            version = get_ffmpeg_version()
            assert version == "ffmpeg version 8.0-full_build-www.gyan.dev"

    def test_version_failure(self):
        """버전 확인 실패"""
        with patch('subprocess.run', side_effect=FileNotFoundError()):
            version = get_ffmpeg_version()
            assert version is None


class TestVerifyFFmpegCapabilities:
    """verify_ffmpeg_capabilities() 테스트"""

    def test_all_capabilities_present(self):
        """모든 기능이 있는 경우"""
        encoders_result = MagicMock()
        encoders_result.returncode = 0
        encoders_result.stdout = "V..... libx264\nA..... aac"

        muxers_result = MagicMock()
        muxers_result.returncode = 0
        muxers_result.stdout = "E hls\nE mp4"

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [encoders_result, muxers_result]
            capabilities = verify_ffmpeg_capabilities()

            assert capabilities["h264_encoder"] is True
            assert capabilities["aac_encoder"] is True
            assert capabilities["hls_muxer"] is True
            assert capabilities["mp4_muxer"] is True

    def test_missing_capabilities(self):
        """일부 기능이 없는 경우"""
        encoders_result = MagicMock()
        encoders_result.returncode = 0
        encoders_result.stdout = "A..... aac"  # libx264 없음

        muxers_result = MagicMock()
        muxers_result.returncode = 0
        muxers_result.stdout = "E mp4"  # hls 없음

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [encoders_result, muxers_result]
            capabilities = verify_ffmpeg_capabilities()

            assert capabilities["h264_encoder"] is False
            assert capabilities["aac_encoder"] is True
            assert capabilities["hls_muxer"] is False
            assert capabilities["mp4_muxer"] is True


class TestValidateFFmpegForProxy:
    """validate_ffmpeg_for_proxy() 테스트"""

    def test_validation_success(self):
        """모든 검증 통과"""
        with patch('src.utils.ffmpeg_check.check_ffmpeg_installation') as mock_check:
            mock_check.return_value = {"ffmpeg_path": "/usr/bin/ffmpeg", "version": "8.0"}

            with patch('src.utils.ffmpeg_check.verify_ffmpeg_capabilities') as mock_caps:
                mock_caps.return_value = {
                    "h264_encoder": True,
                    "aac_encoder": True,
                    "hls_muxer": True,
                    "mp4_muxer": True
                }

                result = validate_ffmpeg_for_proxy()
                assert result is True

    def test_validation_missing_h264(self):
        """H.264 인코더 없음"""
        with patch('src.utils.ffmpeg_check.check_ffmpeg_installation') as mock_check:
            mock_check.return_value = {"ffmpeg_path": "/usr/bin/ffmpeg", "version": "8.0"}

            with patch('src.utils.ffmpeg_check.verify_ffmpeg_capabilities') as mock_caps:
                mock_caps.return_value = {
                    "h264_encoder": False,  # 없음
                    "aac_encoder": True,
                    "hls_muxer": True,
                    "mp4_muxer": True
                }

                with pytest.raises(FFmpegNotFoundError) as exc_info:
                    validate_ffmpeg_for_proxy()

                assert "libx264" in str(exc_info.value)
