"""
Test FFmpeg Proxy Conversion Service

Testing HLS conversion for browser playback
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
from uuid import uuid4, UUID
import ffmpeg

from src.services.ffmpeg.proxy import ProxyConverter, get_proxy_converter


@pytest.fixture
def temp_proxy_path(tmp_path):
    """Create temporary proxy directory"""
    proxy_path = tmp_path / "proxy"
    proxy_path.mkdir()
    return str(proxy_path)


@pytest.fixture
def converter(temp_proxy_path):
    """Create ProxyConverter instance with temp path"""
    return ProxyConverter(temp_proxy_path)


@pytest.fixture
def sample_video_file(tmp_path):
    """Create a fake video file for testing"""
    video_file = tmp_path / "sample.mp4"
    video_file.write_bytes(b"fake video content")
    return str(video_file)


def test_proxy_converter_initialization(temp_proxy_path):
    """Test ProxyConverter initialization"""
    converter = ProxyConverter(temp_proxy_path)

    assert converter.proxy_base_path == Path(temp_proxy_path)


def test_factory_function_returns_converter(temp_proxy_path):
    """Test get_proxy_converter factory function"""
    converter = get_proxy_converter(temp_proxy_path)

    assert isinstance(converter, ProxyConverter)
    assert converter.proxy_base_path == Path(temp_proxy_path)


def test_convert_to_hls_raises_error_for_missing_input(converter):
    """Test that convert_to_hls raises ValueError for non-existent input file"""
    video_id = uuid4()
    non_existent_path = "/nonexistent/video.mp4"

    with pytest.raises(ValueError, match="Input file not found"):
        converter.convert_to_hls(video_id, non_existent_path)


def test_convert_to_hls_creates_proxy_directory(converter, sample_video_file, temp_proxy_path):
    """Test that convert_to_hls creates video-specific directory"""
    video_id = uuid4()

    with patch('src.services.ffmpeg.proxy.ffmpeg') as mock_ffmpeg:
        # Mock ffmpeg chain
        mock_input = MagicMock()
        mock_video = MagicMock()
        mock_audio = MagicMock()
        mock_output = MagicMock()

        mock_ffmpeg.input.return_value = mock_input
        mock_input.video.filter.return_value = mock_video
        mock_input.audio = mock_audio
        mock_ffmpeg.output.return_value = mock_output
        mock_ffmpeg.run.return_value = None

        converter.convert_to_hls(video_id, sample_video_file)

        # Check directory was created
        expected_dir = Path(temp_proxy_path) / str(video_id)
        assert expected_dir.exists()


def test_convert_to_hls_calls_ffmpeg_with_correct_params(converter, sample_video_file):
    """Test that convert_to_hls calls ffmpeg with correct parameters"""
    video_id = uuid4()

    with patch('src.services.ffmpeg.proxy.ffmpeg') as mock_ffmpeg:
        # Mock ffmpeg chain
        mock_input = MagicMock()
        mock_video = MagicMock()
        mock_audio = MagicMock()
        mock_output = MagicMock()

        mock_ffmpeg.input.return_value = mock_input
        mock_input.video.filter.return_value = mock_video
        mock_input.audio = mock_audio
        mock_ffmpeg.output.return_value = mock_output
        mock_ffmpeg.run.return_value = None

        converter.convert_to_hls(
            video_id,
            sample_video_file,
            scale="1280:720",
            preset="fast",
            crf=23,
            audio_bitrate="128k",
            hls_time=10
        )

        # Verify ffmpeg.input was called with input file
        mock_ffmpeg.input.assert_called_once_with(sample_video_file)

        # Verify video filter was called with scale
        mock_input.video.filter.assert_called_once_with('scale', w='1280', h='720')

        # Verify output was called with HLS params
        mock_ffmpeg.output.assert_called_once()
        call_args = mock_ffmpeg.output.call_args
        assert call_args[1]['format'] == 'hls'
        assert call_args[1]['vcodec'] == 'libx264'
        assert call_args[1]['preset'] == 'fast'
        assert call_args[1]['crf'] == 23
        assert call_args[1]['acodec'] == 'aac'
        assert call_args[1]['audio_bitrate'] == '128k'
        assert call_args[1]['hls_time'] == 10
        assert call_args[1]['hls_list_size'] == 0

        # Verify ffmpeg.run was called
        mock_ffmpeg.run.assert_called_once()


def test_convert_to_hls_returns_proxy_paths(converter, sample_video_file, temp_proxy_path):
    """Test that convert_to_hls returns correct proxy paths"""
    video_id = uuid4()

    with patch('src.services.ffmpeg.proxy.ffmpeg') as mock_ffmpeg:
        mock_input = MagicMock()
        mock_video = MagicMock()
        mock_audio = MagicMock()
        mock_output = MagicMock()

        mock_ffmpeg.input.return_value = mock_input
        mock_input.video.filter.return_value = mock_video
        mock_input.audio = mock_audio
        mock_ffmpeg.output.return_value = mock_output
        mock_ffmpeg.run.return_value = None

        result = converter.convert_to_hls(video_id, sample_video_file)

        assert 'proxy_path' in result
        assert 'proxy_dir' in result
        assert result['proxy_path'].endswith('master.m3u8')
        assert str(video_id) in result['proxy_dir']


def test_convert_to_hls_handles_scale_without_colon(converter, sample_video_file):
    """Test scale parameter without colon (proportional scaling)"""
    video_id = uuid4()

    with patch('src.services.ffmpeg.proxy.ffmpeg') as mock_ffmpeg:
        mock_input = MagicMock()
        mock_video = MagicMock()
        mock_audio = MagicMock()
        mock_output = MagicMock()

        mock_ffmpeg.input.return_value = mock_input
        mock_input.video.filter.return_value = mock_video
        mock_input.audio = mock_audio
        mock_ffmpeg.output.return_value = mock_output
        mock_ffmpeg.run.return_value = None

        converter.convert_to_hls(video_id, sample_video_file, scale="1280")

        # Should use proportional height (-1)
        mock_input.video.filter.assert_called_once_with('scale', w='1280', h=-1)


def test_convert_to_hls_cleans_up_on_failure(converter, sample_video_file, temp_proxy_path):
    """Test that failed conversion cleans up proxy directory"""
    video_id = uuid4()
    proxy_dir = Path(temp_proxy_path) / str(video_id)

    with patch('src.services.ffmpeg.proxy.ffmpeg') as mock_ffmpeg:
        mock_input = MagicMock()
        mock_video = MagicMock()
        mock_audio = MagicMock()
        mock_output = MagicMock()

        mock_ffmpeg.input.return_value = mock_input
        mock_input.video.filter.return_value = mock_video
        mock_input.audio = mock_audio
        mock_ffmpeg.output.return_value = mock_output

        # Simulate ffmpeg error
        mock_error = ffmpeg.Error('ffmpeg', b'', b'Encoding failed')
        mock_ffmpeg.run.side_effect = mock_error
        mock_ffmpeg.Error = ffmpeg.Error

        with pytest.raises(ffmpeg.Error):
            converter.convert_to_hls(video_id, sample_video_file)

        # Directory should be cleaned up
        assert not proxy_dir.exists()


def test_convert_to_hls_output_path_includes_segment_pattern(converter, sample_video_file):
    """Test that HLS segment filename pattern is correct"""
    video_id = uuid4()

    with patch('src.services.ffmpeg.proxy.ffmpeg') as mock_ffmpeg:
        mock_input = MagicMock()
        mock_video = MagicMock()
        mock_audio = MagicMock()
        mock_output = MagicMock()

        mock_ffmpeg.input.return_value = mock_input
        mock_input.video.filter.return_value = mock_video
        mock_input.audio = mock_audio
        mock_ffmpeg.output.return_value = mock_output
        mock_ffmpeg.run.return_value = None

        converter.convert_to_hls(video_id, sample_video_file)

        # Check segment filename pattern
        call_args = mock_ffmpeg.output.call_args
        segment_filename = call_args[1]['hls_segment_filename']
        assert 'segment_%03d.ts' in segment_filename
        assert str(video_id) in segment_filename


def test_get_conversion_progress_returns_none_placeholder(converter):
    """Test get_conversion_progress (placeholder implementation)"""
    video_id = uuid4()

    progress = converter.get_conversion_progress(video_id)

    # Should return None (placeholder)
    assert progress is None


def test_cancel_conversion_returns_false_placeholder(converter):
    """Test cancel_conversion (placeholder implementation)"""
    video_id = uuid4()

    result = converter.cancel_conversion(video_id)

    # Should return False (placeholder)
    assert result is False


def test_convert_to_hls_with_custom_encoding_params(converter, sample_video_file):
    """Test convert_to_hls with custom encoding parameters"""
    video_id = uuid4()

    with patch('src.services.ffmpeg.proxy.ffmpeg') as mock_ffmpeg:
        mock_input = MagicMock()
        mock_video = MagicMock()
        mock_audio = MagicMock()
        mock_output = MagicMock()

        mock_ffmpeg.input.return_value = mock_input
        mock_input.video.filter.return_value = mock_video
        mock_input.audio = mock_audio
        mock_ffmpeg.output.return_value = mock_output
        mock_ffmpeg.run.return_value = None

        converter.convert_to_hls(
            video_id,
            sample_video_file,
            scale="1920:1080",
            preset="slow",
            crf=18,
            audio_bitrate="256k",
            hls_time=6
        )

        # Verify custom params were used
        call_args = mock_ffmpeg.output.call_args[1]
        assert call_args['preset'] == 'slow'
        assert call_args['crf'] == 18
        assert call_args['audio_bitrate'] == '256k'
        assert call_args['hls_time'] == 6

        # Verify custom scale
        mock_input.video.filter.assert_called_once_with('scale', w='1920', h='1080')


def test_convert_to_hls_overwrite_existing_output(converter, sample_video_file):
    """Test that convert_to_hls overwrites existing output"""
    video_id = uuid4()

    with patch('src.services.ffmpeg.proxy.ffmpeg') as mock_ffmpeg:
        mock_input = MagicMock()
        mock_video = MagicMock()
        mock_audio = MagicMock()
        mock_output = MagicMock()

        mock_ffmpeg.input.return_value = mock_input
        mock_input.video.filter.return_value = mock_video
        mock_input.audio = mock_audio
        mock_ffmpeg.output.return_value = mock_output
        mock_ffmpeg.run.return_value = None

        converter.convert_to_hls(video_id, sample_video_file)

        # Verify overwrite_output=True
        call_args = mock_ffmpeg.run.call_args[1]
        assert call_args['overwrite_output'] is True
