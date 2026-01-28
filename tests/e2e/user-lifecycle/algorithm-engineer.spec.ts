/**
 * 算法工程师完整流程 E2E 测试
 * 用例覆盖: AE-NB, AE-TR, AE-DP, AE-EV
 *
 * 测试算法工程师角色的完整工作流程：
 * Notebook 环境 → 模型训练 → 模型评估 → 模型部署与 API
 */

import { test, expect } from './fixtures/user-lifecycle.fixture';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const API_BASE = process.env.API_BASE || 'http://localhost:8080';
const CUBE_API = process.env.CUBE_API || 'http://localhost:8083';

test.describe('算法工程师完整流程', () => {
  let aiToken: string;

  test.beforeAll(async ({ request }) => {
    const loginResp = await request.post(`${API_BASE}/api/v1/auth/login`, {
      data: { username: 'test_ai', password: 'Ai1234!' },
    });
    const loginData = await loginResp.json();
    aiToken = loginData.data?.token || '';
  });

  // ==================== Notebook 环境 ====================

  test.describe('AE-NB: Notebook 环境', () => {
    test('AE-NB-001: 创建 Jupyter Notebook 实例', async ({ request }) => {
      const response = await request.post(`${CUBE_API}/api/v1/notebooks`, {
        headers: { Authorization: `Bearer ${aiToken}` },
        data: {
          name: `e2e_notebook_${Date.now()}`,
          image: 'jupyter/scipy-notebook:latest',
          resource: { cpu: '2', memory: '4Gi', gpu: '0' },
        },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
      expect(json.data?.id).toBeTruthy();
    });

    test('AE-NB-002: 查看 Notebook 列表', async ({ request }) => {
      const response = await request.get(`${CUBE_API}/api/v1/notebooks`, {
        headers: { Authorization: `Bearer ${aiToken}` },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
      expect(Array.isArray(json.data)).toBe(true);
    });

    test('AE-NB-003: 停止 Notebook 实例', async ({ request }) => {
      // 创建一个 notebook
      const createResp = await request.post(`${CUBE_API}/api/v1/notebooks`, {
        headers: { Authorization: `Bearer ${aiToken}` },
        data: {
          name: `e2e_nb_stop_${Date.now()}`,
          image: 'jupyter/scipy-notebook:latest',
          resource: { cpu: '1', memory: '2Gi' },
        },
      });
      const createData = await createResp.json();
      const nbId = createData.data?.id;

      if (nbId) {
        const stopResp = await request.post(`${CUBE_API}/api/v1/notebooks/${nbId}/stop`, {
          headers: { Authorization: `Bearer ${aiToken}` },
        });

        expect(stopResp.ok()).toBeTruthy();
      }
    });
  });

  // ==================== 模型训练 ====================

  test.describe('AE-TR: 模型训练', () => {
    test('AE-TR-001: 创建训练实验', async ({ request }) => {
      const response = await request.post(`${CUBE_API}/api/v1/experiments`, {
        headers: { Authorization: `Bearer ${aiToken}` },
        data: {
          name: `e2e_experiment_${Date.now()}`,
          description: 'E2E 测试训练实验',
          framework: 'pytorch',
          dataset_id: 'test-dataset-1',
        },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
      expect(json.data?.id).toBeTruthy();
    });

    test('AE-TR-004: 提交训练作业', async ({ request }) => {
      // 创建实验
      const expResp = await request.post(`${CUBE_API}/api/v1/experiments`, {
        headers: { Authorization: `Bearer ${aiToken}` },
        data: {
          name: `e2e_train_job_${Date.now()}`,
          framework: 'pytorch',
          dataset_id: 'test-dataset-1',
        },
      });
      const expData = await expResp.json();
      const expId = expData.data?.id;

      if (expId) {
        const trainResp = await request.post(`${CUBE_API}/api/v1/experiments/${expId}/runs`, {
          headers: { Authorization: `Bearer ${aiToken}` },
          data: {
            hyperparameters: {
              learning_rate: 0.001,
              batch_size: 32,
              epochs: 10,
            },
            resource: { cpu: '4', memory: '8Gi', gpu: '1' },
          },
        });

        expect(trainResp.ok()).toBeTruthy();
        const trainData = await trainResp.json();
        expect(trainData.code).toBe(0);
        expect(trainData.data?.run_id).toBeTruthy();
      }
    });

    test('AE-TR-005: 查看训练日志', async ({ request }) => {
      const response = await request.get(`${CUBE_API}/api/v1/experiments?status=completed&limit=1`, {
        headers: { Authorization: `Bearer ${aiToken}` },
      });

      const json = await response.json();
      if (json.code === 0 && json.data?.length > 0) {
        const expId = json.data[0].id;
        const logResp = await request.get(`${CUBE_API}/api/v1/experiments/${expId}/logs`, {
          headers: { Authorization: `Bearer ${aiToken}` },
        });
        expect(logResp.ok()).toBeTruthy();
      }
    });

    test('AE-TR-008: 注册训练模型', async ({ request }) => {
      const response = await request.post(`${CUBE_API}/api/v1/models/register`, {
        headers: { Authorization: `Bearer ${aiToken}` },
        data: {
          name: `e2e_model_${Date.now()}`,
          version: '1.0.0',
          framework: 'pytorch',
          experiment_id: 'test-experiment-1',
          run_id: 'test-run-1',
          metrics: { accuracy: 0.95, f1_score: 0.93 },
        },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
    });
  });

  // ==================== 模型评估 ====================

  test.describe('AE-EV: 模型评估', () => {
    test('AE-EV-001: 创建评估任务', async ({ request }) => {
      const response = await request.post(`${CUBE_API}/api/v1/evaluation`, {
        headers: { Authorization: `Bearer ${aiToken}` },
        data: {
          model_id: 'test-model-1',
          dataset_id: 'test-dataset-eval-1',
          metrics: ['accuracy', 'precision', 'recall', 'f1'],
        },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
    });
  });

  // ==================== 模型部署 ====================

  test.describe('AE-DP: 模型部署与 API', () => {
    test('AE-DP-001: 创建模型部署', async ({ request }) => {
      const response = await request.post(`${CUBE_API}/api/v1/deployments`, {
        headers: { Authorization: `Bearer ${aiToken}` },
        data: {
          name: `e2e_deploy_${Date.now()}`,
          model_id: 'test-model-1',
          model_version: '1.0.0',
          runtime: 'vllm',
          resource: { cpu: '4', memory: '8Gi', gpu: '1' },
          replicas: 1,
        },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
      expect(json.data?.id).toBeTruthy();
    });

    test('AE-DP-002: 查看部署状态', async ({ request }) => {
      const response = await request.get(`${CUBE_API}/api/v1/deployments`, {
        headers: { Authorization: `Bearer ${aiToken}` },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
    });

    test('AE-DP-004: 调用模型推理 API', async ({ request }) => {
      // 查找已有部署
      const listResp = await request.get(`${CUBE_API}/api/v1/deployments?status=running`, {
        headers: { Authorization: `Bearer ${aiToken}` },
      });
      const listData = await listResp.json();

      if (listData.data?.length > 0) {
        const deployId = listData.data[0].id;
        const inferResp = await request.post(`${CUBE_API}/api/v1/deployments/${deployId}/predict`, {
          headers: { Authorization: `Bearer ${aiToken}` },
          data: {
            inputs: [{ text: 'test input data' }],
          },
        });

        const inferData = await inferResp.json();
        if (inferData.code === 0) {
          expect(inferData.data?.predictions).toBeDefined();
        }
      }
    });

    test('AE-DP-005: OpenAI 兼容 API 调用', async ({ request }) => {
      const openaiProxy = process.env.OPENAI_PROXY || 'http://localhost:8000';

      const response = await request.post(`${openaiProxy}/v1/chat/completions`, {
        headers: {
          Authorization: `Bearer ${aiToken}`,
          'Content-Type': 'application/json',
        },
        data: {
          model: 'test-model',
          messages: [
            { role: 'user', content: '你好' },
          ],
          max_tokens: 100,
        },
      });

      if (response.ok()) {
        const json = await response.json();
        expect(json.choices).toBeDefined();
        expect(json.choices.length).toBeGreaterThan(0);
      }
    });

    test('AE-DP-006: 部署扩缩容', async ({ request }) => {
      const listResp = await request.get(`${CUBE_API}/api/v1/deployments?status=running`, {
        headers: { Authorization: `Bearer ${aiToken}` },
      });
      const listData = await listResp.json();

      if (listData.data?.length > 0) {
        const deployId = listData.data[0].id;
        const scaleResp = await request.patch(`${CUBE_API}/api/v1/deployments/${deployId}/scale`, {
          headers: { Authorization: `Bearer ${aiToken}` },
          data: { replicas: 2 },
        });

        expect(scaleResp.ok()).toBeTruthy();
      }
    });
  });
});
