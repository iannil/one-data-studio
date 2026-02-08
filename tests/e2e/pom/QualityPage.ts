/**
 * Data Quality Page Object Model
 *
 * Page: /data/quality
 * Features: Quality rules management, task execution, report generation
 */

import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class QualityPage extends BasePage {
  readonly PAGE_PATH = '/data/quality';

  // Tab locators
  readonly rulesTab: Locator;
  readonly tasksTab: Locator;
  readonly reportsTab: Locator;

  // Rules tab locators
  readonly createRuleButton: Locator;
  readonly rulesTable: Locator;
  readonly ruleNameInput: Locator;
  readonly datasetSelect: Locator;
  readonly ruleTypeSelect: Locator;
  readonly configTextarea: Locator;

  // Task tab locators
  readonly runTaskButton: Locator;
  readonly tasksTable: Locator;
  readonly taskStatusFilter: Locator;

  // Report tab locators
  readonly generateReportButton: Locator;
  readonly exportReportButton: Locator;
  readonly reportsTable: Locator;

  constructor(page: Page) {
    super(page);

    // Initialize tab locators
    this.rulesTab = page.locator('.ant-tabs-tab:has-text("规则"), .ant-tabs-tab:has-text("Rules")');
    this.tasksTab = page.locator('.ant-tabs-tab:has-text("任务"), .ant-tabs-tab:has-text("Tasks")');
    this.reportsTab = page.locator('.ant-tabs-tab:has-text("报告"), .ant-tabs-tab:has-text("Reports")');

    // Rules tab locators
    this.createRuleButton = page.locator('button:has-text("新建规则"), button:has-text("创建"), button:has(.anticon-plus)');
    this.rulesTable = page.locator('.ant-table');
    this.ruleNameInput = page.locator('.ant-modal input[name="name"], .ant-modal label:has-text("规则名称") + input');
    this.datasetSelect = page.locator('.ant-modal .ant-select:has-text("数据集"), .ant-modal label:has-text("数据集") + .ant-select');
    this.ruleTypeSelect = page.locator('.ant-modal .ant-select:has-text("规则类型"), .ant-modal label:has-text("规则类型") + .ant-select');
    this.configTextarea = page.locator('.ant-modal textarea, .ant-modal label:has-text("配置") + textarea');

    // Task tab locators
    this.runTaskButton = page.locator('button:has-text("执行"), button:has-text("运行"), button:has(.anticon-play-circle)');
    this.tasksTable = page.locator('.ant-table');
    this.taskStatusFilter = page.locator('.ant-select:has-text("状态")');

    // Report tab locators
    this.generateReportButton = page.locator('button:has-text("生成报告"), button:has-text("生成")');
    this.exportReportButton = page.locator('button:has-text("导出"), button:has-text("Export")');
    this.reportsTable = page.locator('.ant-table');
  }

  /**
   * Navigate to data quality page
   */
  async goto(): Promise<void> {
    await this.page.goto(this.PAGE_PATH);
    await this.waitForStable();
  }

  /**
   * Switch to rules tab
   */
  async switchToRules(): Promise<void> {
    if (await this.rulesTab.isVisible()) {
      await this.rulesTab.click();
      await this.page.waitForTimeout(300);
    }
  }

  /**
   * Switch to tasks tab
   */
  async switchToTasks(): Promise<void> {
    if (await this.tasksTab.isVisible()) {
      await this.tasksTab.click();
      await this.page.waitForTimeout(300);
    }
  }

  /**
   * Switch to reports tab
   */
  async switchToReports(): Promise<void> {
    if (await this.reportsTab.isVisible()) {
      await this.reportsTab.click();
      await this.page.waitForTimeout(300);
    }
  }

  /**
   * Click create rule button
   */
  async clickCreateRule(): Promise<void> {
    await this.switchToRules();
    await this.createRuleButton.first().click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Fill rule form
   */
  async fillRuleForm(data: {
    name: string;
    dataset: string;
    ruleType: string;
    config?: string;
  }): Promise<void> {
    // Name
    await this.ruleNameInput.fill(data.name);
    await this.page.waitForTimeout(200);

    // Dataset
    await this.datasetSelect.click();
    await this.page.waitForTimeout(200);
    await this.page.locator(`.ant-select-item:has-text("${data.dataset}")`).click();
    await this.page.waitForTimeout(200);

    // Rule Type
    await this.ruleTypeSelect.click();
    await this.page.waitForTimeout(200);
    await this.page.locator(`.ant-select-item:has-text("${data.ruleType}")`).click();
    await this.page.waitForTimeout(200);

    // Config (optional)
    if (data.config && await this.configTextarea.isVisible()) {
      await this.configTextarea.fill(data.config);
      await this.page.waitForTimeout(200);
    }
  }

  /**
   * Create a quality rule
   */
  async createRule(data: {
    name: string;
    dataset: string;
    ruleType: string;
    config?: string;
  }): Promise<boolean> {
    await this.clickCreateRule();
    await this.fillRuleForm(data);

    // Save
    await this.page.locator('.ant-modal button:has-text("确定"), .ant-modal button:has-text("保存"), .ant-modal .ant-btn-primary').click();
    await this.page.waitForTimeout(1000);

    return await this.verifyToastMessage('success');
  }

  /**
   * Run quality check for a rule
   */
  async runRuleCheck(ruleName: string): Promise<boolean> {
    await this.switchToRules();

    const row = this.rulesTable.locator('.ant-table-row').filter({ hasText: ruleName });
    await row.locator('button:has-text("执行"), button:has(.anticon-play-circle)').first().click();
    await this.page.waitForTimeout(2000);

    return await this.verifyToastMessage('success');
  }

  /**
   * Get rule count
   */
  async getRuleCount(): Promise<number> {
    await this.switchToRules();
    await this.waitForTableLoad();
    return await this.getTableRowCount();
  }

  /**
   * Check if rule exists
   */
  async ruleExists(name: string): Promise<boolean> {
    await this.switchToRules();
    const row = this.rulesTable.locator('.ant-table-row').filter({ hasText: name });
    return await row.count() > 0;
  }

  /**
   * Delete a rule
   */
  async deleteRule(name: string): Promise<boolean> {
    await this.switchToRules();

    const row = this.rulesTable.locator('.ant-table-row').filter({ hasText: name });
    await row.locator('button:has(.anticon-ellipsis), .ant-dropdown-trigger').first().click();
    await this.page.waitForTimeout(300);

    await this.page.locator('.ant-dropdown-menu-item:has-text("删除")').click();
    await this.confirmDialog();

    return await this.verifyToastMessage('success');
  }

  /**
   * Get task status
   */
  async getTaskStatus(taskName: string): Promise<string> {
    await this.switchToTasks();
    await this.waitForTableLoad();

    const row = this.tasksTable.locator('.ant-table-row').filter({ hasText: taskName });
    const statusCell = row.locator('.ant-table-cell').nth(2);

    return await statusCell.textContent() || '';
  }

  /**
   * Generate quality report
   */
  async generateReport(dataset?: string): Promise<boolean> {
    await this.switchToReports();

    if (await this.generateReportButton.isVisible()) {
      await this.generateReportButton.click();
      await this.page.waitForTimeout(500);

      // If dataset selection modal appears
      if (dataset) {
        const datasetSelect = this.page.locator('.ant-modal .ant-select');
        if (await datasetSelect.isVisible()) {
          await datasetSelect.click();
          await this.page.locator(`.ant-select-item:has-text("${dataset}")`).click();
        }
      }

      await this.page.locator('.ant-modal button:has-text("确定"), .ant-modal .ant-btn-primary').click();
      await this.page.waitForTimeout(2000);

      return await this.verifyToastMessage('success');
    }

    return false;
  }

  /**
   * Export quality report
   */
  async exportReport(format: 'pdf' | 'excel' = 'pdf'): Promise<boolean> {
    await this.switchToReports();

    if (await this.exportReportButton.isVisible()) {
      await this.exportReportButton.click();
      await this.page.waitForTimeout(300);

      const formatOption = this.page.locator(`.ant-dropdown-menu-item:has-text("${format}")`);
      if (await formatOption.isVisible()) {
        await formatOption.click();
        return true;
      }
    }

    return false;
  }

  /**
   * Get report count
   */
  async getReportCount(): Promise<number> {
    await this.switchToReports();
    await this.waitForTableLoad();
    return await this.getTableRowCount();
  }
}
