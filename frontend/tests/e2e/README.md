# Playwright E2E Tests for GCS Clip Creation

## Overview

이 디렉토리에는 Issue #6 (GCS 인증 오류 해결) 검증을 위한 Playwright E2E 테스트가 포함되어 있습니다.

## Test Scenarios

### 1. GCS Clip Creation Workflow (`gcs-clip-creation.spec.ts`)

#### Test 1: should successfully create clip from GCS video
- GCS Videos 페이지 접속
- GCS 영상 목록 로드 확인 (인증 성공 여부)
- 영상 카드에서 "Create Clip" 버튼 클릭
- 타임코드 입력 (Start: 0, End: 10)
- 클립 생성 요청 (method: "streaming")
- 클립 생성 성공 확인
- "Download Clip" 버튼 활성화 확인

#### Test 2: should handle invalid timecode gracefully
- 잘못된 타임코드 입력 (End < Start)
- 에러 메시지 표시 확인

#### Test 3: should display GCS videos when authentication is successful
- GCS Videos 페이지 로드 확인
- 영상 목록 또는 에러 메시지 표시 확인

## Prerequisites

### 1. Backend Server Running
```bash
cd backend
uvicorn src.main:app --reload --port 8001
```

### 2. Frontend Dev Server Running
```bash
cd frontend
npm run dev
```

## Known Issues

### Issue: Vite HMR Error in Playwright Tests

**Problem:**
Playwright 테스트 실행 시 Vite의 HMR (Hot Module Replacement) 에러가 발생합니다:
```
Failed to resolve import "@/api/client" from "src/pages/GCSVideosPage.tsx"
```

**Cause:**
- Vite 개발 서버의 HMR 상태와 Playwright 브라우저 인스턴스 간의 동기화 문제
- 경로 별칭 (`@/*`) 해석 타이밍 이슈

**Workaround Solutions:**

#### Solution 1: Restart Frontend Dev Server
```bash
# 프론트엔드 개발 서버 종료 후 재시작
cd frontend
npm run dev
```

#### Solution 2: Clear Vite Cache
```bash
cd frontend
rm -rf node_modules/.vite
npm run dev
```

#### Solution 3: Test Against Production Build
```bash
# 프론트엔드 빌드
cd frontend
npm run build
npm run preview  # Port 4173

# Playwright 설정에서 baseURL 변경
# playwright.config.ts:
# baseURL: 'http://localhost:4173'
```

#### Solution 4: Use Headless Mode with Longer Wait
Vite의 모듈 로딩을 위해 더 긴 대기 시간 사용:
```typescript
await page.goto('http://localhost:8003/gcs-videos', {
  waitUntil: 'networkidle',
  timeout: 60000
});
await page.waitForTimeout(5000); // Vite HMR 안정화 대기
```

## Running Tests

### Development (Headed Mode with Slowdown)
```bash
cd frontend
npm run test:e2e:headed
```

### CI/CD (Headless Mode)
```bash
npm run test:e2e
```

### With UI Mode (Interactive Debugging)
```bash
npm run test:e2e:ui
```

### View HTML Report
```bash
npm run test:e2e:report
```

## Test Configuration

### Playwright Config (`playwright.config.ts`)
- **Test Directory:** `./tests/e2e`
- **Timeout:** 60 seconds per test
- **Workers:** 1 (sequential execution to avoid GCS API rate limiting)
- **Retries:** 0 (dev), 2 (CI)
- **Browsers:** Chromium (headed mode with 500ms slowMo for debugging)
- **Screenshots:** On failure only
- **Video:** On failure only
- **Trace:** On failure only

### Browser Settings
- **Viewport:** 1920x1080
- **Headless:** false (for development)
- **SlowMo:** 500ms (for debugging)

## Debugging Failed Tests

### 1. View Screenshots
```bash
ls frontend/test-results/**/test-failed-*.png
```

### 2. Watch Video Recording
```bash
ls frontend/test-results/**/*.webm
```

### 3. Inspect Trace
```bash
npx playwright show-trace frontend/test-results/**/trace.zip
```

## Best Practices

1. **Always restart dev server before running E2E tests** to ensure clean HMR state
2. **Run tests sequentially** to avoid GCS API throttling
3. **Use explicit waits** instead of arbitrary timeouts when possible
4. **Check backend health** before running tests:
   ```bash
   curl http://127.0.0.1:8001/health
   ```
5. **Monitor console logs** for API errors during test execution

## Manual Verification

브라우저에서 직접 확인하려면:
1. http://localhost:8003/gcs-videos 접속
2. GCS 영상 목록이 표시되는지 확인 (인증 성공)
3. 영상 카드에서 "Create Clip" 버튼 클릭
4. 타임코드 입력 후 클립 생성
5. "Download Clip" 버튼으로 다운로드

## References

- [Playwright Documentation](https://playwright.dev/docs/intro)
- [Vite HMR API](https://vitejs.dev/guide/api-hmr.html)
- Issue #6: GCS 인증 오류 해결
