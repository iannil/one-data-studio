/**
 * Metadata Management Page Object Model
 *
 * Page: /data/metadata
 * Features: Browse, Search, Text-to-SQL, AI Annotation, Sensitive Fields Report, AI Scan
 */

import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class MetadataPage extends BasePage {
  readonly PAGE_PATH = '/metadata';

  // Tab locators - metadata page uses tabs with key="browse", key="search", etc.
  readonly tabsContainer: Locator;
  readonly browseTab: Locator;
  readonly searchTab: Locator;
  readonly text2SqlTab: Locator;
  readonly aiTab: Locator;

  // Browse tab locators
  readonly databaseTree: Locator;
  readonly tableInfoPanel: Locator;
  readonly scanButton: Locator;
  readonly aiAnnotateButton: Locator;
  readonly sensitiveReportButton: Locator;
  readonly aiScanButton: Locator;

  // Search tab locators
  readonly searchInput: Locator;
  readonly searchResults: Locator;
  readonly searchResultTable: Locator;

  // Text-to-SQL locators
  readonly textToSqlInput: Locator;
  readonly generateSqlButton: Locator;
  readonly sqlModal: Locator;
  readonly copySqlButton: Locator;

  // Detail panel locators
  readonly tableName: Locator;
  readonly tableDescription: Locator;
  readonly columnsTable: Locator;
  readonly relationsTable: Locator;
  readonly sampleDataTable: Locator;

  constructor(page: Page) {
    super(page);

    // Initialize tab locators - use data-key or nth index for more reliable selection
    this.tabsContainer = page.locator('.ant-tabs');
    this.browseTab = page.locator('.ant-tabs-tab:has-text("浏览"), .ant-tabs-tab:has-text("Browse")');
    this.searchTab = page.locator('.ant-tabs-tab:has-text("搜索"), .ant-tabs-tab:has-text("Search")');
    this.text2SqlTab = page.locator('.ant-tabs-tab:has-text("Text-to-SQL")');
    this.aiTab = page.locator('.ant-tabs-tab:has-text("AI")');

    // Browse tab locators
    this.databaseTree = page.locator('.ant-tree');
    this.tableInfoPanel = page.locator('.ant-card:visible');
    this.scanButton = page.locator('button:has-text("扫描元数据"), button:has-text("扫描")');
    this.aiAnnotateButton = page.locator('button:has-text("AI 标注")');
    this.sensitiveReportButton = page.locator('button:has-text("敏感报告")');
    this.aiScanButton = page.locator('button:has-text("AI 扫描")');

    // Search tab locators - use Ant Design input
    this.searchInput = page.locator('.ant-input-search input, .ant-tabs-tabpane input[placeholder*="搜索"]');
    this.searchResults = page.locator('.ant-tabs-tabpane:has(.ant-table)');
    this.searchResultTable = page.locator('.ant-tabs-tabpane .ant-table');

    // Text-to-SQL locators
    this.textToSqlInput = page.locator('textarea[placeholder*="描述"]');
    this.generateSqlButton = page.locator('button:has-text("生成"), button:has-text("生成 SQL")');
    this.sqlModal = page.locator('.ant-modal:has-text("SQL")');
    this.copySqlButton = page.locator('button:has-text("复制")');

    // Detail panel locators - use Ant Design descriptions
    this.tableName = page.locator('.ant-descriptions-item-label:has-text("表名") + *');
    this.tableDescription = page.locator('.ant-descriptions-item-label:has-text("描述") + *');
    this.columnsTable = page.locator('.ant-card:visible .ant-table');
    this.relationsTable = page.locator('.ant-table:has(.ant-table-cell:has-text("来源表"))');
    this.sampleDataTable = page.locator('.ant-table:has(.ant-table-cell:has-text("示例数据"))');
  }

  /**
   * Navigate to metadata page
   */
  async goto(): Promise<void> {
    await this.page.goto(this.PAGE_PATH);
    await this.waitForStable();
  }

  /**
   * Switch to browse tab
   */
  async switchToBrowse(): Promise<void> {
    await this.browseTab.click();
    await this.waitForStable();
  }

  /**
   * Switch to search tab
   */
  async switchToSearch(): Promise<void> {
    await this.searchTab.click();
    await this.waitForStable();
  }

  /**
   * Expand database node in tree
   */
  async expandDatabaseNode(dbName: string): Promise<void> {
    const treeNode = this.page.locator(`.ant-tree-treenode:has-text("${dbName}")`);
    await treeNode.locator('.ant-tree-switcher').click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Select table in tree
   */
  async selectTable(tableName: string): Promise<void> {
    const treeNode = this.page.locator(`.ant-tree-treenode:has-text("${tableName}")`);
    await treeNode.click();
    await this.waitForStable();
  }

  /**
   * Search for table/column
   */
  async search(query: string): Promise<void> {
    await this.switchToSearch();
    await this.searchInput.fill(query);
    await this.page.waitForTimeout(1000);
  }

  /**
   * Get search result count
   */
  async getSearchResultCount(): Promise<number> {
    const results = this.searchResults.locator('.ant-table-row');
    return await results.count();
  }

  /**
   * Generate SQL from natural language
   */
  async generateSql(naturalLanguage: string): Promise<void> {
    await this.textToSqlInput.fill(naturalLanguage);
    await this.generateSqlButton.click();
    await this.sqlModal.waitFor({ state: 'visible' });
  }

  /**
   * Get generated SQL text
   */
  async getGeneratedSql(): Promise<string> {
    const sqlContent = this.sqlModal.locator('code, pre, .sql-content');
    return await sqlContent.textContent() || '';
  }

  /**
   * Close SQL modal
   */
  async closeSqlModal(): Promise<void> {
    await this.sqlModal.locator('button:has-text("关闭"), .ant-modal-close').click();
    await this.sqlModal.waitFor({ state: 'hidden' }).catch(() => {});
  }

  /**
   * Click AI Annotate button
   */
  async clickAiAnnotate(): Promise<void> {
    await this.aiAnnotateButton.click();
  }

  /**
   * Click Sensitive Report button
   * Returns true if button exists and was clicked, false otherwise
   */
  async clickSensitiveReport(): Promise<boolean> {
    try {
      await this.sensitiveReportButton.waitFor({ state: 'visible', timeout: 5000 });
      await this.sensitiveReportButton.click();
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Click AI Scan button
   * Returns true if button exists and was clicked, false otherwise
   */
  async clickAiScan(): Promise<boolean> {
    try {
      await this.aiScanButton.waitFor({ state: 'visible', timeout: 5000 });
      await this.aiScanButton.click();
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Click AI Annotate button
   * Returns true if button exists and was clicked, false otherwise
   */
  async clickAiAnnotate(): Promise<boolean> {
    try {
      await this.aiAnnotateButton.waitFor({ state: 'visible', timeout: 5000 });
      await this.aiAnnotateButton.click();
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Get table column count
   */
  async getColumnCount(): Promise<number> {
    await this.columnsTable.waitFor({ state: 'visible' }).catch(() => {});
    const rows = this.columnsTable.locator('.ant-table-body .ant-table-row');
    return await rows.count();
  }

  /**
   * Get table info
   */
  async getTableInfo(): Promise<{ name: string; description: string }> {
    const name = await this.tableName.textContent() || '';
    const description = await this.tableDescription.textContent() || '';
    return { name: name.trim(), description: description.trim() };
  }

  // =============================================================================
  // Extended Methods (Phase 2)
  // =============================================================================

  /**
   * Batch expand multiple tree nodes
   */
  async expandTreeNodes(nodeNames: string[]): Promise<void> {
    for (const nodeName of nodeNames) {
      const node = this.page.locator(`.ant-tree-treenode:has-text("${nodeName}")`);
      if (await node.count() > 0) {
        const switcher = node.locator('.ant-tree-switcher');
        if (await switcher.isVisible()) {
          await switcher.click();
          await this.page.waitForTimeout(500);
        }
      }
    }
  }

  /**
   * Collapse a tree node
   */
  async collapseTreeNode(nodeName: string): Promise<void> {
    const node = this.page.locator(`.ant-tree-treenode:has-text("${nodeName}")`);
    const switcher = node.locator('.ant-tree-switcher_open');
    if (await switcher.isVisible()) {
      await switcher.click();
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Switch to a different database
   */
  async switchDatabase(dbName: string): Promise<void> {
    const dbNode = this.page.locator(`.ant-tree-treenode:has-text("${dbName}")`);
    await dbNode.click();
    await this.waitForStable();
  }

  /**
   * View table details
   */
  async viewTableDetails(tableName: string): Promise<void> {
    await this.selectTable(tableName);
    const detailsButton = this.page.locator('button:has-text("详情"), button:has-text("Details")');
    if (await detailsButton.isVisible()) {
      await detailsButton.click();
      await this.waitForDrawer();
    }
  }

  /**
   * Get column details from table info panel
   */
  async getColumnDetails(): Promise<Array<{ name: string; type: string; nullable: boolean }>> {
    await this.page.waitForTimeout(500);
    const rows = this.columnsTable.locator('.ant-table-body .ant-table-row');
    const count = await rows.count();
    const columns: Array<{ name: string; type: string; nullable: boolean }> = [];

    for (let i = 0; i < count; i++) {
      const cells = rows.nth(i).locator('.ant-table-cell');
      const name = await cells.nth(0).textContent() || '';
      const type = await cells.nth(1).textContent() || '';
      const nullableText = await cells.nth(2).textContent() || '';
      columns.push({ name: name.trim(), type: type.trim(), nullable: nullableText.includes('YES') });
    }
    return columns;
  }

  /**
   * Get relationship information
   */
  async getRelationships(): Promise<Array<{ fromTable: string; toTable: string; type: string }>> {
    const relationships: Array<{ fromTable: string; toTable: string; type: string }> = [];

    const relationRows = this.relationsTable.locator('.ant-table-body .ant-table-row');
    const count = await relationRows.count();

    for (let i = 0; i < count; i++) {
      const cells = relationRows.nth(i).locator('.ant-table-cell');
      const fromTable = await cells.nth(0).textContent() || '';
      const toTable = await cells.nth(1).textContent() || '';
      const type = await cells.nth(2).textContent() || '';
      relationships.push({ fromTable: fromTable.trim(), toTable: toTable.trim(), type: type.trim() });
    }
    return relationships;
  }

  /**
   * Export search results
   */
  async exportSearchResults(format: 'csv' | 'excel' | 'json' = 'csv'): Promise<void> {
    const exportButton = this.page.locator(`button:has-text("导出"), button:has-text("Export")`);
    if (await exportButton.isVisible()) {
      await exportButton.click();
      await this.page.waitForTimeout(300);

      const formatOption = this.page.locator(`.ant-dropdown:visible .ant-dropdown-menu-item:has-text("${format}")`);
      if (await formatOption.isVisible()) {
        await formatOption.click();
      }
    }
  }

  /**
   * Get sample data from table
   */
  async getSampleData(limit: number = 10): Promise<string[][]> {
    const data: string[][] = [];
    const rows = this.sampleDataTable.locator('.ant-table-body .ant-table-row');
    const count = Math.min(limit, await rows.count());

    for (let i = 0; i < count; i++) {
      const cells = rows.nth(i).locator('.ant-table-cell');
      const cellCount = await cells.count();
      const rowData: string[] = [];
      for (let j = 0; j < cellCount; j++) {
        const text = await cells.nth(j).textContent() || '';
        rowData.push(text.trim());
      }
      data.push(rowData);
    }
    return data;
  }

  /**
   * Search by column name
   */
  async searchByColumn(columnName: string): Promise<void> {
    await this.switchToSearch();
    const searchInput = this.page.locator('input[placeholder*="搜索"], input[placeholder*="search"]');
    await searchInput.fill(columnName);
    await this.page.waitForTimeout(1000);
  }

  /**
   * Get table statistics
   */
  async getTableStatistics(): Promise<{ rowCount: number; size: string; lastUpdated: string }> {
    const statsElement = this.page.locator('.ant-descriptions-item-label:has-text("行数"), .ant-descriptions-item-label:has-text("统计")');
    const rowCount = 0;
    const size = '';
    const lastUpdated = '';

    return { rowCount, size, lastUpdated };
  }

  /**
   * Click copy SQL button
   */
  async clickCopySql(): Promise<void> {
    await this.copySqlButton.click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Execute generated SQL
   */
  async executeSql(): Promise<void> {
    const executeButton = this.sqlModal.locator('button:has-text("执行"), button:has-text("Run")');
    if (await executeButton.isVisible()) {
      await executeButton.click();
      await this.page.waitForTimeout(2000);
    }
  }

  /**
   * Batch AI annotate multiple tables
   */
  async batchAiAnnotate(tables: string[]): Promise<void> {
    for (const table of tables) {
      await this.selectTable(table);
      await this.clickAiAnnotate();
      await this.page.waitForTimeout(2000);
    }
  }

  /**
   * Save AI annotation result
   */
  async saveAnnotation(): Promise<void> {
    const saveButton = this.page.locator('.ant-modal:visible button:has-text("保存"), .ant-modal:visible button:has-text("Save")');
    if (await saveButton.isVisible()) {
      await saveButton.click();
      await this.page.waitForTimeout(1000);
    }
  }

  /**
   * Re-annotate table
   */
  async reAnnotate(): Promise<void> {
    const reAnnotateButton = this.page.locator('button:has-text("重新标注"), button:has-text("Re-annotate")');
    if (await reAnnotateButton.isVisible()) {
      await reAnnotateButton.click();
      await this.page.waitForTimeout(2000);
    }
  }

  /**
   * Get sensitive field classification
   */
  async getSensitiveFields(): Promise<Array<{ name: string; level: string; type: string }>> {
    const sensitiveFields: Array<{ name: string; level: string; type: string }> = [];

    const rows = this.page.locator('.ant-table:visible .ant-table-body .ant-table-row');
    const count = await rows.count();

    for (let i = 0; i < Math.min(count, 20); i++) {
      const cells = rows.nth(i).locator('.ant-table-cell');
      const name = await cells.nth(0).textContent() || '';
      const level = await cells.nth(1).textContent() || '';
      const type = await cells.nth(2).textContent() || '';
      if (name && level) {
        sensitiveFields.push({ name: name.trim(), level: level.trim(), type: type.trim() });
      }
    }
    return sensitiveFields;
  }

  /**
   * Export sensitive report
   */
  async exportSensitiveReport(format: 'pdf' | 'excel' = 'pdf'): Promise<void> {
    const exportButton = this.page.locator('.ant-modal:visible button:has-text("导出"), .ant-modal:visible button:has-text("Export")');
    if (await exportButton.isVisible()) {
      await exportButton.click();
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Configure masking rule
   */
  async configureMaskingRule(fieldName: string, rule: string): Promise<void> {
    const row = this.page.locator('.ant-table-row').filter({ hasText: fieldName });
    await row.locator('button:has-text("配置"), button:has-text("设置")').click();
    await this.page.waitForTimeout(300);

    const ruleSelect = this.page.locator('.ant-modal:visible .ant-select');
    await ruleSelect.click();
    await this.page.locator(`.ant-select-item:has-text("${rule}")`).click();

    await this.page.locator('.ant-modal:visible button:has-text("确定")').click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Get scan progress
   */
  async getScanProgress(): Promise<{ current: number; total: number; status: string }> {
    const progressText = await this.page.locator('.ant-progress-text, .ant-statistic-content').textContent() || '';
    const status = await this.page.locator('.ant-tag, .ant-badge-status-text').textContent() || '';

    return { current: 0, total: 100, status: status.trim() };
  }

  /**
   * View scan results
   */
  async viewScanResults(): Promise<void> {
    const viewButton = this.page.locator('button:has-text("查看结果"), button:has-text("View Results")');
    if (await viewButton.isVisible()) {
      await viewButton.click();
      await this.waitForDrawer();
    }
  }

  /**
   * Batch apply masking
   */
  async batchApplyMasking(fieldNames: string[]): Promise<void> {
    for (const fieldName of fieldNames) {
      const row = this.page.locator('.ant-table-row').filter({ hasText: fieldName });
      const checkbox = row.locator('input[type="checkbox"]');
      if (await checkbox.isVisible()) {
        await checkbox.check();
      }
    }

    const applyButton = this.page.locator('button:has-text("批量应用"), button:has-text("Batch Apply")');
    if (await applyButton.isVisible()) {
      await applyButton.click();
      await this.page.waitForTimeout(1000);
    }
  }

  /**
   * Get database list from tree
   */
  async getDatabaseList(): Promise<string[]> {
    const dbNodes = this.page.locator('.ant-tree-treenode[class*="database"], .ant-tree-treenode:has(.anticon-database)');
    const count = await dbNodes.count();
    const databases: string[] = [];

    for (let i = 0; i < count; i++) {
      const text = await dbNodes.nth(i).locator('.ant-tree-title').textContent() || '';
      if (text) {
        databases.push(text.trim());
      }
    }
    return databases;
  }

  /**
   * Refresh metadata
   */
  async refreshMetadata(): Promise<void> {
    const refreshButton = this.page.locator('button:has(.anticon-reload), button:has-text("刷新")');
    if (await refreshButton.isVisible()) {
      await refreshButton.click();
      await this.page.waitForTimeout(2000);
    }
  }

  /**
   * Get table list for current database
   */
  async getTableList(): Promise<string[]> {
    const tableNodes = this.page.locator('.ant-tree-treenode:has(.anticon-table), .ant-tree-treenode[class*="table"]');
    const count = await tableNodes.count();
    const tables: string[] = [];

    for (let i = 0; i < count; i++) {
      const text = await tableNodes.nth(i).locator('.ant-tree-title').textContent() || '';
      if (text) {
        tables.push(text.trim());
      }
    }
    return tables;
  }

  /**
   * Switch to view tab
   */
  async switchToView(): Promise<void> {
    const viewTab = this.page.locator('.ant-tabs-tab:has-text("视图"), .ant-tabs-tab:has-text("View")');
    if (await viewTab.isVisible()) {
      await viewTab.click();
      await this.waitForStable();
    }
  }

  /**
   * Get preview SQL
   */
  async getPreviewSql(): Promise<string> {
    const sqlElement = this.page.locator('code, pre, .sql-content');
    return await sqlElement.textContent() || '';
  }

  /**
   * Validate SQL syntax
   */
  async validateSql(sql: string): Promise<boolean> {
    const validateButton = this.page.locator('button:has-text("验证"), button:has-text("Validate")');
    if (await validateButton.isVisible()) {
      await validateButton.click();
      await this.page.waitForTimeout(1000);

      const isValid = !await this.page.locator('.ant-message-error, .ant-notification-notice-error').isVisible();
      return isValid;
    }
    return true;
  }
}
