# 文档整理与代码清理进度

> 开始日期：2026-02-06
> 最后更新：2026-02-06
> 状态：进行中

---

## 一、任务概述

本次任务旨在全面整理项目文档、更新记忆系统、清理冗余代码、统一认证模块。

**目标**：
1. 更新记忆系统反映最新项目状态
2. 整理 `/docs/progress/` 目录，移动已完成的文档
3. 更新项目状态文档
4. 统一认证模块到 `services/shared/auth/`
5. 清理 console.log、注释代码、TODO 项

**范围**：
- 涉及模块：memory/, docs/, services/, tests/
- 预计工作量：6-8 小时

---

## 二、进度记录

### 2026-02-06 下午

**完成**：
- ✅ 更新 `memory/MEMORY.md` - 添加项目完成度、最近修复、技术债务状态
- ✅ 更新 `memory/daily/2026-02-06.md` - 添加今日任务和发现的问题
- ✅ 移动 `phased-testing-2026-02-04.md` 到 `docs/reports/completed/`
- ✅ 完成 `doc-cleanup-code-cleanup-2026-02-03.md` 并移动到 `docs/reports/completed/`
- ✅ 创建今日进度文档（本文件）

**进行中**：
- 🔄 更新 `docs/PROJECT_STATUS.md`
- 🔄 更新 `docs/TECH_DEBT.md`
- 🔄 分析认证模块实现差异

**待办**：
- ⏳ 扩展 `services/shared/auth/` 添加统一认证
- ⏳ 更新各服务引用 shared/auth
- ⏳ 删除冗余的 auth.py 文件
- ⏳ 创建 E2E 测试 logger 工具
- ⏳ 替换 console.log 为 logger
- ⏳ 清理注释代码

---

## 三、发现的问题清单

### 3.1 认证模块分析（高优先级）

| 服务 | 文件 | 说明 |
|------|------|------|
| agent-api | `services/agent-api/auth.py` | JWT 认证 + 自定义资源 (WORKFLOW, CHAT, AGENT) |
| data-api | `services/data-api/auth.py` | JWT 认证 + 自定义资源 (DATASET, METADATA) |
| admin-api | `services/admin-api/auth.py` | 简化实现，开发模式 |
| shared | `services/shared/auth/` | **已有完整的 JWT 中间件和权限系统** |

**分析结果**：
- `shared/auth/` 已包含 `jwt_middleware.py`、`permissions.py`、`token_refresh.py`
- 各服务主要差异在于服务特定的 Resource 定义和权限矩阵
- `admin-api/auth.py` 已经尝试导入 shared/auth

**优化方案**：
1. 保持服务特定的 Resource 定义（合理的设计）
2. 各服务统一从 `shared.auth` 导入 `require_jwt`, `require_role` 等装饰器
3. 删除重复的 JWT 验证逻辑（extract_token, decode_jwt_token 等）

**状态**: 分析完成，需要优化导入

### 3.2 console.log 使用（12 个文件）

| 类型 | 文件 |
|------|------|
| E2E 测试 | `tests/e2e/complete-acceptance.spec.ts` |
| E2E 测试 | `tests/e2e/direct-acceptance.spec.ts` |
| E2E 测试 | `tests/e2e/acceptance-test.spec.ts` |
| E2E 测试 | `tests/e2e/user-lifecycle/system-admin.spec.ts` |
| E2E 测试 | `tests/e2e/core-pages-deep.spec.ts` |
| E2E 测试 | `tests/e2e/performance.spec.ts` |
| E2E 测试 | `tests/e2e/admin-deep.spec.ts` |
| E2E 测试 | `tests/e2e/full-acceptance.spec.ts` |
| E2E 测试 | `tests/e2e/error-handling-deep.spec.ts` |
| Helpers | `tests/e2e/helpers/api-client.ts` |
| Helpers | `tests/e2e/helpers/database-seeder.ts` |
| Setup | `tests/e2e/global-setup.ts` |

**操作**：创建 `tests/e2e/helpers/logger.ts` 并替换所有 console.log

### 3.3 注释代码

| 文件 | 清理类型 |
|------|----------|
| `services/data-api/app.py` | 删除注释掉的代码 |
| `services/agent-api/engine/plugin_manager.py` | 删除注释掉的代码 |
| `services/ocr-service/services/validator.py` | 删除注释掉的代码 |

### 3.4 TODO 项整理

| 位置 | 内容 | 决策 |
|------|------|------|
| `services/agent-api/engine/plugin_manager.py` | 从类型注解提取参数 | 移到 TECH_DEBT.md 作为 P2 |
| `services/data-api/app.py` | 从实际表中获取样本数据 | 移到 TECH_DEBT.md 作为 P2 |
| `services/ocr-service/services/validator.py` | 添加校验码验证 | 移到 TECH_DEBT.md 作为 P2 |

### 3.5 重复类

| 类 | 位置 |
|------|------|
| BehaviorAnalyzer | `services/admin-api/src/behavior_analyzer.py` |
| BehaviorAnalyzer | `services/behavior-service/services/behavior_analyzer.py` |

**操作**：记录到 TECH_DEBT.md，评估未来合并可能性

---

## 四、修改文件清单

| 文件路径 | 操作 | 说明 |
|----------|------|------|
| `memory/MEMORY.md` | 更新 | 添加项目完成度、认证整合计划 |
| `memory/daily/2026-02-06.md` | 更新 | 添加今日任务记录 |
| `docs/progress/doc-organization-2026-02-06.md` | 新建 | 本文件 |
| `docs/reports/completed/doc-organization-2026-02-06.md` | 待新建 | 完成报告 |
| `docs/PROJECT_STATUS.md` | 待更新 | 添加最新服务状态 |
| `docs/TECH_DEBT.md` | 待更新 | 更新技术债务 |
| `services/shared/auth/unified_auth.py` | 待新建 | 统一认证模块 |
| `tests/e2e/helpers/logger.ts` | 待新建 | 日志工具 |

---

## 五、待办事项

- [ ] 更新 `docs/PROJECT_STATUS.md`
- [ ] 更新 `docs/TECH_DEBT.md`
- [ ] 分析认证模块实现差异
- [ ] 扩展 `services/shared/auth/`
- [ ] 更新各服务引用 shared/auth
- [ ] 删除冗余的 auth.py 文件
- [ ] 创建 E2E 测试 logger 工具
- [ ] 替换 console.log 为 logger
- [ ] 清理注释代码
- [ ] 整理 TODO 项
- [ ] 验证文档规范合规性
- [ ] 创建完成报告

---

## 六、相关资源

- 进度文档模板：`docs/templates/progress-template.md`
- 完成报告模板：`docs/templates/completion-report.md`
- 技术债务清单：`docs/TECH_DEBT.md`
- 项目状态文档：`docs/PROJECT_STATUS.md`

---

> 更新时间：2026-02-06
