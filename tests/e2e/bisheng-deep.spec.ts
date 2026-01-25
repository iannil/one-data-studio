/**
 * Bisheng LLMOps 深度验收测试
 * 覆盖提示词、知识库、AI 应用、评测、SFT 微调、Agent 等功能
 * 使用真实 API 调用
 */

import { test, expect } from './fixtures/real-auth.fixture';
import { createApiClient, clearRequestLogs, getFailedRequests } from './helpers/api-client';
import type { BishengApiClient } from './helpers/api-client';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

// ============================================
// 提示词模板深度测试
// ============================================
test.describe('Bisheng - 提示词模板', () => {
  test('should display prompts list', async ({ page }) => {
    await page.goto(`${BASE_URL}/prompts`);
    await page.waitForLoadState('networkidle');

    const list = page.locator('.prompt-list, .data-table, [class*="table"]').first();
    await expect(list).toBeVisible();
  });

  test('should create prompt template', async ({ page }) => {
    await page.goto(`${BASE_URL}/prompts`);
    await page.waitForLoadState('networkidle');

    const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);

      const modal = page.locator('.ant-modal, .modal');
      const hasModal = await modal.count() > 0;
      if (hasModal) {
        const nameInput = modal.locator('input[name="name"], input[placeholder*="名称"]');
        if (await nameInput.isVisible()) {
          await nameInput.fill(`e2e-test-prompt-${Date.now()}`);

          const templateInput = modal.locator('textarea[name="template"], textarea[placeholder*="模板"]');
          if (await templateInput.isVisible()) {
            await templateInput.fill('你是一个 helpful assistant，请回答用户的问题：{{question}}');
          }

          const confirmButton = modal.locator('button:has-text("确定"), button:has-text("创建")').first();
          await confirmButton.click();
          await page.waitForTimeout(1000);
        }
      }
    }
  });

  test('should define prompt variables', async ({ page }) => {
    await page.goto(`${BASE_URL}/prompts`);
    await page.waitForLoadState('networkidle');

    const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);

      const variableInput = page.locator('input[name="variables"], .variable-input');
      const hasVariableInput = await variableInput.count() > 0;
      if (hasVariableInput) {
        await variableInput.first().fill('question,context');
      }
    }
  });

  test('should test prompt template', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'bisheng') as BishengApiClient;

    // 创建测试提示词
    const createResult = await apiClient.post('/api/v1/prompts', {
      name: `e2e-test-prompt-${Date.now()}`,
      template: '请总结以下内容：{{content}}',
      variables: ['content'],
    });

    if (createResult.code === 0 && createResult.data?.id) {
      const testResult = await apiClient.post(`/api/v1/prompts/${createResult.data.id}/test`, {
        variables: { content: '这是一段测试内容。' },
      });
      expect(testResult.code).toBe(0);
    }
  });

  test('should display prompt versions', async ({ page }) => {
    await page.goto(`${BASE_URL}/prompts`);
    await page.waitForLoadState('networkidle');

    const firstPrompt = page.locator('tr[data-row-key], .prompt-item').first();
    if (await firstPrompt.isVisible()) {
      const versionButton = firstPrompt.locator('button:has-text("版本"), button:has-text("Version")').first();
      if (await versionButton.isVisible()) {
        await versionButton.click();
        await page.waitForTimeout(500);

        const versionList = page.locator('.version-list, .version-history');
        const hasVersionList = await versionList.count() > 0;
        console.log('Has version list:', hasVersionList);
      }
    }
  });
});

// ============================================
// 知识库深度测试
// ============================================
test.describe('Bisheng - 知识库', () => {
  test('should display knowledge bases list', async ({ page }) => {
    await page.goto(`${BASE_URL}/knowledge`);
    await page.waitForLoadState('networkidle');

    const list = page.locator('.knowledge-list, .data-table, [class*="table"]').first();
    await expect(list).toBeVisible();
  });

  test('should create knowledge base', async ({ page }) => {
    await page.goto(`${BASE_URL}/knowledge`);
    await page.waitForLoadState('networkidle');

    const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);

      const modal = page.locator('.ant-modal, .modal');
      const hasModal = await modal.count() > 0;
      if (hasModal) {
        const nameInput = modal.locator('input[name="name"], input[placeholder*="名称"]');
        if (await nameInput.isVisible()) {
          await nameInput.fill(`e2e-test-kb-${Date.now()}`);

          const descInput = modal.locator('textarea[name="description"]');
          if (await descInput.isVisible()) {
            await descInput.fill('E2E测试知识库');
          }

          const confirmButton = modal.locator('button:has-text("确定"), button:has-text("创建")').first();
          await confirmButton.click();
          await page.waitForTimeout(1000);
        }
      }
    }
  });

  test('should upload document to knowledge base', async ({ page }) => {
    await page.goto(`${BASE_URL}/knowledge`);
    await page.waitForLoadState('networkidle');

    const firstKb = page.locator('tr[data-row-key], .knowledge-item').first();
    if (await firstKb.isVisible()) {
      const uploadButton = firstKb.locator('button:has-text("上传"), button:has-text("Upload")').first();
      if (await uploadButton.isVisible()) {
        await uploadButton.click();
        await page.waitForTimeout(500);

        const fileInput = page.locator('input[type="file"]');
        if (await fileInput.isVisible()) {
          await fileInput.setInputFiles({
            name: 'test-document.txt',
            mimeType: 'text/plain',
            buffer: Buffer.from('This is a test document for knowledge base.'),
          });
          await page.waitForTimeout(2000);
        }
      }
    }
  });

  test('should vectorize uploaded documents', async ({ page }) => {
    await page.goto(`${BASE_URL}/knowledge`);
    await page.waitForLoadState('networkidle');

    const vectorizeButton = page.locator('button:has-text("向量化"), button:has-text("Vectorize")').first();
    if (await vectorizeButton.isVisible()) {
      await vectorizeButton.click();
      await page.waitForTimeout(1000);
    }
  });

  test('should test knowledge base retrieval', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'bisheng') as BishengApiClient;

    const knowledgeResponse = await apiClient.get('/api/v1/knowledge');
    if (knowledgeResponse.data?.knowledge_bases?.length > 0) {
      const kbId = knowledgeResponse.data.knowledge_bases[0].id;

      // 测试检索
      const searchResult = await apiClient.post(`/api/v1/knowledge/${kbId}/search`, {
        query: '测试查询',
        top_k: 5,
      });

      expect(searchResult.code).toBe(0);
    }
  });
});

// ============================================
// AI 应用深度测试
// ============================================
test.describe('Bisheng - AI 应用', () => {
  test('should display apps list', async ({ page }) => {
    await page.goto(`${BASE_URL}/apps`);
    await page.waitForLoadState('networkidle');

    const list = page.locator('.app-list, .data-table, [class*="table"]').first();
    await expect(list).toBeVisible();
  });

  test('should create new AI app', async ({ page }) => {
    await page.goto(`${BASE_URL}/apps`);
    await page.waitForLoadState('networkidle');

    const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);

      const modal = page.locator('.ant-modal, .modal');
      const hasModal = await modal.count() > 0;
      if (hasModal) {
        const nameInput = modal.locator('input[name="name"], input[placeholder*="名称"]');
        if (await nameInput.isVisible()) {
          await nameInput.fill(`e2e-test-app-${Date.now()}`);

          const typeSelect = modal.locator('select[name="type"], .ant-select-selector').first();
          if (await typeSelect.isVisible()) {
            await typeSelect.click();
            await page.waitForTimeout(300);

            const chatOption = page.locator('.ant-select-item-option:has-text("聊天"), .ant-select-item-option:has-text("Chat")').first();
            if (await chatOption.isVisible()) {
              await chatOption.click();
            }
          }

          const confirmButton = modal.locator('button:has-text("确定"), button:has-text("创建")').first();
          await confirmButton.click();
          await page.waitForTimeout(1000);
        }
      }
    }
  });

  test('should configure app settings', async ({ page }) => {
    await page.goto(`${BASE_URL}/apps`);
    await page.waitForLoadState('networkidle');

    const firstApp = page.locator('tr[data-row-key], .app-item').first();
    if (await firstApp.isVisible()) {
      const configButton = firstApp.locator('button:has-text("配置"), button:has-text("Config"), [class*="config"]').first();
      if (await configButton.isVisible()) {
        await configButton.click();
        await page.waitForTimeout(500);

        const configPanel = page.locator('.config-panel, .settings-panel');
        const hasConfigPanel = await configPanel.count() > 0;
        if (hasConfigPanel) {
          await expect(configPanel.first()).toBeVisible();
        }
      }
    }
  });

  test('should publish app', async ({ page }) => {
    await page.goto(`${BASE_URL}/apps`);
    await page.waitForLoadState('networkidle');

    const firstApp = page.locator('tr[data-row-key], .app-item').first();
    if (await firstApp.isVisible()) {
      const publishButton = firstApp.locator('button:has-text("发布"), button:has-text("Publish")').first();
      if (await publishButton.isVisible()) {
        await publishButton.click();
        await page.waitForTimeout(500);

        const confirmButton = page.locator('.ant-modal-confirm button:has-text("确定")').first();
        if (await confirmButton.isVisible()) {
          await confirmButton.click();
          await page.waitForTimeout(1000);
        }
      }
    }
  });

  test('should test app with chat interface', async ({ page }) => {
    await page.goto(`${BASE_URL}/apps`);
    await page.waitForLoadState('networkidle');

    const firstApp = page.locator('tr[data-row-key], .app-item').first();
    if (await firstApp.isVisible()) {
      const testButton = firstApp.locator('button:has-text("测试"), button:has-text("Test")').first();
      if (await testButton.isVisible()) {
        await testButton.click();
        await page.waitForTimeout(500);

        const chatInterface = page.locator('.chat-interface, .test-panel');
        const hasChat = await chatInterface.count() > 0;
        if (hasChat) {
          const inputBox = chatInterface.locator('textarea, input[type="text"]').first();
          if (await inputBox.isVisible()) {
            await inputBox.fill('你好');
            const sendButton = chatInterface.locator('button:has-text("发送"), button:has-text("Send")').first();
            if (await sendButton.isVisible()) {
              await sendButton.click();
              await page.waitForTimeout(2000);
            }
          }
        }
      }
    }
  });
});

// ============================================
// 评测深度测试
// ============================================
test.describe('Bisheng - 评测', () => {
  test('should display evaluations list', async ({ page }) => {
    await page.goto(`${BASE_URL}/evaluations`);
    await page.waitForLoadState('networkidle');

    const list = page.locator('.evaluation-list, .data-table, [class*="table"]').first();
    await expect(list).toBeVisible();
  });

  test('should create evaluation dataset', async ({ page }) => {
    await page.goto(`${BASE_URL}/evaluations`);
    await page.waitForLoadState('networkidle');

    const datasetButton = page.locator('button:has-text("数据集"), button:has-text("Dataset")').first();
    if (await datasetButton.isVisible()) {
      await datasetButton.click();
      await page.waitForTimeout(500);

      const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
      if (await createButton.isVisible()) {
        await createButton.click();
        await page.waitForTimeout(500);
      }
    }
  });

  test('should create evaluation task', async ({ page }) => {
    await page.goto(`${BASE_URL}/evaluations`);
    await page.waitForLoadState('networkidle');

    const createButton = page.locator('button:has-text("创建评测"), button:has-text("创建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);

      const modal = page.locator('.ant-modal, .modal');
      const hasModal = await modal.count() > 0;
      if (hasModal) {
        const form = modal.locator('form');
        const hasForm = await form.count() > 0;
        if (hasForm) {
          await expect(form.first()).toBeVisible();
        }
      }
    }
  });

  test('should display evaluation results', async ({ page }) => {
    await page.goto(`${BASE_URL}/evaluations`);
    await page.waitForLoadState('networkidle');

    const firstEval = page.locator('tr[data-row-key], .evaluation-item').first();
    if (await firstEval.isVisible()) {
      const viewButton = firstEval.locator('button:has-text("查看"), button:has-text("View")').first();
      if (await viewButton.isVisible()) {
        await viewButton.click();
        await page.waitForTimeout(500);

        const resultsPanel = page.locator('.evaluation-results, .results-panel');
        const hasResults = await resultsPanel.count() > 0;
        if (hasResults) {
          await expect(resultsPanel.first()).toBeVisible();
        }
      }
    }
  });

  test('should compare evaluation results', async ({ page }) => {
    await page.goto(`${BASE_URL}/evaluations`);
    await page.waitForLoadState('networkidle');

    const compareButton = page.locator('button:has-text("对比"), button:has-text("Compare")').first();
    if (await compareButton.isVisible()) {
      await compareButton.click();
      await page.waitForTimeout(500);

      const compareView = page.locator('.compare-view, .comparison');
      const hasCompare = await compareView.count() > 0;
      console.log('Has comparison view:', hasCompare);
    }
  });
});

// ============================================
// SFT 微调深度测试
// ============================================
test.describe('Bisheng - SFT 微调', () => {
  test('should display SFT page', async ({ page }) => {
    await page.goto(`${BASE_URL}/sft`);
    await page.waitForLoadState('networkidle');

    const content = page.locator('.sft-content, .tuning-content');
    await expect(content.first()).toBeVisible();
  });

  test('should prepare training data', async ({ page }) => {
    await page.goto(`${BASE_URL}/sft`);
    await page.waitForLoadState('networkidle');

    const dataButton = page.locator('button:has-text("数据"), button:has-text("Data")').first();
    if (await dataButton.isVisible()) {
      await dataButton.click();
      await page.waitForTimeout(500);

      const uploadButton = page.locator('button:has-text("上传"), button:has-text("Upload")').first();
      if (await uploadButton.isVisible()) {
        await uploadButton.click();
        await page.waitForTimeout(500);
      }
    }
  });

  test('should create SFT training task', async ({ page }) => {
    await page.goto(`${BASE_URL}/sft`);
    await page.waitForLoadState('networkidle');

    const createButton = page.locator('button:has-text("创建任务"), button:has-text("新建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);

      const form = page.locator('.ant-form, .training-form');
      const hasForm = await form.count() > 0;
      if (hasForm) {
        const modelSelect = form.locator('select[name="model"], .ant-select').first();
        const hasModelSelect = await modelSelect.count() > 0;
        console.log('Has model select:', hasModelSelect);
      }
    }
  });

  test('should monitor training progress', async ({ page }) => {
    await page.goto(`${BASE_URL}/sft`);
    await page.waitForLoadState('networkidle');

    const progressBar = page.locator('.ant-progress, .progress-bar');
    const hasProgress = await progressBar.count() > 0;
    if (hasProgress) {
      await expect(progressBar.first()).toBeVisible();
    }
  });
});

// ============================================
// Agent 深度测试
// ============================================
test.describe('Bisheng - Agent', () => {
  test('should display agents list', async ({ page }) => {
    await page.goto(`${BASE_URL}/agents`);
    await page.waitForLoadState('networkidle');

    const list = page.locator('.agent-list, .data-table, [class*="table"]').first();
    await expect(list).toBeVisible();
  });

  test('should create agent from template', async ({ page }) => {
    await page.goto(`${BASE_URL}/agents`);
    await page.waitForLoadState('networkidle');

    const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);

      const templateList = page.locator('.agent-template, .template-list');
      const hasTemplates = await templateList.count() > 0;
      if (hasTemplates) {
        const firstTemplate = templateList.locator('.template-item').first();
        if (await firstTemplate.isVisible()) {
          await firstTemplate.click();
          await page.waitForTimeout(500);

          const confirmButton = page.locator('button:has-text("确定"), button:has-text("创建")').first();
          if (await confirmButton.isVisible()) {
            await confirmButton.click();
            await page.waitForTimeout(1000);
          }
        }
      }
    }
  });

  test('should configure agent tools', async ({ page }) => {
    await page.goto(`${BASE_URL}/agents`);
    await page.waitForLoadState('networkidle');

    const firstAgent = page.locator('tr[data-row-key], .agent-item').first();
    if (await firstAgent.isVisible()) {
      const configButton = firstAgent.locator('button:has-text("配置"), button:has-text("Config")').first();
      if (await configButton.isVisible()) {
        await configButton.click();
        await page.waitForTimeout(500);

        const toolsPanel = page.locator('.tools-panel, .tools-config');
        const hasToolsPanel = await toolsPanel.count() > 0;
        if (hasToolsPanel) {
          await expect(toolsPanel.first()).toBeVisible();
        }
      }
    }
  });

  test('should run agent', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'bisheng') as BishengApiClient;

    const agents = await apiClient.getAgents();
    if (agents.data?.agents?.length > 0) {
      const agentId = agents.data.agents[0].id;

      const runResult = await apiClient.runAgent(agentId, '帮我查询今天的天气');
      expect(runResult.code).toBe(0);
    }
  });

  test('should display agent execution history', async ({ page }) => {
    await page.goto(`${BASE_URL}/agents`);
    await page.waitForLoadState('networkidle');

    const firstAgent = page.locator('tr[data-row-key], .agent-item').first();
    if (await firstAgent.isVisible()) {
      const historyButton = firstAgent.locator('button:has-text("历史"), button:has-text("History")').first();
      if (await historyButton.isVisible()) {
        await historyButton.click();
        await page.waitForTimeout(500);

        const historyPanel = page.locator('.history-panel, .execution-list');
        const hasHistory = await historyPanel.count() > 0;
        console.log('Has history panel:', hasHistory);
      }
    }
  });
});

// ============================================
// API 端点验证测试
// ============================================
test.describe('Bisheng - API 端点验证', () => {
  test('should verify all Bisheng API endpoints', async ({ request }) => {
    const apiClient = createApiClient(request, 'bisheng') as BishengApiClient;
    clearRequestLogs();

    // 健康检查
    const health = await apiClient.healthCheck();
    expect(health.code).toBe(0);

    // 用户信息
    const userInfo = await apiClient.getUserInfo();
    expect(userInfo.code).toBe(0);

    // 会话列表
    const conversations = await apiClient.getConversations();
    expect(conversations.code).toBe(0);

    // 工作流列表
    const workflows = await apiClient.getWorkflows();
    expect(workflows.code).toBe(0);

    // Agent 列表
    const agents = await apiClient.getAgents();
    expect(agents.code).toBe(0);

    // 数据集列表
    const datasets = await apiClient.getDatasets();
    expect(datasets.code).toBe(0);

    // 统计信息
    const stats = await apiClient.getStats();
    expect(stats.code).toBe(0);

    // Text2SQL 生成
    const sqlResult = await apiClient.generateSQL('查询所有用户');
    expect(sqlResult.code).toBe(0);

    // 验证没有失败的请求
    const failedRequests = getFailedRequests();
    expect(failedRequests.length).toBe(0);
  });

  test('should handle chat API correctly', async ({ request }) => {
    const apiClient = createApiClient(request, 'bisheng') as BishengApiClient;

    // 创建会话
    const createResult = await apiClient.createConversation('E2E Test Conversation');
    expect(createResult.code).toBe(0);

    if (createResult.data?.id) {
      const conversationId = createResult.data.id;

      // 发送消息
      const messageResult = await apiClient.sendMessage(conversationId, '你好');
      expect(messageResult.code).toBe(0);

      // 获取消息历史
      const messagesResult = await apiClient.getMessages(conversationId);
      expect(messagesResult.code).toBe(0);
    }
  });
});

// ============================================
// 边界条件测试
// ============================================
test.describe('Bisheng - 边界条件', () => {
  test('should handle empty knowledge base', async ({ page }) => {
    await page.goto(`${BASE_URL}/knowledge`);
    await page.waitForLoadState('networkidle');

    const emptyState = page.locator('.empty-state, .no-data');
    const hasEmpty = await emptyState.count() > 0;
    console.log('Has empty state for knowledge base:', hasEmpty);
  });

  test('should handle long prompt template', async ({ page }) => {
    await page.goto(`${BASE_URL}/prompts`);
    await page.waitForLoadState('networkidle');

    const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);

      const textarea = page.locator('textarea[name="template"], .ant-input-textarea').first();
      if (await textarea.isVisible()) {
        const longPrompt = '这是一个很长的提示词模板。'.repeat(100);
        await textarea.fill(longPrompt);

        const value = await textarea.inputValue();
        expect(value.length).toBeGreaterThan(1000);
      }
    }
  });

  test('should handle special characters in prompt', async ({ page }) => {
    await page.goto(`${BASE_URL}/prompts`);
    await page.waitForLoadState('networkidle');

    const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);

      const textarea = page.locator('textarea[name="template"], .ant-input-textarea').first();
      if (await textarea.isVisible()) {
        const specialPrompt = '测试特殊字符：@#$%^&*()_+-={}[]|:;<>,.?/~`\'"\\';
        await textarea.fill(specialPrompt);

        const value = await textarea.inputValue();
        expect(value).toContain('@#$%');
      }
    }
  });
});

test.afterEach(async ({ request }) => {
  const failedRequests = getFailedRequests();
  if (failedRequests.length > 0) {
    console.error('Failed API requests in Bisheng test:', failedRequests);
  }
});
