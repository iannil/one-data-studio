/**
 * 跨角色功能权限验证测试
 * 测试各个功能模块对不同角色的 CRUD 权限
 */

import { test, expect } from './fixtures/user-lifecycle.fixture';
import { verifyCanAccessPage, verifyCannotAccessPage, verifyCanPerformAction } from './helpers/verification';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

// 辅助函数：设置页面用户角色
async function setUserRole(page: any, role: string) {
  await page.goto(`${BASE_URL}`);
  await page.evaluate((r) => {
    localStorage.setItem('user_info', JSON.stringify({
      username: r,
      roles: [r],
    }));
  }, role);
  await page.reload();
}

// ============================================
// 数据管理模块权限验证
// ============================================
test.describe('功能模块权限验证 - 数据管理', () => {
  test('数据源 - CRUD 权限验证', async ({ page }) => {
    // admin 和 data_engineer 应该能访问
    await setUserRole(page, 'data_engineer');
    let result = await verifyCanAccessPage(page, '/data/datasources');
    expect(result.hasAccess).toBe(true);

    // data_analyst 只读访问
    await setUserRole(page, 'data_analyst');
    result = await verifyCanAccessPage(page, '/data/datasources');
    expect(result.hasAccess).toBe(true);

    // user 不能访问
    await setUserRole(page, 'user');
    result = await verifyCannotAccessPage(page, '/data/datasources');
    expect(result.hasAccess).toBe(true);
  });

  test('数据集 - CRUD 权限验证', async ({ page }) => {
    // 所有角色都能访问（至少只读）
    const roles = ['admin', 'data_engineer', 'ai_developer', 'data_analyst', 'user', 'guest'];

    for (const role of roles) {
      await setUserRole(page, role);
      const result = await verifyCanAccessPage(page, '/data/datasets');
      expect(result.hasAccess, `${role} should access datasets`).toBe(true);
    }
  });

  test('元数据 - CRUD 权限验证', async ({ page }) => {
    const canCreateRoles = ['admin', 'data_engineer'];
    const readOnlyRoles = ['ai_developer', 'data_analyst'];
    const noAccessRoles = ['user', 'guest'];

    for (const role of canCreateRoles) {
      await setUserRole(page, role);
      const result = await verifyCanAccessPage(page, '/data/metadata');
      expect(result.hasAccess).toBe(true);
    }

    for (const role of readOnlyRoles) {
      await setUserRole(page, role);
      const result = await verifyCanAccessPage(page, '/data/metadata');
      expect(result.hasAccess).toBe(true);
    }

    for (const role of noAccessRoles) {
      await setUserRole(page, role);
      const result = await verifyCannotAccessPage(page, '/data/metadata');
      expect(result.hasAccess).toBe(true);
    }
  });

  test('特征存储 - Read 权限验证', async ({ page }) => {
    await setUserRole(page, 'data_engineer');
    let result = await verifyCanAccessPage(page, '/data/features');
    expect(result.hasAccess).toBe(true);

    await setUserRole(page, 'user');
    result = await verifyCannotAccessPage(page, '/data/features');
    expect(result.hasAccess).toBe(true);
  });

  test('数据标准 - Read 权限验证', async ({ page }) => {
    await setUserRole(page, 'data_engineer');
    let result = await verifyCanAccessPage(page, '/data/standards');
    expect(result.hasAccess).toBe(true);

    await setUserRole(page, 'user');
    result = await verifyCannotAccessPage(page, '/data/standards');
    expect(result.hasAccess).toBe(true);
  });

  test('数据资产 - Read 权限验证', async ({ page }) => {
    await setUserRole(page, 'admin');
    const result = await verifyCanAccessPage(page, '/data/assets');
    expect(result.hasAccess).toBe(true);
  });

  test('数据服务 - Read 权限验证', async ({ page }) => {
    await setUserRole(page, 'data_engineer');
    const result = await verifyCanAccessPage(page, '/data/services');
    expect(result.hasAccess).toBe(true);
  });

  test('BI 报表 - Read 权限验证', async ({ page }) => {
    await setUserRole(page, 'data_analyst');
    const result = await verifyCanAccessPage(page, '/data/bi');
    expect(result.hasAccess).toBe(true);
  });

  test('指标体系 - Read 权限验证', async ({ page }) => {
    await setUserRole(page, 'data_analyst');
    const result = await verifyCanAccessPage(page, '/data/metrics');
    expect(result.hasAccess).toBe(true);
  });
});

// ============================================
// 数据开发模块权限验证
// ============================================
test.describe('功能模块权限验证 - 数据开发', () => {
  test('ETL 任务 - CRUD 权限验证', async ({ page }) => {
    await setUserRole(page, 'data_engineer');
    let result = await verifyCanAccessPage(page, '/development/etl');
    expect(result.hasAccess).toBe(true);

    await setUserRole(page, 'user');
    result = await verifyCannotAccessPage(page, '/development/etl');
    expect(result.hasAccess).toBe(true);
  });

  test('数据质量 - CRUD 权限验证', async ({ page }) => {
    await setUserRole(page, 'data_engineer');
    let result = await verifyCanAccessPage(page, '/data/quality');
    expect(result.hasAccess).toBe(true);

    await setUserRole(page, 'user');
    result = await verifyCannotAccessPage(page, '/data/quality');
    expect(result.hasAccess).toBe(true);
  });

  test('数据血缘 - CRUD 权限验证', async ({ page }) => {
    await setUserRole(page, 'data_engineer');
    let result = await verifyCanAccessPage(page, '/data/lineage');
    expect(result.hasAccess).toBe(true);
  });

  test('离线开发 - Read/Execute 权限验证', async ({ page }) => {
    await setUserRole(page, 'data_engineer');
    const result = await verifyCanAccessPage(page, '/development/offline');
    expect(result.hasAccess).toBe(true);
  });

  test('实时开发 - Read/Execute 权限验证', async ({ page }) => {
    await setUserRole(page, 'data_engineer');
    const result = await verifyCanAccessPage(page, '/development/streaming');
    expect(result.hasAccess).toBe(true);
  });

  test('实时 IDE - Read/Execute 权限验证', async ({ page }) => {
    await setUserRole(page, 'data_engineer');
    const result = await verifyCanAccessPage(page, '/development/ide');
    expect(result.hasAccess).toBe(true);
  });

  test('Notebook - Read/Execute 权限验证', async ({ page }) => {
    const canAccessRoles = ['admin', 'data_engineer', 'ai_developer'];
    const cannotAccessRoles = ['data_analyst', 'user', 'guest'];

    for (const role of canAccessRoles) {
      await setUserRole(page, role);
      const result = await verifyCanAccessPage(page, '/development/notebook');
      expect(result.hasAccess, `${role} should access notebook`).toBe(true);
    }

    for (const role of cannotAccessRoles) {
      await setUserRole(page, role);
      const result = await verifyCannotAccessPage(page, '/development/notebook');
      expect(result.hasAccess, `${role} should not access notebook`).toBe(true);
    }
  });

  test('SQL Lab - Read/Execute 权限验证', async ({ page }) => {
    const canAccessRoles = ['admin', 'data_engineer', 'ai_developer', 'data_analyst'];
    const cannotAccessRoles = ['user', 'guest'];

    for (const role of canAccessRoles) {
      await setUserRole(page, role);
      const result = await verifyCanAccessPage(page, '/development/sql-lab');
      expect(result.hasAccess, `${role} should access sql-lab`).toBe(true);
    }

    for (const role of cannotAccessRoles) {
      await setUserRole(page, role);
      const result = await verifyCannotAccessPage(page, '/development/sql-lab');
      expect(result.hasAccess, `${role} should not access sql-lab`).toBe(true);
    }
  });
});

// ============================================
// 模型开发模块权限验证
// ============================================
test.describe('功能模块权限验证 - 模型开发', () => {
  test('实验管理 - CRUD 权限验证', async ({ page }) => {
    await setUserRole(page, 'ai_developer');
    let result = await verifyCanAccessPage(page, '/model/experiments');
    expect(result.hasAccess).toBe(true);

    await setUserRole(page, 'user');
    result = await verifyCannotAccessPage(page, '/model/experiments');
    expect(result.hasAccess).toBe(true);
  });

  test('训练任务 - CRUD 权限验证', async ({ page }) => {
    await setUserRole(page, 'ai_developer');
    let result = await verifyCanAccessPage(page, '/model/training');
    expect(result.hasAccess).toBe(true);

    await setUserRole(page, 'user');
    result = await verifyCannotAccessPage(page, '/model/training');
    expect(result.hasAccess).toBe(true);
  });

  test('模型仓库 - Read 权限验证', async ({ page }) => {
    await setUserRole(page, 'ai_developer');
    let result = await verifyCanAccessPage(page, '/model/repository');
    expect(result.hasAccess).toBe(true);

    await setUserRole(page, 'data_analyst');
    result = await verifyCanAccessPage(page, '/model/repository');
    expect(result.hasAccess).toBe(true);
  });

  test('AIHub - Read/Execute 权限验证', async ({ page }) => {
    await setUserRole(page, 'ai_developer');
    const result = await verifyCanAccessPage(page, '/model/aihub');
    expect(result.hasAccess).toBe(true);
  });

  test('Pipeline - CRUD/Execute 权限验证', async ({ page }) => {
    await setUserRole(page, 'ai_developer');
    let result = await verifyCanAccessPage(page, '/model/pipeline');
    expect(result.hasAccess).toBe(true);

    await setUserRole(page, 'user');
    result = await verifyCannotAccessPage(page, '/model/pipeline');
    expect(result.hasAccess).toBe(true);
  });

  test('LLM 微调 - CRUD 权限验证', async ({ page }) => {
    await setUserRole(page, 'ai_developer');
    let result = await verifyCanAccessPage(page, '/model/finetune');
    expect(result.hasAccess).toBe(true);

    await setUserRole(page, 'data_engineer');
    result = await verifyCannotAccessPage(page, '/model/finetune');
    expect(result.hasAccess).toBe(true);
  });
});

// ============================================
// 模型服务模块权限验证
// ============================================
test.describe('功能模块权限验证 - 模型服务', () => {
  test('在线服务 - CRUD 权限验证', async ({ page }) => {
    await setUserRole(page, 'ai_developer');
    let result = await verifyCanAccessPage(page, '/model/serving');
    expect(result.hasAccess).toBe(true);

    await setUserRole(page, 'user');
    result = await verifyCannotAccessPage(page, '/model/serving');
    expect(result.hasAccess).toBe(true);
  });

  test('资源管理 - Read 权限验证', async ({ page }) => {
    await setUserRole(page, 'admin');
    const result = await verifyCanAccessPage(page, '/model/resources');
    expect(result.hasAccess).toBe(true);
  });

  test('监控告警 - Read 权限验证', async ({ page }) => {
    await setUserRole(page, 'ai_developer');
    const result = await verifyCanAccessPage(page, '/model/monitoring');
    expect(result.hasAccess).toBe(true);
  });
});

// ============================================
// AI 应用模块权限验证
// ============================================
test.describe('功能模块权限验证 - AI 应用', () => {
  test('AI 对话 - Execute 权限验证', async ({ page }) => {
    const canAccessRoles = ['admin', 'data_engineer', 'ai_developer', 'user'];
    const cannotAccessRoles = ['data_analyst', 'guest'];

    for (const role of canAccessRoles) {
      await setUserRole(page, role);
      const result = await verifyCanAccessPage(page, '/ai/chat');
      expect(result.hasAccess, `${role} should access ai chat`).toBe(true);
    }

    for (const role of cannotAccessRoles) {
      await setUserRole(page, role);
      const result = await verifyCannotAccessPage(page, '/ai/chat');
      expect(result.hasAccess, `${role} should not access ai chat`).toBe(true);
    }
  });

  test('Prompt 管理 - CRUD 权限验证', async ({ page }) => {
    await setUserRole(page, 'ai_developer');
    let result = await verifyCanAccessPage(page, '/ai/prompts');
    expect(result.hasAccess).toBe(true);

    await setUserRole(page, 'user');
    result = await verifyCannotAccessPage(page, '/ai/prompts');
    expect(result.hasAccess).toBe(true);
  });

  test('知识库 - CRUD 权限验证', async ({ page }) => {
    await setUserRole(page, 'ai_developer');
    let result = await verifyCanAccessPage(page, '/ai/knowledge');
    expect(result.hasAccess).toBe(true);

    await setUserRole(page, 'user');
    result = await verifyCannotAccessPage(page, '/ai/knowledge');
    expect(result.hasAccess).toBe(true);
  });

  test('模型评估 - Execute 权限验证', async ({ page }) => {
    await setUserRole(page, 'ai_developer');
    const result = await verifyCanAccessPage(page, '/ai/evaluation');
    expect(result.hasAccess).toBe(true);
  });

  test('SFT 微调 - Execute 权限验证', async ({ page }) => {
    await setUserRole(page, 'ai_developer');
    const result = await verifyCanAccessPage(page, '/model/sft');
    expect(result.hasAccess).toBe(true);
  });

  test('Agent - Execute 权限验证', async ({ page }) => {
    await setUserRole(page, 'ai_developer');
    let result = await verifyCanAccessPage(page, '/ai/agents');
    expect(result.hasAccess).toBe(true);

    await setUserRole(page, 'user');
    result = await verifyCannotAccessPage(page, '/ai/agents');
    expect(result.hasAccess).toBe(true);
  });

  test('工作流 - CRUD/Execute 权限验证', async ({ page }) => {
    const canAccessRoles = ['admin', 'ai_developer'];
    const readOnlyRoles = ['data_analyst', 'user'];

    for (const role of canAccessRoles) {
      await setUserRole(page, role);
      const result = await verifyCanAccessPage(page, '/ai/workflows');
      expect(result.hasAccess, `${role} should access workflows`).toBe(true);
    }

    for (const role of readOnlyRoles) {
      await setUserRole(page, role);
      const result = await verifyCanAccessPage(page, '/ai/workflows');
      expect(result.hasAccess, `${role} should access workflows (read-only)`).toBe(true);
    }
  });

  test('Text2SQL - Execute 权限验证', async ({ page }) => {
    await setUserRole(page, 'ai_developer');
    const result = await verifyCanAccessPage(page, '/ai/text2sql');
    expect(result.hasAccess).toBe(true);
  });

  test('应用发布 - CRUD 权限验证', async ({ page }) => {
    await setUserRole(page, 'ai_developer');
    let result = await verifyCanAccessPage(page, '/ai/publish');
    expect(result.hasAccess).toBe(true);

    await setUserRole(page, 'user');
    result = await verifyCannotAccessPage(page, '/ai/publish');
    expect(result.hasAccess).toBe(true);
  });
});

// ============================================
// 运维中心模块权限验证
// ============================================
test.describe('功能模块权限验证 - 运维中心', () => {
  test('系统监控 - Read 权限验证', async ({ page }) => {
    await setUserRole(page, 'admin');
    const result = await verifyCanAccessPage(page, '/ops/monitoring');
    expect(result.hasAccess).toBe(true);
  });

  test('调度管理 - Read 权限验证', async ({ page }) => {
    await setUserRole(page, 'admin');
    const result = await verifyCanAccessPage(page, '/ops/scheduling');
    expect(result.hasAccess).toBe(true);
  });

  test('执行记录 - Read 权限验证', async ({ page }) => {
    await setUserRole(page, 'data_engineer');
    const result = await verifyCanAccessPage(page, '/ops/executions');
    expect(result.hasAccess).toBe(true);
  });

  test('文档中心 - Read 权限验证', async ({ page }) => {
    const allRoles = ['admin', 'data_engineer', 'ai_developer', 'data_analyst', 'user', 'guest'];

    for (const role of allRoles) {
      await setUserRole(page, role);
      const result = await verifyCanAccessPage(page, '/docs');
      expect(result.hasAccess, `${role} should access docs`).toBe(true);
    }
  });
});

// ============================================
// 系统管理模块权限验证
// ============================================
test.describe('功能模块权限验证 - 系统管理', () => {
  test('用户管理 - Admin 仅限', async ({ page }) => {
    await setUserRole(page, 'admin');
    let result = await verifyCanAccessPage(page, '/admin/users');
    expect(result.hasAccess).toBe(true);

    await setUserRole(page, 'data_engineer');
    result = await verifyCannotAccessPage(page, '/admin/users');
    expect(result.hasAccess).toBe(true);
  });

  test('用户组管理 - Admin 仅限', async ({ page }) => {
    await setUserRole(page, 'admin');
    let result = await verifyCanAccessPage(page, '/admin/groups');
    expect(result.hasAccess).toBe(true);

    await setUserRole(page, 'data_engineer');
    result = await verifyCannotAccessPage(page, '/admin/groups');
    expect(result.hasAccess).toBe(true);
  });

  test('系统设置 - Admin 仅限', async ({ page }) => {
    await setUserRole(page, 'admin');
    let result = await verifyCanAccessPage(page, '/admin/settings');
    expect(result.hasAccess).toBe(true);

    await setUserRole(page, 'data_engineer');
    result = await verifyCannotAccessPage(page, '/admin/settings');
    expect(result.hasAccess).toBe(true);
  });

  test('审计日志 - Admin 仅限', async ({ page }) => {
    await setUserRole(page, 'admin');
    let result = await verifyCanAccessPage(page, '/admin/audit');
    expect(result.hasAccess).toBe(true);

    await setUserRole(page, 'data_engineer');
    result = await verifyCannotAccessPage(page, '/admin/audit');
    expect(result.hasAccess).toBe(true);
  });

  test('角色管理 - Admin 仅限', async ({ page }) => {
    await setUserRole(page, 'admin');
    let result = await verifyCanAccessPage(page, '/admin/roles');
    expect(result.hasAccess).toBe(true);

    await setUserRole(page, 'data_engineer');
    result = await verifyCannotAccessPage(page, '/admin/roles');
    expect(result.hasAccess).toBe(true);
  });
});
