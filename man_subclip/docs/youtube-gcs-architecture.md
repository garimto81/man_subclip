# YouTube + GCS 통합 아키텍처 설계

**Version**: 1.0.0
**Date**: 2025-01-18
**Status**: Proposal (Phase 0)

---

## 요구사항 요약

### 1. YouTube 영상
- **미리보기**: YouTube Player API 사용 (프록시 불필요)
- **서브클립 추출**: GCS 원본 연동 필수
- **워크플로우**: YouTube → 구간 선택 → GCS 원본에서 추출

### 2. GCS 영상
- **미리보기**: GCS → 프록시 렌더링 → HLS 재생
- **서브클립 추출**: GCS 원본에서 직접 추출
- **워크플로우**: GCS 업로드 → 프록시 생성 → 구간 선택 → 원본 추출

### 3. YouTube-GCS 연동
- YouTube URL과 GCS 원본 경로를 매핑
- 미리보기는 YouTube, 추출은 GCS 원본
- 메타데이터 동기화 (duration, fps, resolution)

---

## 시스템 아키텍처

### 전체 플로우

```
┌─────────────────────────────────────────────────────────┐
│                    사용자 입력                             │
├─────────────────┬───────────────────────────────────────┤
│  YouTube URL    │         GCS 파일 경로                   │
└────────┬────────┴──────────────┬────────────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌──────────────────┐
│ YouTube Video   │     │   GCS Original   │
│  - video_id     │◄────┤   - gs://bucket/ │
│  - url          │ 연동  │   - 원본 파일     │
│  - duration     │     │   - 메타데이터    │
└────────┬────────┘     └────────┬─────────┘
         │                       │
         │ (프록시 불필요)         │ (프록시 필요)
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌──────────────────┐
│ YouTube Player  │     │  ffmpeg HLS      │
│  직접 재생        │     │  Proxy 렌더링     │
│  (iframe API)   │     │  → m3u8          │
└────────┬────────┘     └────────┬─────────┘
         │                       │
         └───────────┬───────────┘
                     ▼
         ┌──────────────────────┐
         │  Timeline Editor     │
         │  - In/Out 타임코드    │
         │  - 구간 미리보기       │
         └──────────┬───────────┘
                    ▼
         ┌──────────────────────┐
         │   서브클립 추출 요청    │
         └──────────┬───────────┘
                    ▼
         ┌──────────────────────┐
         │  GCS 원본에서 추출     │
         │  (ffmpeg -c copy)    │
         │  → 원본 품질 유지      │
         └──────────┬───────────┘
                    ▼
         ┌──────────────────────┐
         │   서브클립 다운로드    │
         └──────────────────────┘
```

---

## 데이터 모델 (Database Schema)

### 1. `videos` 테이블 확장

```sql
CREATE TABLE videos (
  video_id UUID PRIMARY KEY,

  -- 기본 정보
  filename VARCHAR(255),
  source_type VARCHAR(20) NOT NULL,  -- 'youtube' | 'gcs' | 'nas'

  -- YouTube 정보
  youtube_url TEXT,                  -- YouTube URL (source_type='youtube'인 경우)
  youtube_video_id VARCHAR(20),      -- YouTube video ID

  -- GCS 정보
  gcs_bucket VARCHAR(255),           -- gs://bucket-name
  gcs_path TEXT,                     -- GCS 원본 경로
  gcs_signed_url TEXT,               -- GCS 서명된 URL (만료 시간 있음)
  gcs_signed_url_expires TIMESTAMP,  -- 서명 URL 만료 시간

  -- NAS 정보 (기존 시스템 호환)
  original_path TEXT,                -- NAS 경로 (레거시)

  -- 프록시 정보
  proxy_path TEXT,                   -- HLS m3u8 경로
  proxy_status VARCHAR(20),          -- pending|processing|completed|failed|not_required

  -- YouTube-GCS 연동
  linked_video_id UUID,              -- 연결된 영상 ID (YouTube ↔ GCS)

  -- 메타데이터
  duration_sec FLOAT,
  fps INT,
  width INT,
  height INT,
  file_size_mb FLOAT,

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  -- 제약 조건
  CONSTRAINT valid_source_type CHECK (source_type IN ('youtube', 'gcs', 'nas')),
  CONSTRAINT youtube_url_required CHECK (
    (source_type = 'youtube' AND youtube_url IS NOT NULL) OR
    (source_type != 'youtube')
  ),
  CONSTRAINT gcs_path_required CHECK (
    (source_type = 'gcs' AND gcs_path IS NOT NULL) OR
    (source_type != 'gcs')
  )
);

-- 인덱스
CREATE INDEX idx_videos_source_type ON videos(source_type);
CREATE INDEX idx_videos_youtube_video_id ON videos(youtube_video_id);
CREATE INDEX idx_videos_linked_video_id ON videos(linked_video_id);
```

### 2. `clips` 테이블 (변경 없음)

```sql
CREATE TABLE clips (
  clip_id UUID PRIMARY KEY,
  video_id UUID REFERENCES videos(video_id) ON DELETE CASCADE,

  -- 타임코드 정보
  start_sec FLOAT NOT NULL,
  end_sec FLOAT NOT NULL,
  padding_sec FLOAT DEFAULT 0,

  -- 추출 소스 (중요!)
  extraction_source VARCHAR(20) NOT NULL,  -- 'gcs' | 'nas'
  source_video_id UUID,                    -- GCS 원본 video_id (YouTube의 경우)

  -- 파일 정보
  file_path TEXT NOT NULL,                 -- 추출된 클립 경로
  file_size_mb FLOAT,
  duration_sec FLOAT,

  created_at TIMESTAMP DEFAULT NOW(),

  CONSTRAINT valid_extraction_source CHECK (extraction_source IN ('gcs', 'nas'))
);
```

---

## API 엔드포인트 설계

### 1. YouTube 영상 추가

```http
POST /api/videos/youtube
Content-Type: application/json

{
  "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "gcs_original_path": "gs://my-bucket/originals/video.mp4",  // Optional
  "auto_link": true  // GCS 원본 자동 연동 여부
}

Response 201:
{
  "video_id": "uuid",
  "youtube_url": "...",
  "youtube_video_id": "VIDEO_ID",
  "source_type": "youtube",
  "duration_sec": 625.5,
  "proxy_status": "not_required",
  "linked_video_id": "uuid",  // GCS 원본 연동된 경우
  "metadata": {
    "title": "...",
    "duration": "00:10:25",
    "resolution": "1920x1080"
  }
}
```

### 2. GCS 영상 추가

```http
POST /api/videos/gcs
Content-Type: application/json

{
  "gcs_path": "gs://my-bucket/originals/video.mp4",
  "filename": "my-video.mp4",
  "auto_proxy": true,  // 자동 프록시 생성 여부
  "youtube_video_id": "uuid"  // Optional: 기존 YouTube 영상과 연동
}

Response 201:
{
  "video_id": "uuid",
  "gcs_path": "gs://my-bucket/originals/video.mp4",
  "gcs_signed_url": "https://storage.googleapis.com/...",
  "gcs_signed_url_expires": "2025-01-19T10:00:00Z",
  "source_type": "gcs",
  "proxy_status": "pending",
  "linked_video_id": "youtube-video-uuid",
  "metadata": { ... }
}
```

### 3. YouTube-GCS 연동

```http
POST /api/videos/{youtube_video_id}/link-gcs
Content-Type: application/json

{
  "gcs_video_id": "uuid"
}

Response 200:
{
  "youtube_video": {
    "video_id": "uuid",
    "youtube_url": "...",
    "linked_video_id": "gcs-uuid"
  },
  "gcs_video": {
    "video_id": "uuid",
    "gcs_path": "...",
    "linked_video_id": "youtube-uuid"
  },
  "metadata_sync": {
    "duration_match": true,
    "fps_match": true,
    "resolution_match": false  // Warning 발생
  }
}
```

### 4. 서브클립 추출 (통합 엔드포인트)

```http
POST /api/clips
Content-Type: application/json

{
  "video_id": "youtube-or-gcs-uuid",
  "start_sec": 10.5,
  "end_sec": 45.2,
  "padding_sec": 3,
  "force_source": "gcs"  // Optional: 'gcs' | 'nas'
}

Backend Logic:
1. video_id가 YouTube인 경우:
   - linked_video_id에서 GCS 원본 찾기
   - GCS 원본에서 추출
2. video_id가 GCS인 경우:
   - GCS 원본에서 직접 추출

Response 201:
{
  "clip_id": "uuid",
  "video_id": "youtube-uuid",
  "source_video_id": "gcs-uuid",
  "extraction_source": "gcs",
  "start_sec": 10.5,
  "end_sec": 45.2,
  "status": "processing"
}
```

---

## 백엔드 서비스 구조

### 디렉토리 구조

```
backend/src/
├── api/
│   ├── videos.py           # 기존 (NAS 업로드)
│   ├── videos_youtube.py   # 🆕 YouTube 영상 관리
│   ├── videos_gcs.py       # 🆕 GCS 영상 관리
│   ├── videos_linking.py   # 🆕 YouTube-GCS 연동
│   └── clips.py            # 서브클립 추출 (확장)
│
├── services/
│   ├── youtube/
│   │   ├── metadata.py     # 🆕 YouTube API로 메타데이터 가져오기
│   │   ├── validator.py    # 🆕 YouTube URL 검증
│   │   └── embed.py        # 🆕 YouTube iframe 생성
│   │
│   ├── gcs/
│   │   ├── storage.py      # 🆕 GCS 파일 관리
│   │   ├── download.py     # 🆕 GCS → 로컬 다운로드 (서브클립용)
│   │   ├── signed_url.py   # 🆕 서명된 URL 생성
│   │   └── metadata.py     # 🆕 GCS 파일 메타데이터
│   │
│   ├── ffmpeg/
│   │   ├── proxy.py        # 기존 (HLS 변환)
│   │   ├── subclip.py      # 확장 (GCS 지원)
│   │   └── gcs_proxy.py    # 🆕 GCS → 프록시 렌더링
│   │
│   ├── linking/
│   │   ├── youtube_gcs.py  # 🆕 YouTube-GCS 매핑
│   │   └── metadata_sync.py# 🆕 메타데이터 동기화
│   │
│   └── storage.py          # 기존 (NAS 관리)
│
└── models/
    ├── video.py            # 확장 (source_type 필드 추가)
    └── clip.py             # 확장 (extraction_source 필드 추가)
```

---

## 핵심 기술 스택 추가

| 영역 | 기술 | 용도 |
|------|------|------|
| **YouTube 연동** | YouTube Data API v3 | 메타데이터 조회 |
| **YouTube 재생** | YouTube IFrame Player API | 브라우저 직접 재생 |
| **GCS 연동** | Google Cloud Storage Python SDK | 파일 업로드/다운로드 |
| **GCS 인증** | Service Account JSON | GCS 접근 권한 |
| **임시 다운로드** | tempfile | 서브클립 추출 전 GCS → 로컬 |

---

## 워크플로우 상세

### 시나리오 1: YouTube 영상 미리보기 + GCS 원본 서브클립

```
1. 사용자: YouTube URL 입력
   POST /api/videos/youtube
   {
     "youtube_url": "https://youtube.com/watch?v=ABC123",
     "gcs_original_path": "gs://my-bucket/originals/ABC123.mp4"
   }

2. 백엔드:
   - YouTube Data API로 메타데이터 조회 (제목, duration, 해상도)
   - GCS 파일 존재 확인
   - videos 테이블에 2개 레코드 생성:
     a) YouTube 영상 (source_type='youtube', proxy_status='not_required')
     b) GCS 원본 (source_type='gcs', linked_video_id=youtube_uuid)
   - GCS 원본 프록시 렌더링 시작 (선택적)

3. 프론트엔드:
   - YouTube IFrame Player 표시
   - Timeline Editor에서 In/Out 지정
   - "구간 미리보기" → YouTube seekTo() API 사용

4. 사용자: "서브클립 다운로드" 클릭
   POST /api/clips
   {
     "video_id": "youtube-uuid",
     "start_sec": 10,
     "end_sec": 30
   }

5. 백엔드:
   - linked_video_id에서 GCS 원본 찾기
   - GCS 파일을 임시 로컬에 다운로드
   - ffmpeg로 서브클립 추출
   - 추출된 클립을 NAS 또는 GCS에 저장
   - 다운로드 URL 반환
```

### 시나리오 2: GCS 영상 프록시 미리보기 + 원본 서브클립

```
1. 사용자: GCS 경로 입력
   POST /api/videos/gcs
   {
     "gcs_path": "gs://my-bucket/originals/video.mp4",
     "auto_proxy": true
   }

2. 백엔드:
   - GCS 파일 메타데이터 조회
   - videos 테이블에 레코드 생성 (source_type='gcs')
   - 프록시 렌더링 작업 큐 등록
   - GCS 파일 다운로드 → ffmpeg HLS 변환 → NAS 저장

3. 프론트엔드:
   - 프록시 상태 폴링 (GET /api/videos/{video_id}/proxy/status)
   - 완료 시 HLS 플레이어 표시
   - Timeline Editor에서 In/Out 지정

4. 사용자: "서브클립 다운로드"
   - GCS 원본에서 직접 추출 (시나리오 1과 동일)
```

---

## 보안 및 권한 관리

### 1. GCS 접근 권한

```python
# backend/.env
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GCS_BUCKET_NAME=my-video-bucket

# Service Account 권한 (최소 권한 원칙)
# - Storage Object Viewer: 파일 읽기
# - Storage Object Creator: 클립 업로드 (선택적)
```

### 2. YouTube API 인증

```python
# backend/.env
YOUTUBE_API_KEY=AIzaSy...

# 사용량 제한
# - 할당량: 10,000 units/day (기본)
# - videos.list (메타데이터 조회): 1 unit
```

### 3. GCS 서명된 URL

```python
from google.cloud import storage
from datetime import timedelta

def generate_signed_url(bucket_name: str, blob_name: str) -> str:
    """1시간 유효한 서명된 URL 생성"""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(hours=1),
        method="GET"
    )
    return url
```

---

## 성능 최적화

### 1. GCS 다운로드 최적화

```python
# 서브클립 추출 시 전체 파일 다운로드 방지
# → ffmpeg HTTP range request 활용
ffmpeg -ss {start_sec} -to {end_sec} \
  -i "https://storage.googleapis.com/.../signed_url" \
  -c copy output.mp4

# 장점: GCS에서 필요한 구간만 스트리밍
# 단점: 키프레임 정확도 저하 가능성
```

### 2. 프록시 캐싱

```python
# GCS 프록시는 NAS에 저장 (기존 시스템과 동일)
# - 30일 후 자동 삭제
# - 재요청 시 재생성
```

### 3. YouTube 메타데이터 캐싱

```python
# Redis 캐싱 (1일)
import redis
import json

cache = redis.Redis(host='localhost', port=6379)

def get_youtube_metadata(video_id: str):
    cache_key = f"youtube:metadata:{video_id}"
    cached = cache.get(cache_key)

    if cached:
        return json.loads(cached)

    # YouTube API 호출
    metadata = youtube_api.videos().list(...).execute()

    # 캐싱
    cache.setex(cache_key, 86400, json.dumps(metadata))
    return metadata
```

---

## 프론트엔드 변경 사항

### 1. Video Source 선택 UI

```tsx
// UploadPage.tsx 확장
<Tabs defaultActiveKey="nas">
  <TabPane tab="NAS 업로드" key="nas">
    <Upload.Dragger {...uploadProps} />
  </TabPane>

  <TabPane tab="YouTube 추가" key="youtube">
    <Form onFinish={handleYouTubeSubmit}>
      <Form.Item name="youtube_url" label="YouTube URL">
        <Input placeholder="https://www.youtube.com/watch?v=..." />
      </Form.Item>
      <Form.Item name="gcs_original" label="GCS 원본 경로 (선택)">
        <Input placeholder="gs://bucket/path/to/video.mp4" />
      </Form.Item>
      <Button type="primary" htmlType="submit">추가</Button>
    </Form>
  </TabPane>

  <TabPane tab="GCS 영상" key="gcs">
    <Form onFinish={handleGCSSubmit}>
      <Form.Item name="gcs_path" label="GCS 경로">
        <Input placeholder="gs://bucket/path/to/video.mp4" />
      </Form.Item>
      <Form.Item name="auto_proxy" valuePropName="checked">
        <Checkbox>자동 프록시 생성</Checkbox>
      </Form.Item>
      <Button type="primary" htmlType="submit">추가</Button>
    </Form>
  </TabPane>
</Tabs>
```

### 2. Video Player (YouTube 지원)

```tsx
// VideoPlayerPage.tsx 확장
import YouTubePlayer from 'react-youtube';

function VideoPlayerPage({ video }) {
  if (video.source_type === 'youtube') {
    return (
      <YouTubePlayer
        videoId={video.youtube_video_id}
        opts={{
          playerVars: {
            start: Math.floor(inSec),
            end: Math.floor(outSec),
          },
        }}
        onReady={handlePlayerReady}
      />
    );
  }

  // GCS/NAS: HLS 플레이어 (기존)
  return <HLSPlayer src={video.proxy_path} />;
}
```

### 3. VideoCard (소스 타입 표시)

```tsx
// VideoCard.tsx 확장
<Card>
  <Badge
    count={
      video.source_type === 'youtube' ? 'YouTube' :
      video.source_type === 'gcs' ? 'GCS' : 'NAS'
    }
    style={{ backgroundColor: getBadgeColor(video.source_type) }}
  />

  {video.linked_video_id && (
    <Tag icon={<LinkOutlined />} color="blue">
      {video.source_type === 'youtube' ? 'GCS 원본 연동' : 'YouTube 연동'}
    </Tag>
  )}

  <p>{video.filename}</p>
  <p>Duration: {formatDuration(video.duration_sec)}</p>
</Card>
```

---

## 마이그레이션 전략

### 1. 기존 NAS 시스템 호환성

```sql
-- 기존 videos 테이블 마이그레이션
ALTER TABLE videos
  ADD COLUMN source_type VARCHAR(20) DEFAULT 'nas',
  ADD COLUMN youtube_url TEXT,
  ADD COLUMN youtube_video_id VARCHAR(20),
  ADD COLUMN gcs_bucket VARCHAR(255),
  ADD COLUMN gcs_path TEXT,
  ADD COLUMN linked_video_id UUID;

-- 기존 레코드는 source_type='nas'로 자동 설정
UPDATE videos SET source_type = 'nas' WHERE source_type IS NULL;
```

### 2. 점진적 배포

**Phase 1**: YouTube 읽기 전용
- YouTube 메타데이터 조회만 지원
- GCS 연동 없이 YouTube 미리보기만

**Phase 2**: GCS 읽기 전용
- GCS 파일 메타데이터 조회
- GCS → 프록시 렌더링

**Phase 3**: YouTube-GCS 연동
- 서브클립 추출 (GCS 원본)
- 메타데이터 동기화

**Phase 4**: 전체 통합
- 자동 연동 기능
- 배치 처리

---

## 제약 사항 및 고려 사항

### 1. YouTube 제한 사항

**제한**:
- YouTube API 할당량: 10,000 units/day (무료)
- 서브클립 추출 불가 (YouTube에서 직접 다운로드 불가)
- 저작권 제한 영상 재생 불가

**해결**:
- GCS 원본 필수 연동
- YouTube는 미리보기 전용
- API 할당량 모니터링

### 2. GCS 비용

**비용 요소**:
- Storage: $0.020/GB/month (Standard)
- Egress (다운로드): $0.12/GB (아시아)
- Operations: $0.05/10,000 requests (Class A)

**최적화**:
- 서브클립만 다운로드 (전체 파일 X)
- ffmpeg HTTP range request 활용
- 프록시는 NAS에 캐싱

### 3. 메타데이터 동기화

**문제**:
- YouTube와 GCS 원본의 duration이 다를 수 있음 (인코딩 차이)
- FPS, 해상도 불일치

**해결**:
- 허용 오차 설정 (±1초 duration)
- 경고 표시 (불일치 시)
- 수동 매핑 기능

---

## 테스트 계획

### 1. 유닛 테스트

```python
# tests/services/test_youtube_metadata.py
def test_get_youtube_metadata():
    metadata = get_youtube_metadata("dQw4w9WgXcQ")
    assert metadata["duration_sec"] > 0
    assert metadata["title"] is not None

# tests/services/test_gcs_storage.py
def test_gcs_file_exists():
    exists = check_gcs_file_exists("gs://bucket/video.mp4")
    assert exists is True

# tests/services/test_linking.py
def test_link_youtube_gcs():
    yt_video = create_youtube_video(...)
    gcs_video = create_gcs_video(...)
    link_videos(yt_video.video_id, gcs_video.video_id)

    assert yt_video.linked_video_id == gcs_video.video_id
    assert gcs_video.linked_video_id == yt_video.video_id
```

### 2. 통합 테스트

```python
# tests/integration/test_youtube_to_clip.py
def test_youtube_preview_gcs_extraction():
    # 1. YouTube 영상 추가
    response = client.post("/api/videos/youtube", json={
        "youtube_url": "...",
        "gcs_original_path": "gs://test/video.mp4"
    })
    youtube_video = response.json()

    # 2. 서브클립 추출 요청
    response = client.post("/api/clips", json={
        "video_id": youtube_video["video_id"],
        "start_sec": 10,
        "end_sec": 20
    })
    clip = response.json()

    # 3. GCS 원본에서 추출 확인
    assert clip["extraction_source"] == "gcs"
    assert clip["source_video_id"] == youtube_video["linked_video_id"]
```

---

## 다음 단계 (Implementation Roadmap)

### Phase 0: 설계 검토 (현재)
- [x] 요구사항 분석
- [x] 아키텍처 설계
- [ ] PRD 업데이트
- [ ] 이해관계자 검토

### Phase 1: YouTube 기본 지원 (Week 1-2)
- [ ] YouTube Data API 연동
- [ ] YouTube 메타데이터 조회
- [ ] YouTube Player 통합
- [ ] videos 테이블 마이그레이션

### Phase 2: GCS 스토리지 연동 (Week 3-4)
- [ ] GCS Python SDK 연동
- [ ] GCS 파일 메타데이터 조회
- [ ] GCS → 프록시 렌더링
- [ ] 서명된 URL 생성

### Phase 3: YouTube-GCS 연동 (Week 5-6)
- [ ] 연동 API 구현
- [ ] 메타데이터 동기화
- [ ] 서브클립 추출 (GCS 원본)
- [ ] 프론트엔드 UI 업데이트

### Phase 4: 테스트 및 최적화 (Week 7-8)
- [ ] E2E 테스트
- [ ] 성능 최적화
- [ ] 문서화
- [ ] 배포

---

## 참고 자료

- [YouTube Data API v3](https://developers.google.com/youtube/v3)
- [YouTube IFrame Player API](https://developers.google.com/youtube/iframe_api_reference)
- [Google Cloud Storage Python SDK](https://cloud.google.com/storage/docs/reference/libraries#client-libraries-install-python)
- [ffmpeg HTTP Protocol](https://ffmpeg.org/ffmpeg-protocols.html#http)
- [Signed URLs for GCS](https://cloud.google.com/storage/docs/access-control/signed-urls)

---

**검토자**: [Name]
**승인 상태**: Pending
**마지막 업데이트**: 2025-01-18
