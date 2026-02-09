/**
 * Test Data Persistence for Playwright E2E Tests
 *
 * 功能：
 * - 管理测试创建的所有资源
 * - 保存测试数据状态到文件
 * - 生成手动验证指南
 * - 提供数据清理脚本
 */

import { writeFileSync, readFileSync, existsSync, mkdirSync } from 'fs';
import { logger } from './logger';
import { join } from 'path';

// ============================================================================
// Types & Interfaces
// ============================================================================

export interface TestUser {
  username: string;
  password?: string;
  email?: string;
  role?: string;
  userId?: string;
  createdAt: string;
}

export interface DatasourceInfo {
  id?: string;
  name: string;
  type: string;
  host?: string;
  port?: number;
  database?: string;
  createdAt: string;
}

export interface DatasetInfo {
  id?: string;
  name: string;
  type?: string;
  datasourceId?: string;
  createdAt: string;
}

export interface AgentInfo {
  id?: string;
  name: string;
  type?: string;
  description?: string;
  createdAt: string;
}

export interface WorkflowInfo {
  id?: string;
  name: string;
  description?: string;
  status?: string;
  createdAt: string;
}

export interface ModelInfo {
  id?: string;
  name: string;
  version?: string;
  framework?: string;
  createdAt: string;
}

export interface NotebookInfo {
  id?: string;
  name: string;
  kernel?: string;
  status?: string;
  createdAt: string;
}

export interface ExperimentInfo {
  id?: string;
  name: string;
  projectId?: string;
  createdAt: string;
}

export interface DocumentInfo {
  id?: string;
  name: string;
  type?: string;
  size?: number;
  createdAt: string;
}

export interface QualityRuleInfo {
  id?: string;
  name: string;
  datasetId?: string;
  ruleType?: string;
  createdAt: string;
}

export interface ETLTaskInfo {
  id?: string;
  name: string;
  sourceId?: string;
  targetId?: string;
  status?: string;
  createdAt: string;
}

export interface FeatureInfo {
  id?: string;
  name: string;
  datasetId?: string;
  featureType?: string;
  createdAt: string;
}

export interface StandardInfo {
  id?: string;
  name: string;
  category?: string;
  createdAt: string;
}

export interface AssetInfo {
  id?: string;
  name: string;
  type?: string;
  value?: string;
  createdAt: string;
}

export interface TestDataManagerState {
  testInfo: {
    testId: string;
    testName: string;
    startTime: string;
    endTime?: string;
    duration?: number;
    baseUrl: string;
  };
  users: Record<string, TestUser>;
  datasources: Record<string, DatasourceInfo>;
  datasets: Record<string, DatasetInfo>;
  agents: Record<string, AgentInfo>;
  workflows: Record<string, WorkflowInfo>;
  models: Record<string, ModelInfo>;
  notebooks: Record<string, NotebookInfo>;
  experiments: Record<string, ExperimentInfo>;
  documents: Record<string, DocumentInfo>;
  qualityRules: Record<string, QualityRuleInfo>;
  etlTasks: Record<string, ETLTaskInfo>;
  features: Record<string, FeatureInfo>;
  standards: Record<string, StandardInfo>;
  assets: Record<string, AssetInfo>;
}

const STATE_FILE_PATH = join(process.cwd(), 'test-results', 'full-platform-test-data.json');
const VERIFICATION_GUIDE_PATH = join(process.cwd(), 'test-results', 'verification-guide.md');
const CLEANUP_SCRIPT_PATH = join(process.cwd(), 'scripts', 'cleanup-test-data.sh');

// ============================================================================
// Test Data Persistence Class
// ============================================================================

export class TestDataPersistence {
  private state: TestDataManagerState;
  private stateFilePath: string;
  private verificationGuidePath: string;

  constructor(
    testId: string,
    testName: string,
    stateFilePath: string = STATE_FILE_PATH,
    verificationGuidePath: string = VERIFICATION_GUIDE_PATH
  ) {
    this.stateFilePath = stateFilePath;
    this.verificationGuidePath = verificationGuidePath;

    this.state = {
      testInfo: {
        testId,
        testName,
        startTime: new Date().toISOString(),
        baseUrl: process.env.BASE_URL || 'http://localhost:3000',
      },
      users: {},
      datasources: {},
      datasets: {},
      agents: {},
      workflows: {},
      models: {},
      notebooks: {},
      experiments: {},
      documents: {},
      qualityRules: {},
      etlTasks: {},
      features: {},
      standards: {},
      assets: {},
    };
  }

  // ============================================================================
  // State Management
  // ============================================================================

  /**
   * 加载之前保存的状态
   */
  loadState(): boolean {
    if (existsSync(this.stateFilePath)) {
      try {
        const content = readFileSync(this.stateFilePath, 'utf-8');
        const loadedState = JSON.parse(content) as TestDataManagerState;
        // 合并状态，保留当前的 testInfo
        this.state = { ...loadedState, testInfo: this.state.testInfo };
        logger.info(`[TestDataPersistence] State loaded from: ${this.stateFilePath}`);
        return true;
      } catch (error) {
        console.error('[TestDataPersistence] Failed to load state:', error);
        return false;
      }
    }
    return false;
  }

  /**
   * 保存状态到文件
   */
  saveState(): void {
    try {
      const dir = join(process.cwd(), 'test-results');
      if (!existsSync(dir)) {
        mkdirSync(dir, { recursive: true });
      }

      writeFileSync(this.stateFilePath, JSON.stringify(this.state, null, 2), 'utf-8');
      logger.info(`[TestDataPersistence] State saved to: ${this.stateFilePath}`);
    } catch (error) {
      console.error('[TestDataPersistence] Failed to save state:', error);
    }
  }

  /**
   * 完成测试（设置结束时间）
   */
  completeTest(): void {
    this.state.testInfo.endTime = new Date().toISOString();
    this.state.testInfo.duration =
      new Date(this.state.testInfo.endTime).getTime() -
      new Date(this.state.testInfo.startTime).getTime();
    this.saveState();
  }

  // ============================================================================
  // Resource Tracking
  // ============================================================================

  /**
   * 跟踪用户
   */
  trackUser(key: string, user: TestUser): void {
    this.state.users[key] = {
      ...user,
      createdAt: user.createdAt || new Date().toISOString(),
    };
    this.saveState();
    logger.info(`[TestDataPersistence] Tracked user: ${user.username} (${key})`);
  }

  /**
   * 跟踪数据源
   */
  trackDatasource(key: string, datasource: DatasourceInfo): void {
    this.state.datasources[key] = {
      ...datasource,
      createdAt: datasource.createdAt || new Date().toISOString(),
    };
    this.saveState();
    logger.info(`[TestDataPersistence] Tracked datasource: ${datasource.name} (${key})`);
  }

  /**
   * 跟踪数据集
   */
  trackDataset(key: string, dataset: DatasetInfo): void {
    this.state.datasets[key] = {
      ...dataset,
      createdAt: dataset.createdAt || new Date().toISOString(),
    };
    this.saveState();
    logger.info(`[TestDataPersistence] Tracked dataset: ${dataset.name} (${key})`);
  }

  /**
   * 跟踪 Agent
   */
  trackAgent(key: string, agent: AgentInfo): void {
    this.state.agents[key] = {
      ...agent,
      createdAt: agent.createdAt || new Date().toISOString(),
    };
    this.saveState();
    logger.info(`[TestDataPersistence] Tracked agent: ${agent.name} (${key})`);
  }

  /**
   * 跟踪工作流
   */
  trackWorkflow(key: string, workflow: WorkflowInfo): void {
    this.state.workflows[key] = {
      ...workflow,
      createdAt: workflow.createdAt || new Date().toISOString(),
    };
    this.saveState();
    logger.info(`[TestDataPersistence] Tracked workflow: ${workflow.name} (${key})`);
  }

  /**
   * 跟踪模型
   */
  trackModel(key: string, model: ModelInfo): void {
    this.state.models[key] = {
      ...model,
      createdAt: model.createdAt || new Date().toISOString(),
    };
    this.saveState();
    logger.info(`[TestDataPersistence] Tracked model: ${model.name} (${key})`);
  }

  /**
   * 跟踪 Notebook
   */
  trackNotebook(key: string, notebook: NotebookInfo): void {
    this.state.notebooks[key] = {
      ...notebook,
      createdAt: notebook.createdAt || new Date().toISOString(),
    };
    this.saveState();
    logger.info(`[TestDataPersistence] Tracked notebook: ${notebook.name} (${key})`);
  }

  /**
   * 跟踪实验
   */
  trackExperiment(key: string, experiment: ExperimentInfo): void {
    this.state.experiments[key] = {
      ...experiment,
      createdAt: experiment.createdAt || new Date().toISOString(),
    };
    this.saveState();
    logger.info(`[TestDataPersistence] Tracked experiment: ${experiment.name} (${key})`);
  }

  /**
   * 跟踪文档
   */
  trackDocument(key: string, document: DocumentInfo): void {
    this.state.documents[key] = {
      ...document,
      createdAt: document.createdAt || new Date().toISOString(),
    };
    this.saveState();
    logger.info(`[TestDataPersistence] Tracked document: ${document.name} (${key})`);
  }

  /**
   * 跟踪质量规则
   */
  trackQualityRule(key: string, rule: QualityRuleInfo): void {
    this.state.qualityRules[key] = {
      ...rule,
      createdAt: rule.createdAt || new Date().toISOString(),
    };
    this.saveState();
    logger.info(`[TestDataPersistence] Tracked quality rule: ${rule.name} (${key})`);
  }

  /**
   * 跟踪 ETL 任务
   */
  trackETLTask(key: string, task: ETLTaskInfo): void {
    this.state.etlTasks[key] = {
      ...task,
      createdAt: task.createdAt || new Date().toISOString(),
    };
    this.saveState();
    logger.info(`[TestDataPersistence] Tracked ETL task: ${task.name} (${key})`);
  }

  /**
   * 跟踪特征
   */
  trackFeature(key: string, feature: FeatureInfo): void {
    this.state.features[key] = {
      ...feature,
      createdAt: feature.createdAt || new Date().toISOString(),
    };
    this.saveState();
    logger.info(`[TestDataPersistence] Tracked feature: ${feature.name} (${key})`);
  }

  /**
   * 跟踪标准
   */
  trackStandard(key: string, standard: StandardInfo): void {
    this.state.standards[key] = {
      ...standard,
      createdAt: standard.createdAt || new Date().toISOString(),
    };
    this.saveState();
    logger.info(`[TestDataPersistence] Tracked standard: ${standard.name} (${key})`);
  }

  /**
   * 跟踪资产
   */
  trackAsset(key: string, asset: AssetInfo): void {
    this.state.assets[key] = {
      ...asset,
      createdAt: asset.createdAt || new Date().toISOString(),
    };
    this.saveState();
    logger.info(`[TestDataPersistence] Tracked asset: ${asset.name} (${key})`);
  }

  // ============================================================================
  // Getters
  // ============================================================================

  /**
   * 获取所有用户
   */
  getUsers(): TestUser[] {
    return Object.values(this.state.users);
  }

  /**
   * 获取所有数据源
   */
  getDatasources(): DatasourceInfo[] {
    return Object.values(this.state.datasources);
  }

  /**
   * 获取所有数据集
   */
  getDatasets(): DatasetInfo[] {
    return Object.values(this.state.datasets);
  }

  /**
   * 获取所有 Agents
   */
  getAgents(): AgentInfo[] {
    return Object.values(this.state.agents);
  }

  /**
   * 获取所有工作流
   */
  getWorkflows(): WorkflowInfo[] {
    return Object.values(this.state.workflows);
  }

  /**
   * 获取所有模型
   */
  getModels(): ModelInfo[] {
    return Object.values(this.state.models);
  }

  /**
   * 获取所有 Notebooks
   */
  getNotebooks(): NotebookInfo[] {
    return Object.values(this.state.notebooks);
  }

  /**
   * 获取所有实验
   */
  getExperiments(): ExperimentInfo[] {
    return Object.values(this.state.experiments);
  }

  /**
   * 获取所有文档
   */
  getDocuments(): DocumentInfo[] {
    return Object.values(this.state.documents);
  }

  /**
   * 获取所有质量规则
   */
  getQualityRules(): QualityRuleInfo[] {
    return Object.values(this.state.qualityRules);
  }

  /**
   * 获取所有 ETL 任务
   */
  getETLTasks(): ETLTaskInfo[] {
    return Object.values(this.state.etlTasks);
  }

  /**
   * 获取所有特征
   */
  getFeatures(): FeatureInfo[] {
    return Object.values(this.state.features);
  }

  /**
   * 获取所有标准
   */
  getStandards(): StandardInfo[] {
    return Object.values(this.state.standards);
  }

  /**
   * 获取所有资产
   */
  getAssets(): AssetInfo[] {
    return Object.values(this.state.assets);
  }

  /**
   * 获取完整状态
   */
  getState(): TestDataManagerState {
    return { ...this.state };
  }

  // ============================================================================
  // Report Generation
  // ============================================================================

  /**
   * 生成验证指南
   */
  generateVerificationGuide(): string {
    const lines: string[] = [];

    // 标题
    lines.push('# ONE-DATA-STUDIO 全平台 E2E 测试验证指南');
    lines.push('');
    lines.push('## 测试信息');
    lines.push('');
    lines.push(`- **测试ID**: ${this.state.testInfo.testId}`);
    lines.push(`- **测试名称**: ${this.state.testInfo.testName}`);
    lines.push(`- **开始时间**: ${this.state.testInfo.startTime}`);
    if (this.state.testInfo.endTime) {
      lines.push(`- **结束时间**: ${this.state.testInfo.endTime}`);
    }
    if (this.state.testInfo.duration) {
      lines.push(`- **执行时长**: ${(this.state.testInfo.duration / 1000).toFixed(2)} 秒`);
    }
    lines.push(`- **测试环境**: ${this.state.testInfo.baseUrl}`);
    lines.push('');

    // 资源统计
    lines.push('## 创建的资源统计');
    lines.push('');
    lines.push('| 类别 | 数量 |');
    lines.push('|------|------|');
    lines.push(`| 用户 | ${Object.keys(this.state.users).length} |`);
    lines.push(`| 数据源 | ${Object.keys(this.state.datasources).length} |`);
    lines.push(`| 数据集 | ${Object.keys(this.state.datasets).length} |`);
    lines.push(`| Agents | ${Object.keys(this.state.agents).length} |`);
    lines.push(`| 工作流 | ${Object.keys(this.state.workflows).length} |`);
    lines.push(`| 模型 | ${Object.keys(this.state.models).length} |`);
    lines.push(`| Notebooks | ${Object.keys(this.state.notebooks).length} |`);
    lines.push(`| 实验 | ${Object.keys(this.state.experiments).length} |`);
    lines.push(`| 文档 | ${Object.keys(this.state.documents).length} |`);
    lines.push(`| 质量规则 | ${Object.keys(this.state.qualityRules).length} |`);
    lines.push(`| ETL 任务 | ${Object.keys(this.state.etlTasks).length} |`);
    lines.push(`| 特征 | ${Object.keys(this.state.features).length} |`);
    lines.push(`| 标准 | ${Object.keys(this.state.standards).length} |`);
    lines.push(`| 资产 | ${Object.keys(this.state.assets).length} |`);
    lines.push('');

    // 详细资源列表
    if (Object.keys(this.state.users).length > 0) {
      lines.push('## 用户账号');
      lines.push('');
      lines.push('| 用户名 | 邮箱 | 角色 | 创建时间 |');
      lines.push('|--------|------|------|----------|');
      for (const user of Object.values(this.state.users)) {
        lines.push(`| ${user.username} | ${user.email || '-'} | ${user.role || '-'} | ${user.createdAt} |`);
      }
      lines.push('');
    }

    if (Object.keys(this.state.datasources).length > 0) {
      lines.push('## 数据源');
      lines.push('');
      lines.push('| 名称 | 类型 | 主机 | 端口 | 数据库 | 创建时间 |');
      lines.push('|------|------|------|------|--------|----------|');
      for (const ds of Object.values(this.state.datasources)) {
        lines.push(`| ${ds.name} | ${ds.type} | ${ds.host || '-'} | ${ds.port || '-'} | ${ds.database || '-'} | ${ds.createdAt} |`);
      }
      lines.push('');
    }

    if (Object.keys(this.state.datasets).length > 0) {
      lines.push('## 数据集');
      lines.push('');
      lines.push('| 名称 | 类型 | 数据源ID | 创建时间 |');
      lines.push('|------|------|----------|----------|');
      for (const dataset of Object.values(this.state.datasets)) {
        lines.push(`| ${dataset.name} | ${dataset.type || '-'} | ${dataset.datasourceId || '-'} | ${dataset.createdAt} |`);
      }
      lines.push('');
    }

    if (Object.keys(this.state.agents).length > 0) {
      lines.push('## Agents');
      lines.push('');
      lines.push('| 名称 | 类型 | 描述 | 创建时间 |');
      lines.push('|------|------|------|----------|');
      for (const agent of Object.values(this.state.agents)) {
        lines.push(`| ${agent.name} | ${agent.type || '-'} | ${agent.description || '-'} | ${agent.createdAt} |`);
      }
      lines.push('');
    }

    if (Object.keys(this.state.workflows).length > 0) {
      lines.push('## 工作流');
      lines.push('');
      lines.push('| 名称 | 状态 | 描述 | 创建时间 |');
      lines.push('|------|------|------|----------|');
      for (const workflow of Object.values(this.state.workflows)) {
        lines.push(`| ${workflow.name} | ${workflow.status || '-'} | ${workflow.description || '-'} | ${workflow.createdAt} |`);
      }
      lines.push('');
    }

    if (Object.keys(this.state.models).length > 0) {
      lines.push('## 模型');
      lines.push('');
      lines.push('| 名称 | 版本 | 框架 | 创建时间 |');
      lines.push('|------|------|------|----------|');
      for (const model of Object.values(this.state.models)) {
        lines.push(`| ${model.name} | ${model.version || '-'} | ${model.framework || '-'} | ${model.createdAt} |`);
      }
      lines.push('');
    }

    if (Object.keys(this.state.notebooks).length > 0) {
      lines.push('## Notebooks');
      lines.push('');
      lines.push('| 名称 | 内核 | 状态 | 创建时间 |');
      lines.push('|------|------|------|----------|');
      for (const notebook of Object.values(this.state.notebooks)) {
        lines.push(`| ${notebook.name} | ${notebook.kernel || '-'} | ${notebook.status || '-'} | ${notebook.createdAt} |`);
      }
      lines.push('');
    }

    if (Object.keys(this.state.experiments).length > 0) {
      lines.push('## 实验');
      lines.push('');
      lines.push('| 名称 | 项目ID | 创建时间 |');
      lines.push('|------|---------|----------|');
      for (const experiment of Object.values(this.state.experiments)) {
        lines.push(`| ${experiment.name} | ${experiment.projectId || '-'} | ${experiment.createdAt} |`);
      }
      lines.push('');
    }

    if (Object.keys(this.state.documents).length > 0) {
      lines.push('## 文档');
      lines.push('');
      lines.push('| 名称 | 类型 | 大小 | 创建时间 |');
      lines.push('|------|------|------|----------|');
      for (const doc of Object.values(this.state.documents)) {
        lines.push(`| ${doc.name} | ${doc.type || '-'} | ${doc.size ? `${doc.size} bytes` : '-'} | ${doc.createdAt} |`);
      }
      lines.push('');
    }

    if (Object.keys(this.state.etlTasks).length > 0) {
      lines.push('## ETL 任务');
      lines.push('');
      lines.push('| 名称 | 源ID | 目标ID | 状态 | 创建时间 |');
      lines.push('|------|------|--------|------|----------|');
      for (const task of Object.values(this.state.etlTasks)) {
        lines.push(`| ${task.name} | ${task.sourceId || '-'} | ${task.targetId || '-'} | ${task.status || '-'} | ${task.createdAt} |`);
      }
      lines.push('');
    }

    // 验证步骤
    lines.push('## 手动验证步骤');
    lines.push('');
    lines.push('请按以下步骤验证测试创建的资源：');
    lines.push('');
    lines.push('### 1. 登录系统');
    lines.push('');
    lines.push(`1. 访问: ${this.state.testInfo.baseUrl}`);
    lines.push('2. 使用上述任一测试账号登录');
    lines.push('');

    if (Object.keys(this.state.datasources).length > 0) {
      lines.push('### 2. 验证数据源');
      lines.push('');
      lines.push(`1. 导航到: ${this.state.testInfo.baseUrl}/data/datasources`);
      lines.push('2. 检查上述数据源是否存在于列表中');
      lines.push('3. 点击"测试连接"验证数据源连接状态');
      lines.push('');
    }

    if (Object.keys(this.state.agents).length > 0) {
      lines.push('### 3. 验证 Agents');
      lines.push('');
      lines.push(`1. 导航到: ${this.state.testInfo.baseUrl}/agents`);
      lines.push('2. 检查上述 Agents 是否存在于列表中');
      lines.push('3. 点击 Agent 查看详情和配置');
      lines.push('');
    }

    if (Object.keys(this.state.workflows).length > 0) {
      lines.push('### 4. 验证工作流');
      lines.push('');
      lines.push(`1. 导航到: ${this.state.testInfo.baseUrl}/workflows`);
      lines.push('2. 检查上述工作流是否存在于列表中');
      lines.push('3. 查看工作流执行历史');
      lines.push('');
    }

    if (Object.keys(this.state.models).length > 0) {
      lines.push('### 5. 验证模型');
      lines.push('');
      lines.push(`1. 导航到: ${this.state.testInfo.baseUrl}/model/models`);
      lines.push('2. 检查上述模型是否存在于列表中');
      lines.push('3. 查看模型版本和部署状态');
      lines.push('');
    }

    // 数据清理说明
    lines.push('## 数据清理');
    lines.push('');
    lines.push('测试创建的数据将保留在系统中供验证。如需清理，请：');
    lines.push('');
    lines.push('1. **手动清理**: 在系统 UI 中逐个删除上述资源');
    lines.push('2. **脚本清理**: 运行清理脚本（如提供）');
    lines.push('3. **数据库清理**: 直接在数据库中删除测试数据');
    lines.push('');
    lines.push('> ⚠️ **注意**: 清理前请确认数据不再需要！');
    lines.push('');

    // API 端点参考
    lines.push('## API 端点参考');
    lines.push('');
    lines.push('可以通过以下 API 端点验证资源：');
    lines.push('');
    lines.push('```bash');
    lines.push('# 获取数据源列表');
    lines.push(`curl -H "Authorization: Bearer <token>" ${this.state.testInfo.baseUrl}/api/v1/datasources`);
    lines.push('');
    lines.push('# 获取 Agents 列表');
    lines.push(`curl -H "Authorization: Bearer <token>" ${this.state.testInfo.baseUrl}/api/v1/agents`);
    lines.push('');
    lines.push('# 获取模型列表');
    lines.push(`curl -H "Authorization: Bearer <token>" ${this.state.testInfo.baseUrl}/api/v1/models`);
    lines.push('```');
    lines.push('');

    return lines.join('\n');
  }

  /**
   * 保存验证指南到文件
   */
  async saveVerificationGuide(): Promise<string> {
    const dir = join(process.cwd(), 'test-results');
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
    }

    const guide = this.generateVerificationGuide();
    writeFileSync(this.verificationGuidePath, guide, 'utf-8');
    logger.info(`[TestDataPersistence] Verification guide saved to: ${this.verificationGuidePath}`);

    return this.verificationGuidePath;
  }

  /**
   * 生成清理脚本
   */
  generateCleanupScript(): string {
    const lines: string[] = [];

    lines.push('#!/bin/bash');
    lines.push('# ONE-DATA-STUDIO E2E 测试数据清理脚本');
    lines.push('');
    lines.push('# 使用方法:');
    lines.push('#   1. 设置 API_TOKEN 环境变量');
    lines.push('#   2. 设置 BASE_URL 环境变量（默认: http://localhost:3000）');
    lines.push('#   3. 运行: bash scripts/cleanup-test-data.sh');
    lines.push('');
    lines.push('set -e');
    lines.push('');
    lines.push(`BASE_URL="${process.env.BASE_URL || 'http://localhost:3000'}"`);
    lines.push('API_TOKEN="${API_TOKEN}"');
    lines.push('');
    lines.push('if [ -z "$API_TOKEN" ]; then');
    lines.push('  echo "错误: 请设置 API_TOKEN 环境变量"');
    lines.push('  exit 1');
    lines.push('fi');
    lines.push('');
    lines.push('echo "开始清理测试数据..."');
    lines.push('');

    // 清理 ETL 任务
    if (Object.keys(this.state.etlTasks).length > 0) {
      lines.push('# 清理 ETL 任务');
      for (const [key, task] of Object.entries(this.state.etlTasks)) {
        if (task.id) {
          lines.push(`echo "删除 ETL 任务: ${task.name}"`);
          lines.push(`curl -X DELETE -H "Authorization: Bearer $API_TOKEN" "$BASE_URL/api/v1/etl/tasks/${task.id}" || true`);
          lines.push('');
        }
      }
    }

    // 清理质量规则
    if (Object.keys(this.state.qualityRules).length > 0) {
      lines.push('# 清理质量规则');
      for (const [key, rule] of Object.entries(this.state.qualityRules)) {
        if (rule.id) {
          lines.push(`echo "删除质量规则: ${rule.name}"`);
          lines.push(`curl -X DELETE -H "Authorization: Bearer $API_TOKEN" "$BASE_URL/api/v1/quality/rules/${rule.id}" || true`);
          lines.push('');
        }
      }
    }

    // 清理工作流
    if (Object.keys(this.state.workflows).length > 0) {
      lines.push('# 清理工作流');
      for (const [key, workflow] of Object.entries(this.state.workflows)) {
        if (workflow.id) {
          lines.push(`echo "删除工作流: ${workflow.name}"`);
          lines.push(`curl -X DELETE -H "Authorization: Bearer $API_TOKEN" "$BASE_URL/api/v1/workflows/${workflow.id}" || true`);
          lines.push('');
        }
      }
    }

    // 清理 Agents
    if (Object.keys(this.state.agents).length > 0) {
      lines.push('# 清理 Agents');
      for (const [key, agent] of Object.entries(this.state.agents)) {
        if (agent.id) {
          lines.push(`echo "删除 Agent: ${agent.name}"`);
          lines.push(`curl -X DELETE -H "Authorization: Bearer $API_TOKEN" "$BASE_URL/api/v1/agents/${agent.id}" || true`);
          lines.push('');
        }
      }
    }

    // 清理数据集
    if (Object.keys(this.state.datasets).length > 0) {
      lines.push('# 清理数据集');
      for (const [key, dataset] of Object.entries(this.state.datasets)) {
        if (dataset.id) {
          lines.push(`echo "删除数据集: ${dataset.name}"`);
          lines.push(`curl -X DELETE -H "Authorization: Bearer $API_TOKEN" "$BASE_URL/api/v1/datasets/${dataset.id}" || true`);
          lines.push('');
        }
      }
    }

    // 清理数据源
    if (Object.keys(this.state.datasources).length > 0) {
      lines.push('# 清理数据源');
      for (const [key, ds] of Object.entries(this.state.datasources)) {
        if (ds.id) {
          lines.push(`echo "删除数据源: ${ds.name}"`);
          lines.push(`curl -X DELETE -H "Authorization: Bearer $API_TOKEN" "$BASE_URL/api/v1/datasources/${ds.id}" || true`);
          lines.push('');
        }
      }
    }

    // 清理模型
    if (Object.keys(this.state.models).length > 0) {
      lines.push('# 清理模型');
      for (const [key, model] of Object.entries(this.state.models)) {
        if (model.id) {
          lines.push(`echo "删除模型: ${model.name}"`);
          lines.push(`curl -X DELETE -H "Authorization: Bearer $API_TOKEN" "$BASE_URL/api/v1/models/${model.id}" || true`);
          lines.push('');
        }
      }
    }

    // 清理 Notebooks
    if (Object.keys(this.state.notebooks).length > 0) {
      lines.push('# 清理 Notebooks');
      for (const [key, notebook] of Object.entries(this.state.notebooks)) {
        if (notebook.id) {
          lines.push(`echo "删除 Notebook: ${notebook.name}"`);
          lines.push(`curl -X DELETE -H "Authorization: Bearer $API_TOKEN" "$BASE_URL/api/v1/notebooks/${notebook.id}" || true`);
          lines.push('');
        }
      }
    }

    // 清理实验
    if (Object.keys(this.state.experiments).length > 0) {
      lines.push('# 清理实验');
      for (const [key, exp] of Object.entries(this.state.experiments)) {
        if (exp.id) {
          lines.push(`echo "删除实验: ${exp.name}"`);
          lines.push(`curl -X DELETE -H "Authorization: Bearer $API_TOKEN" "$BASE_URL/api/v1/experiments/${exp.id}" || true`);
          lines.push('');
        }
      }
    }

    // 清理文档
    if (Object.keys(this.state.documents).length > 0) {
      lines.push('# 清理文档');
      for (const [key, doc] of Object.entries(this.state.documents)) {
        if (doc.id) {
          lines.push(`echo "删除文档: ${doc.name}"`);
          lines.push(`curl -X DELETE -H "Authorization: Bearer $API_TOKEN" "$BASE_URL/api/v1/documents/${doc.id}" || true`);
          lines.push('');
        }
      }
    }

    lines.push('echo "测试数据清理完成！"');

    return lines.join('\n');
  }

  /**
   * 保存清理脚本
   */
  async saveCleanupScript(): Promise<string> {
    const dir = join(process.cwd(), 'scripts');
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
    }

    const script = this.generateCleanupScript();
    writeFileSync(CLEANUP_SCRIPT_PATH, script, 'utf-8');
    logger.info(`[TestDataPersistence] Cleanup script saved to: ${CLEANUP_SCRIPT_PATH}`);

    return CLEANUP_SCRIPT_PATH;
  }

  /**
   * 打印摘要
   */
  printSummary(): void {
    logger.info('\n' + '='.repeat(60));
    logger.info('Test Data Summary');
    logger.info('='.repeat(60));
    logger.info(`Test ID: ${this.state.testInfo.testId}`);
    logger.info(`Test Name: ${this.state.testInfo.testName}`);
    logger.info(`Base URL: ${this.state.testInfo.baseUrl}`);
    logger.info('');
    logger.info('Created Resources:');
    logger.info(`  Users: ${Object.keys(this.state.users).length}`);
    logger.info(`  Datasources: ${Object.keys(this.state.datasources).length}`);
    logger.info(`  Datasets: ${Object.keys(this.state.datasets).length}`);
    logger.info(`  Agents: ${Object.keys(this.state.agents).length}`);
    logger.info(`  Workflows: ${Object.keys(this.state.workflows).length}`);
    logger.info(`  Models: ${Object.keys(this.state.models).length}`);
    logger.info(`  Notebooks: ${Object.keys(this.state.notebooks).length}`);
    logger.info(`  Experiments: ${Object.keys(this.state.experiments).length}`);
    logger.info(`  Documents: ${Object.keys(this.state.documents).length}`);
    logger.info(`  Quality Rules: ${Object.keys(this.state.qualityRules).length}`);
    logger.info(`  ETL Tasks: ${Object.keys(this.state.etlTasks).length}`);
    logger.info(`  Features: ${Object.keys(this.state.features).length}`);
    logger.info(`  Standards: ${Object.keys(this.state.standards).length}`);
    logger.info(`  Assets: ${Object.keys(this.state.assets).length}`);
    logger.info('='.repeat(60));
  }
}

// ============================================================================
// Factory Function
// ============================================================================

/**
 * 创建测试数据持久化管理器
 */
export function createTestDataPersistence(
  testId?: string,
  testName?: string,
  stateFilePath?: string,
  verificationGuidePath?: string
): TestDataPersistence {
  const id = testId || `test_${Date.now()}`;
  const name = testName || 'Full Platform E2E Test';
  return new TestDataPersistence(id, name, stateFilePath, verificationGuidePath);
}
