"""
Test Database Models
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base
from src.models import Video, Clip


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def db_session():
    """Create a test database session"""
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(bind=engine)
    session = TestSessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


def test_create_video(db_session):
    """Test creating a video record"""
    video = Video(
        filename="test_video.mp4",
        original_path="/nas/original/test.mp4",
        proxy_status="pending"
    )
    db_session.add(video)
    db_session.commit()

    assert video.video_id is not None
    assert video.filename == "test_video.mp4"
    assert video.proxy_status == "pending"
    assert video.created_at is not None


def test_create_clip(db_session):
    """Test creating a clip record"""
    # Create a video first
    video = Video(
        filename="test_video.mp4",
        original_path="/nas/original/test.mp4"
    )
    db_session.add(video)
    db_session.commit()

    # Create a clip
    clip = Clip(
        video_id=video.video_id,
        start_sec=10.5,
        end_sec=45.8,
        padding_sec=3.0,
        file_path="/nas/clips/test_clip.mp4"
    )
    db_session.add(clip)
    db_session.commit()

    assert clip.clip_id is not None
    assert clip.video_id == video.video_id
    assert clip.start_sec == 10.5
    assert clip.end_sec == 45.8


def test_video_clip_relationship(db_session):
    """Test video-clip relationship"""
    # Create a video
    video = Video(
        filename="test_video.mp4",
        original_path="/nas/original/test.mp4"
    )
    db_session.add(video)
    db_session.commit()

    # Create clips
    clip1 = Clip(
        video_id=video.video_id,
        start_sec=10.0,
        end_sec=20.0,
        file_path="/nas/clips/clip1.mp4"
    )
    clip2 = Clip(
        video_id=video.video_id,
        start_sec=30.0,
        end_sec=40.0,
        file_path="/nas/clips/clip2.mp4"
    )
    db_session.add_all([clip1, clip2])
    db_session.commit()

    # Test relationship
    assert len(video.clips) == 2
    assert video.clips[0].start_sec == 10.0
    assert video.clips[1].start_sec == 30.0


def test_cascade_delete(db_session):
    """Test that clips are deleted when video is deleted"""
    # Create video with clips
    video = Video(
        filename="test_video.mp4",
        original_path="/nas/original/test.mp4"
    )
    db_session.add(video)
    db_session.commit()

    clip = Clip(
        video_id=video.video_id,
        start_sec=10.0,
        end_sec=20.0,
        file_path="/nas/clips/clip.mp4"
    )
    db_session.add(clip)
    db_session.commit()

    # Delete video
    db_session.delete(video)
    db_session.commit()

    # Clip should be deleted too
    clips = db_session.query(Clip).all()
    assert len(clips) == 0
