"""
Storage Cleanup Script

Removes orphaned files from NAS storage:
- Original videos without database records
- Proxy files for deleted videos
- Clip files without database records

Usage:
    python scripts/storage_cleanup.py [--dry-run] [--days 30]
"""
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import SessionLocal
from src.models import Video, Clip
from src.config import get_settings
from src.utils.logger import setup_logger

logger = setup_logger("storage_cleanup")
settings = get_settings()


def find_orphaned_originals(dry_run: bool = False):
    """Find and remove original videos without database records"""
    db = SessionLocal()
    originals_path = Path(settings.nas_originals_path)

    if not originals_path.exists():
        logger.warning(f"Originals path does not exist: {originals_path}")
        return

    # Get all video IDs from database
    video_records = db.query(Video.original_path).all()
    valid_paths = {Path(record[0]) for record in video_records}

    orphaned_count = 0
    freed_space_mb = 0

    for video_file in originals_path.glob("**/*"):
        if not video_file.is_file():
            continue

        if video_file not in valid_paths:
            file_size_mb = video_file.stat().st_size / (1024 * 1024)
            orphaned_count += 1
            freed_space_mb += file_size_mb

            logger.info(f"Orphaned original: {video_file} ({file_size_mb:.2f}MB)")

            if not dry_run:
                video_file.unlink()
                logger.info(f"Deleted: {video_file}")

    logger.info(f"Orphaned originals: {orphaned_count} files, {freed_space_mb:.2f}MB")
    db.close()


def find_orphaned_proxies(dry_run: bool = False):
    """Find and remove proxy directories without database records"""
    db = SessionLocal()
    proxy_path = Path(settings.nas_proxy_path)

    if not proxy_path.exists():
        logger.warning(f"Proxy path does not exist: {proxy_path}")
        return

    # Get all proxy paths from database
    proxy_records = db.query(Video.proxy_path).filter(Video.proxy_path.isnot(None)).all()
    valid_dirs = {Path(record[0]).parent for record in proxy_records}

    orphaned_count = 0
    freed_space_mb = 0

    for proxy_dir in proxy_path.iterdir():
        if not proxy_dir.is_dir():
            continue

        if proxy_dir not in valid_dirs:
            # Calculate directory size
            dir_size_mb = sum(
                f.stat().st_size for f in proxy_dir.glob("**/*") if f.is_file()
            ) / (1024 * 1024)

            orphaned_count += 1
            freed_space_mb += dir_size_mb

            logger.info(f"Orphaned proxy: {proxy_dir} ({dir_size_mb:.2f}MB)")

            if not dry_run:
                import shutil
                shutil.rmtree(proxy_dir)
                logger.info(f"Deleted: {proxy_dir}")

    logger.info(f"Orphaned proxies: {orphaned_count} directories, {freed_space_mb:.2f}MB")
    db.close()


def find_orphaned_clips(dry_run: bool = False):
    """Find and remove clip files without database records"""
    db = SessionLocal()
    clips_path = Path(settings.nas_clips_path)

    if not clips_path.exists():
        logger.warning(f"Clips path does not exist: {clips_path}")
        return

    # Get all clip paths from database
    clip_records = db.query(Clip.file_path).all()
    valid_paths = {Path(record[0]) for record in clip_records}

    orphaned_count = 0
    freed_space_mb = 0

    for clip_file in clips_path.glob("**/*"):
        if not clip_file.is_file():
            continue

        if clip_file not in valid_paths:
            file_size_mb = clip_file.stat().st_size / (1024 * 1024)
            orphaned_count += 1
            freed_space_mb += file_size_mb

            logger.info(f"Orphaned clip: {clip_file} ({file_size_mb:.2f}MB)")

            if not dry_run:
                clip_file.unlink()
                logger.info(f"Deleted: {clip_file}")

    logger.info(f"Orphaned clips: {orphaned_count} files, {freed_space_mb:.2f}MB")
    db.close()


def cleanup_old_files(days: int, dry_run: bool = False):
    """Remove files older than specified days"""
    cutoff_date = datetime.now() - timedelta(days=days)
    logger.info(f"Removing files older than {days} days (before {cutoff_date})")

    # Cleanup old originals
    originals_path = Path(settings.nas_originals_path)
    if originals_path.exists():
        for video_file in originals_path.glob("**/*"):
            if not video_file.is_file():
                continue

            modified_time = datetime.fromtimestamp(video_file.stat().st_mtime)
            if modified_time < cutoff_date:
                file_size_mb = video_file.stat().st_size / (1024 * 1024)
                logger.info(
                    f"Old file: {video_file} (modified: {modified_time}, size: {file_size_mb:.2f}MB)"
                )

                if not dry_run:
                    video_file.unlink()
                    logger.info(f"Deleted: {video_file}")


def main():
    parser = argparse.ArgumentParser(description="Clean up orphaned storage files")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Remove files older than N days (optional)",
    )
    parser.add_argument(
        "--orphaned-only",
        action="store_true",
        help="Only remove orphaned files (ignore --days)",
    )

    args = parser.parse_args()

    logger.info("=== Storage Cleanup Started ===")
    logger.info(f"Dry run: {args.dry_run}")

    # Find orphaned files
    find_orphaned_originals(args.dry_run)
    find_orphaned_proxies(args.dry_run)
    find_orphaned_clips(args.dry_run)

    # Cleanup old files if specified
    if args.days and not args.orphaned_only:
        cleanup_old_files(args.days, args.dry_run)

    logger.info("=== Storage Cleanup Completed ===")


if __name__ == "__main__":
    main()
