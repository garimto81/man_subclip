# CLAUDE.md

Claude Code (claude.ai/code) 사용 시 이 저장소 작업을 위한 가이드입니다.

**저장소**: 영상 Proxy & 서브클립 플랫폼
**목적**: HLS 스트리밍 기반 브라우저 영상 Proxy 렌더링 및 서브클립 추출
**현재 단계**: 🚧 Phase 1 구현 중 (v4.0.0) - 70% 완료
**상태**: ✅ 백엔드 100% | ⚠️ 프론트엔드 40% (핵심 UI 누락)

---

## 🌐 GGProduction 영상 처리 생태계

**이 프로젝트는 3개 연결된 프로젝트 중 마지막(2번)입니다:**

```
[0. qwen_hand_analysis]   AI 포커 분석 (Phase 6, 80%)
   - Gemini 2.5 Flash API로 핸드 히스토리 자동 추출
   - Firestore 저장 (타임스탬프 포함)
   - GCS 영상 관리
   - 파일 URI 캐싱 (48h TTL, 95% 시간 단축)
        ↓ (Firestore: 핸드 데이터 + 타임스탬프)
[1. archive-mam]          검색 & 아카이빙 (PoC 30%)
   - AI 자연어 검색 (Vertex AI Vector Search)
   - 하이브리드 검색 (BM25 + Vector + RRF)
   - Perplexica UI (Next.js)
   - 타임코드 정보 제공 (<100ms 응답)
        ↓ (검색 결과: video_id + start/end 타임코드)
[2. man_subclip] ⭐       영상 편집 플랫폼 (현재 70%)
   - HLS Proxy 렌더링 (ffmpeg)
   - 타임코드 자동 로드 (archive-mam 연동 준비 중)
   - 원본 품질 서브클립 추출 (코덱 복사)
        ↓ (최종 서브클립 MP4)
    [편집자/학습자에게 전달]
```

### 데이터 흐름 상세

**0️⃣ qwen_hand_analysis** (시작점):
- **입력**: WSOP 원본 영상 (GCS)
- **처리**: Gemini 2.5 Flash API로 카드/액션 인식
- **출력**: Firestore (핸드 데이터 + **타임스탬프** ⭐)
  ```
  hands/{hand_id}
    - timestamps: {start: 7234.5, end: 7398.2}  ← man_subclip이 사용
    - pot_bb, board_cards, winner
  ```

**1️⃣ archive-mam** (중간 - 검색):
- **입력**: Firestore 핸드 데이터
- **처리**: Vertex AI 임베딩 → Vector Search 인덱싱
- **출력**: 검색 결과 (hand_id, video_id, **타임코드**)
  ```json
  {
    "video_id": "wsop_2025_day5_table3",
    "timestamps": {"start": 7234.5, "end": 7398.2}  ← man_subclip으로 전달
  }
  ```

**2️⃣ man_subclip** (최종 - 현재 프로젝트):
- **입력**: archive-mam의 타임코드 또는 수동 지정
- **처리**:
  1. HLS Proxy 렌더링 (브라우저 재생)
  2. 타임코드 자동 로드 & 미리보기
  3. ffmpeg 코덱 복사로 원본 추출
- **출력**: 서브클립 MP4 (원본 품질)

### 기술 스택 비교

| 영역 | qwen_hand_analysis | archive-mam | man_subclip (현재) |
|------|-------------------|-------------|---------------------|
| **AI/ML** | Gemini 2.5 Flash | Vertex AI Embedding | - |
| **백엔드** | FastAPI | FastAPI | FastAPI |
| **프론트엔드** | (계획: Next.js) | Perplexica (Next.js) | React 18 + Ant Design |
| **데이터베이스** | Firestore | BigQuery + Vector Search | SQLite/PostgreSQL |
| **스토리지** | GCS | GCS + BigQuery | GCS + NAS (로컬) |
| **영상 처리** | Gemini API | - | ffmpeg (HLS + 코덱 복사) |

### 통합 워크플로우 예시

**시나리오**: "Junglemann의 hero call 학습하기"

1. **qwen_hand_analysis** (9분):
   - WSOP 영상 업로드 → Gemini 분석
   - Hand #42 감지: timestamps {start: 7234.5, end: 7398.2}
   - Firestore 저장 완료

2. **archive-mam** (<1초):
   - 검색: "junglemann hero call ace high"
   - 결과: Hand #42 (스코어 0.94, 타임코드 포함)
   - "서브클립 생성" 클릭 → man_subclip으로 타임코드 전달

3. **man_subclip** (20초):
   - 타임코드 자동 로드: In 02:00:34.5 / Out 02:03:18.2
   - Proxy로 구간 미리보기 & 확인
   - 원본 품질 서브클립 다운로드

**총 소요 시간**: ~10분 (전통 방식: 5시간+) → **95% 시간 단축** 🎉

### 프로젝트 위치

- `../qwen_hand_analysis/` - Phase 6 (80%) - Gemini API 분석기
- `../archive-mam/` - PoC (30%) - Vertex AI 검색 시스템
- `./` (현재) - 개발 중 (70%) - 영상 편집 플랫폼

### 비용 분석 (1시간 영상 기준)

| 단계 | 도구 | 비용 | 소요 시간 |
|------|------|------|----------|
| AI 핸드 분석 | qwen | $0.09 (Gemini) | 3분 |
| 검색 인덱싱 | archive | $0.05 (Vertex AI) | 1분 |
| Proxy + 서브클립 | man_subclip | 무료 (로컬/GCS) | 30분 |

**총 비용**: ~$0.14/영상 | **10만 핸드 아카이브**: ~$150/월

---

## 빠른 참조

### 핵심 기능 (3개만)
1. **HLS Proxy 렌더링** - 원본 영상을 브라우저 재생 가능한 HLS 포맷으로 변환
2. **타임코드 미리보기** - Proxy 영상으로 특정 구간 미리보기
3. **원본 품질 서브클립 다운로드** - 원본에서 서브클립 추출 (무손실 코덱 복사)

### 기술 스택
- **백엔드**: FastAPI + SQLite (개발) / PostgreSQL (프로덕션) + SQLAlchemy
- **프론트엔드**: React 18 + TypeScript + Ant Design + Video.js (HLS 플레이어)
- **영상 처리**: ffmpeg (HLS 변환, 코덱 복사 추출)
- **스토리지**: NAS 기반 (original/proxy/clips)

---

## 개발 명령어

### 백엔드 (FastAPI + Python 3.11+)

```bash
# 설정
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 개발 서버 실행
uvicorn src.main:app --reload --port 8000

# 테스트 실행
pytest tests/ -v --cov=src --cov-report=term-missing

# 특정 테스트 실행
pytest tests/services/test_proxy.py -v

# 데이터베이스 마이그레이션
alembic upgrade head
alembic revision --autogenerate -m "설명"
```

### 프론트엔드 (React + TypeScript)

```bash
# 설정
cd frontend
npm install

# 개발 서버 실행
npm run dev  # http://localhost:5173 에서 실행

# 빌드
npm run build

# 테스트
npm test              # 단위 테스트 (Vitest)
npm run test:coverage # 커버리지 포함
npm run test:ui       # 인터랙티브 UI

# 린트
npm run lint
```

### Docker (전체 스택)

```bash
# 모든 서비스 빌드 및 실행
docker-compose up --build

# 백그라운드 실행
docker-compose up -d

# 로그 보기
docker-compose logs -f

# 중지
docker-compose down

# 볼륨 정리
docker-compose down -v
```

---

## 아키텍처 개요

### 디렉토리 구조

```
backend/
├── src/
│   ├── api/              # FastAPI 라우트 핸들러
│   │   ├── videos.py     # 업로드, 목록, Proxy 생성 (✅ 완료)
│   │   └── clips.py      # 서브클립 추출, 다운로드 (✅ 완료)
│   ├── models/           # SQLAlchemy ORM 모델
│   │   ├── video.py      # 영상 메타데이터 (✅ 완료)
│   │   └── clip.py       # 클립 메타데이터 (✅ 완료)
│   ├── schemas/          # Pydantic 요청/응답 스키마 (✅ 완료)
│   ├── services/
│   │   ├── ffmpeg/
│   │   │   ├── proxy.py      # HLS 변환 로직 (✅ 완료)
│   │   │   ├── subclip.py    # 코덱 복사 추출 (✅ 완료)
│   │   │   └── progress.py   # ffmpeg 진행률 추적 (✅ 완료)
│   │   └── storage.py        # NAS 파일 작업 (✅ 완료)
│   ├── utils/            # 유틸리티 (✅ 완료)
│   │   └── timecode.py   # 타임코드 계산
│   ├── config.py         # 환경 설정 (✅ 완료)
│   ├── database.py       # SQLAlchemy 설정 (✅ 완료)
│   └── main.py           # FastAPI 앱 진입점 (✅ 완료)
├── tests/                # src/와 1:1 대응 (✅ 완료)
└── scripts/              # 유틸리티 스크립트

frontend/
├── src/
│   ├── api/              # Axios API 클라이언트 (✅ 완료)
│   ├── components/       # React 컴포넌트 (⚠️ 기본만)
│   │   └── VideoCard.tsx (✅ 완료)
│   ├── pages/
│   │   ├── VideoLibraryPage.tsx  # 영상 목록 (✅ 완료)
│   │   ├── UploadPage.tsx        # 드래그앤드롭 업로드 (✅ 완료)
│   │   └── VideoPlayerPage.tsx   # ❌ 누락: HLS 플레이어, Timeline 편집기, 미리보기 루프
│   ├── types/            # TypeScript 정의 (✅ 완료)
│   └── App.tsx           # 라우팅 포함 메인 앱 (✅ 완료)
└── tests/                # Vitest 테스트 (⚠️ 최소한)
```

**프론트엔드 상태**: 40% 완료
- ✅ 기본 UI 구조, 폼, 네비게이션
- ❌ **누락 (60%)**: Video.js HLS 플레이어, Timeline 슬라이더, 타임코드 포맷, 미리보기 루프

### 데이터 플로우

```
업로드 → NAS (원본) → ffmpeg HLS 변환 → NAS (Proxy)
                                ↓
                        브라우저에서 Proxy 재생
                                ↓
                    사용자가 In/Out 타임코드 선택
                                ↓
                        구간 미리보기 (Proxy)
                                ↓
                    원본에서 추출 (코덱 복사)
                                ↓
                        서브클립 다운로드 (무손실)
```

### 데이터베이스 스키마

**videos 테이블**:
- `video_id` (UUID, PK)
- `filename`, `original_path`, `proxy_path`
- `proxy_status` (pending|processing|completed|failed)
- `duration_sec`, `fps`, `width`, `height`
- 타임스탬프

**clips 테이블**:
- `clip_id` (UUID, PK)
- `video_id` (FK → videos)
- `start_sec`, `end_sec`, `padding_sec`
- `file_path`, `file_size_mb`, `duration_sec`
- 타임스탬프

---

## 핵심 구현 상세

### 1. ffmpeg HLS Proxy 변환

**위치**: `backend/src/services/ffmpeg/proxy.py:32-122`

**핵심 사항**:
- `ffmpeg-python` 라이브러리 사용 (선언적 API)
- Scale 필터: "1280:720"을 별도의 w/h 파라미터로 분리
- 출력: HLS 플레이리스트 (m3u8) + 세그먼트 (ts 파일)
- 에러 처리: 실패 시 Proxy 디렉토리 정리

**흔한 문제**: Scale 필터 문법
```python
# ❌ 잘못된 방법: scale='1280:720' (필터 에러 발생)
# ✅ 올바른 방법:
if ':' in scale:
    width, height = scale.split(':')
    video = stream.video.filter('scale', w=width, h=height)
```

### 2. 서브클립 추출 (코덱 복사)

**위치**: `backend/src/services/ffmpeg/subclip.py:34-113`

**핵심 사항**:
- 빠른 탐색을 위해 `-ss`와 `-to`를 `-i` **앞에** 배치
- 무손실 추출을 위한 `-c copy` (재인코딩 없음)
- 타임스탬프 문제 해결을 위한 `-avoid_negative_ts make_zero`
- 웹 최적화를 위한 `-movflags +faststart`

**보안**: 항상 타임코드 검증
```python
if start_sec < 0 or end_sec <= start_sec:
    raise ValueError("Invalid timecode range")
```

### 3. 비디오 플레이어 통합

**위치**: `frontend/src/pages/VideoPlayerPage.tsx`

**핵심 사항**:
- Video.js 사용 (hls.js 직접 사용 X)
- Proxy 경로: `/api/videos/{video_id}/proxy/master.m3u8`
- In/Out 마커를 위한 타임코드 상태 관리
- 서브클립 추출을 위한 패딩 계산

---

## 테스트 가이드

### 1:1 테스트 페어링 (필수)

모든 소스 파일은 반드시 대응하는 테스트가 있어야 합니다:
- `src/services/ffmpeg/proxy.py` → `tests/services/test_proxy.py`
- `src/utils/timecode.py` → `tests/utils/test_timecode.py`
- 프론트엔드: `VideoCard.tsx` → `__tests__/VideoCard.test.tsx`

### 테스트 실행

**백엔드**:
```bash
# 커버리지 포함 전체 테스트
pytest -v --cov=src --cov-report=term-missing

# 특정 모듈
pytest tests/services/test_proxy.py -v -s

# 통합 테스트만
pytest tests/integration/ -v
```

**프론트엔드**:
```bash
# 단위 테스트
npm test

# Watch 모드
npm test -- --watch

# 커버리지
npm run test:coverage
```

### 주요 테스트 시나리오

1. **Proxy 변환**: HLS 출력 구조, 에러 처리 테스트
2. **타임코드 검증**: 엣지 케이스 (음수, 범위 초과)
3. **API 통합**: 업로드 → Proxy → 추출 → 다운로드 플로우

---

## 설정 & 환경

### 필수 환경 변수

```bash
# 백엔드 (.env)
DATABASE_URL=sqlite:///./video_platform.db  # 개발: SQLite, 프로덕션: PostgreSQL
NAS_ORIGINAL_PATH=D:/AI/claude01/man_subclip/storage/original
NAS_PROXY_PATH=D:/AI/claude01/man_subclip/storage/proxy
NAS_CLIPS_PATH=D:/AI/claude01/man_subclip/storage/clips
FFMPEG_PATH=ffmpeg
FFMPEG_THREADS=4
FFMPEG_PRESET=fast
FFMPEG_CRF=23
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
TASK_QUEUE=fastapi

# 프론트엔드 (.env)
VITE_API_BASE_URL=http://localhost:8000
```

### Pydantic을 통한 설정 로딩

모든 설정과 기본값은 `backend/src/config.py` 참고.

---

## 보안 고려사항

### 1. ffmpeg 명령 인젝션 방지

**항상 입력값 검증**:
```python
# ✅ 안전한 방법
import os
video_path = os.path.abspath(f"/nas/original/{video_id}.mp4")
if not video_path.startswith("/nas/original/"):
    raise ValueError("Invalid path")

# 타임코드 검증
if not 0 <= start_sec <= video.duration_sec:
    raise ValueError("Invalid timecode")
```

### 2. 파일 업로드 검증

- 확장자: MP4, MOV, MXF만 허용
- 크기 제한: 최대 10GB (FastAPI에서 설정)
- UUID 기반 파일명 (사용자 제어 경로 없음)

### 3. API 보안

- CORS: `main.py`에서 설정 (허용된 출처만)
- Rate limiting: 아직 구현 안 됨 (TODO)
- 다운로드 URL: 직접 NAS 경로 (프로덕션에서는 서명된 URL 고려)

---

## 일반 개발 작업

### 새 API 엔드포인트 추가

1. `src/schemas/`에 Pydantic 스키마 정의
2. `src/api/`에 라우트 핸들러 추가
3. `src/main.py`에 라우터 포함
4. `tests/api/`에 테스트 작성

### ffmpeg 처리 수정

1. `src/services/ffmpeg/`에서 서비스 업데이트
2. 실제 영상 파일로 테스트 (작은 테스트 클립 사용)
3. 에러 처리 및 정리 로직 확인
4. 새 시나리오로 테스트 업데이트

### 데이터베이스 스키마 변경

```bash
# 1. src/models/에서 모델 수정
# 2. 마이그레이션 생성
alembic revision --autogenerate -m "필드 X 추가"

# 3. alembic/versions/에서 마이그레이션 검토
# 4. 마이그레이션 적용
alembic upgrade head
```

### ffmpeg 명령 디버그

상세 출력 활성화:
```python
# proxy.py 또는 subclip.py에서
ffmpeg.run(output, capture_stdout=True, capture_stderr=True)
# 에러 시 stderr 출력하여 전체 ffmpeg 출력 확인
```

---

## 성능 목표

| 항목 | 목표 |
|------|------|
| Proxy 변환 | ≤ 영상 재생시간의 0.5배 |
| 서브클립 추출 | ≤ 10초 (5분 영상 기준) |
| HLS 재생 시작 | ≤ 2초 |
| API 응답 시간 | ≤ 평균 200ms |

---

## 알려진 문제 & TODO

1. **진행률 추적**: 실시간 ffmpeg 진행률 미구현 (`proxy.py:124` 참고)
2. **작업 취소**: 진행 중인 ffmpeg 작업 취소 불가 (`proxy.py:142` 참고)
3. **스토리지 정리**: 오래된 Proxy/클립 자동 삭제 미자동화 (`backend/scripts/storage_cleanup.py`의 수동 스크립트)
4. **Rate Limiting**: API rate limiting 아직 없음
5. **서명된 URL**: 다운로드 URL이 직접 경로 (만료되는 서명된 URL 고려)

---

## 참고 자료

- **PRD**: `tasks/prd.md` - 전체 제품 요구사항 (AI용)
- **전역 워크플로우**: `../CLAUDE.md` - Phase 0-6 개발 프로세스
- **ffmpeg 문서**: https://ffmpeg.org/documentation.html
- **FastAPI**: https://fastapi.tiangolo.com/
- **Video.js**: https://videojs.com/
- **Ant Design**: https://ant.design/

---

## 현재 구현 상태 (v4.0.0)

### 📊 진행 현황

**전체 진행률**: 70% 완료
- ✅ **백엔드**: 100% 완료 (FastAPI + SQLite + ffmpeg 파이프라인)
- ⚠️ **프론트엔드**: 40% 완료 (기본 UI만, 핵심 영상 기능 누락)

### ✅ 완료 항목 (백엔드 - 100%)

#### API 엔드포인트
모든 REST API 엔드포인트 구현 및 테스트 완료:
- 영상: 업로드, 목록, 상세, 삭제, Proxy 생성, Proxy 상태
- 클립: 생성, 상세, 다운로드, 삭제

#### ffmpeg 처리
- **HLS Proxy 변환** (`proxy.py:127줄`) - 완전 구현
  - 올바른 w/h 파라미터 처리로 Scale 필터 구현
  - 진행률 추적 지원
  - 에러 처리 및 정리
- **서브클립 추출** (`subclip.py:103줄`) - 완전 구현
  - 코덱 복사 (무손실)
  - 타임코드 검증
  - 패딩 계산

#### 데이터베이스 & 스토리지
- SQLAlchemy 모델 (videos, clips)
- SQLite (개발) / PostgreSQL (프로덕션) 준비 완료
- NAS 스토리지 구조 생성 완료

### ❌ 누락 항목 (프론트엔드 - 60%)

상세 구현 계획은 **tasks/prd.md Section 13** 참고.

**핵심 누락 기능**:
1. **Video.js HLS 플레이어** (4시간)
   - 현재: 비디오 플레이어 없음
   - 필요: HLS.js 통합된 Video.js
   - 위치: `VideoPlayerPage.tsx`

2. **슬라이더 기반 Timeline 편집기** (6시간)
   - 현재: InputNumber만
   - 필요: In/Out 마커가 있는 Ant Design Slider
   - 위치: `VideoPlayerPage.tsx`

3. **타임코드 포맷** (2시간)
   - 현재: 초 단위만 (323.5)
   - 필요: HH:MM:SS.mmm 포맷 변환
   - 위치: `VideoPlayerPage.tsx`

4. **미리보기 루프** (4시간)
   - 현재: 미리보기 기능 없음
   - 필요: In~Out 반복 재생
   - 위치: `VideoPlayerPage.tsx`

5. **패딩 옵션 UI** (2시간)
   - 현재: InputNumber만
   - 필요: Radio 버튼 (없음/3초/커스텀)
   - 위치: `VideoPlayerPage.tsx`

**남은 프론트엔드 작업**: 18시간 (2-3일)

### 🚫 제거된 Scope Creep (2025-01-18)

다음 파일들은 "Only 3 Functions" PRD 원칙을 위반하여 제거됨:
- ❌ `backend/src/api/search.py` (333줄) - Mixpeek 영상 검색
- ❌ `backend/src/api/preview_v2.py` (227줄) - 중복 미리보기 로직
- ❌ `backend/src/services/transcoder_client.py` (150줄) - GCP Transcoder (불필요)
- ❌ `backend/src/services/search/` - 전체 검색 서비스 디렉토리

**결과**: 코드베이스가 이제 3가지 핵심 기능만 엄격히 준수 (Proxy 렌더링, 타임코드 미리보기, 서브클립 다운로드)

### 🎯 다음 단계 (MVP 완성)

**Phase 1**: 프론트엔드 구현 (2-3일)
```bash
# 1. 의존성 설치
cd frontend
npm install video.js @types/video.js

# 2. 핵심 기능 구현 (todo 리스트 또는 tasks/prd.md Section 13 참고)
# - Video.js HLS 플레이어
# - Slider 기반 Timeline 편집기
# - 타임코드 포맷 변환
# - 미리보기 루프
# - 패딩 옵션 UI

# 3. 워크플로우 테스트
# 업로드 → Proxy 생성 → HLS 재생 → In/Out 선택 → 미리보기 루프 → 다운로드
```

**Phase 2**: E2E 테스트 (4시간)
```bash
cd frontend
npm install -D @playwright/test
npx playwright test
```

**Phase 3**: 배포
- 백엔드: 8000번 포트 (현재 설정됨)
- 프론트엔드: 3000번 포트 (8000으로 Vite 프록시)
- Docker 컨테이너화 (선택사항)

### 📋 현재 할일 목록

이 세션에서 추적 중인 todo 항목:
1. ✅ 구현 상태로 CLAUDE.md 업데이트
2. ✅ v4.0 상태로 PRD 업데이트
3. ✅ 8000번 포트 설정 (vite.config.ts)
4. ✅ Scope creep 파일 제거
5. ⏸️ video.js 의존성 설치
6. ⏸️ Video.js HLS 플레이어 구현 (4시간)
7. ⏸️ Timeline 편집기 구현 (6시간)
8. ⏸️ 타임코드 포맷 구현 (2시간)
9. ⏸️ 미리보기 루프 구현 (4시간)
10. ⏸️ 패딩 옵션 UI 개선 (2시간)
11. ⏸️ E2E 테스트 작성 (4시간)
12. ⏸️ 전체 워크플로우 테스트

---

## 프로젝트 원칙

1. **단순성**: 3가지 핵심 기능만 - scope creep 금지
2. **성능**: 빠른 미리보기를 위한 Proxy 우선, 품질을 위한 코덱 복사
3. **정확성**: 프레임 단위 타임코드 처리
4. **테스트**: 1:1 테스트 페어링 필수
5. **보안**: 모든 입력값 검증, 명령 인젝션 방지
