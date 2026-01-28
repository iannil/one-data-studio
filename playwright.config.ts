import { defineConfig, devices } from '@playwright/test';

/**
 * ONE-DATA-STUDIO E2E 测试配置
 * 基于测试计划: docs/04-testing/test-plan.md
 */

export default defineConfig({
  // 测试目录
  testDir: './tests/e2e',

  // 全局超时设置
  timeout: 60 * 1000,
  expect: {
    timeout: 10 * 1000,
  },

  // 并行执行
  fullyParallel: true,

  // 失败重试
  retries: process.env.CI ? 2 : 0,

  // 并发数
  workers: process.env.CI ? 1 : undefined,

  // 报告格式
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results.json' }],
    ['list'],
  ],

  // 全局配置
  use: {
    // 基础 URL
    baseURL: process.env.BASE_URL || 'http://localhost:3000',

    // 追踪和截图
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-retry',

    // 默认超时
    actionTimeout: 15 * 1000,
    navigationTimeout: 30 * 1000,
  },

  // 测试项目配置
  projects: [
    // ==================== 快速测试 ====================
    {
      name: 'chromium-fast',
      use: {
        ...devices['Desktop Chrome'],
      },
      testMatch: /core-pages\.spec\.ts/,
    },

    // ==================== 深度验收测试 ====================
    {
      name: 'chromium-acceptance',
      use: {
        ...devices['Desktop Chrome'],
      },
      testMatch: /.+-deep\.spec\.ts/,
    },

    // ==================== 用户生命周期测试 ====================
    {
      name: 'user-lifecycle',
      use: {
        ...devices['Desktop Chrome'],
      },
      testDir: './tests/e2e/user-lifecycle',
    },

    // ==================== 多浏览器测试 ====================
    {
      name: 'firefox-acceptance',
      use: {
        ...devices['Desktop Firefox'],
      },
      testMatch: /core-pages\.spec\.ts/,
    },

    {
      name: 'webkit-acceptance',
      use: {
        ...devices['Desktop Safari'],
      },
      testMatch: /core-pages\.spec\.ts/,
    },

    // ==================== 移动端测试 ====================
    {
      name: 'mobile-chrome',
      use: {
        ...devices['Pixel 5'],
      },
      testMatch: /mobile\.spec\.ts/,
    },

    {
      name: 'mobile-safari',
      use: {
        ...devices['iPhone 12'],
      },
      testMatch: /mobile\.spec\.ts/,
    },
  ],

  // Web 服务器配置
  webServer: process.env.CI ? undefined : {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: true,
    timeout: 120 * 1000,
  },
});
