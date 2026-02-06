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

## 已知问题

### 测试覆盖
- 当前: 多个页面测试文件已创建但未追踪
- 目标: 80%+ 覆盖率

### 未追踪文件
```
?? web/coverage/
?? web/docs/
?? web/src/pages/portal/*.test.tsx
?? web/src/pages/scheduler/*.test.tsx
```

## 经验教训

> 避免重复过去的错误

*（此部分将在项目中积累经验后填充）*

## 最后更新

- **日期**: 2026-02-06
- **操作**: 记忆系统初始化
