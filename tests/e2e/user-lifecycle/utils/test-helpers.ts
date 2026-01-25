/**
 * 通用测试工具类
 * 提供测试中常用的辅助方法
 */

import { Page, expect, Locator } from '@playwright/test';
import type { TestRole, UserStatus } from '../fixtures/user-lifecycle.fixture';

// ============================================
// 页面导航工具
// ============================================

export class PageNavigator {
  constructor(private readonly page: Page, private readonly baseUrl: string) {}

  /**
   * 导航到指定页面
   */
  async goto(path: string): Promise<void> {
    await this.page.goto(`${this.baseUrl}${path}`);
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * 导航到用户管理页面
   */
  async toUserManagement(): Promise<void> {
    await this.goto('/admin/users');
  }

  /**
   * 导航到角色管理页面
   */
  async toRoleManagement(): Promise<void> {
    await this.goto('/admin/roles');
  }

  /**
   * 导航到用户组管理页面
   */
  async toGroupManagement(): Promise<void> {
    await this.goto('/admin/groups');
  }

  /**
   * 导航到审计日志页面
   */
  async toAuditLogs(): Promise<void> {
    await this.goto('/admin/audit');
  }

  /**
   * 导航到数据集管理页面
   */
  async toDatasets(): Promise<void> {
    await this.goto('/data/datasets');
  }

  /**
   * 导航到工作流页面
   */
  async toWorkflows(): Promise<void> {
    await this.goto('/ai/workflows');
  }

  /**
   * 导航到 AI 对话页面
   */
  async toAIChat(): Promise<void> {
    await this.goto('/ai/chat');
  }

  /**
   * 登出
   */
  async logout(): Promise<void> {
    await this.goto('/logout');
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * 重新加载页面
   */
  async reload(): Promise<void> {
    await this.page.reload();
    await this.page.waitForLoadState('networkidle');
  }
}

// ============================================
// 表单操作工具
// ============================================

export class FormHelper {
  constructor(private readonly page: Page) {}

  /**
   * 填写表单字段
   */
  async fillForm(fields: Record<string, string | number>): Promise<void> {
    for (const [field, value] of Object.entries(fields)) {
      const selector = `[name="${field}"], #${field}`;
      const element = this.page.locator(selector).first();

      if (await element.isVisible()) {
        const tagName = await element.evaluate(el => el.tagName.toLowerCase());

        if (tagName === 'input' || tagName === 'textarea') {
          await element.fill(String(value));
        } else if (tagName === 'select') {
          await element.selectOption(String(value));
        }
      }
    }
  }

  /**
   * 填写 Ant Design 表单
   */
  async fillAntForm(fields: Record<string, string | number | boolean>): Promise<void> {
    for (const [field, value] of Object.entries(fields)) {
      const input = this.page.locator(`#${field}, [name="${field}"]`).first();
      const tagName = await input.evaluate(el => el.tagName.toLowerCase());

      if (tagName === 'input') {
        const inputType = await input.getAttribute('type');
        if (inputType === 'checkbox') {
          if (value) {
            await input.check();
          } else {
            await input.uncheck();
          }
        } else if (inputType === 'radio') {
          await this.page.check(`input[name="${field}"][value="${value}"]`);
        } else {
          await input.fill(String(value));
        }
      } else if (tagName === 'textarea') {
        await input.fill(String(value));
      } else if (tagName === 'select') {
        await input.selectOption(String(value));
      }
    }
  }

  /**
   * 选择 Ant Design Select 选项
   */
  async selectAntOption(selector: string, optionText: string): Promise<void> {
    await this.page.click(selector);
    await this.page.waitForSelector('.ant-select-dropdown', { state: 'visible' });
    await this.page.click(`.ant-select-dropdown .ant-select-item:has-text("${optionText}")`);
  }

  /**
   * 选择 Ant Design Cascader 选项
   */
  async selectAntCascader(selector: string, options: string[]): Promise<void> {
    await this.page.click(selector);
    await this.page.waitForSelector('.ant-cascader-dropdown', { state: 'visible' });

    for (const option of options) {
      const optionElement = this.page.locator(`.ant-cascader-menu-item:has-text("${option}")`).first();
      await optionElement.click();
      await this.page.waitForTimeout(200);
    }
  }

  /**
   * 选择 Ant Design Tree 选项
   */
  async selectAntTreeNode(treeSelector: string, nodeText: string): Promise<void> {
    const treeNode = this.page.locator(`${treeSelector} .ant-tree-node:has-text("${nodeText}")`).first();
    await treeNode.click();
  }

  /**
   * 选择 Ant Design DatePicker 日期
   */
  async selectAntDate(selector: string, date: Date): Promise<void> {
    await this.page.click(selector);
    await this.page.waitForSelector('.ant-picker-dropdown', { state: 'visible' });

    const year = date.getFullYear();
    const month = date.getMonth() + 1;
    const day = date.getDate();

    // 选择年份（如果需要）
    // 选择月份
    // 选择日期
    await this.page.click(`.ant-picker-cell[title="${year}-${month}-${day}"]`);
  }

  /**
   * 上传文件
   */
  async uploadFile(selector: string, filePath: string): Promise<void> {
    const fileInput = this.page.locator(`${selector} input[type="file"]`);
    await fileInput.setInputFiles(filePath);
  }

  /**
   * 提交表单
   */
  async submit(formSelector: string = 'form'): Promise<void> {
    const submitButton = this.page.locator(`${formSelector} button[type="submit"], ${formSelector} .ant-btn-primary`).first();
    await submitButton.click();
    await this.page.waitForTimeout(500);
  }

  /**
   * 重置表单
   */
  async reset(formSelector: string = 'form'): Promise<void> {
    const resetButton = this.page.locator(`${formSelector} button[type="reset"], ${formSelector} .ant-btn-default`).first();
    await resetButton.click();
  }
}

// ============================================
// 表格操作工具
// ============================================

export class TableHelper {
  constructor(private readonly page: Page) {}

  /**
   * 获取表格行数
   */
  async getRowCount(tableSelector: string = '.ant-table'): Promise<number> {
    const rows = this.page.locator(`${tableSelector} .ant-table-tbody .ant-table-row`);
    return await rows.count();
  }

  /**
   * 获取指定行数据
   */
  async getRowData(rowIndex: number, tableSelector: string = '.ant-table'): Promise<string[]> {
    const cells = this.page.locator(
      `${tableSelector} .ant-table-tbody .ant-table-row:nth-child(${rowIndex + 1}) .ant-table-cell`
    );
    const count = await cells.count();
    const data: string[] = [];

    for (let i = 0; i < count; i++) {
      const text = await cells.nth(i).textContent();
      data.push(text || '');
    }

    return data;
  }

  /**
   * 根据单元格内容查找行
   */
  async findRowByCellText(
    text: string,
    tableSelector: string = '.ant-table'
  ): Promise<Locator | null> {
    const row = this.page.locator(`${tableSelector} .ant-table-tbody tr:has-text("${text}")`).first();
    const count = await row.count();

    return count > 0 ? row : null;
  }

  /**
   * 点击表格行操作按钮
   */
  async clickRowAction(
    rowIndex: number,
    actionText: string,
    tableSelector: string = '.ant-table'
  ): Promise<void> {
    const row = this.page.locator(
      `${tableSelector} .ant-table-tbody .ant-table-row:nth-child(${rowIndex + 1})`
    );
    const actionButton = row.locator(`button:has-text("${actionText}"), a:has-text("${actionText}")`).first();

    await actionButton.click();
  }

  /**
   * 选择表格行（复选框）
   */
  async selectRow(rowIndex: number, tableSelector: string = '.ant-table'): Promise<void> {
    const checkbox = this.page.locator(
      `${tableSelector} .ant-table-tbody .ant-table-row:nth-child(${rowIndex + 1}) input[type="checkbox"]`
    ).first();
    await checkbox.check();
  }

  /**
   * 选择所有行
   */
  async selectAll(tableSelector: string = '.ant-table'): Promise<void> {
    const headerCheckbox = this.page.locator(
      `${tableSelector} .ant-table-thead input[type="checkbox"]`
    ).first();
    await headerCheckbox.check();
  }

  /**
   * 排序表格
   */
  async sortByColumn(columnIndex: number, tableSelector: string = '.ant-table'): Promise<void> {
    const headerCell = this.page.locator(
      `${tableSelector} .ant-table-thead th:nth-child(${columnIndex + 1})`
    ).first();

    await headerCell.click();
    await this.page.waitForTimeout(300);
  }

  /**
   * 等待表格加载完成
   */
  async waitForLoad(tableSelector: string = '.ant-table'): Promise<void> {
    await this.page.waitForSelector(`${tableSelector} .ant-table-tbody`, { state: 'attached' });
    await this.page.waitForSelector(`${tableSelector} .ant-spin`, { state: 'hidden', timeout: 10000 }).catch(() => {});
  }
}

// ============================================
// 对话框操作工具
// ============================================

export class DialogHelper {
  constructor(private readonly page: Page) {}

  /**
   * 确认 Ant Design Popconfirm
   */
  async confirmPopconfirm(): Promise<void> {
    const confirmButton = this.page.locator('.ant-popconfirm-buttons .ant-btn-primary').first();
    await confirmButton.click();
  }

  /**
   * 取消 Ant Design Popconfirm
   */
  async cancelPopconfirm(): Promise<void> {
    const cancelButton = this.page.locator('.ant-popconfirm-buttons .ant-btn-default').first();
    await cancelButton.click();
  }

  /**
   * 确认 Ant Design Modal
   */
  async confirmModal(buttonText: string = '确定'): Promise<void> {
    const confirmButton = this.page.locator(`.ant-modal button:has-text("${buttonText}")`).first();
    await confirmButton.click();
  }

  /**
   * 取消 Ant Design Modal
   */
  async cancelModal(buttonText: string = '取消'): Promise<void> {
    const cancelButton = this.page.locator(`.ant-modal button:has-text("${buttonText}")`).first();
    await cancelButton.click();
  }

  /**
   * 关闭 Ant Design Modal
   */
  async closeModal(): Promise<void> {
    const closeButton = this.page.locator('.ant-modal-close').first();
    if (await closeButton.isVisible()) {
      await closeButton.click();
    }
    await this.page.waitForSelector('.ant-modal', { state: 'hidden' }).catch(() => {});
  }

  /**
   * 等待 Modal 打开
   */
  async waitForModal(title?: string): Promise<void> {
    await this.page.waitForSelector('.ant-modal', { state: 'visible' });

    if (title) {
      await this.page.waitForSelector(`.ant-modal-title:has-text("${title}")`);
    }
  }

  /**
   * 等待 Drawer 打开
   */
  async waitForDrawer(title?: string): Promise<void> {
    await this.page.waitForSelector('.ant-drawer', { state: 'visible' });

    if (title) {
      await this.page.waitForSelector(`.ant-drawer-title:has-text("${title}")`);
    }
  }

  /**
   * 关闭 Drawer
   */
  async closeDrawer(): Promise<void> {
    const closeButton = this.page.locator('.ant-drawer-close').first();
    if (await closeButton.isVisible()) {
      await closeButton.click();
    }
    await this.page.waitForSelector('.ant-drawer', { state: 'hidden' }).catch(() => {});
  }
}

// ============================================
// 消息提示工具
// ============================================

export class MessageHelper {
  constructor(private readonly page: Page) {}

  /**
   * 等待成功消息
   */
  async waitForSuccess(text?: string): Promise<void> {
    const message = this.page.locator('.ant-message-success');
    await expect(message.first()).toBeVisible({ timeout: 5000 });

    if (text) {
      await expect(message).toContainText(text);
    }
  }

  /**
   * 等待错误消息
   */
  async waitForError(text?: string): Promise<void> {
    const message = this.page.locator('.ant-message-error');
    await expect(message.first()).toBeVisible({ timeout: 5000 });

    if (text) {
      await expect(message).toContainText(text);
    }
  }

  /**
   * 等待警告消息
   */
  async waitForWarning(text?: string): Promise<void> {
    const message = this.page.locator('.ant-message-warning');
    await expect(message.first()).toBeVisible({ timeout: 5000 });

    if (text) {
      await expect(message).toContainText(text);
    }
  }

  /**
   * 等待信息消息
   */
  async waitForInfo(text?: string): Promise<void> {
    const message = this.page.locator('.ant-message-info');
    await expect(message.first()).toBeVisible({ timeout: 5000 });

    if (text) {
      await expect(message).toContainText(text);
    }
  }

  /**
   * 等待消息消失
   */
  async waitForDisappear(): Promise<void> {
    await this.page.waitForSelector('.ant-message', { state: 'hidden', timeout: 5000 }).catch(() => {});
  }

  /**
   * 获取所有消息
   */
  async getAllMessages(): Promise<string[]> {
    const messages = this.page.locator('.ant-message .ant-message-notice-content');
    const count = await messages.count();
    const result: string[] = [];

    for (let i = 0; i < count; i++) {
      const text = await messages.nth(i).textContent();
      result.push(text || '');
    }

    return result;
  }
}

// ============================================
// 加载状态工具
// ============================================

export class LoadingHelper {
  constructor(private readonly page: Page) {}

  /**
   * 等待加载完成
   */
  async waitForLoad(): Promise<void> {
    await Promise.all([
      this.page.waitForSelector('.ant-spin', { state: 'hidden', timeout: 30000 }).catch(() => {}),
      this.page.waitForLoadState('networkidle'),
    ]);
  }

  /**
   * 等待加载中
   */
  async waitForLoading(): Promise<void> {
    await this.page.waitForSelector('.ant-spin, .ant-spin-dot-holding', { state: 'visible' });
  }

  /**
   * 等待按钮加载完成
   */
  async waitForButton(buttonSelector: string): Promise<void> {
    const button = this.page.locator(buttonSelector);

    // 等待按钮不在加载状态
    await button.waitFor({ state: 'visible' });
    await expect(button.locator('.anticon-loading')).not.toBeAttached();
  }

  /**
   * 等待表格数据加载
   */
  async waitForTableData(tableSelector: string = '.ant-table'): Promise<void> {
    await this.page.waitForSelector(`${tableSelector} .ant-table-tbody tr`, { timeout: 30000 });
    await this.page.waitForSelector(`${tableSelector} .ant-spin`, { state: 'hidden' }).catch(() => {});
  }
}

// ============================================
// 验证工具
// ============================================

export class AssertionHelper {
  constructor(private readonly page: Page) {}

  /**
   * 验证页面标题
   */
  async assertTitle(expectedTitle: string): Promise<void> {
    await expect(this.page).toHaveTitle(new RegExp(expectedTitle));
  }

  /**
   * 验证当前 URL
   */
  async assertUrl(expectedUrl: string): Promise<void> {
    const currentUrl = this.page.url();
    expect(currentUrl).toContain(expectedUrl);
  }

  /**
   * 验证元素可见
   */
  async assertVisible(selector: string): Promise<void> {
    await expect(this.page.locator(selector).first()).toBeVisible();
  }

  /**
   * 验证元素不可见
   */
  async assertNotVisible(selector: string): Promise<void> {
    await expect(this.page.locator(selector).first()).not.toBeVisible();
  }

  /**
   * 验证文本内容
   */
  async assertText(selector: string, text: string): Promise<void> {
    await expect(this.page.locator(selector).first()).toContainText(text);
  }

  /**
   * 验证输入框值
   */
  async assertValue(selector: string, expectedValue: string): Promise<void> {
    const input = this.page.locator(selector).first();
    await expect(input).toHaveValue(expectedValue);
  }

  /**
   * 验证复选框状态
   */
  async assertChecked(selector: string, checked: boolean = true): Promise<void> {
    const checkbox = this.page.locator(selector).first();
    if (checked) {
      await expect(checkbox).toBeChecked();
    } else {
      await expect(checkbox).not.toBeChecked();
    }
  }

  /**
   * 验证禁用状态
   */
  async assertDisabled(selector: string): Promise<void> {
    await expect(this.page.locator(selector).first()).toBeDisabled();
  }

  /**
   * 验证启用状态
   */
  async assertEnabled(selector: string): Promise<void> {
    await expect(this.page.locator(selector).first()).not.toBeDisabled();
  }

  /**
   * 验证元素数量
   */
  async assertCount(selector: string, expectedCount: number): Promise<void> {
    const elements = this.page.locator(selector);
    await expect(elements).toHaveCount(expectedCount);
  }

  /**
   * 验证选项卡激活状态
   */
  async assertActiveTab(tabText: string): Promise<void> {
    const activeTab = this.page.locator(`.ant-tabs-tab-active:has-text("${tabText}")`);
    await expect(activeTab.first()).toBeVisible();
  }
}

// ============================================
// 导出所有工具类
// ============================================

export const TestHelpers = {
  PageNavigator,
  FormHelper,
  TableHelper,
  DialogHelper,
  MessageHelper,
  LoadingHelper,
  AssertionHelper,
};

// 快捷工厂函数
export function createHelpers(page: Page, baseUrl: string) {
  return {
    navigator: new PageNavigator(page, baseUrl),
    form: new FormHelper(page),
    table: new TableHelper(page),
    dialog: new DialogHelper(page),
    message: new MessageHelper(page),
    loading: new LoadingHelper(page),
    assertion: new AssertionHelper(page),
  };
}
