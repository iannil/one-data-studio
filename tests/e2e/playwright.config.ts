/**
 * Playwright E2E 测试配置
 * Sprint 9: E2E 测试扩展
 */

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',

  // 测试超时时间
  timeout: 30 * 1000,

  // 预期超时
  expect: {
    timeout: 5000,
  },

  // 失败时截图和视频
  use: {
    actionTimeout: 10000,
    navigationTimeout: 30000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  // 并行执行
  workers: process.env.CI ? 2 : 4,

  // 报告器配置
  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['json', { outputFile: 'test-results/test-results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
    ['list'],
  ],

  // 测试文件匹配
  testMatch: [
    '**/*.spec.ts',
    '**/*.e2e.ts',
  ],

  // 忽略的文件
  testIgnore: [
    '**/node_modules/**',
    '**/dist/**',
  ],

  // 多浏览器配置
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    // 移动端测试
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
  ],

  // 开发服务器配置（可选）
  // webServer: {
  //   command: 'npm run dev',
  //   port: 3000,
  //   reuseExistingServer: !process.env.CI,
  //   timeout: 120 * 1000,
  // },
});
