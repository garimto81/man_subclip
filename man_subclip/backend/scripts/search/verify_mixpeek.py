#!/usr/bin/env python3
"""
Verify Mixpeek API connection and test embedding generation
"""

import os
import sys
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.services.search.mixpeek_client import MixpeekClient


async def main():
    print("🔍 Verifying Mixpeek API setup...\n")

    # Check environment variable
    api_key = os.getenv('MIXPEEK_API_KEY')

    if not api_key:
        print("❌ MIXPEEK_API_KEY not set")
        print("\n💡 Get your API key:")
        print("   1. Go to https://mixpeek.com/dashboard")
        print("   2. Copy API key")
        print("   3. Set: export MIXPEEK_API_KEY='your_key_here'")
        return 1

    print(f"✅ MIXPEEK_API_KEY set: {api_key[:20]}...")

    try:
        # Initialize client
        print("\n📡 Initializing Mixpeek client...")
        client = MixpeekClient(api_key=api_key)
        print("✅ Client initialized")

        # Test text embedding (fast test)
        print("\n📝 Testing text embedding...")
        test_text = "poker hand with all-in on river"
        result = await client.embed_text(text=test_text)

        print(f"✅ Text embedding generated")
        print(f"   Dimensions: {len(result['embedding'])}")
        print(f"   First 5 values: {result['embedding'][:5]}")

        # Test with public video URL (optional)
        test_video = input("\n🎬 Test video embedding? Paste public video URL (or press Enter to skip): ").strip()

        if test_video:
            print(f"\n📹 Testing video embedding for: {test_video}")
            print("⏳ This may take 30-60 seconds...")

            video_result = await client.embed_video(
                url=test_video,
                extract_features=["visual"]  # Just visual for speed
            )

            print(f"✅ Video embedding generated")
            print(f"   Dimensions: {len(video_result['embedding'])}")
            print(f"   Features: {list(video_result.get('features', {}).keys())}")
        else:
            print("⏭️ Skipped video embedding test")

        print("\n✅ Mixpeek API verification complete!")
        print("\n📝 Next steps:")
        print("   1. Configure Supabase (verify_supabase.py)")
        print("   2. Create tables (create_tables.py)")
        print("   3. Index videos (index_videos.py)")

        return 0

    except Exception as e:
        print(f"\n❌ Verification failed: {str(e)}")
        print("\n💡 Troubleshooting:")
        print("   1. Verify API key is correct")
        print("   2. Check network connection")
        print("   3. Ensure Mixpeek account is active")
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
