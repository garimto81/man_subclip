# E2E Testing Guide

## Overview

This document describes the E2E testing strategy for the Video Proxy & Subclip Platform using Playwright.

## Setup

```bash
# Install Playwright
npm install -D @playwright/test

# Install browsers
npx playwright install
```

## Test Scenarios

### 1. Video Upload Flow

```typescript
// tests/e2e/upload.spec.ts
import { test, expect } from '@playwright/test'

test('upload video successfully', async ({ page }) => {
  // Navigate to upload page
  await page.goto('http://localhost:3000/upload')

  // Upload file
  const fileInput = page.locator('input[type="file"]')
  await fileInput.setInputFiles('test-assets/sample.mp4')

  // Wait for upload completion
  await expect(page.locator('text=Upload Successful')).toBeVisible()

  // Verify redirect to library
  await page.waitForURL('http://localhost:3000/')
  await expect(page.locator('text=sample.mp4')).toBeVisible()
})
```

### 2. Video Library & Search

```typescript
test('search and filter videos', async ({ page }) => {
  await page.goto('http://localhost:3000/')

  // Search by filename
  await page.fill('input[placeholder="Search videos..."]', 'sample')
  await expect(page.locator('.video-card')).toHaveCount(1)

  // Filter by proxy status
  await page.selectOption('select', 'completed')
  await expect(page.locator('text=Ready')).toBeVisible()
})
```

### 3. Clip Extraction Flow

```typescript
test('extract clip from video', async ({ page }) => {
  // Navigate to video player
  await page.goto('http://localhost:3000/video/[video-id]')

  // Set start/end times
  await page.fill('input[aria-label="Start Time"]', '10')
  await page.fill('input[aria-label="End Time"]', '20')
  await page.fill('input[aria-label="Padding"]', '1')

  // Extract clip
  await page.click('button:has-text("Extract Clip")')

  // Verify success message
  await expect(page.locator('text=Clip extracted successfully')).toBeVisible()

  // Verify redirect to clips page
  await page.waitForURL('http://localhost:3000/clips')
})
```

### 4. Complete Workflow

```typescript
test('complete workflow: upload → proxy → clip', async ({ page }) => {
  // Step 1: Upload video
  await page.goto('http://localhost:3000/upload')
  const fileInput = page.locator('input[type="file"]')
  await fileInput.setInputFiles('test-assets/sample.mp4')
  await expect(page.locator('text=Upload Successful')).toBeVisible()

  // Step 2: Navigate to video player
  await page.click('text=sample.mp4')
  await page.waitForURL(/\/video\//)

  // Step 3: Start proxy rendering
  await page.click('button:has-text("Start Proxy Rendering")')
  await expect(page.locator('text=Proxy rendering started')).toBeVisible()

  // Step 4: Wait for proxy completion (polling)
  await page.waitForSelector('text=Ready', { timeout: 60000 })

  // Step 5: Extract clip
  await page.fill('input[aria-label="Start Time"]', '5')
  await page.fill('input[aria-label="End Time"]', '15')
  await page.click('button:has-text("Extract Clip")')

  // Step 6: Verify clip created
  await expect(page.locator('text=Clip extracted successfully')).toBeVisible()
})
```

## Configuration

**playwright.config.ts**:

```typescript
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
  ],

  webServer: [
    {
      command: 'cd backend && uvicorn src.main:app --port 8000',
      port: 8000,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'npm run dev',
      port: 3000,
      reuseExistingServer: !process.env.CI,
    },
  ],
})
```

## Running Tests

```bash
# Run all E2E tests
npx playwright test

# Run specific test file
npx playwright test upload.spec.ts

# Run in UI mode
npx playwright test --ui

# Run with browser visible
npx playwright test --headed

# Generate test report
npx playwright show-report
```

## Best Practices

1. **Use data-testid**: Add `data-testid` attributes for stable selectors
2. **Mock network**: Use `page.route()` to mock API responses for fast tests
3. **Parallel execution**: Enable `fullyParallel: true` for faster CI
4. **Visual regression**: Use `await expect(page).toHaveScreenshot()` for UI tests
5. **Wait strategies**: Use `waitForSelector()` instead of `setTimeout()`

## Test Assets

Required test files in `tests/e2e/test-assets/`:
- `sample.mp4` - 10-second sample video for upload tests

## CI Integration

**GitHub Actions** (`.github/workflows/e2e.yml`):

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18
      - name: Install dependencies
        run: npm ci && cd backend && pip install -r requirements.txt
      - name: Install Playwright browsers
        run: npx playwright install --with-deps
      - name: Run E2E tests
        run: npx playwright test
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
```

## Coverage Goals

- ✅ Video upload success path
- ✅ Search and filtering
- ✅ Proxy rendering workflow
- ✅ Clip extraction with validation
- ✅ Error handling (invalid files, network errors)
- ✅ Responsive design (mobile, tablet, desktop)
