# Performance Optimization Guide

## Overview

This document outlines performance optimization strategies for the Video Proxy & Subclip Platform.

## Backend Optimizations

### 1. Parallel Video Processing

**Problem**: Sequential proxy rendering blocks other operations.

**Solution**: Celery task queue for parallel processing.

```python
# backend/src/tasks/celery_app.py
from celery import Celery

celery_app = Celery(
    'video_tasks',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

@celery_app.task
def proxy_rendering_task(video_id: str):
    """Background task for proxy rendering"""
    # Existing proxy conversion logic
    pass

@celery_app.task
def clip_extraction_task(clip_id: str, video_id: str, start_sec: float, end_sec: float):
    """Background task for clip extraction"""
    # Existing subclip extraction logic
    pass
```

**Benefits**:
- Process multiple videos simultaneously
- Non-blocking API responses
- Scalable worker pool

### 2. Database Query Optimization

**Problem**: N+1 queries when loading videos with clips.

**Solution**: Use SQLAlchemy `joinedload` for eager loading.

```python
# Before (N+1 queries)
videos = db.query(Video).all()
for video in videos:
    clips = video.clips  # Separate query for each video

# After (2 queries total)
from sqlalchemy.orm import joinedload

videos = db.query(Video).options(joinedload(Video.clips)).all()
```

**Indexing**:

```python
# Add indexes for frequently queried columns
class Video(Base):
    __tablename__ = "videos"

    video_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    filename = Column(String, nullable=False, index=True)  # Index for search
    proxy_status = Column(String, default="pending", index=True)  # Index for filtering
    created_at = Column(DateTime, default=datetime.utcnow, index=True)  # Index for sorting
```

### 3. Chunked File Upload

**Problem**: Large file uploads timeout or fail.

**Solution**: Resumable uploads with chunking.

```python
# backend/src/api/videos.py
from fastapi import UploadFile, File, Form

@router.post("/upload/chunked")
async def upload_video_chunk(
    chunk: UploadFile = File(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    upload_id: str = Form(...),
    filename: str = Form(...)
):
    """Handle chunked upload"""
    chunk_dir = Path(f"/tmp/uploads/{upload_id}")
    chunk_dir.mkdir(parents=True, exist_ok=True)

    # Save chunk
    chunk_path = chunk_dir / f"chunk_{chunk_index}"
    with open(chunk_path, "wb") as f:
        content = await chunk.read()
        f.write(content)

    # If all chunks received, assemble file
    if len(list(chunk_dir.glob("chunk_*"))) == total_chunks:
        return await assemble_chunks(upload_id, filename, total_chunks)

    return {"status": "chunk_received", "chunk_index": chunk_index}
```

### 4. Caching

**Redis caching** for frequently accessed data:

```python
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def get_video_cached(video_id: str):
    # Check cache first
    cached = redis_client.get(f"video:{video_id}")
    if cached:
        return json.loads(cached)

    # Query database
    video = db.query(Video).filter(Video.video_id == video_id).first()

    # Cache for 5 minutes
    redis_client.setex(
        f"video:{video_id}",
        300,
        json.dumps(video.to_dict())
    )

    return video
```

## Frontend Optimizations

### 1. Code Splitting

**Problem**: Large initial bundle size.

**Solution**: Lazy loading with React.lazy().

```typescript
// frontend/src/App.tsx
import { lazy, Suspense } from 'react'

const VideoPlayerPage = lazy(() => import('./pages/VideoPlayerPage'))
const UploadPage = lazy(() => import('./pages/UploadPage'))

function App() {
  return (
    <Suspense fallback={<Spin />}>
      <Routes>
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/video/:videoId" element={<VideoPlayerPage />} />
      </Routes>
    </Suspense>
  )
}
```

### 2. Virtual Scrolling

**Problem**: Rendering 1000+ video cards causes lag.

**Solution**: Use `react-window` for virtual scrolling.

```typescript
import { FixedSizeGrid } from 'react-window'

function VideoLibrary({ videos }) {
  const columnCount = 4
  const rowCount = Math.ceil(videos.length / columnCount)

  const Cell = ({ columnIndex, rowIndex, style }) => {
    const index = rowIndex * columnCount + columnIndex
    const video = videos[index]
    if (!video) return null

    return (
      <div style={style}>
        <VideoCard video={video} />
      </div>
    )
  }

  return (
    <FixedSizeGrid
      columnCount={columnCount}
      columnWidth={300}
      height={800}
      rowCount={rowCount}
      rowHeight={400}
      width={1200}
    >
      {Cell}
    </FixedSizeGrid>
  )
}
```

### 3. Image Optimization

**Thumbnail generation**:

```python
# backend/src/services/thumbnail.py
from PIL import Image
import subprocess

def generate_thumbnail(video_path: str, output_path: str, timestamp: float = 1.0):
    """Generate thumbnail from video at specific timestamp"""
    subprocess.run([
        'ffmpeg',
        '-ss', str(timestamp),
        '-i', video_path,
        '-vframes', '1',
        '-vf', 'scale=320:180',
        '-q:v', '2',
        output_path
    ])
```

**Responsive images**:

```typescript
<img
  src={`/api/thumbnails/${video.video_id}`}
  srcSet={`
    /api/thumbnails/${video.video_id}?size=320w 320w,
    /api/thumbnails/${video.video_id}?size=640w 640w,
    /api/thumbnails/${video.video_id}?size=1280w 1280w
  `}
  sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
  alt={video.filename}
/>
```

### 4. React Query for Data Fetching

**Problem**: Redundant API calls, no caching.

**Solution**: Use TanStack Query (React Query).

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

function VideoLibrary() {
  const queryClient = useQueryClient()

  // Fetch videos with caching
  const { data, isLoading } = useQuery({
    queryKey: ['videos'],
    queryFn: () => apiClient.listVideos(),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  })

  // Delete video with cache invalidation
  const deleteMutation = useMutation({
    mutationFn: (videoId: string) => apiClient.deleteVideo(videoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['videos'] })
    },
  })

  return (
    <div>
      {data?.videos.map(video => (
        <VideoCard
          key={video.video_id}
          video={video}
          onDelete={() => deleteMutation.mutate(video.video_id)}
        />
      ))}
    </div>
  )
}
```

## Network Optimizations

### 1. HTTP/2 Server Push

Enable HTTP/2 in production:

```python
# Use uvicorn with HTTP/2 support
uvicorn src.main:app --host 0.0.0.0 --port 8000 --http h2
```

### 2. Compression

Enable gzip compression:

```python
# backend/src/main.py
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

### 3. CDN for Static Assets

Serve HLS segments from CDN:

```typescript
// frontend/src/config.ts
const CDN_URL = process.env.VITE_CDN_URL || 'http://localhost:8000'

export function getProxyUrl(videoId: string): string {
  return `${CDN_URL}/proxy/${videoId}/master.m3u8`
}
```

## Performance Metrics

### Target Benchmarks

| Metric | Target | Current |
|--------|--------|---------|
| API response time (list videos) | < 200ms | TBD |
| API response time (upload) | < 5s (10MB) | TBD |
| Proxy rendering (1080p, 60s) | < 30s | TBD |
| Clip extraction (10s) | < 3s | TBD |
| Frontend initial load | < 2s | TBD |
| Time to Interactive (TTI) | < 3s | TBD |

### Monitoring Tools

1. **Backend**: FastAPI middleware for request timing
2. **Frontend**: Lighthouse CI for performance audits
3. **Database**: pg_stat_statements for query analysis
4. **Network**: Chrome DevTools Network panel

## Implementation Priority

1. **High**: Database indexing, Celery task queue
2. **Medium**: Code splitting, React Query
3. **Low**: Virtual scrolling, CDN setup

## Next Steps

1. Add Celery for background tasks
2. Implement chunked uploads
3. Add Redis caching layer
4. Set up performance monitoring
5. Run Lighthouse audits
6. Optimize database queries with indexes

## References

- [FastAPI Performance](https://fastapi.tiangolo.com/deployment/performance/)
- [React Performance](https://react.dev/learn/render-and-commit)
- [FFmpeg Optimization](https://trac.ffmpeg.org/wiki/Encode/H.264)
