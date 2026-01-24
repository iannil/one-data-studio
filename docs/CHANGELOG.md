# Changelog

本文档记录 ONE-DATA-STUDIO 项目的版本变更历史。

---

## [0.2.0] - 2025-01-24

### Added

#### 新增前端页面
- **Text2SQL 页面** - Text-to-SQL 生成和执行 (`web/src/pages/text2sql/`)
- **Agents 页面组** - Agent 管理、模板、工具执行 (`web/src/pages/agents/`)
  - AgentTemplatesModal - Agent 模板选择
  - SchemaViewer - Schema 查看器
  - StepsViewer - 步骤查看器
  - ToolExecuteModal - 工具执行弹窗
- **Documents 页面** - 文档管理 (`web/src/pages/documents/`)
- **Executions 页面** - 执行历史看板 (`web/src/pages/executions/`)
- **Schedules 页面** - 调度管理 (`web/src/pages/schedules/`)

#### 新增前端组件
- **工作流编辑器** - React Flow 可视化编辑器
  - FlowCanvas - 流程图画布
  - NodePalette - 节点面板
  - NodeConfigPanel - 节点配置面板
  - 9 种节点类型组件（Agent, LLM, Retriever, ToolCall, Condition, Loop, Input, Output, Think）

#### 后端功能增强
- **Agent 系统** - ReAct Agent 实现，支持工具调用
- **调度系统** - 支持 Cron、Interval、Event 触发
- **向量存储服务** - Milvus 集成，支持文档删除
- **执行追踪** - 工作流执行统计和历史记录

### Changed

#### 代码质量
- **日志规范化** - 11 个 Python 文件的 `print()` 替换为 `logging`
- **调试代码清理** - TypeScript 文件移除 `console.log`，保留 `console.error`
- **Mock 服务清理** - 删除 `docs/99-archived/mock-services/` 目录

### Fixed

- 修复向量数据库删除功能（向量索引同步删除）
- 修复调度器暂停/恢复功能

---

## [0.1.0] - 2025-01

### Added

#### 前端 (web/)
- React + TypeScript + Vite 项目结构
- Ant Design 5.14.0 UI 组件库集成
- React Router 6.22.0 路由系统
- React Query 5.24.0 + Zustand 4.5.0 状态管理
- Keycloak SSO 认证集成（支持模拟登录）
- 登录页 (`pages/LoginPage.tsx`)
- 首页 (`pages/HomePage.tsx`)
- 数据集管理页 (`pages/datasets/`)
- 聊天页 (`pages/chat/ChatPage.tsx`) - 支持流式聊天
- 元数据页 (`pages/metadata/`)
- 工作流页 (`pages/workflows/`) - 基础结构

#### 后端 (docker/)
- **Alldata API** (Flask)
  - 数据集注册、查询、更新、删除接口
  - 元数据查询接口
  - MinIO 数据源集成
  - 数据库模型和迁移

- **OpenAI Proxy** (FastAPI)
  - OpenAI 兼容 API (`/v1/chat/completions`)
  - 模型列表接口 (`/v1/models`)
  - 流式响应支持 (SSE)

- **Bisheng API** (Flask)
  - 工作流 CRUD 接口
  - 工作流执行接口
  - Prompt 模板管理
  - 知识库文档管理
  - 向量集合列表
  - 引擎节点系统（RAG、LLM 节点）

#### 部署
- **Docker Compose** 完整服务编排
  - Web 前端
  - Alldata API
  - OpenAI Proxy
  - Bisheng API
  - MySQL、Redis、MinIO、Keycloak
- **Kubernetes** 部署配置
  - 基础设施服务 (MySQL, Redis, MinIO, Milvus, Keycloak)
  - 应用服务 (Alldata API, Bisheng API, OpenAI Proxy, Web Frontend, vLLM Serving)
  - HPA 自动扩缩容策略
- **Helm Charts** 结构
- 部署脚本
  - `deploy-phase1.sh` - Phase 1 基础设施部署
  - `deploy-phase2.sh` - Phase 2 应用服务部署
  - `test-all.sh` - 全量测试
  - `test-e2e.sh` - 端到端测试
  - `clean.sh` - 清理脚本

#### 文档
- 架构设计文档 (`01-architecture/`)
- 集成方案文档 (`02-integration/`)
- 进度追踪文档 (`03-progress/`)
- 规划文档 (`04-planning/`)
- 开发指南 (`05-development/`)

### Changed

#### 文档整理
- 更新项目进度文档，反映实际开发状态
- 标记项目为开源项目
- 创建详细的代码实现状态追踪文档
- 更新 Sprint 计划，标记已完成的任务

#### 清理
- 删除空目录 (`web/src/utils/`, `web/src/hooks/`, `web/src/assets/`)
- 删除空示例目录 (`examples/go/`, `examples/java/`)
- 归档 Mock 服务配置到 `docs/99-archived/mock-services/`

### Known Issues

#### 前端
- 聊天历史记录 API 待实现 (`web/src/pages/chat/ChatPage.tsx`)
- Agent 编辑器可视化待完善

#### 后端
- 向量检索功能使用模拟数据，需集成真实 Milvus (`services/bisheng-api/engine/nodes.py`)
- 聊天历史记录 API 待实现

---

## Version History

| 版本 | 日期 | 说明 |
|------|------|------|
| 0.2.0 | 2025-01-24 | 新增 10+ 页面，Agent 系统，调度系统 |
| 0.1.0 | 2025-01-23 | 开发中版本，PoC 阶段 |

---

## Version History

| 版本 | 日期 | 说明 |
|------|------|------|
| 0.1.0-dev | 2025-01 | 开发中版本，PoC 阶段 |

---

## 计划中的功能

### Sprint 4 (进行中)
- [ ] 聊天历史记录功能
- [ ] 向量检索功能实现
- [ ] 工作流编辑器完善

### Sprint 5 (未开始)
- [ ] 端到端集成测试
- [ ] Demo 准备

### Sprint 6 (未开始)
- [ ] 向量数据库删除功能
- [ ] 性能优化

---

## 贡献指南

欢迎贡献！请查看：
- 架构设计：`docs/01-architecture/`
- API 规范：`docs/02-integration/api-specifications.md`
- 开发指南：`docs/05-development/`
