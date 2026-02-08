/**
 * Notebook Page Object Model
 *
 * Page: /model/notebooks
 * Features: Notebook CRUD, code execution, kernel management
 */

import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class NotebookPage extends BasePage {
  readonly PAGE_PATH = '/model/notebooks';

  // Page locators
  readonly createButton: Locator;
  readonly searchInput: Locator;
  readonly table: Locator;
  readonly tableBody: Locator;

  // Modal locators
  readonly nameInput: Locator;
  readonly kernelSelect: Locator;
  readonly descriptionTextarea: Locator;
  readonly saveButton: Locator;

  // Notebook action locators
  readonly startButton: Locator;
  readonly stopButton: Locator;
  readonly runButton: Locator;
  readonly codeEditor: Locator;
  readonly outputArea: Locator;

  // Status locators
  readonly statusBadge: Locator;
  readonly kernelStatus: Locator;

  constructor(page: Page) {
    super(page);

    // Initialize locators
    this.createButton = page.locator('button:has-text("新建"), button:has-text("创建"), button:has(.anticon-plus)');
    this.searchInput = page.locator('input[placeholder*="搜索"], .ant-input-search input');
    this.table = page.locator('.ant-table');
    this.tableBody = page.locator('.ant-table-tbody');

    // Modal locators
    this.nameInput = page.locator('.ant-modal input[name="name"], .ant-modal label:has-text("名称") + input');
    this.kernelSelect = page.locator('.ant-modal .ant-select:has-text("内核"), .ant-modal label:has-text("Kernel") + .ant-select');
    this.descriptionTextarea = page.locator('.ant-modal textarea, .ant-modal label:has-text("描述") + textarea');
    this.saveButton = page.locator('.ant-modal button:has-text("创建"), .ant-modal button:has-text("确定"), .ant-modal .ant-btn-primary');

    // Notebook action locators
    this.startButton = page.locator('button:has-text("启动"), button:has(.anticon-play-circle)');
    this.stopButton = page.locator('button:has-text("停止"), button:has(.anticon-stop)');
    this.runButton = page.locator('button:has-text("运行"), button:has(.anticon-caret-right)');
    this.codeEditor = page.locator('.monaco-editor, .CodeMirror, [contenteditable="true"], textarea.code-editor');
    this.outputArea = page.locator('.output-area, .cell-output, .execution-result');

    // Status locators
    this.statusBadge = page.locator('.ant-badge, .status-badge');
    this.kernelStatus = page.locator('.kernel-status, .ant-tag');
  }

  /**
   * Navigate to notebooks page
   */
  async goto(): Promise<void> {
    await this.page.goto(this.PAGE_PATH);
    await this.waitForStable();
  }

  /**
   * Click create button
   */
  async clickCreate(): Promise<void> {
    await this.createButton.first().click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Fill notebook form
   */
  async fillForm(data: {
    name: string;
    kernel?: string;
    description?: string;
  }): Promise<void> {
    // Name
    await this.nameInput.fill(data.name);
    await this.page.waitForTimeout(200);

    // Kernel (optional)
    if (data.kernel && await this.kernelSelect.isVisible()) {
      await this.kernelSelect.click();
      await this.page.waitForTimeout(200);
      await this.page.locator(`.ant-select-item:has-text("${data.kernel}")`).click();
      await this.page.waitForTimeout(200);
    }

    // Description (optional)
    if (data.description && await this.descriptionTextarea.isVisible()) {
      await this.descriptionTextarea.fill(data.description);
      await this.page.waitForTimeout(200);
    }
  }

  /**
   * Create a notebook
   */
  async createNotebook(data: {
    name: string;
    kernel?: string;
    description?: string;
  }): Promise<boolean> {
    await this.clickCreate();
    await this.fillForm(data);

    await this.saveButton.first().click();
    await this.page.waitForTimeout(1000);

    return await this.verifyToastMessage('success');
  }

  /**
   * Open a notebook
   */
  async openNotebook(name: string): Promise<void> {
    const row = this.tableBody.locator('.ant-table-row').filter({ hasText: name });
    await row.locator('a, button:has-text("打开")').first().click();
    await this.page.waitForTimeout(1000);
  }

  /**
   * Start a notebook
   */
  async startNotebook(name: string): Promise<boolean> {
    const row = this.tableBody.locator('.ant-table-row').filter({ hasText: name });
    await row.locator('button:has-text("启动"), button:has(.anticon-play-circle)').first().click();
    await this.page.waitForTimeout(2000);

    return await this.verifyToastMessage('success');
  }

  /**
   * Stop a notebook
   */
  async stopNotebook(name: string): Promise<boolean> {
    const row = this.tableBody.locator('.ant-table-row').filter({ hasText: name });
    await row.locator('button:has-text("停止"), button:has(.anticon-stop)').first().click();
    await this.page.waitForTimeout(1000);

    return await this.verifyToastMessage('success');
  }

  /**
   * Execute code in notebook
   */
  async executeCode(code: string): Promise<void> {
    // Wait for editor to be available
    await this.codeEditor.first().waitFor({ state: 'visible', timeout: 10000 }).catch(() => {});

    // Focus editor and type code
    await this.codeEditor.first().click();
    await this.page.keyboard.press('Control+A');
    await this.page.keyboard.type(code);

    // Click run button
    await this.runButton.first().click();
    await this.page.waitForTimeout(2000);
  }

  /**
   * Get output from code execution
   */
  async getOutput(): Promise<string> {
    await this.page.waitForTimeout(1000);
    const output = await this.outputArea.textContent() || '';
    return output.trim();
  }

  /**
   * Get notebook status
   */
  async getNotebookStatus(name: string): Promise<string> {
    const row = this.tableBody.locator('.ant-table-row').filter({ hasText: name });
    const statusCell = row.locator('.ant-tag, .status-badge');

    return await statusCell.textContent() || '';
  }

  /**
   * Get notebook count
   */
  async getCount(): Promise<number> {
    await this.waitForTableLoad();
    return await this.getTableRowCount();
  }

  /**
   * Check if notebook exists
   */
  async exists(name: string): Promise<boolean> {
    const row = this.tableBody.locator('.ant-table-row').filter({ hasText: name });
    return await row.count() > 0;
  }

  /**
   * Search for a notebook
   */
  async search(name: string): Promise<void> {
    await this.searchInput.fill(name);
    await this.page.waitForTimeout(1000);
  }

  /**
   * Delete a notebook
   */
  async deleteNotebook(name: string): Promise<boolean> {
    const row = this.tableBody.locator('.ant-table-row').filter({ hasText: name });
    await row.locator('button:has(.anticon-ellipsis), .ant-dropdown-trigger').first().click();
    await this.page.waitForTimeout(300);

    await this.page.locator('.ant-dropdown-menu-item:has-text("删除")').click();
    await this.confirmDialog();

    return await this.verifyToastMessage('success');
  }

  /**
   * Get all notebook names
   */
  async getAllNames(): Promise<string[]> {
    await this.waitForTableLoad();
    return await this.getTableColumnValues(0);
  }

  /**
   * Add a new cell to notebook
   */
  async addCell(): Promise<void> {
    const addButton = this.page.locator('button:has-text("添加单元格"), button:has(.anticon-plus)');
    await addButton.click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Save notebook
   */
  async saveNotebook(): Promise<void> {
    const saveButton = this.page.locator('button:has-text("保存"), button:has(.anticon-save)');
    await saveButton.click();
    await this.page.waitForTimeout(1000);
  }

  /**
   * Close notebook and return to list
   */
  async closeNotebook(): Promise<void> {
    const closeButton = this.page.locator('button:has-text("关闭"), .ant-modal-close');
    await closeButton.click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Get kernel status
   */
  async getKernelStatus(): Promise<string> {
    const status = await this.kernelStatus.textContent() || '';
    return status.trim();
  }
}
