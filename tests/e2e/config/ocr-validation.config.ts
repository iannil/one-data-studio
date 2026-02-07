/**
 * OCR 验证测试配置
 * 定义所有页面的 OCR 验证规则和测试数据
 */

import { PageValidationConfig } from '../helpers/ocr-validator';
import { PageType } from '../helpers/data-ops-validator';

// ==================== 类型定义 ====================

/**
 * OCR 页面测试配置
 */
export interface OCRPageConfig {
  /** 页面名称 */
  name: string;
  /** 页面路由 */
  route: string;
  /** 页面类型 */
  type: PageType;
  /** 是否启用测试 */
  enabled: boolean;
  /** OCR 验证配置 */
  validation: PageValidationConfig;
  /** 测试超时时间（毫秒） */
  timeout?: number;
  /** 跳过原因 */
  skipReason?: string;
}

/**
 * OCR 操作配置
 */
export interface OCROperationConfig {
  /** 是否启用 */
  enabled: boolean;
  /** 操作按钮选择器 */
  buttonSelector?: string;
  /** 表单选择器 */
  formSelector?: string;
  /** 测试数据 */
  testData?: Record<string, unknown>;
  /** 成功提示文本 */
  successTexts?: string[];
}

/**
 * OCR CRUD 操作配置
 */
export interface OCRCrudOperations {
  /** 创建操作 */
  create?: OCROperationConfig;
  /** 读取操作 */
  read?: OCROperationConfig;
  /** 更新操作 */
  update?: OCROperationConfig;
  /** 删除操作 */
  delete?: OCROperationConfig;
}

// ==================== 默认验证配置 ====================

/**
 * 默认的页面验证配置
 */
export const DEFAULT_VALIDATION_CONFIG: Partial<PageValidationConfig> = {
  forbiddenTexts: [
    '错误',
    '失败',
    '异常',
    'error',
    'failed',
    'exception',
    '404 Not Found',
    '500 Internal Server Error',
    '403 Forbidden',
  ],
};

// ==================== 辅助函数 ====================

/**
 * 创建基础 OCR 页面配置
 */
function createOCRPageConfig(
  name: string,
  route: string,
  type: PageType,
  expectedTitle?: string,
  additionalOptions?: Partial<OCRPageConfig>
): OCRPageConfig {
  return {
    name,
    route,
    type,
    enabled: true,
    validation: {
      pageName: name,
      expectedTitle,
      ...DEFAULT_VALIDATION_CONFIG,
    },
    ...additionalOptions,
  };
}

// ==================== DataOps 数据治理模块 ====================

/**
 * DataOps 模块 OCR 页面配置
 */
export const DATA_OPS_OCR_PAGES: OCRPageConfig[] = [
  // 数据源管理
  createOCRPageConfig(
    '数据源管理',
    '/data/datasources',
    PageType.List,
    '数据源'
  ),

  // ETL 流程
  createOCRPageConfig(
    'ETL流程',
    '/data/etl',
    PageType.List,
    'ETL'
  ),

  // Kettle 引擎
  createOCRPageConfig(
    'Kettle引擎',
    '/data/kettle',
    PageType.Editor,
    'Kettle'
  ),

  // Kettle 配置生成
  createOCRPageConfig(
    'Kettle配置生成',
    '/data/kettle-generator',
    PageType.Form,
    'Kettle'
  ),

  // 数据质量
  createOCRPageConfig(
    '数据质量',
    '/data/quality',
    PageType.List,
    '数据质量'
  ),

  // 数据血缘
  createOCRPageConfig(
    '数据血缘',
    '/data/lineage',
    PageType.Visualization,
    '血缘'
  ),

  // 特征存储
  createOCRPageConfig(
    '特征存储',
    '/data/features',
    PageType.List,
    '特征'
  ),

  // 数据标准
  createOCRPageConfig(
    '数据标准',
    '/data/standards',
    PageType.List,
    '数据标准'
  ),

  // 数据资产
  createOCRPageConfig(
    '数据资产',
    '/data/assets',
    PageType.List,
    '数据资产'
  ),

  // 数据服务
  createOCRPageConfig(
    '数据服务',
    '/data/services',
    PageType.List,
    '数据服务'
  ),

  // BI 报表
  createOCRPageConfig(
    'BI报表',
    '/data/bi',
    PageType.Visualization,
    'BI'
  ),

  // 系统监控
  createOCRPageConfig(
    '系统监控',
    '/data/monitoring',
    PageType.Visualization,
    '监控'
  ),

  // 实时开发
  createOCRPageConfig(
    '实时开发',
    '/data/streaming',
    PageType.List,
    '实时'
  ),

  // 实时 IDE
  createOCRPageConfig(
    '实时IDE',
    '/data/streaming-ide',
    PageType.Editor,
    '实时IDE'
  ),

  // 离线开发
  createOCRPageConfig(
    '离线开发',
    '/data/offline',
    PageType.Editor,
    '离线开发'
  ),

  // 指标体系
  createOCRPageConfig(
    '指标体系',
    '/data/metrics',
    PageType.List,
    '指标'
  ),

  // 智能预警
  createOCRPageConfig(
    '智能预警',
    '/data/alerts',
    PageType.List,
    '预警'
  ),

  // 文档 OCR
  createOCRPageConfig(
    '文档OCR',
    '/data/ocr',
    PageType.List,
    'OCR'
  ),
];

// ==================== MLOps 模型管理模块 ====================

/**
 * MLOps 模块 OCR 页面配置
 */
export const ML_OPS_OCR_PAGES: OCRPageConfig[] = [
  // Notebook 开发
  createOCRPageConfig(
    'Notebook开发',
    '/model/notebooks',
    PageType.List,
    'Notebook'
  ),

  // 实验管理
  createOCRPageConfig(
    '实验管理',
    '/model/experiments',
    PageType.List,
    '实验'
  ),

  // 模型管理
  createOCRPageConfig(
    '模型管理',
    '/model/models',
    PageType.List,
    '模型'
  ),

  // 模型训练
  createOCRPageConfig(
    '模型训练',
    '/model/training',
    PageType.List,
    '训练'
  ),

  // 模型服务
  createOCRPageConfig(
    '模型服务',
    '/model/serving',
    PageType.List,
    '服务'
  ),

  // 资源管理
  createOCRPageConfig(
    '资源管理',
    '/model/resources',
    PageType.Visualization,
    '资源'
  ),

  // 模型监控
  createOCRPageConfig(
    '模型监控',
    '/model/monitoring',
    PageType.Visualization,
    '监控'
  ),

  // AI Hub
  createOCRPageConfig(
    'AI Hub',
    '/model/aihub',
    PageType.List,
    'AI Hub'
  ),

  // 模型流水线
  createOCRPageConfig(
    '模型流水线',
    '/model/pipelines',
    PageType.Visualization,
    '流水线'
  ),

  // LLM 微调
  createOCRPageConfig(
    'LLM微调',
    '/model/llm-tuning',
    PageType.Form,
    '微调'
  ),

  // SQL Lab
  createOCRPageConfig(
    'SQL Lab',
    '/model/sql-lab',
    PageType.Editor,
    'SQL Lab'
  ),
];

// ==================== LLMOps Agent 平台模块 ====================

/**
 * LLMOps 模块 OCR 页面配置
 */
export const AGENT_OCR_PAGES: OCRPageConfig[] = [
  // Prompt 管理
  createOCRPageConfig(
    'Prompt管理',
    '/agent-platform/prompts',
    PageType.List,
    'Prompt'
  ),

  // 知识库管理
  createOCRPageConfig(
    '知识库管理',
    '/agent-platform/knowledge',
    PageType.List,
    '知识库'
  ),

  // Agent 应用
  createOCRPageConfig(
    'Agent应用',
    '/agent-platform/apps',
    PageType.List,
    '应用'
  ),

  // 效果评估
  createOCRPageConfig(
    '效果评估',
    '/agent-platform/evaluation',
    PageType.Visualization,
    '评估'
  ),

  // SFT 训练
  createOCRPageConfig(
    'SFT训练',
    '/agent-platform/sft',
    PageType.Form,
    'SFT'
  ),
];

// ==================== 工作流管理模块 ====================

/**
 * 工作流模块 OCR 页面配置
 */
export const WORKFLOW_OCR_PAGES: OCRPageConfig[] = [
  // 工作流列表
  createOCRPageConfig(
    '工作流列表',
    '/workflows',
    PageType.List,
    '工作流'
  ),

  // 新建工作流
  createOCRPageConfig(
    '新建工作流',
    '/workflows/new',
    PageType.Editor,
    '工作流编辑'
  ),

  // 执行监控
  createOCRPageConfig(
    '执行监控',
    '/executions',
    PageType.List,
    '执行'
  ),

  // Text2SQL
  createOCRPageConfig(
    'Text2SQL',
    '/text2sql',
    PageType.Editor,
    'Text2SQL'
  ),
];

// ==================== 元数据管理模块 ====================

/**
 * 元数据模块 OCR 页面配置
 */
export const METADATA_OCR_PAGES: OCRPageConfig[] = [
  // 元数据查询
  createOCRPageConfig(
    '元数据查询',
    '/metadata',
    PageType.List,
    '元数据'
  ),

  // 元数据图谱
  createOCRPageConfig(
    '元数据图谱',
    '/metadata/graph',
    PageType.Visualization,
    '图谱'
  ),

  // 版本对比
  createOCRPageConfig(
    '版本对比',
    '/metadata/version-diff',
    PageType.Visualization,
    '版本对比'
  ),
];

// ==================== 管理后台模块 ====================

/**
 * 管理后台模块 OCR 页面配置
 */
export const ADMIN_OCR_PAGES: OCRPageConfig[] = [
  // 用户管理
  createOCRPageConfig(
    '用户管理',
    '/admin/users',
    PageType.List,
    '用户'
  ),

  // 角色管理
  createOCRPageConfig(
    '角色管理',
    '/admin/roles',
    PageType.List,
    '角色'
  ),

  // 权限管理
  createOCRPageConfig(
    '权限管理',
    '/admin/permissions',
    PageType.Visualization,
    '权限'
  ),

  // 系统设置
  createOCRPageConfig(
    '系统设置',
    '/admin/settings',
    PageType.Form,
    '设置'
  ),

  // 审计日志
  createOCRPageConfig(
    '审计日志',
    '/admin/audit',
    PageType.List,
    '审计'
  ),

  // 分组管理
  createOCRPageConfig(
    '分组管理',
    '/admin/groups',
    PageType.List,
    '分组'
  ),

  // 成本报告
  createOCRPageConfig(
    '成本报告',
    '/admin/cost-report',
    PageType.Visualization,
    '成本'
  ),

  // 通知管理
  createOCRPageConfig(
    '通知管理',
    '/admin/notifications',
    PageType.Form,
    '通知'
  ),

  // 内容管理
  createOCRPageConfig(
    '内容管理',
    '/admin/content',
    PageType.Form,
    '内容'
  ),

  // 用户画像
  createOCRPageConfig(
    '用户画像',
    '/admin/user-profiles',
    PageType.Visualization,
    '画像'
  ),

  // 用户分群
  createOCRPageConfig(
    '用户分群',
    '/admin/user-segments',
    PageType.List,
    '分群'
  ),

  // API 测试器
  createOCRPageConfig(
    'API测试器',
    '/admin/api-tester',
    PageType.Form,
    'API测试'
  ),

  // 行为分析
  createOCRPageConfig(
    '行为分析',
    '/admin/behavior',
    PageType.Visualization,
    '行为分析'
  ),
];

// ==================== 门户模块 ====================

/**
 * 门户模块 OCR 页面配置
 */
export const PORTAL_OCR_PAGES: OCRPageConfig[] = [
  // 门户仪表板
  createOCRPageConfig(
    '门户仪表板',
    '/portal/dashboard',
    PageType.Visualization,
    '仪表板'
  ),

  // 通知中心
  createOCRPageConfig(
    '通知中心',
    '/portal/notifications',
    PageType.List,
    '通知'
  ),

  // 待办事项
  createOCRPageConfig(
    '待办事项',
    '/portal/todos',
    PageType.List,
    '待办'
  ),

  // 公告管理
  createOCRPageConfig(
    '公告管理',
    '/portal/announcements',
    PageType.List,
    '公告'
  ),

  // 个人中心
  createOCRPageConfig(
    '个人中心',
    '/portal/profile',
    PageType.Form,
    '个人'
  ),
];

// ==================== 通用模块 ====================

/**
 * 通用模块 OCR 页面配置
 */
export const COMMON_OCR_PAGES: OCRPageConfig[] = [
  // 数据集管理
  createOCRPageConfig(
    '数据集管理',
    '/datasets',
    PageType.List,
    '数据集'
  ),

  // 文档管理
  createOCRPageConfig(
    '文档管理',
    '/documents',
    PageType.List,
    '文档'
  ),

  // 调度管理
  createOCRPageConfig(
    '调度管理',
    '/schedules',
    PageType.List,
    '调度'
  ),

  // 智能调度
  createOCRPageConfig(
    '智能调度',
    '/scheduler/smart',
    PageType.Visualization,
    '智能调度'
  ),

  // Agents 列表
  createOCRPageConfig(
    'Agents列表',
    '/agents',
    PageType.List,
    'Agent'
  ),
];

// ==================== 汇总所有配置 ====================

/**
 * 所有 OCR 页面配置
 */
export const ALL_OCR_PAGES: OCRPageConfig[] = [
  ...DATA_OPS_OCR_PAGES,
  ...ML_OPS_OCR_PAGES,
  ...AGENT_OCR_PAGES,
  ...WORKFLOW_OCR_PAGES,
  ...METADATA_OCR_PAGES,
  ...ADMIN_OCR_PAGES,
  ...PORTAL_OCR_PAGES,
  ...COMMON_OCR_PAGES,
];

/**
 * 获取启用的 OCR 页面配置
 */
export function getEnabledOCRPages(): OCRPageConfig[] {
  return ALL_OCR_PAGES.filter(page => page.enabled);
}

/**
 * 按模块分组 OCR 页面配置
 */
export function getOCRPagesByModule(): Record<string, OCRPageConfig[]> {
  const grouped: Record<string, OCRPageConfig[]> = {
    data: DATA_OPS_OCR_PAGES.filter(p => p.enabled),
    model: ML_OPS_OCR_PAGES.filter(p => p.enabled),
    agent: AGENT_OCR_PAGES.filter(p => p.enabled),
    workflow: WORKFLOW_OCR_PAGES.filter(p => p.enabled),
    metadata: METADATA_OCR_PAGES.filter(p => p.enabled),
    admin: ADMIN_OCR_PAGES.filter(p => p.enabled),
    portal: PORTAL_OCR_PAGES.filter(p => p.enabled),
    common: COMMON_OCR_PAGES.filter(p => p.enabled),
  };
  return grouped;
}

/**
 * 按 URL 获取页面配置
 */
export function getOCRPageByRoute(route: string): OCRPageConfig | undefined {
  return ALL_OCR_PAGES.find(page => page.route === route);
}

/**
 * 获取 OCR 页面统计信息
 */
export function getOCRPageStats(): {
  total: number;
  enabled: number;
  byModule: Record<string, number>;
  byType: Record<PageType, number>;
} {
  const enabledPages = getEnabledOCRPages();

  const byModule: Record<string, number> = {};
  for (const page of enabledPages) {
    const module = page.route.split('/')[1];
    byModule[module] = (byModule[module] ?? 0) + 1;
  }

  const byType: Record<PageType, number> = {
    [PageType.List]: 0,
    [PageType.Editor]: 0,
    [PageType.Visualization]: 0,
    [PageType.Form]: 0,
    [PageType.Generic]: 0,
  };
  for (const page of enabledPages) {
    byType[page.type]++;
  }

  return {
    total: ALL_OCR_PAGES.length,
    enabled: enabledPages.length,
    byModule,
    byType,
  };
}

// ==================== 测试运行配置 ====================

/**
 * OCR 验证测试运行配置
 */
export const OCR_TEST_CONFIG = {
  /** 并发测试数量 */
  concurrency: 1,

  /** 单个页面超时时间（毫秒） */
  pageTimeout: 60000,

  /** 是否在失败时继续测试 */
  continueOnFailure: true,

  /** 是否生成详细报告 */
  generateDetailedReport: true,

  /** 报告保存目录 */
  reportDir: 'test-results/ocr-validation',

  /** 截图保存目录 */
  screenshotDir: 'test-results/ocr-validation/screenshots',

  /** OCR 服务 URL */
  ocrServiceUrl: process.env.OCR_SERVICE_URL ?? 'http://localhost:8007',

  /** OCR 服务就绪等待时间（毫秒） */
  ocrServiceReadyTimeout: 60000,

  /** 是否跳过 OCR 服务检查 */
  skipOCRServiceCheck: true, // 默认跳过，OCR 服务有数据库模型问题需要修复
};
