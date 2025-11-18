# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Repository**: Video Proxy & Subclip Platform (man_subclip)
**Version**: 1.0.0
**Tech Stack**: FastAPI (Python) + React (TypeScript) + PostgreSQL + ffmpeg

---

## Project Overview

A browser-based video processing platform that:
1. **Renders HLS proxy** from high-resolution originals (720p, H.264, m3u8 format)
2. **Previews segments** using proxy with In/Out timecode markers
3. **Extracts subclips** from originals at full quality (codec copy, lossless)

**Core Principle**: "Preview with proxy, download from original - all in browser, no Premiere required"

---

## Architecture

```
┌─────────────┐
│  React UI   │  Vite + Ant Design + video.js
└──────┬──────┘
       │ HTTP/REST
┌──────▼──────┐
│  FastAPI    │  Python 3.11 + SQLAlchemy
└──────┬──────┘
       │
   ┌───┴───┬─────────┬──────────┐
   │       │         │          │
┌──▼───┐ ┌▼──────┐ ┌▼─────┐  ┌─▼──────┐
│ NAS  │ │ffmpeg │ │ DB   │  │ Celery │
│ /nas │ │ HLS   │ │ PG   │  │(future)│
└──────┘ └───────┘ └──────┘  └────────┘
```

### Directory Structure

```
man_subclip/
├── backend/
│   ├── src/
│   │   ├── api/              # FastAPI routes
│   │   │   ├── videos.py     # Upload, list, proxy
│   │   │   └── clips.py      # Subclip extraction
│   │   ├── models/           # SQLAlchemy models
│   │   │   ├── video.py      # Video metadata
│   │   │   └── clip.py       # Clip metadata
│   │   ├── services/         # Core business logic
│   │   │   ├── ffmpeg/
│   │   │   │   ├── proxy.py  # HLS conversion
│   │   │   │   └── subclip.py# Lossless extraction
│   │   │   └── storage.py    # NAS file management
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── tasks/            # Background tasks
│   │   ├── utils/            # Timecode, logging
│   │   ├── config.py         # Settings
│   │   ├── database.py       # DB connection
│   │   └── main.py           # FastAPI app
│   ├── tests/
│   │   ├── api/              # API endpoint tests
│   │   ├── services/         # Service layer tests
│   │   ├── integration/      # Full workflow tests
│   │   └── utils/            # Utility tests
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── VideoCard.tsx # Library grid item
│   │   ├── pages/
│   │   │   ├── HomePage.tsx       # Landing
│   │   │   ├── UploadPage.tsx     # Drag-n-drop upload
│   │   │   ├── VideoLibraryPage.tsx # Grid view
│   │   │   └── VideoPlayerPage.tsx  # Player + editor
│   │   ├── api/
│   │   │   └── client.ts     # Axios setup
│   │   ├── types/
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── docs/
│   ├── prd.md                # Product requirements
│   ├── E2E_TEST_GUIDE.md     # Playwright guide
│   ├── MONITORING.md         # Logging/metrics
│   └── PERFORMANCE_OPTIMIZATION.md
│
├── RUN_LOCALLY.md            # Development setup
├── DOCKER_QUICKSTART.md      # Docker setup
└── docker-compose.yml
```

---

## Common Commands

### Backend Development

```bash
cd man_subclip/backend

# Setup (one-time)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run development server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/services/test_proxy.py -v

# Run specific test
pytest tests/api/test_videos.py::test_upload_video -v
```

**Test Markers:**
```bash
pytest -v -m unit          # Unit tests only
pytest -v -m integration   # Integration tests only
pytest -v -m slow          # Long-running tests
```

### Frontend Development

```bash
cd man_subclip/frontend

# Setup (one-time)
npm install

# Run development server
npm run dev                # Usually http://localhost:5173

# Run tests
npm test                   # Vitest watch mode
npm run test:coverage      # With coverage report

# Lint
npm run lint

# Build for production
npm run build
npm run preview            # Preview production build
```

### Docker Development

```bash
cd man_subclip

# Start all services (backend + frontend + postgres)
docker-compose up -d --build

# View logs
docker-compose logs -f
docker-compose logs -f backend    # Backend only
docker-compose logs -f frontend   # Frontend only

# Stop services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v

# Rebuild single service
docker-compose up -d --build backend
```

**Access Points:**
- Frontend: http://localhost (port 80)
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432

---

## Key Technical Details

### Database Schema

**videos table:**
```sql
CREATE TABLE videos (
  video_id UUID PRIMARY KEY,
  filename VARCHAR(255),
  original_path TEXT,           -- /nas/originals/{video_id}.mp4
  proxy_path TEXT,              -- /nas/proxy/{video_id}/master.m3u8
  proxy_status VARCHAR(20),     -- pending|processing|completed|failed
  duration_sec FLOAT,
  fps INT,
  width INT,
  height INT,
  file_size_mb FLOAT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

**clips table:**
```sql
CREATE TABLE clips (
  clip_id UUID PRIMARY KEY,
  video_id UUID REFERENCES videos(video_id),
  start_sec FLOAT,              -- Actual start (with padding applied)
  end_sec FLOAT,                -- Actual end (with padding applied)
  padding_sec FLOAT,            -- User-specified padding
  file_path TEXT,               -- /nas/clips/{clip_id}.mp4
  file_size_mb FLOAT,
  duration_sec FLOAT,
  created_at TIMESTAMP
);
```

### ffmpeg Commands

**Proxy Rendering (HLS):**
```bash
ffmpeg -i /nas/originals/{video_id}.mp4 \
  -vf "scale=1280:720:force_original_aspect_ratio=decrease" \
  -c:v libx264 -preset fast -crf 23 \
  -c:a aac -b:a 128k \
  -hls_time 10 -hls_list_size 0 \
  -f hls /nas/proxy/{video_id}/master.m3u8
```

**Subclip Extraction (lossless):**
```bash
ffmpeg -ss {start_sec} -to {end_sec} \
  -i /nas/originals/{video_id}.mp4 \
  -c copy \
  -avoid_negative_ts make_zero \
  -movflags +faststart \
  /nas/clips/{clip_id}.mp4
```

### API Endpoints

**Videos:**
- `POST /videos/upload` - Upload original video
- `GET /videos` - List all videos
- `GET /videos/{video_id}` - Get video details
- `POST /videos/{video_id}/proxy/start` - Start HLS conversion
- `GET /videos/{video_id}/proxy/status` - Check conversion status
- `DELETE /videos/{video_id}` - Delete video

**Clips:**
- `POST /clips` - Extract subclip (body: `{video_id, start_sec, end_sec, padding_sec}`)
- `GET /clips/{clip_id}` - Get clip details
- `GET /clips/{clip_id}/download` - Download clip file
- `DELETE /clips/{clip_id}` - Delete clip

### Environment Variables

**Backend** (`backend/.env`):
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/video_platform
# Or for local dev:
DATABASE_URL=sqlite:///./video_platform.db

# Storage paths
NAS_ORIGINALS_PATH=/nas/originals  # Or ./nas/originals for local
NAS_PROXY_PATH=/nas/proxy
NAS_CLIPS_PATH=/nas/clips

# CORS
ALLOWED_ORIGINS=http://localhost:5173

# Optional
FFMPEG_PATH=/usr/bin/ffmpeg
FFMPEG_THREADS=4
```

**Frontend** (`frontend/.env`):
```bash
VITE_API_BASE_URL=http://localhost:8000
```

---

## Development Workflow

### 1. Starting from Scratch

```bash
# Backend
cd man_subclip/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
mkdir -p nas/originals nas/proxy nas/clips
# Create backend/.env with DATABASE_URL=sqlite:///./video_platform.db
uvicorn src.main:app --reload --port 8000

# Frontend (new terminal)
cd man_subclip/frontend
npm install
# Create frontend/.env with VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

### 2. Adding a New Feature

**Example: Add video metadata extraction**

1. **Backend implementation:**
   ```bash
   # Create service
   touch backend/src/services/video_metadata.py

   # Create test
   touch backend/tests/services/test_video_metadata.py

   # Implement logic in video_metadata.py
   # Write tests in test_video_metadata.py

   # Run tests
   pytest backend/tests/services/test_video_metadata.py -v
   ```

2. **Frontend integration:**
   ```bash
   # Add component
   touch frontend/src/components/VideoMetadata.tsx

   # Add test
   touch frontend/src/components/__tests__/VideoMetadata.test.tsx

   # Run tests
   npm test -- VideoMetadata
   ```

### 3. Running Tests

**Backend:**
```bash
# All tests
pytest backend/tests/ -v

# Specific module
pytest backend/tests/services/ -v

# Single test
pytest backend/tests/api/test_videos.py::test_upload_video -v

# With coverage
pytest backend/tests/ --cov=backend/src --cov-report=html
open htmlcov/index.html
```

**Frontend:**
```bash
# Watch mode
npm test

# Run once
npm test -- --run

# Coverage
npm run test:coverage
```

### 4. Debugging

**Backend (FastAPI):**
```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use VS Code debugger with launch.json:
{
  "name": "FastAPI",
  "type": "python",
  "request": "launch",
  "module": "uvicorn",
  "args": ["src.main:app", "--reload"],
  "cwd": "${workspaceFolder}/man_subclip/backend"
}
```

**Frontend (React):**
```tsx
// Use browser DevTools or add console logs
console.log('VideoCard props:', props);

// Or React DevTools extension
```

---

## Testing Strategy

### Backend Tests (pytest)

**Location:** `backend/tests/`

**Structure:**
- `api/` - Endpoint integration tests
- `services/` - Business logic unit tests
- `integration/` - Full workflow tests
- `utils/` - Utility function tests

**Fixtures:** Defined in `conftest.py`
```python
@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.fixture
def sample_video():
    return Video(
        video_id=uuid4(),
        filename="test.mp4",
        ...
    )
```

### Frontend Tests (Vitest + React Testing Library)

**Location:** `frontend/src/**/__tests__/`

**Conventions:**
- Component tests: `ComponentName.test.tsx`
- Hook tests: `useHook.test.ts`
- Integration tests: `workflow.test.tsx`

**Example:**
```tsx
import { render, screen } from '@testing-library/react';
import VideoCard from '../VideoCard';

test('renders video card with filename', () => {
  render(<VideoCard video={mockVideo} />);
  expect(screen.getByText('test.mp4')).toBeInTheDocument();
});
```

### E2E Tests (Future: Playwright)

See `docs/E2E_TEST_GUIDE.md` for detailed setup.

---

## Security Considerations

### Input Validation

**Timecode validation:**
```python
def validate_timecode(sec: float, max_duration: float) -> float:
    if not 0 <= sec <= max_duration:
        raise ValueError(f"Timecode {sec} out of range [0, {max_duration}]")
    return sec
```

**File path validation:**
```python
import os

video_path = os.path.abspath(f"/nas/originals/{video_id}.mp4")
if not video_path.startswith("/nas/originals/"):
    raise ValueError("Invalid path traversal attempt")
```

**File upload limits:**
- Max file size: 10GB (configurable)
- Allowed extensions: `.mp4`, `.mov`, `.mxf`
- Rate limiting: 10 uploads/hour per IP

### ffmpeg Command Injection Prevention

**Always use subprocess with argument list:**
```python
# ✅ SAFE
subprocess.run([
    "ffmpeg",
    "-i", video_path,
    "-ss", str(start_sec),
    "-to", str(end_sec),
    ...
], check=True)

# ❌ DANGEROUS - Never use shell=True with user input
subprocess.run(f"ffmpeg -i {user_input}", shell=True)  # NO!
```

---

## Performance Targets

| Metric | Target |
|--------|--------|
| Proxy rendering | 0.5x realtime (5min video → 2.5min) |
| Subclip extraction | <10s for 5min segment |
| HLS playback start | <2s buffering |
| API response time | <200ms (avg) |
| Concurrent jobs | 5 max (proxy + clip) |

---

## Troubleshooting

### "ffmpeg not found"

**Solution:**
```bash
# Mac
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows
choco install ffmpeg
# Or download from https://www.gyan.dev/ffmpeg/builds/
```

### "Database connection failed"

**Check:**
1. PostgreSQL running: `docker-compose ps` or `sudo systemctl status postgresql`
2. Credentials in `backend/.env` match database
3. Database exists: `psql -U postgres -l`

**Quick fix (SQLite):**
```bash
# Change backend/.env to:
DATABASE_URL=sqlite:///./video_platform.db
```

### "CORS error"

**Ensure backend/.env has:**
```bash
ALLOWED_ORIGINS=http://localhost:5173  # Match frontend dev server port
```

### "Port already in use"

```bash
# Find process using port 8000
lsof -ti:8000   # Mac/Linux
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 <PID>   # Mac/Linux
taskkill /PID <PID> /F  # Windows
```

---

## Additional Documentation

- **PRD:** `man_subclip/docs/prd.md` - Full product requirements
- **Local Setup:** `man_subclip/RUN_LOCALLY.md` - Detailed dev environment guide
- **Docker Setup:** `man_subclip/DOCKER_QUICKSTART.md` - Container deployment
- **E2E Testing:** `man_subclip/docs/E2E_TEST_GUIDE.md` - Playwright guide
- **Monitoring:** `man_subclip/docs/MONITORING.md` - Logging & metrics
- **Performance:** `man_subclip/docs/PERFORMANCE_OPTIMIZATION.md`

---

## Git Workflow

**Branch:** `claude/init-project-019gn3vSpaS4NnEBa59m4gkm`

**Commit format:**
```
type: description

Types: feat, fix, docs, test, refactor, perf, chore

Examples:
feat: Add HLS proxy rendering
fix: Correct ffmpeg scale filter syntax
test: Add integration tests for clip extraction
```

**Before committing:**
```bash
# Backend
cd backend
pytest tests/ -v

# Frontend
cd frontend
npm run lint
npm test -- --run

# Both
git add .
git commit -m "feat: Add feature description"
git push origin claude/init-project-019gn3vSpaS4NnEBa59m4gkm
```

---

**Last Updated:** 2025-01-18
