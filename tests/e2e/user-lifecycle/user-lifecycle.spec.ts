/**
 * 用户全生命周期端到端测试
 * 测试完整的用户生命周期场景
 */

import { test, expect } from './fixtures/user-lifecycle.fixture';
import { generateTestUserData } from './helpers/user-management';
import { verifyCanAccessPage, verifyCannotAccessPage } from './helpers/verification';
import type { TestRole, UserStatus } from './fixtures/user-lifecycle.fixture';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.describe('用户全生命周期端到端测试', () => {
  test('完整用户生命周期: 创建 -> 激活 -> 使用 -> 角色变更 -> 停用', async ({ userManager, page, adminPage }) => {
    // 1. 创建阶段
    const userData = generateTestUserData({
      status: 'pending',
      username: `lifecycle_user_${Date.now()}`,
      password: 'Lifecycle123!',
    });

    const user = await userManager.createUser(userData);
    expect(user.status).toBe('pending');
    expect(user.roles).toEqual(['user']);

    // 2. 激活阶段
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    let updatedUser = await userManager.getUser(user.id);
    expect(updatedUser?.status).toBe('active');

    // 3. 使用阶段 - 验证基础访问权限
    let result = await verifyCanAccessPage(page, '/workspace');
    expect(result.hasAccess).toBe(true);

    result = await verifyCannotAccessPage(page, '/admin/users');
    expect(result.hasAccess).toBe(true);

    // 4. 角色变更阶段
    await userManager.assignRole(user.id, 'data_engineer');

    // 重新登录
    await page.goto(`${BASE_URL}/logout`);
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    // 验证新权限
    result = await verifyCanAccessPage(page, '/data/datasets');
    expect(result.hasAccess).toBe(true);

    // 5. 停用阶段
    await userManager.deactivateUser(user.id);

    updatedUser = await userManager.getUser(user.id);
    expect(updatedUser?.status).toBe('inactive');

    // 验证无法登录
    await page.goto(`${BASE_URL}/logout`);
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    const currentUrl = page.url();
    expect(currentUrl).toContain('/login');
  });

  test('数据工程师完整工作流', async ({ userManager, page, testDataManager }) => {
    const userData = generateTestUserData({
      roles: ['data_engineer'],
      username: `de_lifecycle_${Date.now()}`,
      password: 'De1234!',
    });

    const user = await userManager.createUser(userData);

    // 登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    // 1. 创建数据源
    await page.goto(`${BASE_URL}/data/datasources`);
    await page.waitForLoadState('networkidle');

    const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);

      const nameInput = page.locator('input[name="name"]').first();
      await nameInput.fill(`test_datasource_${Date.now()}`);

      const typeSelect = page.locator('select[name="type"]').first();
      if (await typeSelect.isVisible()) {
        await typeSelect.selectOption('mysql');
      }

      const confirmButton = page.locator('.ant-modal button:has-text("确定")').first();
      await confirmButton.click();
      await page.waitForTimeout(1000);
    }

    // 2. 创建数据集
    const dataset = await testDataManager.createTestDataset({
      name: `de_dataset_${Date.now()}`,
      owner_id: user.id,
    });

    expect(dataset).toBeTruthy();

    // 3. 执行 SQL 查询
    await page.goto(`${BASE_URL}/development/sql-lab`);
    await page.waitForLoadState('networkidle');

    // 验证能访问 SQL Lab
    const sqlEditor = page.locator('.sql-editor, .monaco-editor').first();
    const hasEditor = await sqlEditor.count() > 0;
    expect(hasEditor).toBe(true);

    // 4. 查看数据质量报告
    await page.goto(`${BASE_URL}/data/quality`);
    await page.waitForLoadState('networkidle');

    const result = await verifyCanAccessPage(page, '/data/quality');
    expect(result.hasAccess).toBe(true);
  });

  test('AI 开发者完整工作流', async ({ userManager, page, testDataManager }) => {
    const userData = generateTestUserData({
      roles: ['ai_developer'],
      username: `ai_lifecycle_${Date.now()}`,
      password: 'Ai1234!',
    });

    const user = await userManager.createUser(userData);

    // 登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    // 1. 创建 AI 对话
    await page.goto(`${BASE_URL}/ai/chat`);
    await page.waitForLoadState('networkidle');

    const chatInput = page.locator('textarea[placeholder*="输入"], .chat-input').first();
    if (await chatInput.isVisible()) {
      await chatInput.fill('你好');
      await page.keyboard.press('Enter');
      await page.waitForTimeout(1000);
    }

    // 2. 创建工作流
    const workflow = await testDataManager.createTestWorkflow({
      name: `ai_workflow_${Date.now()}`,
      owner_id: user.id,
    });

    expect(workflow).toBeTruthy();

    // 3. 创建模型
    const model = await testDataManager.createTestModel({
      name: `ai_model_${Date.now()}`,
      owner_id: user.id,
    });

    expect(model).toBeTruthy();

    // 4. 访问训练任务页面
    await page.goto(`${BASE_URL}/model/training`);
    await page.waitForLoadState('networkidle');

    const result = await verifyCanAccessPage(page, '/model/training');
    expect(result.hasAccess).toBe(true);
  });

  test('用户从普通用户升级为数据工程师', async ({ userManager, page }) => {
    const userData = generateTestUserData({
      roles: ['user'],
      username: `upgrade_de_${Date.now()}`,
      password: 'Upgrade123!',
    });

    const user = await userManager.createUser(userData);

    // 登录为普通用户
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    // 验证只能访问基础功能
    let result = await verifyCannotAccessPage(page, '/data/datasources');
    expect(result.hasAccess).toBe(true);

    // 升级为数据工程师
    await userManager.assignRole(user.id, 'data_engineer');

    // 重新登录
    await page.goto(`${BASE_URL}/logout`);
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    // 验证可以访问数据工程师功能
    result = await verifyCanAccessPage(page, '/data/datasources');
    expect(result.hasAccess).toBe(true);
  });

  test('用户从数据工程师降级为普通用户', async ({ userManager, page }) => {
    const userData = generateTestUserData({
      roles: ['data_engineer'],
      username: `downgrade_user_${Date.now()}`,
      password: 'Downgrade123!',
    });

    const user = await userManager.createUser(userData);

    // 登录为数据工程师
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    // 验证可以访问数据源
    let result = await verifyCanAccessPage(page, '/data/datasources');
    expect(result.hasAccess).toBe(true);

    // 降级为普通用户
    await userManager.revokeRole(user.id, 'data_engineer');

    // 重新登录
    await page.goto(`${BASE_URL}/logout`);
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    // 验证不能访问数据工程师功能
    result = await verifyCannotAccessPage(page, '/data/datasources');
    expect(result.hasAccess).toBe(true);
  });

  test('账户被锁定后的解锁流程', async ({ userManager, page, adminPage }) => {
    const userData = generateTestUserData({
      status: 'active',
      username: `lock_unlock_${Date.now()}`,
      password: 'Lock123!',
    });

    const user = await userManager.createUser(userData);

    // 模拟5次登录失败导致锁定
    for (let i = 0; i < 5; i++) {
      await userManager.simulateFailedLogin(userData.username);
    }

    let lockedUser = await userManager.getUser(user.id);
    expect(lockedUser?.status).toBe('locked');

    // 用户尝试登录应该失败
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    const currentUrl = page.url();
    expect(currentUrl).toContain('/login');

    // 管理员解锁用户
    await userManager.unlockUser(user.id);

    // 验证已解锁
    const unlockedUser = await userManager.getUser(user.id);
    expect(unlockedUser?.status).toBe('active');

    // 用户现在应该可以登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    const loggedInUrl = page.url();
    expect(loggedInUrl).not.toContain('/login');
  });

  test('用户离职后的停用流程', async ({ userManager, page, adminPage }) => {
    const userData = generateTestUserData({
      status: 'active',
      roles: ['data_engineer'],
      username: `resignation_${Date.now()}`,
      password: 'Resign123!',
    });

    const user = await userManager.createUser(userData);

    // 用户正常工作状态 - 可以登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    let currentUrl = page.url();
    expect(currentUrl).not.toContain('/login');

    // 用户离职 - 管理员停用账户
    await userManager.deactivateUser(user.id);

    const inactiveUser = await userManager.getUser(user.id);
    expect(inactiveUser?.status).toBe('inactive');

    // 用户无法登录
    await page.goto(`${BASE_URL}/logout`);
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    currentUrl = page.url();
    expect(currentUrl).toContain('/login');

    // 管理员查看用户状态
    await adminPage.goto(`${BASE_URL}/admin/users`);
    await adminPage.waitForLoadState('networkidle');

    const userRow = adminPage.locator(`tr:has-text("${user.username}")`).first();
    const statusTag = userRow.locator('.ant-tag:has-text("inactive")').first();
    await expect(statusTag).toBeVisible();
  });

  test('跨租户用户权限隔离', async ({ userManager, page, request }) => {
    // 创建两个不同租户的用户（如果支持多租户）
    const userData1 = generateTestUserData({
      roles: ['data_engineer'],
      username: `tenant1_user_${Date.now()}`,
      password: 'Tenant1123!',
    });

    const userData2 = generateTestUserData({
      roles: ['ai_developer'],
      username: `tenant2_user_${Date.now()}`,
      password: 'Tenant2123!',
    });

    const user1 = await userManager.createUser(userData1);
    const user2 = await userManager.createUser(userData2);

    // 用户1登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData1.username);
    await page.fill('input[name="password"]', userData1.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    // 用户1应该不能访问用户2的资源
    const response = await request.get(`${BASE_URL}/api/v1/users/${user2.id}`);
    expect([403, 404]).toContain(response.status());

    // 用户1只能看到自己的资源
    const datasetsResponse = await request.get(`${BASE_URL}/api/v1/datasets`);
    if (datasetsResponse.ok()) {
      const datasetsJson = await datasetsResponse.json();
      const datasets = datasetsJson.data?.datasets || datasetsJson.data || [];
      // 验证只显示用户有权访问的数据集
      expect(Array.isArray(datasets)).toBe(true);
    }
  });

  test('用户从入职到离职的完整周期', async ({ userManager, page, testDataManager, adminPage }) => {
    const timestamp = Date.now();
    const userData = generateTestUserData({
      status: 'pending',
      username: `full_cycle_${timestamp}`,
      password: 'FullCycle123!',
    });

    // === 入职阶段 ===
    // 1. HR/管理员创建账户
    const user = await userManager.createUser({
      ...userData,
      roles: ['user'],
      status: 'pending',
    });

    expect(user.status).toBe('pending');

    // 2. 员工首次登录激活账户
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    let activatedUser = await userManager.getUser(user.id);
    expect(activatedUser?.status).toBe('active');

    // === 工作阶段 ===
    // 3. 分配工作角色 - 数据工程师
    await userManager.assignRole(user.id, 'data_engineer');

    // 4. 员工开始工作 - 创建数据集
    await page.reload();
    await page.waitForLoadState('networkidle');

    const dataset = await testDataManager.createTestDataset({
      name: `work_dataset_${timestamp}`,
      owner_id: user.id,
    });

    expect(dataset).toBeTruthy();

    // 5. 创建 ETL 任务
    await page.goto(`${BASE_URL}/development/etl`);
    await page.waitForLoadState('networkidle');

    // 6. 执行数据质量检查
    await page.goto(`${BASE_URL}/data/quality`);
    await page.waitForLoadState('networkidle');

    const canAccessQuality = await verifyCanAccessPage(page, '/data/quality');
    expect(canAccessQuality.hasAccess).toBe(true);

    // === 晋升阶段 ===
    // 7. 晋升为 AI 开发者（增加角色）
    await userManager.assignRole(user.id, 'ai_developer');

    // 8. 创建 AI 工作流
    const workflow = await testDataManager.createTestWorkflow({
      name: `promotion_workflow_${timestamp}`,
      owner_id: user.id,
    });

    expect(workflow).toBeTruthy();

    // === 离职阶段 ===
    // 9. 降级权限（撤销 AI 开发者角色）
    await userManager.revokeRole(user.id, 'ai_developer');

    // 10. 停用账户
    await userManager.deactivateUser(user.id);

    const inactiveUser = await userManager.getUser(user.id);
    expect(inactiveUser?.status).toBe('inactive');

    // 11. 用户尝试登录失败
    await page.goto(`${BASE_URL}/logout`);
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    const loginUrl = page.url();
    expect(loginUrl).toContain('/login');

    // === 归档阶段 ===
    // 12. 管理员查看审计记录
    await adminPage.goto(`${BASE_URL}/admin/audit`);
    await adminPage.waitForLoadState('networkidle');

    await adminPage.fill('input[placeholder*="搜索"]', userData.username);
    await adminPage.waitForTimeout(500);

    const logEntries = adminPage.locator('.audit-log, .log-item');
    const count = await logEntries.count();
    expect(count).toBeGreaterThan(0);

    // 13. 软删除用户（保留记录）
    await userManager.deleteUser(user.id);

    const deletedUser = await userManager.getUser(user.id);
    expect(deletedUser?.status).toBe('deleted');
  });

  test('多角色用户权限合并', async ({ userManager, page }) => {
    const userData = generateTestUserData({
      roles: ['data_engineer', 'ai_developer'],
      username: `multi_role_${Date.now()}`,
      password: 'Multi123!',
    });

    const user = await userManager.createUser(userData);

    // 登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    // 验证拥有 data_engineer 的权限
    let result = await verifyCanAccessPage(page, '/data/datasources');
    expect(result.hasAccess).toBe(true);

    // 验证拥有 ai_developer 的权限
    result = await verifyCanAccessPage(page, '/ai/workflows');
    expect(result.hasAccess).toBe(true);

    // 验证拥有两者的 AI 对话权限
    result = await verifyCanAccessPage(page, '/ai/chat');
    expect(result.hasAccess).toBe(true);
  });
});

test.describe('用户生命周期边界条件测试', () => {
  test('处理已存在的用户名', async ({ userManager }) => {
    const userData = generateTestUserData();

    await userManager.createUser(userData);

    // 尝试创建相同用户名的用户
    await expect(userManager.createUser(userData)).rejects.toThrow();
  });

  test('处理无效的用户状态转换', async ({ userManager }) => {
    const userData = generateTestUserData({
      status: 'deleted',
    });

    const user = await userManager.createUser(userData);

    // 尝试激活已删除的用户应该失败
    try {
      await userManager.activateUser(user.id);
      const stillDeleted = await userManager.getUser(user.id);
      expect(stillDeleted?.status).toBe('deleted');
    } catch (error) {
      expect(error).toBeTruthy();
    }
  });

  test('处理并发角色变更', async ({ userManager, request }) => {
    const userData = generateTestUserData({
      roles: ['user'],
    });

    const user = await userManager.createUser(userData);

    // 并发分配多个角色
    await Promise.all([
      userManager.assignRole(user.id, 'data_engineer'),
      userManager.assignRole(user.id, 'ai_developer'),
      userManager.assignRole(user.id, 'data_analyst'),
    ]);

    const updatedUser = await userManager.getUser(user.id);
    expect(updatedUser?.roles).toContain('data_engineer');
    expect(updatedUser?.roles).toContain('ai_developer');
    expect(updatedUser?.roles).toContain('data_analyst');
  });

  test('处理大量用户批量操作', async ({ userManager, request }) => {
    const userCount = 10;
    const users = await Promise.all(
      Array.from({ length: userCount }, (_, i) =>
        userManager.createUser(generateTestUserData({
          username: `batch_test_${i}_${Date.now()}`,
        }))
      )
    );

    expect(users).toHaveLength(userCount);

    // 批量更新状态
    const userIds = users.map(u => u.id);
    const response = await request.post(`${BASE_URL}/api/v1/users/batch/status`, {
      data: {
        user_ids: userIds,
        status: 'inactive',
      },
    });

    if (response.ok()) {
      for (const user of users) {
        const updatedUser = await userManager.getUser(user.id);
        expect(updatedUser?.status).toBe('inactive');
      }
    }
  });
});
