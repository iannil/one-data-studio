/**
 * Playwright E2E 测试配置 - 深度验收测试版本
 *
 * 配置说明：
 * - 有头模式：实际打开浏览器窗口，便于观察测试过程
 * - 完整报告：支持 HTML、JSON、JUnit 格式
 * - 视频录制：失败时保留视频
 * - 追踪记录：失败时保留追踪信息
 * - 多浏览器支持：Chromium, Firefox, WebKit, 移动端
 */

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  // 测试目录
  testDir: '.',

  // 测试超时时间 (60秒)
  timeout: 60 * 1000,

  // 预期超时
  expect: {
    timeout: 10000,
  },

  // 失败时截图和视频
  use: {
    // 有头模式：实际打开浏览器窗口
    headless: process.env.HEADED === 'true' ? false : true,

    // 操作超时
    actionTimeout: parseInt(process.env.ACTION_TIMEOUT || '10000'),
    navigationTimeout: parseInt(process.env.NAVIGATION_TIMEOUT || '30000'),

    // 失败时保留追踪信息
    trace: process.env.TRACE || 'retain-on-failure',

    // 失败时截图
    screenshot: process.env.SCREENSHOT || 'only-on-failure',

    // 失败时保留视频
    video: process.env.VIDEO || 'retain-on-failure',

    // 基础 URL
    baseURL: process.env.BASE_URL || 'http://localhost:3000',

    // 忽略 HTTPS 错误
    ignoreHTTPSErrors: true,
  },

  // 并行执行数量
  workers: process.env.CI ? 2 : parseInt(process.env.WORKERS || '4'),

  // 报告器配置
  reporter: [
    // HTML 报告（推荐）
    ['html', {
      outputFolder: 'playwright-report',
      open: process.env.OPEN_REPORT === 'true' ? 'always' : 'never',
    }],

    // JSON 报告（用于 CI 集成）
    ['json', {
      outputFile: 'test-results/results.json',
    }],

    // JUnit 报告（用于 CI 集成）
    ['junit', {
      outputFile: 'test-results/junit.xml',
    }],

    // 列表报告（终端输出）
    ['list'],
  ],

  // 测试文件匹配
  testMatch: [
    '**/*.spec.ts',
    '**/*.e2e.ts',
  ],

  // 完全测试模式
  fullyParallel: true,

  // 忽略的文件
  testIgnore: [
    '**/node_modules/**',
    '**/dist/**',
    '**/*.bak',
  ],

  // 重试配置
  retries: process.env.CI ? 2 : 0,

  // 全局设置
  globalSetup: './global-setup.ts',

  // 测试输出目录
  outputDir: 'test-results',

  // 多浏览器配置
  projects: [
    // ============================================
    // 桌面浏览器 - 主测试套件
    // ============================================

    // Chromium (推荐用于本地测试)
    {
      name: 'chromium-acceptance',
      use: {
        ...devices['Desktop Chrome'],
        // 有头模式用于验收测试
        headless: false,
        viewport: { width: 1280, height: 720 },
      },
    },

    // Firefox
    {
      name: 'firefox-acceptance',
      use: {
        ...devices['Desktop Firefox'],
        viewport: { width: 1280, height: 720 },
      },
    },

    // WebKit (Safari)
    {
      name: 'webkit-acceptance',
      use: {
        ...devices['Desktop Safari'],
        viewport: { width: 1280, height: 720 },
      },
    },

    // ============================================
    // 移动端测试
    // ============================================

    // 移动端 Chrome
    {
      name: 'mobile-chrome',
      use: {
        ...devices['Pixel 5'],
      },
    },

    // 移动端 Safari
    {
      name: 'mobile-safari',
      use: {
        ...devices['iPhone 12'],
      },
    },

    // ============================================
    // 快速测试套件（仅 Chromium，无头模式）
    // ============================================

    {
      name: 'chromium-fast',
      use: {
        ...devices['Desktop Chrome'],
        headless: true,
      },
      testMatch: [
        '**/api-validation.spec.ts',
        '**/performance.spec.ts',
      ],
    },

    // ============================================
    // 深度测试套件（仅在有头模式下运行）
    // ============================================

    {
      name: 'deep-tests',
      use: {
        ...devices['Desktop Chrome'],
        headless: false,
        viewport: { width: 1920, height: 1080 },
      },
      testMatch: [
        '**/*-deep.spec.ts',
      ],
    },

    // ============================================
    // 用户生命周期测试套件
    // ============================================

    {
      name: 'user-lifecycle',
      use: {
        ...devices['Desktop Chrome'],
        headless: false,
        viewport: { width: 1280, height: 720 },
      },
      testMatch: [
        '**/user-lifecycle/*.spec.ts',
      ],
    },

    // ============================================
    // 用户生命周期测试（快速模式，无头）
    // ============================================

    {
      name: 'user-lifecycle-fast',
      use: {
        ...devices['Desktop Chrome'],
        headless: true,
        viewport: { width: 1280, height: 720 },
      },
      testMatch: [
        '**/user-lifecycle/user-creation.spec.ts',
        '**/user-lifecycle/user-activation.spec.ts',
        '**/user-lifecycle/role-assignment.spec.ts',
      ],
    },
  ],

  // Web Server 配置（用于开发模式）
  // webServer: {
  //   command: 'npm run dev',
  //   port: 3000,
  //   timeout: 120 * 1000,
  //   reuseExistingServer: !process.env.CI,
  // },
});
