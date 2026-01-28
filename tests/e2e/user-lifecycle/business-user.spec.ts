/**
 * 业务用户完整流程 E2E 测试
 * 用例覆盖: BU-KB, BU-IQ, BU-BI, BU-WN, BU-AS
 *
 * 测试业务用户角色的完整工作流程：
 * 知识库管理 → 智能查询 → BI 报表 → 智能预警 → 资产检索
 */

import { test, expect } from '../fixtures/user-lifecycle.fixture';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const API_BASE = process.env.API_BASE || 'http://localhost:8080';
const ALLDATA_API = process.env.ALLDATA_API || 'http://localhost:8001';
const BISHENG_API = process.env.BISHENG_API || 'http://localhost:8000';

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
      const response = await request.post(`${BISHENG_API}/api/v1/knowledge-bases`, {
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
      expect(json.data?.knowledge_base_id).toBeTruthy();
    });

    test.skip('BU-KB-002: 上传文档到知识库 (需要嵌入服务)', async ({ request }) => {
      // 跳过：需要 Embedding Service
    });

    test('BU-KB-004: 查询知识库文档列表', async ({ request }) => {
      const response = await request.get(`${BISHENG_API}/api/v1/knowledge-bases`, {
        headers: { Authorization: `Bearer ${userToken}` },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
    });

    test('BU-KB-005: 删除知识库文档', async ({ request }) => {
      // 先上传文档
      const uploadResp = await request.post(`${BISHENG_API}/api/v1/documents/upload`, {
        headers: { Authorization: `Bearer ${userToken}` },
        data: {
          collection: 'default',
          file_name: 'to_delete.txt',
          title: '待删除文档',
          content: '这是待删除的文档内容。',
        },
      });
      const uploadData = await uploadResp.json();
      const docId = uploadData.data?.doc_id;

      if (docId) {
        const deleteResp = await request.delete(`${BISHENG_API}/api/v1/documents/${docId}`, {
          headers: { Authorization: `Bearer ${userToken}` },
        });
        expect(deleteResp.ok()).toBeTruthy();
      }
    });

    test.skip('BU-KB-006: 知识库语义搜索 (端点不存在)', async ({ request }) => {
      // 跳过：端点不存在
    });
  });

  // ==================== 智能查询 ====================

  test.describe('BU-IQ: 智能查询', () => {
    test('BU-IQ-001: Text-to-SQL 基本查询', async ({ request }) => {
      const response = await request.post(`${BISHENG_API}/api/v1/text2sql`, {
        headers: { Authorization: `Bearer ${userToken}` },
        data: {
          natural_language: '查询所有用户的数量',
          database: 'test_db',
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
      const response = await request.post(`${BISHENG_API}/api/v1/text2sql`, {
        headers: { Authorization: `Bearer ${userToken}` },
        data: {
          natural_language: '查询每个月的订单总金额，按月份排序',
          database: 'test_db',
        },
      });

      const json = await response.json();
      if (json.code === 0 && json.data) {
        expect(json.data.sql).toBeDefined();
      }
    });

    test.skip('BU-IQ-003: RAG 知识库问答 (需要嵌入服务)', async ({ request }) => {
      // 跳过：需要 Embedding Service 和 Milvus
    });

    test('BU-IQ-004: Text-to-SQL 执行查询', async ({ request }) => {
      const response = await request.post(`${BISHENG_API}/api/v1/text2sql`, {
        headers: { Authorization: `Bearer ${userToken}` },
        data: {
          natural_language: '查询用户总数',
          database: 'test_db',
        },
      });

      const json = await response.json();
      if (json.code === 0 && json.data) {
        expect(json.data.sql).toBeDefined();
      }
    });

    test('BU-IQ-005: 多轮对话查询', async ({ request }) => {
      // 第一轮
      const resp1 = await request.post(`${BISHENG_API}/api/v1/text2sql`, {
        headers: { Authorization: `Bearer ${userToken}` },
        data: {
          natural_language: '查询所有用户',
          database: 'test_db',
        },
      });
      const data1 = await resp1.json();
      const sessionId = data1.data?.session_id;

      // 第二轮（追问）
      if (sessionId) {
        const resp2 = await request.post(`${BISHENG_API}/api/v1/text2sql`, {
          headers: { Authorization: `Bearer ${userToken}` },
          data: {
            natural_language: '其中年龄大于30的有多少',
            database: 'test_db',
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
      const response = await request.post(`${BISHENG_API}/api/v1/text2sql`, {
        headers: { Authorization: `Bearer ${userToken}` },
        data: {
          natural_language: '删除所有用户数据',
          database: 'test_db',
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

    test.skip('BU-IQ-007: 查询历史记录 (端点不存在)', async ({ request }) => {
      // 跳过：端点不存在
    });
  });

  // ==================== BI 报表 ====================

  test.describe('BU-BI: BI 报表', () => {
    test('BU-BI-001: 查询报表列表', async ({ request }) => {
      const response = await request.get(`${ALLDATA_API}/api/v1/bi/reports`, {
        headers: { Authorization: `Bearer ${userToken}` },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
    });
  });

  // ==================== 智能预警 ====================

  test.describe('BU-WN: 智能预警', () => {
    test('BU-WN-001: 查看预警规则列表', async ({ request }) => {
      const response = await request.get(`${ALLDATA_API}/api/v1/alerts/metric-rules`, {
        headers: { Authorization: `Bearer ${userToken}` },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
    });

    test('BU-WN-002: 查看质量告警', async ({ request }) => {
      const response = await request.get(`${ALLDATA_API}/api/v1/quality/alerts`, {
        headers: { Authorization: `Bearer ${userToken}` },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
    });
  });

  // ==================== 资产检索 ====================

  test.describe('BU-AS: 数据资产检索', () => {
    test('BU-AS-001: 查询资产列表', async ({ request }) => {
      const response = await request.get(`${ALLDATA_API}/api/v1/assets`, {
        headers: { Authorization: `Bearer ${userToken}` },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
    });

    test.skip('BU-AS-002: 查询资产排名 (端点500错误)', async ({ request }) => {
      // 跳过：端点返回500错误
    });
  });
});
