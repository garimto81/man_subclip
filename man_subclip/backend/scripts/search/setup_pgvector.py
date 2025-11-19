#!/usr/bin/env python3
"""
Setup pgvector extension in Supabase PostgreSQL
This must run BEFORE creating tables
"""

import os
import sys
from supabase import create_client

def main():
    # Environment variables
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')  # service_role key

    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set")
        sys.exit(1)

    print(f"🔧 Setting up pgvector extension in Supabase...")
    print(f"📍 URL: {supabase_url}")

    try:
        client = create_client(supabase_url, supabase_key)

        # Execute SQL to enable pgvector extension
        # This requires service_role key with sufficient permissions
        sql = """
        -- Enable pgvector extension
        CREATE EXTENSION IF NOT EXISTS vector;

        -- Verify extension
        SELECT * FROM pg_extension WHERE extname = 'vector';
        """

        result = client.rpc('exec_sql', {'sql': sql}).execute()

        print("✅ pgvector extension enabled successfully")
        print(f"📊 Result: {result.data}")

        return 0

    except Exception as e:
        print(f"❌ Failed to setup pgvector: {str(e)}")
        print("\n💡 Troubleshooting:")
        print("1. Ensure you're using service_role key (not anon key)")
        print("2. Go to Supabase Dashboard → Database → Extensions")
        print("3. Manually enable 'vector' extension")
        print("4. Re-run this script")
        sys.exit(1)


if __name__ == '__main__':
    sys.exit(main())
