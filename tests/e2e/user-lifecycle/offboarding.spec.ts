/**
 * 用户离职流程 E2E 测试
 * 测试用例编号: LC-OF-E-001 ~ LC-OF-E-005
 *
 * 阶段5: 离职处理流程
 * - 正常离职（权限降级）
 * - 紧急离职（立即停用）
 * - 用户删除
 * - 资源所有权转移
 */

import { test, expect } from '@playwright/test';

// ==================== 常量定义 ====================

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

// ==================== 测试套件 ====================

test.describe('User Offboarding - Normal Process', () => {
  test('LC-OF-E-001: Normal offboarding - Revoke roles then disable', async ({ page }) => {
    /** 测试场景：正常离职流程
     *
     * 前置条件：
     * - 用户拥有多个角色
     * - 用户状态为 active
     *
     * 测试步骤：
     * 1. 管理员在用户管理页面找到用户
     * 2. 撤销所有角色
     * 3. 停用用户
     *
     * 预期结果：
     * - 用户角色全部撤销
     * - 用户状态变为 inactive
     * - 用户无法登录
     */

    // Mock 用户数据
    await page.route('**/api/v1/users/*', async (route) => {
      const url = route.request().url();
      if (route.request().method() === 'PATCH') {
        // 停用用户
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              user_id: 'user_offboard_001',
              username: 'offboard_user',
              status: 'inactive',
              roles: []
            }
          })
        });
      } else if (route.request().method() === 'DELETE') {
        // 撤销角色
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              user_id: 'user_offboard_001',
              roles: []
            }
          })
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              user_id: 'user_offboard_001',
              username: 'offboard_user',
              email: 'offboard@example.com',
              status: 'active',
              roles: ['data_engineer', 'data_admin']
            }
          })
        });
      }
    });

    // 导航到用户管理页面
    await page.goto(`${BASE_URL}/admin/users`);

    // 搜索用户
    await page.fill('[data-testid="search-input"]', 'offboard_user');
    await page.press('[data-testid="search-input"]', 'Enter');

    // 点击用户
    await page.click('tr:has-text("offboard_user")');
    await page.click('[data-testid="edit-user-button"]');

    // 撤销所有角色
    await page.uncheck('[data-testid="role-data_engineer"]');
    await page.uncheck('[data-testid="role-data_admin"]');

    // 保存
    await page.click('button:has-text("保存")');
    await expect(page.locator('.toast-message:has-text("更新成功")')).toBeVisible();

    // 停用用户
    await page.click('[data-testid="disable-user-button"]');
    await page.click('.ant-modal button:has-text("确定")');

    // 验证用户状态变为 inactive
    await expect(page.locator('[data-user-id="user_offboard_001"] [data-testid="user-status"]')).toHaveText('inactive');
  });

  test('LC-OF-E-002: Disabled user cannot login', async ({ page }) => {
    /** 测试场景：验证停用用户无法登录
     *
     * 前置条件：
     * - 用户状态为 inactive
     *
     * 测试步骤：
     * 1. 尝试使用停用用户凭证登录
     *
     * 预期结果：
     * - 登录失败
     * - 显示账户已停用提示
     */

    // Mock 登录 API 返回账户已停用
    await page.route('**/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 403,
          message: '账户已被停用，无法登录',
          error: 'USER_DISABLED'
        })
      });
    });

    // 导航到登录页
    await page.goto(`${BASE_URL}/login`);

    // 输入凭证
    await page.fill('input[name="username"]', 'offboard_user');
    await page.fill('input[name="password"]', 'password123');

    // 尝试登录
    await page.click('button[type="submit"]');

    // 验证错误消息
    await expect(page.locator('.error-message:has-text("账户已被停用")')).toBeVisible();
  });
});

test.describe('User Offboarding - Emergency Process', () => {
  test('LC-OF-E-003: Emergency offboarding - Immediate disable', async ({ page }) => {
    /** 测试场景：紧急离职流程
     *
     * 前置条件：
     * - 用户拥有敏感角色（如系统管理员）
     * - 需要立即停用
     *
     * 测试步骤：
     * 1. 管理员在用户管理页面找到用户
     * 2. 直接点击"立即停用"按钮
     * 3. 确认停用
     *
     * 预期结果：
     * - 用户立即被停用
     * - 所有权限立即失效
     * - 记录紧急停用审计日志
     */

    // Mock API
    await page.route('**/api/v1/users/*/emergency-disable', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            user_id: 'user_emergency_001',
            username: 'emergency_user',
            status: 'inactive',
            disabled_at: new Date().toISOString(),
            reason: 'emergency'
          }
        })
      });
    });

    // 导航到用户管理页面
    await page.goto(`${BASE_URL}/admin/users`);

    // 搜索用户
    await page.fill('[data-testid="search-input"]', 'emergency_user');
    await page.press('[data-testid="search-input"]', 'Enter');

    // 点击紧急停用按钮
    await page.click('[data-testid="emergency-disable-button"]');

    // 确认停用
    await page.click('.ant-modal button:has-text("确定")');

    // 验证成功消息
    await expect(page.locator('.toast-message:has-text("已紧急停用")')).toBeVisible();

    // 验证状态
    await expect(page.locator('[data-user-id="user_emergency_001"] [data-testid="user-status"]')).toHaveText('inactive');
  });
});

test.describe('User Offboarding - Resource Transfer', () => {
  test('LC-OF-E-004: Transfer resource ownership before offboarding', async ({ page }) => {
    /** 测试场景：离职前资源所有权转移
     *
     * 前置条件：
     * - 用户拥有多个资源（ETL 任务、工作流等）
     * - 有接手人
     *
     * 测试步骤：
     * 1. 管理员在用户详情页面点击"转移资源"
     * 2. 选择接手人
     * 3. 选择要转移的资源类型
     * 4. 确认转移
     *
     * 预期结果：
     * - 资源所有权转移成功
     * - 记录转移审计日志
     */

    // Mock 用户资源数据
    await page.route('**/api/v1/users/*/resources', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            etl_jobs: [
              { id: 'etl_001', name: '用户数据同步' },
              { id: 'etl_002', name: '日志采集' }
            ],
            workflows: [
              { id: 'wf_001', name: 'RAG问答流程' }
            ],
            dashboards: [
              { id: 'dash_001', name: '销售分析' }
            ]
          }
        })
      });
    });

    // Mock 其他用户列表
    await page.route('**/api/v1/users?exclude=*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            users: [
              { user_id: 'user_transfer_001', username: 'transfer_user', display_name: '接手人' }
            ]
          }
        })
      });
    });

    // Mock 转移 API
    await page.route('**/api/v1/users/*/transfer-resources', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            transferred: 4,
            details: {
              etl_jobs: 2,
              workflows: 1,
              dashboards: 1
            }
          }
        })
      });
    });

    // 导航到用户详情页面
    await page.goto(`${BASE_URL}/admin/users/user_offboard_001`);

    // 点击转移资源按钮
    await page.click('[data-testid="transfer-resources-button"]');

    // 选择接手人
    await page.click('[data-testid="successor-select"]');
    await page.click('.ant-select-dropdown-option:has-text("transfer_user")');

    // 选择资源类型
    await page.check('[data-testid="transfer-etl-jobs"]');
    await page.check('[data-testid="transfer-workflows"]');
    await page.check('[data-testid="transfer-dashboards"]');

    // 确认转移
    await page.click('.ant-modal button:has-text("确认转移")');

    // 验证成功消息
    await expect(page.locator('.toast-message:has-text("成功转移 4 个资源")')).toBeVisible();
  });
});

test.describe('User Offboarding - Deletion', () => {
  test('LC-OF-E-005: Soft delete user after offboarding', async ({ page }) => {
    /** 测试场景：离职后软删除用户
     *
     * 前置条件：
     * - 用户状态为 inactive
     * - 所有资源已转移
     *
     * 测试步骤：
     * 1. 管理员在用户管理页面找到用户
     * 2. 点击删除按钮
     * 3. 确认删除
     *
     * 预期结果：
     * - 用户被软删除（状态变为 deleted）
     * - 用户不再出现在正常列表中
     */

    // Mock 删除 API
    await page.route('**/api/v1/users/*', async (route) => {
      const method = route.request().method();
      if (method === 'DELETE') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              user_id: 'user_offboard_001',
              status: 'deleted',
              deleted_at: new Date().toISOString()
            }
          })
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              user_id: 'user_offboard_001',
              username: 'offboard_user',
              status: 'inactive',
              roles: []
            }
          })
        });
      }
    });

    // 导航到用户管理页面
    await page.goto(`${BASE_URL}/admin/users`);

    // 搜索用户
    await page.fill('[data-testid="search-input"]', 'offboard_user');
    await page.press('[data-testid="search-input"]', 'Enter');

    // 点击删除按钮
    await page.click('[data-testid="delete-user-button"]');

    // 确认删除
    await page.click('.ant-modal button:has-text("确定")');

    // 验证成功消息
    await expect(page.locator('.toast-message:has-text("删除成功")')).toBeVisible();

    // 验证用户不再在列表中
    await expect(page.locator('tr:has-text("offboard_user")')).not.toBeVisible();
  });

  test('LC-OF-E-006: View deleted users in archive', async ({ page }) => {
    /** 测试场景：查看已归档（删除）的用户
     *
     * 前置条件：
     * - 有已删除的用户
     *
     * 测试步骤：
     * 1. 导航到用户管理页面
     * 2. 切换到"已归档"标签
     *
     * 预期结果：
     * - 显示所有已删除的用户
     * - 可以恢复已删除用户（可选）
     */

    // Mock 已删除用户列表
    await page.route('**/api/v1/users?status=deleted', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            users: [
              {
                user_id: 'user_deleted_001',
                username: 'deleted_user',
                email: 'deleted@example.com',
                status: 'deleted',
                deleted_at: '2024-01-15T10:00:00Z'
              }
            ],
            total: 1
          }
        })
      });
    });

    // 导航到用户管理页面
    await page.goto(`${BASE_URL}/admin/users`);

    // 切换到已归档标签
    await page.click('[data-testid="tab-deleted"], .ant-tabs-tab:has-text("已归档")');

    // 验证已删除用户显示
    await expect(page.locator('tr:has-text("deleted_user")')).toBeVisible();
    await expect(page.locator('text=2024-01-15')).toBeVisible();
  });
});

test.describe('User Offboarding - Audit Trail', () => {
  test('LC-OF-E-007: View offboarding audit trail', async ({ page }) => {
    /** 测试场景：查看离职审计记录
     *
     * 前置条件：
     * - 用户完成离职流程
     *
     * 测试步骤：
     * 1. 导航到审计日志页面
     * 2. 筛选目标用户
     * 3. 查看完整的离职操作记录
     *
     * 预期结果：
     * - 显示所有离职相关操作
     * - 包括角色撤销、停用、删除等
     */

    // Mock 审计日志
    await page.route('**/api/v1/audit/logs', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            logs: [
              {
                id: 'audit_001',
                action: 'revoke_role',
                user_id: 'user_offboard_001',
                actor: 'admin',
                details: { role: 'data_admin' },
                created_at: '2024-01-15T09:00:00Z'
              },
              {
                id: 'audit_002',
                action: 'revoke_role',
                user_id: 'user_offboard_001',
                actor: 'admin',
                details: { role: 'data_engineer' },
                created_at: '2024-01-15T09:05:00Z'
              },
              {
                id: 'audit_003',
                action: 'disable_user',
                user_id: 'user_offboard_001',
                actor: 'admin',
                details: { reason: 'resignation' },
                created_at: '2024-01-15T09:10:00Z'
              },
              {
                id: 'audit_004',
                action: 'delete_user',
                user_id: 'user_offboard_001',
                actor: 'admin',
                details: {},
                created_at: '2024-01-20T10:00:00Z'
              }
            ],
            total: 4
          }
        })
      });
    });

    // 导航到审计日志页面
    await page.goto(`${BASE_URL}/admin/audit`);

    // 筛选用户
    await page.fill('[data-testid="user-filter"]', 'offboard_user');
    await page.click('[data-testid="filter-button"]');

    // 验证所有离职操作都被记录
    await expect(page.locator('text=revoke_role')).toHaveCount(2);
    await expect(page.locator('text=disable_user')).toBeVisible();
    await expect(page.locator('text=delete_user')).toBeVisible();
  });
});
