"""
Test Proxy Conversion Service
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from uuid import uuid4
from unittest.mock import Mock, patch

from src.services.ffmpeg.proxy import ProxyConverter


@pytest.fixture
def temp_proxy_dir():
    """Create temporary proxy directory"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def proxy_converter(temp_proxy_dir):
    """Create proxy converter with temp directory"""
    return ProxyConverter(str(temp_proxy_dir))


def test_proxy_converter_initialization(proxy_converter, temp_proxy_dir):
    """Test proxy converter initialization"""
    assert proxy_converter.proxy_base_path == temp_proxy_dir


def test_convert_to_hls_input_validation(proxy_converter):
    """Test that convert_to_hls validates input file"""
    video_id = uuid4()
    non_existent_path = "/nonexistent/video.mp4"

    with pytest.raises(ValueError, match="Input file not found"):
        proxy_converter.convert_to_hls(video_id, non_existent_path)


@patch('ffmpeg.run')
@patch('ffmpeg.output')
@patch('ffmpeg.input')
def test_convert_to_hls_creates_proxy_directory(
    mock_input,
    mock_output,
    mock_run,
    proxy_converter,
    temp_proxy_dir
):
    """Test that convert_to_hls creates proxy directory"""
    video_id = uuid4()

    # Create fake input file
    input_file = temp_proxy_dir / "test_input.mp4"
    input_file.write_bytes(b"fake video content")

    # Mock ffmpeg
    mock_stream = Mock()
    mock_stream.video.filter.return_value = Mock()
    mock_stream.audio = Mock()
    mock_input.return_value = mock_stream
    mock_output.return_value = Mock()

    result = proxy_converter.convert_to_hls(video_id, str(input_file))

    # Check that proxy directory was created
    proxy_dir = temp_proxy_dir / str(video_id)
    assert proxy_dir.exists()
    assert proxy_dir.is_dir()

    # Check return value
    assert 'proxy_path' in result
    assert 'proxy_dir' in result
    assert 'master.m3u8' in result['proxy_path']


@patch('ffmpeg.run')
@patch('ffmpeg.output')
@patch('ffmpeg.input')
def test_convert_to_hls_with_custom_parameters(
    mock_input,
    mock_output,
    mock_run,
    proxy_converter,
    temp_proxy_dir
):
    """Test convert_to_hls with custom encoding parameters"""
    video_id = uuid4()

    # Create fake input file
    input_file = temp_proxy_dir / "test_input.mp4"
    input_file.write_bytes(b"fake video content")

    # Mock ffmpeg
    mock_stream = Mock()
    mock_video = Mock()
    mock_stream.video.filter.return_value = mock_video
    mock_stream.audio = Mock()
    mock_input.return_value = mock_stream

    result = proxy_converter.convert_to_hls(
        video_id=video_id,
        input_path=str(input_file),
        scale="1920:1080",
        preset="slow",
        crf=20,
        audio_bitrate="192k",
        hls_time=5
    )

    # Verify ffmpeg.output was called with correct parameters
    mock_output.assert_called_once()
    call_args = mock_output.call_args

    # Check output parameters
    assert call_args.kwargs['format'] == 'hls'
    assert call_args.kwargs['vcodec'] == 'libx264'
    assert call_args.kwargs['preset'] == 'slow'
    assert call_args.kwargs['crf'] == 20
    assert call_args.kwargs['audio_bitrate'] == '192k'
    assert call_args.kwargs['hls_time'] == 5


@patch('ffmpeg.run')
@patch('ffmpeg.output')
@patch('ffmpeg.input')
def test_convert_to_hls_cleanup_on_error(
    mock_input,
    mock_output,
    mock_run,
    proxy_converter,
    temp_proxy_dir
):
    """Test that proxy directory is cleaned up on conversion error"""
    video_id = uuid4()

    # Create fake input file
    input_file = temp_proxy_dir / "test_input.mp4"
    input_file.write_bytes(b"fake video content")

    # Mock ffmpeg to raise error
    mock_stream = Mock()
    mock_stream.video.filter.return_value = Mock()
    mock_stream.audio = Mock()
    mock_input.return_value = mock_stream
    mock_output.return_value = Mock()

    import ffmpeg
    mock_run.side_effect = ffmpeg.Error("ffmpeg error", b"", b"conversion failed")

    # Attempt conversion (should fail)
    with pytest.raises(ffmpeg.Error):
        proxy_converter.convert_to_hls(video_id, str(input_file))

    # Check that proxy directory was cleaned up
    proxy_dir = temp_proxy_dir / str(video_id)
    assert not proxy_dir.exists()


def test_get_conversion_progress(proxy_converter):
    """Test get_conversion_progress (currently placeholder)"""
    video_id = uuid4()
    progress = proxy_converter.get_conversion_progress(video_id)

    # Currently returns None (TODO: implement real-time tracking)
    assert progress is None


def test_cancel_conversion(proxy_converter):
    """Test cancel_conversion (currently placeholder)"""
    video_id = uuid4()
    result = proxy_converter.cancel_conversion(video_id)

    # Currently returns False (TODO: implement cancellation)
    assert result is False
