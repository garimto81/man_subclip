#!/usr/bin/env python3
"""
Create video_embeddings table and SQL functions for vector search
Requires pgvector extension to be enabled first
"""

import os
import sys
from supabase import create_client

# SQL schema for video embeddings table
CREATE_TABLE_SQL = """
-- Create video_embeddings table with pgvector
CREATE TABLE IF NOT EXISTS video_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id VARCHAR(255) UNIQUE NOT NULL,
    video_uri TEXT NOT NULL,
    embedding vector(1536),  -- Mixpeek uses 1536-dimensional embeddings
    dimension INTEGER NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on video_id for fast lookups
CREATE INDEX IF NOT EXISTS idx_video_embeddings_video_id
ON video_embeddings(video_id);

-- Create GiST index for vector similarity search (faster than ivfflat for small datasets)
CREATE INDEX IF NOT EXISTS idx_video_embeddings_embedding
ON video_embeddings USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Alternative: GiST index (better for small datasets <100k)
-- CREATE INDEX IF NOT EXISTS idx_video_embeddings_embedding_gist
-- ON video_embeddings USING gist (embedding);

-- Create index on metadata for filtering
CREATE INDEX IF NOT EXISTS idx_video_embeddings_metadata
ON video_embeddings USING gin (metadata);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_video_embeddings_updated_at
    BEFORE UPDATE ON video_embeddings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
"""

# SQL function for vector similarity search
CREATE_MATCH_FUNCTION_SQL = """
-- Create match_videos function for similarity search
CREATE OR REPLACE FUNCTION match_videos(
    query_embedding vector(1536),
    match_count int DEFAULT 10,
    filter_metadata jsonb DEFAULT NULL
)
RETURNS TABLE (
    video_id VARCHAR(255),
    video_uri TEXT,
    score FLOAT,
    metadata JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ve.video_id,
        ve.video_uri,
        1 - (ve.embedding <=> query_embedding) AS score,  -- Cosine similarity
        ve.metadata
    FROM video_embeddings ve
    WHERE
        CASE
            WHEN filter_metadata IS NOT NULL THEN
                ve.metadata @> filter_metadata
            ELSE TRUE
        END
    ORDER BY ve.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
"""

# SQL function for index statistics
CREATE_STATS_FUNCTION_SQL = """
-- Create get_index_stats function
CREATE OR REPLACE FUNCTION get_index_stats()
RETURNS TABLE (
    total_videos BIGINT,
    avg_dimension FLOAT,
    latest_indexed_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT AS total_videos,
        AVG(dimension)::FLOAT AS avg_dimension,
        MAX(created_at) AS latest_indexed_at
    FROM video_embeddings;
END;
$$;
"""

def main():
    # Environment variables
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')

    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set")
        sys.exit(1)

    print("🔧 Creating video_embeddings table and functions...")
    print(f"📍 URL: {supabase_url}")

    try:
        # Create Supabase client
        client = create_client(supabase_url, supabase_key)

        # Step 1: Create table
        print("\n📊 Step 1: Creating video_embeddings table...")
        # Note: In production, use Supabase SQL Editor or migration tool
        # For automated setup, we'll use direct SQL execution

        # Create table via SQL (this requires custom RPC or direct PostgreSQL connection)
        # For now, provide manual instructions
        print("✅ SQL schema ready (apply via Supabase SQL Editor):")
        print("\n" + "="*80)
        print(CREATE_TABLE_SQL)
        print("="*80)

        print("\n📊 Step 2: Creating match_videos function...")
        print("\n" + "="*80)
        print(CREATE_MATCH_FUNCTION_SQL)
        print("="*80)

        print("\n📊 Step 3: Creating get_index_stats function...")
        print("\n" + "="*80)
        print(CREATE_STATS_FUNCTION_SQL)
        print("="*80)

        print("\n✅ Setup SQL generated successfully!")
        print("\n📝 Manual Steps Required:")
        print("1. Go to Supabase Dashboard → SQL Editor")
        print("2. Copy and run the SQL above")
        print("3. Verify table created: SELECT * FROM video_embeddings LIMIT 1;")
        print("4. Re-run verify_supabase.py to confirm setup")

        # Alternative: Save SQL to file
        sql_file = "backend/scripts/search/supabase_setup.sql"
        with open(sql_file, 'w') as f:
            f.write("-- Supabase Video Search Setup SQL\n\n")
            f.write("-- Step 1: Create table\n")
            f.write(CREATE_TABLE_SQL)
            f.write("\n\n-- Step 2: Create match function\n")
            f.write(CREATE_MATCH_FUNCTION_SQL)
            f.write("\n\n-- Step 3: Create stats function\n")
            f.write(CREATE_STATS_FUNCTION_SQL)

        print(f"\n💾 SQL saved to: {sql_file}")

        return 0

    except Exception as e:
        print(f"❌ Failed to generate setup SQL: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    sys.exit(main())
