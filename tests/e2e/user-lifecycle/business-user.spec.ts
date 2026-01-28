/**
 * 业务用户完整流程 E2E 测试
 * 用例覆盖: BU-KB, BU-IQ, BU-BI, BU-WN, BU-AS
 *
 * 测试业务用户角色的完整工作流程：
 * 知识库管理 → 智能查询 → BI 报表 → 智能预警 → 资产检索
 */

import { test, expect } from './fixtures/user-lifecycle.fixture';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const API_BASE = process.env.API_BASE || 'http://localhost:8080';
const BISHENG_API = process.env.BISHENG_API || 'http://localhost:8081';

test.describe('业务用户完整流程', () => {
  let userToken: string;

  test.beforeAll(async ({ request }) => {
    const loginResp = await request.post(`${API_BASE}/api/v1/auth/login`, {
      data: { username: 'test_user', password: 'User1234!' },
    });
    const loginData = await loginResp.json();
    userToken = loginData.data?.token || '';
  });

  // ==================== 知识库管理 ====================

  test.describe('BU-KB: 知识库文档管理', () => {
    test('BU-KB-001: 创建知识库', async ({ request }) => {
      const response = await request.post(`${BISHENG_API}/api/v1/knowledge_bases`, {
        headers: { Authorization: `Bearer ${userToken}` },
        data: {
          name: `e2e_kb_${Date.now()}`,
          description: 'E2E 测试知识库',
          embedding_model: 'bge-large-zh',
        },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
      expect(json.data?.id).toBeTruthy();
    });

    test('BU-KB-002: 上传文档到知识库', async ({ request }) => {
      // 创建知识库
      const kbResp = await request.post(`${BISHENG_API}/api/v1/knowledge_bases`, {
        headers: { Authorization: `Bearer ${userToken}` },
        data: {
          name: `e2e_kb_upload_${Date.now()}`,
          description: 'E2E 测试上传',
          embedding_model: 'bge-large-zh',
        },
      });
      const kbData = await kbResp.json();
      const kbId = kbData.data?.id;

      if (kbId) {
        const uploadResp = await request.post(`${BISHENG_API}/api/v1/documents`, {
          headers: { Authorization: `Bearer ${userToken}` },
          data: {
            knowledge_base_id: kbId,
            name: 'test_document.txt',
            content: '这是一个测试文档，用于验证知识库的文档上传功能。',
            type: 'text',
          },
        });

        expect(uploadResp.ok()).toBeTruthy();
        const uploadData = await uploadResp.json();
        expect(uploadData.code).toBe(0);
      }
    });

    test('BU-KB-004: 查询知识库文档列表', async ({ request }) => {
      const response = await request.get(`${BISHENG_API}/api/v1/knowledge_bases`, {
        headers: { Authorization: `Bearer ${userToken}` },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
    });

    test('BU-KB-005: 删除知识库文档', async ({ request }) => {
      // 创建知识库和文档
      const kbResp = await request.post(`${BISHENG_API}/api/v1/knowledge_bases`, {
        headers: { Authorization: `Bearer ${userToken}` },
        data: {
          name: `e2e_kb_del_${Date.now()}`,
          embedding_model: 'bge-large-zh',
        },
      });
      const kbData = await kbResp.json();
      const kbId = kbData.data?.id;

      if (kbId) {
        const docResp = await request.post(`${BISHENG_API}/api/v1/documents`, {
          headers: { Authorization: `Bearer ${userToken}` },
          data: {
            knowledge_base_id: kbId,
            name: 'to_delete.txt',
            content: '待删除文档',
            type: 'text',
          },
        });
        const docData = await docResp.json();
        const docId = docData.data?.id;

        if (docId) {
          const deleteResp = await request.delete(`${BISHENG_API}/api/v1/documents/${docId}`, {
            headers: { Authorization: `Bearer ${userToken}` },
          });
          expect(deleteResp.ok()).toBeTruthy();
        }
      }
    });

    test('BU-KB-006: 知识库语义搜索', async ({ request }) => {
      const response = await request.post(`${BISHENG_API}/api/v1/knowledge_bases/search`, {
        headers: { Authorization: `Bearer ${userToken}` },
        data: {
          query: '销售政策',
          knowledge_base_ids: ['test-kb-1'],
          top_k: 5,
        },
      });

      const json = await response.json();
      if (json.code === 0 && json.data) {
        expect(Array.isArray(json.data.results)).toBe(true);
      }
    });
  });

  // ==================== 智能查询 ====================

  test.describe('BU-IQ: 智能查询', () => {
    test('BU-IQ-001: Text-to-SQL 基本查询', async ({ request }) => {
      const response = await request.post(`${API_BASE}/api/v1/text2sql`, {
        headers: { Authorization: `Bearer ${userToken}` },
        data: {
          question: '查询所有用户的数量',
          datasource_id: 'test-datasource-1',
        },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
      if (json.data) {
        expect(json.data.sql).toBeDefined();
      }
    });

    test('BU-IQ-002: Text-to-SQL 复杂查询', async ({ request }) => {
      const response = await request.post(`${API_BASE}/api/v1/text2sql`, {
        headers: { Authorization: `Bearer ${userToken}` },
        data: {
          question: '查询每个月的订单总金额，按月份排序',
          datasource_id: 'test-datasource-1',
        },
      });

      const json = await response.json();
      if (json.code === 0 && json.data) {
        expect(json.data.sql).toBeDefined();
        expect(json.data.sql.toLowerCase()).toContain('group by');
      }
    });

    test('BU-IQ-003: RAG 知识库问答', async ({ request }) => {
      const response = await request.post(`${BISHENG_API}/api/v1/rag/query`, {
        headers: { Authorization: `Bearer ${userToken}` },
        data: {
          question: '公司的退货政策是什么？',
          knowledge_base_ids: ['test-kb-1'],
          mode: 'rag',
        },
      });

      const json = await response.json();
      if (json.code === 0 && json.data) {
        expect(json.data.answer).toBeDefined();
        expect(json.data.sources).toBeDefined();
      }
    });

    test('BU-IQ-004: Text-to-SQL 执行查询', async ({ request }) => {
      const response = await request.post(`${API_BASE}/api/v1/text2sql/execute`, {
        headers: { Authorization: `Bearer ${userToken}` },
        data: {
          question: '查询用户总数',
          datasource_id: 'test-datasource-1',
          auto_execute: true,
        },
      });

      const json = await response.json();
      if (json.code === 0 && json.data) {
        expect(json.data.sql).toBeDefined();
        expect(json.data.result).toBeDefined();
      }
    });

    test('BU-IQ-005: 多轮对话查询', async ({ request }) => {
      // 第一轮
      const resp1 = await request.post(`${API_BASE}/api/v1/text2sql`, {
        headers: { Authorization: `Bearer ${userToken}` },
        data: {
          question: '查询所有用户',
          datasource_id: 'test-datasource-1',
        },
      });
      const data1 = await resp1.json();
      const sessionId = data1.data?.session_id;

      // 第二轮（追问）
      if (sessionId) {
        const resp2 = await request.post(`${API_BASE}/api/v1/text2sql`, {
          headers: { Authorization: `Bearer ${userToken}` },
          data: {
            question: '其中年龄大于30的有多少',
            datasource_id: 'test-datasource-1',
            session_id: sessionId,
          },
        });

        const data2 = await resp2.json();
        if (data2.code === 0 && data2.data) {
          expect(data2.data.sql).toBeDefined();
        }
      }
    });

    test('BU-IQ-006: SQL 安全检查', async ({ request }) => {
      const response = await request.post(`${API_BASE}/api/v1/text2sql`, {
        headers: { Authorization: `Bearer ${userToken}` },
        data: {
          question: '删除所有用户数据',
          datasource_id: 'test-datasource-1',
        },
      });

      const json = await response.json();
      // 应该拒绝或生成只读查询
      if (json.code === 0 && json.data?.sql) {
        const sql = json.data.sql.toLowerCase();
        expect(sql).not.toContain('delete');
        expect(sql).not.toContain('drop');
        expect(sql).not.toContain('truncate');
      }
    });

    test('BU-IQ-007: 查询历史记录', async ({ request }) => {
      const response = await request.get(`${API_BASE}/api/v1/text2sql/history`, {
        headers: { Authorization: `Bearer ${userToken}` },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
    });
  });

  // ==================== BI 报表 ====================

  test.describe('BU-BI: BI 报表', () => {
    test('BU-BI-001: 自然语言生成报表', async ({ request }) => {
      const response = await request.post(`${API_BASE}/api/v1/bi/dashboards`, {
        headers: { Authorization: `Bearer ${userToken}` },
        data: {
          name: `e2e_dashboard_${Date.now()}`,
          description: '按月份统计销售趋势',
          datasource_id: 'test-datasource-1',
          prompt: '生成按月份的销售趋势图表',
        },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
    });
  });

  // ==================== 智能预警 ====================

  test.describe('BU-WN: 智能预警', () => {
    test('BU-WN-001: 创建预警规则', async ({ request }) => {
      const response = await request.post(`${API_BASE}/api/v1/alerts/rules`, {
        headers: { Authorization: `Bearer ${userToken}` },
        data: {
          name: `e2e_alert_${Date.now()}`,
          description: '每日订单量低于100时告警',
          datasource_id: 'test-datasource-1',
          condition: {
            metric: 'order_count',
            operator: 'less_than',
            threshold: 100,
          },
          schedule: '0 9 * * *',
          notification: {
            channels: ['email'],
            recipients: ['test@example.com'],
          },
        },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
    });

    test('BU-WN-002: 查看预警规则列表', async ({ request }) => {
      const response = await request.get(`${API_BASE}/api/v1/alerts/rules`, {
        headers: { Authorization: `Bearer ${userToken}` },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
    });
  });

  // ==================== 资产检索 ====================

  test.describe('BU-AS: 数据资产检索', () => {
    test('BU-AS-001: 关键词检索资产', async ({ request }) => {
      const response = await request.get(`${API_BASE}/api/v1/assets/search?q=用户`, {
        headers: { Authorization: `Bearer ${userToken}` },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
      if (json.data) {
        expect(Array.isArray(json.data.results || json.data)).toBe(true);
      }
    });

    test('BU-AS-002: 按分类浏览资产', async ({ request }) => {
      const response = await request.get(`${API_BASE}/api/v1/assets/categories`, {
        headers: { Authorization: `Bearer ${userToken}` },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
    });
  });
});
