/**
 * Data Standards Page Object Model
 *
 * Page: /data/standards
 * Features: Data Elements, Word Libraries, Standard Documents, Standard Mappings
 */

import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class StandardsPage extends BasePage {
  readonly PAGE_PATH = '/data/standards';

  // Tab locators
  readonly elementsTab: Locator;
  readonly librariesTab: Locator;
  readonly documentsTab: Locator;
  readonly mappingsTab: Locator;

  // Elements tab locators
  readonly createElementButton: Locator;
  readonly elementTable: Locator;
  readonly elementDrawer: Locator;
  readonly elementsTabPane: Locator;

  // Element form locators
  readonly elementNameInput: Locator;
  readonly elementCodeInput: Locator;
  readonly elementDataTypeSelect: Locator;
  readonly elementLengthInput: Locator;
  readonly elementPrecisionInput: Locator;
  readonly elementScaleInput: Locator;
  readonly elementStandardValueInput: Locator;
  readonly elementDescriptionInput: Locator;
  readonly elementLibrarySelect: Locator;
  readonly elementTagsSelect: Locator;

  // Libraries tab locators
  readonly librariesTabPane: Locator;
  readonly createLibraryButton: Locator;
  readonly libraryTable: Locator;

  // Library form locators
  readonly libraryNameInput: Locator;
  readonly libraryCategoryInput: Locator;
  readonly libraryDescriptionInput: Locator;

  constructor(page: Page) {
    super(page);

    // Initialize tab locators
    this.elementsTab = page.locator('.ant-tabs-tab:has-text("数据元")');
    this.librariesTab = page.locator('.ant-tabs-tab:has-text("词根库")');
    this.documentsTab = page.locator('.ant-tabs-tab:has-text("标准文档")');
    this.mappingsTab = page.locator('.ant-tabs-tab:has-text("标准映射")');

    // Elements tab locators
    this.elementsTabPane = page.locator('.ant-tabs-tabpane').nth(0);
    this.createElementButton = page.locator('.ant-tabs-tabpane').nth(0).locator('button:has-text("新建数据元")');
    this.elementTable = page.locator('.ant-tabs-tabpane').nth(0).locator('.ant-table');
    this.elementDrawer = page.locator('.ant-drawer:has-text("数据元详情"), [data-testid="element-drawer"]');
    this.libraryButton = page.locator('button:has-text("词根库")');

    // Element form locators
    this.elementNameInput = page.locator('.ant-modal:visible input[name="name"]');
    this.elementCodeInput = page.locator('.ant-modal:visible input[name="code"]');
    this.elementDataTypeSelect = page.locator('.ant-modal:visible select[name="data_type"]');
    this.elementLengthInput = page.locator('.ant-modal:visible input[name="length"]');
    this.elementPrecisionInput = page.locator('.ant-modal:visible input[name="precision"]');
    this.elementScaleInput = page.locator('.ant-modal:visible input[name="scale"]');
    this.elementStandardValueInput = page.locator('.ant-modal:visible input[name="standard_value"]');
    this.elementDescriptionInput = page.locator('.ant-modal:visible textarea[name="description"]');
    this.elementLibrarySelect = page.locator('.ant-modal:visible select[name="library_id"]');
    this.elementTagsSelect = page.locator('.ant-modal:visible select[name="tags"]');

    // Libraries tab locators
    this.librariesTabPane = page.locator('.ant-tabs-tabpane').nth(1);
    this.createLibraryButton = page.locator('.ant-tabs-tabpane').nth(1).locator('button:has-text("新建词根库")');
    this.libraryTable = page.locator('.ant-tabs-tabpane').nth(1).locator('.ant-table');

    // Library form locators
    this.libraryNameInput = page.locator('.ant-modal:visible input[name="name"]');
    this.libraryCategoryInput = page.locator('.ant-modal:visible input[name="category"]');
    this.libraryDescriptionInput = page.locator('.ant-modal:visible textarea[name="description"]');
  }

  /**
   * Navigate to standards page
   */
  async goto(): Promise<void> {
    await this.page.goto(this.PAGE_PATH);
    await this.waitForStable();
  }

  /**
   * Switch to elements tab
   */
  async switchToElements(): Promise<void> {
    if (await this.elementsTab.isVisible()) {
      await this.elementsTab.click();
      await this.waitForStable();
    }
  }

  /**
   * Switch to libraries tab
   */
  async switchToLibraries(): Promise<void> {
    if (await this.librariesTab.isVisible()) {
      await this.librariesTab.click();
      await this.waitForStable();
    }
  }

  /**
   * Switch to documents tab
   */
  async switchToDocuments(): Promise<void> {
    if (await this.documentsTab.isVisible()) {
      await this.documentsTab.click();
      await this.waitForStable();
    }
  }

  /**
   * Switch to mappings tab
   */
  async switchToMappings(): Promise<void> {
    if (await this.mappingsTab.isVisible()) {
      await this.mappingsTab.click();
      await this.waitForStable();
    }
  }

  /**
   * Get element count
   */
  async getElementCount(): Promise<number> {
    await this.waitForLoading();
    const rows = this.elementTable.locator('.ant-table-body .ant-table-row');
    return await rows.count();
  }

  /**
   * Click create element button
   */
  async clickCreateElement(): Promise<void> {
    await this.createElementButton.click();
    await this.waitForModal();
  }

  /**
   * Fill element form
   */
  async fillElementForm(data: {
    name: string;
    code: string;
    dataType: string;
    length?: number;
    precision?: number;
    scale?: number;
    standardValue?: string;
    description?: string;
  }): Promise<void> {
    await this.elementNameInput.fill(data.name);
    await this.elementCodeInput.fill(data.code);

    await this.elementDataTypeSelect.click();
    await this.page.locator(`.ant-select-item:has-text("${data.dataType}")`).click();

    if (data.length) {
      await this.elementLengthInput.fill(String(data.length));
    }

    if (data.precision) {
      await this.elementPrecisionInput.fill(String(data.precision));
    }

    if (data.scale) {
      await this.elementScaleInput.fill(String(data.scale));
    }

    if (data.standardValue) {
      await this.elementStandardValueInput.fill(data.standardValue);
    }

    if (data.description) {
      await this.elementDescriptionInput.fill(data.description);
    }
  }

  /**
   * Submit element form
   */
  async submitElementForm(): Promise<void> {
    await this.page.locator('.ant-modal:visible button:has-text("确定"), .ant-modal:visible button[type="submit"]').click();
  }

  /**
   * View element details by name
   */
  async viewElementDetails(elementName: string): Promise<void> {
    const row = this.findTableRowByText(elementName);
    await row.locator('a').click();
    await this.elementDrawer.waitFor({ state: 'visible' });
  }

  /**
   * Close element drawer
   */
  async closeElementDrawer(): Promise<void> {
    await this.elementDrawer.locator('.ant-drawer-close').click();
    await this.elementDrawer.waitFor({ state: 'hidden' }).catch(() => {});
  }

  /**
   * Click create library button
   */
  async clickCreateLibrary(): Promise<void> {
    await this.createLibraryButton.click();
    await this.waitForModal();
  }

  /**
   * Fill library form
   */
  async fillLibraryForm(data: {
    name: string;
    category?: string;
    description?: string;
  }): Promise<void> {
    await this.libraryNameInput.fill(data.name);

    if (data.category) {
      await this.libraryCategoryInput.fill(data.category);
    }

    if (data.description) {
      await this.libraryDescriptionInput.fill(data.description);
    }
  }

  /**
   * Submit library form
   */
  async submitLibraryForm(): Promise<void> {
    await this.page.locator('.ant-modal:visible button:has-text("确定"), .ant-modal:visible button[type="submit"]').click();
  }

  /**
   * Get library count
   */
  async getLibraryCount(): Promise<number> {
    const rows = this.libraryTable.locator('.ant-table-body .ant-table-row');
    return await rows.count();
  }

  /**
   * Delete element by name
   */
  async deleteElement(elementName: string): Promise<void> {
    const row = this.findTableRowByText(elementName);
    await row.locator('button:has(.anticon-delete), button[danger]').click();
    await this.page.locator('.ant-popconfirm:visible button:has-text("确定")').click();
  }

  // =============================================================================
  // Extended Methods (Phase 5)
  // =============================================================================

  /**
   * Search elements by keyword
   */
  async searchElements(keyword: string): Promise<void> {
    await this.switchToElements();
    const searchInput = this.elementsTabPane.locator('input[placeholder*="搜索"], input[data-testid="search"]');
    if (await searchInput.isVisible()) {
      await searchInput.fill(keyword);
      await this.page.waitForTimeout(1000);
    }
  }

  /**
   * Filter elements by criteria
   */
  async filterElements(filter: {
    dataType?: string;
    libraryId?: string;
    hasCode?: boolean;
  }): Promise<void> {
    await this.switchToElements();
    const filterButton = this.elementsTabPane.locator('button:has(.anticon-filter), button:has-text("筛选")');
    if (await filterButton.isVisible()) {
      await filterButton.click();
      await this.page.waitForTimeout(300);

      if (filter.dataType) {
        await this.page.locator('.ant-dropdown:visible select[name="dataType"]').selectOption(filter.dataType);
      }
      if (filter.libraryId) {
        await this.page.locator('.ant-dropdown:visible select[name="libraryId"]').selectOption(filter.libraryId);
      }

      await this.page.locator('.ant-dropdown:visible button:has-text("确定")').click();
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * View element mappings
   */
  async viewElementMappings(elementName: string): Promise<void> {
    await this.switchToElements();
    const row = this.findTableRowByText(elementName);
    await row.locator('button:has-text("映射"), button:has(.anticon-swap)').click();
    await this.waitForDrawer();
  }

  /**
   * Import elements from file
   */
  async importElements(filePath: string): Promise<void> {
    await this.switchToElements();
    const importButton = this.elementsTabPane.locator('button:has-text("导入"), button:has(.anticon-import)');
    if (await importButton.isVisible()) {
      await importButton.click();
      await this.waitForModal();

      const fileInput = this.page.locator('.ant-modal:visible input[type="file"]');
      await fileInput.setInputFiles(filePath);

      await this.page.locator('.ant-modal:visible button:has-text("确定")').click();
      await this.page.waitForTimeout(2000);
    }
  }

  /**
   * Export elements
   */
  async exportElements(format: 'csv' | 'excel' | 'json' = 'excel'): Promise<void> {
    await this.switchToElements();
    const exportButton = this.elementsTabPane.locator('button:has-text("导出"), button:has(.anticon-export)');
    if (await exportButton.isVisible()) {
      await exportButton.click();
      await this.page.waitForTimeout(300);
      await this.page.locator(`.ant-dropdown-item:has-text("${format}")`).click();
    }
  }

  /**
   * Add word root to library
   */
  async addWordRoot(libraryId: string, word: string, meaning?: string): Promise<void> {
    await this.switchToLibraries();
    const row = this.findTableRowByText(libraryId);
    await row.locator('button:has-text("管理词根"), button:has(.anticon-plus)').click();
    await this.waitForModal();

    await this.page.locator('.ant-modal:visible input[name="word"]').fill(word);
    if (meaning) {
      await this.page.locator('.ant-modal:visible textarea[name="meaning"]').fill(meaning);
    }

    await this.page.locator('.ant-modal:visible button:has-text("添加")').click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Search word roots
   */
  async searchWordRoots(keyword: string): Promise<void> {
    await this.switchToLibraries();
    const searchInput = this.librariesTabPane.locator('input[placeholder*="搜索词根"]');
    if (await searchInput.isVisible()) {
      await searchInput.fill(keyword);
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Get word root recommendation
   */
  async getWordRootRecommendation(fieldName: string): Promise<string[]> {
    const recommendButton = this.page.locator('button:has-text("词根推荐"), button:has-text("推荐")');
    if (await recommendButton.isVisible()) {
      await recommendButton.click();
      await this.page.waitForTimeout(500);

      const recommendations = this.page.locator('.recommendation-item');
      const count = await recommendations.count();
      const result: string[] = [];

      for (let i = 0; i < count; i++) {
        const text = await recommendations.nth(i).textContent() || '';
        result.push(text.trim());
      }
      return result;
    }
    return [];
  }

  /**
   * Upload standard document
   */
  async uploadDocument(file: { path: string; name: string }, category?: string): Promise<void> {
    await this.switchToDocuments();
    const uploadButton = this.page.locator('button:has-text("上传文档")');
    if (await uploadButton.isVisible()) {
      await uploadButton.click();
      await this.waitForModal();

      const fileInput = this.page.locator('.ant-modal:visible input[type="file"]');
      await fileInput.setInputFiles(file.path);

      if (category) {
        await this.page.locator('.ant-modal:visible select[name="category"]').selectOption(category);
      }

      await this.page.locator('.ant-modal:visible button:has-text("上传")').click();
      await this.page.waitForTimeout(2000);
    }
  }

  /**
   * Preview document
   */
  async previewDocument(docName: string): Promise<void> {
    await this.switchToDocuments();
    const row = this.findTableRowByText(docName);
    await row.locator('button:has(.anticon-eye), button:has-text("预览")').click();
    await this.waitForModal();
  }

  /**
   * Download document
   */
  async downloadDocument(docName: string): Promise<void> {
    await this.switchToDocuments();
    const row = this.findTableRowByText(docName);
    await row.locator('button:has(.anticon-download)').click();
    await this.page.waitForTimeout(2000);
  }

  /**
   * Manage document categories
   */
  async manageDocumentCategories(): Promise<void> {
    await this.switchToDocuments();
    const categoryButton = this.page.locator('button:has-text("分类管理"), button:has-text("管理分类")');
    if (await categoryButton.isVisible()) {
      await categoryButton.click();
      await this.waitForDrawer();
    }
  }

  /**
   * Create standard mapping
   */
  async createMapping(fieldId: string, elementId: string): Promise<void> {
    await this.switchToMappings();
    await this.page.locator('button:has-text("新建映射")').click();
    await this.waitForModal();

    await this.page.locator('.ant-modal:visible input[name="fieldId"]').fill(fieldId);
    await this.page.locator('.ant-modal:visible select[name="elementId"]').selectOption(elementId);

    await this.page.locator('.ant-modal:visible button:has-text("确定")').click();
    await this.waitForModalClose();
  }

  /**
   * Batch create mappings
   */
  async batchCreateMapping(mappings: Array<{ fieldId: string; elementId: string }>): Promise<void> {
    await this.switchToMappings();
    const batchButton = this.page.locator('button:has-text("批量映射")');
    if (await batchButton.isVisible()) {
      await batchButton.click();
      await this.waitForModal();

      const mappingInput = this.page.locator('.ant-modal:visible textarea[name="mappings"]');
      await mappingInput.fill(JSON.stringify(mappings));

      await this.page.locator('.ant-modal:visible button:has-text("确定")').click();
      await this.page.waitForTimeout(2000);
    }
  }

  /**
   * Check mapping conflicts
   */
  async checkMappingConflicts(mappings: Array<{ fieldId: string; elementId: string }>): Promise<Array<{
    fieldId: string;
    conflictType: string;
    suggestion: string;
  }>> {
    await this.switchToMappings();
    const checkButton = this.page.locator('button:has-text("检查冲突")');
    if (await checkButton.isVisible()) {
      await checkButton.click();
      await this.page.waitForTimeout(1000);

      const conflicts: Array<{ fieldId: string; conflictType: string; suggestion: string }> = [];
      const conflictRows = this.page.locator('.conflict-list .conflict-item');
      const count = await conflictRows.count();

      for (let i = 0; i < count; i++) {
        const fieldId = await conflictRows.nth(i).locator('.field-id').textContent() || '';
        const conflictType = await conflictRows.nth(i).locator('.conflict-type').textContent() || '';
        const suggestion = await conflictRows.nth(i).locator('.suggestion').textContent() || '';
        conflicts.push({ fieldId: fieldId.trim(), conflictType: conflictType.trim(), suggestion: suggestion.trim() });
      }
      return conflicts;
    }
    return [];
  }

  /**
   * Export mapping rules
   */
  async exportMappingRules(): Promise<void> {
    await this.switchToMappings();
    const exportButton = this.page.locator('button:has-text("导出规则")');
    if (await exportButton.isVisible()) {
      await exportButton.click();
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Edit data element
   */
  async editElement(elementName: string, data: {
    name?: string;
    code?: string;
    description?: string;
  }): Promise<void> {
    await this.switchToElements();
    const row = this.findTableRowByText(elementName);
    await row.locator('button:has(.anticon-edit)').click();
    await this.waitForModal();

    if (data.name) {
      await this.page.locator('.ant-modal:visible input[name="name"]').fill(data.name);
    }
    if (data.code) {
      await this.page.locator('.ant-modal:visible input[name="code"]').fill(data.code);
    }
    if (data.description) {
      await this.page.locator('.ant-modal:visible textarea[name="description"]').fill(data.description);
    }

    await this.page.locator('.ant-modal:visible button:has-text("确定")').click();
    await this.waitForModalClose();
  }

  /**
   * View library details
   */
  async viewLibraryDetails(libraryName: string): Promise<any> {
    await this.switchToLibraries();
    const row = this.findTableRowByText(libraryName);
    await row.locator('a, button:has-text("详情")').click();
    await this.waitForDrawer();

    const name = await this.page.locator('.ant-drawer-body .library-name').textContent() || '';
    const category = await this.page.locator('.ant-drawer-body .library-category').textContent() || '';
    const wordCount = await this.page.locator('.ant-drawer-body .word-count').textContent() || '0';
    return { name: name.trim(), category: category.trim(), wordCount: parseInt(wordCount) || 0 };
  }

  /**
   * Edit library
   */
  async editLibrary(libraryId: string, data: {
    name?: string;
    category?: string;
    description?: string;
  }): Promise<void> {
    await this.switchToLibraries();
    const row = this.findTableRowByText(libraryId);
    await row.locator('button:has(.anticon-edit)').click();
    await this.waitForModal();

    if (data.name) {
      await this.page.locator('.ant-modal:visible input[name="name"]').fill(data.name);
    }
    if (data.category) {
      await this.page.locator('.ant-modal:visible input[name="category"]').fill(data.category);
    }
    if (data.description) {
      await this.page.locator('.ant-modal:visible textarea[name="description"]').fill(data.description);
    }

    await this.page.locator('.ant-modal:visible button:has-text("确定")').click();
    await this.waitForModalClose();
  }

  /**
   * Delete library
   */
  async deleteLibrary(libraryId: string): Promise<void> {
    await this.switchToLibraries();
    const row = this.findTableRowByText(libraryId);
    await row.locator('button:has(.anticon-delete)').click();
    await this.page.waitForTimeout(300);
    await this.confirmDialog();
  }

  /**
   * Get library word list
   */
  async getLibraryWordList(libraryName: string): Promise<string[]> {
    await this.switchToLibraries();
    const row = this.findTableRowByText(libraryName);
    await row.locator('button:has-text("词根"), button:has(.anticon-book)').click();
    await this.waitForDrawer();

    const wordRows = this.page.locator('.ant-drawer-body .ant-table-row');
    const count = await wordRows.count();
    const words: string[] = [];

    for (let i = 0; i < count; i++) {
      const word = await wordRows.nth(i).locator('.ant-table-cell').nth(0).textContent() || '';
      if (word) words.push(word.trim());
    }
    return words;
  }

  /**
   * Delete document
   */
  async deleteDocument(docName: string): Promise<void> {
    await this.switchToDocuments();
    const row = this.findTableRowByText(docName);
    await row.locator('button:has(.anticon-delete)').click();
    await this.page.waitForTimeout(300);
    await this.confirmDialog();
  }

  /**
   * Edit mapping
   */
  async editMapping(fieldId: string, newElementId: string): Promise<void> {
    await this.switchToMappings();
    const row = this.findTableRowByText(fieldId);
    await row.locator('button:has(.anticon-edit)').click();
    await this.waitForModal();

    await this.page.locator('.ant-modal:visible select[name="elementId"]').selectOption(newElementId);
    await this.page.locator('.ant-modal:visible button:has-text("确定")').click();
    await this.waitForModalClose();
  }

  /**
   * Delete mapping
   */
  async deleteMapping(fieldId: string): Promise<void> {
    await this.switchToMappings();
    const row = this.findTableRowByText(fieldId);
    await row.locator('button:has(.anticon-delete)').click();
    await this.page.waitForTimeout(300);
    await this.confirmDialog();
  }

  /**
   * Get mapping statistics
   */
  async getMappingStatistics(): Promise<{
    totalMappings: number;
    coverage: number;
    lastUpdated: string;
  }> {
    await this.switchToMappings();
    const statsElement = this.page.locator('.mapping-stats, .statistics-panel');
    if (await statsElement.isVisible()) {
      const totalText = await statsElement.locator('.total-mappings').textContent() || '0';
      const coverageText = await statsElement.locator('.coverage').textContent() || '0%';
      const lastUpdated = await statsElement.locator('.last-updated').textContent() || '';
      return {
        totalMappings: parseInt(totalText) || 0,
        coverage: parseFloat(coverageText.replace('%', '')) || 0,
        lastUpdated: lastUpdated.trim()
      };
    }
    return { totalMappings: 0, coverage: 0, lastUpdated: '' };
  }

  /**
   * Validate element code
   */
  async validateElementCode(code: string): Promise<boolean> {
    const validateButton = this.page.locator('button:has-text("验证代码")');
    if (await validateButton.isVisible()) {
      await this.page.locator('input[name="code"]').fill(code);
      await validateButton.click();
      await this.page.waitForTimeout(500);

      const isValid = !(await this.page.locator('.ant-message-error').isVisible());
      return isValid;
    }
    return true;
  }

  /**
   * Apply element template
   */
  async applyElementTemplate(templateName: string): Promise<void> {
    const templateButton = this.page.locator('button:has-text("应用模板"), button:has-text("模板")');
    if (await templateButton.isVisible()) {
      await templateButton.click();
      await this.page.waitForTimeout(300);

      await this.page.locator(`.ant-dropdown-item:has-text("${templateName}")`).click();
      await this.page.waitForTimeout(1000);
    }
  }

  /**
   * Get element usage
   */
  async getElementUsage(elementName: string): Promise<{ mappings: number; tables: string[] }> {
    await this.switchToElements();
    const row = this.findTableRowByText(elementName);
    await row.locator('button:has-text("使用情况"), button:has(.anticon-bar-chart)').click();
    await this.waitForDrawer();

    const mappingCountText = await this.page.locator('.mapping-count').textContent() || '0';
    const mappingCount = parseInt(mappingCountText) || 0;

    const tableRows = this.page.locator('.usage-table .ant-table-row');
    const count = await tableRows.count();
    const tables: string[] = [];

    for (let i = 0; i < Math.min(count, 10); i++) {
      const tableName = await tableRows.nth(i).locator('.ant-table-cell').nth(0).textContent() || '';
      if (tableName) tables.push(tableName.trim());
    }

    return { mappings: mappingCount, tables };
  }

  /**
   * Export document
   */
  async exportDocument(docName: string, format: 'pdf' | 'word' = 'pdf'): Promise<void> {
    await this.switchToDocuments();
    const row = this.findTableRowByText(docName);
    await row.locator('button:has-text("导出")').click();
    await this.page.waitForTimeout(300);

    await this.page.locator(`.ant-dropdown-item:has-text("${format}")`).click();
  }

  /**
   * Compare documents
   */
  async compareDocuments(doc1Name: string, doc2Name: string): Promise<void> {
    await this.switchToDocuments();
    const doc1Row = this.findTableRowByText(doc1Name);
    await doc1Row.locator('input[type="checkbox"]').check();

    const doc2Row = this.findTableRowByText(doc2Name);
    await doc2Row.locator('input[type="checkbox"]').check();

    const compareButton = this.page.locator('button:has-text("对比文档")');
    if (await compareButton.isEnabled()) {
      await compareButton.click();
      await this.waitForModal();
    }
  }
}
