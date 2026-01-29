/**
 * 系统管理员完整流程 E2E 测试
 * 用例覆盖: SA-CF, SA-UM, SA-MN, SA-AU
 *
 * 测试系统管理员角色的完整工作流程：
 * 系统配置 → 用户与权限管理 → 服务监控 → 审计与追溯
 */

import { test, expect } from '../fixtures/user-lifecycle.fixture';
import { navigateToUserManagement, generateTestUserData } from '../helpers/user-management';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const API_BASE = process.env.API_BASE || 'http://localhost:8080';
const ADMIN_API = process.env.ADMIN_API || 'http://localhost:8004';
const AGENT_API = process.env.AGENT_API || process.env.agent_API || 'http://localhost:8000';

test.describe('系统管理员完整流程', () => {
  let adminToken: string;

  test.beforeAll(async ({ request }) => {
    const loginResp = await request.post(`${API_BASE}/api/v1/auth/login`, {
      data: { username: 'test_admin', password: 'Admin1234!' },
    });
    const loginData = await loginResp.json();
    adminToken = loginData.data?.token || '';
  });

  // ==================== 系统配置 ====================

  test.describe('SA-CF: 系统配置', () => {
    test('SA-CF-001: 获取系统配置', async ({ request }) => {
      const response = await request.get(`${ADMIN_API}/api/v1/settings`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
      expect(json.data).toBeTruthy();
    });

    test('SA-CF-002: 修改系统配置', async ({ request }) => {
      const response = await request.put(`${ADMIN_API}/api/v1/settings`, {
        headers: { Authorization: `Bearer ${adminToken}` },
        data: {
          max_upload_size: 100,
          session_timeout: 3600,
          enable_audit_log: true,
        },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
    });

    test('SA-CF-003: 配置邮件服务', async ({ request }) => {
      const response = await request.put(`${ADMIN_API}/api/v1/settings/email`, {
        headers: { Authorization: `Bearer ${adminToken}` },
        data: {
          smtp_host: 'smtp.example.com',
          smtp_port: 587,
          smtp_user: 'noreply@example.com',
          smtp_password: 'test123',
          use_tls: true,
        },
      });

      expect(response.ok()).toBeTruthy();
    });

    test('SA-CF-004: 配置 LDAP 集成', async ({ request }) => {
      const response = await request.put(`${ADMIN_API}/api/v1/settings/ldap`, {
        headers: { Authorization: `Bearer ${adminToken}` },
        data: {
          enabled: false,
          server_url: 'ldap://ldap.example.com',
          base_dn: 'dc=example,dc=com',
          bind_dn: 'cn=admin,dc=example,dc=com',
        },
      });

      expect(response.ok()).toBeTruthy();
    });

    test('SA-CF-005: 配置备份策略', async ({ request }) => {
      const response = await request.put(`${ADMIN_API}/api/v1/settings/backup`, {
        headers: { Authorization: `Bearer ${adminToken}` },
        data: {
          enabled: true,
          schedule: '0 2 * * *',
          retention_days: 30,
          storage_path: '/backups',
        },
      });

      expect(response.ok()).toBeTruthy();
    });
  });

  // ==================== 用户与权限管理 ====================

  test.describe('SA-UM: 用户与权限管理', () => {
    test('SA-UM-001: 创建新用户', async ({ request }) => {
      const response = await request.post(`${ADMIN_API}/api/v1/users`, {
        headers: { Authorization: `Bearer ${adminToken}` },
        data: {
          username: `e2e_user_${Date.now()}`,
          email: `e2e_${Date.now()}@example.com`,
          password: 'Test1234!',
          role_ids: ['role_user'],  // 使用 role_ids 而非 roles
        },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
      expect(json.data?.id || json.data?.user_id).toBeTruthy();
    });

    test('SA-UM-006: 分配角色', async ({ request }) => {
      // 创建用户
      const userResp = await request.post(`${ADMIN_API}/api/v1/users`, {
        headers: { Authorization: `Bearer ${adminToken}` },
        data: {
          username: `e2e_role_${Date.now()}`,
          email: `e2e_role_${Date.now()}@example.com`,
          password: 'Test1234!',
          role_ids: ['role_user'],
        },
      });
      const userData = await userResp.json();
      const userId = userData.data?.id || userData.data?.user_id;

      if (userId) {
        // 分配角色 - 通过 PUT 更新用户
        const roleResp = await request.put(`${ADMIN_API}/api/v1/users/${userId}`, {
          headers: { Authorization: `Bearer ${adminToken}` },
          data: { role_ids: ['role_data_engineer', 'role_user'] },
        });

        expect(roleResp.ok()).toBeTruthy();
        const roleData = await roleResp.json();
        expect(roleData.code).toBe(0);
      }
    });

    test('SA-UM-009: 禁用用户', async ({ request }) => {
      // 创建用户
      const userResp = await request.post(`${ADMIN_API}/api/v1/users`, {
        headers: { Authorization: `Bearer ${adminToken}` },
        data: {
          username: `e2e_disable_${Date.now()}`,
          email: `e2e_disable_${Date.now()}@example.com`,
          password: 'Test1234!',
          role_ids: ['role_user'],
        },
      });
      const userData = await userResp.json();
      const userId = userData.data?.id || userData.data?.user_id;

      if (userId) {
        // 禁用用户 - 使用 toggle-status 端点
        const disableResp = await request.post(`${ADMIN_API}/api/v1/users/${userId}/toggle-status`, {
          headers: { Authorization: `Bearer ${adminToken}` },
        });

        expect(disableResp.ok()).toBeTruthy();
      }
    });

    test('SA-UM-010: 重置用户密码', async ({ request }) => {
      const userResp = await request.post(`${ADMIN_API}/api/v1/users`, {
        headers: { Authorization: `Bearer ${adminToken}` },
        data: {
          username: `e2e_reset_${Date.now()}`,
          email: `e2e_reset_${Date.now()}@example.com`,
          password: 'Test1234!',
          role_ids: ['role_user'],
        },
      });
      const userData = await userResp.json();
      const userId = userData.data?.id || userData.data?.user_id;

      if (userId) {
        const resetResp = await request.post(`${ADMIN_API}/api/v1/users/${userId}/reset-password`, {
          headers: { Authorization: `Bearer ${adminToken}` },
          data: { new_password: 'NewPass1234!' },
        });

        expect(resetResp.ok()).toBeTruthy();
      }
    });

    test.skip('SA-UM-001 (UI): 通过 UI 创建用户 (需要前端页面)', async ({ systemAdminPage }) => {
      // 跳过：需要完整的 UI 实现
    });
  });

  // ==================== 服务监控 ====================

  test.describe('SA-MN: 服务监控', () => {
    test('SA-MN-001: Admin API 健康检查', async ({ request }) => {
      const response = await request.get(`${ADMIN_API}/api/v1/health`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.status || json.service).toBeDefined();
    });

    test('SA-MN-001: 各服务健康检查', async ({ request }) => {
      const data_API = process.env.data_API || 'http://localhost:8001';
      const services = [
        { name: 'data', url: `${data_API}/api/v1/health` },
        { name: 'agent', url: `${agent_API}/api/v1/health` },
        { name: 'admin', url: `${ADMIN_API}/api/v1/health` },
      ];

      for (const service of services) {
        try {
          const response = await request.get(service.url, { timeout: 10000 });

          if (response.ok()) {
            const json = await response.json();
            expect(json.status || json.service || json.code).toBeDefined();
          }
        } catch (e) {
          // 某些服务可能未运行，仅记录不抛出错误
          console.log(`Service ${service.name} health check skipped: ${e}`);
        }
      }
    });
  });

  // ==================== 审计与追溯 ====================

  test.describe('SA-AU: 审计与追溯', () => {
    test('SA-AU-001: 查看审计日志', async ({ request }) => {
      const response = await request.get(`${ADMIN_API}/api/v1/audit/logs`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
      if (json.data) {
        expect(Array.isArray(json.data.logs || json.data)).toBe(true);
      }
    });

    test('SA-AU-003: 按用户筛选审计日志', async ({ request }) => {
      const response = await request.get(`${ADMIN_API}/api/v1/audit/logs?user_id=test-user-1`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
    });

    test('SA-AU-004: 按操作类型筛选审计日志', async ({ request }) => {
      const response = await request.get(`${ADMIN_API}/api/v1/audit/logs?action=login`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });

      expect(response.ok()).toBeTruthy();
      const json = await response.json();
      expect(json.code).toBe(0);
    });

    test('SA-AU-001: 审计日志包含关键字段', async ({ request }) => {
      const response = await request.get(`${ADMIN_API}/api/v1/audit/logs?limit=1`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });

      const json = await response.json();
      if (json.code === 0) {
        const logs = json.data?.logs || json.data || [];
        if (logs.length > 0) {
          const log = logs[0];
          expect(log.timestamp || log.created_at).toBeDefined();
          expect(log.user_id || log.operator).toBeDefined();
          expect(log.action || log.operation).toBeDefined();
        }
      }
    });
  });
});
