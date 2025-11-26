"""
FFmpeg Installation Verification Utility

백엔드 시작 시 ffmpeg 설치 상태를 확인하고,
문제가 있을 경우 명확한 에러 메시지를 제공합니다.
"""
import subprocess
import shutil
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class FFmpegNotFoundError(Exception):
    """ffmpeg가 설치되지 않았거나 PATH에서 찾을 수 없을 때 발생"""
    pass


def check_ffmpeg_installation() -> Dict[str, str]:
    """
    ffmpeg 설치 상태를 확인합니다.

    Returns:
        Dict with 'ffmpeg_path', 'ffprobe_path', 'version'

    Raises:
        FFmpegNotFoundError: ffmpeg가 설치되지 않은 경우
    """
    # ffmpeg 경로 확인
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise FFmpegNotFoundError(
            "ffmpeg를 찾을 수 없습니다.\n"
            "해결 방법:\n"
            "1. winget install Gyan.FFmpeg (Windows)\n"
            "2. 또는 choco install ffmpeg (Chocolatey)\n"
            "3. 설치 후 새 터미널을 열어주세요 (PATH 업데이트 필요)"
        )

    # ffprobe 경로 확인
    ffprobe_path = shutil.which("ffprobe")

    # 버전 확인
    version = get_ffmpeg_version()

    result = {
        "ffmpeg_path": ffmpeg_path,
        "ffprobe_path": ffprobe_path or "Not found",
        "version": version or "Unknown"
    }

    logger.info(f"ffmpeg 확인 완료: {result}")
    return result


def get_ffmpeg_version() -> Optional[str]:
    """
    ffmpeg 버전 문자열을 반환합니다.

    Returns:
        버전 문자열 (예: "ffmpeg version 8.0-full_build") 또는 None
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            # 첫 번째 줄에서 버전 정보 추출
            first_line = result.stdout.split('\n')[0]
            return first_line
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        logger.warning(f"ffmpeg 버전 확인 실패: {e}")
        return None


def verify_ffmpeg_capabilities() -> Dict[str, bool]:
    """
    ffmpeg의 주요 기능 지원 여부를 확인합니다.

    Returns:
        Dict with capability flags
    """
    capabilities = {
        "h264_encoder": False,
        "aac_encoder": False,
        "hls_muxer": False,
        "mp4_muxer": False
    }

    try:
        # 인코더 확인
        encoders_result = subprocess.run(
            ["ffmpeg", "-encoders"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if encoders_result.returncode == 0:
            output = encoders_result.stdout
            capabilities["h264_encoder"] = "libx264" in output
            capabilities["aac_encoder"] = "aac" in output

        # 먹서 확인
        muxers_result = subprocess.run(
            ["ffmpeg", "-muxers"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if muxers_result.returncode == 0:
            output = muxers_result.stdout
            capabilities["hls_muxer"] = "hls" in output
            capabilities["mp4_muxer"] = "mp4" in output

    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        logger.warning(f"ffmpeg 기능 확인 실패: {e}")

    return capabilities


def validate_ffmpeg_for_proxy() -> bool:
    """
    Proxy 변환에 필요한 ffmpeg 기능이 모두 있는지 확인합니다.

    Returns:
        True if all required capabilities are available

    Raises:
        FFmpegNotFoundError: 필수 기능이 없는 경우
    """
    check_ffmpeg_installation()
    capabilities = verify_ffmpeg_capabilities()

    missing = []
    if not capabilities["h264_encoder"]:
        missing.append("libx264 (H.264 인코더)")
    if not capabilities["aac_encoder"]:
        missing.append("aac (오디오 인코더)")
    if not capabilities["hls_muxer"]:
        missing.append("hls (HLS 먹서)")

    if missing:
        raise FFmpegNotFoundError(
            f"ffmpeg에 필수 기능이 없습니다: {', '.join(missing)}\n"
            "full build 버전을 설치해주세요: winget install Gyan.FFmpeg"
        )

    logger.info("ffmpeg Proxy 변환 기능 검증 완료")
    return True
