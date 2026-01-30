# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 提供在此代码仓库中工作的指导。

## 仓库概述

ONE-DATA-STUDIO 是一个**企业级 DataOps + MLOps + LLMOps 融合平台**，将三个 AI 基础设施整合为统一的智能数据平台。

**项目特点：**

- 完整的前后端实现（274 Python 文件 + 216 TSX 文件）
- 主要使用中文编写文档
- 使用 Mermaid 图表来可视化工作流程和架构
- 支持 Docker Compose 和 Kubernetes 部署

**代码规模：**

| 类型 | 文件数 | 代码行数 |
|------|--------|----------|
| Python 后端 | 274 | 142,887 |
| TypeScript 前端 | 216 | 120,334 |
| 测试代码 | 143+ | 32,500+ |
| **总计** | **630+** | **~295,000+** |

## 项目指南

- 目标：以强类型、可测试、分层解耦为核心，保证项目健壮性与可扩展性；以清晰可读、模式统一为核心，使大模型易于理解与改写。
- 语言约定：交流与文档使用中文；生成的代码使用英文；文档放在 `docs` 且使用 Markdown。
- 发布约定：
  - 发布固定在 `/release` 文件夹，如 rust 服务固定发布在 `/release/rust` 文件夹。
  - 发布的成果物必须且始终以生产环境为标准，要包含所有发布生产所应该包含的文件或数据（包含全量发布与增量发布，首次发布与非首次发布）。
- 文档约定：
  - 每次修改都必须延续上一次的进展，每次修改的进展都必须保存在对应的 `docs` 文件夹下的文档中。
  - 执行修改过程中，进展随时保存文档，带上实际修改的时间，便于追溯修改历史。
  - 未完成的修改，文档保存在 `/docs/progress` 文件夹下。
  - 已完成的修改，文档保存在 `/docs/reports/completed` 文件夹下。
  - 对修改进行验收，文档保存在 `/docs/reports` 文件夹下。
  - 对重复的、冗余的、不能体现实际情况的文档或文档内容，要保持更新和调整。
  - 文档模板和命名规范可以参考 `/docs/standards` 和 `docs/templates` 文件夹下的内容。

### 面向大模型的可改写性（LLM Friendly）

- 一致的分层与目录：相同功能在各应用/包中遵循相同结构与命名，使检索与大范围重构更可控。
- 明确边界与单一职责：函数/类保持单一职责；公共模块暴露极少稳定接口；避免隐式全局状态。
- 显式类型与契约优先：导出 API 均有显式类型；运行时与编译时契约一致（zod schema 即类型源）。
- 声明式配置：将重要行为转为数据驱动（配置对象 + `as const`/`satisfies`），减少分支与条件散落。
- 可搜索性：统一命名（如 `parseXxx`、`assertNever`、`safeJsonParse`、`createXxxService`），降低 LLM 与人类的检索成本。
- 小步提交与计划：通过 `IMPLEMENTATION_PLAN.md` 和小步提交让模型理解上下文、意图与边界。
- 变更安全策略：批量程序性改动前先将原文件备份至 `/backup` 相对路径；若错误数异常上升，立即回滚备份。

## 项目结构

```
one-data-studio/
├── services/                 # 后端服务
│   ├── data-api/            # 数据治理 API (Flask)
│   ├── agent-api/           # 应用编排 API (Flask)
│   ├── openai-proxy/        # OpenAI 兼容代理 (FastAPI)
│   ├── admin-api/           # 管理后台 API
│   ├── model-api/           # MLOps 模型管理 API
│   ├── ocr-service/         # OCR 文档识别服务
│   ├── behavior-service/    # 用户行为分析服务
│   └── shared/              # 共享模块（认证、存储）
├── web/                      # 前端应用 (React + TypeScript + Vite)
├── deploy/                   # 部署配置
│   ├── local/               # Docker Compose 配置
│   ├── scripts/             # 部署脚本
│   └── dockerfiles/         # Dockerfile
├── tests/                    # 测试用例
│   ├── unit/                # 单元测试（按角色分类）
│   ├── integration/         # 集成测试
│   ├── e2e/                 # 端到端测试 (Playwright)
│   ├── performance/         # 性能测试
│   └── mocks/               # Mock 服务
├── docs/                     # 项目文档
│   ├── 00-project/          # 项目概览
│   ├── 01-architecture/     # 架构设计
│   ├── 02-integration/      # 集成方案
│   ├── 03-progress/         # 进度追踪
│   ├── 04-testing/          # 测试文档
│   ├── 05-planning/         # 规划文档
│   ├── 06-development/      # 开发指南
│   ├── 07-operations/       # 运维指南
│   ├── 08-user-guide/       # 用户手册
│   ├── 09-requirements/     # 需求文档
│   └── 99-archived/         # 归档文档
└── scripts/                  # 运维脚本
```

## 快速开始

```bash
# 使用 Docker Compose 启动（推荐开发环境）
docker-compose -f deploy/local/docker-compose.yml up -d

# 或使用 Makefile
make docker-up

# 启动前端开发服务器
cd web && npm install && npm run dev

# 运行测试
pytest tests/
```

## 平台概念

平台包含三个核心层：

1. **Data** - 数据治理与开发平台（DataOps 层）
2. **Model** - 云原生 MLOps 平台（模型/计算层）
3. **Agent** - 大模型应用开发平台（LLMOps 层）

## 架构概览

四层架构（从下到上）：

- **L1 基础设施层**：基于 Kubernetes 的容器编排，包含 CPU/GPU 资源池
- **L2 数据底座层（Data）**：数据集成、ETL、治理、特征存储、向量存储
- **L3 算法引擎层（Model）**：Notebook 开发、分布式训练、支持 OpenAI 兼容 API 的模型服务
- **L4 应用编排层（Agent）**：RAG 流水线、Agent 编排、Prompt 管理

## 关键集成点

三种关键集成模式：

1. **Data → Model**：统一存储协议与数据集版本化。ETL 输出到 MinIO/HDFS，然后自动注册为可被训练任务消费的数据集对象。

2. **Model → Agent**：使用 OpenAI 兼容 API 的模型即服务标准化。通过 vLLM/TGI 部署的模型经由 Istio 网关暴露。

3. **Data → Agent**：基于元数据的 Text-to-SQL。Data 的元数据（表结构、关系）被注入到 Prompt 中用于生成 SQL。

## 开发规范

### 语言

- 所有文档使用中文
- 代码注释可使用中英文

### 代码风格

- Python：使用 `logging` 模块而非 `print()`
- TypeScript：避免使用 `console.log`（仅保留 `console.error`）
- 使用 Mermaid 语法绘制架构图和流程图

### 测试

```bash
# 运行所有测试
pytest tests/

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 运行端到端测试
pytest tests/e2e/
```

## 图表格式

时序图和架构图使用 Mermaid 语法。关键图表包括：

- 构建阶段工作流（数据清洗 → 模型训练 → 部署）
- 运行阶段工作流（RAG + Text-to-SQL 查询流程）
- 四层架构堆栈
