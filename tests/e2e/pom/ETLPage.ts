/**
 * ETL Page Object Model
 *
 * Page: /data/etl
 * Features: ETL task management, execution, monitoring
 */

import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class ETLPage extends BasePage {
  readonly PAGE_PATH = '/data/etl';

  // Page locators
  readonly createTaskButton: Locator;
  readonly searchInput: Locator;
  readonly table: Locator;
  readonly tableBody: Locator;

  // Modal locators
  readonly taskNameInput: Locator;
  readonly sourceSelect: Locator;
  readonly targetSelect: Locator;
  readonly scheduleInput: Locator;
  readonly configTextarea: Locator;
  readonly saveButton: Locator;
  readonly runButton: Locator;

  // Task action locators
  readonly stopButton: Locator;
  readonly viewLogsButton: Locator;
  readonly editButton: Locator;

  constructor(page: Page) {
    super(page);

    // Initialize locators
    this.createTaskButton = page.locator('button:has-text("新建任务"), button:has-text("创建"), button:has(.anticon-plus)');
    this.searchInput = page.locator('input[placeholder*="搜索"], .ant-input-search input');
    this.table = page.locator('.ant-table');
    this.tableBody = page.locator('.ant-table-tbody');

    // Modal locators
    this.taskNameInput = page.locator('.ant-modal input[name="name"], .ant-modal label:has-text("任务名称") + input');
    this.sourceSelect = page.locator('.ant-modal .ant-select:has-text("数据源"), .ant-modal label:has-text("源") + .ant-select');
    this.targetSelect = page.locator('.ant-modal .ant-select:has-text("目标"), .ant-modal label:has-text("目标") + .ant-select');
    this.scheduleInput = page.locator('.ant-modal input[name="schedule"], .ant-modal label:has-text("调度") + input');
    this.configTextarea = page.locator('.ant-modal textarea, .ant-modal label:has-text("配置") + textarea');
    this.saveButton = page.locator('.ant-modal button:has-text("保存"), .ant-modal button:has-text("确定"), .ant-modal .ant-btn-primary');

    // Task action locators
    this.runButton = page.locator('button:has-text("运行"), button:has(.anticon-play-circle)');
    this.stopButton = page.locator('button:has-text("停止"), button:has(.anticon-stop)');
    this.viewLogsButton = page.locator('button:has-text("日志"), button:has-text("Logs")');
    this.editButton = page.locator('button:has-text("编辑"), button:has(.anticon-edit)');
  }

  /**
   * Navigate to ETL page
   */
  async goto(): Promise<void> {
    await this.page.goto(this.PAGE_PATH);
    await this.waitForStable();
  }

  /**
   * Click create task button
   */
  async clickCreateTask(): Promise<void> {
    await this.createTaskButton.first().click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Fill ETL task form
   */
  async fillForm(data: {
    name: string;
    source: string;
    target: string;
    schedule?: string;
    config?: string;
  }): Promise<void> {
    // Name
    await this.taskNameInput.fill(data.name);
    await this.page.waitForTimeout(200);

    // Source
    await this.sourceSelect.click();
    await this.page.waitForTimeout(200);
    await this.page.locator(`.ant-select-item:has-text("${data.source}")`).click();
    await this.page.waitForTimeout(200);

    // Target
    await this.targetSelect.click();
    await this.page.waitForTimeout(200);
    await this.page.locator(`.ant-select-item:has-text("${data.target}")`).click();
    await this.page.waitForTimeout(200);

    // Schedule (optional)
    if (data.schedule && await this.scheduleInput.isVisible()) {
      await this.scheduleInput.fill(data.schedule);
      await this.page.waitForTimeout(200);
    }

    // Config (optional)
    if (data.config && await this.configTextarea.isVisible()) {
      await this.configTextarea.fill(data.config);
      await this.page.waitForTimeout(200);
    }
  }

  /**
   * Create an ETL task
   */
  async createTask(data: {
    name: string;
    source: string;
    target: string;
    schedule?: string;
    config?: string;
  }): Promise<boolean> {
    await this.clickCreateTask();
    await this.fillForm(data);

    await this.saveButton.first().click();
    await this.page.waitForTimeout(1000);

    return await this.verifyToastMessage('success');
  }

  /**
   * Run an ETL task
   */
  async runTask(taskName: string): Promise<boolean> {
    const row = this.tableBody.locator('.ant-table-row').filter({ hasText: taskName });
    await row.locator('button:has-text("运行"), button:has(.anticon-play-circle)').first().click();
    await this.page.waitForTimeout(1000);

    return await this.verifyToastMessage('success');
  }

  /**
   * Stop a running task
   */
  async stopTask(taskName: string): Promise<boolean> {
    const row = this.tableBody.locator('.ant-table-row').filter({ hasText: taskName });
    await row.locator('button:has-text("停止"), button:has(.anticon-stop)').first().click();
    await this.page.waitForTimeout(500);

    await this.confirmDialog();

    return await this.verifyToastMessage('success');
  }

  /**
   * Get task status
   */
  async getTaskStatus(taskName: string): Promise<string> {
    const row = this.tableBody.locator('.ant-table-row').filter({ hasText: taskName });
    const statusCell = row.locator('.ant-table-cell').nth(2);

    return await statusCell.textContent() || '';
  }

  /**
   * Get task count
   */
  async getTaskCount(): Promise<number> {
    await this.waitForTableLoad();
    return await this.getTableRowCount();
  }

  /**
   * Check if task exists
   */
  async taskExists(name: string): Promise<boolean> {
    const row = this.tableBody.locator('.ant-table-row').filter({ hasText: name });
    return await row.count() > 0;
  }

  /**
   * Search for a task
   */
  async search(name: string): Promise<void> {
    await this.searchInput.fill(name);
    await this.page.waitForTimeout(1000);
  }

  /**
   * Delete a task
   */
  async deleteTask(name: string): Promise<boolean> {
    const row = this.tableBody.locator('.ant-table-row').filter({ hasText: name });
    await row.locator('button:has(.anticon-ellipsis), .ant-dropdown-trigger').first().click();
    await this.page.waitForTimeout(300);

    await this.page.locator('.ant-dropdown-menu-item:has-text("删除")').click();
    await this.confirmDialog();

    return await this.verifyToastMessage('success');
  }

  /**
   * View task logs
   */
  async viewLogs(name: string): Promise<void> {
    const row = this.tableBody.locator('.ant-table-row').filter({ hasText: name });
    await row.locator('button:has-text("日志"), button:has(.anticon-file-text)').first().click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Get task info from table
   */
  async getTaskInfo(name: string): Promise<{
    name: string;
    source: string;
    target: string;
    status: string;
  } | null> {
    const row = this.tableBody.locator('.ant-table-row').filter({ hasText: name });
    if (await row.count() === 0) {
      return null;
    }

    const cells = row.locator('.ant-table-cell');
    const nameText = await cells.nth(0).textContent() || '';
    const sourceText = await cells.nth(1).textContent() || '';
    const targetText = await cells.nth(2).textContent() || '';
    const statusText = await cells.nth(3).textContent() || '';

    return {
      name: nameText.trim(),
      source: sourceText.trim(),
      target: targetText.trim(),
      status: statusText.trim(),
    };
  }

  /**
   * Get all task names
   */
  async getAllNames(): Promise<string[]> {
    await this.waitForTableLoad();
    return await this.getTableColumnValues(0);
  }

  /**
   * Refresh the table
   */
  async refresh(): Promise<void> {
    const refreshButton = this.page.locator('button:has(.anticon-reload), button:has-text("刷新")');
    await refreshButton.click();
    await this.waitForTableLoad();
  }
}
