"""
Video Search Integration Services

Mixpeek + Supabase pgvector based semantic video search
"""
from .video_search import VideoSearchService, get_video_search_service

__all__ = ["VideoSearchService", "get_video_search_service"]
