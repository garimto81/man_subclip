# 로컬 개발 환경 실행 가이드 (Docker 없이)

## 개요

Docker 없이 로컬에서 백엔드와 프론트엔드를 실행하는 방법입니다.

## 사전 요구사항

- Python 3.11+
- Node.js 20+
- ffmpeg (시스템에 설치 필요)
- (선택) PostgreSQL 15+ 또는 SQLite 사용

---

## 1. 백엔드 실행

### Option A: SQLite 사용 (빠른 테스트)

```bash
cd backend

# 가상환경 생성 (선택사항)
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정 (SQLite)
# backend/.env 파일 수정
DATABASE_URL=sqlite:///./video_platform.db
NAS_ORIGINALS_PATH=./nas/originals
NAS_PROXY_PATH=./nas/proxy
NAS_CLIPS_PATH=./nas/clips
ALLOWED_ORIGINS=http://localhost:3000

# NAS 디렉토리 생성
mkdir -p nas/originals nas/proxy nas/clips

# 서버 실행
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**결과**:
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Redoc: http://localhost:8000/redoc

### Option B: PostgreSQL 사용 (프로덕션과 동일)

```bash
# PostgreSQL 설치 및 실행
# Windows: https://www.postgresql.org/download/windows/
# Mac: brew install postgresql
# Linux: sudo apt-get install postgresql

# 데이터베이스 생성
psql -U postgres
CREATE DATABASE video_platform;
CREATE USER video_user WITH PASSWORD 'video_password';
GRANT ALL PRIVILEGES ON DATABASE video_platform TO video_user;
\q

# backend/.env 파일 수정
DATABASE_URL=postgresql://video_user:video_password@localhost:5432/video_platform

# 테이블 생성 (Alembic 또는 자동 생성)
# src/main.py에서 Base.metadata.create_all(bind=engine) 실행됨

# 서버 실행
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 2. 프론트엔드 실행

```bash
cd frontend

# 의존성 설치
npm install

# 환경 변수 설정
# frontend/.env 파일 확인
VITE_API_BASE_URL=http://localhost:8000

# 개발 서버 실행
npm run dev
```

**결과**:
- Frontend: http://localhost:3000 (또는 Vite가 지정한 포트)

---

## 3. 통합 테스트

### 3.1 백엔드 API 테스트

브라우저에서 http://localhost:8000/docs 접속하여 Swagger UI에서 테스트:

1. **POST /videos/upload** - 비디오 업로드
   - 테스트 파일: 작은 MP4 파일 업로드
   - 응답: video_id, filename, proxy_status

2. **GET /videos** - 비디오 목록 조회
   - 응답: 업로드한 비디오 목록

3. **POST /videos/{video_id}/proxy/start** - Proxy 렌더링 시작
   - 주의: ffmpeg 설치 필요, 시간 소요

4. **POST /clips** - 서브클립 추출
   - body: `{"video_id": "...", "start_sec": 0, "end_sec": 10, "padding_sec": 0}`

### 3.2 프론트엔드 테스트

브라우저에서 http://localhost:3000 접속:

1. **Upload Page** (/) - 비디오 업로드 테스트
   - 드래그 앤 드롭 또는 파일 선택
   - 진행률 확인
   - 업로드 성공 후 자동 리다이렉트

2. **Library Page** (/library) - 비디오 목록
   - 업로드한 비디오 카드 확인
   - 검색 기능 테스트
   - Proxy 상태 필터 테스트

3. **Player Page** (/video/:videoId) - 비디오 재생 및 클립 추출
   - 비디오 메타데이터 확인
   - Proxy 렌더링 시작 버튼
   - 클립 추출 폼 (시작/종료 시간, 패딩)

### 3.3 E2E 워크플로우 테스트

1. 비디오 업로드
2. 비디오 라이브러리에서 확인
3. 비디오 플레이어로 이동
4. Proxy 렌더링 시작 (백그라운드)
5. Proxy 완료 대기
6. 서브클립 추출
7. 추출된 클립 확인

---

## 4. 트러블슈팅

### Backend 포트 충돌

```bash
# 포트 변경
uvicorn src.main:app --reload --port 8001

# frontend/.env도 업데이트
VITE_API_BASE_URL=http://localhost:8001
```

### ffmpeg 없음 오류

**Windows**:
```bash
# Chocolatey 사용
choco install ffmpeg

# 또는 수동 다운로드
# https://www.gyan.dev/ffmpeg/builds/
# PATH에 ffmpeg.exe 추가
```

**Mac**:
```bash
brew install ffmpeg
```

**Linux**:
```bash
sudo apt-get install ffmpeg
```

### 데이터베이스 초기화

```bash
# SQLite
rm backend/video_platform.db
# 서버 재시작하면 자동 생성

# PostgreSQL
psql -U postgres
DROP DATABASE video_platform;
CREATE DATABASE video_platform;
GRANT ALL PRIVILEGES ON DATABASE video_platform TO video_user;
\q
```

### CORS 오류

backend/.env 확인:
```
ALLOWED_ORIGINS=http://localhost:3000
```

frontend 개발 서버 포트와 일치해야 함.

---

## 5. 성능 확인

### API 응답 시간

```bash
# cURL로 테스트
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/videos

# curl-format.txt 내용:
time_namelookup:  %{time_namelookup}\n
time_connect:  %{time_connect}\n
time_appconnect:  %{time_appconnect}\n
time_pretransfer:  %{time_pretransfer}\n
time_redirect:  %{time_redirect}\n
time_starttransfer:  %{time_starttransfer}\n
----------\n
time_total:  %{time_total}\n
```

### Frontend 빌드 성능

```bash
cd frontend
npm run build

# 빌드 결과 확인
ls -lh dist/
```

---

## 6. 정리

### 개발 서버 중지

```bash
# 터미널에서 Ctrl+C

# 프로세스 강제 종료 (Windows)
taskkill /F /IM python.exe
taskkill /F /IM node.exe

# 프로세스 강제 종료 (Linux/Mac)
pkill -f uvicorn
pkill -f vite
```

### 데이터 정리

```bash
# 테스트 파일 삭제
rm -rf backend/nas/*
rm backend/video_platform.db  # SQLite인 경우
```

---

## 요약

| 서비스 | URL | 포트 |
|--------|-----|------|
| Backend API | http://localhost:8000 | 8000 |
| API Docs | http://localhost:8000/docs | 8000 |
| Frontend | http://localhost:3000 | 3000 |

**개발 순서**:
1. Backend 실행 → http://localhost:8000/docs에서 API 테스트
2. Frontend 실행 → http://localhost:3000에서 UI 테스트
3. 통합 테스트 → 업로드 → 라이브러리 → 플레이어 → 클립 추출
