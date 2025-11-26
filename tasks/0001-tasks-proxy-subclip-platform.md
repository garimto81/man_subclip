# Task List: 영상 Proxy & 서브클립 추출 플랫폼 (PRD-0001)

**Generated**: 2025-01-18
**PRD**: docs/prd.md v3.0
**Total Duration**: 4-5 weeks

---

## Task 0.0: Setup ✅ (2 hours)

- [ ] Create feature branch: `feature/PRD-0001-proxy-subclip-platform`
- [ ] Update CLAUDE.md with project context
- [ ] Initialize directory structure (backend, frontend, docs)
- [ ] Setup .gitignore (.env, node_modules, __pycache__, etc)

**Acceptance Criteria**:
- ✅ Feature branch created
- ✅ CLAUDE.md updated with project-specific info
- ✅ Directory structure matches CLAUDE.md specification

---

## Task 1.0: Phase 1 - 백엔드 기본 구조 (Week 1)

### Task 1.1: FastAPI 프로젝트 초기화 (4 hours)
- [ ] Create FastAPI project structure (`backend/src/`)
- [ ] Setup virtual environment (Python 3.11+)
- [ ] Create `requirements.txt` with dependencies:
  - fastapi, uvicorn[standard]
  - sqlalchemy, psycopg2-binary
  - python-multipart
  - ffmpeg-python
  - pytest, pytest-cov (testing)
- [ ] Create `backend/src/main.py` with basic FastAPI app
- [ ] Test: Run `uvicorn src.main:app --reload`

**Acceptance Criteria**:
- ✅ FastAPI app runs on http://localhost:8000
- ✅ `/docs` endpoint shows Swagger UI
- ✅ All dependencies installed

### Task 1.2: PostgreSQL 스키마 설계 및 연동 (3 hours)
- [ ] Create Docker Compose for PostgreSQL
- [ ] Create SQLAlchemy models:
  - `backend/src/models/video.py` (videos 테이블)
  - `backend/src/models/clip.py` (clips 테이블)
- [ ] Create database initialization script
- [ ] Setup Alembic for migrations
- [ ] Create test: `backend/tests/test_models.py`

**Schema**:
```sql
videos: video_id, filename, original_path, proxy_path,
        proxy_status, duration_sec, fps, created_at
clips:  clip_id, video_id, start_sec, end_sec, padding_sec,
        file_path, file_size_mb, created_at
```

**Acceptance Criteria**:
- ✅ PostgreSQL running in Docker
- ✅ Tables created with correct schema
- ✅ SQLAlchemy models working
- ✅ Test coverage: 80%+

### Task 1.3: NAS 스토리지 연동 및 파일 관리 (3 hours)
- [ ] Create `backend/src/services/storage.py`
- [ ] Implement NAS path configuration:
  - `/nas/original/` (원본)
  - `/nas/proxy/` (프록시)
  - `/nas/clips/` (서브클립)
- [ ] Implement file operations:
  - `save_uploaded_file()`
  - `get_file_path()`
  - `delete_file()`
- [ ] Create test: `backend/tests/test_storage.py`

**Acceptance Criteria**:
- ✅ NAS paths configured in .env
- ✅ File operations working
- ✅ Test coverage: 80%+

---

## Task 2.0: Phase 1 - 영상 업로드 API (Week 1)

### Task 2.1: 파일 업로드 엔드포인트 구현 (4 hours)
- [ ] Create `backend/src/api/videos.py`
- [ ] Implement `POST /api/videos/upload`:
  - Accept multipart/form-data
  - Validate file extension (MP4, MOV, MXF)
  - Validate file size (max 10GB)
  - Generate UUID for video_id
  - Save to NAS `/nas/original/{video_id}.{ext}`
  - Extract video metadata (duration, fps, resolution) with ffmpeg
  - Save to PostgreSQL with proxy_status='pending'
- [ ] Create test: `backend/tests/api/test_videos.py`

**Acceptance Criteria**:
- ✅ Upload endpoint working
- ✅ File validation working
- ✅ Metadata extraction working
- ✅ Test coverage: 80%+

### Task 2.2: 영상 목록 및 조회 API 구현 (2 hours)
- [ ] Implement `GET /api/videos` (목록)
- [ ] Implement `GET /api/videos/{video_id}` (상세)
- [ ] Implement `DELETE /api/videos/{video_id}` (삭제)
- [ ] Create test: Add to `backend/tests/api/test_videos.py`

**Acceptance Criteria**:
- ✅ All CRUD endpoints working
- ✅ Test coverage: 80%+

---

## Task 3.0: Phase 1 - Proxy 렌더링 파이프라인 (Week 1-2)

### Task 3.1: ffmpeg HLS 변환 로직 구현 (6 hours)
- [ ] Create `backend/src/services/ffmpeg/proxy.py`
- [ ] Implement `convert_to_hls()`:
  - Input: video_id, original_path
  - ffmpeg command:
    ```bash
    ffmpeg -i /nas/original/{video_id}.mp4 \
      -vf scale=1280:720 \
      -c:v libx264 -preset fast -crf 23 \
      -c:a aac -b:a 128k \
      -hls_time 10 -hls_list_size 0 \
      -f hls /nas/proxy/{video_id}/master.m3u8
    ```
  - Parse ffmpeg progress output
  - Return proxy_path
- [ ] Create test: `backend/tests/services/ffmpeg/test_proxy.py`

**Acceptance Criteria**:
- ✅ HLS conversion working
- ✅ m3u8 + ts segments generated
- ✅ Test with sample video (5분 영상)
- ✅ Test coverage: 80%+

### Task 3.2: 비동기 작업 큐 구현 (4 hours)
- [ ] Create `backend/src/tasks.py`
- [ ] Implement BackgroundTasks for proxy conversion:
  - `async def proxy_conversion_task(video_id)`
  - Update proxy_status in DB (pending → processing → completed/failed)
  - Handle errors and retry logic (최대 3회)
- [ ] Create test: `backend/tests/test_tasks.py`

**Acceptance Criteria**:
- ✅ Background task working
- ✅ DB status updates working
- ✅ Retry logic working
- ✅ Test coverage: 80%+

### Task 3.3: Proxy 상태 조회 API 구현 (2 hours)
- [ ] Implement `POST /api/videos/{video_id}/proxy` (Proxy 생성 시작)
- [ ] Implement `GET /api/videos/{video_id}/proxy/status` (상태 조회)
- [ ] Return: proxy_status, progress_percent, estimated_time_remaining
- [ ] Create test: Add to `backend/tests/api/test_videos.py`

**Acceptance Criteria**:
- ✅ Proxy creation endpoint triggers background task
- ✅ Status endpoint returns correct state
- ✅ Test coverage: 80%+

---

## Task 4.0: Phase 1 - 서브클립 추출 API (Week 2)

### Task 4.1: 타임코드 계산 로직 구현 (3 hours)
- [ ] Create `backend/src/services/ffmpeg/timecode.py`
- [ ] Implement `calculate_timecode()`:
  ```python
  def calculate_timecode(
      in_sec: float,
      out_sec: float,
      padding_sec: float,
      video_duration: float
  ) -> dict:
      start_sec = max(0, in_sec - padding_sec)
      end_sec = min(video_duration, out_sec + padding_sec)
      duration_sec = end_sec - start_sec
      return {
          "start_sec": start_sec,
          "end_sec": end_sec,
          "duration_sec": duration_sec
      }
  ```
- [ ] Implement input validation:
  - 0 <= in_sec < out_sec <= video_duration
  - padding_sec >= 0
- [ ] Create test: `backend/tests/services/ffmpeg/test_timecode.py`

**Acceptance Criteria**:
- ✅ Timecode calculation correct
- ✅ Validation working
- ✅ Test coverage: 100%

### Task 4.2: ffmpeg 서브클립 추출 로직 구현 (4 hours)
- [ ] Create `backend/src/services/ffmpeg/clip.py`
- [ ] Implement `extract_clip()`:
  - Input: video_id, start_sec, end_sec
  - ffmpeg command:
    ```bash
    ffmpeg -ss {start_sec} -to {end_sec} \
      -i /nas/original/{video_id}.mp4 \
      -c copy \
      -avoid_negative_ts make_zero \
      -movflags +faststart \
      /nas/clips/{clip_id}.mp4
    ```
  - Return: clip_path, file_size_mb
- [ ] Create test: `backend/tests/services/ffmpeg/test_clip.py`

**Acceptance Criteria**:
- ✅ Clip extraction working
- ✅ No re-encoding (원본 품질 유지)
- ✅ Fast start enabled
- ✅ Test coverage: 80%+

### Task 4.3: 서브클립 추출 API 구현 (3 hours)
- [ ] Create `backend/src/api/clips.py`
- [ ] Implement `POST /api/clips/create`:
  - Input: video_id, in_sec, out_sec, padding_sec
  - Validate timecode
  - Generate clip_id
  - Extract clip (background task)
  - Save to DB
  - Return: clip_id, status
- [ ] Implement `GET /api/clips/{clip_id}` (상태 조회)
- [ ] Implement `GET /api/clips/{clip_id}/download` (다운로드)
- [ ] Implement `DELETE /api/clips/{clip_id}` (삭제)
- [ ] Create test: `backend/tests/api/test_clips.py`

**Acceptance Criteria**:
- ✅ All endpoints working
- ✅ Background task integration working
- ✅ Download working
- ✅ Test coverage: 80%+

---

## Task 5.0: Phase 1 - 백엔드 통합 테스트 (Week 2)

### Task 5.1: E2E 백엔드 테스트 작성 (4 hours)
- [ ] Create `backend/tests/integration/test_e2e.py`
- [ ] Test full workflow:
  1. Upload video
  2. Trigger proxy conversion
  3. Wait for completion
  4. Extract subclip
  5. Download subclip
- [ ] Test error cases:
  - Invalid file format
  - Invalid timecode
  - File not found

**Acceptance Criteria**:
- ✅ E2E test passing
- ✅ All error cases covered
- ✅ Test coverage: Overall 80%+

---

## Task 6.0: Phase 2 - 프론트엔드 기본 구조 (Week 3)

### Task 6.1: React 프로젝트 초기화 (3 hours)
- [ ] Create React + TypeScript project (`frontend/`)
- [ ] Setup Ant Design 5
- [ ] Setup React Router
- [ ] Setup Axios API client
- [ ] Setup Zustand for state management
- [ ] Create basic layout with Ant Design components
- [ ] Create test: `frontend/src/App.test.tsx`

**Acceptance Criteria**:
- ✅ React app runs on http://localhost:3000
- ✅ Ant Design components working
- ✅ Routing working

### Task 6.2: API 클라이언트 구현 (2 hours)
- [ ] Create `frontend/src/services/api.ts`
- [ ] Implement API methods:
  - `uploadVideo(file): Promise<Video>`
  - `getVideos(): Promise<Video[]>`
  - `getVideo(id): Promise<Video>`
  - `createProxy(id): Promise<void>`
  - `getProxyStatus(id): Promise<ProxyStatus>`
  - `createClip(params): Promise<Clip>`
  - `getClip(id): Promise<Clip>`
  - `downloadClip(id): Promise<Blob>`
- [ ] Create test: `frontend/src/services/api.test.ts`

**Acceptance Criteria**:
- ✅ All API methods working
- ✅ Error handling working
- ✅ Test coverage: 80%+

---

## Task 7.0: Phase 2 - 영상 업로드 페이지 (Week 3)

### Task 7.1: VideoUploader 컴포넌트 구현 (4 hours)
- [ ] Create `frontend/src/components/VideoUploader/VideoUploader.tsx`
- [ ] Implement drag-and-drop upload (Ant Design Upload)
- [ ] Show upload progress
- [ ] Show proxy conversion status
- [ ] Handle errors (file size, format, network)
- [ ] Create test: `VideoUploader.test.tsx`

**Acceptance Criteria**:
- ✅ Drag-and-drop working
- ✅ Upload progress showing
- ✅ Proxy conversion auto-starts
- ✅ Test coverage: 80%+

### Task 7.2: 영상 업로드 페이지 구현 (2 hours)
- [ ] Create `frontend/src/pages/Upload.tsx`
- [ ] Integrate VideoUploader component
- [ ] Add instructions
- [ ] Redirect to library on completion
- [ ] Create test: `Upload.test.tsx`

**Acceptance Criteria**:
- ✅ Upload page working
- ✅ Navigation working
- ✅ Test coverage: 80%+

---

## Task 8.0: Phase 2 - 영상 라이브러리 페이지 (Week 3)

### Task 8.1: VideoCard 컴포넌트 구현 (3 hours)
- [ ] Create `frontend/src/components/VideoCard/VideoCard.tsx`
- [ ] Show thumbnail, filename, duration
- [ ] Show proxy status badge (완료/변환 중/실패)
- [ ] Click to navigate to player
- [ ] Create test: `VideoCard.test.tsx`

**Acceptance Criteria**:
- ✅ Card displays all info
- ✅ Status badge working
- ✅ Navigation working
- ✅ Test coverage: 80%+

### Task 8.2: 영상 라이브러리 페이지 구현 (3 hours)
- [ ] Create `frontend/src/pages/Library.tsx`
- [ ] Display video grid (Ant Design Grid)
- [ ] Implement search/filter (filename, date)
- [ ] Implement pagination
- [ ] Handle empty state
- [ ] Create test: `Library.test.tsx`

**Acceptance Criteria**:
- ✅ Library page working
- ✅ Search/filter working
- ✅ Pagination working
- ✅ Test coverage: 80%+

---

## Task 9.0: Phase 2 - 영상 플레이어 (Week 3-4) 🔥 핵심

### Task 9.1: VideoPlayer 컴포넌트 구현 (6 hours)
- [ ] Create `frontend/src/components/VideoPlayer/VideoPlayer.tsx`
- [ ] Integrate hls.js for HLS playback
- [ ] Implement playback controls:
  - Play/Pause
  - Seek bar
  - Volume control
  - Playback speed (0.5x, 1x, 1.5x, 2x)
- [ ] Display current timecode (00:00:00.000)
- [ ] Handle errors (video not found, proxy not ready)
- [ ] Create test: `VideoPlayer.test.tsx`

**Acceptance Criteria**:
- ✅ HLS playback working
- ✅ All controls working
- ✅ Timecode display accurate
- ✅ Test coverage: 80%+

### Task 9.2: TimelineEditor 컴포넌트 구현 (6 hours)
- [ ] Create `frontend/src/components/TimelineEditor/TimelineEditor.tsx`
- [ ] Implement timeline with In/Out markers:
  - Draggable In marker (blue)
  - Draggable Out marker (red)
  - Visual duration bar between markers
- [ ] Implement TimecodeInput:
  - Format: HH:MM:SS.mmm
  - Validation
  - Sync with markers
- [ ] Calculate and display duration
- [ ] Create test: `TimelineEditor.test.tsx`

**Acceptance Criteria**:
- ✅ Markers draggable and accurate
- ✅ Timecode input working
- ✅ Duration calculation correct
- ✅ Test coverage: 80%+

### Task 9.3: PreviewSection 컴포넌트 구현 (4 hours)
- [ ] Create `frontend/src/components/PreviewSection/PreviewSection.tsx`
- [ ] Implement "구간 미리보기" button
- [ ] Loop playback between In/Out markers
- [ ] Allow real-time In/Out adjustment during preview
- [ ] Stop button to exit preview mode
- [ ] Create test: `PreviewSection.test.tsx`

**Acceptance Criteria**:
- ✅ Preview loop working
- ✅ Real-time adjustment working
- ✅ Test coverage: 80%+

### Task 9.4: ClipExportPanel 컴포넌트 구현 (4 hours)
- [ ] Create `frontend/src/components/ClipExportPanel/ClipExportPanel.tsx`
- [ ] Implement padding options:
  - None (0초)
  - 3초 (default)
  - 커스텀 (input field)
- [ ] Show calculated start/end with padding
- [ ] Show estimated file size
- [ ] "서브클립 다운로드" button
- [ ] Create test: `ClipExportPanel.test.tsx`

**Acceptance Criteria**:
- ✅ Padding options working
- ✅ Calculations accurate
- ✅ Export button working
- ✅ Test coverage: 80%+

### Task 9.5: ExportProgressModal 컴포넌트 구현 (3 hours)
- [ ] Create `frontend/src/components/ExportProgressModal/ExportProgressModal.tsx`
- [ ] Show extraction progress:
  - Status: 대기 중 / 처리 중 / 완료
  - Progress bar (0-100%)
  - Estimated time remaining
- [ ] On completion:
  - Show clip metadata (duration, file size)
  - Download button
  - "새 클립 추출" button
- [ ] Create test: `ExportProgressModal.test.tsx`

**Acceptance Criteria**:
- ✅ Progress modal working
- ✅ Download working
- ✅ Test coverage: 80%+

### Task 9.6: Player 페이지 통합 (4 hours)
- [ ] Create `frontend/src/pages/Player.tsx`
- [ ] Integrate all components:
  - VideoPlayer (top)
  - TimelineEditor (middle)
  - PreviewSection (middle-right)
  - ClipExportPanel (bottom)
- [ ] Implement state management (Zustand)
- [ ] Handle video loading and errors
- [ ] Create test: `Player.test.tsx`

**Acceptance Criteria**:
- ✅ All components integrated
- ✅ State management working
- ✅ Full workflow working (재생 → In/Out 지정 → 미리보기 → 다운로드)
- ✅ Test coverage: 80%+

---

## Task 10.0: Phase 2 - E2E 테스트 (Week 4)

### Task 10.1: Playwright E2E 테스트 작성 (6 hours)
- [ ] Setup Playwright
- [ ] Create `frontend/tests/e2e/upload-to-download.spec.ts`
- [ ] Test scenarios:
  1. **Upload flow**:
     - Upload video
     - Wait for proxy conversion
     - Navigate to library
  2. **Playback flow**:
     - Select video from library
     - Player loads and plays HLS
     - Seek to different positions
  3. **Clip extraction flow**:
     - Set In/Out markers
     - Preview clip
     - Adjust markers
     - Export clip
     - Download clip
     - Verify file downloaded

**Acceptance Criteria**:
- ✅ All E2E tests passing
- ✅ Tests run in CI/CD
- ✅ Cross-browser testing (Chrome, Firefox)

---

## Task 11.0: Phase 3 - 성능 최적화 (Week 5)

### Task 11.1: ffmpeg 병렬 처리 구현 (4 hours)
- [ ] Implement task queue with priority
- [ ] Allow multiple ffmpeg processes (max 5 concurrent)
- [ ] Implement queue monitoring API
- [ ] Create test: Add to `backend/tests/test_tasks.py`

**Acceptance Criteria**:
- ✅ Multiple videos converting simultaneously
- ✅ Queue management working
- ✅ Test coverage: 80%+

### Task 11.2: 파일 업로드 청크 처리 (3 hours)
- [ ] Implement chunked upload (Ant Design Upload)
- [ ] Add resume capability
- [ ] Optimize chunk size (10MB)
- [ ] Create test: Add to `frontend/tests/upload.test.tsx`

**Acceptance Criteria**:
- ✅ Large files (10GB) upload reliably
- ✅ Resume working after network interruption
- ✅ Test coverage: 80%+

### Task 11.3: 프론트엔드 번들 최적화 (2 hours)
- [ ] Implement code splitting
- [ ] Lazy load routes
- [ ] Optimize bundle size (target: <500KB initial)
- [ ] Add loading states

**Acceptance Criteria**:
- ✅ Initial load < 2 seconds
- ✅ Lighthouse score > 90

---

## Task 12.0: Phase 3 - 모니터링 & 로깅 (Week 5)

### Task 12.1: 백엔드 로깅 시스템 구현 (3 hours)
- [ ] Setup structured logging (Python logging)
- [ ] Log all ffmpeg operations
- [ ] Log API requests/responses
- [ ] Log errors with stack traces
- [ ] Create log rotation policy

**Acceptance Criteria**:
- ✅ Logs written to file and stdout
- ✅ Log levels configured (DEBUG/INFO/ERROR)
- ✅ Rotation working (daily, max 30 days)

### Task 12.2: 스토리지 모니터링 구현 (2 hours)
- [ ] Implement storage usage tracking
- [ ] Create cleanup job:
  - Delete proxy files > 30 days old
  - Delete clip files > 7 days old
- [ ] Create admin API: `GET /api/admin/storage`
- [ ] Create test: `backend/tests/admin/test_storage.py`

**Acceptance Criteria**:
- ✅ Storage usage tracked
- ✅ Cleanup job working
- ✅ Admin API working

---

## Task 13.0: Phase 3 - 배포 준비 (Week 5)

### Task 13.1: Docker 컨테이너화 (4 hours)
- [ ] Create `backend/Dockerfile`
- [ ] Create `frontend/Dockerfile`
- [ ] Create `docker-compose.yml`:
  - PostgreSQL
  - Backend (FastAPI)
  - Frontend (Nginx)
- [ ] Test local deployment

**Acceptance Criteria**:
- ✅ All services run in Docker
- ✅ docker-compose up working
- ✅ Production-ready configuration

### Task 13.2: CI/CD 파이프라인 구축 (4 hours)
- [ ] Create `.github/workflows/test.yml`:
  - Backend tests
  - Frontend tests
  - E2E tests
- [ ] Create `.github/workflows/deploy.yml`:
  - Build Docker images
  - Push to registry
  - Deploy to server (optional)

**Acceptance Criteria**:
- ✅ Tests run on every push
- ✅ CI/CD pipeline working

### Task 13.3: 프로덕션 환경 설정 (3 hours)
- [ ] Create `.env.production` template
- [ ] Setup HTTPS (optional)
- [ ] Configure CORS for production domain
- [ ] Setup rate limiting
- [ ] Create deployment documentation

**Acceptance Criteria**:
- ✅ Production config ready
- ✅ Security measures in place
- ✅ Documentation complete

---

## 📊 Task Summary

| Phase | Tasks | Duration | Priority |
|-------|-------|----------|----------|
| Setup | Task 0.0 | 2 hours | P0 |
| 백엔드 기본 | Task 1.0-2.0 | Week 1 | P0 |
| Proxy 렌더링 | Task 3.0 | Week 1-2 | P0 |
| 서브클립 추출 | Task 4.0-5.0 | Week 2 | P0 |
| 프론트 기본 | Task 6.0-8.0 | Week 3 | P0 |
| 영상 플레이어 | Task 9.0 | Week 3-4 | P0 |
| E2E 테스트 | Task 10.0 | Week 4 | P0 |
| 최적화 | Task 11.0 | Week 5 | P1 |
| 모니터링 | Task 12.0 | Week 5 | P1 |
| 배포 | Task 13.0 | Week 5 | P1 |

**Total**: 13 Parent Tasks, 40+ Sub-Tasks

---

## 🎯 핵심 마일스톤

1. **Week 1 완료**: 백엔드 기본 구조 + Proxy 렌더링 API 동작
2. **Week 2 완료**: 서브클립 추출 API 완성, 백엔드 E2E 테스트 통과
3. **Week 3 완료**: 프론트엔드 기본 페이지 완성 (Upload, Library)
4. **Week 4 완료**: 플레이어 페이지 완성, E2E 테스트 통과 ✅ MVP 완성
5. **Week 5 완료**: 최적화, 모니터링, 배포 준비 완료

---

## ✅ Definition of Done (DoD)

Each task must meet:
- [ ] Code written and reviewed
- [ ] 1:1 test file created (mandatory)
- [ ] Tests passing (80%+ coverage)
- [ ] Documentation updated (if needed)
- [ ] No critical bugs
- [ ] Committed with proper message: `type: description (vX.Y.Z) [PRD-0001]`

---

**Next Action**: Start Task 0.0 (Setup)
