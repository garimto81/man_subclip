"""
Test FFmpeg Subclip Extraction Service

Testing lossless subclip extraction with codec copy
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from uuid import uuid4
import ffmpeg

from src.services.ffmpeg.subclip import SubclipExtractor, get_subclip_extractor


@pytest.fixture
def temp_clips_path(tmp_path):
    """Create temporary clips directory"""
    clips_path = tmp_path / "clips"
    clips_path.mkdir()
    return str(clips_path)


@pytest.fixture
def extractor(temp_clips_path):
    """Create SubclipExtractor instance with temp path"""
    return SubclipExtractor(temp_clips_path)


@pytest.fixture
def sample_video_file(tmp_path):
    """Create a fake video file for testing"""
    video_file = tmp_path / "original.mp4"
    video_file.write_bytes(b"fake video content")
    return str(video_file)


def test_subclip_extractor_initialization(temp_clips_path):
    """Test SubclipExtractor initialization"""
    extractor = SubclipExtractor(temp_clips_path)

    assert extractor.clips_base_path == Path(temp_clips_path)
    assert Path(temp_clips_path).exists()


def test_subclip_extractor_creates_base_directory_if_missing(tmp_path):
    """Test that extractor creates base directory"""
    clips_path = str(tmp_path / "new_clips")

    extractor = SubclipExtractor(clips_path)

    assert Path(clips_path).exists()


def test_factory_function_returns_extractor(temp_clips_path):
    """Test get_subclip_extractor factory function"""
    extractor = get_subclip_extractor(temp_clips_path)

    assert isinstance(extractor, SubclipExtractor)
    assert extractor.clips_base_path == Path(temp_clips_path)


def test_extract_subclip_raises_error_for_missing_input(extractor):
    """Test that extract_subclip raises ValueError for non-existent input file"""
    clip_id = uuid4()
    non_existent_path = "/nonexistent/video.mp4"

    with pytest.raises(ValueError, match="Input file not found"):
        extractor.extract_subclip(clip_id, non_existent_path, 10.0, 20.0)


def test_extract_subclip_raises_error_for_negative_start(extractor, sample_video_file):
    """Test that extract_subclip raises ValueError for negative start_sec"""
    clip_id = uuid4()

    with pytest.raises(ValueError, match="start_sec must be >= 0"):
        extractor.extract_subclip(clip_id, sample_video_file, -5.0, 20.0)


def test_extract_subclip_raises_error_when_end_before_start(extractor, sample_video_file):
    """Test that extract_subclip raises ValueError when end_sec <= start_sec"""
    clip_id = uuid4()

    with pytest.raises(ValueError, match="end_sec .* must be > start_sec"):
        extractor.extract_subclip(clip_id, sample_video_file, 20.0, 10.0)


def test_extract_subclip_raises_error_when_end_equals_start(extractor, sample_video_file):
    """Test that extract_subclip raises ValueError when end_sec == start_sec"""
    clip_id = uuid4()

    with pytest.raises(ValueError, match="end_sec .* must be > start_sec"):
        extractor.extract_subclip(clip_id, sample_video_file, 10.0, 10.0)


def test_extract_subclip_calls_ffmpeg_with_correct_params(extractor, sample_video_file):
    """Test that extract_subclip calls ffmpeg with correct parameters"""
    clip_id = uuid4()
    start_sec = 7234.5
    end_sec = 7398.2

    with patch('src.services.ffmpeg.subclip.ffmpeg') as mock_ffmpeg:
        # Mock ffmpeg chain
        mock_input = MagicMock()
        mock_output = MagicMock()

        mock_ffmpeg.input.return_value = mock_input
        mock_ffmpeg.output.return_value = mock_output
        mock_ffmpeg.run.return_value = None

        # Mock output file stat
        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat_result = MagicMock()
            mock_stat_result.st_size = 1024 * 1024  # 1 MB
            mock_stat.return_value = mock_stat_result

            extractor.extract_subclip(clip_id, sample_video_file, start_sec, end_sec)

        # Verify ffmpeg.input was called with correct params
        mock_ffmpeg.input.assert_called_once_with(
            sample_video_file,
            ss=start_sec,
            to=end_sec
        )

        # Verify output was called with codec copy
        mock_ffmpeg.output.assert_called_once()
        call_args = mock_ffmpeg.output.call_args[1]
        assert call_args['c'] == 'copy'
        assert call_args['avoid_negative_ts'] == 'make_zero'
        assert call_args['movflags'] == '+faststart'

        # Verify ffmpeg.run was called
        mock_ffmpeg.run.assert_called_once()


def test_extract_subclip_returns_correct_metadata(extractor, sample_video_file, temp_clips_path):
    """Test that extract_subclip returns correct metadata"""
    clip_id = uuid4()
    start_sec = 10.0
    end_sec = 45.8

    with patch('src.services.ffmpeg.subclip.ffmpeg') as mock_ffmpeg:
        mock_input = MagicMock()
        mock_output = MagicMock()

        mock_ffmpeg.input.return_value = mock_input
        mock_ffmpeg.output.return_value = mock_output
        mock_ffmpeg.run.return_value = None

        # Mock output file
        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat_result = MagicMock()
            mock_stat_result.st_size = 5 * 1024 * 1024  # 5 MB
            mock_stat.return_value = mock_stat_result

            result = extractor.extract_subclip(clip_id, sample_video_file, start_sec, end_sec)

        assert 'file_path' in result
        assert 'file_size_mb' in result
        assert 'duration_sec' in result
        assert str(clip_id) in result['file_path']
        assert result['file_path'].endswith('.mp4')
        assert result['file_size_mb'] == 5.0
        assert result['duration_sec'] == 35.8  # 45.8 - 10.0


def test_extract_subclip_with_custom_extension(extractor, sample_video_file):
    """Test extract_subclip with custom output extension"""
    clip_id = uuid4()

    with patch('src.services.ffmpeg.subclip.ffmpeg') as mock_ffmpeg:
        mock_input = MagicMock()
        mock_output = MagicMock()

        mock_ffmpeg.input.return_value = mock_input
        mock_ffmpeg.output.return_value = mock_output
        mock_ffmpeg.run.return_value = None

        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat_result = MagicMock()
            mock_stat_result.st_size = 1024 * 1024
            mock_stat.return_value = mock_stat_result

            result = extractor.extract_subclip(
                clip_id,
                sample_video_file,
                10.0,
                20.0,
                output_extension=".mov"
            )

        assert result['file_path'].endswith('.mov')


def test_extract_subclip_cleans_up_on_failure(extractor, sample_video_file, temp_clips_path):
    """Test that failed extraction cleans up output file"""
    clip_id = uuid4()
    output_path = Path(temp_clips_path) / f"{clip_id}.mp4"

    with patch('src.services.ffmpeg.subclip.ffmpeg') as mock_ffmpeg:
        mock_input = MagicMock()
        mock_output = MagicMock()

        mock_ffmpeg.input.return_value = mock_input
        mock_ffmpeg.output.return_value = mock_output

        # Create file before error (simulating partial write)
        output_path.write_bytes(b"partial content")

        # Simulate ffmpeg error
        mock_error = ffmpeg.Error('ffmpeg', b'', b'Extraction failed')
        mock_ffmpeg.run.side_effect = mock_error
        mock_ffmpeg.Error = ffmpeg.Error

        with pytest.raises(ffmpeg.Error):
            extractor.extract_subclip(clip_id, sample_video_file, 10.0, 20.0)

        # File should be cleaned up
        assert not output_path.exists()


def test_extract_subclip_uses_faststart_for_web_playback(extractor, sample_video_file):
    """Test that extract_subclip uses faststart movflag for web optimization"""
    clip_id = uuid4()

    with patch('src.services.ffmpeg.subclip.ffmpeg') as mock_ffmpeg:
        mock_input = MagicMock()
        mock_output = MagicMock()

        mock_ffmpeg.input.return_value = mock_input
        mock_ffmpeg.output.return_value = mock_output
        mock_ffmpeg.run.return_value = None

        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat_result = MagicMock()
            mock_stat_result.st_size = 1024 * 1024
            mock_stat.return_value = mock_stat_result

            extractor.extract_subclip(clip_id, sample_video_file, 10.0, 20.0)

        # Verify faststart movflag
        call_args = mock_ffmpeg.output.call_args[1]
        assert call_args['movflags'] == '+faststart'


def test_extract_subclip_uses_avoid_negative_ts(extractor, sample_video_file):
    """Test that extract_subclip uses avoid_negative_ts to fix timestamp issues"""
    clip_id = uuid4()

    with patch('src.services.ffmpeg.subclip.subclip.ffmpeg') as mock_ffmpeg:
        mock_input = MagicMock()
        mock_output = MagicMock()

        mock_ffmpeg.input.return_value = mock_input
        mock_ffmpeg.output.return_value = mock_output
        mock_ffmpeg.run.return_value = None

        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat_result = MagicMock()
            mock_stat_result.st_size = 1024 * 1024
            mock_stat.return_value = mock_stat_result

            extractor.extract_subclip(clip_id, sample_video_file, 10.0, 20.0)

        # Verify avoid_negative_ts
        call_args = mock_ffmpeg.output.call_args[1]
        assert call_args['avoid_negative_ts'] == 'make_zero'


def test_extract_subclip_overwrites_existing_output(extractor, sample_video_file):
    """Test that extract_subclip overwrites existing output"""
    clip_id = uuid4()

    with patch('src.services.ffmpeg.subclip.ffmpeg') as mock_ffmpeg:
        mock_input = MagicMock()
        mock_output = MagicMock()

        mock_ffmpeg.input.return_value = mock_input
        mock_ffmpeg.output.return_value = mock_output
        mock_ffmpeg.run.return_value = None

        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat_result = MagicMock()
            mock_stat_result.st_size = 1024 * 1024
            mock_stat.return_value = mock_stat_result

            extractor.extract_subclip(clip_id, sample_video_file, 10.0, 20.0)

        # Verify overwrite_output=True
        call_args = mock_ffmpeg.run.call_args[1]
        assert call_args['overwrite_output'] is True


def test_estimate_clip_size_calculates_correctly(extractor):
    """Test clip size estimation formula"""
    # 8 Mbps * 60 seconds / 8 bits per byte = 60 MB
    size = extractor.estimate_clip_size(video_bitrate_mbps=8.0, duration_sec=60.0)
    assert size == 60.0

    # 10 Mbps * 30 seconds / 8 = 37.5 MB
    size = extractor.estimate_clip_size(video_bitrate_mbps=10.0, duration_sec=30.0)
    assert size == 37.5

    # 4 Mbps * 120 seconds / 8 = 60 MB
    size = extractor.estimate_clip_size(video_bitrate_mbps=4.0, duration_sec=120.0)
    assert size == 60.0


def test_estimate_clip_size_handles_fractional_results(extractor):
    """Test clip size estimation with fractional results"""
    size = extractor.estimate_clip_size(video_bitrate_mbps=5.5, duration_sec=45.7)
    expected = (5.5 * 45.7) / 8
    assert abs(size - expected) < 0.001


def test_extract_subclip_with_precise_timecodes(extractor, sample_video_file):
    """Test extract_subclip with precise fractional timecodes"""
    clip_id = uuid4()
    start_sec = 7234.567
    end_sec = 7398.123

    with patch('src.services.ffmpeg.subclip.ffmpeg') as mock_ffmpeg:
        mock_input = MagicMock()
        mock_output = MagicMock()

        mock_ffmpeg.input.return_value = mock_input
        mock_ffmpeg.output.return_value = mock_output
        mock_ffmpeg.run.return_value = None

        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat_result = MagicMock()
            mock_stat_result.st_size = 1024 * 1024
            mock_stat.return_value = mock_stat_result

            result = extractor.extract_subclip(clip_id, sample_video_file, start_sec, end_sec)

        # Verify precise timecodes were passed
        mock_ffmpeg.input.assert_called_once_with(
            sample_video_file,
            ss=start_sec,
            to=end_sec
        )

        # Verify duration calculation
        expected_duration = end_sec - start_sec
        assert abs(result['duration_sec'] - expected_duration) < 0.001


def test_extract_subclip_with_zero_start_time(extractor, sample_video_file):
    """Test extract_subclip starting from beginning of video"""
    clip_id = uuid4()

    with patch('src.services.ffmpeg.subclip.ffmpeg') as mock_ffmpeg:
        mock_input = MagicMock()
        mock_output = MagicMock()

        mock_ffmpeg.input.return_value = mock_input
        mock_ffmpeg.output.return_value = mock_output
        mock_ffmpeg.run.return_value = None

        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat_result = MagicMock()
            mock_stat_result.st_size = 1024 * 1024
            mock_stat.return_value = mock_stat_result

            extractor.extract_subclip(clip_id, sample_video_file, 0.0, 30.0)

        # Should work with zero start time
        mock_ffmpeg.input.assert_called_once_with(
            sample_video_file,
            ss=0.0,
            to=30.0
        )
