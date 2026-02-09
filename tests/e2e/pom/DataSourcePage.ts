/**
 * Data Sources Page Object Model
 *
 * Page: /data/datasources
 * Features: CRUD operations for datasources, connection testing
 */

import { Page, Locator } from '@playwright/test';
import { logger } from '../helpers/logger';
import { BasePage } from './BasePage';

export class DataSourcePage extends BasePage {
  readonly PAGE_PATH = '/data/datasources';

  // Page locators
  readonly createButton: Locator;
  readonly searchInput: Locator;
  readonly table: Locator;
  readonly tableBody: Locator;

  // Modal locators
  readonly createModal: Locator;
  readonly nameInput: Locator;
  readonly typeSelect: Locator;
  readonly hostInput: Locator;
  readonly portInput: Locator;
  readonly databaseInput: Locator;
  readonly usernameInput: Locator;
  readonly passwordInput: Locator;
  readonly testConnectionButton: Locator;
  readonly saveButton: Locator;
  readonly cancelButton: Locator;

  constructor(page: Page) {
    super(page);

    // Initialize locators
    this.createButton = page.locator('button:has-text("新建"), button:has-text("创建"), button:has-text("Create"), button:has(.anticon-plus)');
    this.searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="search"], .ant-input-search input');
    this.table = page.locator('.ant-table');
    this.tableBody = page.locator('.ant-table-tbody');

    // Modal locators
    this.createModal = page.locator('.ant-modal:has-text("数据源"), .ant-modal:has-text("Datasource")');
    this.nameInput = page.locator('.ant-modal input[name="name"], .ant-modal label:has-text("名称") + input');
    this.typeSelect = page.locator('.ant-modal .ant-select:has-text("类型"), .ant-modal label:has-text("类型") + .ant-select');
    this.hostInput = page.locator('.ant-modal input[name="host"], .ant-modal label:has-text("主机") + input');
    this.portInput = page.locator('.ant-modal input[name="port"], .ant-modal label:has-text("端口") + input');
    this.databaseInput = page.locator('.ant-modal input[name="database"], .ant-modal label:has-text("数据库") + input');
    this.usernameInput = page.locator('.ant-modal input[name="username"], .ant-modal label:has-text("用户名") + input');
    this.passwordInput = page.locator('.ant-modal input[name="password"], .ant-modal input[type="password"]');
    this.testConnectionButton = page.locator('.ant-modal button:has-text("测试连接"), .ant-modal button:has-text("Test")');
    this.saveButton = page.locator('.ant-modal button:has-text("保存"), .ant-modal button:has-text("确定"), .ant-modal .ant-btn-primary');
    this.cancelButton = page.locator('.ant-modal button:has-text("取消"), .ant-modal button:has-text("Cancel")');
  }

  /**
   * Navigate to data sources page
   */
  async goto(): Promise<void> {
    await this.page.goto(this.PAGE_PATH);
    await this.waitForStable();
  }

  /**
   * Click create button to open create modal
   */
  async clickCreate(): Promise<void> {
    await this.createButton.first().click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Fill datasource form
   */
  async fillForm(data: {
    name: string;
    type: string;
    host: string;
    port: string;
    database: string;
    username: string;
    password: string;
  }): Promise<void> {
    // Name
    await this.nameInput.fill(data.name);
    await this.page.waitForTimeout(200);

    // Type
    await this.typeSelect.click();
    await this.page.waitForTimeout(200);
    await this.page.locator(`.ant-select-item:has-text("${data.type}")`).click();
    await this.page.waitForTimeout(200);

    // Host
    await this.hostInput.fill(data.host);
    await this.page.waitForTimeout(200);

    // Port
    await this.portInput.fill(data.port);
    await this.page.waitForTimeout(200);

    // Database
    await this.databaseInput.fill(data.database);
    await this.page.waitForTimeout(200);

    // Username
    await this.usernameInput.fill(data.username);
    await this.page.waitForTimeout(200);

    // Password
    await this.passwordInput.fill(data.password);
    await this.page.waitForTimeout(200);
  }

  /**
   * Test connection
   */
  async testConnection(): Promise<boolean> {
    const testButton = this.testConnectionButton.first();
    await testButton.click();
    await this.page.waitForTimeout(2000);

    // Check for success message
    const successMessage = this.page.locator('.ant-message-success, .ant-notification-notice-success');
    const isVisible = await successMessage.isVisible().catch(() => false);

    return isVisible;
  }

  /**
   * Save datasource
   */
  async save(): Promise<void> {
    await this.saveButton.first().click();
    await this.page.waitForTimeout(1000);
  }

  /**
   * Cancel and close modal
   */
  async cancel(): Promise<void> {
    await this.cancelButton.first().click();
    await this.waitForModalClose();
  }

  /**
   * Create a new datasource
   */
  async createDataSource(data: {
    name: string;
    type: string;
    host: string;
    port: string;
    database: string;
    username: string;
    password: string;
    testConnection?: boolean;
  }): Promise<boolean> {
    await this.clickCreate();
    await this.fillForm(data);

    if (data.testConnection !== false) {
      const success = await this.testConnection();
      if (!success) {
        logger.warn('[DataSourcePage] Connection test failed, but continuing...');
      }
    }

    await this.save();
    await this.waitForModalClose();

    // Verify success message
    return await this.verifyToastMessage('success');
  }

  /**
   * Search for a datasource by name
   */
  async search(name: string): Promise<void> {
    await this.searchInput.fill(name);
    await this.page.waitForTimeout(1000);
  }

  /**
   * Get datasource count from table
   */
  async getCount(): Promise<number> {
    await this.waitForTableLoad();
    return await this.getTableRowCount();
  }

  /**
   * Check if datasource exists in table
   */
  async exists(name: string): Promise<boolean> {
    await this.search(name);
    await this.page.waitForTimeout(500);

    const row = this.tableBody.locator('.ant-table-row').filter({ hasText: name });
    return await row.count() > 0;
  }

  /**
   * Click action button for a datasource
   */
  async clickAction(name: string, action: 'edit' | 'delete' | 'test' | string): Promise<void> {
    const row = this.tableBody.locator('.ant-table-row').filter({ hasText: name });
    await row.locator('button:has(.anticon-ellipsis), .ant-dropdown-trigger').first().click();
    await this.page.waitForTimeout(300);

    const actionOption = this.page.locator(`.ant-dropdown-menu-item:has-text("${action}")`);
    await actionOption.click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Delete a datasource
   */
  async delete(name: string): Promise<boolean> {
    await this.clickAction(name, 'delete');

    // Confirm deletion
    await this.confirmDialog();

    // Verify success message
    return await this.verifyToastMessage('success');
  }

  /**
   * Edit a datasource
   */
  async edit(name: string, updates: Partial<{ name: string; host: string; port: string }>): Promise<boolean> {
    await this.clickAction(name, 'edit');
    await this.page.waitForTimeout(500);

    if (updates.name) {
      await this.nameInput.fill(updates.name);
    }
    if (updates.host) {
      await this.hostInput.fill(updates.host);
    }
    if (updates.port) {
      await this.portInput.fill(updates.port);
    }

    await this.save();
    await this.waitForModalClose();

    return await this.verifyToastMessage('success');
  }

  /**
   * Get datasource info from table row
   */
  async getDataSourceInfo(name: string): Promise<{
    name: string;
    type: string;
    host: string;
    status: string;
  } | null> {
    const row = this.tableBody.locator('.ant-table-row').filter({ hasText: name });
    if (await row.count() === 0) {
      return null;
    }

    const cells = row.locator('.ant-table-cell');
    const nameText = await cells.nth(0).textContent() || '';
    const typeText = await cells.nth(1).textContent() || '';
    const hostText = await cells.nth(2).textContent() || '';
    const statusText = await cells.nth(3).textContent() || '';

    return {
      name: nameText.trim(),
      type: typeText.trim(),
      host: hostText.trim(),
      status: statusText.trim(),
    };
  }

  /**
   * Get all datasource names from table
   */
  async getAllNames(): Promise<string[]> {
    await this.waitForTableLoad();
    return await this.getTableColumnValues(0);
  }

  /**
   * Clear search
   */
  async clearSearch(): Promise<void> {
    await this.searchInput.clear();
    await this.page.waitForTimeout(500);
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
