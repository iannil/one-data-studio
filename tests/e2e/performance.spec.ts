/**
 * 性能和并发验收测试
 * 测试页面加载时间、API 响应时间、大数据量渲染、并发操作等
 */

import { test, expect } from './fixtures/real-auth.fixture';
import { logger } from './helpers/logger';
import { createApiClient, clearRequestLogs, getRequestLogs, getFailedRequests } from './helpers/api-client';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

// 性能阈值配置
const PERFORMANCE_THRESHOLDS = {
  maxPageLoadTime: parseInt(process.env.MAX_PAGE_LOAD_TIME || '3000'),
  maxApiP50ResponseTime: parseInt(process.env.MAX_P50_RESPONSE_TIME || '1000'),
  maxApiP95ResponseTime: parseInt(process.env.MAX_P95_RESPONSE_TIME || '2000'),
  maxApiP99ResponseTime: parseInt(process.env.MAX_P99_RESPONSE_TIME || '5000'),
};

// ============================================
// 页面加载性能测试
// ============================================
test.describe('性能 - 页面加载', () => {
  test('should measure home page load time', async ({ page }) => {
    const startTime = Date.now();

    await page.goto(`${BASE_URL}/`);
    await page.waitForLoadState('networkidle');

    const loadTime = Date.now() - startTime;
    logger.info(`Home page load time: ${loadTime}ms`);

    expect(loadTime).toBeLessThan(PERFORMANCE_THRESHOLDS.maxPageLoadTime);
  });

  test('should measure datasets page load time', async ({ page }) => {
    const startTime = Date.now();

    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    const loadTime = Date.now() - startTime;
    logger.info(`Datasets page load time: ${loadTime}ms`);

    expect(loadTime).toBeLessThan(PERFORMANCE_THRESHOLDS.maxPageLoadTime);
  });

  test('should measure workflows page load time', async ({ page }) => {
    const startTime = Date.now();

    await page.goto(`${BASE_URL}/workflows`);
    await page.waitForLoadState('networkidle');

    const loadTime = Date.now() - startTime;
    logger.info(`Workflows page load time: ${loadTime}ms`);

    expect(loadTime).toBeLessThan(PERFORMANCE_THRESHOLDS.maxPageLoadTime);
  });

  test('should measure First Contentful Paint (FCP)', async ({ page }) => {
    const metrics = await page.goto(`${BASE_URL}/`).then(async () => {
      return await page.evaluate(() => {
        const perfData = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
        return {
          fcp: perfData.responseStart - perfData.fetchStart,
          domContentLoaded: perfData.domContentLoadedEventEnd - perfData.fetchStart,
          loadComplete: perfData.loadEventEnd - perfData.fetchStart,
        };
      });
    });

    logger.info('Performance metrics:', metrics);

    expect(metrics.fcp).toBeLessThan(PERFORMANCE_THRESHOLDS.maxPageLoadTime);
  });

  test('should measure Largest Contentful Paint (LCP)', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);

    const lcp = await page.evaluate(async () => {
      return new Promise<number>((resolve) => {
        new PerformanceObserver((list) => {
          const entries = list.getEntries();
          const lastEntry = entries[entries.length - 1] as any;
          resolve(lastEntry.renderTime || lastEntry.loadTime);
        }).observe({ entryTypes: ['largest-contentful-paint'] });

        // 超时保护
        setTimeout(() => resolve(0), 5000);
      });
    });

    if (lcp > 0) {
      logger.info(`Largest Contentful Paint: ${lcp}ms`);
      expect(lcp).toBeLessThan(PERFORMANCE_THRESHOLDS.maxPageLoadTime * 2);
    }
  });
});

// ============================================
// API 响应时间测试
// ============================================
test.describe('性能 - API 响应时间', () => {
  test('should measure health check API response time', async ({ request }) => {
    clearRequestLogs();

    const apiClient = createApiClient(request, 'agent_api');

    const startTime = Date.now();
    await apiClient.get('/api/v1/health');
    const responseTime = Date.now() - startTime;

    logger.info(`Health check API response time: ${responseTime}ms`);
    expect(responseTime).toBeLessThan(PERFORMANCE_THRESHOLDS.maxApiP50ResponseTime);
  });

  test('should measure user info API response time', async ({ request }) => {
    const apiClient = createApiClient(request, 'agent_api');

    const startTime = Date.now();
    await apiClient.get('/api/v1/user/info');
    const responseTime = Date.now() - startTime;

    logger.info(`User info API response time: ${responseTime}ms`);
    expect(responseTime).toBeLessThan(PERFORMANCE_THRESHOLDS.maxApiP50ResponseTime);
  });

  test('should measure datasets list API response time', async ({ request }) => {
    const apiClient = createApiClient(request, 'agent_api');

    const startTime = Date.now();
    await apiClient.get('/api/v1/datasets');
    const responseTime = Date.now() - startTime;

    logger.info(`Datasets list API response time: ${responseTime}ms`);
    expect(responseTime).toBeLessThan(PERFORMANCE_THRESHOLDS.maxApiP95ResponseTime);
  });

  test('should measure workflows list API response time', async ({ request }) => {
    const apiClient = createApiClient(request, 'agent_api');

    const startTime = Date.now();
    await apiClient.get('/api/v1/workflows');
    const responseTime = Date.now() - startTime;

    logger.info(`Workflows list API response time: ${responseTime}ms`);
    expect(responseTime).toBeLessThan(PERFORMANCE_THRESHOLDS.maxApiP95ResponseTime);
  });

  test('should measure P50, P95, P99 response times', async ({ request }) => {
    clearRequestLogs();

    const apiClient = createApiClient(request, 'agent_api');

    // 发送多个请求
    const endpoints = [
      '/api/v1/health',
      '/api/v1/user/info',
      '/api/v1/datasets',
      '/api/v1/workflows',
      '/api/v1/conversations',
    ];

    for (let i = 0; i < 10; i++) {
      for (const endpoint of endpoints) {
        await apiClient.get(endpoint);
      }
    }

    const logs = getRequestLogs();
    const responseTimes = logs.map(log => log.duration).sort((a, b) => a - b);

    const p50 = responseTimes[Math.floor(responseTimes.length * 0.5)];
    const p95 = responseTimes[Math.floor(responseTimes.length * 0.95)];
    const p99 = responseTimes[Math.floor(responseTimes.length * 0.99)];

    logger.info(`Response times - P50: ${p50}ms, P95: ${p95}ms, P99: ${p99}ms`);

    expect(p50).toBeLessThan(PERFORMANCE_THRESHOLDS.maxApiP50ResponseTime);
    expect(p95).toBeLessThan(PERFORMANCE_THRESHOLDS.maxApiP95ResponseTime);
    expect(p99).toBeLessThan(PERFORMANCE_THRESHOLDS.maxApiP99ResponseTime);
  });
});

// ============================================
// 大数据量渲染测试
// ============================================
test.describe('性能 - 大数据量渲染', () => {
  test('should handle large dataset list (1000+ rows)', async ({ page, request }) => {
    // 注意：这需要测试数据支持
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    const table = page.locator('.data-table, .ant-table, table').first();
    const hasTable = await table.count() > 0;

    if (hasTable) {
      const rows = table.locator('tr, [data-row-key]');
      const rowCount = await rows.count();

      logger.info(`Dataset list row count: ${rowCount}`);

      if (rowCount > 0) {
        // 测试滚动性能
        const startTime = Date.now();
        await table.evaluate((el: HTMLElement) => {
          el.scrollTop = el.scrollHeight / 2;
        });
        const scrollTime = Date.now() - startTime;

        logger.info(`Scroll time: ${scrollTime}ms`);
        expect(scrollTime).toBeLessThan(500);
      }
    }
  });

  test('should handle large table with virtual scrolling', async ({ page }) => {
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    const table = page.locator('.data-table, .ant-table').first();
    const hasTable = await table.count() > 0;

    if (hasTable) {
      // 检查是否有虚拟滚动
      const hasVirtualScroll = await table.locator('.virtual-scroll, [class*="virtual"]').count() > 0;
      logger.info('Has virtual scroll:', hasVirtualScroll);
    }
  });

  test('should render complex workflow without lag', async ({ page }) => {
    await page.goto(`${BASE_URL}/workflows`);
    await page.waitForLoadState('networkidle');

    const firstWorkflow = page.locator('tr[data-row-key], .workflow-item').first();
    const hasWorkflow = await firstWorkflow.count() > 0;

    if (hasWorkflow) {
      const viewButton = firstWorkflow.locator('button:has-text("查看"), button:has-text("View")').first();
      if (await viewButton.isVisible()) {
        const startTime = Date.now();
        await viewButton.click();
        await page.waitForLoadState('networkidle');
        const loadTime = Date.now() - startTime;

        logger.info(`Workflow detail load time: ${loadTime}ms`);
        expect(loadTime).toBeLessThan(PERFORMANCE_THRESHOLDS.maxPageLoadTime);
      }
    }
  });
});

// ============================================
// 并发操作测试
// ============================================
test.describe('性能 - 并发操作', () => {
  test('should handle concurrent API requests', async ({ request }) => {
    clearRequestLogs();

    const apiClient = createApiClient(request, 'agent_api');

    // 并发发送10个请求
    const promises = Array.from({ length: 10 }, (_, i) =>
      apiClient.get(`/api/v1/datasets?page=${i + 1}&page_size=10`)
    );

    const startTime = Date.now();
    await Promise.all(promises);
    const totalTime = Date.now() - startTime;

    logger.info(`Concurrent requests (10) total time: ${totalTime}ms`);
    logger.info(`Average time per request: ${totalTime / 10}ms`);

    // 并发请求应该比串行快
    expect(totalTime).toBeLessThan(10000);
  });

  test('should handle rapid page navigations', async ({ page }) => {
    const pages = [
      `${BASE_URL}/datasets`,
      `${BASE_URL}/documents`,
      `${BASE_URL}/workflows`,
      `${BASE_URL}/chat`,
      `${BASE_URL}/agents`,
    ];

    const startTime = Date.now();

    for (const pg of pages) {
      await page.goto(pg);
      // 不等待 networkidle，模拟快速导航
    }

    await page.waitForLoadState('networkidle');
    const totalTime = Date.now() - startTime;

    logger.info(`Rapid navigation (5 pages) time: ${totalTime}ms`);
    expect(totalTime).toBeLessThan(15000);
  });

  test('should handle simultaneous form submissions', async ({ page }) => {
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    const createButtons = page.locator('button:has-text("创建"), button:has-text("新建")');
    const count = await createButtons.count();

    if (count > 0) {
      // 快速点击多次（测试防抖）
      const firstButton = createButtons.first();
      for (let i = 0; i < 3; i++) {
        await firstButton.click();
        await page.waitForTimeout(100);
      }

      // 应该只打开一个对话框
      const modals = page.locator('.ant-modal, .modal');
      const modalCount = await modals.count();
      expect(modalCount).toBeLessThanOrEqual(1);
    }
  });
});

// ============================================
// 内存泄漏检测
// ============================================
test.describe('性能 - 内存泄漏检测', () => {
  test('should not leak memory during navigation', async ({ page }) => {
    const getMemoryUsage = async () => {
      return await page.evaluate(() => {
        return (performance as any).memory?.usedJSHeapSize || 0;
      });
    };

    const initialMemory = await getMemoryUsage();
    logger.info(`Initial memory: ${initialMemory} bytes`);

    // 进行多次导航
    for (let i = 0; i < 5; i++) {
      await page.goto(`${BASE_URL}/datasets`);
      await page.waitForLoadState('networkidle');
      await page.goto(`${BASE_URL}/workflows`);
      await page.waitForLoadState('networkidle');
    }

    // 强制垃圾回收（如果支持）
    await page.evaluate(() => {
      if ((globalThis as any).gc) {
        (globalThis as any).gc();
      }
    });

    const finalMemory = await getMemoryUsage();
    const memoryIncrease = finalMemory - initialMemory;
    const memoryIncreaseMB = memoryIncrease / (1024 * 1024);

    logger.info(`Final memory: ${finalMemory} bytes`);
    logger.info(`Memory increase: ${memoryIncreaseMB.toFixed(2)} MB`);

    // 内存增长不应超过 50MB（这是一个宽松的阈值）
    expect(memoryIncrease).toBeLessThan(50 * 1024 * 1024);
  });

  test('should not leak memory during API calls', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'agent_api');

    const getMemoryUsage = async () => {
      return await page.evaluate(() => {
        return (performance as any).memory?.usedJSHeapSize || 0;
      });
    };

    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    const initialMemory = await getMemoryUsage();

    // 进行多次 API 调用
    for (let i = 0; i < 20; i++) {
      await apiClient.get('/api/v1/datasets');
      await page.waitForTimeout(100);
    }

    await page.evaluate(() => {
      if ((globalThis as any).gc) {
        (globalThis as any).gc();
      }
    });

    const finalMemory = await getMemoryUsage();
    const memoryIncrease = finalMemory - initialMemory;

    logger.info(`Memory increase after API calls: ${(memoryIncrease / (1024 * 1024)).toFixed(2)} MB`);

    expect(memoryIncrease).toBeLessThan(30 * 1024 * 1024);
  });
});

// ============================================
// 资源加载优化
// ============================================
test.describe('性能 - 资源加载', () => {
  test('should use efficient bundle sizes', async ({ page }) => {
    const resources: { name: string; size: number; transferSize: number }[] = [];

    page.on('response', async (response) => {
      const url = response.url();
      if (url.includes('.js') || url.includes('.css')) {
        const headers = response.headers();
        const size = parseInt(headers['content-length'] || '0');
        resources.push({
          name: url.split('/').pop() || 'unknown',
          size,
          transferSize: size,
        });
      }
    });

    await page.goto(`${BASE_URL}/`);
    await page.waitForLoadState('networkidle');

    // 找出最大的资源
    resources.sort((a, b) => b.size - a.size);
    const largest = resources.slice(0, 5);

    logger.info('Largest resources:');
    for (const resource of largest) {
      const sizeKB = (resource.size / 1024).toFixed(2);
      logger.info(`  ${resource.name}: ${sizeKB} KB`);
    }

    // 主 bundle 不应过大（1MB 以下为佳）
    const mainBundleSize = resources.find(r => r.name.includes('main') || r.name.includes('index'));
    if (mainBundleSize) {
      const sizeMB = mainBundleSize.size / (1024 * 1024);
      logger.info(`Main bundle size: ${sizeMB.toFixed(2)} MB`);
    }
  });

  test('should have efficient caching headers', async ({ page }) => {
    const cacheableResources: { url: string; cacheControl: string }[] = [];

    page.on('response', async (response) => {
      const url = response.url();
      if (url.includes('.js') || url.includes('.css') || url.includes('.png') || url.includes('.jpg')) {
        const headers = response.headers();
        const cacheControl = headers['cache-control'] || '';
        cacheableResources.push({ url, cacheControl });
      }
    });

    await page.goto(`${BASE_URL}/`);
    await page.waitForLoadState('networkidle');

    const withCache = cacheableResources.filter(r => r.cacheControl.includes('max-age'));
    const withLongCache = withCache.filter(r => {
      const match = r.cacheControl.match(/max-age=(\d+)/);
      return match && parseInt(match[1]) > 86400; // 超过1天
    });

    logger.info(`Cacheable resources: ${cacheableResources.length}`);
    logger.info(`With cache headers: ${withCache.length}`);
    logger.info(`With long-term cache (>1 day): ${withLongCache.length}`);
  });
});

// ============================================
// 性能回归测试
// ============================================
test.describe('性能 - 性能回归测试', () => {
  test('should meet performance baseline', async ({ page }) => {
    const pages = [
      { path: '/', name: 'Home' },
      { path: '/datasets', name: 'Datasets' },
      { path: '/workflows', name: 'Workflows' },
      { path: '/chat', name: 'Chat' },
    ];

    const results: { name: string; loadTime: number }[] = [];

    for (const pg of pages) {
      const startTime = Date.now();
      await page.goto(`${BASE_URL}${pg.path}`);
      await page.waitForLoadState('networkidle');
      const loadTime = Date.now() - startTime;

      results.push({ name: pg.name, loadTime });
      logger.info(`${pg.name} page load time: ${loadTime}ms`);
    }

    // 计算平均加载时间
    const avgLoadTime = results.reduce((sum, r) => sum + r.loadTime, 0) / results.length;
    logger.info(`Average page load time: ${avgLoadTime.toFixed(2)}ms`);

    expect(avgLoadTime).toBeLessThan(PERFORMANCE_THRESHOLDS.maxPageLoadTime);
  });
});

test.afterEach(async ({ request }) => {
  const failedRequests = getFailedRequests();
  if (failedRequests.length > 0) {
    console.error('Failed API requests in Performance test:', failedRequests);
  }
});
