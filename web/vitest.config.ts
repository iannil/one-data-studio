/**
 * Vitest 配置文件
 * Sprint 6: 前端单元测试框架
 *
 * 使用方法:
 *   npm run test              # 运行所有测试
 *   npm run test:ui          # 运行测试 UI
 *   npm run test:coverage    # 生成覆盖率报告
 */

import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    // 测试环境
    environment: 'jsdom',

    // 全局配置
    globals: true,

    // 设置文件
    setupFiles: ['./src/test/setup.ts'],

    // 测试文件匹配模式
    include: ['**/*.{test,spec}.{js,jsx,ts,tsx}'],

    // 排除目录
    exclude: ['node_modules', 'dist', '.idea', '.git', '.cache'],

    // 覆盖率配置
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'src/test/',
        '*.config.ts',
        '*.config.js',
        'src/main.tsx',
        'src/vite-env.d.ts',
        '**/*.d.ts',
        '**/*.test.{ts,tsx}',
        '**/*.spec.{ts,tsx}',
      ],
      // 覆盖率阈值
      thresholds: {
        lines: 70,
        functions: 70,
        branches: 60,
        statements: 70,
      },
    },

    // 并行执行
    threads: true,
    maxThreads: 4,
    minThreads: 1,

    // 超时时间（毫秒）
    testTimeout: 10000,
    hookTimeout: 10000,

    // 静默输出（非 CI 环境）
    silent: false,
    watch: false,
  },

  // 路径解析
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
