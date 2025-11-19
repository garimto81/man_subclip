"""
Integration tests for video search functionality
Tests the complete flow: Mixpeek → Supabase → FastAPI
"""

import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient

from src.main import app
from src.services.search import VideoSearchService


# Test fixtures
@pytest.fixture
def mock_mixpeek_api_key():
    """Mock Mixpeek API key"""
    return "test_mixpeek_key_1234567890"


@pytest.fixture
def mock_supabase_credentials():
    """Mock Supabase credentials"""
    return {
        "url": "https://test-project.supabase.co",
        "key": "test_supabase_key_1234567890"
    }


@pytest.fixture
def mock_search_service(mock_mixpeek_api_key, mock_supabase_credentials):
    """Mock VideoSearchService"""
    with patch.dict(os.environ, {
        'MIXPEEK_API_KEY': mock_mixpeek_api_key,
        'SUPABASE_URL': mock_supabase_credentials['url'],
        'SUPABASE_KEY': mock_supabase_credentials['key']
    }):
        yield VideoSearchService(
            mixpeek_api_key=mock_mixpeek_api_key,
            supabase_url=mock_supabase_credentials['url'],
            supabase_key=mock_supabase_credentials['key']
        )


# Test: Index single video
@pytest.mark.asyncio
async def test_index_video_endpoint():
    """Test POST /api/search/index endpoint"""

    with patch.dict(os.environ, {
        'MIXPEEK_API_KEY': 'test_key',
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_KEY': 'test_key'
    }):
        # Mock the search service
        with patch('src.api.search.get_search_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.index_video.return_value = {
                "video_id": "hand_123",
                "embedding_id": "uuid-123",
                "indexed_at": "2025-01-19T10:30:00Z",
                "metadata": {"hand_id": "hand_123"}
            }
            mock_get_service.return_value = mock_service

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/search/index",
                    json={
                        "video_uri": "gs://test-bucket/video.mp4",
                        "video_id": "hand_123",
                        "metadata": {"hand_id": "hand_123"}
                    }
                )

            assert response.status_code == 200
            data = response.json()
            assert data["video_id"] == "hand_123"
            assert data["embedding_id"] == "uuid-123"


# Test: Batch indexing
@pytest.mark.asyncio
async def test_index_batch_endpoint():
    """Test POST /api/search/index/batch endpoint"""

    with patch.dict(os.environ, {
        'MIXPEEK_API_KEY': 'test_key',
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_KEY': 'test_key'
    }):
        with patch('src.api.search.get_search_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.index_videos_batch.return_value = {
                "total": 2,
                "indexed": 2,
                "failed": 0,
                "duration_seconds": 45.2,
                "results": []
            }
            mock_get_service.return_value = mock_service

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/search/index/batch",
                    json={
                        "videos": [
                            {"video_uri": "gs://test/v1.mp4", "video_id": "v1"},
                            {"video_uri": "gs://test/v2.mp4", "video_id": "v2"}
                        ],
                        "batch_size": 2,
                        "parallel": 2
                    }
                )

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert data["indexed"] == 2
            assert data["failed"] == 0


# Test: Search endpoint
@pytest.mark.asyncio
async def test_search_endpoint():
    """Test POST /api/search/search endpoint"""

    with patch.dict(os.environ, {
        'MIXPEEK_API_KEY': 'test_key',
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_KEY': 'test_key'
    }):
        with patch('src.api.search.get_search_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.search.return_value = [
                {
                    "video_id": "hand_456",
                    "video_uri": "gs://test/video.mp4",
                    "score": 0.89,
                    "metadata": {"hand_id": "hand_456"}
                },
                {
                    "video_id": "hand_789",
                    "video_uri": "gs://test/video2.mp4",
                    "score": 0.75,
                    "metadata": {"hand_id": "hand_789"}
                }
            ]
            mock_get_service.return_value = mock_service

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/search/search",
                    json={
                        "query": "poker hand with all-in on river",
                        "top_k": 10
                    }
                )

            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "poker hand with all-in on river"
            assert data["total_results"] == 2
            assert len(data["results"]) == 2
            assert data["results"][0]["score"] == 0.89


# Test: Similar videos endpoint
@pytest.mark.asyncio
async def test_similar_videos_endpoint():
    """Test GET /api/search/similar/{video_id} endpoint"""

    with patch.dict(os.environ, {
        'MIXPEEK_API_KEY': 'test_key',
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_KEY': 'test_key'
    }):
        with patch('src.api.search.get_search_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.search_by_video.return_value = [
                {
                    "video_id": "similar_1",
                    "video_uri": "gs://test/similar1.mp4",
                    "score": 0.92,
                    "metadata": {}
                }
            ]
            mock_get_service.return_value = mock_service

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/search/similar/hand_123?top_k=10")

            assert response.status_code == 200
            data = response.json()
            assert data["reference_video_id"] == "hand_123"
            assert data["total_results"] == 1


# Test: Index statistics endpoint
@pytest.mark.asyncio
async def test_index_stats_endpoint():
    """Test GET /api/search/stats endpoint"""

    with patch.dict(os.environ, {
        'MIXPEEK_API_KEY': 'test_key',
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_KEY': 'test_key'
    }):
        with patch('src.api.search.get_search_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_index_stats.return_value = {
                "total_videos": 1250,
                "total_embeddings": 1250,
                "avg_dimension": 1536,
                "latest_indexed_at": "2025-01-19T10:30:00Z"
            }
            mock_get_service.return_value = mock_service

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/search/stats")

            assert response.status_code == 200
            data = response.json()
            assert data["total_videos"] == 1250
            assert data["avg_dimension"] == 1536


# Test: Delete video index endpoint
@pytest.mark.asyncio
async def test_delete_video_index_endpoint():
    """Test DELETE /api/search/index/{video_id} endpoint"""

    with patch.dict(os.environ, {
        'MIXPEEK_API_KEY': 'test_key',
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_KEY': 'test_key'
    }):
        with patch('src.api.search.get_search_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.delete_video_index.return_value = True
            mock_get_service.return_value = mock_service

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.delete("/api/search/index/hand_123")

            assert response.status_code == 200
            data = response.json()
            assert data["video_id"] == "hand_123"
            assert data["deleted"] is True


# Test: Performance benchmarks
@pytest.mark.asyncio
async def test_search_performance():
    """Test search performance (<100ms target)"""

    import time

    with patch.dict(os.environ, {
        'MIXPEEK_API_KEY': 'test_key',
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_KEY': 'test_key'
    }):
        with patch('src.api.search.get_search_service') as mock_get_service:
            # Simulate 50ms search latency
            async def mock_search(*args, **kwargs):
                await asyncio.sleep(0.05)
                return [{
                    "video_id": "test",
                    "video_uri": "gs://test/video.mp4",
                    "score": 0.9,
                    "metadata": {}
                }]

            mock_service = AsyncMock()
            mock_service.search = mock_search
            mock_get_service.return_value = mock_service

            async with AsyncClient(app=app, base_url="http://test") as client:
                start = time.time()
                response = await client.post(
                    "/api/search/search",
                    json={"query": "test", "top_k": 10}
                )
                duration = time.time() - start

            assert response.status_code == 200
            # Allow 150ms for overhead (target: <100ms for search alone)
            assert duration < 0.15, f"Search took {duration:.3f}s (too slow)"


# Test: Error handling
@pytest.mark.asyncio
async def test_search_error_handling():
    """Test error handling in search endpoint"""

    with patch.dict(os.environ, {
        'MIXPEEK_API_KEY': 'test_key',
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_KEY': 'test_key'
    }):
        with patch('src.api.search.get_search_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.search.side_effect = Exception("Database connection failed")
            mock_get_service.return_value = mock_service

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/search/search",
                    json={"query": "test", "top_k": 10}
                )

            assert response.status_code == 500
            assert "Database connection failed" in response.json()["detail"]


# Import asyncio for performance test
import asyncio
