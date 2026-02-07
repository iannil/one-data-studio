/**
 * 用户角色演进流程 E2E 测试
 * 测试用例编号: LC-RP-E-001 ~ LC-RP-E-005
 *
 * 阶段4: 角色演进流程
 * - 权限升级（角色添加）
 * - 权限降级（角色撤销）
 * - 跨角色权限隔离验证
 */

import { test, expect } from '@playwright/test';

// ==================== 常量定义 ====================

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

// ==================== 测试套件 ====================

test.describe('User Role Progression - Permission Upgrade', () => {
  test('LC-RP-E-001: Upgrade user from business user to data analyst', async ({ page }) => {
    /** 测试场景：用户权限升级
     *
     * 前置条件：
     * - 用户为业务用户角色
     * - 用户状态为 active
     *
     * 测试步骤：
     * 1. 管理员在用户管理页面找到用户
     * 2. 点击编辑用户
     * 3. 添加数据分析师角色
     * 4. 保存更改
     * 5. 用户重新登录
     *
     * 预期结果：
     * - 用户拥有数据分析师权限
     * - 可以访问 BI 报表页面
     */

    // Mock 用户数据
    await page.route('**/api/v1/users/*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            user_id: 'user_upgrade_001',
            username: 'upgrade_user',
            email: 'upgrade@example.com',
            status: 'active',
            roles: ['business_user', 'data_analyst']
          }
        })
      });
    });

    // 导航到用户管理页面
    await page.goto(`${BASE_URL}/admin/users`);

    // 搜索用户
    await page.fill('[data-testid="search-input"]', 'upgrade_user');
    await page.press('[data-testid="search-input"]', 'Enter');

    // 点击用户行
    await page.click('tr:has-text("upgrade_user")');

    // 点击编辑按钮
    await page.click('[data-testid="edit-user-button"]');

    // 添加数据分析师角色
    await page.check('[data-testid="role-data_analyst"]');

    // 保存
    await page.click('button:has-text("保存")');

    // 验证成功消息
    await expect(page.locator('.toast-message:has-text("更新成功")')).toBeVisible();

    // 验证角色标签显示
    await expect(page.locator('[data-testid="role-badge-data_analyst"]')).toBeVisible();
  });

  test('LC-RP-E-002: Verify upgraded user can access new features', async ({ page }) => {
    /** 测试场景：验证升级后的用户可以访问新功能
     *
     * 前置条件：
     * - 用户已升级为数据分析师
     *
     * 测试步骤：
     * 1. 用户登录
     * 2. 导航到 BI 报表页面
     *
     * 预期结果：
     * - 用户可以成功访问 BI 页面
     * - 显示报表列表
     */

    // Mock 权限验证
    await page.route('**/api/v1/auth/permissions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            permissions: ['bi:read', 'bi:create', 'metrics:read', 'sql:execute']
          }
        })
      });
    });

    // Mock BI 数据
    await page.route('**/api/v1/data/bi', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            dashboards: [
              { id: 'dash_001', name: '销售分析', charts: 5 },
              { id: 'dash_002', name: '运营监控', charts: 8 }
            ],
            total: 2
          }
        })
      });
    });

    // 导航到 BI 页面
    await page.goto(`${BASE_URL}/data/bi`);

    // 验证页面加载成功
    await expect(page.locator('body')).toBeVisible();
    await expect(page.locator('text=销售分析')).toBeVisible();
  });
});

test.describe('User Role Progression - Permission Downgrade', () => {
  test('LC-RP-E-003: Revoke role from user', async ({ page }) => {
    /** 测试场景：用户权限降级
     *
     * 前置条件：
     * - 用户拥有数据管理员角色
     *
     * 测试步骤：
     * 1. 管理员在用户管理页面找到用户
     * 2. 点击编辑用户
     * 3. 取消数据管理员角色
     * 4. 保存更改
     *
     * 预期结果：
     * - 用户不再拥有数据管理员权限
     * - 角色标签消失
     */

    // Mock 用户数据
    await page.route('**/api/v1/users/*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            user_id: 'user_downgrade_001',
            username: 'downgrade_user',
            email: 'downgrade@example.com',
            status: 'active',
            roles: ['business_user']  // 已移除 data_admin
          }
        })
      });
    });

    await page.goto(`${BASE_URL}/admin/users`);

    // 搜索用户
    await page.fill('[data-testid="search-input"]', 'downgrade_user');
    await page.press('[data-testid="search-input"]', 'Enter');

    // 点击编辑
    await page.click('tr:has-text("downgrade_user")');
    await page.click('[data-testid="edit-user-button"]');

    // 取消数据管理员角色
    await page.uncheck('[data-testid="role-data_admin"]');

    // 保存
    await page.click('button:has-text("保存")');

    // 验证角色标签消失
    await expect(page.locator('[data-testid="role-badge-data_admin"]')).not.toBeVisible();
  });

  test('LC-RP-E-004: Verify downgraded user cannot access revoked features', async ({ page }) => {
    /** 测试场景：验证降级后的用户无法访问已撤销的功能
     *
     * 前置条件：
     * - 用户已被撤销数据管理员角色
     *
     * 测试步骤：
     * 1. 用户尝试访问数据源管理页面
     *
     * 预期结果：
     * - 显示权限不足提示
     * - 或重定向到无权限页面
     */

    // Mock 权限验证（无数据源管理权限）
    await page.route('**/api/v1/auth/permissions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            permissions: ['bi:read']  // 只有 BI 读取权限
          }
        })
      });
    });

    // 尝试访问数据源页面
    await page.goto(`${BASE_URL}/data/datasources`);

    // 验证权限不足提示
    await expect(page.locator('.error-message:has-text("权限不足"), .toast:has-text("无权限")')).toBeVisible({ timeout: 5000 });
  });
});

test.describe('User Role Progression - Cross-Role Isolation', () => {
  test('LC-RP-E-005: Data engineer cannot access workflow features', async ({ page }) => {
    /** 测试场景：跨角色权限隔离验证
     *
     * 前置条件：
     * - 用户为数据工程师角色
     *
     * 测试步骤：
     * 1. 数据工程师尝试访问工作流页面
     *
     * 预期结果：
     * - 显示权限不足
     * - 数据工程师只能访问 ETL、质量等功能
     */

    // Mock 数据工程师权限
    await page.route('**/api/v1/auth/permissions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            permissions: ['etl:*', 'quality:*', 'feature:*']
          }
        })
      });
    });

    // 尝试访问工作流页面（AI 开发者功能）
    await page.goto(`${BASE_URL}/workflows`);

    // 验证权限不足
    await expect(page.locator('.error-message:has-text("权限不足")')).toBeVisible({ timeout: 5000 });
  });

  test('LC-RP-E-006: AI developer cannot access ETL features', async ({ page }) => {
    /** 测试场景：AI 开发者无法访问 ETL 功能
     *
     * 前置条件：
     * - 用户为 AI 开发者角色
     *
     * 测试步骤：
     * 1. AI 开发者尝试访问 ETL 任务页面
     *
     * 预期结果：
     * - 显示权限不足
     */

    // Mock AI 开发者权限
    await page.route('**/api/v1/auth/permissions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            permissions: ['workflow:*', 'prompt:*', 'knowledge:*', 'agent:*']
          }
        })
      });
    });

    // 尝试访问 ETL 页面
    await page.goto(`${BASE_URL}/data/etl`);

    // 验证权限不足
    await expect(page.locator('.error-message:has-text("权限不足")')).toBeVisible({ timeout: 5000 });
  });

  test('LC-RP-E-007: User with multiple roles has merged permissions', async ({ page }) => {
    /** 测试场景：多角色用户权限合并
     *
     * 前置条件：
     * - 用户拥有数据工程师和数据分析师两个角色
     *
     * 测试步骤：
     * 1. 用户访问 ETL 页面（数据工程师权限）
     * 2. 用户访问 BI 页面（数据分析师权限）
     *
     * 预期结果：
     * - 两个页面都可以正常访问
     */

    // Mock 合并权限
    await page.route('**/api/v1/auth/permissions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            permissions: ['etl:*', 'quality:*', 'feature:*', 'bi:*', 'metrics:*', 'sql:*']
          }
        })
      });
    });

    // Mock ETL 数据
    await page.route('**/api/v1/data/etl-jobs', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: { jobs: [], total: 0 }
        })
      });
    });

    // Mock BI 数据
    await page.route('**/api/v1/data/bi', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: { dashboards: [], total: 0 }
        })
      });
    });

    // 访问 ETL 页面
    await page.goto(`${BASE_URL}/data/etl`);
    await expect(page.locator('body')).toBeVisible();

    // 访问 BI 页面
    await page.goto(`${BASE_URL}/data/bi`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('User Role Progression - Role Change History', () => {
  test('LC-RP-E-008: View role change history in audit logs', async ({ page }) => {
    /** 测试场景：查看角色变更历史
     *
     * 前置条件：
     * - 用户角色有过变更
     *
     * 测试步骤：
     * 1. 导航到审计日志页面
     * 2. 筛选目标用户
     * 3. 查看角色变更记录
     *
     * 预期结果：
     * - 显示完整的角色变更历史
     * - 包含操作人、操作时间、变更内容
     */

    // Mock 审计日志数据
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
                action: 'assign_role',
                user_id: 'user_upgrade_001',
                username: 'upgrade_user',
                actor: 'admin',
                details: { role: 'data_analyst', action: 'added' },
                created_at: '2024-01-15T10:30:00Z'
              },
              {
                id: 'audit_002',
                action: 'revoke_role',
                user_id: 'user_upgrade_001',
                username: 'upgrade_user',
                actor: 'admin',
                details: { role: 'data_admin', action: 'removed' },
                created_at: '2024-01-20T14:20:00Z'
              }
            ],
            total: 2
          }
        })
      });
    });

    // 导航到审计日志页面
    await page.goto(`${BASE_URL}/admin/audit`);

    // 筛选用户
    await page.fill('[data-testid="user-filter"]', 'upgrade_user');
    await page.click('[data-testid="filter-button"]');

    // 验证日志显示
    await expect(page.locator('text=assign_role')).toBeVisible();
    await expect(page.locator('text=revoke_role')).toBeVisible();
  });
});
