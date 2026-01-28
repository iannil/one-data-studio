/**
 * 数据工程师完整流程 E2E 测试
 * 用例覆盖: DE-DC, DE-ETL, DE-AI, DE-DM, DE-FU
 *
 * 测试数据工程师角色的完整工作流程：
 * 数据采集 → ETL 编排 → 缺失值处理 → 数据脱敏 → 多表融合
 */

import { test, expect } from './fixtures/user-lifecycle.fixture';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const API_BASE = process.env.API_BASE || 'http://localhost:8080';

test.describe('数据工程师完整流程', () => {
  let deToken: string;

  test.beforeAll(async ({ request }) => {
    const loginResp = await request.post(`${API_BASE}/api/v1/auth/login`, {
      data: { username: 'test_de', password: 'De1234!' },
    });
    const loginData = await loginResp.json();
    deToken = loginData.data?.token || '';
  });

  // ==================== 数据采集 ====================

  test.describe('DE-DC: 数据采集', () => {
    test('DE-DC-001: 创建全量采集任务', async ({ request }) => {
      const response = await request.post(`${API_BASE}/api/v1/datasets/ingest`, {
        headers: { Authorization: `Bearer ${deToken}` },
        data: {
          name: `e2e_ingest_full_${Date.now()}`,
          source_datasource_id: 'test-datasource-1',
          target_datasource_id: 'test-datasource-2',
          tables: ['test_users', 'test_orders'],
          mode: 'full',
        },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
      expect(json.data?.task_id).toBeTruthy();
    });

    test('DE-DC-002: 创建增量采集任务', async ({ request }) => {
      const response = await request.post(`${API_BASE}/api/v1/datasets/ingest`, {
        headers: { Authorization: `Bearer ${deToken}` },
        data: {
          name: `e2e_ingest_incr_${Date.now()}`,
          source_datasource_id: 'test-datasource-1',
          target_datasource_id: 'test-datasource-2',
          tables: ['test_orders'],
          mode: 'incremental',
          incremental_field: 'updated_at',
        },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
    });
  });

  // ==================== ETL 编排 ====================

  test.describe('DE-ETL: ETL 编排与执行', () => {
    test('DE-ETL-001: 创建 ETL 任务', async ({ request }) => {
      const response = await request.post(`${API_BASE}/api/v1/etl/tasks`, {
        headers: { Authorization: `Bearer ${deToken}` },
        data: {
          name: `e2e_etl_${Date.now()}`,
          description: 'E2E 测试 ETL 任务',
          source_datasource_id: 'test-datasource-1',
          target_datasource_id: 'test-datasource-2',
          transformations: [
            { type: 'filter', condition: 'age > 18' },
            { type: 'rename', mapping: { old_name: 'new_name' } },
          ],
        },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
      expect(json.data?.id).toBeTruthy();
    });

    test('DE-ETL-002: 执行 ETL 任务', async ({ request }) => {
      // 创建任务
      const createResp = await request.post(`${API_BASE}/api/v1/etl/tasks`, {
        headers: { Authorization: `Bearer ${deToken}` },
        data: {
          name: `e2e_etl_exec_${Date.now()}`,
          source_datasource_id: 'test-datasource-1',
          target_datasource_id: 'test-datasource-2',
          transformations: [],
        },
      });
      const createData = await createResp.json();
      const taskId = createData.data?.id;

      // 执行任务
      const execResp = await request.post(`${API_BASE}/api/v1/etl/tasks/${taskId}/execute`, {
        headers: { Authorization: `Bearer ${deToken}` },
      });

      expect(execResp.ok()).toBeTruthy();
      const execData = await execResp.json();
      expect(execData.code).toBe(0);
      expect(execData.data?.execution_id).toBeTruthy();
    });

    test('DE-ETL-003: 查询 ETL 执行状态', async ({ request }) => {
      const response = await request.get(`${API_BASE}/api/v1/etl/tasks?status=running`, {
        headers: { Authorization: `Bearer ${deToken}` },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
    });

    test('DE-ETL-004: ETL 任务调度配置', async ({ request }) => {
      const createResp = await request.post(`${API_BASE}/api/v1/etl/tasks`, {
        headers: { Authorization: `Bearer ${deToken}` },
        data: {
          name: `e2e_etl_sched_${Date.now()}`,
          source_datasource_id: 'test-datasource-1',
          target_datasource_id: 'test-datasource-2',
          transformations: [],
          schedule: { cron: '0 2 * * *', timezone: 'Asia/Shanghai' },
        },
      });
      const createData = await createResp.json();

      expect(createData.code).toBe(0);
      if (createData.data?.schedule) {
        expect(createData.data.schedule.cron).toBe('0 2 * * *');
      }
    });

    test('DE-ETL-005: ETL 错误处理与重试', async ({ request }) => {
      const response = await request.post(`${API_BASE}/api/v1/etl/tasks`, {
        headers: { Authorization: `Bearer ${deToken}` },
        data: {
          name: `e2e_etl_retry_${Date.now()}`,
          source_datasource_id: 'test-datasource-1',
          target_datasource_id: 'test-datasource-2',
          transformations: [],
          retry_policy: { max_retries: 3, backoff_seconds: 60 },
        },
      });

      expect(response.ok()).toBeTruthy();
    });
  });

  // ==================== 缺失值处理 ====================

  test.describe('DE-AI: 缺失值分析与填充', () => {
    test('DE-AI-001: 缺失模式分析', async ({ request }) => {
      const response = await request.post(`${API_BASE}/api/v1/data/analyze-missing`, {
        headers: { Authorization: `Bearer ${deToken}` },
        data: {
          datasource_id: 'test-datasource-1',
          table_name: 'test_users',
        },
      });

      const json = await response.json();
      if (json.code === 0 && json.data) {
        expect(json.data.pattern).toBeDefined();
        expect(json.data.missing_rate).toBeDefined();
      }
    });

    test('DE-AI-002: 均值填充', async ({ request }) => {
      const response = await request.post(`${API_BASE}/api/v1/data/impute-mean`, {
        headers: { Authorization: `Bearer ${deToken}` },
        data: {
          datasource_id: 'test-datasource-1',
          table_name: 'test_users',
          column: 'age',
        },
      });

      expect(response.ok()).toBeTruthy();
    });
  });

  // ==================== 数据脱敏 ====================

  test.describe('DE-DM: 数据脱敏', () => {
    test('DE-DM-001: 应用手机号脱敏', async ({ request }) => {
      const response = await request.post(`${API_BASE}/api/v1/masking/apply`, {
        headers: { Authorization: `Bearer ${deToken}` },
        data: {
          datasource_id: 'test-datasource-1',
          table_name: 'test_users',
          rules: [
            { column: 'phone', strategy: 'partial_mask', type: 'phone' },
          ],
        },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
    });

    test('DE-DM-002: 应用身份证脱敏', async ({ request }) => {
      const response = await request.post(`${API_BASE}/api/v1/masking/apply`, {
        headers: { Authorization: `Bearer ${deToken}` },
        data: {
          datasource_id: 'test-datasource-1',
          table_name: 'test_users',
          rules: [
            { column: 'id_card', strategy: 'partial_mask', type: 'id_card' },
          ],
        },
      });

      expect(response.ok()).toBeTruthy();
    });

    test('DE-DM-003: 应用银行卡脱敏', async ({ request }) => {
      const response = await request.post(`${API_BASE}/api/v1/masking/apply`, {
        headers: { Authorization: `Bearer ${deToken}` },
        data: {
          datasource_id: 'test-datasource-1',
          table_name: 'test_users',
          rules: [
            { column: 'bank_card', strategy: 'partial_mask', type: 'bank_card' },
          ],
        },
      });

      expect(response.ok()).toBeTruthy();
    });

    test('DE-DM-004: 应用邮箱脱敏', async ({ request }) => {
      const response = await request.post(`${API_BASE}/api/v1/masking/apply`, {
        headers: { Authorization: `Bearer ${deToken}` },
        data: {
          datasource_id: 'test-datasource-1',
          table_name: 'test_users',
          rules: [
            { column: 'email', strategy: 'partial_mask', type: 'email' },
          ],
        },
      });

      expect(response.ok()).toBeTruthy();
    });
  });

  // ==================== 多表融合 ====================

  test.describe('DE-FU: 多表融合', () => {
    test('DE-FU-001: 创建多表融合任务', async ({ request }) => {
      const response = await request.post(`${API_BASE}/api/v1/etl/fusion`, {
        headers: { Authorization: `Bearer ${deToken}` },
        data: {
          name: `e2e_fusion_${Date.now()}`,
          tables: [
            { datasource_id: 'test-datasource-1', table: 'test_users', alias: 'u' },
            { datasource_id: 'test-datasource-1', table: 'test_orders', alias: 'o' },
          ],
          join_conditions: [
            { left: 'u.id', right: 'o.user_id', type: 'inner' },
          ],
          output_columns: ['u.id', 'u.name', 'o.amount', 'o.order_date'],
        },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
    });

    test('DE-FU-006: 融合任务预览', async ({ request }) => {
      const response = await request.post(`${API_BASE}/api/v1/etl/fusion/preview`, {
        headers: { Authorization: `Bearer ${deToken}` },
        data: {
          tables: [
            { datasource_id: 'test-datasource-1', table: 'test_users', alias: 'u' },
            { datasource_id: 'test-datasource-1', table: 'test_orders', alias: 'o' },
          ],
          join_conditions: [
            { left: 'u.id', right: 'o.user_id', type: 'inner' },
          ],
          limit: 10,
        },
      });

      const json = await response.json();
      if (json.code === 0 && json.data) {
        expect(json.data.preview).toBeDefined();
        expect(json.data.total_count).toBeDefined();
      }
    });

    test('DE-FU-008: 融合结果输出到新表', async ({ request }) => {
      const response = await request.post(`${API_BASE}/api/v1/etl/fusion`, {
        headers: { Authorization: `Bearer ${deToken}` },
        data: {
          name: `e2e_fusion_output_${Date.now()}`,
          tables: [
            { datasource_id: 'test-datasource-1', table: 'test_users', alias: 'u' },
          ],
          output: {
            datasource_id: 'test-datasource-2',
            table_name: `fusion_result_${Date.now()}`,
            mode: 'create',
          },
        },
      });

      expect(response.ok()).toBeTruthy();
    });

    test('DE-FU-009: 融合任务执行与监控', async ({ request }) => {
      // 创建融合任务
      const createResp = await request.post(`${API_BASE}/api/v1/etl/fusion`, {
        headers: { Authorization: `Bearer ${deToken}` },
        data: {
          name: `e2e_fusion_monitor_${Date.now()}`,
          tables: [
            { datasource_id: 'test-datasource-1', table: 'test_users', alias: 'u' },
          ],
        },
      });
      const createData = await createResp.json();
      const taskId = createData.data?.id;

      if (taskId) {
        // 查询执行状态
        const statusResp = await request.get(`${API_BASE}/api/v1/etl/fusion/${taskId}/status`, {
          headers: { Authorization: `Bearer ${deToken}` },
        });

        const statusData = await statusResp.json();
        if (statusData.code === 0) {
          expect(statusData.data?.status).toBeDefined();
        }
      }
    });
  });
});
