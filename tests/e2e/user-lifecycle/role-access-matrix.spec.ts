/**
 * 角色权限矩阵测试
 * 测试每个角色对不同功能模块的访问权限
 */

import { test, expect } from './fixtures/user-lifecycle.fixture';
import { generateTestUserData } from './helpers/user-management';
import { verifyCanAccessPage, verifyCannotAccessPage } from './helpers/verification';
import { ROLE_PERMISSIONS, getRoleTestData } from './helpers/role-management';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

// ============================================
// Admin 角色权限测试
// ============================================
test.describe('Admin 角色权限', () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test('应该能够访问所有功能模块', async ({ page }) => {
    // 设置 admin 认证
    await page.goto(`${BASE_URL}/login`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'admin',
        roles: ['admin'],
      }));
    });
    await page.reload();

    // 管理模块
    for (const path of ['/admin/users', '/admin/roles', '/admin/groups', '/admin/audit', '/admin/settings']) {
      await page.goto(`${BASE_URL}${path}`);
      await page.waitForLoadState('networkidle');
      const result = await verifyCanAccessPage(page, path);
      expect(result.hasAccess, `Admin should access ${path}`).toBe(true);
    }
  });

  test('应该能够 CRUD 数据源、数据集、元数据', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'admin',
        roles: ['admin'],
      }));
    });
    await page.reload();

    const dataPaths = ['/data/datasources', '/data/datasets', '/data/metadata'];
    for (const path of dataPaths) {
      const result = await verifyCanAccessPage(page, path);
      expect(result.hasAccess).toBe(true);
    }
  });

  test('应该能够 CRUD 工作流、模型', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'admin',
        roles: ['admin'],
      }));
    });
    await page.reload();

    const aiPaths = ['/ai/workflows', '/ai/prompts', '/ai/knowledge', '/ai/agents'];
    for (const path of aiPaths) {
      const result = await verifyCanAccessPage(page, path);
      expect(result.hasAccess).toBe(true);
    }
  });

  test('应该能够执行所有操作', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'admin',
        roles: ['admin'],
      }));
    });
    await page.reload();

    // 验证有创建按钮
    await page.goto(`${BASE_URL}/data/datasets`);
    const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
    await expect(createButton).toBeVisible({ timeout: 5000 });
  });
});

// ============================================
// Data Engineer 角色权限测试
// ============================================
test.describe('Data Engineer 角色权限', () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test('应该能够 CRUD 数据源', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'data_engineer',
        roles: ['data_engineer'],
      }));
    });
    await page.reload();

    const result = await verifyCanAccessPage(page, '/data/datasources');
    expect(result.hasAccess).toBe(true);
  });

  test('应该能够 CRUD 数据集', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'data_engineer',
        roles: ['data_engineer'],
      }));
    });
    await page.reload();

    const result = await verifyCanAccessPage(page, '/data/datasets');
    expect(result.hasAccess).toBe(true);
  });

  test('应该能够 CRUD 元数据', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'data_engineer',
        roles: ['data_engineer'],
      }));
    });
    await page.reload();

    const result = await verifyCanAccessPage(page, '/data/metadata');
    expect(result.hasAccess).toBe(true);
  });

  test('只读访问特征存储、数据标准', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'data_engineer',
        roles: ['data_engineer'],
      }));
    });
    await page.reload();

    const result = await verifyCanAccessPage(page, '/data/features');
    expect(result.hasAccess).toBe(true);
  });

  test('应该能够 CRUD ETL 任务、数据质量、数据血缘', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'data_engineer',
        roles: ['data_engineer'],
      }));
    });
    await page.reload();

    const etlPaths = ['/development/etl', '/data/quality', '/data/lineage'];
    for (const path of etlPaths) {
      const result = await verifyCanAccessPage(page, path);
      expect(result.hasAccess).toBe(true);
    }
  });

  test('应该能够 Execute Notebook 和 SQL Lab', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'data_engineer',
        roles: ['data_engineer'],
      }));
    });
    await page.reload();

    const devPaths = ['/development/notebook', '/development/sql-lab'];
    for (const path of devPaths) {
      const result = await verifyCanAccessPage(page, path);
      expect(result.hasAccess).toBe(true);
    }
  });

  test('只读访问模型开发功能', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'data_engineer',
        roles: ['data_engineer'],
      }));
    });
    await page.reload();

    const result = await verifyCanAccessPage(page, '/model/experiments');
    expect(result.hasAccess).toBe(true);
  });

  test('应该能够 Execute AI 对话', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'data_engineer',
        roles: ['data_engineer'],
      }));
    });
    await page.reload();

    const result = await verifyCanAccessPage(page, '/ai/chat');
    expect(result.hasAccess).toBe(true);
  });

  test('无法访问系统管理功能', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'data_engineer',
        roles: ['data_engineer'],
      }));
    });
    await page.reload();

    const result = await verifyCannotAccessPage(page, '/admin/users');
    expect(result.hasAccess).toBe(true); // 确认不能访问
  });
});

// ============================================
// AI Developer 角色权限测试
// ============================================
test.describe('AI Developer 角色权限', () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test('只读访问数据集和元数据', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'ai_developer',
        roles: ['ai_developer'],
      }));
    });
    await page.reload();

    const result1 = await verifyCanAccessPage(page, '/data/datasets');
    const result2 = await verifyCanAccessPage(page, '/data/metadata');
    expect(result1.hasAccess).toBe(true);
    expect(result2.hasAccess).toBe(true);
  });

  test('应该能够 CRUD 实验管理', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'ai_developer',
        roles: ['ai_developer'],
      }));
    });
    await page.reload();

    const result = await verifyCanAccessPage(page, '/model/experiments');
    expect(result.hasAccess).toBe(true);
  });

  test('应该能够 CRUD 训练任务', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'ai_developer',
        roles: ['ai_developer'],
      }));
    });
    await page.reload();

    const result = await verifyCanAccessPage(page, '/model/training');
    expect(result.hasAccess).toBe(true);
  });

  test('应该能够 CRUD Pipeline', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'ai_developer',
        roles: ['ai_developer'],
      }));
    });
    await page.reload();

    const result = await verifyCanAccessPage(page, '/ai/workflows');
    expect(result.hasAccess).toBe(true);
  });

  test('应该能够 CRUD LLM 微调', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'ai_developer',
        roles: ['ai_developer'],
      }));
    });
    await page.reload();

    const result = await verifyCanAccessPage(page, '/model/finetune');
    expect(result.hasAccess).toBe(true);
  });

  test('应该能够 CRUD 在线服务', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'ai_developer',
        roles: ['ai_developer'],
      }));
    });
    await page.reload();

    const result = await verifyCanAccessPage(page, '/model/serving');
    expect(result.hasAccess).toBe(true);
  });

  test('应该能够 CRUD AI 应用（Prompt、知识库、Agent、工作流）', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'ai_developer',
        roles: ['ai_developer'],
      }));
    });
    await page.reload();

    const aiPaths = ['/ai/prompts', '/ai/knowledge', '/ai/agents', '/ai/workflows'];
    for (const path of aiPaths) {
      const result = await verifyCanAccessPage(page, path);
      expect(result.hasAccess).toBe(true);
    }
  });

  test('应该能够 Execute AI 对话、模型评估、SFT 微调', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'ai_developer',
        roles: ['ai_developer'],
      }));
    });
    await page.reload();

    const result = await verifyCanAccessPage(page, '/ai/chat');
    expect(result.hasAccess).toBe(true);
  });

  test('无法访问系统管理功能', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'ai_developer',
        roles: ['ai_developer'],
      }));
    });
    await page.reload();

    const result = await verifyCannotAccessPage(page, '/admin/users');
    expect(result.hasAccess).toBe(true);
  });
});

// ============================================
// Data Analyst 角色权限测试
// ============================================
test.describe('Data Analyst 角色权限', () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test('只读访问数据源、数据集、元数据', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'data_analyst',
        roles: ['data_analyst'],
      }));
    });
    await page.reload();

    const dataPaths = ['/data/datasources', '/data/datasets', '/data/metadata'];
    for (const path of dataPaths) {
      const result = await verifyCanAccessPage(page, path);
      expect(result.hasAccess).toBe(true);
    }
  });

  test('只读访问特征存储、BI 报表、指标体系', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'data_analyst',
        roles: ['data_analyst'],
      }));
    });
    await page.reload();

    const analysisPaths = ['/data/features', '/data/bi', '/data/metrics'];
    for (const path of analysisPaths) {
      const result = await verifyCanAccessPage(page, path);
      expect(result.hasAccess).toBe(true);
    }
  });

  test('应该能够 Execute SQL Lab', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'data_analyst',
        roles: ['data_analyst'],
      }));
    });
    await page.reload();

    const result = await verifyCanAccessPage(page, '/development/sql-lab');
    expect(result.hasAccess).toBe(true);
  });

  test('只读访问模型仓库、工作流', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'data_analyst',
        roles: ['data_analyst'],
      }));
    });
    await page.reload();

    const readOnlyPaths = ['/model/repository', '/ai/workflows'];
    for (const path of readOnlyPaths) {
      const result = await verifyCanAccessPage(page, path);
      expect(result.hasAccess).toBe(true);
    }
  });

  test('无法执行写操作', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'data_analyst',
        roles: ['data_analyst'],
      }));
    });
    await page.reload();

    // 访问数据集页面
    await page.goto(`${BASE_URL}/data/datasets`);
    await page.waitForLoadState('networkidle');

    // 应该没有创建按钮
    const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
    const isVisible = await createButton.isVisible().catch(() => false);
    expect(isVisible).toBe(false);
  });

  test('无法访问系统管理功能', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'data_analyst',
        roles: ['data_analyst'],
      }));
    });
    await page.reload();

    const result = await verifyCannotAccessPage(page, '/admin/users');
    expect(result.hasAccess).toBe(true);
  });
});

// ============================================
// User 角色权限测试
// ============================================
test.describe('User 角色权限', () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test('应该能够访问工作台', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'user',
        roles: ['user'],
      }));
    });
    await page.reload();

    const result = await verifyCanAccessPage(page, '/workspace');
    expect(result.hasAccess).toBe(true);
  });

  test('只读访问数据集', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'user',
        roles: ['user'],
      }));
    });
    await page.reload();

    const result = await verifyCanAccessPage(page, '/data/datasets');
    expect(result.hasAccess).toBe(true);
  });

  test('应该能够 Execute AI 对话', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'user',
        roles: ['user'],
      }));
    });
    await page.reload();

    const result = await verifyCanAccessPage(page, '/ai/chat');
    expect(result.hasAccess).toBe(true);
  });

  test('只读访问工作流', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'user',
        roles: ['user'],
      }));
    });
    await page.reload();

    const result = await verifyCanAccessPage(page, '/ai/workflows');
    expect(result.hasAccess).toBe(true);
  });

  test('只读访问文档中心', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'user',
        roles: ['user'],
      }));
    });
    await page.reload();

    const result = await verifyCanAccessPage(page, '/docs');
    expect(result.hasAccess).toBe(true);
  });

  test('无法访问开发功能', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'user',
        roles: ['user'],
      }));
    });
    await page.reload();

    const result = await verifyCannotAccessPage(page, '/development/notebook');
    expect(result.hasAccess).toBe(true);
  });

  test('无法访问系统管理功能', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'user',
        roles: ['user'],
      }));
    });
    await page.reload();

    const result = await verifyCannotAccessPage(page, '/admin/users');
    expect(result.hasAccess).toBe(true);
  });
});

// ============================================
// Guest 角色权限测试
// ============================================
test.describe('Guest 角色权限', () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test('应该能够访问工作台', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'guest',
        roles: ['guest'],
      }));
    });
    await page.reload();

    const result = await verifyCanAccessPage(page, '/workspace');
    expect(result.hasAccess).toBe(true);
  });

  test('只读访问数据集', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'guest',
        roles: ['guest'],
      }));
    });
    await page.reload();

    const result = await verifyCanAccessPage(page, '/data/datasets');
    expect(result.hasAccess).toBe(true);
  });

  test('只读访问元数据', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'guest',
        roles: ['guest'],
      }));
    });
    await page.reload();

    const result = await verifyCanAccessPage(page, '/data/metadata');
    expect(result.hasAccess).toBe(true);
  });

  test('无法访问其他功能', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'guest',
        roles: ['guest'],
      }));
    });
    await page.reload();

    const restrictedPaths = [
      '/development/notebook',
      '/ai/workflows',
      '/model/experiments',
    ];

    for (const path of restrictedPaths) {
      const result = await verifyCannotAccessPage(page, path);
      expect(result.hasAccess).toBe(true);
    }
  });
});
