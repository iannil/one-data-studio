/**
 * Agents Page Object Model
 *
 * Page: /agents
 * Features: Agent CRUD, configuration, execution
 */

import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class AgentsPage extends BasePage {
  readonly PAGE_PATH = '/agents';

  // Page locators
  readonly createButton: Locator;
  readonly searchInput: Locator;
  readonly table: Locator;
  readonly tableBody: Locator;

  // Modal locators
  readonly agentNameInput: Locator;
  readonly agentTypeSelect: Locator;
  readonly modelSelect: Locator;
  readonly promptTextarea: Locator;
  readonly configTextarea: Locator;
  readonly saveButton: Locator;
  readonly cancelButton: Locator;

  // Agent action locators
  readonly runButton: Locator;
  readonly chatButton: Locator;
  readonly editButton: Locator;
  readonly deleteButton: Locator;

  // Chat interface locators
  readonly chatInput: Locator;
  readonly sendButton: Locator;
  readonly chatMessages: Locator;
  readonly agentResponse: Locator;

  constructor(page: Page) {
    super(page);

    // Initialize locators
    this.createButton = page.locator('button:has-text("新建"), button:has-text("创建"), button:has(.anticon-plus)');
    this.searchInput = page.locator('input[placeholder*="搜索"], .ant-input-search input');
    this.table = page.locator('.ant-table');
    this.tableBody = page.locator('.ant-table-tbody');

    // Modal locators
    this.agentNameInput = page.locator('.ant-modal input[name="name"], .ant-modal label:has-text("名称") + input');
    this.agentTypeSelect = page.locator('.ant-modal .ant-select:has-text("类型"), .ant-modal label:has-text("类型") + .ant-select');
    this.modelSelect = page.locator('.ant-modal .ant-select:has-text("模型"), .ant-modal label:has-text("模型") + .ant-select');
    this.promptTextarea = page.locator('.ant-modal textarea:visible, .ant-modal label:has-text("提示词") + textarea');
    this.configTextarea = page.locator('.ant-modal label:has-text("配置") + textarea');
    this.saveButton = page.locator('.ant-modal button:has-text("保存"), .ant-modal button:has-text("确定"), .ant-modal .ant-btn-primary');
    this.cancelButton = page.locator('.ant-modal button:has-text("取消"), .ant-modal button:has-text("Cancel")');

    // Agent action locators
    this.runButton = page.locator('button:has-text("运行"), button:has(.anticon-play-circle)');
    this.chatButton = page.locator('button:has-text("对话"), button:has(.anticon-message)');
    this.editButton = page.locator('button:has-text("编辑"), button:has(.anticon-edit)');
    this.deleteButton = page.locator('button:has-text("删除"), button:has(.anticon-delete)');

    // Chat interface locators
    this.chatInput = page.locator('textarea[placeholder*="输入"], .chat-input textarea, .ant-input textarea');
    this.sendButton = page.locator('button:has-text("发送"), button:has(.anticon-send)');
    this.chatMessages = page.locator('.chat-messages, .message-list, .conversation-messages');
    this.agentResponse = page.locator('.agent-response, .assistant-message, .message-content');
  }

  /**
   * Navigate to agents page
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
   * Fill agent form
   */
  async fillForm(data: {
    name: string;
    type?: string;
    model?: string;
    prompt?: string;
    config?: string;
  }): Promise<void> {
    // Name
    await this.agentNameInput.fill(data.name);
    await this.page.waitForTimeout(200);

    // Type (optional)
    if (data.type && await this.agentTypeSelect.isVisible()) {
      await this.agentTypeSelect.click();
      await this.page.waitForTimeout(200);
      await this.page.locator(`.ant-select-item:has-text("${data.type}")`).click();
      await this.page.waitForTimeout(200);
    }

    // Model (optional)
    if (data.model && await this.modelSelect.isVisible()) {
      await this.modelSelect.click();
      await this.page.waitForTimeout(200);
      await this.page.locator(`.ant-select-item:has-text("${data.model}")`).click();
      await this.page.waitForTimeout(200);
    }

    // Prompt (optional)
    if (data.prompt && await this.promptTextarea.isVisible()) {
      await this.promptTextarea.fill(data.prompt);
      await this.page.waitForTimeout(200);
    }

    // Config (optional)
    if (data.config && await this.configTextarea.isVisible()) {
      await this.configTextarea.fill(data.config);
      await this.page.waitForTimeout(200);
    }
  }

  /**
   * Create an agent
   */
  async createAgent(data: {
    name: string;
    type?: string;
    model?: string;
    prompt?: string;
    config?: string;
  }): Promise<boolean> {
    await this.clickCreate();
    await this.fillForm(data);

    await this.saveButton.first().click();
    await this.page.waitForTimeout(1000);

    return await this.verifyToastMessage('success');
  }

  /**
   * Get agent count
   */
  async getCount(): Promise<number> {
    await this.waitForTableLoad();
    return await this.getTableRowCount();
  }

  /**
   * Check if agent exists
   */
  async exists(name: string): Promise<boolean> {
    const row = this.tableBody.locator('.ant-table-row').filter({ hasText: name });
    return await row.count() > 0;
  }

  /**
   * Search for an agent
   */
  async search(name: string): Promise<void> {
    await this.searchInput.fill(name);
    await this.page.waitForTimeout(1000);
  }

  /**
   * Run an agent
   */
  async runAgent(name: string, input?: string): Promise<void> {
    const row = this.tableBody.locator('.ant-table-row').filter({ hasText: name });
    await row.locator('button:has-text("运行"), button:has(.anticon-play-circle)').first().click();
    await this.page.waitForTimeout(1000);

    // If input is provided and input field appears
    if (input && await this.chatInput.isVisible()) {
      await this.chatInput.fill(input);
      await this.sendButton.click();
      await this.page.waitForTimeout(3000);
    }
  }

  /**
   * Open chat with agent
   */
  async openChat(name: string): Promise<void> {
    const row = this.tableBody.locator('.ant-table-row').filter({ hasText: name });
    await row.locator('button:has-text("对话"), button:has(.anticon-message)').first().click();
    await this.page.waitForTimeout(1000);
  }

  /**
   * Send message to agent
   */
  async sendMessage(message: string): Promise<void> {
    await this.chatInput.fill(message);
    await this.sendButton.click();
    await this.page.waitForTimeout(3000);
  }

  /**
   * Get agent response
   */
  async getResponse(): Promise<string> {
    await this.page.waitForTimeout(1000);
    const response = await this.agentResponse.last().textContent() || '';
    return response.trim();
  }

  /**
   * Get all chat messages
   */
  async getChatMessages(): Promise<string[]> {
    const messages = this.chatMessages.locator('.message, .chat-message');
    const count = await messages.count();
    const result: string[] = [];

    for (let i = 0; i < count; i++) {
      const text = await messages.nth(i).textContent() || '';
      result.push(text.trim());
    }

    return result;
  }

  /**
   * Delete an agent
   */
  async deleteAgent(name: string): Promise<boolean> {
    const row = this.tableBody.locator('.ant-table-row').filter({ hasText: name });
    await row.locator('button:has(.anticon-ellipsis), .ant-dropdown-trigger').first().click();
    await this.page.waitForTimeout(300);

    await this.page.locator('.ant-dropdown-menu-item:has-text("删除")').click();
    await this.confirmDialog();

    return await this.verifyToastMessage('success');
  }

  /**
   * Edit an agent
   */
  async editAgent(name: string): Promise<void> {
    const row = this.tableBody.locator('.ant-table-row').filter({ hasText: name });
    await row.locator('button:has(.anticon-ellipsis), .ant-dropdown-trigger').first().click();
    await this.page.waitForTimeout(300);

    await this.page.locator('.ant-dropdown-menu-item:has-text("编辑")').click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Get agent info from table
   */
  async getAgentInfo(name: string): Promise<{
    name: string;
    type: string;
    model: string;
    status: string;
  } | null> {
    const row = this.tableBody.locator('.ant-table-row').filter({ hasText: name });
    if (await row.count() === 0) {
      return null;
    }

    const cells = row.locator('.ant-table-cell');
    const nameText = await cells.nth(0).textContent() || '';
    const typeText = await cells.nth(1).textContent() || '';
    const modelText = await cells.nth(2).textContent() || '';
    const statusText = await cells.nth(3).textContent() || '';

    return {
      name: nameText.trim(),
      type: typeText.trim(),
      model: modelText.trim(),
      status: statusText.trim(),
    };
  }

  /**
   * Get all agent names
   */
  async getAllNames(): Promise<string[]> {
    await this.waitForTableLoad();
    return await this.getTableColumnValues(0);
  }

  /**
   * Close chat dialog
   */
  async closeChat(): Promise<void> {
    const closeButton = this.page.locator('.ant-modal-close, button:has-text("关闭")');
    await closeButton.click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Configure agent settings
   */
  async configureAgent(name: string): Promise<void> {
    const row = this.tableBody.locator('.ant-table-row').filter({ hasText: name });
    await row.locator('button:has-text("配置"), button:has(.anticon-setting)').first().click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Get agent execution history
   */
  async getExecutionHistory(name: string): Promise<string[]> {
    const row = this.tableBody.locator('.ant-table-row').filter({ hasText: name });
    await row.locator('button:has-text("历史"), button:has(.anticon-history)').first().click();
    await this.page.waitForTimeout(500);

    const historyItems = this.page.locator('.history-item, .execution-record');
    const count = await historyItems.count();
    const result: string[] = [];

    for (let i = 0; i < count; i++) {
      const text = await historyItems.nth(i).textContent() || '';
      result.push(text.trim());
    }

    return result;
  }
}
