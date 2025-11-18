# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Repository Purpose**: 영상 Proxy 렌더링 및 서브클립 추출 플랫폼
**Version**: 3.0.0 | **Updated**: 2025-01-18
**Stage**: Phase 0 (Planning) → Ready for Phase 0.5 (Task Generation)

---

## 프로젝트 개요 (Project Overview)

원본 영상을 **Proxy로 렌더링**하고, **타임코드 구간을 미리보기**한 후, **원본 품질의 서브클립을 다운로드**하는 브라우저 기반 영상 처리 플랫폼.

### 핵심 기능 (Only 3 Functions)

1. **영상 Proxy 렌더링**
   - 원본 고해상도 영상 → HLS(m3u8) 포맷 자동 변환
   - 브라우저에서 즉시 재생 가능

2. **Proxy 기반 구간 미리보기**
   - Proxy로 빠른 탐색
   - In/Out 타임코드 지정
   - 지정 구간만 반복 재생

3. **원본 품질 서브클립 다운로드**
   - 원본에서 정확한 구간 추출 (ffmpeg, 재인코딩 없음)
   - 즉시 다운로드

**핵심 원칙**: "프리미어 열기 전에, 웹에서 정확한 구간 확인하고 바로 다운로드"

---

## 기술 스택 (Tech Stack)

| 영역         | 기술                      | 용도                         |
| ---------- | ----------------------- | -------------------------- |
| **영상 처리** | **ffmpeg**              | Proxy 변환, 서브클립 추출          |
| **스토리지**  | **NAS**                 | 원본/프록시/클립 저장              |
| **백엔드**   | **FastAPI (Python)**    | REST API, ffmpeg 작업 큐 관리   |
| **프론트엔드** | **React + Ant Design**   | UI/UX, 타임라인 편집기            |
| **영상 재생** | **HLS (m3u8) + hls.js** | 브라우저 프록시 스트리밍             |
| **데이터베이스** | **PostgreSQL**          | 영상/클립 메타데이터 (videos, clips) |

---

## 시스템 아키텍처

```
[원본 영상 업로드]
        ↓
   NAS (Original)
        ↓
   ffmpeg Proxy 렌더링
   (HLS 변환)
        ↓
   NAS (Proxy)
        ↓
   React UI
   - HLS 재생
   - In/Out 타임코드 지정
   - Proxy로 구간 미리보기
        ↓
   FastAPI 백엔드
   (ffmpeg 작업 큐)
        ↓
   원본에서 서브클립 추출
   (코덱 복사, 무손실)
        ↓
   NAS (Clips)
        ↓
   다운로드 제공
```

---

## 데이터 모델 (Database Schema)

### `videos` (영상 메타데이터)

```sql
CREATE TABLE videos (
  video_id UUID PRIMARY KEY,
  filename VARCHAR(255),
  original_path TEXT,
  proxy_path TEXT,
  proxy_status VARCHAR(20), -- pending | processing | completed | failed
  duration_sec FLOAT,
  fps INT,
  created_at TIMESTAMP
);
```

### `clips` (서브클립 메타데이터)

```sql
CREATE TABLE clips (
  clip_id UUID PRIMARY KEY,
  video_id UUID REFERENCES videos(video_id),
  start_sec FLOAT,
  end_sec FLOAT,
  padding_sec FLOAT,
  file_path TEXT,
  file_size_mb FLOAT,
  created_at TIMESTAMP
);
```

---

## 개발 Phase 구조

### Phase 0: PRD 완료 ✅
- `docs/prd.md` 존재

### Phase 0.5: Task List 생성 (다음 단계)

Claude Code에게 요청:
```
"docs/prd.md 읽고 Task List 작성해줘"
```

예상 Task 구조:
- **Task 0.0**: Setup (feature branch, 환경 설정)
- **Task 1.0**: 백엔드 기본 구조 (FastAPI, PostgreSQL, NAS)
- **Task 2.0**: Proxy 렌더링 파이프라인 (ffmpeg HLS)
- **Task 3.0**: 서브클립 추출 API (ffmpeg copy)
- **Task 4.0**: React UI 기본 구조
- **Task 5.0**: 영상 업로드 UI
- **Task 6.0**: Video Player (HLS, hls.js)
- **Task 7.0**: Timeline Editor (In/Out 마커)
- **Task 8.0**: 구간 미리보기 기능
- **Task 9.0**: 서브클립 다운로드 플로우
- **Task 10.0**: 테스트 & 배포

### Phase 1-2: 표준 개발 사이클
전역 CLAUDE.md의 Phase 0-6 워크플로우 따름.

---

## 디렉토리 구조 (예상)

```
man_subclip/
├── docs/
│   └── prd.md                    # PRD v3.0
│
├── backend/
│   ├── src/
│   │   ├── api/                  # FastAPI routes
│   │   │   ├── videos.py         # 업로드, 목록, Proxy 생성
│   │   │   └── clips.py          # 서브클립 추출, 다운로드
│   │   ├── services/
│   │   │   ├── ffmpeg/           # 🔥 핵심
│   │   │   │   ├── proxy.py      # HLS 변환
│   │   │   │   ├── clip.py       # 서브클립 추출
│   │   │   │   └── progress.py   # 진행률 추적
│   │   │   └── storage.py        # NAS 파일 관리
│   │   ├── models/               # SQLAlchemy
│   │   │   ├── video.py
│   │   │   └── clip.py
│   │   ├── tasks.py              # 비동기 작업 큐
│   │   └── main.py
│   ├── tests/
│   │   ├── test_proxy.py         # 🔥 Proxy 변환 테스트
│   │   ├── test_clip.py          # 🔥 서브클립 추출 테스트
│   │   └── test_timecode.py      # 타임코드 계산
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── VideoUploader/    # 🔥 드래그앤드롭
│   │   │   ├── VideoPlayer/      # 🔥 HLS 플레이어
│   │   │   ├── TimelineEditor/   # 🔥 In/Out 편집기
│   │   │   ├── PreviewSection/   # 🔥 구간 미리보기
│   │   │   └── ClipExportPanel/  # 🔥 다운로드
│   │   ├── pages/
│   │   │   ├── Upload.tsx
│   │   │   ├── Library.tsx
│   │   │   ├── Player.tsx        # 🔥 핵심 페이지
│   │   │   └── Clips.tsx
│   │   └── App.tsx
│   └── package.json
│
├── CLAUDE.md                     # 이 파일
└── README.md
```

**우선순위**: 🔥 = 모든 기능이 핵심 (추가/제거 없음)

---

## 주요 기능 명세

### 1. Proxy 렌더링 (ffmpeg HLS)

**ffmpeg 명령어**:
```bash
ffmpeg -i /nas/original/{video_id}.mp4 \
  -vf scale=1280:720 \
  -c:v libx264 -preset fast -crf 23 \
  -c:a aac -b:a 128k \
  -hls_time 10 -hls_list_size 0 \
  -f hls /nas/proxy/{video_id}/master.m3u8
```

**출력**:
- HLS 포맷 (m3u8 + ts 세그먼트)
- 브라우저에서 hls.js로 즉시 재생

---

### 2. 구간 미리보기 (Proxy 기반)

**UI 플로우**:
1. HLS Proxy 재생
2. Timeline에서 In/Out 드래그
3. 타임코드 수동 입력 (00:05:23.500)
4. "구간 미리보기" 버튼 클릭
5. In ~ Out 구간만 반복 재생
6. 만족할 때까지 조정

**패딩 옵션**:
- None (구간만)
- 3초 (자동 앞뒤 3초 추가)
- 커스텀 (사용자 지정)

---

### 3. 서브클립 다운로드 (원본 기준)

**ffmpeg 명령어**:
```bash
ffmpeg -ss {start_sec} -to {end_sec} \
  -i /nas/original/{video_id}.mp4 \
  -c copy \
  -avoid_negative_ts make_zero \
  /nas/clips/{clip_id}.mp4
```

**특징**:
- 원본 품질 유지 (코덱 복사, 재인코딩 없음)
- 프레임 단위 정확도
- 빠른 처리 (10초 이내, 5분 영상 기준)

---

## API 엔드포인트

### 영상 관리
```
POST   /api/videos/upload          # 영상 업로드
GET    /api/videos                 # 영상 목록
GET    /api/videos/{video_id}      # 영상 상세
DELETE /api/videos/{video_id}      # 영상 삭제
```

### Proxy 처리
```
POST   /api/videos/{video_id}/proxy        # Proxy 생성 시작
GET    /api/videos/{video_id}/proxy/status # Proxy 상태 조회
```

### 서브클립 처리
```
POST   /api/clips/create                   # 서브클립 추출
GET    /api/clips/{clip_id}                # 클립 정보
GET    /api/clips/{clip_id}/download       # 다운로드
DELETE /api/clips/{clip_id}                # 삭제
```

---

## 개발 컨벤션

### Python (백엔드)

**가상환경**:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
```

**개발 서버**:
```bash
cd backend
uvicorn src.main:app --reload --port 8000
```

**테스트**:
```bash
pytest backend/tests/ -v --cov=backend/src
```

### React (프론트엔드)

**패키지 설치**:
```bash
cd frontend
npm install
```

**개발 서버**:
```bash
npm run dev
```

**테스트**:
```bash
npm test
npm run test:e2e  # Playwright E2E
```

### 커밋 메시지
```
type: 설명 (vX.Y.Z) [PRD-XXXX]

types:
- feat: 새 기능
- fix: 버그 수정
- test: 테스트

예시:
feat: Add HLS proxy rendering (v0.1.0) [PRD-0001]
feat: Implement timeline editor (v0.2.0) [PRD-0001]
feat: Add subclip extraction (v0.3.0) [PRD-0001]
```

---

## 테스트 전략

### 1:1 Test Pairing (Mandatory)

**백엔드**:
- `src/services/ffmpeg/proxy.py` → `tests/test_proxy.py`
- `src/services/ffmpeg/clip.py` → `tests/test_clip.py`

**프론트엔드**:
- `src/components/VideoPlayer/Player.tsx` → `Player.test.tsx`
- `src/components/TimelineEditor/Editor.tsx` → `Editor.test.tsx`

### E2E 테스트 (Playwright)

**핵심 시나리오**:
1. 영상 업로드 → Proxy 변환 완료
2. 플레이어 재생 → In/Out 지정 → 구간 미리보기
3. 서브클립 다운로드 → 파일 확인

```bash
npx playwright test
```

---

## 환경 변수 설정

**`.env.example`**:
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/video_archive

# NAS Storage
NAS_ORIGINAL_PATH=/mnt/nas/original
NAS_PROXY_PATH=/mnt/nas/proxy
NAS_CLIPS_PATH=/mnt/nas/clips

# ffmpeg
FFMPEG_PATH=/usr/bin/ffmpeg
FFMPEG_THREADS=4
FFMPEG_PRESET=fast
FFMPEG_CRF=23

# 작업 큐
TASK_QUEUE=fastapi  # or celery
CELERY_BROKER_URL=redis://localhost:6379/0  # Celery 사용 시
```

**`.env`** (실제 값, git 제외):
```bash
DATABASE_URL=postgresql://prod_user:prod_pass@prod_db:5432/video_archive
NAS_ORIGINAL_PATH=/production/nas/original
...
```

---

## 보안 체크리스트

### 필수 조치

**1. ffmpeg 인젝션 방지**:
```python
# ✅ 안전한 코드
import subprocess
import os

def validate_timecode(sec: float, max_duration: float) -> float:
    if not 0 <= sec <= max_duration:
        raise ValueError("Invalid timecode")
    return sec

start_sec = validate_timecode(request.in_sec, video.duration_sec)
video_path = os.path.abspath(f"/nas/original/{video.video_id}.mp4")
if not video_path.startswith("/nas/original/"):
    raise ValueError("Invalid path")

subprocess.run([
    "ffmpeg",
    "-ss", str(start_sec),
    "-to", str(end_sec),
    "-i", video_path,
    "-c", "copy",
    output_path
], check=True)
```

**2. 파일 검증**:
- 확장자: MP4, MOV, MXF만 허용
- 파일 크기: 최대 10GB
- 타임코드 범위: 0 ~ video_duration

**3. API 보안**:
- Rate limiting (업로드: 10회/시간)
- CORS 설정
- 다운로드 URL 만료 (1시간)

---

## 성능 목표

| 항목               | 목표                         |
| ---------------- | -------------------------- |
| Proxy 변환 속도      | 원본 duration의 0.5배 이내      |
| 서브클립 추출 속도      | 10초 이내 (5분 영상 기준)          |
| HLS 재생 버퍼링      | 2초 이내 시작                   |
| 동시 처리 작업        | 최대 5개 (Proxy 변환 + 클립 추출)   |
| 스토리지 정리 (Proxy)  | 30일 후 자동 삭제                |
| 스토리지 정리 (Clips) | 7일 후 자동 삭제                 |

---

## 사용자 플로우 (User Flow)

```
1. 영상 업로드
   → 드래그앤드롭
   → 자동 Proxy 변환 시작

2. Proxy 변환 대기
   → 진행률 표시
   → 완료 시 라이브러리 이동

3. 영상 재생
   → 라이브러리에서 선택
   → HLS Proxy 자동 재생

4. 구간 지정 & 미리보기
   → Timeline에서 In/Out 드래그
   → "구간 미리보기" 클릭
   → In ~ Out 반복 재생
   → 만족할 때까지 조정

5. 서브클립 다운로드
   → 패딩 옵션 선택
   → "서브클립 다운로드" 클릭
   → 완료 시 자동 다운로드
```

---

## 다음 단계 (Next Steps)

1. **Phase 0.5 시작**: Claude Code에게 Task List 생성 요청
   ```
   "docs/prd.md 읽고 Task List 작성해줘"
   ```

2. **Phase 1 준비**:
   - FastAPI 프로젝트 구조 생성
   - PostgreSQL 스키마 설계
   - React 프로젝트 초기화

3. **개발 환경 구축**:
   - PostgreSQL Docker 컨테이너
   - NAS 마운트 설정
   - ffmpeg 설치 확인

---

## 참고 문서

- **PRD**: `docs/prd.md` (핵심 요구사항)
- **전역 워크플로우**: 상위 디렉토리 `../CLAUDE.md` (Phase 0-6 프로세스)
- **ffmpeg 문서**: https://ffmpeg.org/documentation.html
- **HLS.js 문서**: https://github.com/video-dev/hls.js/
- **FastAPI 문서**: https://fastapi.tiangolo.com/
- **Ant Design**: https://ant.design/

---

**Note**: 이 프로젝트는 오로지 3가지 기능만 구현합니다:
1. Proxy 렌더링
2. Proxy 기반 구간 미리보기
3. 원본 품질 서브클립 다운로드

부가 기능(검색, LLM, 메타데이터 등)은 없습니다. 단순하고 명확하게 유지합니다.
