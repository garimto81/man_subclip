"""
PostgreSQL Migration Runner
Runs SQL migration files without requiring psql
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import psycopg2
from psycopg2 import sql

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

def run_migration(migration_file: str):
    """Run a SQL migration file"""

    if not DATABASE_URL:
        print("[ERROR] DATABASE_URL not found in environment")
        print("\nPlease create .env file with:")
        print("DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/video_platform")
        sys.exit(1)

    # Read migration file
    migration_path = Path(__file__).parent.parent / 'migrations' / migration_file

    if not migration_path.exists():
        print(f"[ERROR] Migration file not found: {migration_path}")
        sys.exit(1)

    print(f"[INFO] Reading migration: {migration_file}")
    with open(migration_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # Split by semicolon (simple approach)
    # Note: This won't handle semicolons in strings/comments perfectly,
    # but works for our simple migration
    statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]

    print(f"\n[INFO] Connecting to database...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False  # Use transaction
        cursor = conn.cursor()

        print(f"[SUCCESS] Connected successfully!")
        print(f"\n[INFO] Executing {len(statements)} SQL statements...\n")

        for i, statement in enumerate(statements, 1):
            # Skip comments and empty lines
            if statement.startswith('--') or not statement:
                continue

            # Show first 60 chars of statement
            preview = statement[:60].replace('\n', ' ') + '...' if len(statement) > 60 else statement
            print(f"  [{i}/{len(statements)}] {preview}")

            try:
                cursor.execute(statement)
            except psycopg2.Error as e:
                print(f"\n[ERROR] Error executing statement {i}:")
                print(f"   {e}")
                conn.rollback()
                cursor.close()
                conn.close()
                sys.exit(1)

        # Commit transaction
        conn.commit()
        print(f"\n[SUCCESS] Migration completed successfully!")

        # Verify: Check if videos table exists
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'videos'
        """)

        if cursor.fetchone():
            print("\n[INFO] Verifying migration...")
            cursor.execute("SELECT COUNT(*) FROM videos")
            count = cursor.fetchone()[0]
            print(f"   [SUCCESS] Table 'videos' exists with {count} rows")

            if count > 0:
                cursor.execute("SELECT video_id, proxy_status FROM videos LIMIT 1")
                row = cursor.fetchone()
                print(f"   [INFO] Sample data: video_id={row[0]}, proxy_status={row[1]}")

        cursor.close()
        conn.close()

    except psycopg2.OperationalError as e:
        print(f"\n[ERROR] Database connection failed:")
        print(f"   {e}")
        print("\n[INFO] Troubleshooting:")
        print("   1. Check if Cloud SQL Proxy is running:")
        print("      cloud-sql-proxy gg-poker-prod:asia-northeast3:video-platform-db")
        print("   2. Verify DATABASE_URL in .env file")
        print("   3. Check password is correct")
        sys.exit(1)

    except Exception as e:
        print(f"\n[ERROR] Unexpected error:")
        print(f"   {e}")
        sys.exit(1)

if __name__ == '__main__':
    print("=" * 60)
    print("PostgreSQL Migration Runner")
    print("=" * 60)

    # Run the first migration
    run_migration('001_create_videos.sql')

    print("\n" + "=" * 60)
    print("[SUCCESS] Migration Complete!")
    print("=" * 60)
