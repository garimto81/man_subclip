"""
Video Search API Endpoints

Semantic video search using Mixpeek + Supabase pgvector
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from src.config import get_settings
from src.services.search.video_search import (
    VideoSearchService,
    VideoSearchError,
    get_video_search_service
)

settings = get_settings()
router = APIRouter(prefix="/api/search", tags=["search"])


# Request/Response schemas
class SearchRequest(BaseModel):
    """Search request schema"""
    query: str = Field(..., min_length=1, description="Search query")
    top_k: int = Field(default=5, ge=1, le=100, description="Number of results")
    threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Similarity threshold")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "poker hand with all-in",
                "top_k": 5,
                "threshold": 0.7
            }
        }


class SearchResult(BaseModel):
    """Single search result"""
    video_id: str
    gcs_path: str
    similarity: float
    metadata: Dict[str, Any] = {}


class SearchResponse(BaseModel):
    """Search response schema"""
    results: List[SearchResult]
    total: int
    query: str


class IndexRequest(BaseModel):
    """Video indexing request"""
    gcs_path: str = Field(..., description="GCS path to video")
    video_id: str = Field(..., description="Unique video ID")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "gcs_path": "2025/day1/table1.mp4",
                "video_id": "video-123",
                "metadata": {"table": "1", "day": "day1"}
            }
        }


class IndexResponse(BaseModel):
    """Indexing response"""
    success: bool
    video_id: str
    gcs_path: str
    embedding_dim: int


class StatsResponse(BaseModel):
    """Search stats response"""
    total_videos: int
    index_status: str
    last_checked: str
    error: Optional[str] = None


@router.post("/search", response_model=SearchResponse)
async def search_videos(
    request: SearchRequest,
    search_service: VideoSearchService = Depends(get_video_search_service)
):
    """
    Search for videos using natural language query
    
    Uses Mixpeek multimodal embeddings and Supabase pgvector for
    semantic similarity search.
    
    Example:
        POST /api/search/search
        {
            "query": "poker hand with all-in",
            "top_k": 5,
            "threshold": 0.7
        }
    """
    if not settings.use_video_search:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Video search is disabled. Set USE_VIDEO_SEARCH=true"
        )
    
    try:
        results = await search_service.search(
            query=request.query,
            top_k=request.top_k,
            threshold=request.threshold
        )
        
        return SearchResponse(
            results=[SearchResult(**r) for r in results],
            total=len(results),
            query=request.query
        )
        
    except VideoSearchError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/index", response_model=IndexResponse)
async def index_video(
    request: IndexRequest,
    search_service: VideoSearchService = Depends(get_video_search_service)
):
    """
    Index a video for search
    
    Generates multimodal embeddings using Mixpeek and stores
    them in Supabase pgvector.
    
    Example:
        POST /api/search/index
        {
            "gcs_path": "2025/day1/table1.mp4",
            "video_id": "video-123"
        }
    """
    if not settings.use_video_search:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Video search is disabled"
        )
    
    try:
        result = await search_service.index_video(
            gcs_path=request.gcs_path,
            video_id=request.video_id,
            metadata=request.metadata
        )
        
        return IndexResponse(**result)
        
    except VideoSearchError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/stats", response_model=StatsResponse)
async def get_search_stats(
    search_service: VideoSearchService = Depends(get_video_search_service)
):
    """
    Get search index statistics
    
    Returns total indexed videos and index health status.
    """
    if not settings.use_video_search:
        return StatsResponse(
            total_videos=0,
            index_status="disabled",
            last_checked="",
            error="Video search is disabled"
        )
    
    try:
        stats = await search_service.get_stats()
        return StatsResponse(**stats)
        
    except VideoSearchError as e:
        return StatsResponse(
            total_videos=0,
            index_status="error",
            last_checked="",
            error=str(e)
        )


@router.delete("/index/{video_id}")
async def delete_from_index(
    video_id: str,
    search_service: VideoSearchService = Depends(get_video_search_service)
):
    """
    Remove a video from the search index
    """
    if not settings.use_video_search:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Video search is disabled"
        )
    
    try:
        deleted = await search_service.delete_video(video_id)
        
        if deleted:
            return {"message": f"Video {video_id} removed from index"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video {video_id} not found in index"
            )
            
    except VideoSearchError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/health")
async def search_health():
    """
    Check video search service health
    """
    return {
        "service": "video-search",
        "enabled": settings.use_video_search,
        "mixpeek_configured": bool(settings.mixpeek_api_key),
        "supabase_configured": bool(settings.supabase_url and settings.supabase_key)
    }
