# GCS 스토리지 통합 아키텍처 설계

**Version**: 1.0.0
**Date**: 2025-01-18
**Status**: Proposal (Phase 0)

---

## 요구사항 요약

### GCS 중심 영상 처리
- **원본 저장**: Google Cloud Storage (GCS) 버킷
- **미리보기**: GCS → Proxy 렌더링 → HLS 재생
- **서브클립 추출**: GCS 원본에서 직접 추출
- **워크플로우**: GCS 업로드 → 프록시 생성 → 구간 선택 → 원본 추출

---

## 시스템 아키텍처

### 전체 플로우

```
┌──────────────────────────────────────────────┐
│          사용자: GCS 경로 입력                  │
│       gs://bucket-name/videos/video.mp4      │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
         ┌──────────────────┐
         │   GCS Original   │
         │  - gs://bucket/  │
         │  - 원본 파일       │
         │  - 메타데이터      │
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │  GCS 다운로드     │
         │  (임시 또는 캐싱) │
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │  ffmpeg HLS      │
         │  Proxy 렌더링     │
         │  → m3u8          │
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │  HLS Player      │
         │  브라우저 재생     │
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │ Timeline Editor  │
         │ - In/Out 지정    │
         │ - 구간 미리보기   │
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │ 서브클립 추출 요청 │
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │ GCS 원본에서 추출 │
         │ (ffmpeg -c copy) │
         │ → 원본 품질 유지  │
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │ 서브클립 저장     │
         │ - NAS 또는       │
         │ - GCS (clips/)   │
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │  다운로드 제공    │
         └──────────────────┘
```

---

## 데이터 모델 (Database Schema)

### 1. `videos` 테이블 확장

```sql
CREATE TABLE videos (
  video_id UUID PRIMARY KEY,

  -- 기본 정보
  filename VARCHAR(255),
  source_type VARCHAR(20) NOT NULL DEFAULT 'gcs',  -- 'gcs' | 'nas' (레거시)

  -- GCS 정보
  gcs_bucket VARCHAR(255) NOT NULL,       -- 버킷명 (예: my-video-bucket)
  gcs_path TEXT NOT NULL,                 -- GCS 객체 경로 (예: originals/video.mp4)
  gcs_full_path TEXT NOT NULL,            -- 전체 경로 (예: gs://bucket/originals/video.mp4)
  gcs_signed_url TEXT,                    -- 서명된 URL (만료 시간 있음)
  gcs_signed_url_expires TIMESTAMP,       -- 서명 URL 만료 시간

  -- NAS 정보 (레거시 호환)
  original_path TEXT,                     -- NAS 경로 (기존 시스템)

  -- 프록시 정보
  proxy_path TEXT,                        -- HLS m3u8 경로 (NAS 저장)
  proxy_status VARCHAR(20),               -- pending|processing|completed|failed
  proxy_gcs_path TEXT,                    -- 프록시 GCS 저장 경로 (선택)

  -- 메타데이터
  duration_sec FLOAT,
  fps INT,
  width INT,
  height INT,
  file_size_mb FLOAT,
  codec_video VARCHAR(50),                -- H.264, H.265 등
  codec_audio VARCHAR(50),                -- AAC, MP3 등

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  -- 제약 조건
  CONSTRAINT valid_source_type CHECK (source_type IN ('gcs', 'nas')),
  CONSTRAINT gcs_path_required CHECK (
    (source_type = 'gcs' AND gcs_path IS NOT NULL AND gcs_bucket IS NOT NULL) OR
    (source_type != 'gcs')
  )
);

-- 인덱스
CREATE INDEX idx_videos_source_type ON videos(source_type);
CREATE INDEX idx_videos_gcs_bucket ON videos(gcs_bucket);
CREATE INDEX idx_videos_gcs_path ON videos(gcs_path);
```

### 2. `clips` 테이블 확장

```sql
CREATE TABLE clips (
  clip_id UUID PRIMARY KEY,
  video_id UUID REFERENCES videos(video_id) ON DELETE CASCADE,

  -- 타임코드 정보
  start_sec FLOAT NOT NULL,
  end_sec FLOAT NOT NULL,
  padding_sec FLOAT DEFAULT 0,

  -- 파일 정보
  file_path TEXT NOT NULL,                -- NAS 경로 또는 로컬 경로
  gcs_clip_path TEXT,                     -- GCS 클립 저장 경로 (선택)
  file_size_mb FLOAT,
  duration_sec FLOAT,

  -- 추출 정보
  extraction_source VARCHAR(20) NOT NULL DEFAULT 'gcs',  -- 'gcs' | 'nas'
  extraction_method VARCHAR(20) DEFAULT 'copy',           -- 'copy' | 'transcode'

  created_at TIMESTAMP DEFAULT NOW(),

  CONSTRAINT valid_extraction_source CHECK (extraction_source IN ('gcs', 'nas'))
);

-- 인덱스
CREATE INDEX idx_clips_video_id ON clips(video_id);
CREATE INDEX idx_clips_gcs_clip_path ON clips(gcs_clip_path);
```

---

## API 엔드포인트 설계

### 1. GCS 영상 추가

```http
POST /api/videos/gcs
Content-Type: application/json

{
  "gcs_path": "gs://my-bucket/originals/video.mp4",
  "filename": "my-video.mp4",
  "auto_proxy": true,                    // 자동 프록시 생성 여부
  "proxy_storage": "nas"                 // 'nas' | 'gcs' (프록시 저장 위치)
}

Response 201:
{
  "video_id": "uuid",
  "gcs_bucket": "my-bucket",
  "gcs_path": "originals/video.mp4",
  "gcs_full_path": "gs://my-bucket/originals/video.mp4",
  "gcs_signed_url": "https://storage.googleapis.com/...",
  "gcs_signed_url_expires": "2025-01-19T10:00:00Z",
  "source_type": "gcs",
  "proxy_status": "pending",
  "metadata": {
    "duration_sec": 625.5,
    "fps": 30,
    "width": 1920,
    "height": 1080,
    "file_size_mb": 1250.5,
    "codec_video": "h264",
    "codec_audio": "aac"
  }
}
```

### 2. GCS 영상 목록 조회

```http
GET /api/videos?source_type=gcs&bucket=my-bucket

Response 200:
{
  "videos": [
    {
      "video_id": "uuid",
      "filename": "video1.mp4",
      "gcs_full_path": "gs://my-bucket/originals/video1.mp4",
      "proxy_status": "completed",
      "duration_sec": 625.5,
      "created_at": "2025-01-18T10:00:00Z"
    },
    ...
  ],
  "total": 150,
  "page": 1,
  "page_size": 20
}
```

### 3. 프록시 렌더링 시작

```http
POST /api/videos/{video_id}/proxy/start
Content-Type: application/json

{
  "proxy_storage": "nas",  // 'nas' | 'gcs'
  "quality": "720p",       // '720p' | '1080p' | '480p'
  "preset": "fast"         // 'fast' | 'medium' | 'slow'
}

Response 202:
{
  "video_id": "uuid",
  "proxy_status": "processing",
  "estimated_time_sec": 300,
  "job_id": "proxy-job-uuid"
}
```

### 4. 프록시 상태 조회

```http
GET /api/videos/{video_id}/proxy/status

Response 200:
{
  "video_id": "uuid",
  "proxy_status": "processing",
  "progress_percent": 45,
  "current_sec": 280,
  "total_sec": 625,
  "estimated_remaining_sec": 120
}
```

### 5. 서브클립 추출

```http
POST /api/clips
Content-Type: application/json

{
  "video_id": "uuid",
  "start_sec": 10.5,
  "end_sec": 45.2,
  "padding_sec": 3,
  "clip_storage": "nas",   // 'nas' | 'gcs' (클립 저장 위치)
  "quality": "original"    // 'original' | 'proxy'
}

Backend Logic:
1. video_id로 GCS 경로 조회
2. GCS 서명된 URL 생성 (만료: 1시간)
3. ffmpeg HTTP range request로 필요 구간만 다운로드
4. ffmpeg -c copy로 서브클립 추출
5. NAS 또는 GCS에 저장

Response 201:
{
  "clip_id": "uuid",
  "video_id": "uuid",
  "start_sec": 10.5,
  "end_sec": 45.2,
  "status": "processing",
  "estimated_time_sec": 8
}
```

### 6. 서브클립 다운로드

```http
GET /api/clips/{clip_id}/download

Response 200:
{
  "clip_id": "uuid",
  "download_url": "https://storage.googleapis.com/...",  // GCS 서명 URL
  "expires_at": "2025-01-18T11:00:00Z",
  "file_size_mb": 125.5,
  "filename": "clip_2025-01-18_10-30-00.mp4"
}
```

---

## 백엔드 서비스 구조

### 디렉토리 구조

```
backend/src/
├── api/
│   ├── videos.py           # 기존 (NAS 업로드)
│   ├── videos_gcs.py       # 🆕 GCS 영상 관리
│   └── clips.py            # 서브클립 추출 (GCS 지원 확장)
│
├── services/
│   ├── gcs/
│   │   ├── storage.py      # 🆕 GCS 파일 관리
│   │   ├── download.py     # 🆕 GCS → 로컬 다운로드
│   │   ├── upload.py       # 🆕 로컬 → GCS 업로드
│   │   ├── signed_url.py   # 🆕 서명된 URL 생성
│   │   └── metadata.py     # 🆕 GCS 파일 메타데이터
│   │
│   ├── ffmpeg/
│   │   ├── proxy.py        # 기존 (HLS 변환)
│   │   ├── subclip.py      # 확장 (GCS 지원)
│   │   ├── gcs_proxy.py    # 🆕 GCS → 프록시 렌더링
│   │   └── metadata.py     # 🆕 영상 메타데이터 추출
│   │
│   └── storage.py          # 기존 (NAS 관리)
│
├── models/
│   ├── video.py            # 확장 (gcs_* 필드 추가)
│   └── clip.py             # 확장 (gcs_clip_path 필드 추가)
│
└── config.py               # GCS 설정 추가
```

---

## 핵심 기술 스택

| 영역 | 기술 | 용도 |
|------|------|------|
| **GCS 연동** | Google Cloud Storage Python SDK | 파일 업로드/다운로드 |
| **GCS 인증** | Service Account JSON | GCS 접근 권한 |
| **메타데이터** | ffprobe | 영상 정보 추출 |
| **프록시 렌더링** | ffmpeg | GCS → HLS 변환 |
| **서브클립 추출** | ffmpeg | GCS → 무손실 추출 |
| **임시 저장** | tempfile | 추출 전 임시 다운로드 |

---

## 워크플로우 상세

### 시나리오 1: GCS 영상 추가 및 프록시 생성

```
1. 사용자: GCS 경로 입력
   POST /api/videos/gcs
   {
     "gcs_path": "gs://my-bucket/originals/video.mp4",
     "auto_proxy": true,
     "proxy_storage": "nas"
   }

2. 백엔드:
   a) GCS 파일 존재 확인
      - google.cloud.storage.Client()
      - bucket.blob(path).exists()

   b) GCS 메타데이터 조회
      - 파일 크기, 생성 시간, Content-Type

   c) 영상 메타데이터 추출
      - GCS 서명 URL 생성 (1시간 만료)
      - ffprobe로 duration, fps, 해상도 추출

   d) videos 테이블에 레코드 생성
      - source_type='gcs'
      - proxy_status='pending'

   e) 프록시 렌더링 작업 큐 등록
      - BackgroundTasks 또는 Celery

3. 프록시 렌더링 작업:
   a) GCS에서 원본 다운로드
      - 서명 URL로 스트리밍 다운로드
      - 또는 임시 파일에 저장

   b) ffmpeg HLS 변환
      ffmpeg -i "https://storage.googleapis.com/.../signed_url" \
        -vf "scale=1280:720:force_original_aspect_ratio=decrease" \
        -c:v libx264 -preset fast -crf 23 \
        -c:a aac -b:a 128k \
        -hls_time 10 -hls_list_size 0 \
        -f hls /nas/proxy/{video_id}/master.m3u8

   c) 프록시 상태 업데이트
      - proxy_status='completed'
      - proxy_path 저장

4. 프론트엔드:
   - 프록시 상태 폴링 (WebSocket 또는 polling)
   - 완료 시 HLS 플레이어 표시
```

### 시나리오 2: 서브클립 추출

```
1. 사용자: Timeline Editor에서 In/Out 지정
   - In: 00:10:00 (600초)
   - Out: 00:12:30 (750초)
   - Padding: 3초

2. 사용자: "서브클립 다운로드" 클릭
   POST /api/clips
   {
     "video_id": "uuid",
     "start_sec": 600,
     "end_sec": 750,
     "padding_sec": 3,
     "clip_storage": "nas"
   }

3. 백엔드:
   a) 타임코드 계산 (패딩 적용)
      start_sec = max(0, 600 - 3) = 597
      end_sec = min(video_duration, 750 + 3) = 753
      duration_sec = 753 - 597 = 156

   b) GCS 서명 URL 생성 (1시간 만료)

   c) ffmpeg HTTP range request로 서브클립 추출
      ffmpeg -ss 597 -to 753 \
        -i "https://storage.googleapis.com/.../signed_url" \
        -c copy \
        -avoid_negative_ts make_zero \
        -movflags +faststart \
        /nas/clips/{clip_id}.mp4

      장점: GCS에서 필요한 구간만 다운로드
      단점: 키프레임 정확도 저하 가능성

   d) 클립 파일 저장
      - NAS: /nas/clips/{clip_id}.mp4
      - 또는 GCS: gs://bucket/clips/{clip_id}.mp4

   e) clips 테이블에 레코드 생성

4. 사용자: 다운로드
   GET /api/clips/{clip_id}/download
   - NAS 저장: FastAPI FileResponse
   - GCS 저장: 서명 URL 반환
```

---

## 환경 변수 설정

### backend/.env

```bash
# GCS Configuration
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GCS_BUCKET_NAME=my-video-bucket
GCS_ORIGINALS_PREFIX=originals/
GCS_CLIPS_PREFIX=clips/
GCS_SIGNED_URL_EXPIRATION=3600  # 1시간 (초)

# GCS 프록시 저장 (선택)
GCS_PROXY_ENABLED=false
GCS_PROXY_PREFIX=proxy/

# Storage Strategy
CLIP_STORAGE_DEFAULT=nas  # 'nas' | 'gcs'
PROXY_STORAGE_DEFAULT=nas # 'nas' | 'gcs'

# 기존 설정
DATABASE_URL=postgresql://user:pass@localhost:5432/video_platform
NAS_ORIGINALS_PATH=/nas/originals
NAS_PROXY_PATH=/nas/proxy
NAS_CLIPS_PATH=/nas/clips
```

---

## GCS 접근 권한 설정

### 1. Service Account 생성

```bash
# GCP Console에서 Service Account 생성
# 또는 gcloud CLI 사용

gcloud iam service-accounts create video-platform-sa \
  --display-name="Video Platform Service Account"

# Key 생성
gcloud iam service-accounts keys create service-account.json \
  --iam-account=video-platform-sa@PROJECT_ID.iam.gserviceaccount.com
```

### 2. 버킷 권한 부여

```bash
# Storage Object Viewer (읽기)
gsutil iam ch serviceAccount:video-platform-sa@PROJECT_ID.iam.gserviceaccount.com:roles/storage.objectViewer \
  gs://my-video-bucket

# Storage Object Creator (쓰기 - 클립 업로드용)
gsutil iam ch serviceAccount:video-platform-sa@PROJECT_ID.iam.gserviceaccount.com:roles/storage.objectCreator \
  gs://my-video-bucket
```

### 3. Python 코드에서 인증

```python
from google.cloud import storage
import os

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/path/to/service-account.json'
client = storage.Client()
```

---

## 핵심 서비스 구현

### 1. GCS Storage Service

```python
# backend/src/services/gcs/storage.py
from google.cloud import storage
from datetime import timedelta
from typing import Optional

class GCSStorageService:
    def __init__(self, bucket_name: str):
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    def file_exists(self, gcs_path: str) -> bool:
        """GCS 파일 존재 확인"""
        blob = self.bucket.blob(gcs_path)
        return blob.exists()

    def get_metadata(self, gcs_path: str) -> dict:
        """GCS 파일 메타데이터 조회"""
        blob = self.bucket.blob(gcs_path)
        blob.reload()

        return {
            "size_bytes": blob.size,
            "size_mb": blob.size / (1024 * 1024),
            "content_type": blob.content_type,
            "created_at": blob.time_created,
            "updated_at": blob.updated,
            "md5_hash": blob.md5_hash
        }

    def generate_signed_url(
        self,
        gcs_path: str,
        expiration: int = 3600  # 1시간
    ) -> str:
        """서명된 URL 생성 (읽기 전용)"""
        blob = self.bucket.blob(gcs_path)

        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=expiration),
            method="GET"
        )
        return url

    def upload_file(
        self,
        source_file_path: str,
        destination_gcs_path: str
    ) -> str:
        """로컬 파일 → GCS 업로드"""
        blob = self.bucket.blob(destination_gcs_path)
        blob.upload_from_filename(source_file_path)
        return f"gs://{self.bucket.name}/{destination_gcs_path}"

    def download_file(
        self,
        gcs_path: str,
        destination_file_path: str
    ) -> None:
        """GCS → 로컬 다운로드"""
        blob = self.bucket.blob(gcs_path)
        blob.download_to_filename(destination_file_path)
```

### 2. GCS Proxy Rendering Service

```python
# backend/src/services/ffmpeg/gcs_proxy.py
import subprocess
import tempfile
from pathlib import Path
from .metadata import extract_metadata
from ..gcs.storage import GCSStorageService

class GCSProxyService:
    def __init__(self, gcs_service: GCSStorageService):
        self.gcs = gcs_service

    async def render_proxy(
        self,
        gcs_path: str,
        output_dir: Path,
        quality: str = "720p"
    ) -> Path:
        """GCS 원본 → HLS 프록시 렌더링"""

        # 1. GCS 서명 URL 생성
        signed_url = self.gcs.generate_signed_url(gcs_path, expiration=3600)

        # 2. ffmpeg HLS 변환
        resolution = self._get_resolution(quality)
        output_path = output_dir / "master.m3u8"

        cmd = [
            "ffmpeg",
            "-i", signed_url,
            "-vf", f"scale={resolution}:force_original_aspect_ratio=decrease",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-hls_time", "10",
            "-hls_list_size", "0",
            "-f", "hls",
            str(output_path)
        ]

        subprocess.run(cmd, check=True)
        return output_path

    def _get_resolution(self, quality: str) -> str:
        resolutions = {
            "480p": "854:480",
            "720p": "1280:720",
            "1080p": "1920:1080"
        }
        return resolutions.get(quality, "1280:720")
```

### 3. GCS Subclip Extraction Service

```python
# backend/src/services/ffmpeg/subclip.py (확장)
import subprocess
from pathlib import Path
from ..gcs.storage import GCSStorageService

class SubclipService:
    def __init__(self, gcs_service: GCSStorageService):
        self.gcs = gcs_service

    async def extract_from_gcs(
        self,
        gcs_path: str,
        start_sec: float,
        end_sec: float,
        output_path: Path
    ) -> Path:
        """GCS 원본에서 서브클립 추출"""

        # 1. GCS 서명 URL 생성
        signed_url = self.gcs.generate_signed_url(gcs_path, expiration=3600)

        # 2. ffmpeg HTTP range request로 추출
        cmd = [
            "ffmpeg",
            "-ss", str(start_sec),
            "-to", str(end_sec),
            "-i", signed_url,
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            "-movflags", "+faststart",
            str(output_path)
        ]

        subprocess.run(cmd, check=True)
        return output_path
```

---

## 프론트엔드 변경 사항

### 1. Video Source 선택 UI

```tsx
// UploadPage.tsx 확장
import { Tabs, Form, Input, Button, Upload, Checkbox } from 'antd';

<Tabs defaultActiveKey="nas">
  <TabPane tab="NAS 업로드" key="nas">
    <Upload.Dragger {...uploadProps} />
  </TabPane>

  <TabPane tab="GCS 영상 추가" key="gcs">
    <Form onFinish={handleGCSSubmit}>
      <Form.Item
        name="gcs_path"
        label="GCS 경로"
        rules={[{ required: true, message: 'GCS 경로를 입력하세요' }]}
      >
        <Input
          placeholder="gs://my-bucket/originals/video.mp4"
          prefix="gs://"
        />
      </Form.Item>

      <Form.Item name="auto_proxy" valuePropName="checked" initialValue={true}>
        <Checkbox>자동 프록시 생성</Checkbox>
      </Form.Item>

      <Form.Item name="proxy_storage" label="프록시 저장 위치" initialValue="nas">
        <Select>
          <Option value="nas">NAS</Option>
          <Option value="gcs">GCS</Option>
        </Select>
      </Form.Item>

      <Button type="primary" htmlType="submit" icon={<CloudUploadOutlined />}>
        GCS 영상 추가
      </Button>
    </Form>
  </TabPane>
</Tabs>
```

### 2. VideoCard (GCS 표시)

```tsx
// VideoCard.tsx
import { Badge, Tag } from 'antd';
import { CloudOutlined, HddOutlined } from '@ant-design/icons';

function VideoCard({ video }) {
  const getSourceIcon = () => {
    return video.source_type === 'gcs' ? <CloudOutlined /> : <HddOutlined />;
  };

  const getSourceColor = () => {
    return video.source_type === 'gcs' ? '#1890ff' : '#52c41a';
  };

  return (
    <Card>
      <Badge
        count={
          <Tag icon={getSourceIcon()} color={getSourceColor()}>
            {video.source_type.toUpperCase()}
          </Tag>
        }
      />

      {video.source_type === 'gcs' && (
        <Tooltip title={video.gcs_full_path}>
          <Tag icon={<CloudOutlined />} color="blue">
            {video.gcs_bucket}
          </Tag>
        </Tooltip>
      )}

      <p>{video.filename}</p>
      <p>Duration: {formatDuration(video.duration_sec)}</p>
      <p>Size: {video.file_size_mb.toFixed(1)} MB</p>
    </Card>
  );
}
```

---

## 성능 최적화

### 1. HTTP Range Request 활용

```python
# ffmpeg가 HTTP range request를 자동으로 사용
# GCS에서 필요한 바이트만 다운로드

ffmpeg -ss {start_sec} -to {end_sec} \
  -i "https://storage.googleapis.com/.../signed_url" \
  -c copy output.mp4

# 장점:
# - 전체 파일 다운로드 불필요
# - 네트워크 대역폭 절약
# - GCS egress 비용 절감

# 단점:
# - 키프레임이 정확히 start_sec에 없으면 정확도 저하
# - 해결: -ss 옵션을 -i 앞에 배치 (빠르지만 정확도 낮음)
#        또는 -i 뒤에 배치 (느리지만 정확)
```

### 2. 프록시 캐싱 전략

```python
# 프록시는 NAS에 캐싱 (기본)
# - GCS 원본은 그대로 유지
# - 프록시만 주기적으로 정리 (30일)

# 선택: 프록시도 GCS에 저장
# - 장점: NAS 용량 절약
# - 단점: GCS 비용 증가, 재생 시 네트워크 대역폭 필요
```

### 3. 서명 URL 캐싱

```python
# Redis에 서명 URL 캐싱 (TTL: 50분)
import redis
import json

cache = redis.Redis(host='localhost', port=6379)

def get_or_create_signed_url(gcs_path: str) -> str:
    cache_key = f"gcs:signed_url:{gcs_path}"
    cached = cache.get(cache_key)

    if cached:
        return json.loads(cached)["url"]

    # 새로 생성
    url = gcs_service.generate_signed_url(gcs_path, expiration=3600)

    # 캐싱 (TTL: 50분)
    cache.setex(
        cache_key,
        3000,  # 50분
        json.dumps({"url": url, "created_at": time.time()})
    )

    return url
```

---

## 비용 분석

### GCS 비용 요소

| 항목 | 가격 (아시아 리전) | 예시 |
|------|------------------|------|
| Storage (Standard) | $0.020/GB/월 | 1TB = $20/월 |
| Egress (다운로드) | $0.12/GB | 100GB 다운로드 = $12 |
| Operations (Class A) | $0.05/10,000회 | 10만 요청 = $0.50 |
| Operations (Class B) | $0.004/10,000회 | 10만 읽기 = $0.04 |

### 비용 최적화 전략

1. **HTTP Range Request 활용**
   - 전체 파일 다운로드 대신 필요 구간만
   - Egress 비용 50-90% 절감

2. **프록시는 NAS 캐싱**
   - GCS 읽기 요청 최소화
   - 반복 재생 시 비용 없음

3. **서명 URL 캐싱**
   - Class A 요청 감소 (URL 생성)
   - Redis 캐싱으로 50% 절감

4. **라이프사이클 정책**
   ```bash
   # 30일 후 Nearline으로 이동 (저장 비용 50% 절감)
   # 90일 후 Coldline으로 이동 (저장 비용 75% 절감)
   ```

---

## 마이그레이션 전략

### 1. 기존 NAS 시스템 호환성

```sql
-- videos 테이블 마이그레이션
ALTER TABLE videos
  ADD COLUMN source_type VARCHAR(20) DEFAULT 'nas',
  ADD COLUMN gcs_bucket VARCHAR(255),
  ADD COLUMN gcs_path TEXT,
  ADD COLUMN gcs_full_path TEXT,
  ADD COLUMN gcs_signed_url TEXT,
  ADD COLUMN gcs_signed_url_expires TIMESTAMP,
  ADD COLUMN proxy_gcs_path TEXT;

-- 기존 레코드는 source_type='nas'로 유지
UPDATE videos SET source_type = 'nas' WHERE source_type IS NULL;

-- clips 테이블 마이그레이션
ALTER TABLE clips
  ADD COLUMN gcs_clip_path TEXT,
  ADD COLUMN extraction_source VARCHAR(20) DEFAULT 'nas';

UPDATE clips SET extraction_source = 'nas' WHERE extraction_source IS NULL;
```

### 2. 점진적 배포 계획

**Phase 1: GCS 읽기 전용** (Week 1-2)
- GCS 파일 메타데이터 조회
- GCS 서명 URL 생성
- GCS → 프록시 렌더링 (NAS 저장)

**Phase 2: GCS 서브클립 추출** (Week 3-4)
- GCS HTTP range request
- 서브클립 NAS 저장

**Phase 3: GCS 전체 통합** (Week 5-6)
- 클립 GCS 저장 옵션
- 프록시 GCS 저장 옵션
- 성능 최적화

**Phase 4: 프로덕션 배포** (Week 7-8)
- E2E 테스트
- 비용 모니터링
- 문서화

---

## 테스트 계획

### 1. 유닛 테스트

```python
# tests/services/gcs/test_storage.py
def test_gcs_file_exists():
    gcs_service = GCSStorageService("test-bucket")
    exists = gcs_service.file_exists("originals/test.mp4")
    assert exists is True

def test_generate_signed_url():
    gcs_service = GCSStorageService("test-bucket")
    url = gcs_service.generate_signed_url("originals/test.mp4")
    assert url.startswith("https://storage.googleapis.com/")
    assert "X-Goog-Signature" in url

# tests/services/ffmpeg/test_gcs_proxy.py
@pytest.mark.slow
async def test_gcs_to_proxy():
    gcs_service = GCSStorageService("test-bucket")
    proxy_service = GCSProxyService(gcs_service)

    output_dir = Path("/tmp/proxy")
    output_dir.mkdir(exist_ok=True)

    result = await proxy_service.render_proxy(
        gcs_path="originals/test.mp4",
        output_dir=output_dir,
        quality="720p"
    )

    assert result.exists()
    assert (output_dir / "master.m3u8").exists()
```

### 2. 통합 테스트

```python
# tests/integration/test_gcs_workflow.py
def test_gcs_to_clip_workflow():
    # 1. GCS 영상 추가
    response = client.post("/api/videos/gcs", json={
        "gcs_path": "gs://test-bucket/originals/test.mp4",
        "auto_proxy": True
    })
    assert response.status_code == 201
    video = response.json()

    # 2. 프록시 상태 확인 (폴링)
    for _ in range(30):  # 최대 30초 대기
        response = client.get(f"/api/videos/{video['video_id']}/proxy/status")
        status = response.json()
        if status["proxy_status"] == "completed":
            break
        time.sleep(1)

    assert status["proxy_status"] == "completed"

    # 3. 서브클립 추출
    response = client.post("/api/clips", json={
        "video_id": video["video_id"],
        "start_sec": 10,
        "end_sec": 20,
        "clip_storage": "nas"
    })
    assert response.status_code == 201
    clip = response.json()

    # 4. 클립 다운로드
    response = client.get(f"/api/clips/{clip['clip_id']}/download")
    assert response.status_code == 200
```

---

## 보안 고려사항

### 1. Service Account 권한 최소화

```bash
# 읽기만 필요한 경우
roles/storage.objectViewer

# 클립 업로드도 필요한 경우
roles/storage.objectCreator

# ❌ 절대 부여하지 말 것
roles/storage.admin
roles/storage.objectAdmin
```

### 2. 서명 URL 만료 시간

```python
# 프록시 렌더링: 1시간 (긴 영상 고려)
signed_url = gcs.generate_signed_url(gcs_path, expiration=3600)

# 서브클립 추출: 30분 (일반적인 작업 시간)
signed_url = gcs.generate_signed_url(gcs_path, expiration=1800)

# 다운로드 URL: 5분 (즉시 다운로드)
signed_url = gcs.generate_signed_url(clip_path, expiration=300)
```

### 3. GCS 버킷 보안

```bash
# 퍼블릭 액세스 차단
gsutil iam ch -d allUsers:objectViewer gs://my-video-bucket

# CORS 설정 (프론트엔드 직접 액세스용)
gsutil cors set cors.json gs://my-video-bucket

# cors.json:
[
  {
    "origin": ["http://localhost:3000", "https://yourdomain.com"],
    "method": ["GET"],
    "responseHeader": ["Content-Type"],
    "maxAgeSeconds": 3600
  }
]
```

---

## 다음 단계 (Implementation Roadmap)

### Phase 0: 설계 검토 (현재)
- [x] 요구사항 분석
- [x] 아키텍처 설계
- [ ] PRD 업데이트
- [ ] 이해관계자 검토

### Phase 1: GCS 기본 연동 (Week 1-2)
- [ ] GCS Python SDK 설정
- [ ] Service Account 인증
- [ ] GCS 메타데이터 조회 API
- [ ] 서명 URL 생성
- [ ] videos 테이블 마이그레이션

### Phase 2: GCS 프록시 렌더링 (Week 3-4)
- [ ] GCS → HLS 변환 서비스
- [ ] 프록시 진행률 추적
- [ ] 프론트엔드 GCS 영상 추가 UI
- [ ] 프록시 상태 폴링

### Phase 3: GCS 서브클립 추출 (Week 5-6)
- [ ] HTTP range request 서브클립
- [ ] 클립 NAS/GCS 저장 선택
- [ ] 다운로드 URL 생성
- [ ] E2E 테스트

### Phase 4: 최적화 및 배포 (Week 7-8)
- [ ] 성능 최적화
- [ ] 비용 모니터링
- [ ] 문서화
- [ ] 프로덕션 배포

---

## 참고 자료

- [Google Cloud Storage Python SDK](https://cloud.google.com/storage/docs/reference/libraries#client-libraries-install-python)
- [Signed URLs for GCS](https://cloud.google.com/storage/docs/access-control/signed-urls)
- [ffmpeg HTTP Protocol](https://ffmpeg.org/ffmpeg-protocols.html#http)
- [GCS Pricing](https://cloud.google.com/storage/pricing)
- [GCS Best Practices](https://cloud.google.com/storage/docs/best-practices)

---

**검토자**: [Name]
**승인 상태**: Pending
**마지막 업데이트**: 2025-01-18
