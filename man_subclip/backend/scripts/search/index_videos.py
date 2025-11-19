#!/usr/bin/env python3
"""
Index videos from GCS bucket with Mixpeek embeddings
Batch processing with progress tracking
"""

import os
import sys
import asyncio
import argparse
import json
from datetime import datetime
from google.cloud import storage
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.services.search import VideoSearchService


async def scan_gcs_bucket(bucket_name: str, prefix: str = "") -> List[Dict[str, Any]]:
    """
    Scan GCS bucket for videos

    Returns:
        List of {"video_uri": str, "video_id": str, "metadata": dict}
    """
    print(f"📁 Scanning GCS bucket: {bucket_name}")

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=prefix)

    videos = []
    video_extensions = {'.mp4', '.mov', '.mxf', '.avi', '.mkv'}

    for blob in blobs:
        # Check if file is a video
        _, ext = os.path.splitext(blob.name)
        if ext.lower() not in video_extensions:
            continue

        # Extract video_id from filename
        video_id = os.path.splitext(os.path.basename(blob.name))[0]

        videos.append({
            "video_uri": f"gs://{bucket_name}/{blob.name}",
            "video_id": video_id,
            "metadata": {
                "filename": blob.name,
                "size_mb": round(blob.size / (1024 * 1024), 2),
                "content_type": blob.content_type,
                "created_at": blob.time_created.isoformat() if blob.time_created else None
            }
        })

    print(f"✅ Found {len(videos)} videos in bucket")
    return videos


async def main():
    parser = argparse.ArgumentParser(description='Index videos with Mixpeek embeddings')
    parser.add_argument('--bucket', required=True, help='GCS bucket name')
    parser.add_argument('--prefix', default='', help='Bucket prefix/folder')
    parser.add_argument('--batch-size', type=int, default=10, help='Videos per batch')
    parser.add_argument('--parallel', type=int, default=4, help='Parallel workers')
    parser.add_argument('--limit', type=int, help='Limit total videos (for testing)')
    parser.add_argument('--dry-run', action='store_true', help='Show videos without indexing')

    args = parser.parse_args()

    # Environment variables
    mixpeek_api_key = os.getenv('MIXPEEK_API_KEY')
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')

    if not all([mixpeek_api_key, supabase_url, supabase_key]):
        print("❌ Error: Missing environment variables")
        print("Required: MIXPEEK_API_KEY, SUPABASE_URL, SUPABASE_KEY")
        sys.exit(1)

    print("="*80)
    print("🎬 Video Indexing Pipeline")
    print("="*80)
    print(f"📍 Bucket: {args.bucket}")
    print(f"📂 Prefix: {args.prefix or '(root)'}")
    print(f"📦 Batch size: {args.batch_size}")
    print(f"⚡ Parallel: {args.parallel}")
    if args.limit:
        print(f"🔢 Limit: {args.limit} videos")
    if args.dry_run:
        print("🔍 Mode: DRY RUN (no indexing)")
    print("="*80)

    # Step 1: Scan GCS bucket
    videos = await scan_gcs_bucket(args.bucket, args.prefix)

    if not videos:
        print("⚠️ No videos found in bucket")
        sys.exit(0)

    # Apply limit
    if args.limit:
        videos = videos[:args.limit]
        print(f"🔢 Limited to {len(videos)} videos")

    # Dry run: just show videos
    if args.dry_run:
        print("\n📋 Videos found:")
        for i, video in enumerate(videos, 1):
            print(f"  {i}. {video['video_id']}")
            print(f"     URI: {video['video_uri']}")
            print(f"     Size: {video['metadata']['size_mb']} MB")
        print(f"\n✅ Dry run complete. Would index {len(videos)} videos.")
        return 0

    # Step 2: Initialize search service
    print("\n🔧 Initializing search service...")
    service = VideoSearchService(
        mixpeek_api_key=mixpeek_api_key,
        supabase_url=supabase_url,
        supabase_key=supabase_key
    )

    # Step 3: Batch indexing
    print(f"\n🚀 Starting batch indexing ({len(videos)} videos)...")
    start_time = datetime.utcnow()

    result = await service.index_videos_batch(
        videos=videos,
        batch_size=args.batch_size,
        parallel=args.parallel
    )

    duration = (datetime.utcnow() - start_time).total_seconds()

    # Step 4: Report
    print("\n"+"="*80)
    print("📊 Indexing Report")
    print("="*80)
    print(f"Total videos: {result['total']}")
    print(f"Successfully indexed: {result['indexed']} ✅")
    print(f"Failed: {result['failed']} ❌")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Average: {duration / result['total']:.2f} seconds per video")
    print("="*80)

    # Save report
    report_file = f"indexing_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    report_path = os.path.join(os.path.dirname(__file__), report_file)

    with open(report_path, 'w') as f:
        json.dump({
            "bucket": args.bucket,
            "prefix": args.prefix,
            "total": result['total'],
            "indexed": result['indexed'],
            "failed": result['failed'],
            "duration_seconds": duration,
            "timestamp": datetime.utcnow().isoformat(),
            "results": result['results']
        }, f, indent=2)

    print(f"\n💾 Report saved: {report_path}")

    # Exit code
    if result['failed'] > 0:
        print(f"\n⚠️ Warning: {result['failed']} videos failed to index")
        return 1
    else:
        print("\n✅ All videos indexed successfully!")
        return 0


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
