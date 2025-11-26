"""
Video Search Service Tests

Tests for Mixpeek + Supabase video search integration
"""
import pytest
from unittest.mock import patch, MagicMock

from src.services.search.video_search import (
    VideoSearchService,
    VideoSearchError,
    get_video_search_service
)


class TestVideoSearchService:
    """VideoSearchService unit tests"""

    def test_service_initialization(self):
        """Service initializes without errors"""
        service = VideoSearchService()
        assert service.mixpeek_client is None
        assert service.supabase_client is None
        assert service._initialized is False

    def test_ensure_initialized_disabled(self):
        """Raises error when video search is disabled"""
        service = VideoSearchService()
        
        with patch("src.services.search.video_search.settings") as mock_settings:
            mock_settings.use_video_search = False
            
            with pytest.raises(VideoSearchError) as exc_info:
                service._ensure_initialized()
            
            assert "disabled" in str(exc_info.value).lower()

    def test_ensure_initialized_missing_mixpeek_key(self):
        """Raises error when Mixpeek API key is missing"""
        service = VideoSearchService()
        
        with patch("src.services.search.video_search.settings") as mock_settings:
            mock_settings.use_video_search = True
            mock_settings.mixpeek_api_key = ""
            
            with pytest.raises(VideoSearchError) as exc_info:
                service._ensure_initialized()
            
            assert "MIXPEEK_API_KEY" in str(exc_info.value)

    def test_ensure_initialized_missing_supabase(self):
        """Raises error when Supabase credentials are missing"""
        service = VideoSearchService()
        
        with patch("src.services.search.video_search.settings") as mock_settings:
            mock_settings.use_video_search = True
            mock_settings.mixpeek_api_key = "test-key"
            mock_settings.supabase_url = ""
            mock_settings.supabase_key = ""
            
            with pytest.raises(VideoSearchError) as exc_info:
                service._ensure_initialized()
            
            assert "SUPABASE" in str(exc_info.value)


class TestVideoSearchServiceMocked:
    """VideoSearchService tests with mocked dependencies"""

    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        """Search returns formatted results"""
        service = VideoSearchService()
        service._initialized = True
        
        service.mixpeek_client = MagicMock()
        service.mixpeek_client.embed.text.return_value = {
            "embedding": [0.1] * 1536
        }
        
        service.supabase_client = MagicMock()
        service.supabase_client.rpc.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "video_id": "video-1",
                    "gcs_path": "test.mp4",
                    "similarity": 0.95,
                    "metadata": {}
                }
            ]
        )
        
        results = await service.search("test query", top_k=5)
        
        assert len(results) == 1
        assert results[0]["video_id"] == "video-1"
        assert results[0]["similarity"] == 0.95

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        """Search returns empty list when no matches"""
        service = VideoSearchService()
        service._initialized = True
        
        service.mixpeek_client = MagicMock()
        service.mixpeek_client.embed.text.return_value = {
            "embedding": [0.1] * 1536
        }
        
        service.supabase_client = MagicMock()
        service.supabase_client.rpc.return_value.execute.return_value = MagicMock(
            data=[]
        )
        
        results = await service.search("no matches", top_k=5)
        
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_index_video_success(self):
        """Index video successfully"""
        service = VideoSearchService()
        service._initialized = True
        
        with patch("src.services.search.video_search.settings") as mock_settings:
            mock_settings.gcs_bucket_name = "test-bucket"
            
            service.mixpeek_client = MagicMock()
            service.mixpeek_client.embed.video.return_value = {
                "embedding": [0.1] * 1536
            }
            
            service.supabase_client = MagicMock()
            service.supabase_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()
            
            result = await service.index_video(
                gcs_path="test.mp4",
                video_id="video-123"
            )
            
            assert result["success"] is True
            assert result["video_id"] == "video-123"
            assert result["embedding_dim"] == 1536

    @pytest.mark.asyncio
    async def test_get_stats_success(self):
        """Get stats returns correct format"""
        service = VideoSearchService()
        service._initialized = True
        
        service.supabase_client = MagicMock()
        service.supabase_client.table.return_value.select.return_value.execute.return_value = MagicMock(
            count=100
        )
        
        stats = await service.get_stats()
        
        assert stats["total_videos"] == 100
        assert stats["index_status"] == "healthy"

    @pytest.mark.asyncio
    async def test_delete_video_success(self):
        """Delete video returns True when successful"""
        service = VideoSearchService()
        service._initialized = True
        
        service.supabase_client = MagicMock()
        service.supabase_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"video_id": "video-123"}]
        )
        
        result = await service.delete_video("video-123")
        
        assert result is True


class TestGetVideoSearchService:
    """Test singleton factory function"""

    def test_returns_same_instance(self):
        """Factory returns same instance"""
        import src.services.search.video_search as module
        module._video_search_service = None
        
        service1 = get_video_search_service()
        service2 = get_video_search_service()
        
        assert service1 is service2
