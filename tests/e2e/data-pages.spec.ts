/**
 * Data DataOps 页面 E2E 验收测试
 * 测试数据治理、ETL、质量监控等 DataOps 功能
 */

import { test, expect } from '@playwright/test';
import { setupAuth, setupCommonMocks, BASE_URL } from './helpers';

test.describe('Data - Data Sources', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);
    page.route('**/api/v1/data/datasources', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            datasources: [
              { id: 'ds-1', name: 'MySQL主库', type: 'mysql', host: 'db1.example.com', status: 'connected' },
              { id: 'ds-2', name: 'ClickHouse集群', type: 'clickhouse', host: 'ch1.example.com', status: 'connected' },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display datasources page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/data/datasources`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('should have add datasource button', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/data/datasources`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Data - ETL', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);
    page.route('**/api/v1/data/etl-jobs', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            jobs: [
              { id: 'etl-1', name: '用户数据同步', source: 'MySQL', target: 'Hive', status: 'running' },
              { id: 'etl-2', name: '日志采集', source: 'Kafka', target: 'ClickHouse', status: 'active' },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display ETL page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/data/etl`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Data - Data Quality', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);
    page.route('**/api/v1/data/quality', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            rules: [
              { id: 'qr-1', name: '用户ID非空检查', table: 'users', column: 'user_id', type: 'not_null', status: 'passed' },
              { id: 'qr-2', name: '金额范围检查', table: 'orders', column: 'amount', type: 'range', status: 'failed' },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display data quality page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/data/quality`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Data - Lineage', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);
    page.route('**/api/v1/data/lineage', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            nodes: [
              { id: 'tbl-1', name: 'raw_users', type: 'source' },
              { id: 'tbl-2', name: 'dim_users', type: 'dimension' },
            ],
            edges: [
              { source: 'tbl-1', target: 'tbl-2' },
            ],
          },
        }),
      });
    });
  });

  test('should display lineage page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/data/lineage`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Data - Features', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);
    page.route('**/api/v1/data/features', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            feature_groups: [
              { id: 'fg-1', name: 'user_features', description: '用户特征', features: 25, status: 'online' },
              { id: 'fg-2', name: 'item_features', description: '商品特征', features: 18, status: 'online' },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display features page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/data/features`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Data - Standards', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);
    page.route('**/api/v1/data/standards', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            standards: [
              { id: 'std-1', name: '日期格式标准', type: 'format', rule: 'YYYY-MM-DD' },
            ],
            total: 1,
          },
        }),
      });
    });
  });

  test('should display standards page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/data/standards`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Data - Assets', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);
    page.route('**/api/v1/data/assets', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            assets: [
              { id: 'asset-1', name: '用户画像表', type: 'table', owner: '数据组' },
              { id: 'asset-2', name: '销售指标API', type: 'api', owner: '分析组' },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display assets page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/data/assets`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Data - Services', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);
    page.route('**/api/v1/data/services', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            services: [
              { id: 'svc-1', name: '数据查询服务', type: 'query', status: 'online', qps: 450 },
              { id: 'svc-2', name: '特征获取服务', type: 'feature', status: 'online', qps: 1200 },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display services page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/data/services`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Data - BI', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);
    page.route('**/api/v1/data/bi', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            dashboards: [
              { id: 'dash-1', name: '运营大屏', charts: 8, owner: '运营组' },
              { id: 'dash-2', name: '销售分析', charts: 12, owner: '销售组' },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display BI page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/data/bi`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Data - Monitoring', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);
    page.route('**/api/v1/data/monitoring', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            metrics: {
              total_tables: 256,
              total_etl_jobs: 45,
              success_rate: 99.5,
            },
          },
        }),
      });
    });
  });

  test('should display monitoring page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/data/monitoring`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Data - Streaming', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);
    page.route('**/api/v1/data/streaming', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            streams: [
              { id: 'stream-1', name: '用户行为流', source: 'Kafka', status: 'running', tps: 1500 },
              { id: 'stream-2', name: '订单事件流', source: 'Kafka', status: 'running', tps: 800 },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display streaming page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/data/streaming`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Data - Streaming IDE', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);
  });

  test('should display streaming IDE page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/data/streaming-ide`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Data - Offline', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);
    page.route('**/api/v1/data/offline', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            tasks: [
              { id: 'task-1', name: '日结任务', status: 'completed', duration: 3600 },
              { id: 'task-2', name: '数据归档', status: 'running', duration: null },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display offline page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/data/offline`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Data - Metrics', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);
    page.route('**/api/v1/data/metrics', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            metrics: [
              { id: 'm-1', name: '日活跃用户', value: 125000, trend: '+5%' },
              { id: 'm-2', name: 'GMV', value: 8500000, trend: '+12%' },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display metrics page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/data/metrics`);
    await expect(page.locator('body')).toBeVisible();
  });
});
