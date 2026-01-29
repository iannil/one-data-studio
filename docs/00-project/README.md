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

## 目录文档

| 文档 | 说明 |
|------|------|
| [features.md](./features.md) | 功能清单与完成度 |

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

## 内容语言

所有文档均为中文。在编辑或添加内容时，请保持与现有中文术语和风格的一致性。

## 图表格式

时序图和架构图使用 Mermaid 语法。关键图表包括：

- 构建阶段工作流（数据清洗 → 模型训练 → 部署）
- 运行阶段工作流（RAG + Text-to-SQL 查询流程）
- 四层架构堆栈
