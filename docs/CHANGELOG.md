# Changelog

本文档记录 ONE-DATA-STUDIO 项目的版本变更历史。

---

## [Unreleased] - 2025-01

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
- 聊天历史记录功能待实现 (`web/src/pages/chat/ChatPage.tsx:161`)
- 工作流编辑器实际逻辑待完善

#### 后端
- 向量检索功能使用模拟数据 (`services/bisheng-api/engine/nodes.py:97`)
- 向量数据库删除功能待实现 (`services/bisheng-api/app.py:966`)

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
