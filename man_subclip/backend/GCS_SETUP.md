# GCS (Google Cloud Storage) 설정 가이드

## ✅ 설정 완료

man_subclip 프로젝트에서 qwen_hand_analysis의 GCS 버킷(`wsop-archive-raw`)에 접근 가능합니다.

---

## 📊 현재 구성

### Service Account

- **Email**: `poker-video-analyzer@gg-poker-prod.iam.gserviceaccount.com`
- **Project**: `gg-poker-prod`
- **권한**: Storage Object Viewer (읽기 전용)

### GCS 버킷

- **Bucket**: `gs://wsop-archive-raw`
- **영상 파일**: 5개 확인 (Archive-MAM_Sample.mp4, WSOP 2025 등)
- **다운로드 테스트**: ✅ 성공 (1.5GB 파일)

---

## 🔧 파일 구조

```
man_subclip/
├── backend/
│   ├── secrets/
│   │   └── gcs-key.json           # Service Account 키 (✅ .gitignore)
│   ├── src/
│   │   ├── config.py              # GCS 설정
│   │   └── services/
│   │       └── gcs_client.py      # GCS 클라이언트 (✅ 완료)
│   └── scripts/
│       └── test_gcs_download.py   # 테스트 스크립트
└── .gitignore                     # secrets/ 제외 (✅ 완료)
```

---

## 🚀 사용 방법

### 1. GCS 접근 확인

```python
from src.services.gcs_client import check_gcs_access

if check_gcs_access():
    print("GCS 접근 가능")
else:
    print("GCS 접근 실패")
```

### 2. 영상 목록 조회

```python
from src.services.gcs_client import list_gcs_videos

# 전체 영상 목록
videos = list_gcs_videos()

# 특정 경로만
videos_2025 = list_gcs_videos(prefix="2025/")

print(f"Found {len(videos)} videos")
for video in videos:
    print(f"  - {video}")
```

### 3. 영상 다운로드

```python
from src.services.gcs_client import download_video_from_gcs

# GCS에서 로컬로 다운로드
gcs_path = "Archive-MAM_Sample.mp4"
local_path = download_video_from_gcs(gcs_path)

print(f"Downloaded to: {local_path}")
# 출력: Downloaded to: /tmp/Archive-MAM_Sample.mp4
```

### 4. 서브클립 추출 워크플로우

```python
from src.services.gcs_client import download_video_from_gcs
from src.services.ffmpeg.subclip import create_subclip

# 1. GCS에서 원본 다운로드
gcs_path = "2025/day5/table3.mp4"
local_original = download_video_from_gcs(gcs_path)

# 2. 서브클립 추출 (archive-mam에서 받은 타임코드)
clip_path = create_subclip(
    input_path=local_original,
    start_sec=7234.5,  # archive-mam 검색 결과
    end_sec=7398.2,
    output_path="/nas/clips/hand_042.mp4",
    padding_sec=3.0
)

# 3. 원본 파일 정리
os.remove(local_original)

print(f"Subclip created: {clip_path}")
```

---

## 🔒 보안

### .gitignore 설정

```gitignore
# Secrets (GCS Service Account keys)
backend/secrets/
*.json
!package.json
!package-lock.json
!tsconfig.json
!vite.config.json
```

### Service Account 권한

- **현재**: `Storage Object Viewer` (읽기 전용)
- **추천**: 최소 권한 원칙 유지
- **변경 금지**: Service Account 키는 절대 커밋하지 말 것

---

## 📝 환경 변수 (.env)

```bash
# GCS 설정 (선택 - 기본값 사용 가능)
GCS_PROJECT_ID=gg-poker-prod
GCS_BUCKET_NAME=wsop-archive-raw
GCS_CREDENTIALS_PATH=secrets/gcs-key.json
USE_GCS=True
```

---

## 🧪 테스트

### 1. GCS 접근 테스트

```bash
cd backend
python -m src.services.gcs_client
```

**예상 출력**:
```
Testing GCS access...
[OK] GCS access OK: gs://wsop-archive-raw

Listing videos in bucket...
Found 5 videos:
  - Archive-MAM_Sample.mp4
  - WSOP 2025 Main Event _ Day 1A.mp4
  ...
```

### 2. 다운로드 테스트

```bash
cd backend
python scripts/test_gcs_download.py
```

**예상 출력**:
```
============================================================
GCS Download Test
============================================================

[Step 1] Checking GCS access...
[OK] GCS access OK: gs://wsop-archive-raw

[Step 2] Listing videos in bucket...
Found 5 videos:
  1. Archive-MAM_Sample.mp4
  ...

[Step 3] Downloading test video: Archive-MAM_Sample.mp4
[OK] Downloaded to: /tmp/Archive-MAM_Sample.mp4
[OK] File size: 1496.13 MB
[OK] GCS URI: gs://wsop-archive-raw/Archive-MAM_Sample.mp4

============================================================
GCS Download Test: SUCCESS
============================================================
```

---

## 🌐 생태계 통합 (qwen_hand_analysis → man_subclip)

### 데이터 흐름

```
[qwen_hand_analysis]
   - 영상 업로드: GCS (gs://wsop-archive-raw/2025/...)
   - Firestore 저장: video_id, gcs_uri, timestamps
        ↓
[archive-mam]
   - 검색: "junglemann hero call"
   - 결과: video_id + timestamps (7234.5~7398.2)
        ↓
[man_subclip] ⭐
   - GCS 다운로드: download_video_from_gcs(gcs_path)
   - 서브클립 추출: create_subclip(start, end)
   - 다운로드 제공: /api/clips/{clip_id}/download
```

### API 통합 (예정)

```python
# man_subclip API: archive-mam에서 호출
@router.post("/api/clips/create-from-search")
async def create_clip_from_search(
    video_id: str,
    gcs_path: str,      # qwen_hand_analysis가 저장한 GCS 경로
    start_sec: float,   # archive-mam 검색 결과
    end_sec: float,
    hand_id: str        # 메타데이터용
):
    # 1. GCS에서 원본 다운로드
    local_path = download_video_from_gcs(gcs_path)

    # 2. 서브클립 추출
    clip = create_subclip(local_path, start_sec, end_sec)

    # 3. 다운로드 URL 반환
    return {"clip_id": clip.id, "download_url": clip.url}
```

---

## ⚠️ 문제 해결

### 문제 1: Service Account 키 파일 없음

**증상**:
```
[ERROR] GCS access failed: [Errno 2] No such file or directory: 'secrets/gcs-key.json'
```

**해결**:
```bash
# 1. secrets/ 디렉토리 확인
ls -la backend/secrets/

# 2. 키 파일 존재 확인
cat backend/secrets/gcs-key.json | head -5

# 3. 키 파일 권한 확인
chmod 600 backend/secrets/gcs-key.json
```

### 문제 2: 권한 부족

**증상**:
```
[ERROR] GCS access failed: 403 Forbidden
```

**해결**:
1. Service Account에 `Storage Object Viewer` 역할 부여:
   ```bash
   gsutil iam ch \
     serviceAccount:poker-video-analyzer@gg-poker-prod.iam.gserviceaccount.com:objectViewer \
     gs://wsop-archive-raw
   ```

2. 또는 GCP Console에서:
   - GCS 버킷 → Permissions → Add Member
   - Member: `poker-video-analyzer@gg-poker-prod.iam.gserviceaccount.com`
   - Role: `Storage Object Viewer`

### 문제 3: 버킷 이름 오류

**증상**:
```
[ERROR] Bucket does not exist: wsop-archive-raw
```

**해결**:
```bash
# 버킷 목록 확인
gsutil ls

# 올바른 버킷 이름 확인
gsutil ls -p gg-poker-prod

# config.py 업데이트
# gcs_bucket_name: str = "실제-버킷-이름"
```

---

## 📊 성능

- **GCS 다운로드 속도**: ~150MB/s (내부망)
- **1.5GB 영상 다운로드**: ~10초
- **5분 영상 서브클립 추출**: ~5초 (코덱 복사)
- **총 처리 시간**: ~15초 (다운로드 + 추출)

---

## 🎯 다음 단계

- [ ] API 엔드포인트 추가: `/api/clips/create-from-gcs`
- [ ] archive-mam 연동: 검색 결과 → 서브클립 자동 생성
- [ ] 캐싱 전략: 자주 사용되는 원본 영상 로컬 캐싱
- [ ] 배치 처리: 여러 서브클립 동시 추출

---

**마지막 업데이트**: 2025-01-20
**테스트 상태**: ✅ 모두 성공
