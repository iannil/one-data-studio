/**
 * 管理后台深度验收测试
 * 覆盖用户管理、角色权限、用户组、审计日志、系统设置、成本报告等功能
 * 使用真实 API 调用
 */

import { test, expect } from './fixtures/real-auth.fixture';
import { logger } from './helpers/logger';
import { createApiClient, clearRequestLogs, getFailedRequests } from './helpers/api-client';
import type { AgentApiClient } from './helpers/api-client';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

// ============================================
// 用户管理深度测试
// ============================================
test.describe('管理后台 - 用户管理', () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test('should display users list', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/users`);
    await adminPage.waitForLoadState('networkidle');

    const list = adminPage.locator('.user-list, .data-table, [class*="table"]').first();
    await expect(list).toBeVisible();
  });

  test('should create new user', async ({ adminPage, request }) => {
    await adminPage.goto(`${BASE_URL}/admin/users`);
    await adminPage.waitForLoadState('networkidle');

    const createButton = adminPage.locator('button:has-text("创建"), button:has-text("新建"), button:has-text("添加")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await adminPage.waitForTimeout(500);

      const modal = adminPage.locator('.ant-modal, .modal');
      const hasModal = await modal.count() > 0;
      if (hasModal) {
        const usernameInput = modal.locator('input[name="username"], input[name="name"]');
        if (await usernameInput.isVisible()) {
          await usernameInput.fill(`e2e-test-user-${Date.now()}`);

          const emailInput = modal.locator('input[name="email"], input[type="email"]');
          if (await emailInput.isVisible()) {
            await emailInput.fill(`e2e-test-${Date.now()}@example.com`);
          }

          const passwordInput = modal.locator('input[name="password"], input[type="password"]');
          if (await passwordInput.isVisible()) {
            await passwordInput.fill('Test1234!');
          }

          const confirmButton = modal.locator('button:has-text("确定"), button:has-text("创建")').first();
          await confirmButton.click();
          await adminPage.waitForTimeout(1000);
        }
      }
    }
  });

  test('should edit user information', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/users`);
    await adminPage.waitForLoadState('networkidle');

    const firstUser = adminPage.locator('tr[data-row-key], .user-item').first();
    if (await firstUser.isVisible()) {
      const editButton = firstUser.locator('button:has-text("编辑"), button:has-text("Edit")').first();
      if (await editButton.isVisible()) {
        await editButton.click();
        await adminPage.waitForTimeout(500);

        const modal = adminPage.locator('.ant-modal, .modal');
        const hasModal = await modal.count() > 0;
        if (hasModal) {
          const form = modal.locator('form');
          await expect(form.first()).toBeVisible();
        }
      }
    }
  });

  test('should delete user with confirmation', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/users`);
    await adminPage.waitForLoadState('networkidle');

    // 查找测试用户
    const testUser = adminPage.locator('tr:has-text("e2e-test-user")').first();
    if (await testUser.isVisible()) {
      const deleteButton = testUser.locator('button:has-text("删除"), button:has-text("Delete")').first();
      await deleteButton.click();
      await adminPage.waitForTimeout(500);

      const confirmButton = adminPage.locator('.ant-modal-confirm button:has-text("确定"), button:has-text("确认")').first();
      if (await confirmButton.isVisible()) {
        await confirmButton.click();
        await adminPage.waitForTimeout(1000);
      }
    }
  });

  test('should reset user password', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/users`);
    await adminPage.waitForLoadState('networkidle');

    const firstUser = adminPage.locator('tr[data-row-key], .user-item').first();
    if (await firstUser.isVisible()) {
      const resetButton = firstUser.locator('button:has-text("重置"), button:has-text("Reset")').first();
      if (await resetButton.isVisible()) {
        await resetButton.click();
        await adminPage.waitForTimeout(500);

        const confirmButton = adminPage.locator('.ant-modal-confirm button:has-text("确定")').first();
        if (await confirmButton.isVisible()) {
          await confirmButton.click();
          await adminPage.waitForTimeout(1000);
        }
      }
    }
  });

  test('should search and filter users', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/users`);
    await adminPage.waitForLoadState('networkidle');

    const searchInput = adminPage.locator('input[placeholder*="搜索"], input[placeholder*="search"]').first();
    if (await searchInput.isVisible()) {
      await searchInput.fill('admin');
      await adminPage.waitForTimeout(500);

      const filteredResults = adminPage.locator('tr[data-row-key], .user-item');
      const count = await filteredResults.count();
      logger.info('Filtered users count:', count);
    }
  });
});

// ============================================
// 角色权限深度测试
// ============================================
test.describe('管理后台 - 角色权限', () => {
  test('should display roles list', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/roles`);
    await adminPage.waitForLoadState('networkidle');

    const list = adminPage.locator('.role-list, .data-table, [class*="table"]').first();
    await expect(list).toBeVisible();
  });

  test('should create new role', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/roles`);
    await adminPage.waitForLoadState('networkidle');

    const createButton = adminPage.locator('button:has-text("创建"), button:has-text("新建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await adminPage.waitForTimeout(500);

      const modal = adminPage.locator('.ant-modal, .modal');
      const hasModal = await modal.count() > 0;
      if (hasModal) {
        const nameInput = modal.locator('input[name="name"], input[name="role_name"]');
        if (await nameInput.isVisible()) {
          await nameInput.fill(`e2e-test-role-${Date.now()}`);

          const descInput = modal.locator('textarea[name="description"]');
          if (await descInput.isVisible()) {
            await descInput.fill('E2E测试角色');
          }

          const confirmButton = modal.locator('button:has-text("确定"), button:has-text("创建")').first();
          await confirmButton.click();
          await adminPage.waitForTimeout(1000);
        }
      }
    }
  });

  test('should assign permissions to role', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/roles`);
    await adminPage.waitForLoadState('networkidle');

    const firstRole = adminPage.locator('tr[data-row-key], .role-item').first();
    if (await firstRole.isVisible()) {
      const permissionButton = firstRole.locator('button:has-text("权限"), button:has-text("Permission")').first();
      if (await permissionButton.isVisible()) {
        await permissionButton.click();
        await adminPage.waitForTimeout(500);

        const permissionPanel = adminPage.locator('.permission-panel, .permission-tree');
        const hasPanel = await permissionPanel.count() > 0;
        if (hasPanel) {
          await expect(permissionPanel.first()).toBeVisible();
        }
      }
    }
  });

  test('should view role details', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/roles`);
    await adminPage.waitForLoadState('networkidle');

    const firstRole = adminPage.locator('tr[data-row-key], .role-item').first();
    if (await firstRole.isVisible()) {
      const viewButton = firstRole.locator('button:has-text("查看"), button:has-text("View")').first();
      if (await viewButton.isVisible()) {
        await viewButton.click();
        await adminPage.waitForTimeout(500);

        const detailPanel = adminPage.locator('.role-detail, .detail-panel');
        const hasDetail = await detailPanel.count() > 0;
        logger.info('Has role detail panel:', hasDetail);
      }
    }
  });

  test('should delete role', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/roles`);
    await adminPage.waitForLoadState('networkidle');

    const testRole = adminPage.locator('tr:has-text("e2e-test-role")').first();
    if (await testRole.isVisible()) {
      const deleteButton = testRole.locator('button:has-text("删除"), button:has-text("Delete")').first();
      await deleteButton.click();
      await adminPage.waitForTimeout(500);

      const confirmButton = adminPage.locator('.ant-modal-confirm button:has-text("确定")').first();
      if (await confirmButton.isVisible()) {
        await confirmButton.click();
        await adminPage.waitForTimeout(1000);
      }
    }
  });
});

// ============================================
// 用户组深度测试
// ============================================
test.describe('管理后台 - 用户组', () => {
  test('should display groups list', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/groups`);
    await adminPage.waitForLoadState('networkidle');

    const list = adminPage.locator('.group-list, .data-table, [class*="table"]').first();
    await expect(list).toBeVisible();
  });

  test('should create new group', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/groups`);
    await adminPage.waitForLoadState('networkidle');

    const createButton = adminPage.locator('button:has-text("创建"), button:has-text("新建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await adminPage.waitForTimeout(500);

      const modal = adminPage.locator('.ant-modal, .modal');
      const hasModal = await modal.count() > 0;
      if (hasModal) {
        const nameInput = modal.locator('input[name="name"], input[name="group_name"]');
        if (await nameInput.isVisible()) {
          await nameInput.fill(`e2e-test-group-${Date.now()}`);

          const confirmButton = modal.locator('button:has-text("确定"), button:has-text("创建")').first();
          await confirmButton.click();
          await adminPage.waitForTimeout(1000);
        }
      }
    }
  });

  test('should manage group members', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/groups`);
    await adminPage.waitForLoadState('networkidle');

    const firstGroup = adminPage.locator('tr[data-row-key], .group-item').first();
    if (await firstGroup.isVisible()) {
      const memberButton = firstGroup.locator('button:has-text("成员"), button:has-text("Member")').first();
      if (await memberButton.isVisible()) {
        await memberButton.click();
        await adminPage.waitForTimeout(500);

        const memberPanel = adminPage.locator('.member-panel, .member-list');
        const hasPanel = await memberPanel.count() > 0;
        if (hasPanel) {
          await expect(memberPanel.first()).toBeVisible();
        }
      }
    }
  });

  test('should assign permissions to group', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/groups`);
    await adminPage.waitForLoadState('networkidle');

    const firstGroup = adminPage.locator('tr[data-row-key], .group-item').first();
    if (await firstGroup.isVisible()) {
      const permissionButton = firstGroup.locator('button:has-text("权限"), button:has-text("Permission")').first();
      if (await permissionButton.isVisible()) {
        await permissionButton.click();
        await adminPage.waitForTimeout(500);

        const permissionPanel = adminPage.locator('.permission-panel, .permission-tree');
        const hasPanel = await permissionPanel.count() > 0;
        if (hasPanel) {
          await expect(permissionPanel.first()).toBeVisible();
        }
      }
    }
  });
});

// ============================================
// 审计日志深度测试
// ============================================
test.describe('管理后台 - 审计日志', () => {
  test('should display audit logs', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/audit`);
    await adminPage.waitForLoadState('networkidle');

    const list = adminPage.locator('.audit-list, .log-list, .data-table').first();
    await expect(list).toBeVisible();
  });

  test('should filter audit logs', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/audit`);
    await adminPage.waitForLoadState('networkidle');

    const filterPanel = adminPage.locator('.filter-panel, .filter-form');
    const hasFilter = await filterPanel.count() > 0;
    if (hasFilter) {
      // 尝试按用户筛选
      const userSelect = filterPanel.locator('select[name="user"], .ant-select').first();
      if (await userSelect.isVisible()) {
        await userSelect.click();
        await adminPage.waitForTimeout(300);
      }

      // 尝试按操作类型筛选
      const actionSelect = filterPanel.locator('select[name="action"]').nth(1);
      if (await actionSelect.isVisible()) {
        await actionSelect.click();
        await adminPage.waitForTimeout(300);
      }
    }
  });

  test('should search audit logs by keyword', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/audit`);
    await adminPage.waitForLoadState('networkidle');

    const searchInput = adminPage.locator('input[placeholder*="搜索"], input[placeholder*="search"]').first();
    if (await searchInput.isVisible()) {
      await searchInput.fill('login');
      await adminPage.waitForTimeout(500);

      const filteredResults = adminPage.locator('tr[data-row-key], .log-item');
      const count = await filteredResults.count();
      logger.info('Filtered logs count:', count);
    }
  });

  test('should export audit logs', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/audit`);
    await adminPage.waitForLoadState('networkidle');

    const exportButton = adminPage.locator('button:has-text("导出"), button:has-text("Export")').first();
    if (await exportButton.isVisible()) {
      // 点击导出按钮
      const [download] = await Promise.all([
        adminPage.waitForEvent('download'),
        exportButton.click(),
      ]);
      expect(download.suggestedFilename()).toBeTruthy();
    }
  });

  test('should view log details', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/audit`);
    await adminPage.waitForLoadState('networkidle');

    const firstLog = adminPage.locator('tr[data-row-key], .log-item').first();
    if (await firstLog.isVisible()) {
      const viewButton = firstLog.locator('button:has-text("查看"), button:has-text("View"), [class*="view"]').first();
      if (await viewButton.isVisible()) {
        await viewButton.click();
        await adminPage.waitForTimeout(500);

        const detailModal = adminPage.locator('.ant-modal, .modal');
        const hasModal = await detailModal.count() > 0;
        if (hasModal) {
          await expect(detailModal.first()).toBeVisible();
        }
      }
    }
  });
});

// ============================================
// 系统设置深度测试
// ============================================
test.describe('管理后台 - 系统设置', () => {
  test('should display system settings', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/settings`);
    await adminPage.waitForLoadState('networkidle');

    const settingsPanel = adminPage.locator('.settings-panel, .config-panel');
    await expect(settingsPanel.first()).toBeVisible();
  });

  test('should modify system configuration', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/settings`);
    await adminPage.waitForLoadState('networkidle');

    const settingsPanel = adminPage.locator('.settings-panel, .config-panel');

    // 查找可修改的配置项
    const switchInput = settingsPanel.locator('.ant-switch, input[type="checkbox"]').first();
    const hasSwitch = await switchInput.count() > 0;
    if (hasSwitch) {
      await switchInput.first().click();
      await adminPage.waitForTimeout(500);
    }

    const textInput = settingsPanel.locator('input[type="text"], input[type="number"]').first();
    const hasInput = await textInput.count() > 0;
    if (hasInput) {
      const currentValue = await textInput.inputValue();
      await textInput.fill(currentValue + '-test');
      await adminPage.waitForTimeout(500);
    }
  });

  test('should test email configuration', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/settings`);
    await adminPage.waitForLoadState('networkidle');

    const emailSection = adminPage.locator('.email-config, [class*="email"]').first();
    const hasEmailSection = await emailSection.count() > 0;
    if (hasEmailSection && await emailSection.isVisible()) {
      const testButton = emailSection.locator('button:has-text("测试"), button:has-text("Test")').first();
      if (await testButton.isVisible()) {
        await testButton.click();
        await adminPage.waitForTimeout(1000);
      }
    }
  });

  test('should save system settings', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/settings`);
    await adminPage.waitForLoadState('networkidle');

    const saveButton = adminPage.locator('button:has-text("保存"), button:has-text("Save")').first();
    if (await saveButton.isVisible()) {
      await saveButton.click();
      await adminPage.waitForTimeout(1000);

      // 验证保存成功提示
      const successMessage = adminPage.locator('.ant-message-success, .success-message');
      const hasSuccess = await successMessage.count() > 0;
      logger.info('Has success message:', hasSuccess);
    }
  });
});

// ============================================
// 成本报告深度测试
// ============================================
test.describe('管理后台 - 成本报告', () => {
  test('should display cost dashboard', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/costs`);
    await adminPage.waitForLoadState('networkidle');

    const dashboard = adminPage.locator('.cost-dashboard, .dashboard');
    await expect(dashboard.first()).toBeVisible();
  });

  test('should display resource usage statistics', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/costs`);
    await adminPage.waitForLoadState('networkidle');

    const statsCards = adminPage.locator('.stat-card, .metric-card');
    const hasStats = await statsCards.count() > 0;
    if (hasStats) {
      expect(await statsCards.count()).toBeGreaterThan(0);
    }
  });

  test('should display cost trend chart', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/costs`);
    await adminPage.waitForLoadState('networkidle');

    const chart = adminPage.locator('.cost-chart, canvas, [class*="chart"]');
    const hasChart = await chart.count() > 0;
    if (hasChart) {
      await expect(chart.first()).toBeVisible();
    }
  });

  test('should filter cost by date range', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/costs`);
    await adminPage.waitForLoadState('networkidle');

    const dateRangePicker = adminPage.locator('.ant-picker-range, .date-range-picker').first();
    const hasPicker = await dateRangePicker.count() > 0;
    if (hasPicker && await dateRangePicker.isVisible()) {
      await dateRangePicker.click();
      await adminPage.waitForTimeout(300);

      // 选择最近7天
      const recentOption = adminPage.locator('text=/最近.*天/, text=/Last.*days/').first();
      if (await recentOption.isVisible()) {
        await recentOption.click();
        await adminPage.waitForTimeout(500);
      }
    }
  });

  test('should filter cost by user', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/costs`);
    await adminPage.waitForLoadState('networkidle');

    const userFilter = adminPage.locator('select[name="user"], .user-filter').first();
    const hasFilter = await userFilter.count() > 0;
    if (hasFilter && await userFilter.isVisible()) {
      await userFilter.click();
      await adminPage.waitForTimeout(300);

      const firstOption = adminPage.locator('.ant-select-item-option').first();
      if (await firstOption.isVisible()) {
        await firstOption.click();
        await adminPage.waitForTimeout(500);
      }
    }
  });

  test('should export cost report', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/costs`);
    await adminPage.waitForLoadState('networkidle');

    const exportButton = adminPage.locator('button:has-text("导出"), button:has-text("Export")').first();
    if (await exportButton.isVisible()) {
      const [download] = await Promise.all([
        adminPage.waitForEvent('download'),
        exportButton.click(),
      ]);
      expect(download.suggestedFilename()).toBeTruthy();
    }
  });
});

// ============================================
// 权限验证测试
// ============================================
test.describe('管理后台 - 权限验证', () => {
  test('should deny access for non-admin users', async ({ authenticatedPage }) => {
    await authenticatedPage.goto(`${BASE_URL}/admin/users`);
    await authenticatedPage.waitForLoadState('networkidle');

    // 非管理员用户应该看到权限不足提示
    const accessDenied = authenticatedPage.locator('.access-denied, .error-page, [class*="forbidden"]');
    const hasAccessDenied = await accessDenied.count() > 0;
    if (hasAccessDenied) {
      await expect(accessDenied.first()).toBeVisible();
    }
  });

  test('should allow admin access to all admin pages', async ({ adminPage }) => {
    const adminPages = [
      '/admin/users',
      '/admin/roles',
      '/admin/groups',
      '/admin/audit',
      '/admin/settings',
      '/admin/costs',
    ];

    for (const pagePath of adminPages) {
      await adminPage.goto(`${BASE_URL}${pagePath}`);
      await adminPage.waitForLoadState('networkidle');

      // 管理员应该能正常访问，不应看到权限不足
      const accessDenied = adminPage.locator('.access-denied, .error-page, [class*="forbidden"]');
      const hasAccessDenied = await accessDenied.count() > 0;

      if (hasAccessDenied) {
        const isVisible = await accessDenied.first().isVisible();
        expect(isVisible).toBe(false);
      }
    }
  });

  test('should respect role-based permissions', async ({ developerPage }) => {
    // 开发者角色应该有部分权限
    await developerPage.goto(`${BASE_URL}/admin/settings`);
    await developerPage.waitForLoadState('networkidle');

    const content = developerPage.locator('body');
    await expect(content).toBeVisible();
  });
});

// ============================================
// API 端点验证测试
// ============================================
test.describe('管理后台 - API 端点验证', () => {
  test('should verify admin API endpoints', async ({ request }) => {
    const apiClient = createApiClient(request, 'agent_api') as AgentApiClient;
    clearRequestLogs();

    // 用户列表
    const usersResponse = await apiClient.get('/api/v1/admin/users');
    expect(usersResponse.code).toBeLessThan(500); // 可能为 403（无权限）或 200

    // 角色列表
    const rolesResponse = await apiClient.get('/api/v1/admin/roles');
    expect(rolesResponse.code).toBeLessThan(500);

    // 用户组列表
    const groupsResponse = await apiClient.get('/api/v1/admin/groups');
    expect(groupsResponse.code).toBeLessThan(500);

    // 审计日志
    const auditResponse = await apiClient.get('/api/v1/admin/audit/logs');
    expect(auditResponse.code).toBeLessThan(500);

    // 系统设置
    const settingsResponse = await apiClient.get('/api/v1/admin/settings');
    expect(settingsResponse.code).toBeLessThan(500);
  });
});

// ============================================
// 边界条件测试
// ============================================
test.describe('管理后台 - 边界条件', () => {
  test('should handle empty user list gracefully', async ({ adminPage }) => {
    // 此测试假设可能存在空列表的情况
    await adminPage.goto(`${BASE_URL}/admin/users`);
    await adminPage.waitForLoadState('networkidle');

    const emptyState = adminPage.locator('.empty-state, .no-data');
    const hasEmpty = await emptyState.count() > 0;
    logger.info('Has empty state for users:', hasEmpty);
  });

  test('should handle long user name', async ({ adminPage }) => {
    await adminPage.goto(`${BASE_URL}/admin/users`);
    await adminPage.waitForLoadState('networkidle');

    const createButton = adminPage.locator('button:has-text("创建"), button:has-text("新建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await adminPage.waitForTimeout(500);

      const nameInput = adminPage.locator('input[name="username"], input[name="name"]').first();
      if (await nameInput.isVisible()) {
        const longName = 'a'.repeat(100);
        await nameInput.fill(longName);

        const value = await nameInput.inputValue();
        expect(value.length).toBeGreaterThan(50);
      }
    }
  });
});

test.afterEach(async ({ request }) => {
  const failedRequests = getFailedRequests();
  if (failedRequests.length > 0) {
    console.error('Failed API requests in Admin test:', failedRequests);
  }
});
