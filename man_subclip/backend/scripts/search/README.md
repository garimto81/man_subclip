# 🚀 Search Integration - Quick Start

Fast setup guide for video search integration.

---

## ⚡ 5-Minute Setup (Automated)

### 1. Get API Keys

```bash
# Mixpeek: https://mixpeek.com → Sign up → Dashboard → Copy API Key
export MIXPEEK_API_KEY="your_mixpeek_api_key"

# Supabase: https://supabase.com → New Project → Settings → API
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your_service_role_key"  # NOT anon key!
```

### 2. Verify Setup

```bash
cd backend

# Test Mixpeek connection
python scripts/search/verify_mixpeek.py

# Test Supabase connection
python scripts/search/verify_supabase.py
```

### 3. Create Database Schema

```bash
# Generate SQL
python scripts/search/create_tables.py

# Copy output to Supabase SQL Editor and run
```

### 4. Index Videos

```bash
# Dry run (see what will be indexed)
python scripts/search/index_videos.py \
  --bucket wsop-archive-raw \
  --dry-run

# Index all videos
python scripts/search/index_videos.py \
  --bucket wsop-archive-raw \
  --batch-size 10 \
  --parallel 4
```

### 5. Test Search

```bash
# Start local API server
cd backend
uvicorn src.main:app --reload

# In another terminal:
curl -X POST http://localhost:8000/api/search/search \
  -H "Content-Type: application/json" \
  -d '{"query": "poker hand with all-in", "top_k": 5}'
```

---

## 🤖 Fully Automated (GitHub Actions)

### Setup GitHub Secrets

Go to GitHub → Settings → Secrets → Actions:

```
MIXPEEK_API_KEY
SUPABASE_URL
SUPABASE_KEY
GCP_SA_KEY
```

### Trigger Workflow

```bash
# Full setup (infrastructure + indexing + deployment)
gh workflow run search-integration.yml -f action=full-setup

# Monitor progress
gh run list --workflow=search-integration.yml

# View logs
gh run view --log
```

**Result**: Complete search system deployed to Cloud Run in ~15 minutes.

---

## 📋 Scripts Reference

| Script | Purpose | Usage |
|--------|---------|-------|
| `verify_mixpeek.py` | Test Mixpeek API | `python verify_mixpeek.py` |
| `verify_supabase.py` | Test Supabase connection | `python verify_supabase.py` |
| `setup_pgvector.py` | Enable pgvector extension | `python setup_pgvector.py` |
| `create_tables.py` | Generate DB schema SQL | `python create_tables.py` |
| `index_videos.py` | Index videos with embeddings | `python index_videos.py --bucket BUCKET` |
| `scan_videos.py` | List videos in GCS | `python scan_videos.py --bucket BUCKET` |
| `verify_index.py` | Check indexing status | `python verify_index.py` |

---

## 🔍 Example Queries

```bash
# Search by action
curl -X POST http://localhost:8000/api/search/search \
  -H "Content-Type: application/json" \
  -d '{"query": "all-in on river", "top_k": 10}'

# Search with filters
curl -X POST http://localhost:8000/api/search/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "final table action",
    "top_k": 10,
    "filters": {"tournament": "WSOP 2024"}
  }'

# Find similar videos
curl http://localhost:8000/api/search/similar/hand_123?top_k=5

# Get stats
curl http://localhost:8000/api/search/stats
```

---

## 💰 Cost Estimate

**For 1,000 videos**:
- Mixpeek indexing: ~$3
- Mixpeek searches (10k/month): ~$0.50
- Supabase: Free tier (500MB)
- Cloud Run: Free tier
- **Total**: ~$3.50/month

**For 10,000 videos**:
- Mixpeek indexing: ~$30
- Mixpeek searches (100k/month): ~$5
- Supabase Pro: $25
- Cloud Run: ~$5
- **Total**: ~$65/month

---

## 🐛 Troubleshooting

**"MIXPEEK_API_KEY not set"**
```bash
export MIXPEEK_API_KEY="your_key"
echo $MIXPEEK_API_KEY  # Verify
```

**"pgvector extension not found"**
```bash
# Enable in Supabase Dashboard:
# Database → Extensions → Search "vector" → Enable
```

**"match_videos function does not exist"**
```bash
# Run create_tables.py and copy SQL to Supabase SQL Editor
python scripts/search/create_tables.py
```

**Slow indexing**
```bash
# Increase parallelism
python scripts/search/index_videos.py --parallel 8
```

---

## 📚 Full Documentation

See `docs/SEARCH_INTEGRATION.md` for complete guide.

---

**Version**: 1.0.0 | **Last Updated**: 2025-01-19
