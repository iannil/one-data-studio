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
      testMatch: /core-pages\.spec\.ts$/,
    },

    // ==================== 深度验收测试 ====================
    {
      name: 'chromium-acceptance',
      use: {
        ...devices['Desktop Chrome'],
      },
      testMatch: /.+-deep\.spec\.ts$/,
    },

    // ==================== DataOps 验证测试 ====================
    {
      name: 'data-ops-validation',
      use: {
        ...devices['Desktop Chrome'],
      },
      testMatch: /data-ops(-validation)?\.spec\.ts$/,
    },

    // ==================== DataOps 真实 API 验证测试 ====================
    {
      name: 'data-ops-live',
      use: {
        ...devices['Desktop Chrome'],
        // 非 headless 模式通过环境变量控制
        headless: process.env.HEADLESS !== 'false',
      },
      testMatch: /data-ops-live(-validation)?\.spec\.ts$/,
    },

    // ==================== DataOps 完整测试 ====================
    {
      name: 'data-ops-full',
      use: {
        ...devices['Desktop Chrome'],
      },
      testDir: './tests/e2e/data-ops',
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

    // ==================== 全面功能交互式验证测试 ====================
    {
      name: 'interactive-full-validation',
      use: {
        ...devices['Desktop Chrome'],
        // 非 headless 模式通过环境变量控制
        headless: process.env.HEADLESS !== 'false',
      },
      testMatch: /interactive-full-validation\.spec\.ts$/,
      retries: 0,
      timeout: 300 * 1000, // 5 分钟超时
      // 降低并发避免资源竞争
      workers: process.env.CI ? 1 : 2,
    },

    // ==================== OCR 验证测试 ====================
    {
      name: '@ocr-validation',
      use: {
        ...devices['Desktop Chrome'],
        // 非 headless 模式通过环境变量控制
        headless: process.env.HEADLESS !== 'false',
      },
      testMatch: /ocr-validation\.spec\.ts$/,
      retries: 0,
      timeout: 120 * 1000, // 2 分钟单个测试超时
      // OCR 测试需要串行执行，避免资源竞争
      workers: 1,
    },

    // ==================== 数据治理 UI E2E 测试 ====================
    {
      name: 'data-governance-ui',
      use: {
        ...devices['Desktop Chrome'],
        // 非 headless 模式通过环境变量控制
        headless: process.env.HEADLESS !== 'false',
      },
      testMatch: /data-governance-ui\.spec\.ts$/,
      retries: 0,
      timeout: 300 * 1000, // 5 分钟测试超时
      // UI E2E 测试串行执行，避免资源竞争
      workers: 1,
    },

    // ==================== Manual Test 数据治理完整测试 ====================
    // 使用独立端口 (MySQL 3316, PostgreSQL 5442)
    // 测试数据永久保留，供手动验证
    {
      name: 'manual-test',
      use: {
        ...devices['Desktop Chrome'],
        // 默认非 headless 模式，便于观察测试过程
        headless: process.env.HEADLESS === 'true',
      },
      testMatch: /manual-test-workflow\.spec\.ts$/,
      retries: 0,
      timeout: 600 * 1000, // 10 分钟测试超时
      // 串行执行，避免资源竞争
      workers: 1,
    },

    // ==================== Persistent Test 持久化完整测试 ====================
    // 使用独立端口 (MySQL 3325, PostgreSQL 5450)
    // 测试数据永久保留，供手动验证
    {
      name: 'persistent-test',
      use: {
        ...devices['Desktop Chrome'],
        // 默认非 headless 模式，便于观察测试过程
        headless: process.env.HEADLESS === 'true',
      },
      testMatch: /persistent-full-workflow\.spec\.ts$/,
      retries: 0,
      timeout: 600 * 1000, // 10 分钟测试超时
      // 串行执行，避免资源竞争
      workers: 1,
    },

    // ==================== Full Platform Test 全平台综合测试 ====================
    // 覆盖所有 30+ 功能模块
    // 使用真实 API（禁止 mock）
    // 测试数据持久化，生成验证指南
    {
      name: 'full-platform',
      use: {
        ...devices['Desktop Chrome'],
        // 默认非 headless 模式，便于观察测试过程
        headless: process.env.HEADLESS === 'true',
      },
      testMatch: /full-platform-test\.spec\.ts$/,
      retries: 0,
      timeout: 1800 * 1000, // 30 分钟测试超时
      // 串行执行，确保资源状态一致
      workers: 1,
    },

    // ==================== Visual Acceptance 可见浏览器验收测试 ====================
    // 用于人工观察的功能验收测试
    // 默认非 headless 模式，逐页面截图
    // 覆盖 70+ 页面的完整验收
    {
      name: 'visual-acceptance',
      use: {
        ...devices['Desktop Chrome'],
        // 默认非 headless 模式，便于人工观察
        headless: process.env.HEADLESS === 'true',
        // 支持 slowMo 模式
        launchOptions: {
          slowMo: parseInt(process.env.SLOW_MO || '0', 10),
        },
        // 视频录制（可选）
        video: process.env.RECORD_VIDEO === 'true' ? 'on' : 'off',
      },
      testMatch: /visual-acceptance\.spec\.ts$/,
      retries: 0,
      timeout: 600 * 1000, // 10 分钟测试超时
      // 串行执行，确保页面顺序
      workers: 1,
    },

    // ==================== Visual CRUD Acceptance 可见浏览器 CRUD 验收测试 ====================
    // 用于 CRUD 操作的功能验收测试
    // 覆盖 Create/Read/Update/Delete 四种操作
    // 默认非 headless 模式，逐操作截图
    {
      name: 'visual-crud-acceptance',
      use: {
        ...devices['Desktop Chrome'],
        // 默认非 headless 模式，便于人工观察
        headless: process.env.HEADLESS === 'true',
        // 支持 slowMo 模式
        launchOptions: {
          slowMo: parseInt(process.env.SLOW_MO || '0', 10),
        },
        // 视频录制（可选）
        video: process.env.RECORD_VIDEO === 'true' ? 'on' : 'off',
      },
      testMatch: /visual-crud-acceptance\.spec\.ts$/,
      retries: 0,
      timeout: 600 * 1000, // 10 分钟测试超时
      // 串行执行，确保操作顺序
      workers: 1,
    },

    // ==================== P0 CRUD Acceptance P0 核心功能 CRUD 验收测试 ====================
    // 专门针对 P0 核心功能的 CRUD 验收测试
    // 使用真实 API（非 Mock）
    // 生成详细验收报告 + 截图 + 网络请求日志
    {
      name: 'p0-crud-acceptance',
      use: {
        ...devices['Desktop Chrome'],
        // 默认非 headless 模式，便于人工观察
        headless: process.env.HEADLESS === 'true',
        // 支持 slowMo 模式
        launchOptions: {
          slowMo: parseInt(process.env.SLOW_MO || '0', 10),
        },
        // 视频录制（可选）
        video: process.env.RECORD_VIDEO === 'true' ? 'on' : 'off',
      },
      testMatch: /p0-crud-acceptance\.spec\.ts$/,
      retries: 0,
      timeout: 600 * 1000, // 10 分钟测试超时
      // 串行执行，确保操作顺序
      workers: 1,
    },

    // ==================== DataOps 功能测试规范 ====================
    // 基于 docs/03-progress/test-specs/ 文档的 321 个功能测试
    // 覆盖 6 大领域 28 个模块
    {
      name: 'dataops-test-specs',
      use: {
        ...devices['Desktop Chrome'],
        headless: process.env.HEADLESS !== 'false',
      },
      testDir: './tests/e2e/dataops-test-specs',
      retries: 0,
      timeout: 120 * 1000, // 2 分钟单个测试超时
      workers: process.env.CI ? 1 : 4,
    },
  ],

  // Web 服务器配置
  webServer: process.env.CI ? undefined : {
    command: 'cd web && npm run dev',
    port: 3001,
    reuseExistingServer: !process.env.FRESH,
    timeout: 120 * 1000,
  },
});
