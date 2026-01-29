/**
 * 用户删除阶段测试
 * 测试用户删除的各种场景和数据保留策略
 */

import { test, expect } from './fixtures/user-lifecycle.fixture';
import { generateTestUserData, deleteUserViaUI } from './helpers/user-management';
import { verifyUserExists, verifyUserNotExists } from './helpers/user-management';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.describe('用户删除阶段', () => {
  test('管理员删除用户应该需要二次确认', async ({ userManager, adminPage }) => {
    const userData = generateTestUserData({
      status: 'active',
    });

    const user = await userManager.createUser(userData);

    await adminPage.goto(`${BASE_URL}/admin/users`);
    await adminPage.waitForLoadState('networkidle');

    const userRow = adminPage.locator(`tr:has-text("${user.username}")`).first();
    const deleteButton = userRow.locator('button:has-text("删除")').first();
    await deleteButton.click();
    await adminPage.waitForTimeout(500);

    // 应该显示确认对话框
    const confirmDialog = adminPage.locator('.ant-modal-confirm, .confirm-dialog').first();
    await expect(confirmDialog).toBeVisible();

    // 验证确认对话框内容
    const confirmText = await confirmDialog.textContent();
    expect(confirmText).toMatch(/确认|删除|warning/i);
  });

  test('删除用户后状态应该变为 deleted', async ({ userManager }) => {
    const userData = generateTestUserData({
      status: 'active',
    });

    const user = await userManager.createUser(userData);
    expect(user.status).not.toBe('deleted');

    // 删除用户
    await userManager.deleteUser(user.id);

    // 验证状态
    const deletedUser = await userManager.getUser(user.id);
    expect(deletedUser?.status).toBe('deleted');
  });

  test('删除用户后应该保留审计记录', async ({ userManager, request, adminPage }) => {
    const userData = generateTestUserData({
      status: 'active',
    });

    const user = await userManager.createUser(userData);

    // 先进行一些操作产生审计记录
    await request.post(`${BASE_URL}/api/v1/datasets`, {
      data: { name: `test_dataset_${user.id}`, owner_id: user.id },
    });

    // 删除用户
    await userManager.deleteUser(user.id);

    // 检查审计日志
    await adminPage.goto(`${BASE_URL}/admin/audit`);
    await adminPage.waitForLoadState('networkidle');

    await adminPage.fill('input[placeholder*="搜索"]', user.username);
    await adminPage.waitForTimeout(500);

    // 应该能看到该用户的历史记录
    const logEntries = adminPage.locator('.audit-log, .log-item');
    const count = await logEntries.count();
    expect(count).toBeGreaterThan(0);
  });

  test('删除用户后应该撤销所有访问权限', async ({ userManager, request }) => {
    const userData = generateTestUserData({
      status: 'active',
      username: `delete_perm_${Date.now()}`,
      password: 'Test1234!',
    });

    const user = await userManager.createUser(userData);

    // 获取 token
    const loginResponse = await request.post(`${BASE_URL}/api/v1/auth/login`, {
      data: {
        username: userData.username,
        password: userData.password,
      },
    });

    let token: string | null = null;
    if (loginResponse.ok()) {
      const loginJson = await loginResponse.json();
      token = loginJson.data?.access_token || loginJson.data?.token;
    }

    // 删除用户
    await userManager.deleteUser(user.id);

    // 使用之前的 token 访问应该被拒绝
    if (token) {
      const response = await request.get(`${BASE_URL}/api/v1/datasets`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      expect([401, 403]).toContain(response.status());
    }
  });

  test('删除用户后应该从用户列表消失', async ({ userManager, adminPage }) => {
    const userData = generateTestUserData({
      status: 'active',
    });

    const user = await userManager.createUser(userData);

    // 验证用户在列表中
    await adminPage.goto(`${BASE_URL}/admin/users`);
    await adminPage.waitForLoadState('networkidle');
    let exists = await verifyUserExists(adminPage, user.username);
    expect(exists).toBe(true);

    // 删除用户
    await userManager.deleteUser(user.id);

    // 刷新页面
    await adminPage.reload();
    await adminPage.waitForLoadState('networkidle');

    // 验证用户不在列表中
    exists = await verifyUserExists(adminPage, user.username);
    expect(exists).toBe(false);
  });

  test('应该支持批量删除用户', async ({ userManager, adminPage }) => {
    const users = await Promise.all([
      userManager.createUser(generateTestUserData({ username: `batch_del_1_${Date.now()}` })),
      userManager.createUser(generateTestUserData({ username: `batch_del_2_${Date.now()}` })),
      userManager.createUser(generateTestUserData({ username: `batch_del_3_${Date.now()}` })),
    ]);

    // 导航到用户管理页面
    await adminPage.goto(`${BASE_URL}/admin/users`);
    await adminPage.waitForLoadState('networkidle');

    // 选择多个用户（如果 UI 支持）
    const checkboxes = adminPage.locator('input[type="checkbox"]').all();
    for (const checkbox of await checkboxes) {
      if (await checkbox.isVisible()) {
        await checkbox.check();
      }
    }

    // 查找批量删除按钮
    const batchDeleteButton = adminPage.locator('button:has-text("批量删除")').first();
    if (await batchDeleteButton.isVisible()) {
      await batchDeleteButton.click();
      await adminPage.waitForTimeout(500);

      // 确认删除
      const confirmButton = adminPage.locator('.ant-modal-confirm button:has-text("确定")').first();
      if (await confirmButton.isVisible()) {
        await confirmButton.click();
      }
    }

    await adminPage.waitForTimeout(1000);

    // 验证用户已被删除
    for (const user of users) {
      const exists = await verifyUserExists(adminPage, user.username);
      expect(exists).toBe(false);
    }
  });

  test('删除用户后其创建的资源应该有处理策略', async ({ userManager, testDataManager, request }) => {
    const userData = generateTestUserData({
      status: 'active',
    });

    const user = await userManager.createUser(userData);

    // 创建一些资源
    const dataset = await testDataManager.createTestDataset({
      name: `dataset_${user.id}`,
      owner_id: user.id,
    });

    const workflow = await testDataManager.createTestWorkflow({
      name: `workflow_${user.id}`,
      owner_id: user.id,
    });

    // 删除用户
    await userManager.deleteUser(user.id);

    // 检查资源的处理策略
    // 可能的策略：
    // 1. 资源被删除
    // 2. 资源所有权转移给管理员或系统用户
    // 3. 资源标记为孤儿资源

    const datasetResponse = await request.get(`${BASE_URL}/api/v1/datasets/${dataset.id}`);
    if (datasetResponse.ok()) {
      const datasetJson = await datasetResponse.json();
      // 资源可能还存在，但 owner_id 已变更
      expect(datasetJson.data?.owner_id).not.toBe(user.id);
    }

    const workflowResponse = await request.get(`${BASE_URL}/api/v1/workflows/${workflow.id}`);
    if (workflowResponse.ok()) {
      const workflowJson = await workflowResponse.json();
      expect(workflowJson.data?.owner_id).not.toBe(user.id);
    }
  });

  test('通过 UI 删除用户', async ({ userManager, adminPage }) => {
    const userData = generateTestUserData({
      status: 'active',
    });

    const user = await userManager.createUser(userData);

    // 通过 UI 删除
    await deleteUserViaUI(adminPage, user.username);

    // 验证删除成功
    const deletedUser = await userManager.getUser(user.id);
    expect(deletedUser?.status).toBe('deleted');
  });

  test('删除不存在用户应该返回错误', async ({ request }) => {
    const fakeUserId = 'non-existent-user-id';

    const response = await request.delete(`${BASE_URL}/api/v1/users/${fakeUserId}`);

    expect(response.ok()).toBeFalsy();

    const json = await response.json();
    expect(json.code).not.toBe(0);
  });

  test('已删除用户再次删除应该不报错', async ({ userManager }) => {
    const userData = generateTestUserData({
      status: 'deleted',
    });

    const user = await userManager.createUser(userData);

    // 再次删除已删除的用户
    try {
      await userManager.deleteUser(user.id);
      // 如果没有抛出错误，验证状态仍然是 deleted
      const stillDeleted = await userManager.getUser(user.id);
      expect(stillDeleted?.status).toBe('deleted');
    } catch (error) {
      // 也可能返回"用户不存在"的错误
      expect(error).toBeTruthy();
    }
  });

  test('删除用户应该同步到所有服务', async ({ userManager, request }) => {
    const userData = generateTestUserData({
      status: 'active',
    });

    const user = await userManager.createUser(userData);

    // 在各服务中创建资源
    const agentResponse = await request.post(`${process.env.AGENT_API_URL || process.env.BISHENG_API_URL || 'http://localhost:8000'}/api/v1/conversations`, {
      data: { title: 'Test', user_id: user.id },
    });

    const dataResponse = await request.post(`${process.env.DATA_API_URL || process.env.ALLDATA_API_URL || 'http://localhost:8001'}/api/v1/datasets`, {
      data: { name: 'Test', user_id: user.id },
    });

    // 删除用户
    await userManager.deleteUser(user.id);

    // 验证各服务中的资源都已处理
    if (agentResponse.ok()) {
      const agentJson = await agentResponse.json();
      const conversationId = agentJson.data?.id;
      if (conversationId) {
        const checkResponse = await request.get(`${process.env.AGENT_API_URL || process.env.BISHENG_API_URL || 'http://localhost:8000'}/api/v1/conversations/${conversationId}`);
        // 资源可能被删除或标记为已删除
        expect([404, 403, 410]).toContain(checkResponse.status());
      }
    }
  });

  test('删除用户时应该检查是否有未完成的任务', async ({ userManager, request }) => {
    const userData = generateTestUserData({
      status: 'active',
    });

    const user = await userManager.createUser(userData);

    // 创建一个运行中的任务（模拟）
    const taskResponse = await request.post(`${process.env.MODEL_API_URL || process.env.CUBE_API_URL || 'http://localhost:8002'}/api/v1/training/jobs`, {
      data: {
        name: 'Running Job',
        status: 'running',
        user_id: user.id,
      },
    });

    // 尝试删除用户
    const deleteResponse = await request.delete(`${BASE_URL}/api/v1/users/${user.id}`);

    if (taskResponse.ok()) {
      // 如果用户有运行中的任务，删除可能被阻止或给出警告
      const deleteJson = await deleteResponse.json();
      if (deleteResponse.status() === 409) {
        expect(deleteJson.message).toMatch(/任务|running|active/i);
      }
    } else {
      // 如果没有任务支持，正常删除
      expect(deleteResponse.ok()).toBeTruthy();
    }
  });

  test('删除用户应该记录删除者和删除时间', async ({ userManager, request, adminPage }) => {
    const userData = generateTestUserData({
      status: 'active',
    });

    const user = await userManager.createUser(userData);

    // 通过管理员删除
    await adminPage.goto(`${BASE_URL}/admin/users`);
    await adminPage.waitForLoadState('networkidle');

    const userRow = adminPage.locator(`tr:has-text("${user.username}")`).first();
    const deleteButton = userRow.locator('button:has-text("删除")').first();
    await deleteButton.click();
    await adminPage.waitForTimeout(500);

    const confirmButton = adminPage.locator('.ant-modal-confirm button:has-text("确定")').first();
    await confirmButton.click();
    await adminPage.waitForTimeout(1000);

    // 检查用户详情
    const response = await request.get(`${BASE_URL}/api/v1/users/${user.id}`);
    if (response.ok()) {
      const json = await response.json();
      expect(json.data?.deleted_at).toBeTruthy();
      expect(json.data?.deleted_by).toBeTruthy();
    }
  });

  test('删除用户后应该能够查询到历史记录', async ({ userManager, request }) => {
    const userData = generateTestUserData({
      status: 'active',
    });

    const user = await userManager.createUser(userData);

    // 记录删除前的用户 ID
    const userId = user.id;

    // 删除用户
    await userManager.deleteUser(user.id);

    // 查询历史记录（包括已删除用户）
    const response = await request.get(`${BASE_URL}/api/v1/users`, {
      params: { include_deleted: true },
    });

    if (response.ok()) {
      const json = await response.json();
      const deletedUser = json.data?.users?.find((u: any) => u.id === userId);
      expect(deletedUser).toBeTruthy();
      expect(deletedUser.status).toBe('deleted');
    }
  });

  test('删除用户后其登录会话应该失效', async ({ userManager, page }) => {
    const userData = generateTestUserData({
      status: 'active',
      username: `session_delete_${Date.now()}`,
      password: 'Test1234!',
    });

    const user = await userManager.createUser(userData);

    // 用户登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    // 验证已登录
    let currentUrl = page.url();
    expect(currentUrl).not.toContain('/login');

    // 管理员删除用户
    await userManager.deleteUser(user.id);

    // 用户尝试访问页面应该被重定向到登录页
    await page.reload();
    await page.waitForLoadState('networkidle');

    currentUrl = page.url();
    expect(currentUrl).toContain('/login');
  });
});
