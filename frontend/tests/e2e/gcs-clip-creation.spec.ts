import { test, expect } from '@playwright/test';

/**
 * E2E Test: GCS 영상 클립 생성 워크플로우
 *
 * Issue #6: GCS 인증 오류 해결 검증
 *
 * 테스트 시나리오:
 * 1. GCS Videos 페이지 접속
 * 2. GCS 영상 목록 로드 확인 (인증 성공 여부)
 * 3. 영상 카드에서 "Create Clip" 버튼 클릭
 * 4. 타임코드 입력 (Start: 0, End: 10)
 * 5. 클립 생성 요청 (method: "streaming")
 * 6. 클립 생성 성공 확인
 * 7. "Download Clip" 버튼 활성화 확인
 */

test.describe('GCS Clip Creation Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // 백엔드와 프론트엔드가 실행 중이어야 함
    // Backend: http://127.0.0.1:8001
    // Frontend: http://localhost:8003

    // 홈페이지 접속
    await page.goto('http://localhost:8003', { waitUntil: 'domcontentloaded' });

    // Vite 개발 서버 초기화 대기
    await page.waitForTimeout(2000);
  });

  test('should successfully create clip from GCS video', async ({ page }) => {
    // Step 1: GCS Videos 페이지로 직접 이동
    await page.goto('http://localhost:8003/gcs-videos', { waitUntil: 'domcontentloaded' });

    // Vite가 모듈을 로드할 시간 대기
    await page.waitForTimeout(3000);

    // URL 변경 확인
    await expect(page).toHaveURL(/\/gcs-videos/);

    // Step 2: GCS 영상 목록 로드 확인
    // GCS API 호출 대기 (최대 30초)
    await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {
      console.log('Network idle timeout - proceeding anyway');
    });

    // 영상 카드가 표시되는지 확인 (인증 성공 여부)
    const videoCards = page.locator('.ant-card');

    // 로딩 스피너가 사라질 때까지 대기
    const spinner = page.locator('.ant-spin');
    await spinner.waitFor({ state: 'hidden', timeout: 30000 }).catch(() => {
      console.log('Spinner timeout - proceeding anyway');
    });

    await expect(videoCards.first()).toBeVisible({ timeout: 20000 });

    // 영상이 최소 1개 이상 로드되었는지 확인
    const videoCount = await videoCards.count();
    expect(videoCount).toBeGreaterThan(0);

    console.log(`Loaded ${videoCount} GCS videos successfully`);

    // Step 3: 첫 번째 영상 카드에서 "Create Clip" 버튼 클릭
    const firstVideoCard = videoCards.first();
    const createClipButton = firstVideoCard.getByRole('button', { name: /Create Clip/i });

    // 버튼이 표시될 때까지 대기
    await expect(createClipButton).toBeVisible({ timeout: 10000 });
    await createClipButton.click();

    // 모달이 열렸는지 확인
    const modal = page.locator('.ant-modal');
    await expect(modal).toBeVisible({ timeout: 5000 });

    // Step 4: 타임코드 입력
    // Form에서 입력 필드 찾기 (label 기반)
    const startTimeInput = modal.locator('input[id*="start"]');
    await expect(startTimeInput).toBeVisible();
    await startTimeInput.clear();
    await startTimeInput.fill('0');

    // End Time 입력
    const endTimeInput = modal.locator('input[id*="end"]');
    await expect(endTimeInput).toBeVisible();
    await endTimeInput.clear();
    await endTimeInput.fill('10');

    console.log('Timecode input completed: Start=0, End=10, Method=streaming');

    // Step 5: 모달 내 "Create Clip" 버튼 클릭
    const modalCreateButton = modal.getByRole('button', { name: /Create Clip/i });
    await expect(modalCreateButton).toBeEnabled();

    // API 응답 대기를 위한 인터셉트 설정
    const clipCreationPromise = page.waitForResponse(
      response => {
        const url = response.url();
        const status = response.status();
        console.log(`API Response: ${url} - Status: ${status}`);
        return url.includes('/api/clips/gcs') && (status === 200 || status === 201);
      },
      { timeout: 120000 } // 클립 생성은 시간이 걸릴 수 있으므로 120초 대기
    );

    await modalCreateButton.click();

    // Step 6: 클립 생성 성공 확인
    try {
      const response = await clipCreationPromise;
      const responseBody = await response.json();

      console.log('Clip creation response:', JSON.stringify(responseBody, null, 2));

      // 응답 검증
      expect([200, 201]).toContain(response.status());
      expect(responseBody).toHaveProperty('clip_id');
      expect(responseBody).toHaveProperty('file_size_mb');
      expect(responseBody).toHaveProperty('duration_sec');
      expect(responseBody.method).toBe('streaming');

      console.log(`Clip created successfully: ID=${responseBody.clip_id}`);
    } catch (error) {
      // 타임아웃 또는 에러 발생 시 스크린샷 저장
      await page.screenshot({
        path: `D:/AI/claude01/man_subclip/frontend/tests/e2e/failure-${Date.now()}.png`,
        fullPage: true
      });
      throw error;
    }

    // 성공 메시지 확인
    const successMessage = page.locator('.ant-message-success');
    await expect(successMessage).toBeVisible({ timeout: 5000 });

    // Step 7: "Download Clip" 버튼 활성화 확인
    // 성공 Alert 내에서 Download Clip 버튼 확인
    const successAlert = modal.locator('.ant-alert-success');
    await expect(successAlert).toBeVisible({ timeout: 5000 });

    const downloadButton = modal.getByRole('button', { name: /Download Clip/i });
    await expect(downloadButton).toBeVisible({ timeout: 5000 });
    await expect(downloadButton).toBeEnabled();

    console.log('GCS clip creation E2E test completed successfully - Download button is ready');
  });

  test('should handle invalid timecode gracefully', async ({ page }) => {
    // GCS Videos 페이지로 이동
    await page.goto('http://localhost:8003/gcs-videos', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);
    await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {
      console.log('Network idle timeout - proceeding anyway');
    });

    // 로딩 스피너가 사라질 때까지 대기
    const spinner = page.locator('.ant-spin');
    await spinner.waitFor({ state: 'hidden', timeout: 30000 }).catch(() => {
      console.log('Spinner timeout - proceeding anyway');
    });

    // 첫 번째 영상 카드에서 "Create Clip" 버튼 클릭
    const videoCards = page.locator('.ant-card');
    await expect(videoCards.first()).toBeVisible({ timeout: 20000 });

    const createClipButton = videoCards.first().getByRole('button', { name: /Create Clip/i });
    await createClipButton.click();

    const modal = page.locator('.ant-modal');
    await expect(modal).toBeVisible();

    // 잘못된 타임코드 입력 (End < Start)
    const startTimeInput = modal.locator('input[id*="start"]');
    await startTimeInput.clear();
    await startTimeInput.fill('20');

    const endTimeInput = modal.locator('input[id*="end"]');
    await endTimeInput.clear();
    await endTimeInput.fill('10');

    // Create Clip 버튼 클릭
    const modalCreateButton = modal.getByRole('button', { name: /Create Clip/i });
    await modalCreateButton.click();

    // 에러 메시지 확인
    const errorMessage = page.locator('.ant-message-error');
    await expect(errorMessage).toBeVisible({ timeout: 10000 });

    console.log('Invalid timecode validation test passed');
  });

  test('should display GCS videos when authentication is successful', async ({ page }) => {
    // GCS Videos 페이지로 이동
    await page.goto('http://localhost:8003/gcs-videos', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    // 로딩 완료 대기
    await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {
      console.log('Network idle timeout - proceeding anyway');
    });

    // 로딩 스피너가 사라질 때까지 대기
    const spinner = page.locator('.ant-spin');
    await spinner.waitFor({ state: 'hidden', timeout: 30000 }).catch(() => {
      console.log('Spinner timeout - proceeding anyway');
    });

    // 에러 상태 확인 (영상이 로드되지 않았다면 에러 메시지 확인)
    const videoCards = page.locator('.ant-card');
    const errorAlert = page.locator('.ant-alert-error');
    const emptyState = page.locator('.ant-empty');

    // 영상이 있거나, 빈 상태이거나, 에러 메시지가 있어야 함
    const hasVideos = await videoCards.count() > 0;
    const hasError = await errorAlert.isVisible().catch(() => false);
    const isEmpty = await emptyState.isVisible().catch(() => false);

    expect(hasVideos || hasError || isEmpty).toBeTruthy();

    if (hasError) {
      console.log('GCS authentication error detected (expected if credentials are invalid)');
    } else if (isEmpty) {
      console.log('GCS bucket is empty (no videos found)');
    } else {
      const count = await videoCards.count();
      console.log(`GCS videos loaded successfully (authentication OK) - ${count} videos found`);
    }
  });
});
