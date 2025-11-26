"""
Video Search Service

Mixpeek + Supabase pgvector based semantic video search
"""
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class VideoSearchError(Exception):
    """Video Search related errors"""
    pass


class VideoSearchService:
    """Video Search Service using Mixpeek embeddings and Supabase pgvector"""
    
    def __init__(self):
        self.mixpeek_client = None
        self.supabase_client = None
        self._initialized = False
        
    def _ensure_initialized(self):
        """Lazy initialization of clients"""
        if self._initialized:
            return
            
        if not settings.use_video_search:
            raise VideoSearchError("Video Search is disabled. Set USE_VIDEO_SEARCH=true")
            
        if not settings.mixpeek_api_key:
            raise VideoSearchError("MIXPEEK_API_KEY not configured")
            
        if not settings.supabase_url or not settings.supabase_key:
            raise VideoSearchError("SUPABASE_URL and SUPABASE_KEY required")
        
        try:
            from mixpeek import Mixpeek
            self.mixpeek_client = Mixpeek(api_key=settings.mixpeek_api_key)
            
            from supabase import create_client
            self.supabase_client = create_client(
                settings.supabase_url,
                settings.supabase_key
            )
            
            self._initialized = True
            logger.info("Video Search Service initialized successfully")
            
        except ImportError as e:
            raise VideoSearchError(f"Required package not installed: {e}")
        except Exception as e:
            raise VideoSearchError(f"Failed to initialize Video Search: {e}")
    
    async def index_video(
        self,
        gcs_path: str,
        video_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Index a video for search"""
        self._ensure_initialized()
        
        try:
            gcs_url = f"gs://{settings.gcs_bucket_name}/{gcs_path}"
            logger.info(f"Generating embedding for {gcs_path}")
            
            embedding_response = self.mixpeek_client.embed.video(
                url=gcs_url,
                model="video-v1"
            )
            
            embedding = embedding_response.get("embedding", [])
            
            if not embedding:
                raise VideoSearchError(f"Failed to generate embedding for {gcs_path}")
            
            record = {
                "video_id": video_id,
                "gcs_path": gcs_path,
                "embedding": embedding,
                "metadata": metadata or {},
                "indexed_at": datetime.utcnow().isoformat()
            }
            
            self.supabase_client.table("video_embeddings").upsert(
                record,
                on_conflict="video_id"
            ).execute()
            
            logger.info(f"Successfully indexed video: {video_id}")
            
            return {
                "success": True,
                "video_id": video_id,
                "gcs_path": gcs_path,
                "embedding_dim": len(embedding)
            }
            
        except Exception as e:
            logger.error(f"Failed to index video {video_id}: {e}")
            raise VideoSearchError(f"Indexing failed: {e}")
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for videos by text query"""
        self._ensure_initialized()
        
        try:
            query_embedding = self.mixpeek_client.embed.text(
                text=query,
                model="text-v1"
            ).get("embedding", [])
            
            if not query_embedding:
                raise VideoSearchError("Failed to generate query embedding")
            
            result = self.supabase_client.rpc(
                "match_videos",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": threshold,
                    "match_count": top_k
                }
            ).execute()
            
            videos = result.data or []
            logger.info(f"Search returned {len(videos)} results")
            
            return [
                {
                    "video_id": v["video_id"],
                    "gcs_path": v["gcs_path"],
                    "similarity": v["similarity"],
                    "metadata": v.get("metadata", {})
                }
                for v in videos
            ]
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise VideoSearchError(f"Search failed: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get search index statistics"""
        self._ensure_initialized()
        
        try:
            result = self.supabase_client.table("video_embeddings").select(
                "video_id",
                count="exact"
            ).execute()
            
            return {
                "total_videos": result.count or 0,
                "index_status": "healthy",
                "last_checked": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "total_videos": 0,
                "index_status": "error",
                "error": str(e)
            }
    
    async def delete_video(self, video_id: str) -> bool:
        """Remove a video from the search index"""
        self._ensure_initialized()
        
        try:
            result = self.supabase_client.table("video_embeddings").delete().eq(
                "video_id", video_id
            ).execute()
            
            deleted = len(result.data) > 0 if result.data else False
            
            if deleted:
                logger.info(f"Deleted video from index: {video_id}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to delete video {video_id}: {e}")
            return False


_video_search_service: Optional[VideoSearchService] = None


def get_video_search_service() -> VideoSearchService:
    """Get or create Video Search Service instance"""
    global _video_search_service
    
    if _video_search_service is None:
        _video_search_service = VideoSearchService()
    
    return _video_search_service
