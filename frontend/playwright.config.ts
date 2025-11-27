import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright 설정
 * E2E 테스트를 위한 브라우저 자동화 설정
 *
 * See https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  // 테스트 파일 위치
  testDir: './tests/e2e',

  // 각 테스트의 최대 실행 시간 (60초)
  timeout: 60 * 1000,

  // 각 expect 단언문의 최대 대기 시간 (10초)
  expect: {
    timeout: 10000,
  },

  // 테스트 실행 설정
  fullyParallel: false, // 순차 실행 (GCS API 부하 방지)
  forbidOnly: !!process.env.CI, // CI에서는 test.only 금지
  retries: process.env.CI ? 2 : 0, // CI에서는 2회 재시도
  workers: 1, // 동시 실행 워커 수 (1개로 제한)

  // 리포터 설정
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['list'],
    ['json', { outputFile: 'test-results/results.json' }],
  ],

  // 브라우저 설정
  use: {
    // 기본 URL (모든 테스트에서 사용)
    baseURL: 'http://localhost:8003',

    // 실패 시 스크린샷 캡처
    screenshot: 'only-on-failure',

    // 실패 시 비디오 녹화
    video: 'retain-on-failure',

    // 실패 시 트레이스 저장
    trace: 'retain-on-failure',

    // 브라우저 컨텍스트 설정
    viewport: { width: 1920, height: 1080 },
    ignoreHTTPSErrors: true,

    // 네트워크 로깅
    extraHTTPHeaders: {
      'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    },
  },

  // 테스트 프로젝트 설정 (브라우저별)
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // 헤드리스 모드 비활성화 (개발 중 디버깅 용이)
        headless: false,
        // 느린 속도 (디버깅 시 동작 확인)
        slowMo: 500,
      },
    },

    // Firefox 테스트 (필요 시 활성화)
    // {
    //   name: 'firefox',
    //   use: {
    //     ...devices['Desktop Firefox'],
    //     headless: false,
    //   },
    // },

    // WebKit 테스트 (필요 시 활성화)
    // {
    //   name: 'webkit',
    //   use: {
    //     ...devices['Desktop Safari'],
    //     headless: false,
    //   },
    // },

    // 모바일 브라우저 테스트 (필요 시 활성화)
    // {
    //   name: 'Mobile Chrome',
    //   use: {
    //     ...devices['Pixel 5'],
    //   },
    // },
  ],

  // 웹 서버 설정 (자동으로 개발 서버 시작/종료)
  // 주의: 이미 서버가 실행 중이므로 주석 처리
  // webServer: {
  //   command: 'npm run dev',
  //   url: 'http://localhost:8003',
  //   reuseExistingServer: !process.env.CI,
  //   timeout: 120 * 1000,
  // },
});
