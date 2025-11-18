# 📘 **영상 Proxy & 서브클립 추출 플랫폼 – PRD**

**GG PRODUCTION — Internal Document v3.0**

---

## 0. 시스템 목적 (Mission)

원본 영상을 **Proxy로 렌더링**하고, **타임코드 구간을 미리보기**한 후, **원본 품질의 서브클립을 다운로드**하는 브라우저 기반 영상 처리 플랫폼.

### 핵심 기능 (Only 3 Functions)

1. **영상 Proxy 렌더링**
   - 원본 고해상도 영상 → 브라우저 재생 가능한 저용량 HLS Proxy 자동 생성

2. **Proxy 기반 구간 미리보기**
   - Proxy로 빠른 재생
   - In/Out 타임코드 지정
   - 지정된 구간만 Proxy로 즉시 미리보기

3. **원본 품질 서브클립 다운로드**
   - 지정된 구간을 원본 영상에서 정확하게 추출
   - 원본 품질 유지 (재인코딩 없음)
   - 즉시 다운로드 가능

---

## 1. 전체 아키텍처

```
[사용자 업로드]
        ↓
   원본 영상 (NAS)
        ↓
   ffmpeg Proxy 렌더링
   → HLS (m3u8)
        ↓
   Proxy 영상 (NAS)
        ↓
   브라우저 재생
   - In/Out 타임코드 지정
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
Proxy 영상으로 빠른 탐색 후, 특정 구간을 미리보기.

#### UI 기능

**Video Player**:
- HLS Proxy 재생 (hls.js)
- 재생 컨트롤 (play/pause, seek, 배속)
- 현재 타임코드 표시 (00:00:00.000)

**Timeline Editor**:
- 전체 타임라인 표시
- In/Out 마커 드래그 (슬라이더)
- 타임코드 수동 입력
  ```
  In:  00:05:23.500
  Out: 00:06:45.200
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
