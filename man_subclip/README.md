# 영상 Proxy & 서브클립 추출 플랫폼

원본 영상을 **Proxy로 렌더링**하고, **타임코드 구간을 미리보기**한 후, **원본 품질의 서브클립을 다운로드**하는 브라우저 기반 영상 처리 플랫폼.

## 핵심 기능 (Only 3 Functions)

1. **영상 Proxy 렌더링**: 원본 → HLS(m3u8) 자동 변환 → 브라우저 즉시 재생
2. **Proxy 기반 구간 미리보기**: In/Out 지정 → 해당 구간만 반복 재생
3. **원본 품질 서브클립 다운로드**: 원본에서 정확한 구간 추출 → 다운로드

## 기술 스택

- **Backend**: FastAPI (Python 3.11+), PostgreSQL, ffmpeg
- **Frontend**: React 18, TypeScript, Ant Design 5, hls.js
- **Storage**: NAS (원본/프록시/클립)

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- ffmpeg 5.0+
- NAS 마운트 (개발 환경: 로컬 디렉토리)

### Backend Setup

```bash
cd backend

# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일 수정 (DATABASE_URL, NAS_ORIGINAL_PATH 등)

# 데이터베이스 마이그레이션
alembic upgrade head

# 개발 서버 실행
uvicorn src.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# 패키지 설치
npm install

# 환경변수 설정
cp .env.example .env
# .env 파일 수정 (REACT_APP_API_URL 등)

# 개발 서버 실행
npm run dev
```

### Access

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 개발 가이드

자세한 개발 가이드는 `CLAUDE.md` 참조.

### 테스트 실행

```bash
# Backend
cd backend
pytest tests/ -v --cov=src

# Frontend
cd frontend
npm test
npm run test:e2e  # Playwright E2E
```

## 프로젝트 구조

```
man_subclip/
├── backend/          # FastAPI 백엔드
├── frontend/         # React 프론트엔드
├── docs/             # 문서 (PRD 등)
├── tasks/            # Task Lists
├── CLAUDE.md         # 개발 가이드
└── README.md         # 이 파일
```

## 문서

- [PRD](docs/prd.md): 제품 요구사항 명세서
- [CLAUDE.md](CLAUDE.md): 개발자 가이드
- [Task List](tasks/0001-tasks-proxy-subclip-platform.md): 개발 Task 목록

## 라이선스

Internal Project - GG PRODUCTION

## 연락처

프로젝트 관련 문의: [담당자 이메일]
