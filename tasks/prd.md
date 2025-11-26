# 📘 **영상 Proxy & 서브클립 추출 플랫폼 – PRD**

**GG PRODUCTION — Internal Document v4.0**

---

## 0. 시스템 목적 (Mission)

원본 영상을 **Proxy로 렌더링**하고, **타임코드 구간을 미리보기**한 후, **원본 품질의 서브클립을 다운로드**하는 브라우저 기반 영상 처리 플랫폼.

### 🌐 생태계 컨텍스트

**이 프로젝트는 GGProduction 영상 처리 생태계의 최종 단계입니다:**

```
[0. qwen_hand_analysis]   AI 포커 분석
   - Gemini 2.5 Flash API로 핸드 히스토리 자동 추출
   - Firestore에 타임스탬프 저장
        ↓ (핸드 데이터 + 타임스탬프)
[1. archive-mam]          검색 시스템
   - AI 자연어 검색 (Vertex AI Vector Search)
   - 검색 결과에 타임코드 정보 제공
        ↓ (검색 결과: video_id + start/end 타임코드)
[2. man_subclip] ⭐       영상 편집 플랫폼 (현재)
   - 타임코드 자동 로드 (archive-mam 연동)
   - HLS Proxy 렌더링
   - 원본 품질 서브클립 추출
        ↓ (최종 서브클립 MP4)
    [편집자/학습자에게 전달]
```

**통합 워크플로우 예시**:
1. **qwen_hand_analysis**: WSOP 영상 업로드 → Gemini AI 분석 → Hand #42 감지 (timestamps: 7234.5~7398.2초)
2. **archive-mam**: "junglemann hero call" 검색 → Hand #42 발견 (타임코드 포함)
3. **man_subclip**: "서브클립 생성" 클릭 → **타임코드 자동 로드** → 미리보기 → 다운로드

**효율성**: 검색부터 서브클립까지 **10분** (전통 방식: 5시간+) → **95% 시간 단축**

### 핵심 기능 (Only 3 Functions)

1. **영상 Proxy 렌더링**
   - 원본 고해상도 영상 → 브라우저 재생 가능한 저용량 HLS Proxy 자동 생성

2. **Proxy 기반 구간 미리보기**
   - Proxy로 빠른 재생
   - In/Out 타임코드 지정 (수동 or **archive-mam에서 자동 로드**)
   - 지정된 구간만 Proxy로 즉시 미리보기

3. **원본 품질 서브클립 다운로드**
   - 지정된 구간을 원본 영상에서 정확하게 추출
   - 원본 품질 유지 (재인코딩 없음)
   - 즉시 다운로드 가능

---

## 1. 전체 아키텍처

### 1.1 기본 워크플로우 (독립 실행)

```
[사용자 업로드]
        ↓
   원본 영상 (NAS/GCS)
        ↓
   ffmpeg Proxy 렌더링
   → HLS (m3u8)
        ↓
   Proxy 영상 (NAS)
        ↓
   브라우저 재생
   - In/Out 타임코드 지정 (수동)
   - Proxy로 구간 미리보기
        ↓
   서브클립 추출 요청
        ↓
   ffmpeg 원본에서 추출
   (코덱 복사, 무손실)
        ↓
   서브클립 (NAS)
        ↓
   다운로드 제공
```

### 1.2 통합 워크플로우 (archive-mam 연동)

```
[archive-mam 검색 결과]
   - video_id: "wsop_2025_day5_table3"
   - timestamps: {start: 7234.5, end: 7398.2}
        ↓ (타임코드 자동 전달)
[man_subclip 플레이어 페이지]
   - URL: /player/{video_id}?in=7234.5&out=7398.2
   - 타임코드 자동 로드 ✨
        ↓
   HLS Proxy 자동 재생
   - In: 02:00:34.500 (자동 설정)
   - Out: 02:03:18.200 (자동 설정)
        ↓
   사용자 미세 조정 (±5초 등)
        ↓
   "구간 미리보기" 클릭
   → In~Out 반복 재생으로 확인
        ↓
   "서브클립 다운로드" 클릭
        ↓
   원본 품질 서브클립 생성
        ↓
   즉시 다운로드 (junglemann_hero_call_hand42.mp4)
```

---

## 2. 핵심 기술 스택

| 영역         | 기술                    | 용도                       |
| ---------- | --------------------- | ------------------------ |
| **영상 처리** | **ffmpeg**            | Proxy 변환, 서브클립 추출        |
| **스토리지**  | **NAS**               | 원본/프록시/클립 저장            |
| **백엔드**   | **FastAPI (Python)**  | REST API, ffmpeg 작업 큐 관리 |
| **프론트엔드** | **React + Ant Design** | UI/UX, 타임라인 편집기          |
| **영상 재생** | **HLS + hls.js**      | 브라우저 프록시 스트리밍           |
| **데이터베이스** | **PostgreSQL**        | 영상/클립 메타데이터             |

---

## 3. 기능 요구사항 (Core Functionalities)

### 3.1 영상 Proxy 렌더링

#### 목적
원본 고해상도 영상을 브라우저에서 빠르게 재생 가능한 저용량 Proxy로 변환.

#### 프로세스

**입력**:
```
원본 영상 파일 (MP4, MOV, MXF 등)
NAS 경로: /nas/original/{video_id}.mp4
```

**ffmpeg 변환**:
```bash
ffmpeg -i /nas/original/{video_id}.mp4 \
  -vf scale=1280:720 \
  -c:v libx264 -preset fast -crf 23 \
  -c:a aac -b:a 128k \
  -hls_time 10 -hls_list_size 0 \
  -f hls /nas/proxy/{video_id}/master.m3u8
```

**출력**:
```
HLS 포맷 (m3u8 + ts 세그먼트)
NAS 경로: /nas/proxy/{video_id}/master.m3u8
PostgreSQL: video_id, proxy_path, duration_sec 등록
```

#### UI 기능
- 드래그앤드롭 영상 업로드
- 업로드 진행률 표시
- Proxy 변환 진행률 표시
- 변환 완료 시 자동 재생 가능

---

### 3.2 Proxy 기반 구간 미리보기

#### 목적
Proxy 영상으로 빠른 탐색 후, 특정 구간을 미리보기. **archive-mam에서 검색 결과 타임코드를 자동 로드** 가능.

#### 타임코드 입력 방식

**1. 수동 입력** (기본):
- 사용자가 직접 In/Out 타임코드 지정
- 타임라인 슬라이더 드래그 or 직접 입력

**2. 자동 로드** (archive-mam 연동) ✨:
```typescript
// URL 파라미터로 타임코드 전달
// 예시: /player/wsop_2025_day5_table3?in=7234.5&out=7398.2

// 프론트엔드 구현
const searchParams = new URLSearchParams(window.location.search);
const autoIn = parseFloat(searchParams.get('in') || '0');
const autoOut = parseFloat(searchParams.get('out') || '0');

if (autoIn > 0 && autoOut > autoIn) {
  setInPoint(autoIn);   // 7234.5초 → 02:00:34.500
  setOutPoint(autoOut); // 7398.2초 → 02:03:18.200

  // 자동 로드 표시
  message.info('archive-mam 검색 결과에서 타임코드를 자동 로드했습니다.');
}
```

**archive-mam 연동 플로우**:
```
1. archive-mam 검색 페이지
   → "junglemann hero call" 검색
   → Hand #42 결과 (timestamps: 7234.5~7398.2)
   → "서브클립 생성" 버튼 클릭

2. man_subclip으로 리디렉션
   → URL: https://man-subclip.ggprod.net/player/wsop_2025_day5_table3?in=7234.5&out=7398.2
   → 타임코드 자동 로드 ✨
   → In/Out 자동 설정
   → 구간 미리보기 바로 가능

3. 사용자 미세 조정 (선택)
   → ±5초 패딩 추가
   → 구간 확인 후 다운로드
```

#### UI 기능

**Video Player**:
- HLS Proxy 재생 (hls.js)
- 재생 컨트롤 (play/pause, seek, 배속)
- 현재 타임코드 표시 (00:00:00.000)
- **자동 로드 배지** (URL 파라미터 감지 시)

**Timeline Editor**:
- 전체 타임라인 표시
- In/Out 마커 드래그 (슬라이더)
- 타임코드 수동 입력
  ```
  In:  00:05:23.500  (수동 or 자동 로드)
  Out: 00:06:45.200  (수동 or 자동 로드)
  ```
- 구간 duration 계산 표시 (00:01:21.700)

**구간 미리보기**:
- "구간 미리보기" 버튼 클릭
- In ~ Out 구간만 Proxy로 반복 재생
- 미리보기 중 In/Out 실시간 조정 가능

#### 패딩 옵션
- **None**: 지정 구간만
- **3초**: 자동 앞뒤 3초 추가
- **커스텀**: 사용자 지정 (예: 5초)

예시:
```
In:  00:05:23.500
Out: 00:06:45.200
Padding: 3초

계산 결과:
Start: 00:05:20.500 (In - 3초)
End:   00:06:48.200 (Out + 3초)
Duration: 00:01:27.700
```

---

### 3.3 원본 품질 서브클립 다운로드

#### 목적
지정된 구간을 원본 영상에서 정확하게 추출하여 다운로드.

#### 프로세스

**API 요청**:
```json
POST /api/clips/create
{
  "video_id": "abc123",
  "in_sec": 323.5,
  "out_sec": 405.2,
  "padding_sec": 3
}
```

**백엔드 처리**:
1. 타임코드 계산 (패딩 적용)
2. 원본 영상 경로 확인
3. ffmpeg 작업 큐 등록
4. 비동기 추출 실행

**ffmpeg 추출 명령어**:
```bash
ffmpeg -ss {start_sec} -to {end_sec} \
  -i /nas/original/{video_id}.mp4 \
  -c copy \
  -avoid_negative_ts make_zero \
  -movflags +faststart \
  /nas/clips/{clip_id}.mp4
```

**출력**:
```
서브클립 파일: /nas/clips/{clip_id}.mp4
원본 품질 유지 (코덱 복사, 재인코딩 없음)
PostgreSQL: clip_id, video_id, start_sec, end_sec, file_size_mb 등록
```

#### UI 기능

**추출 진행**:
- "서브클립 다운로드" 버튼 클릭
- 추출 진행률 모달 표시
- ffmpeg 작업 상태 표시 (대기 중/처리 중/완료)

**완료 화면**:
- 서브클립 메타데이터
  ```
  Duration: 00:01:27.700
  File Size: 245.8 MB
  Format: MP4 (H.264)
  ```
- 서브클립 미리보기 (Proxy)
- **다운로드 버튼** (원본 품질 파일)
- 공유 URL 복사

---

## 4. 데이터 모델 (PostgreSQL)

### 테이블 구조

#### `videos` (영상 메타데이터)

```sql
CREATE TABLE videos (
  video_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  filename VARCHAR(255) NOT NULL,
  original_path TEXT NOT NULL,
  proxy_path TEXT,
  proxy_status VARCHAR(20) DEFAULT 'pending', -- pending | processing | completed | failed
  duration_sec FLOAT,
  fps INT,
  width INT,
  height INT,
  file_size_mb FLOAT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

#### `clips` (서브클립 메타데이터)

```sql
CREATE TABLE clips (
  clip_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID REFERENCES videos(video_id) ON DELETE CASCADE,
  start_sec FLOAT NOT NULL,
  end_sec FLOAT NOT NULL,
  padding_sec FLOAT DEFAULT 0,
  file_path TEXT NOT NULL,
  file_size_mb FLOAT,
  duration_sec FLOAT,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 5. 기술 구조 상세

### 5.1 ffmpeg 처리 파이프라인

#### Proxy 렌더링 명세

**변환 파라미터**:
- **해상도**: 1280x720 (원본이 작으면 유지)
- **코덱**: H.264 (libx264)
- **인코딩 속도**: fast (빠른 변환)
- **품질**: CRF 23 (적정 품질)
- **오디오**: AAC 128kbps
- **HLS 세그먼트**: 10초

**작업 관리**:
- 비동기 큐: FastAPI BackgroundTasks or Celery
- 진행률 추적: ffmpeg progress 출력 파싱
- 오류 처리: 재시도 로직 (최대 3회)
- 상태 업데이트: PostgreSQL `proxy_status` 필드

#### 서브클립 추출 명세

**추출 파라미터**:
- **코덱**: copy (재인코딩 없음)
- **타임코드**: 정확한 키프레임 탐색 (`-ss` 옵션)
- **타임스탬프**: 정규화 (`-avoid_negative_ts make_zero`)
- **웹 최적화**: Fast start (`-movflags +faststart`)

**타임코드 정확성**:
```python
# 패딩 적용 계산
start_sec = max(0, in_sec - padding_sec)
end_sec = min(video_duration, out_sec + padding_sec)
duration_sec = end_sec - start_sec

# 파일 크기 예측 (원본 비트레이트 기반)
estimated_size_mb = (original_bitrate_mbps * duration_sec) / 8
```

---

### 5.2 NAS 스토리지 구조

```
/nas/
├── original/              # 원본 영상
│   ├── {video_id}.mp4
│   └── {video_id}.mov
│
├── proxy/                 # Proxy (HLS)
│   ├── {video_id}/
│   │   ├── master.m3u8
│   │   ├── segment_000.ts
│   │   ├── segment_001.ts
│   │   └── ...
│   └── ...
│
└── clips/                 # 서브클립
    ├── {clip_id}.mp4
    └── ...
```

**권한 설정**:
- Original: Read/Write (업로드 가능)
- Proxy: Read/Write (자동 생성)
- Clips: Read/Write (자동 생성)

**저장소 정책**:
- Original: 영구 보존
- Proxy: 30일 후 자동 삭제 (재생성 가능)
- Clips: 7일 후 자동 삭제 (재생성 가능)

---

### 5.3 API 엔드포인트

#### 영상 관리

```
POST   /api/videos/upload          # 영상 업로드
GET    /api/videos                 # 영상 목록 조회
GET    /api/videos/{video_id}      # 영상 상세 조회
DELETE /api/videos/{video_id}      # 영상 삭제
```

#### Proxy 처리

```
POST   /api/videos/{video_id}/proxy       # Proxy 생성 시작
GET    /api/videos/{video_id}/proxy/status # Proxy 변환 상태 조회
```

#### 서브클립 처리

```
POST   /api/clips/create                  # 서브클립 추출 요청
GET    /api/clips/{clip_id}               # 서브클립 정보 조회
GET    /api/clips/{clip_id}/download      # 서브클립 다운로드
DELETE /api/clips/{clip_id}               # 서브클립 삭제
GET    /api/videos/{video_id}/clips       # 특정 영상의 서브클립 목록
```

---

### 5.4 프론트엔드 UI 구조

#### 주요 페이지

**1. 영상 업로드 페이지** (`/upload`)
- 드래그앤드롭 업로드 영역
- 업로드 진행률 표시
- Proxy 변환 상태 표시

**2. 영상 라이브러리** (`/library`)
- 영상 목록 (그리드 뷰)
- 썸네일, 제목, duration
- Proxy 상태 배지 (완료/변환 중/실패)
- 검색/필터 (파일명, 날짜)

**3. 영상 플레이어 + 편집기** (`/player/{video_id}`) 🔥 핵심
- **Video Player**: HLS Proxy 재생
- **Timeline Editor**: In/Out 마커, 타임코드 입력
- **Preview Section**: 구간 미리보기
- **Export Panel**: 패딩 옵션, 다운로드 버튼

**4. 클립 관리** (`/clips`)
- 생성된 서브클립 목록
- 다운로드, 삭제 기능

#### 핵심 컴포넌트

```typescript
// 영상 업로드
<VideoUploader />

// 영상 플레이어 (hls.js)
<VideoPlayer videoId={id} />

// 타임라인 편집기
<TimelineEditor
  duration={duration}
  onInChange={setIn}
  onOutChange={setOut}
/>

// 타임코드 입력
<TimecodeInput
  label="In"
  value={inSec}
  onChange={setInSec}
/>

// 구간 미리보기
<PreviewSection
  videoId={videoId}
  inSec={inSec}
  outSec={outSec}
/>

// 서브클립 추출 패널
<ClipExportPanel
  videoId={videoId}
  inSec={inSec}
  outSec={outSec}
  paddingSec={paddingSec}
  onExport={handleExport}
/>

// 추출 진행률 모달
<ExportProgressModal
  clipId={clipId}
  status={status}
/>
```

---

## 6. 사용자 플로우 (User Flow)

```
1. 영상 업로드
   → 드래그앤드롭 or 파일 선택
   → 업로드 진행률 표시
   → 자동 Proxy 변환 시작

2. Proxy 변환 대기
   → 진행률 표시 (0% ~ 100%)
   → 완료 시 자동 라이브러리 이동

3. 영상 선택 & 재생
   → 라이브러리에서 영상 클릭
   → 플레이어 페이지로 이동
   → HLS Proxy 자동 재생

4. 구간 지정 & 미리보기
   → 타임라인에서 In/Out 드래그
   → "구간 미리보기" 클릭
   → In ~ Out 구간만 반복 재생
   → 만족할 때까지 조정

5. 서브클립 다운로드
   → 패딩 옵션 선택 (0초 / 3초 / 커스텀)
   → "서브클립 다운로드" 클릭
   → 추출 진행률 모달 표시
   → 완료 시 자동 다운로드 시작
```

---

## 7. 개발 로드맵

### Phase 1: 백엔드 기본 구조 (Week 1-2)

**1.1 프로젝트 초기화**
- FastAPI 프로젝트 구조
- PostgreSQL 스키마 생성
- NAS 스토리지 연동 테스트

**1.2 영상 업로드 API**
- 파일 업로드 엔드포인트
- 파일 검증 (확장자, 크기)
- NAS 저장 및 DB 등록

**1.3 Proxy 렌더링 파이프라인**
- ffmpeg HLS 변환 로직
- 비동기 작업 큐 (BackgroundTasks)
- 진행률 추적 및 상태 업데이트
- 오류 처리 및 재시도

**1.4 서브클립 추출 API**
- 타임코드 계산 로직 (패딩 포함)
- ffmpeg 서브클립 추출
- 클립 파일 저장 및 DB 등록
- 다운로드 URL 생성

**1.5 테스트**
- 단위 테스트 (타임코드 계산)
- 통합 테스트 (업로드 → Proxy → 클립 추출)

---

### Phase 2: 프론트엔드 UI (Week 3-4)

**2.1 프로젝트 초기화**
- React + TypeScript + Ant Design
- React Router 설정
- Axios API 클라이언트

**2.2 영상 업로드 페이지**
- 드래그앤드롭 컴포넌트
- 업로드 진행률 표시
- Proxy 변환 상태 표시

**2.3 영상 라이브러리 페이지**
- 영상 목록 그리드 뷰
- Proxy 상태 배지
- 영상 클릭 → 플레이어 이동

**2.4 영상 플레이어 + 편집기** 🔥 핵심
- HLS 플레이어 (hls.js 통합)
- 타임라인 슬라이더 (In/Out 마커)
- 타임코드 입력 필드
- 구간 미리보기 기능
- 패딩 옵션 선택
- 서브클립 다운로드 버튼

**2.5 추출 진행 & 완료 모달**
- 추출 진행률 표시
- 완료 시 다운로드 링크
- 클립 메타데이터 표시

**2.6 테스트**
- E2E 테스트 (Playwright)
  - 업로드 플로우
  - 재생 플로우
  - 클립 추출 플로우

---

### Phase 3: 최적화 & 배포 (Week 5)

**3.1 성능 최적화**
- ffmpeg 병렬 처리
- 파일 업로드 청크 처리
- 프론트엔드 번들 최적화

**3.2 모니터링**
- 로그 시스템 (영상 처리 로그)
- 오류 추적 (Sentry)
- 스토리지 사용량 모니터링

**3.3 배포**
- Docker 컨테이너화
- CI/CD 파이프라인 (GitHub Actions)
- 프로덕션 환경 설정

---

## 8. 기술 요구사항

### 백엔드

**필수 패키지**:
```txt
fastapi
uvicorn[standard]
sqlalchemy
psycopg2-binary
python-multipart
ffmpeg-python
```

**Python 버전**: 3.11+

### 프론트엔드

**필수 패키지**:
```json
{
  "react": "^18.0.0",
  "antd": "^5.0.0",
  "hls.js": "^1.5.0",
  "axios": "^1.0.0",
  "zustand": "^4.0.0"
}
```

**Node 버전**: 18+

### 인프라

- **NAS**: 최소 1TB (원본/프록시/클립 저장)
- **PostgreSQL**: 14+
- **ffmpeg**: 5.0+ (libx264, AAC 코덱 필수)
- **Redis**: 7+ (Celery 사용 시)

---

## 9. 성능 목표

| 항목                | 목표                       |
| ----------------- | ------------------------ |
| Proxy 변환 속도       | 원본 duration의 0.5배 이내    |
| 서브클립 추출 속도       | 10초 이내 (5분 영상 기준)        |
| HLS 재생 버퍼링       | 2초 이내 시작                 |
| 파일 업로드 속도        | 10MB/s 이상 (내부망)          |
| 동시 처리 작업         | 최대 5개 (Proxy 변환 + 클립 추출) |
| API 응답 시간        | 평균 200ms 이내              |
| 프론트엔드 초기 로드      | 2초 이내                    |
| 스토리지 자동 정리 (Proxy) | 30일 후 삭제                 |
| 스토리지 자동 정리 (Clips) | 7일 후 삭제                  |

---

## 10. 보안 요구사항

### 필수 보안 조치

**1. 입력 검증**
- 타임코드 범위 검증 (0 ~ video_duration)
- 파일 확장자 검증 (MP4, MOV, MXF만 허용)
- 파일 크기 제한 (최대 10GB)

**2. ffmpeg 인젝션 방지**
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

**3. 파일 시스템 보안**
- NAS 경로 권한 제한
- UUID 기반 파일명 (추측 불가)
- 다운로드 URL 만료 시간 (1시간)

**4. API 보안**
- Rate limiting (업로드 API: 10회/시간)
- CORS 설정 (허용된 도메인만)
- 파일 업로드 크기 제한

---

## 11. 가치 (Value Proposition)

| 가치                  | 설명                           |
| ------------------- | ---------------------------- |
| **브라우저 완결 워크플로우**   | 프리미어 없이 웹에서 전체 작업 완료         |
| **빠른 미리보기**         | Proxy로 즉시 재생, 구간 확인          |
| **원본 품질 유지**        | 서브클립 추출 시 재인코딩 없이 원본 품질 보존   |
| **정확한 타임코드**        | ffmpeg 기반 프레임 단위 정확도         |
| **제작 시간 단축**        | 업로드 → 미리보기 → 다운로드 5분 이내      |
| **스토리지 효율**         | Proxy 자동 정리로 저장 공간 최적화       |
| **확장 가능한 구조**       | 향후 배치 처리, 자동화 기능 추가 가능       |
| **내부 MAM 기반 구축**    | 상용 솔루션 도입 전 파일럿 시스템으로 활용 가능 |

---

## 12. 결론

이 시스템은:

### 핵심 가치
- **단순함**: 오로지 3가지 기능 (Proxy 렌더링, 구간 미리보기, 원본 다운로드)
- **빠름**: Proxy 기반 즉시 미리보기, 무손실 서브클립 추출
- **정확함**: ffmpeg 기반 프레임 단위 타임코드 정확도

### 사용 시나리오
1. 편집자가 원본 영상 업로드
2. 자동 Proxy 생성 (재생 가능 대기)
3. Proxy로 빠르게 탐색, 필요한 구간 확인
4. 해당 구간 Proxy로 미리보기 (반복 재생)
5. 만족하면 원본 품질로 다운로드
6. 다운로드 받은 파일 바로 프리미어/SNS 활용

### 개발 우선순위
**Phase 1-2 (필수)**: Proxy 렌더링 + 구간 미리보기 + 서브클립 다운로드
**Phase 3 (선택)**: 성능 최적화, 배포

**핵심 원칙**: "프리미어 열기 전에, 웹에서 정확한 구간 확인하고 바로 다운로드"

---

## 13. 생태계 통합 로드맵 (archive-mam 연동)

### Phase 1: 독립 실행 (현재)

**상태**: ✅ 구현 완료 (백엔드 100%, 프론트엔드 40%)

**기능**:
- 영상 업로드 및 Proxy 렌더링
- 수동 타임코드 입력
- 구간 미리보기 및 서브클립 다운로드

**제한사항**:
- archive-mam 연동 없음
- 사용자가 직접 타임코드 찾아야 함

---

### Phase 2: 타임코드 자동 로드 (다음 단계)

**목표**: archive-mam 검색 결과를 man_subclip에서 자동 로드

**구현 요구사항**:

#### 2.1 URL 파라미터 지원

```typescript
// 프론트엔드: VideoPlayerPage.tsx
// URL 파싱
const searchParams = new URLSearchParams(window.location.search);
const autoIn = parseFloat(searchParams.get('in') || '0');
const autoOut = parseFloat(searchParams.get('out') || '0');
const handId = searchParams.get('hand_id'); // 선택 (메타데이터용)

// 자동 로드 로직
useEffect(() => {
  if (autoIn > 0 && autoOut > autoIn) {
    setInPoint(autoIn);
    setOutPoint(autoOut);

    message.success({
      content: '검색 결과에서 타임코드를 자동 로드했습니다.',
      duration: 3
    });
  }
}, [autoIn, autoOut]);
```

#### 2.2 archive-mam에서 연동 버튼 추가

```typescript
// archive-mam 프론트엔드
function HandResultCard({ hand }: { hand: SearchResult }) {
  const handleCreateSubclip = () => {
    const url = `https://man-subclip.ggprod.net/player/${hand.video_id}?in=${hand.timestamps.start}&out=${hand.timestamps.end}&hand_id=${hand.hand_id}`;

    window.open(url, '_blank');
  };

  return (
    <Card>
      <Title>{hand.hero_name} vs {hand.villain_name}</Title>
      <Text>Pot: {hand.pot_bb} BB</Text>
      <Text>Timestamps: {formatTimecode(hand.timestamps.start)} ~ {formatTimecode(hand.timestamps.end)}</Text>

      <Button type="primary" onClick={handleCreateSubclip}>
        서브클립 생성 ⚡
      </Button>
    </Card>
  );
}
```

#### 2.3 메타데이터 전달 (선택)

**옵션 A**: URL 파라미터 확장
```
/player/{video_id}?in=7234.5&out=7398.2&hand_id=hand_042&pot_bb=145.5&hero=Junglemann
```

**옵션 B**: API 호출로 메타데이터 조회
```typescript
// man_subclip에서 hand_id로 archive-mam API 호출
const handMeta = await fetch(`https://archive-mam.ggprod.net/api/hands/${hand_id}`);

// 서브클립 파일명에 자동 반영
// 예: junglemann_vs_ivey_145bb_hand042.mp4
```

**작업량**: 2-3시간

---

### Phase 3: 완전 자동화 (장기 - Q2 2025)

**목표**: 검색 → 서브클립 생성까지 원클릭

**구현 계획**:

#### 3.1 API 기반 서브클립 생성 트리거

```python
# man_subclip 백엔드 API 추가
@router.post("/api/clips/create-from-search")
async def create_clip_from_search(
    video_id: str,
    start_sec: float,
    end_sec: float,
    hand_id: str,
    metadata: dict  # archive-mam에서 전달
):
    # 1. Proxy 확인 (없으면 즉시 생성)
    # 2. 서브클립 추출 트리거
    # 3. 완료 시 다운로드 URL 반환
    return {"clip_id": clip_id, "download_url": url}
```

```typescript
// archive-mam 프론트엔드
async function handleAutoCreateSubclip(hand: SearchResult) {
  const response = await fetch('https://man-subclip.ggprod.net/api/clips/create-from-search', {
    method: 'POST',
    body: JSON.stringify({
      video_id: hand.video_id,
      start_sec: hand.timestamps.start,
      end_sec: hand.timestamps.end,
      hand_id: hand.hand_id,
      metadata: {
        hero: hand.hero_name,
        pot_bb: hand.pot_bb
      }
    })
  });

  const { clip_id, download_url } = await response.json();

  // 진행률 표시 + 완료 시 자동 다운로드
  message.success('서브클립 생성 완료! 다운로드 중...');
  window.location.href = download_url;
}
```

#### 3.2 배치 서브클립 생성

**기능**: 여러 핸드 선택 → 일괄 서브클립 생성

```typescript
// archive-mam UI
<Checkbox.Group>
  {searchResults.map(hand => (
    <Checkbox value={hand.hand_id}>
      {hand.hero_name} - Hand #{hand.hand_number}
    </Checkbox>
  ))}
</Checkbox.Group>

<Button onClick={handleBatchCreate}>
  선택한 {selectedHands.length}개 핸드 서브클립 일괄 생성
</Button>
```

**작업량**: 1주

---

### 통합 로드맵 타임라인

| Phase | 기간 | 상태 | 기능 |
|-------|------|------|------|
| **Phase 1** | 완료 | ✅ 70% | 독립 실행 (수동 타임코드) |
| **Phase 2** | 2-3일 | 🚧 계획 중 | URL 파라미터 자동 로드 |
| **Phase 3** | Q2 2025 | ⏳ 장기 | API 기반 완전 자동화 |

**우선순위**: Phase 2 먼저 완성 → 사용자 피드백 → Phase 3 구현

---

## 14. 현재 구현 상태 (v4.0 - 2025-01-20)

### 📊 Implementation Status: 70% Complete

| 구분       | 상태        | 완성도   | 비고                          |
| -------- | --------- | ----- | --------------------------- |
| **백엔드**  | ✅ 완료      | 100%  | FastAPI + SQLite + ffmpeg   |
| **프론트엔드** | ⚠️ 부분 완료 | 40%   | 기본 UI 있음, 핵심 기능 누락          |
| **전체**   | 🚧 진행 중   | **70%** | 백엔드 완료, 프론트엔드 30% 남음        |

---

### ✅ 완료된 기능 (Backend - 100%)

#### 1. API 엔드포인트
**구현 파일**: `backend/src/api/`

| 엔드포인트                               | 파일               | 상태  | 기능                  |
| ----------------------------------- | ---------------- | --- | ------------------- |
| `POST /api/videos/upload`           | videos.py:37     | ✅   | 영상 업로드              |
| `GET /api/videos`                   | videos.py:77     | ✅   | 영상 목록 조회            |
| `GET /api/videos/{video_id}`        | videos.py:86     | ✅   | 영상 상세 조회            |
| `DELETE /api/videos/{video_id}`     | videos.py:101    | ✅   | 영상 삭제               |
| `POST /api/videos/{video_id}/proxy` | videos.py:114    | ✅   | Proxy 생성 시작         |
| `GET /api/videos/{video_id}/proxy/status` | videos.py:137 | ✅ | Proxy 상태 조회 |
| `POST /api/clips/create`            | clips.py:33      | ✅   | 서브클립 추출             |
| `GET /api/clips/{clip_id}`          | clips.py:78      | ✅   | 클립 정보 조회            |
| `GET /api/clips/{clip_id}/download` | clips.py:93      | ✅   | 클립 다운로드             |
| `DELETE /api/clips/{clip_id}`       | clips.py:110     | ✅   | 클립 삭제               |

#### 2. ffmpeg 처리 파이프라인
**구현 파일**: `backend/src/services/ffmpeg/`

| 파일          | 라인 수 | 기능                   | 상태  |
| ----------- | ---- | -------------------- | --- |
| proxy.py    | 127  | HLS Proxy 변환         | ✅   |
| subclip.py  | 103  | 서브클립 추출 (코덱 복사)      | ✅   |
| progress.py | 77   | ffmpeg 진행률 추적        | ✅   |

**특징**:
- ✅ HLS(m3u8) 변환 완료
- ✅ 코덱 복사(무손실) 추출 완료
- ✅ 진행률 실시간 추적
- ✅ 타임코드 계산 (패딩 포함)

#### 3. 데이터베이스
**구현 파일**: `backend/src/models/`

| 테이블     | 파일        | 상태  | 비고                       |
| ------- | --------- | --- | ------------------------ |
| videos  | video.py  | ✅   | SQLAlchemy 모델 (UUID 기반) |
| clips   | clip.py   | ✅   | SQLAlchemy 모델 (UUID 기반) |

**DB 엔진**: SQLite (개발), PostgreSQL (프로덕션 준비)

#### 4. 스토리지 구조
**디렉토리**: `storage/`

```
storage/
├── original/  ✅ 원본 영상 저장
├── proxy/     ✅ HLS Proxy 저장
└── clips/     ✅ 서브클립 저장
```

---

### ⚠️ 미완성 기능 (Frontend - 30% 남음)

#### 1. Video Player (hls.js 통합)
**현재 상태**: ❌ 누락
**파일**: `frontend/src/pages/VideoPlayerPage.tsx:1-200`

**문제**:
```typescript
// ❌ 현재: 단순 타임코드 입력 폼만 존재
<Form.Item label="In (초)">
  <InputNumber value={inPoint} onChange={setInPoint} />
</Form.Item>
```

**필요**:
```typescript
// ✅ 필요: Video.js + hls.js 통합
import videojs from 'video.js';
import 'video.js/dist/video-js.css';

export function VideoPlayer({ videoId, src }: VideoPlayerProps) {
  const playerRef = useRef<any>(null);

  useEffect(() => {
    const player = videojs(videoRef.current, {
      controls: true,
      sources: [{ src, type: 'application/x-mpegURL' }]
    });

    playerRef.current = player;

    return () => player.dispose();
  }, [src]);

  return <video ref={videoRef} className="video-js vjs-big-play-centered" />;
}
```

**작업량**: 4시간

---

#### 2. Timeline Editor (슬라이더 기반 In/Out 마커)
**현재 상태**: ❌ 누락
**파일**: `frontend/src/pages/VideoPlayerPage.tsx`

**문제**:
- 슬라이더 없음 (단순 InputNumber만)
- 타임라인 표시 없음
- In/Out 마커 드래그 불가

**필요**:
```typescript
// ✅ 필요: Ant Design Slider + 타임라인
<Slider
  range
  min={0}
  max={duration}
  step={0.001}
  value={[inPoint, outPoint]}
  onChange={(values) => {
    setInPoint(values[0]);
    setOutPoint(values[1]);
  }}
  marks={{
    0: '00:00:00',
    [duration]: formatTimecode(duration)
  }}
/>

<Space>
  <TimecodeInput label="In" value={inPoint} onChange={setInPoint} />
  <TimecodeInput label="Out" value={outPoint} onChange={setOutPoint} />
  <Text>Duration: {formatTimecode(outPoint - inPoint)}</Text>
</Space>
```

**작업량**: 6시간

---

#### 3. Timecode Format (HH:MM:SS.mmm)
**현재 상태**: ❌ 누락
**파일**: `frontend/src/pages/VideoPlayerPage.tsx`

**문제**:
- 초 단위 표시만 (예: 323.5초)
- 타임코드 포맷 없음

**필요**:
```typescript
// ✅ 필요: 타임코드 포맷 변환
function formatTimecode(sec: number): string {
  const hours = Math.floor(sec / 3600);
  const mins = Math.floor((sec % 3600) / 60);
  const secs = Math.floor(sec % 60);
  const ms = Math.floor((sec % 1) * 1000);

  return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
}

function parseTimecode(timecode: string): number {
  const [time, ms] = timecode.split('.');
  const [hours, mins, secs] = time.split(':').map(Number);
  return hours * 3600 + mins * 60 + secs + (parseInt(ms) || 0) / 1000;
}

// 사용 예시
<Input
  value={formatTimecode(inPoint)}
  onChange={(e) => setInPoint(parseTimecode(e.target.value))}
  placeholder="00:00:00.000"
/>
```

**작업량**: 2시간

---

#### 4. Preview Loop (구간 미리보기)
**현재 상태**: ❌ 누락
**파일**: `frontend/src/pages/VideoPlayerPage.tsx`

**문제**:
- "구간 미리보기" 버튼 없음
- In~Out 반복 재생 로직 없음

**필요**:
```typescript
// ✅ 필요: 구간 미리보기 기능
function handlePreview() {
  const player = playerRef.current;

  player.currentTime(inPoint);
  player.play();

  const intervalId = setInterval(() => {
    if (player.currentTime() >= outPoint) {
      player.currentTime(inPoint); // Loop back to In
    }
  }, 100);

  setPreviewIntervalId(intervalId);
}

function stopPreview() {
  if (previewIntervalId) {
    clearInterval(previewIntervalId);
    setPreviewIntervalId(null);
  }
}

// UI
<Button type="primary" onClick={handlePreview}>
  구간 미리보기 (In ~ Out 반복 재생)
</Button>
<Button onClick={stopPreview}>중지</Button>
```

**작업량**: 4시간

---

#### 5. Padding Options (패딩 선택)
**현재 상태**: ✅ 부분 완료 (InputNumber만)
**파일**: `frontend/src/pages/VideoPlayerPage.tsx:93`

**개선 필요**:
```typescript
// ✅ 현재
<InputNumber value={padding} onChange={setPadding} />

// ✅ 개선: Radio 버튼 + 커스텀 입력
<Radio.Group value={paddingOption} onChange={(e) => setPaddingOption(e.target.value)}>
  <Radio value="none">패딩 없음</Radio>
  <Radio value="3sec">3초 자동 추가</Radio>
  <Radio value="custom">커스텀</Radio>
</Radio.Group>

{paddingOption === 'custom' && (
  <InputNumber value={padding} onChange={setPadding} suffix="초" />
)}
```

**작업량**: 2시간

---

### 🚫 Scope Creep (PRD 외 기능)

다음 파일들은 **PRD에 없는 기능**이므로 제거 권장:

| 파일                                    | 라인 수 | 기능             | 상태  | 조치       |
| ------------------------------------- | ---- | -------------- | --- | -------- |
| `backend/src/api/search.py`           | 333  | Mixpeek 영상 검색  | 🚫  | **제거 권장** |
| `backend/src/api/preview_v2.py`       | 227  | 미리보기 v2 (중복)  | 🚫  | **제거 권장** |
| `backend/src/services/transcoder_client.py` | 150  | GCP Transcoder | 🚫  | **제거 권장** |
| `backend/src/services/search/`        | 다수   | 검색 서비스 디렉토리   | 🚫  | **제거 권장** |

**이유**:
- PRD는 "Only 3 Functions" 명시
- 검색 기능은 PRD에 없음
- Transcoder는 이미 proxy.py로 구현 완료
- 코드 복잡도 증가, 유지보수 어려움

---

### 🎯 Next Steps (권장 작업)

#### Option A: MVP 완성 (권장 ⭐)

**1. Scope Creep 제거**:
```bash
rm backend/src/api/search.py
rm backend/src/api/preview_v2.py
rm backend/src/services/transcoder_client.py
rm -rf backend/src/services/search/
```

**2. Frontend 핵심 기능 구현** (16시간 = 2-3일):
- [ ] Video.js HLS 플레이어 통합 (4시간)
- [ ] 슬라이더 기반 Timeline Editor (6시간)
- [ ] Timecode 포맷 변환 (2시간)
- [ ] 구간 미리보기 Loop (4시간)
- [ ] Padding 옵션 UI 개선 (2시간)

**3. E2E 테스트** (4시간):
```bash
npx playwright test
# 시나리오: 업로드 → Proxy 재생 → In/Out 지정 → 미리보기 → 다운로드
```

**4. Port 8000 통일**:
```bash
# backend/.env
# (포트 변경 없음 - 이미 8000 사용 중인 서비스 정리 필요)

# frontend/vite.config.ts
target: 'http://localhost:8000'  # 8001 → 8000
```

**총 작업 시간**: 20시간 (2-3일)

---

#### Option B: 모든 기능 유지 (비권장)

**작업**:
- Scope creep 파일 유지
- 검색 기능 완성
- 두 가지 기능셋 병행 유지

**문제**:
- PRD 위반 ("Only 3 Functions")
- 코드 복잡도 2배
- 유지보수 어려움
- 완성까지 2주 이상 소요

**결론**: ❌ 권장하지 않음

---

### 📋 Implementation Checklist

#### Phase 0.5: Task List
- [ ] Claude Code에게 Task List 생성 요청
  ```
  "docs/prd.md 읽고 Task List 작성해줘"
  ```

#### Phase 1: Implementation (Option A)
- [ ] Scope creep 제거 (search.py, preview_v2.py 등)
- [ ] Video.js 플레이어 구현
- [ ] Timeline Editor 구현
- [ ] Timecode 포맷 구현
- [ ] Preview Loop 구현
- [ ] Padding UI 개선

#### Phase 2: Testing
- [ ] Unit Tests (타임코드 변환)
- [ ] E2E Tests (Playwright)
- [ ] 크로스 브라우저 테스트

#### Phase 3: Deployment
- [ ] Port 8000 통일
- [ ] Docker 컨테이너화
- [ ] CI/CD 설정

---

### 💡 Conclusion

**현재 상황**:
- ✅ 백엔드 100% 완료 (ffmpeg 파이프라인, API 완비)
- ⚠️ 프론트엔드 40% 완료 (기본 폼만, 핵심 UI 누락)
- 🚫 Scope creep 존재 (PRD 외 검색 기능)

**권장 방향**:
1. **Option A 선택**: MVP 완성 (2-3일)
2. Scope creep 제거
3. 프론트엔드 핵심 기능 완성
4. E2E 테스트 후 배포

**핵심 원칙 준수**:
> "Only 3 Functions: Proxy 렌더링, 구간 미리보기, 원본 다운로드"

---
