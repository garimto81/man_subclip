# 🎬 man_subclip - 영상 Proxy & 서브클립 플랫폼

> GGProduction 영상 처리 생태계의 **최종 서브클립 추출 도구** (qwen_hand_analysis → archive-mam → **man_subclip**)

원본 영상을 **HLS Proxy로 렌더링**하고, **타임코드 구간을 미리보기**한 후, **원본 품질 서브클립을 다운로드**하는 브라우저 기반 플랫폼

## 🌐 생태계 연결 구조

이 프로젝트는 **3개 연결된 프로젝트의 마지막 단계**입니다:

```
0. qwen_hand_analysis  → AI 포커 분석 (Gemini API)
       ↓ (Firestore: 핸드 데이터 + 타임스탬프)
1. archive-mam         → 검색 시스템 (Vertex AI)
       ↓ (검색 결과: video_id + 타임코드)
2. man_subclip ⭐      → 서브클립 추출 (현재)
       ↓ (최종 서브클립)
   [학습자/편집자]
```

**통합 워크플로우**:
1. **qwen_hand_analysis**: 영상 업로드 → Gemini AI 분석 → 핸드 데이터 저장
2. **archive-mam**: "junglemann hero call" 검색 → Hand #42 발견 (타임코드 포함)
3. **man_subclip**: 타임코드 자동 로드 → 미리보기 → 서브클립 다운로드

**효율성**: 검색부터 서브클립까지 **10분** (전통 방식: 5시간+)

---

## ✨ 핵심 기능 (Only 3)

1. **HLS Proxy 렌더링** - 원본 → 브라우저 재생 가능한 HLS
2. **타임코드 미리보기** - In/Out 지정 후 Proxy로 구간 반복 재생
3. **원본 품질 다운로드** - 지정 구간을 원본에서 추출 (무손실)

## 🚀 빠른 시작

### 백엔드 실행
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

### 프론트엔드 실행
```bash
cd frontend
npm install
npm run dev  # http://localhost:3000
```

## 📊 현재 상태 (v4.0.0)

- ✅ **백엔드**: 100% 완료 (FastAPI + SQLite + ffmpeg)
- ⚠️ **프론트엔드**: 40% 완료 (기본 UI만, 핵심 기능 누락)

**남은 작업**: Video.js 플레이어, Timeline 편집기, 타임코드 포맷, 구간 미리보기 Loop (2-3일 소요)

## 📚 문서 구조

**사용자용**:
- **README.md** (이 파일) - 빠른 시작 + 생태계 개요

**개발자/AI용**:
- **CLAUDE.md** - 개발 가이드 (아키텍처, API, 생태계 상세)
- **tasks/prd.md** - PRD v4.0 (요구사항, 구현 상태)

## 🛠️ 기술 스택

- **Backend**: FastAPI + SQLite + ffmpeg
- **Frontend**: React 18 + TypeScript + Ant Design
- **Video**: HLS (m3u8) + Video.js
- **Storage**: NAS (original/proxy/clips)

## 📁 프로젝트 구조

```
man_subclip/
├── backend/          # FastAPI (✅ 100% 완료)
│   ├── src/api/      # REST API
│   ├── src/services/ # ffmpeg 처리
│   └── tests/        # 1:1 테스트
├── frontend/         # React (⚠️ 40% 완료)
│   ├── src/pages/    # 페이지
│   └── src/api/      # API 클라이언트
├── docs/prd.md       # PRD v4.0
└── CLAUDE.md         # 개발자 가이드
```

## 🎯 다음 단계

1. Video.js HLS 플레이어 구현 (4시간)
2. Timeline Editor 구현 (6시간)
3. 타임코드 포맷 구현 (2시간)
4. 구간 미리보기 Loop 구현 (4시간)
5. E2E 테스트 작성 (4시간)

**상세 구현 계획**: `tasks/prd.md` Section 13 참고

---

**프로젝트 원칙**: "Only 3 Functions" - Proxy 렌더링, 구간 미리보기, 원본 다운로드만 구현
