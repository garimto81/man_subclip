#!/usr/bin/env python3
"""
Verify Supabase connection and pgvector setup
"""

import os
import sys
from supabase import create_client

def main():
    print("🔍 Verifying Supabase setup...\n")

    # Check environment variables
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')

    if not supabase_url:
        print("❌ SUPABASE_URL not set")
        return 1

    if not supabase_key:
        print("❌ SUPABASE_KEY not set")
        return 1

    print(f"✅ Environment variables set")
    print(f"   URL: {supabase_url}")
    print(f"   Key: {supabase_key[:20]}...")

    try:
        # Connect to Supabase
        print("\n📡 Connecting to Supabase...")
        client = create_client(supabase_url, supabase_key)
        print("✅ Connection successful")

        # Check if video_embeddings table exists
        print("\n📊 Checking video_embeddings table...")
        result = client.table('video_embeddings').select('*').limit(1).execute()
        print(f"✅ Table exists (found {len(result.data)} rows)")

        # Check pgvector extension
        print("\n🔧 Checking pgvector extension...")
        # Note: This requires custom RPC or direct PostgreSQL connection
        print("⚠️ Manual verification required:")
        print("   1. Go to Supabase Dashboard → SQL Editor")
        print("   2. Run: SELECT * FROM pg_extension WHERE extname = 'vector';")
        print("   3. Verify 'vector' extension is listed")

        # Check match_videos function
        print("\n🔍 Checking match_videos function...")
        print("⚠️ Manual verification required:")
        print("   1. Go to Supabase Dashboard → Database → Functions")
        print("   2. Verify 'match_videos' function exists")

        print("\n✅ Supabase setup verification complete!")
        print("\n📝 Next steps:")
        print("   1. Ensure pgvector extension is enabled")
        print("   2. Run create_tables.py to create schema")
        print("   3. Test with verify_mixpeek.py")

        return 0

    except Exception as e:
        print(f"\n❌ Verification failed: {str(e)}")
        print("\n💡 Troubleshooting:")
        print("   1. Check SUPABASE_URL format: https://xxx.supabase.co")
        print("   2. Ensure using service_role key (not anon key)")
        print("   3. Verify project is active in Supabase Dashboard")
        return 1


if __name__ == '__main__':
    sys.exit(main())
