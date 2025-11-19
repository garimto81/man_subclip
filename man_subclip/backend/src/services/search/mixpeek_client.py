"""
Mixpeek Client - Multimodal video embedding generation
"""

import logging
from typing import Dict, List, Any, Optional
import httpx

logger = logging.getLogger(__name__)


class MixpeekClient:
    """
    Wrapper for Mixpeek API
    Generates multimodal embeddings for video, image, text, and audio
    """

    BASE_URL = "https://api.mixpeek.com/v1"

    def __init__(self, api_key: str):
        """
        Initialize Mixpeek client

        Args:
            api_key: Mixpeek API key from https://mixpeek.com/dashboard
        """
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    async def embed_video(
        self,
        url: str,
        extract_features: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate multimodal embedding for video

        Args:
            url: Video URL (GCS signed URL or public URL)
            extract_features: Features to extract
                             ["visual", "audio", "text"]
                             Default: all features

        Returns:
            {
                "embedding": List[float],  # 1536-dim vector
                "features": {
                    "visual": {...},
                    "audio": {...},
                    "text": {...}
                }
            }
        """
        logger.info(f"Generating video embedding for: {url}")

        payload = {
            "url": url,
            "features": extract_features or ["visual", "audio", "text"]
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/embed/video",
                headers=self.headers,
                json=payload
            )

            response.raise_for_status()
            result = response.json()

            logger.info(f"✅ Video embedding generated: {len(result['embedding'])} dimensions")

            return result

    async def embed_text(self, text: str) -> Dict[str, Any]:
        """
        Generate text embedding for search queries

        Args:
            text: Search query or description

        Returns:
            {
                "embedding": List[float],
                "text": str
            }
        """
        logger.info(f"Generating text embedding for: '{text[:50]}...'")

        payload = {"text": text}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/embed/text",
                headers=self.headers,
                json=payload
            )

            response.raise_for_status()
            result = response.json()

            logger.info(f"✅ Text embedding generated")

            return result

    async def embed_image(self, url: str) -> Dict[str, Any]:
        """
        Generate image embedding (for thumbnails)

        Args:
            url: Image URL

        Returns:
            {
                "embedding": List[float]
            }
        """
        logger.info(f"Generating image embedding for: {url}")

        payload = {"url": url}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/embed/image",
                headers=self.headers,
                json=payload
            )

            response.raise_for_status()
            result = response.json()

            logger.info(f"✅ Image embedding generated")

            return result

    async def analyze_video_content(
        self,
        url: str,
        analysis_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Deep video content analysis

        Args:
            url: Video URL
            analysis_types: ["objects", "actions", "scenes", "text", "speech"]

        Returns:
            {
                "objects": [{"label": str, "confidence": float, "timestamp": float}, ...],
                "actions": [...],
                "scenes": [...],
                "text": [...],
                "speech": {"transcription": str, "language": str}
            }
        """
        logger.info(f"Analyzing video content: {url}")

        payload = {
            "url": url,
            "analysis_types": analysis_types or ["objects", "actions", "scenes", "speech"]
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/analyze/video",
                headers=self.headers,
                json=payload
            )

            response.raise_for_status()
            result = response.json()

            logger.info(f"✅ Video analysis complete")

            return result
