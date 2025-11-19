"""
Supabase Client - pgvector storage and similarity search
"""

import logging
from typing import Dict, List, Any, Optional
from supabase import create_client, Client

logger = logging.getLogger(__name__)


class SupabaseClient:
    """
    Wrapper for Supabase with pgvector operations
    Handles embedding storage and vector similarity search
    """

    def __init__(self, url: str, key: str):
        """
        Initialize Supabase client

        Args:
            url: Supabase project URL
            key: Supabase service_role key (for admin operations)
        """
        self.client: Client = create_client(url, key)
        self.table_name = "video_embeddings"

    async def insert_embedding(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert video embedding into Supabase

        Args:
            data: {
                "id": str (UUID),
                "video_id": str,
                "video_uri": str,
                "embedding": List[float],
                "dimension": int,
                "metadata": dict,
                "created_at": str (ISO)
            }

        Returns:
            Inserted row data
        """
        logger.info(f"Inserting embedding for video: {data['video_id']}")

        result = self.client.table(self.table_name).insert(data).execute()

        if result.data:
            logger.info(f"✅ Embedding inserted: {data['video_id']}")
            return result.data[0]
        else:
            raise Exception(f"Failed to insert embedding: {result}")

    async def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Vector similarity search using pgvector

        Args:
            query_embedding: Query vector
            top_k: Number of results
            filters: Optional metadata filters
                     {"hand_id": "...", "tournament": "..."}

        Returns:
            [
                {
                    "video_id": str,
                    "video_uri": str,
                    "score": float,  # Cosine similarity 0-1
                    "metadata": dict
                },
                ...
            ]
        """
        logger.info(f"Searching for top {top_k} similar videos")

        # Use Supabase RPC function for vector similarity search
        # This calls the PostgreSQL function created in setup_pgvector.py
        rpc_params = {
            "query_embedding": query_embedding,
            "match_count": top_k
        }

        # Apply metadata filters if provided
        if filters:
            rpc_params["filter_metadata"] = filters

        result = self.client.rpc("match_videos", rpc_params).execute()

        if result.data:
            logger.info(f"✅ Found {len(result.data)} similar videos")
            return result.data
        else:
            logger.warning(f"⚠️ No results found")
            return []

    async def get_embedding(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get embedding for specific video

        Args:
            video_id: Video ID

        Returns:
            Embedding data or None
        """
        result = self.client.table(self.table_name).select("*").eq("video_id", video_id).execute()

        if result.data:
            return result.data[0]
        else:
            return None

    async def delete_embedding(self, video_id: str) -> bool:
        """
        Delete video embedding

        Args:
            video_id: Video ID

        Returns:
            True if deleted
        """
        logger.info(f"Deleting embedding for video: {video_id}")

        result = self.client.table(self.table_name).delete().eq("video_id", video_id).execute()

        if result.data:
            logger.info(f"✅ Embedding deleted: {video_id}")
            return True
        else:
            logger.warning(f"⚠️ Video not found: {video_id}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get index statistics

        Returns:
            {
                "total_videos": int,
                "total_embeddings": int,
                "avg_dimension": float,
                "latest_indexed_at": str
            }
        """
        logger.info("Fetching index statistics")

        # Count total embeddings
        count_result = self.client.table(self.table_name).select("*", count="exact").execute()
        total_count = count_result.count if count_result.count else 0

        # Get dimension statistics
        result = self.client.rpc("get_index_stats").execute()

        stats = {
            "total_embeddings": total_count,
            "total_videos": total_count,  # Assuming 1:1 mapping
            "avg_dimension": result.data[0]["avg_dimension"] if result.data else 0,
            "latest_indexed_at": result.data[0]["latest_indexed_at"] if result.data else None
        }

        logger.info(f"✅ Index stats: {stats}")

        return stats

    async def update_metadata(
        self,
        video_id: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Update metadata for video embedding

        Args:
            video_id: Video ID
            metadata: New metadata to merge

        Returns:
            True if updated
        """
        logger.info(f"Updating metadata for video: {video_id}")

        result = self.client.table(self.table_name).update(
            {"metadata": metadata}
        ).eq("video_id", video_id).execute()

        if result.data:
            logger.info(f"✅ Metadata updated: {video_id}")
            return True
        else:
            logger.warning(f"⚠️ Video not found: {video_id}")
            return False
