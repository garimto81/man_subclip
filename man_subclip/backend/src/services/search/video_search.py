"""
Video Search Service - Main orchestrator
Integrates Mixpeek embeddings with Supabase pgvector for semantic video search
"""

import asyncio
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import uuid

from .mixpeek_client import MixpeekClient
from .supabase_client import SupabaseClient

logger = logging.getLogger(__name__)


class VideoSearchService:
    """
    Semantic video search service using Mixpeek + Supabase

    Features:
    - Video embedding generation (Mixpeek)
    - Vector similarity search (Supabase pgvector)
    - Batch indexing with progress tracking
    - Hybrid search (text + visual + audio)
    """

    def __init__(
        self,
        mixpeek_api_key: str,
        supabase_url: str,
        supabase_key: str
    ):
        """
        Initialize search service

        Args:
            mixpeek_api_key: Mixpeek API key
            supabase_url: Supabase project URL
            supabase_key: Supabase API key (service_role)
        """
        self.mixpeek = MixpeekClient(api_key=mixpeek_api_key)
        self.supabase = SupabaseClient(url=supabase_url, key=supabase_key)

    async def index_video(
        self,
        video_uri: str,
        video_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Index a single video with Mixpeek embeddings

        Args:
            video_uri: GCS URI (gs://bucket/path.mp4) or public URL
            video_id: Unique video identifier
            metadata: Optional metadata (hand_id, tournament, etc.)

        Returns:
            {
                "video_id": str,
                "embedding_id": str,
                "indexed_at": datetime,
                "metadata": dict
            }
        """
        logger.info(f"Indexing video: {video_id} from {video_uri}")

        try:
            # 1. Generate Mixpeek embedding
            embedding_result = await self.mixpeek.embed_video(
                url=video_uri,
                extract_features=["visual", "audio", "text"]  # Multimodal
            )

            # 2. Store in Supabase with pgvector
            embedding_data = {
                "id": str(uuid.uuid4()),
                "video_id": video_id,
                "video_uri": video_uri,
                "embedding": embedding_result["embedding"],
                "dimension": len(embedding_result["embedding"]),
                "metadata": {
                    **(metadata or {}),
                    "mixpeek_features": embedding_result.get("features", {}),
                    "indexed_at": datetime.utcnow().isoformat()
                },
                "created_at": datetime.utcnow().isoformat()
            }

            result = await self.supabase.insert_embedding(embedding_data)

            logger.info(f"✅ Video indexed: {video_id} (embedding: {result['id']})")

            return {
                "video_id": video_id,
                "embedding_id": result["id"],
                "indexed_at": datetime.utcnow(),
                "metadata": embedding_data["metadata"]
            }

        except Exception as e:
            logger.error(f"❌ Failed to index video {video_id}: {str(e)}")
            raise

    async def index_videos_batch(
        self,
        videos: List[Dict[str, Any]],
        batch_size: int = 10,
        parallel: int = 4
    ) -> Dict[str, Any]:
        """
        Index multiple videos in parallel batches

        Args:
            videos: List of {"video_uri": str, "video_id": str, "metadata": dict}
            batch_size: Videos per batch
            parallel: Parallel workers

        Returns:
            {
                "total": int,
                "indexed": int,
                "failed": int,
                "duration_seconds": float,
                "results": List[dict]
            }
        """
        logger.info(f"Starting batch indexing: {len(videos)} videos, "
                   f"batch_size={batch_size}, parallel={parallel}")

        start_time = datetime.utcnow()
        results = []
        failed = 0

        # Process in batches
        for i in range(0, len(videos), batch_size):
            batch = videos[i:i + batch_size]
            logger.info(f"Processing batch {i // batch_size + 1} "
                       f"({len(batch)} videos)")

            # Parallel processing within batch
            tasks = [
                self.index_video(
                    video_uri=video["video_uri"],
                    video_id=video["video_id"],
                    metadata=video.get("metadata")
                )
                for video in batch
            ]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch indexing error: {result}")
                    failed += 1
                else:
                    results.append(result)

        duration = (datetime.utcnow() - start_time).total_seconds()

        summary = {
            "total": len(videos),
            "indexed": len(results),
            "failed": failed,
            "duration_seconds": round(duration, 2),
            "results": results
        }

        logger.info(f"✅ Batch indexing complete: {summary}")
        return summary

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for videos using text query

        Args:
            query: Natural language search query
                   Examples:
                   - "poker hand with all-in on river"
                   - "tournament final table action"
            top_k: Number of results to return
            filters: Optional metadata filters
                     {"hand_id": "...", "tournament": "WSOP 2024"}

        Returns:
            [
                {
                    "video_id": str,
                    "video_uri": str,
                    "score": float,  # Similarity score 0-1
                    "metadata": dict
                },
                ...
            ]
        """
        logger.info(f"Searching: '{query}' (top_k={top_k})")

        try:
            # 1. Generate query embedding
            query_embedding = await self.mixpeek.embed_text(text=query)

            # 2. Vector similarity search in Supabase
            results = await self.supabase.search_similar(
                query_embedding=query_embedding["embedding"],
                top_k=top_k,
                filters=filters
            )

            logger.info(f"✅ Found {len(results)} results")

            return results

        except Exception as e:
            logger.error(f"❌ Search failed: {str(e)}")
            raise

    async def search_by_video(
        self,
        video_uri: str,
        top_k: int = 10,
        exclude_self: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Find similar videos using video similarity

        Args:
            video_uri: Reference video URI
            top_k: Number of similar videos
            exclude_self: Exclude reference video from results

        Returns:
            Similar videos ranked by similarity
        """
        logger.info(f"Finding videos similar to: {video_uri}")

        try:
            # 1. Generate video embedding
            video_embedding = await self.mixpeek.embed_video(url=video_uri)

            # 2. Search similar
            results = await self.supabase.search_similar(
                query_embedding=video_embedding["embedding"],
                top_k=top_k + (1 if exclude_self else 0)
            )

            # 3. Exclude self if requested
            if exclude_self:
                results = [r for r in results if r["video_uri"] != video_uri][:top_k]

            logger.info(f"✅ Found {len(results)} similar videos")

            return results

        except Exception as e:
            logger.error(f"❌ Video similarity search failed: {str(e)}")
            raise

    async def get_index_stats(self) -> Dict[str, Any]:
        """
        Get indexing statistics

        Returns:
            {
                "total_videos": int,
                "total_embeddings": int,
                "avg_dimension": float,
                "latest_indexed_at": datetime
            }
        """
        return await self.supabase.get_stats()

    async def delete_video_index(self, video_id: str) -> bool:
        """
        Remove video from search index

        Args:
            video_id: Video to remove

        Returns:
            True if deleted
        """
        logger.info(f"Deleting index for video: {video_id}")

        result = await self.supabase.delete_embedding(video_id=video_id)

        if result:
            logger.info(f"✅ Index deleted: {video_id}")
        else:
            logger.warning(f"⚠️ Video not found in index: {video_id}")

        return result
