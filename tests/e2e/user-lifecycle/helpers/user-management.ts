/**
 * 用户管理操作辅助函数
 * 提供用户相关的 UI 操作和 API 调用辅助函数
 */

import { Page, expect } from '@playwright/test';
import type { TestUser, CreateUserRequest, UserStatus } from '../fixtures/user-lifecycle.fixture';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

// ============================================
// 页面元素选择器常量
// ============================================

export const USER_SELECTORS = {
  // 用户管理页面
  userList: '.user-list, .data-table, [class*="table"]',
  userRow: 'tr[data-row-key], .user-item',
  userRowByName: (name: string) => `tr:has-text("${name}"), .user-item:has-text("${name}")`,

  // 按钮
  createUserButton: 'button:has-text("创建"), button:has-text("新建"), button:has-text("添加")',
  editButton: 'button:has-text("编辑"), button:has-text("Edit")',
  deleteButton: 'button:has-text("删除"), button:has-text("Delete")',
  resetPasswordButton: 'button:has-text("重置"), button:has-text("Reset")',
  activateButton: 'button:has-text("激活"), button:has-text("Activate")',
  deactivateButton: 'button:has-text("停用"), button:has-text("停用")',
  unlockButton: 'button:has-text("解锁"), button:has-text("解锁")',

  // 表单输入
  usernameInput: 'input[name="username"], input[name="name"]',
  emailInput: 'input[name="email"], input[type="email"]',
  passwordInput: 'input[name="password"], input[type="password"]',
  statusSelect: 'select[name="status"], [name="status"] .ant-select',
  rolesSelect: 'select[name="roles"], [name="roles"] .ant-select',

  // 模态框
  modal: '.ant-modal, .modal',
  modalTitle: '.ant-modal-title, .modal-title',
  modalConfirm: '.ant-modal button:has-text("确定"), .modal button:has-text("创建")',
  modalCancel: '.ant-modal button:has-text("取消"), .modal button:has-text("取消")',

  // 确认对话框
  confirmDialog: '.ant-modal-confirm',
  confirmOk: '.ant-modal-confirm button:has-text("确定"), button:has-text("确认")',
  confirmCancel: '.ant-modal-confirm button:has-text("取消")',

  // 消息提示
  successMessage: '.ant-message-success, .success-message',
  errorMessage: '.ant-message-error, .error-message',

  // 状态标签
  statusTag: '.ant-tag, [class*="status"]',
  statusPending: '.ant-tag:has-text("pending"), [class*="status-pending"]',
  statusActive: '.ant-tag:has-text("active"), [class*="status-active"]',
  statusInactive: '.ant-tag:has-text("inactive"), [class*="status-inactive"]',
  statusLocked: '.ant-tag:has-text("locked"), [class*="status-locked"]',
  statusDeleted: '.ant-tag:has-text("deleted"), [class*="status-deleted"]',

  // 搜索和筛选
  searchInput: 'input[placeholder*="搜索"], input[placeholder*="search"]',
  filterButton: 'button:has-text("筛选"), button:has-text("过滤")',
};

// ============================================
// UI 操作辅助函数
// ============================================

/**
 * 导航到用户管理页面
 */
export async function navigateToUserManagement(page: Page): Promise<void> {
  await page.goto(`${BASE_URL}/admin/users`);
  await page.waitForLoadState('networkidle');
}

/**
 * 打开创建用户对话框
 */
export async function openCreateUserDialog(page: Page): Promise<void> {
  const createButton = page.locator(USER_SELECTORS.createUserButton).first();
  await createButton.click();
  await page.waitForTimeout(500);

  // 等待模态框出现
  await expect(page.locator(USER_SELECTORS.modal).first()).toBeVisible();
}

/**
 * 填写用户创建表单
 */
export async function fillUserForm(page: Page, data: CreateUserRequest): Promise<void> {
  // 填写用户名
  const usernameInput = page.locator(USER_SELECTORS.usernameInput);
  if (await usernameInput.isVisible()) {
    await usernameInput.fill(data.username);
  }

  // 填写邮箱
  const emailInput = page.locator(USER_SELECTORS.emailInput);
  if (await emailInput.isVisible()) {
    await emailInput.fill(data.email);
  }

  // 填写密码（如果有）
  if (data.password) {
    const passwordInput = page.locator(USER_SELECTORS.passwordInput);
    if (await passwordInput.isVisible()) {
      await passwordInput.fill(data.password);
    }
  }

  // 选择角色（如果有）
  if (data.roles && data.roles.length > 0) {
    const rolesSelect = page.locator(USER_SELECTORS.rolesSelect);
    if (await rolesSelect.isVisible()) {
      await rolesSelect.click();
      await page.waitForTimeout(300);

      for (const role of data.roles) {
        const roleOption = page.locator(`.ant-select-item:has-text("${role}")`).first();
        if (await roleOption.isVisible()) {
          await roleOption.click();
        }
      }
    }
  }

  // 选择状态（如果有）
  if (data.status) {
    const statusSelect = page.locator(USER_SELECTORS.statusSelect);
    if (await statusSelect.isVisible()) {
      await statusSelect.click();
      await page.waitForTimeout(300);

      const statusOption = page.locator(`.ant-select-item:has-text("${data.status}")`).first();
      if (await statusOption.isVisible()) {
        await statusOption.click();
      }
    }
  }
}

/**
 * 提交用户表单
 */
export async function submitUserForm(page: Page): Promise<void> {
  const confirmButton = page.locator(USER_SELECTORS.modalConfirm).first();
  await confirmButton.click();
  await page.waitForTimeout(1000);
}

/**
 * 取消用户表单
 */
export async function cancelUserForm(page: Page): Promise<void> {
  const cancelButton = page.locator(USER_SELECTORS.modalCancel).first();
  await cancelButton.click();
  await page.waitForTimeout(500);
}

/**
 * 通过 UI 创建用户
 */
export async function createUserViaUI(page: Page, data: CreateUserRequest): Promise<void> {
  await navigateToUserManagement(page);
  await openCreateUserDialog(page);
  await fillUserForm(page, data);
  await submitUserForm(page);

  // 验证成功消息
  await expect(page.locator(USER_SELECTORS.successMessage).first()).toBeVisible({ timeout: 5000 });
}

/**
 * 查找用户行
 */
export async function findUserRow(page: Page, username: string): Promise<any> {
  return page.locator(USER_SELECTORS.userRowByName(username)).first();
}

/**
 * 打开用户编辑对话框
 */
export async function openEditUserDialog(page: Page, username: string): Promise<void> {
  const userRow = await findUserRow(page, username);
  const editButton = userRow.locator(USER_SELECTORS.editButton).first();

  if (await editButton.isVisible()) {
    await editButton.click();
    await page.waitForTimeout(500);
    await expect(page.locator(USER_SELECTORS.modal).first()).toBeVisible();
  }
}

/**
 * 删除用户（带确认）
 */
export async function deleteUserViaUI(page: Page, username: string): Promise<void> {
  const userRow = await findUserRow(page, username);
  const deleteButton = userRow.locator(USER_SELECTORS.deleteButton).first();

  await deleteButton.click();
  await page.waitForTimeout(500);

  // 确认删除
  const confirmButton = page.locator(USER_SELECTORS.confirmOk).first();
  if (await confirmButton.isVisible()) {
    await confirmButton.click();
  }

  await page.waitForTimeout(1000);
}

/**
 * 重置用户密码
 */
export async function resetUserPasswordViaUI(page: Page, username: string): Promise<void> {
  const userRow = await findUserRow(page, username);
  const resetButton = userRow.locator(USER_SELECTORS.resetPasswordButton).first();

  if (await resetButton.isVisible()) {
    await resetButton.click();
    await page.waitForTimeout(500);

    // 确认重置
    const confirmButton = page.locator(USER_SELECTORS.confirmOk).first();
    if (await confirmButton.isVisible()) {
      await confirmButton.click();
    }
  }

  await page.waitForTimeout(1000);
}

/**
 * 激活用户
 */
export async function activateUserViaUI(page: Page, username: string): Promise<void> {
  const userRow = await findUserRow(page, username);
  const activateButton = userRow.locator(USER_SELECTORS.activateButton).first();

  if (await activateButton.isVisible()) {
    await activateButton.click();
    await page.waitForTimeout(500);

    // 确认激活
    const confirmButton = page.locator(USER_SELECTORS.confirmOk).first();
    if (await confirmButton.isVisible()) {
      await confirmButton.click();
    }
  }

  await page.waitForTimeout(1000);
}

/**
 * 停用用户
 */
export async function deactivateUserViaUI(page: Page, username: string): Promise<void> {
  const userRow = await findUserRow(page, username);
  const deactivateButton = userRow.locator(USER_SELECTORS.deactivateButton).first();

  if (await deactivateButton.isVisible()) {
    await deactivateButton.click();
    await page.waitForTimeout(500);

    // 确认停用
    const confirmButton = page.locator(USER_SELECTORS.confirmOk).first();
    if (await confirmButton.isVisible()) {
      await confirmButton.click();
    }
  }

  await page.waitForTimeout(1000);
}

/**
 * 解锁用户
 */
export async function unlockUserViaUI(page: Page, username: string): Promise<void> {
  const userRow = await findUserRow(page, username);
  const unlockButton = userRow.locator(USER_SELECTORS.unlockButton).first();

  if (await unlockButton.isVisible()) {
    await unlockButton.click();
    await page.waitForTimeout(500);

    // 确认解锁
    const confirmButton = page.locator(USER_SELECTORS.confirmOk).first();
    if (await confirmButton.isVisible()) {
      await confirmButton.click();
    }
  }

  await page.waitForTimeout(1000);
}

/**
 * 搜索用户
 */
export async function searchUser(page: Page, keyword: string): Promise<void> {
  const searchInput = page.locator(USER_SELECTORS.searchInput).first();
  await searchInput.fill(keyword);
  await page.waitForTimeout(500);
}

/**
 * 获取用户状态
 */
export async function getUserStatus(page: Page, username: string): Promise<UserStatus | null> {
  const userRow = await findUserRow(page, username);
  const statusTag = userRow.locator(USER_SELECTORS.statusTag).first();

  if (await statusTag.isVisible()) {
    const statusText = await statusTag.textContent();
    if (statusText) {
      const status = statusText.toLowerCase().trim();
      if (['pending', 'active', 'inactive', 'locked', 'deleted'].includes(status)) {
        return status as UserStatus;
      }
    }
  }

  return null;
}

/**
 * 验证用户状态
 */
export async function verifyUserStatus(page: Page, username: string, expectedStatus: UserStatus): Promise<boolean> {
  const actualStatus = await getUserStatus(page, username);
  return actualStatus === expectedStatus;
}

/**
 * 验证用户存在
 */
export async function verifyUserExists(page: Page, username: string): Promise<boolean> {
  const userRow = await findUserRow(page, username);
  return await userRow.isVisible();
}

/**
 * 验证用户不存在
 */
export async function verifyUserNotExists(page: Page, username: string): Promise<boolean> {
  const userRow = await findUserRow(page, username);
  const isVisible = await userRow.isVisible();
  return !isVisible;
}

/**
 * 获取用户列表中的用户数量
 */
export async function getUserListCount(page: Page): Promise<number> {
  const userRows = page.locator(USER_SELECTORS.userRow);
  return await userRows.count();
}

/**
 * 等待用户列表更新
 */
export async function waitForUserListUpdate(page: Page, expectedCount?: number): Promise<void> {
  await page.waitForTimeout(500);

  if (expectedCount !== undefined) {
    await page.waitForFunction(
      (count) => {
        const rows = document.querySelectorAll('tr[data-row-key], .user-item');
        return rows.length === count;
      },
      expectedCount,
      { timeout: 5000 }
    );
  }
}

/**
 * 验证成功消息
 */
export async function verifySuccessMessage(page: Page, expectedText?: string): Promise<void> {
  const successMsg = page.locator(USER_SELECTORS.successMessage).first();
  await expect(successMsg).toBeVisible({ timeout: 5000 });

  if (expectedText) {
    await expect(successMsg).toContainText(expectedText);
  }
}

/**
 * 验证错误消息
 */
export async function verifyErrorMessage(page: Page, expectedText?: string): Promise<void> {
  const errorMsg = page.locator(USER_SELECTORS.errorMessage).first();
  await expect(errorMsg).toBeVisible({ timeout: 5000 });

  if (expectedText) {
    await expect(errorMsg).toContainText(expectedText);
  }
}

// ============================================
// 辅助函数
// ============================================

/**
 * 生成随机用户名
 */
export function generateRandomUsername(prefix = 'test_user'): string {
  const timestamp = Date.now();
  const random = Math.floor(Math.random() * 1000);
  return `${prefix}_${timestamp}_${random}`;
}

/**
 * 生成随机邮箱
 */
export function generateRandomEmail(username?: string): string {
  const name = username || generateRandomUsername();
  return `${name}@example.com`;
}

/**
 * 生成测试用户数据
 */
export function generateTestUserData(overrides?: Partial<CreateUserRequest>): CreateUserRequest {
  const username = generateRandomUsername();
  return {
    username,
    email: generateRandomEmail(username),
    password: 'Test1234!',
    roles: ['user'],
    status: 'pending',
    ...overrides,
  };
}

/**
 * 等待用户状态变更（通过 UI）
 */
export async function waitForUserStatusChangeUI(
  page: Page,
  username: string,
  expectedStatus: UserStatus,
  timeout = 10000
): Promise<boolean> {
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    const currentStatus = await getUserStatus(page, username);
    if (currentStatus === expectedStatus) {
      return true;
    }
    await page.waitForTimeout(500);
    await page.reload();
    await page.waitForLoadState('networkidle');
  }

  return false;
}
