"""
Search API - Semantic video search endpoints
Mixpeek + Supabase integration
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os
import logging

from src.services.search import VideoSearchService

logger = logging.getLogger(__name__)

router = APIRouter()

# Configuration
MIXPEEK_API_KEY = os.getenv('MIXPEEK_API_KEY')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')


def get_search_service() -> VideoSearchService:
    """
    Dependency injection for search service
    """
    if not all([MIXPEEK_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
        raise HTTPException(
            status_code=500,
            detail="Search service not configured. Missing environment variables."
        )

    return VideoSearchService(
        mixpeek_api_key=MIXPEEK_API_KEY,
        supabase_url=SUPABASE_URL,
        supabase_key=SUPABASE_KEY
    )


# Request/Response Models
class IndexVideoRequest(BaseModel):
    """Request to index a video"""
    video_uri: str = Field(..., description="GCS URI or public URL")
    video_id: str = Field(..., description="Unique video identifier")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")


class IndexBatchRequest(BaseModel):
    """Request to index multiple videos"""
    videos: List[IndexVideoRequest] = Field(..., description="List of videos to index")
    batch_size: int = Field(10, ge=1, le=50, description="Batch size")
    parallel: int = Field(4, ge=1, le=10, description="Parallel workers")


class SearchRequest(BaseModel):
    """Search query request"""
    query: str = Field(..., min_length=1, description="Search query")
    top_k: int = Field(10, ge=1, le=100, description="Number of results")
    filters: Optional[Dict[str, Any]] = Field(None, description="Metadata filters")


class SearchResult(BaseModel):
    """Search result item"""
    video_id: str
    video_uri: str
    score: float = Field(..., ge=0, le=1, description="Similarity score")
    metadata: Dict[str, Any]


class SearchResponse(BaseModel):
    """Search response"""
    query: str
    total_results: int
    results: List[SearchResult]


# Endpoints
@router.post("/index", summary="Index a single video")
async def index_video(
    request: IndexVideoRequest,
    service: VideoSearchService = Depends(get_search_service)
):
    """
    Index a video for semantic search

    **Example Request**:
    ```json
    {
        "video_uri": "gs://wsop-archive-raw/hand_123.mp4",
        "video_id": "hand_123",
        "metadata": {
            "hand_id": "hand_123",
            "tournament": "WSOP 2024 Main Event",
            "table": "Final Table"
        }
    }
    ```

    **Response**:
    ```json
    {
        "video_id": "hand_123",
        "embedding_id": "uuid-...",
        "indexed_at": "2025-01-19T10:30:00Z",
        "metadata": {...}
    }
    ```
    """
    try:
        result = await service.index_video(
            video_uri=request.video_uri,
            video_id=request.video_id,
            metadata=request.metadata
        )
        return result

    except Exception as e:
        logger.error(f"Failed to index video: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index/batch", summary="Index multiple videos")
async def index_videos_batch(
    request: IndexBatchRequest,
    service: VideoSearchService = Depends(get_search_service)
):
    """
    Index multiple videos in parallel batches

    **Example Request**:
    ```json
    {
        "videos": [
            {"video_uri": "gs://...", "video_id": "hand_1", "metadata": {...}},
            {"video_uri": "gs://...", "video_id": "hand_2", "metadata": {...}}
        ],
        "batch_size": 10,
        "parallel": 4
    }
    ```

    **Response**:
    ```json
    {
        "total": 50,
        "indexed": 48,
        "failed": 2,
        "duration_seconds": 125.3,
        "results": [...]
    }
    ```
    """
    try:
        videos_data = [
            {
                "video_uri": v.video_uri,
                "video_id": v.video_id,
                "metadata": v.metadata
            }
            for v in request.videos
        ]

        result = await service.index_videos_batch(
            videos=videos_data,
            batch_size=request.batch_size,
            parallel=request.parallel
        )

        return result

    except Exception as e:
        logger.error(f"Failed to index videos batch: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SearchResponse, summary="Semantic search")
async def search_videos(
    request: SearchRequest,
    service: VideoSearchService = Depends(get_search_service)
):
    """
    Semantic search for videos using natural language

    **Example Request**:
    ```json
    {
        "query": "poker hand with all-in on river",
        "top_k": 10,
        "filters": {"tournament": "WSOP 2024"}
    }
    ```

    **Response**:
    ```json
    {
        "query": "poker hand with all-in on river",
        "total_results": 10,
        "results": [
            {
                "video_id": "hand_456",
                "video_uri": "gs://...",
                "score": 0.89,
                "metadata": {...}
            },
            ...
        ]
    }
    ```
    """
    try:
        results = await service.search(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters
        )

        return SearchResponse(
            query=request.query,
            total_results=len(results),
            results=[
                SearchResult(
                    video_id=r["video_id"],
                    video_uri=r["video_uri"],
                    score=r["score"],
                    metadata=r["metadata"]
                )
                for r in results
            ]
        )

    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/similar/{video_id}", summary="Find similar videos")
async def find_similar_videos(
    video_id: str,
    top_k: int = Query(10, ge=1, le=100),
    service: VideoSearchService = Depends(get_search_service)
):
    """
    Find videos similar to a given video

    **Example**: `/api/search/similar/hand_123?top_k=10`

    **Response**:
    ```json
    {
        "reference_video_id": "hand_123",
        "total_results": 10,
        "results": [...]
    }
    ```
    """
    try:
        # Get reference video URI from database
        # For now, assume video_uri follows pattern
        video_uri = f"gs://wsop-archive-raw/{video_id}.mp4"

        results = await service.search_by_video(
            video_uri=video_uri,
            top_k=top_k,
            exclude_self=True
        )

        return {
            "reference_video_id": video_id,
            "total_results": len(results),
            "results": results
        }

    except Exception as e:
        logger.error(f"Similar video search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", summary="Get index statistics")
async def get_index_stats(
    service: VideoSearchService = Depends(get_search_service)
):
    """
    Get search index statistics

    **Response**:
    ```json
    {
        "total_videos": 1250,
        "total_embeddings": 1250,
        "avg_dimension": 1536,
        "latest_indexed_at": "2025-01-19T10:30:00Z"
    }
    ```
    """
    try:
        stats = await service.get_index_stats()
        return stats

    except Exception as e:
        logger.error(f"Failed to get stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/index/{video_id}", summary="Delete video from index")
async def delete_video_index(
    video_id: str,
    service: VideoSearchService = Depends(get_search_service)
):
    """
    Remove video from search index

    **Example**: `/api/search/index/hand_123` (DELETE)

    **Response**:
    ```json
    {
        "video_id": "hand_123",
        "deleted": true
    }
    ```
    """
    try:
        deleted = await service.delete_video_index(video_id)

        if deleted:
            return {"video_id": video_id, "deleted": True}
        else:
            raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")

    except Exception as e:
        logger.error(f"Failed to delete index: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
