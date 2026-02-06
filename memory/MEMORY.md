# ONE-DATA-STUDIO 长期记忆

> 本文件存储项目的长期知识、决策和上下文。

## 项目概述

ONE-DATA-STUDIO 是一个**企业级 DataOps + MLOps + LLMOps 融合平台**。

### 核心特点
- 完整的前后端实现
- 主要使用中文编写文档
- 使用 Mermaid 图表可视化工作流程
- 支持 Docker Compose 和 Kubernetes 部署

### 四层架构
1. **L1 基础设施层**: Kubernetes 容器编排，CPU/GPU 资源池
2. **L2 数据底座层 (Data)**: 数据集成、ETL、治理、特征存储、向量存储
3. **L3 算法引擎层 (Model)**: Notebook 开发、分布式训练、模型服务
4. **L4 应用编排层 (Agent)**: RAG 流水线、Agent 编排、Prompt 管理

## 用户偏好

### 编码风格
- **不可变性优先**: 始终创建新对象，永不突变
- **小文件组织**: 高内聚低耦合，200-400 行典型，800 行最大
- **类型安全**: 显式类型，运行时与编译时契约一致
- **声明式配置**: 减少分支，数据驱动

### 工作流偏好
- **TDD 强制**: 先写测试，80%+ 覆盖率
- **计划驱动**: 复杂任务先规划
- **小步提交**: 便于理解和回滚
- **并行执行**: 独立操作使用并行 Task

### 文档规范
- 中文交流与文档
- 代码使用英文
- 文档放在 `docs` 文件夹
- 进度保存到 `/docs/progress`（未完成）
- 完成报告保存到 `/docs/reports/completed`

### 发布规范
- 固定在 `/release` 文件夹
- 必须包含生产环境所需的所有文件
- 支持全量和增量发布

## 关键决策

### 记忆系统
- **决策**: 使用基于 Markdown 的透明双层记忆
- **原因**: 禁止复杂嵌入检索，保持人类可读和 Git 友好
- **结构**:
  - 流层: `memory/daily/{YYYY-MM-DD}.md` - 仅追加日志
  - 沉积层: `memory/MEMORY.md` - 结构化知识

### 面向 LLM 可改写性
- 一致的分层与目录
- 明确边界与单一职责
- 显式类型与契约优先
- 统一命名约定（parseXxx、assertNever、createXxxService）

## 项目结构

```
one-data-studio/
├── services/         # 后端服务（Flask/FastAPI）
│   ├── data-api/     # 数据治理 API
│   ├── agent-api/    # 应用编排 API
│   ├── openai-proxy/ # OpenAI 兼容代理
│   └── ...
├── web/              # 前端应用（React + TypeScript + Vite）
├── deploy/           # 部署配置
├── tests/            # 测试用例
├── docs/             # 项目文档
├── memory/           # 记忆系统
└── scripts/          # 运维脚本
```

## 项目完成度（2026-02-06）

### 服务状态

| 服务 | 状态 | 文件数 | 代码行数 |
|------|------|--------|----------|
| data-api | ✅ 生产就绪 | 90 | 69,054 |
| agent-api | ✅ 生产就绪 | 56 | 23,462 |
| model-api | ✅ 生产就绪 | 24 | 10,304 |
| admin-api | ✅ 生产就绪 | 25 | 10,316 |
| openai-proxy | ✅ 生产就绪 | 1 | 890 |
| ocr-service | ✅ 已完成 | 33 | 11,503 |
| behavior-service | ✅ 已完成 | 11 | 3,058 |
| shared | ✅ 生产就绪 | 62 | ~90,000 |

**所有后端服务 100% 完成**

### 最近修复的问题

| 日期 | 问题 | 修复 |
|------|------|------|
| 2026-02-04 | 向量检索使用模拟数据 | 添加环境变量控制向量服务启用 |
| 2026-02-04 | 聊天历史加载缺少错误处理 | 添加错误处理和日志记录 |
| 2026-02-04 | 向量删除不完整 | 添加参数验证、SQL 注入防护 |
| 2026-02-06 | Lint 警告过多 (547) | 清理未使用导入，降至 499 |

### 分阶段测试计划

- **状态**: ✅ 已实施
- **目的**: 资源受限环境（16GB 内存）下的分阶段验证
- **成果**:
  - 环境变量模板 (`deploy/local/.env.example`)
  - 自动化测试脚本 (`deploy/local/test-phased.sh`)
  - 6 个阶段集成测试文件 (205 测试用例)
  - 完整测试指南文档

### 代码质量改进

| 项目 | 改进前 | 改进后 |
|------|--------|--------|
| Lint 警告 | 547 | 499 (-48) |
| 测试通过率 | 1361/1371 (99.3%) | 目标 100% |

## 当前技术债务

### 代码清理待处理

1. **认证模块重复**: 3 个服务有独立 auth.py 实现
   - `services/agent-api/auth.py`
   - `services/data-api/auth.py`
   - `services/admin-api/auth.py`
   - **计划**: 统一迁移到 `services/shared/auth/`

2. **console.log 清理**: 12 个 E2E 测试文件需要替换为 logger

3. **注释代码清理**:
   - `services/data-api/app.py`
   - `services/agent-api/engine/plugin_manager.py`
   - `services/ocr-service/services/validator.py`

4. **TODO 项整理**: 3 个 TODO 需要移到 TECH_DEBT.md

5. **重复的 BehaviorAnalyzer 类**:
   - `services/admin-api/src/behavior_analyzer.py`
   - `services/behavior-service/services/behavior_analyzer.py`

### 待改进功能

| 优先级 | 功能 | 位置 |
|--------|------|------|
| P1 | 工作流编辑器完善 | `web/src/pages/workflows/` |
| P1 | 模型热切换 | `services/openai-proxy/` |
| P2 | 数据集版本控制 | `services/data-api/` |
| P2 | 自动触发训练 | `services/model-api/` |

## 经验教训

> 避免重复过去的错误

1. **认证逻辑应该共享**: 多个服务各自实现 auth.py 导致维护困难
2. **测试环境资源限制**: 16GB 内存无法同时运行所有服务，需要分阶段测试
3. **console.log 在 E2E 测试中应统一**: 便于调试和日志管理

## 最后更新

- **日期**: 2026-02-06
- **操作**: 添加项目完成度、认证整合计划
