/**
 * 测试数据配置
 * 定义每个页面操作所需的测试数据
 */

// ==================== 类型定义 ====================

export interface TestData {
  [key: string]: any;
}

export interface TestDataSource {
  name: string;
  type: string;
  host: string;
  port: number;
  database: string;
  username: string;
  password: string;
  [key: string]: any;
}

export interface TestUser {
  username: string;
  email: string;
  password: string;
  roles: string[];
  real_name?: string;
  department?: string;
}

export interface TestETLTask {
  name: string;
  source_type: string;
  target_type: string;
  schedule?: string;
  description?: string;
  config?: any;
}

export interface TestWorkflow {
  name: string;
  description: string;
  nodes: any[];
  edges: any[];
}

export interface TestPrompt {
  name: string;
  content: string;
  model: string;
  temperature?: number;
  max_tokens?: number;
}

export interface TestKnowledge {
  name: string;
  type: string;
  description?: string;
}

export interface TestNotebook {
  name: string;
  kernel?: string;
  description?: string;
}

export interface TestExperiment {
  name: string;
  project_id?: string;
  description?: string;
}

export interface TestModel {
  name: string;
  version: string;
  framework: string;
  description?: string;
}

// ==================== 测试数据配置 ====================

/**
 * 获取时间戳后缀，确保测试数据唯一性
 */
function getTimestamp(): string {
  return Date.now().toString();
}

function getRandomSuffix(): string {
  return Math.floor(Math.random() * 10000).toString();
}

/**
 * 测试数据前缀标识
 */
export const TEST_PREFIX = 'E2E测试';
export const TEST_PREFIX_EN = 'e2e_test_';

/**
 * 所有测试数据配置
 */
export const TEST_DATA = {
  // ==================== 数据源测试数据 ====================
  datasource: {
    mysql: {
      name: `${TEST_PREFIX}数据源_${getTimestamp()}`,
      type: 'mysql',
      host: 'localhost',
      port: 3306,
      database: 'test_db',
      username: 'test_user',
      password: 'test_pass',
      charset: 'utf8mb4',
    } as TestDataSource,
    postgresql: {
      name: `${TEST_PREFIX}PostgreSQL数据源_${getTimestamp()}`,
      type: 'postgresql',
      host: 'localhost',
      port: 5432,
      database: 'test_db',
      username: 'test_user',
      password: 'test_pass',
    } as TestDataSource,
    clickhouse: {
      name: `${TEST_PREFIX}ClickHouse数据源_${getTimestamp()}`,
      type: 'clickhouse',
      host: 'localhost',
      port: 8123,
      database: 'test_db',
      username: 'default',
      password: '',
    } as TestDataSource,
    mongodb: {
      name: `${TEST_PREFIX}MongoDB数据源_${getTimestamp()}`,
      type: 'mongodb',
      host: 'localhost',
      port: 27017,
      database: 'test_db',
      username: 'test_user',
      password: 'test_pass',
    } as TestDataSource,
    kafka: {
      name: `${TEST_PREFIX}Kafka数据源_${getTimestamp()}`,
      type: 'kafka',
      host: 'localhost',
      port: 9092,
      database: 'test_topic',
      username: '',
      password: '',
    } as TestDataSource,
  },

  // ==================== 用户测试数据 ====================
  user: {
    admin: {
      username: `${TEST_PREFIX_EN}admin_${getTimestamp()}`,
      email: `e2e_admin_${getTimestamp()}@test.local`,
      password: 'Admin1234!',
      roles: ['system_admin'],
      real_name: `${TEST_PREFIX}管理员`,
      department: '技术部',
    } as TestUser,
    data_admin: {
      username: `${TEST_PREFIX_EN}da_${getTimestamp()}`,
      email: `e2e_da_${getTimestamp()}@test.local`,
      password: 'Da1234!',
      roles: ['data_admin'],
      real_name: `${TEST_PREFIX}数据管理员`,
      department: '数据部',
    } as TestUser,
    data_engineer: {
      username: `${TEST_PREFIX_EN}de_${getTimestamp()}`,
      email: `e2e_de_${getTimestamp()}@test.local`,
      password: 'De1234!',
      roles: ['data_engineer'],
      real_name: `${TEST_PREFIX}数据工程师`,
      department: '数据部',
    } as TestUser,
    algorithm_engineer: {
      username: `${TEST_PREFIX_EN}ae_${getTimestamp()}`,
      email: `e2e_ae_${getTimestamp()}@test.local`,
      password: 'Ae1234!',
      roles: ['algorithm_engineer'],
      real_name: `${TEST_PREFIX}算法工程师`,
      department: '算法部',
    } as TestUser,
    business_user: {
      username: `${TEST_PREFIX_EN}bu_${getTimestamp()}`,
      email: `e2e_bu_${getTimestamp()}@test.local`,
      password: 'Bu1234!',
      roles: ['business_user'],
      real_name: `${TEST_PREFIX}业务用户`,
      department: '业务部',
    } as TestUser,
  },

  // ==================== ETL 任务测试数据 ====================
  etl: {
    mysql_to_clickhouse: {
      name: `${TEST_PREFIX}ETL任务_${getTimestamp()}`,
      source_type: 'mysql',
      target_type: 'clickhouse',
      schedule: '0 2 * * *',
      description: 'E2E测试创建的ETL任务',
      config: {
        batch_size: 10000,
        parallel: 2,
      },
    } as TestETLTask,
    postgresql_to_mysql: {
      name: `${TEST_PREFIX}PG到MySQL同步_${getTimestamp()}`,
      source_type: 'postgresql',
      target_type: 'mysql',
      schedule: '0 */4 * * *',
      description: 'PostgreSQL到MySQL的数据同步任务',
    } as TestETLTask,
    realtime: {
      name: `${TEST_PREFIX}实时同步任务_${getTimestamp()}`,
      source_type: 'kafka',
      target_type: 'clickhouse',
      description: '实时数据同步任务',
    } as TestETLTask,
  },

  // ==================== 工作流测试数据 ====================
  workflow: {
    simple: {
      name: `${TEST_PREFIX}简单工作流_${getTimestamp()}`,
      description: 'E2E测试创建的简单工作流',
      nodes: [
        { id: 'node1', type: 'start', name: '开始' },
        { id: 'node2', type: 'task', name: '数据处理' },
        { id: 'node3', type: 'end', name: '结束' },
      ],
      edges: [
        { source: 'node1', target: 'node2' },
        { source: 'node2', target: 'node3' },
      ],
    } as TestWorkflow,
    complex: {
      name: `${TEST_PREFIX}复杂工作流_${getTimestamp()}`,
      description: '包含分支和条件的复杂工作流',
      nodes: [],
      edges: [],
    } as TestWorkflow,
  },

  // ==================== Prompt 测试数据 ====================
  prompt: {
    chat: {
      name: `${TEST_PREFIX}对话Prompt_${getTimestamp()}`,
      content: '你是一个智能数据助手，可以帮助用户分析数据和生成SQL查询。',
      model: 'gpt-4',
      temperature: 0.7,
      max_tokens: 2000,
    } as TestPrompt,
    sql_generation: {
      name: `${TEST_PREFIX}SQL生成Prompt_${getTimestamp()}`,
      content: '根据用户的自然语言描述，生成对应的SQL查询语句。',
      model: 'gpt-3.5-turbo',
      temperature: 0.3,
      max_tokens: 1000,
    } as TestPrompt,
  },

  // ==================== 知识库测试数据 ====================
  knowledge: {
    document: {
      name: `${TEST_PREFIX}文档知识库_${getTimestamp()}`,
      type: 'document',
      description: '用于文档管理和检索的知识库',
    } as TestKnowledge,
    faq: {
      name: `${TEST_PREFIX}FAQ知识库_${getTimestamp()}`,
      type: 'faq',
      description: '常见问题知识库',
    } as TestKnowledge,
    table: {
      name: `${TEST_PREFIX}表结构知识库_${getTimestamp()}`,
      type: 'table_schema',
      description: '数据库表结构知识库',
    } as TestKnowledge,
  },

  // ==================== Notebook 测试数据 ====================
  notebook: {
    python: {
      name: `${TEST_PREFIX}Python Notebook_${getTimestamp()}`,
      kernel: 'python3',
      description: 'Python数据分析Notebook',
    } as TestNotebook,
    scala: {
      name: `${TEST_PREFIX}Scala Notebook_${getTimestamp()}`,
      kernel: 'scala',
      description: 'Scala大数据处理Notebook',
    } as TestNotebook,
    sql: {
      name: `${TEST_PREFIX}SQL Notebook_${getTimestamp()}`,
      kernel: 'sql',
      description: 'SQL查询Notebook',
    } as TestNotebook,
  },

  // ==================== 实验测试数据 ====================
  experiment: {
    classification: {
      name: `${TEST_PREFIX}分类实验_${getTimestamp()}`,
      description: '用户行为分类实验',
    } as TestExperiment,
    regression: {
      name: `${TEST_PREFIX}回归实验_${getTimestamp()}`,
      description: '销量预测回归实验',
    } as TestExperiment,
  },

  // ==================== 模型测试数据 ====================
  model: {
    sklearn: {
      name: `${TEST_PREFIX}Sklearn模型_${getTimestamp()}`,
      version: '1.0.0',
      framework: 'sklearn',
      description: '基于Scikit-learn的分类模型',
    } as TestModel,
    tensorflow: {
      name: `${TEST_PREFIX}TensorFlow模型_${getTimestamp()}`,
      version: '1.0.0',
      framework: 'tensorflow',
      description: '基于TensorFlow的深度学习模型',
    } as TestModel,
    pytorch: {
      name: `${TEST_PREFIX}PyTorch模型_${getTimestamp()}`,
      version: '1.0.0',
      framework: 'pytorch',
      description: '基于PyTorch的神经网络模型',
    } as TestModel,
  },

  // ==================== 数据质量规则测试数据 ====================
  quality_rule: {
    not_null: {
      name: `${TEST_PREFIX}非空检查_${getTimestamp()}`,
      rule_type: 'not_null',
      description: '字段非空校验规则',
      config: {
        column: 'user_id',
        table: 'users',
      },
    },
    range: {
      name: `${TEST_PREFIX}范围检查_${getTimestamp()}`,
      rule_type: 'range',
      description: '数值范围校验规则',
      config: {
        column: 'amount',
        table: 'orders',
        min: 0,
        max: 1000000,
      },
    },
    uniqueness: {
      name: `${TEST_PREFIX}唯一性检查_${getTimestamp()}`,
      rule_type: 'uniqueness',
      description: '字段唯一性校验规则',
      config: {
        column: 'email',
        table: 'users',
      },
    },
  },

  // ==================== 数据集测试数据 ====================
  dataset: {
    table: {
      name: `${TEST_PREFIX}表数据集_${getTimestamp()}`,
      type: 'table',
      description: '数据库表数据集',
    },
    file: {
      name: `${TEST_PREFIX}文件数据集_${getTimestamp()}`,
      type: 'file',
      description: '文件上传数据集',
    },
    query: {
      name: `${TEST_PREFIX}查询数据集_${getTimestamp()}`,
      type: 'query',
      description: 'SQL查询结果数据集',
    },
  },

  // ==================== 特征存储测试数据 ====================
  feature: {
    user_feature: {
      name: `${TEST_PREFIX}用户特征_${getTimestamp()}`,
      description: '用户行为特征集合',
      feature_type: 'user',
    },
    item_feature: {
      name: `${TEST_PREFIX}商品特征_${getTimestamp()}`,
      description: '商品属性特征集合',
      feature_type: 'item',
    },
  },

  // ==================== 调度任务测试数据 ====================
  schedule: {
    daily: {
      name: `${TEST_PREFIX}日结调度_${getTimestamp()}`,
      cron: '0 2 * * *',
      description: '每天凌晨2点执行',
    },
    hourly: {
      name: `${TEST_PREFIX}小时调度_${getTimestamp()}`,
      cron: '0 * * * *',
      description: '每小时整点执行',
    },
    weekly: {
      name: `${TEST_PREFIX}周调度_${getTimestamp()}`,
      cron: '0 2 * * 1',
      description: '每周一凌晨2点执行',
    },
  },

  // ==================== 告警规则测试数据 ====================
  alert_rule: {
    etl_failed: {
      name: `${TEST_PREFIX}ETL失败告警_${getTimestamp()}`,
      level: 'critical',
      description: 'ETL任务失败时发送告警',
      config: {
        condition: 'etl_status == failed',
        notify_channels: ['email', 'dingtalk'],
      },
    },
    quality_issue: {
      name: `${TEST_PREFIX}质量异常告警_${getTimestamp()}`,
      level: 'warning',
      description: '数据质量检查失败时发送告警',
      config: {
        condition: 'quality_score < 80',
        notify_channels: ['email'],
      },
    },
  },

  // ==================== Agent 应用测试数据 ====================
  agent: {
    chatbot: {
      name: `${TEST_PREFIX}聊天机器人_${getTimestamp()}`,
      type: 'chatbot',
      description: '智能客服机器人',
    },
    analyst: {
      name: `${TEST_PREFIX}数据分析助手_${getTimestamp()}`,
      type: 'analyst',
      description: '数据分析师智能助手',
    },
  },
};

// ==================== 辅助函数 ====================

/**
 * 获取指定类型的测试数据
 */
export function getTestData(category: string, subCategory?: string): TestData {
  if (subCategory && TEST_DATA[category]?.[subCategory]) {
    return TEST_DATA[category][subCategory];
  }
  if (TEST_DATA[category]) {
    // 如果有子分类，返回第一个子分类
    const keys = Object.keys(TEST_DATA[category]);
    if (keys.length > 0) {
      return TEST_DATA[category][keys[0]];
    }
  }
  return {};
}

/**
 * 生成带时间戳的测试数据
 */
export function generateTestData(category: string, subCategory?: string): TestData {
  const base = getTestData(category, subCategory);
  const timestamp = getTimestamp();

  // 递归更新字符串中的时间戳占位符
  function updateTimestamp(obj: any): any {
    if (typeof obj === 'string') {
      return obj.replace(/\${timestamp}/g, timestamp).replace(/_\d+/g, `_${timestamp}`);
    }
    if (Array.isArray(obj)) {
      return obj.map(updateTimestamp);
    }
    if (obj && typeof obj === 'object') {
      const result: any = {};
      for (const key in obj) {
        result[key] = updateTimestamp(obj[key]);
      }
      return result;
    }
    return obj;
  }

  return updateTimestamp(base);
}

/**
 * 检查数据是否为测试数据
 */
export function isTestData(value: string): boolean {
  return value.startsWith(TEST_PREFIX) || value.startsWith(TEST_PREFIX_EN);
}

/**
 * 清理测试数据中的敏感信息
 */
export function sanitizeTestData(data: any): any {
  const sanitized = { ...data };
  if (sanitized.password) {
    sanitized.password = '***';
  }
  return sanitized;
}
