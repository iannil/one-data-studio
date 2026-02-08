/**
 * Base Page Object Model
 *
 * Provides common utilities and locators for all pages
 */

import { Page, Locator } from '@playwright/test';

export class BasePage {
  readonly page: Page;

  // Common locators
  readonly antModal: Locator;
  readonly antDrawer: Locator;
  readonly antTable: Locator;
  readonly antTableBody: Locator;
  readonly antMessage: Locator;
  readonly antNotification: Locator;

  constructor(page: Page) {
    this.page = page;

    // Initialize common locators
    this.antModal = page.locator('.ant-modal');
    this.antDrawer = page.locator('.ant-drawer');
    this.antTable = page.locator('.ant-table');
    this.antTableBody = page.locator('.ant-table-tbody');
    this.antMessage = page.locator('.ant-message');
    this.antNotification = page.locator('.ant-notification');
  }

  /**
   * Navigate to a URL
   */
  async goto(path: string): Promise<void> {
    await this.page.goto(path);
    await this.page.waitForLoadState('domcontentloaded');
  }

  /**
   * Wait for page to be stable
   */
  async waitForStable(): Promise<void> {
    await this.page.waitForLoadState('networkidle');
    await this.page.waitForTimeout(500);
  }

  /**
   * Click a button by text
   */
  async clickButton(text: string): Promise<void> {
    await this.page.click(`button:has-text("${text}")`);
  }

  /**
   * Click a button with exact text
   */
  async clickButtonExact(text: string): Promise<void> {
    await this.page.click(`button:has-text("${text}")`);
  }

  /**
   * Fill an input by placeholder
   */
  async fillByPlaceholder(placeholder: string, value: string): Promise<void> {
    await this.page.fill(`input[placeholder*="${placeholder}"]`, value);
  }

  /**
   * Fill a textarea by placeholder
   */
  async fillTextareaByPlaceholder(placeholder: string, value: string): Promise<void> {
    await this.page.fill(`textarea[placeholder*="${placeholder}"]`, value);
  }

  /**
   * Select from a dropdown
   */
  async selectOption(selector: string, optionText: string): Promise<void> {
    await this.page.click(selector);
    await this.page.waitForSelector('.ant-select-dropdown', { state: 'visible' });
    await this.page.click(`.ant-select-item:has-text("${optionText}")`);
  }

  /**
   * Wait for success message
   */
  async waitForSuccess(): Promise<void> {
    await this.page.waitForSelector('.ant-message-success, .ant-notification-notice-success', { timeout: 5000 });
  }

  /**
   * Wait for modal to be visible
   */
  async waitForModal(): Promise<void> {
    await this.antModal.waitFor({ state: 'visible' });
  }

  /**
   * Wait for modal to be hidden
   */
  async waitForModalHidden(): Promise<void> {
    await this.antModal.waitFor({ state: 'hidden' }).catch(() => {});
  }

  /**
   * Wait for drawer to be visible
   */
  async waitForDrawer(): Promise<void> {
    await this.antDrawer.waitFor({ state: 'visible' });
  }

  /**
   * Wait for drawer to be hidden
   */
  async waitForDrawerHidden(): Promise<void> {
    await this.antDrawer.waitFor({ state: 'hidden' }).catch(() => {});
  }

  /**
   * Get table row count
   */
  async getTableRowCount(): Promise<number> {
    await this.antTable.waitFor({ state: 'visible' });
    const rows = this.antTableBody.locator('.ant-table-row');
    return await rows.count();
  }

  /**
   * Find table row by text
   */
  findTableRowByText(text: string): Locator {
    return this.antTableBody.locator('.ant-table-row').filter({ hasText: text }).first();
  }

  /**
   * Click tab by text
   */
  async clickTab(tabText: string): Promise<void> {
    await this.page.click(`.ant-tabs-tab:has-text("${tabText}")`);
  }

  /**
   * Switch to iframe if needed
   */
  async switchToIframe(selector: string): Promise<void> {
    const frame = this.page.frameLocator(selector);
    // For use in child classes
    return;
  }

  /**
   * Take screenshot on failure
   */
  async screenshot(path: string): Promise<void> {
    await this.page.screenshot({ path, fullPage: true });
  }

  /**
   * Get text content of element
   */
  async getText(selector: string): Promise<string> {
    return await this.page.locator(selector).textContent() || '';
  }

  /**
   * Check if element exists
   */
  async exists(selector: string): Promise<boolean> {
    return await this.page.locator(selector).count() > 0;
  }

  /**
   * Wait for loading to complete
   */
  async waitForLoading(): Promise<void> {
    await this.page.waitForSelector('.ant-spin-spinning, .ant-table-placeholder', { state: 'hidden' }).catch(() => {});
    await this.page.waitForTimeout(500);
  }

  // =============================================================================
  // Extended Helper Methods (Phase 1)
  // =============================================================================

  /**
   * Wait for table to fully load with data
   */
  async waitForTableLoad(): Promise<void> {
    await this.page.waitForSelector('.ant-table', { state: 'visible' });
    await this.page.waitForSelector('.ant-spin-spinning', { state: 'hidden', timeout: 10000 }).catch(() => {});
    await this.page.waitForSelector('.ant-skeleton', { state: 'hidden', timeout: 10000 }).catch(() => {});
    await this.page.waitForTimeout(300);
  }

  /**
   * Wait for modal to close completely
   */
  async waitForModalClose(): Promise<void> {
    await this.antModal.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {});
    await this.page.waitForTimeout(200);
  }

  /**
   * Select a table row by index (0-based)
   */
  async selectTableRow(index: number): Promise<void> {
    await this.waitForTableLoad();
    const checkbox = this.antTableBody.locator('.ant-table-row').nth(index).locator('input[type="checkbox"]');
    await checkbox.check();
    await this.page.waitForTimeout(200);
  }

  /**
   * Get all values from a specific column by index (0-based)
   */
  async getTableColumnValues(columnIndex: number): Promise<string[]> {
    await this.waitForTableLoad();
    const cells = this.antTableBody.locator(`.ant-table-cell:nth-child(${columnIndex + 1})`);
    const count = await cells.count();
    const values: string[] = [];
    for (let i = 0; i < count; i++) {
      const text = await cells.nth(i).textContent() || '';
      values.push(text.trim());
    }
    return values;
  }

  /**
   * Click action button in a table row
   */
  async clickTableRowAction(rowIndex: number, action: 'edit' | 'delete' | 'view' | string): Promise<void> {
    await this.waitForTableLoad();
    const row = this.antTableBody.locator('.ant-table-row').nth(rowIndex);

    switch (action) {
      case 'edit':
        await row.locator('button:has(.anticon-edit), [aria-label*="edit"], button:has-text("编辑")').first().click();
        break;
      case 'delete':
        await row.locator('button:has(.anticon-delete), [aria-label*="delete"], button:has-text("删除")').first().click();
        break;
      case 'view':
        await row.locator('a, button:has(.anticon-eye), [aria-label*="view"]').first().click();
        break;
      default:
        await row.locator(`button:has-text("${action}")`).first().click();
    }
    await this.page.waitForTimeout(300);
  }

  /**
   * Verify toast message appears
   */
  async verifyToastMessage(type: 'success' | 'error' | 'info' | 'warning', expectedText?: string): Promise<boolean> {
    const selector = `.ant-message-${type}, .ant-notification-notice-${type}`;
    try {
      await this.page.waitForSelector(selector, { state: 'visible', timeout: 5000 });
      if (expectedText) {
        const element = this.page.locator(selector).first();
        const text = await element.textContent() || '';
        return text.includes(expectedText);
      }
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Get all visible toast messages
   */
  async getToastMessages(): Promise<string[]> {
    const messages = this.page.locator('.ant-message-notice, .ant-notification-notice');
    const count = await messages.count();
    const result: string[] = [];
    for (let i = 0; i < count; i++) {
      const text = await messages.nth(i).textContent() || '';
      result.push(text.trim());
    }
    return result;
  }

  /**
   * Wait for drawer to close completely
   */
  async waitForDrawerClose(): Promise<void> {
    await this.antDrawer.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {});
    await this.page.waitForTimeout(200);
  }

  /**
   * Click button with icon class
   */
  async clickIconButton(iconClass: string): Promise<void> {
    await this.page.locator(`button .${iconClass}, .anticon-${iconClass}`).first().click();
    await this.page.waitForTimeout(200);
  }

  /**
   * Fill input by label
   */
  async fillByLabel(label: string, value: string): Promise<void> {
    const labelElement = this.page.locator(`label:has-text("${label}")`).first();
    const inputId = await labelElement.getAttribute('for');
    if (inputId) {
      await this.page.locator(`#${inputId}`).fill(value);
    } else {
      const parent = labelElement.locator('..');
      await parent.locator('input, textarea').first().fill(value);
    }
    await this.page.waitForTimeout(200);
  }

  /**
   * Select date in date picker
   */
  async selectDate(date: Date): Promise<void> {
    const day = date.getDate();
    const month = date.getMonth();
    const year = date.getFullYear();

    await this.page.click('.ant-picker-input');
    await this.page.waitForTimeout(300);

    // Select year if needed
    const yearButton = this.page.locator('.ant-picker-header-year-btn');
    if (await yearButton.isVisible()) {
      await yearButton.click();
      await this.page.locator(`.ant-picker-year-panel .ant-picker-cell:has-text("${year}")`).click();
    }

    // Select month if needed
    const monthButton = this.page.locator('.ant-picker-header-month-btn');
    if (await monthButton.isVisible()) {
      await monthButton.click();
      const monthNames = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];
      await this.page.locator(`.ant-picker-month-panel .ant-picker-cell:has-text("${monthNames[month]}")`).click();
    }

    // Select day
    await this.page.locator(`.ant-picker-cell:has-text("${day}"):not(.ant-picker-cell-in-view)`).click();
    await this.page.waitForTimeout(200);
  }

  /**
   * Upload file via input
   */
  async uploadFile(selector: string, filePath: string): Promise<void> {
    const fileInput = this.page.locator(selector);
    await fileInput.setInputFiles(filePath);
    await this.page.waitForTimeout(500);
  }

  /**
   * Get pagination info
   */
  async getPaginationInfo(): Promise<{ current: number; pageSize: number; total: number }> {
    const pagination = this.page.locator('.ant-pagination');
    if (!(await pagination.isVisible())) {
      return { current: 1, pageSize: 10, total: 0 };
    }

    const totalText = await pagination.locator('.ant-pagination-total-text').textContent() || '';
    const totalMatch = totalText.match(/共\s*(\d+)/);
    const total = totalMatch ? parseInt(totalMatch[1]) : 0;

    const activeItem = pagination.locator('.ant-pagination-item-active');
    const current = parseInt(await activeItem.textContent() || '1');

    const pageSizeSelector = this.page.locator('.ant-pagination-options-size-changer');
    const pageSizeText = await pageSizeSelector.locator('.ant-select-selection-item').textContent() || '10';
    const pageSize = parseInt(pageSizeText);

    return { current, pageSize, total };
  }

  /**
   * Navigate to next page in pagination
   */
  async nextPage(): Promise<void> {
    await this.page.locator('.ant-pagination-next:not(.ant-pagination-disabled)').click();
    await this.waitForTableLoad();
  }

  /**
   * Navigate to previous page in pagination
   */
  async prevPage(): Promise<void> {
    await this.page.locator('.ant-pagination-prev:not(.ant-pagination-disabled)').click();
    await this.waitForTableLoad();
  }

  /**
   * Search in table by column
   */
  async searchInTable(columnIndex: number, searchText: string): Promise<void> {
    const searchIcon = this.page.locator('.ant-table-filter-trigger');
    if (await searchIcon.isVisible()) {
      await searchIcon.click();
      await this.page.waitForTimeout(300);

      const searchInput = this.page.locator('.ant-table-filter-dropdown input');
      await searchInput.fill(searchText);
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Confirm dialog (ant-confirm)
   */
  async confirmDialog(): Promise<void> {
    await this.page.locator('.ant-popconfirm:visible button:has-text("确定"), .ant-modal-confirm .ant-btn-primary').click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Cancel dialog (ant-confirm)
   */
  async cancelDialog(): Promise<void> {
    await this.page.locator('.ant-popconfirm:visible button:has-text("取消"), .ant-modal-confirm .ant-btn-default').click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Get text from table cell by row and column index
   */
  async getTableCellText(rowIndex: number, columnIndex: number): Promise<string> {
    const cell = this.antTableBody.locator('.ant-table-row').nth(rowIndex).locator('.ant-table-cell').nth(columnIndex);
    return await cell.textContent() || '';
  }

  /**
   * Wait for network idle
   */
  async waitForNetworkIdle(): Promise<void> {
    await this.page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {});
  }

  /**
   * Check if element is visible
   */
  async isElementVisible(selector: string): Promise<boolean> {
    return await this.page.locator(selector).isVisible().catch(() => false);
  }

  /**
   * Wait for element to be visible
   */
  async waitForElementVisible(selector: string, timeout: number = 5000): Promise<boolean> {
    try {
      await this.page.waitForSelector(selector, { state: 'visible', timeout });
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Hover over element
   */
  async hover(selector: string): Promise<void> {
    await this.page.locator(selector).hover();
    await this.page.waitForTimeout(200);
  }

  /**
   * Scroll to element
   */
  async scrollToElement(selector: string): Promise<void> {
    await this.page.locator(selector).scrollIntoViewIfNeeded();
    await this.page.waitForTimeout(200);
  }

  /**
   * Get badge count
   */
  async getBadgeCount(selector: string): Promise<number> {
    const badge = this.page.locator(selector).locator('.ant-badge-count, .ant-scroll-number');
    const text = await badge.textContent() || '0';
    return parseInt(text.replace(/\D/g, '')) || 0;
  }

  /**
   * Wait for tooltip to appear
   */
  async waitForTooltip(): Promise<void> {
    await this.page.waitForSelector('.ant-tooltip-open', { state: 'visible', timeout: 3000 }).catch(() => {});
  }
}
