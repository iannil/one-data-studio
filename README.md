# ONE-DATA-STUDIO

> 企业级 DataOps + MLOps + LLMOps 全栈智能基础设施

## 简介

ONE-DATA-STUDIO 是一个融合平台设计，整合了三个企业级 AI 平台：

* **Alldata** - 数据治理与开发平台（DataOps 层）
* **Cube Studio** - 云原生 MLOps 平台（模型/计算层）
* **Bisheng** - 大模型应用开发平台（LLMOps 层）

这个平台打通了从**原始数据治理**到**模型训练部署**，再到**生成式AI应用构建**的完整价值链。

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                     L4 应用编排层 (Bisheng)                      │
│                  RAG 流水线 | Agent 编排 | Prompt 管理             │
└─────────────────────────────────────────────────────────────────┘
                              ↕ OpenAI API / 元数据
┌─────────────────────────────────────────────────────────────────┐
│                    L3 算法引擎层 (Cube Studio)                   │
│            Notebook | 分布式训练 | 模型仓库 | 模型服务化           │
└─────────────────────────────────────────────────────────────────┘
                              ↕ 挂载数据卷
┌─────────────────────────────────────────────────────────────────┐
│                    L2 数据底座层 (Alldata)                       │
│          数据集成 | ETL | 数据治理 | 特征存储 | 向量存储           │
└─────────────────────────────────────────────────────────────────┘
                              ↕ 存储协议
┌─────────────────────────────────────────────────────────────────┐
│                    L1 基础设施层 (K8s)                           │
│              CPU/GPU 资源池 | 存储 | 网络 | 监控                  │
└─────────────────────────────────────────────────────────────────┘
```

## 文档导航

### 项目概览

| 文档 | 说明 |
|------|------|
| [项目说明](docs/00-project/README.md) | 仓库概述和使用指南 |
| [当前状态](docs/03-progress/current-status.md) | 项目进度与待办事项 |
| [路线图](docs/04-planning/roadmap.md) | 开发计划与里程碑 |

### 架构设计

| 文档 | 说明 |
|------|------|
| [平台概览](docs/01-architecture/platform-overview.md) | 平台概念与价值主张 |
| [四层架构](docs/01-architecture/four-layer-stack.md) | L1-L4 架构详解 |
| [应用场景](docs/01-architecture/use-cases.md) | 典型应用场景介绍 |
| [技术栈](docs/01-architecture/tech-stack.md) | 技术选型与版本 |

### 集成方案

| 文档 | 说明 |
|------|------|
| [集成总览](docs/02-integration/integration-overview.md) | 三个集成点概览 |
| [Alldata ↔ Cube](docs/02-integration/alldata-cube.md) | 数据与训练连接 |
| [Cube ↔ Bisheng](docs/02-integration/cube-bisheng.md) | 模型与应用连接 |
| [Alldata ↔ Bisheng](docs/02-integration/alldata-bisheng.md) | 结构化数据与LLM |
| [时序图](docs/02-integration/sequence-diagrams.md) | 研发态/运行态流程图 |

### 设计规范

| 文档 | 说明 |
|------|------|
| [API 规范](docs/02-integration/api-specifications.md) | 三大集成点 API 接口规范 |
| [安全设计](docs/02-integration/security-design.md) | 认证鉴权与权限管理方案 |
| [部署架构](docs/02-integration/deployment-architecture.md) | K8s 部署架构与 Helm Chart |

### 开发指南

| 文档 | 说明 |
|------|------|
| [PoC 实施手册](docs/05-development/poc-playbook.md) | PoC 环境搭建指南 |
| [API 测试指南](docs/05-development/api-testing-guide.md) | API 测试用例与方法 |

## 核心集成点

1. **Alldata → Cube Studio**：统一存储协议与数据集版本化
2. **Cube Studio → Bisheng**：OpenAI 兼容的模型即服务
3. **Alldata → Bisheng**：基于元数据的 Text-to-SQL

## 典型应用场景

* **企业知识中台**：统一管理企业文档知识，提供智能问答
* **ChatBI**：用自然语言查询数据库，自动生成报表
* **工业质检**：传感器数据实时分析，预测性维护

## 许可证

[待补充]
