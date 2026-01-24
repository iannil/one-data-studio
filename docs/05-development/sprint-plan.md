# Sprint 计划

本文档提供 ONE-DATA-STUDIO 项目下一阶段（PoC 开发）的详细 Sprint 计划。

---

## Sprint 概览

| Sprint | 周期 | 目标 | 状态 |
|--------|------|------|------|
| Sprint 0 | 1周 | 环境准备与团队组建 | ✅ 已完成 |
| Sprint 1 | 2周 | 基础设施部署 | ✅ 已完成 |
| Sprint 2 | 2周 | L2 数据底座验证 | 🟡 进行中 |
| Sprint 3 | 2周 | L3 模型服务验证 | 🟡 进行中 |
| Sprint 4 | 2周 | L4 应用层验证 | 🟡 进行中 |
| Sprint 5 | 1周 | 端到端集成与 Demo | ⚪ 未开始 |

---

## Sprint 0: 环境准备与团队组建 (1周)

**状态**: ✅ 已完成

### 目标

- 准备开发环境
- 组建开发团队
- 明确分工和协作流程

### 任务清单

| 任务 | 负责人 | 预计工时 | 状态 |
|------|--------|----------|------|
| K8s 测试环境准备 | DevOps | 4h | ✅ |
| 开发工具配置 (Git/Harbor/Jenkins) | DevOps | 4h | ✅ |
| 团队角色分工 | PM | 2h | ✅ |
| 协作流程制定 (站会/评审) | PM | 2h | ✅ |
| 代码仓库初始化 | Tech Lead | 2h | ✅ |
| CI/CD 流水线搭建 | DevOps | 8h | ✅ |

### 交付物

- [x] K8s 测试环境就绪
- [x] Git 仓库创建
- [x] CI/CD 流水线配置
- [x] 团队分工文档

---

## Sprint 1: 基础设施部署 (2周)

**状态**: ✅ 已完成

### 目标

部署存储、中间件和基础服务

### 任务清单

| 任务 | 负责人 | 预计工时 | 状态 |
|------|--------|----------|------|
| MinIO 部署与配置 | DevOps | 4h | ✅ |
| MySQL 主从部署 | DevOps | 8h | ✅ |
| Redis 部署 | DevOps | 4h | ✅ |
| Milvus 部署 | DevOps | 8h | ✅ |
| Keycloak 部署与配置 | DevOps | 8h | ✅ |
| Prometheus + Grafana 部署 | DevOps | 4h | ✅ |
| 基础设施联调测试 | QA | 8h | ✅ |

### 交付物

- [x] 存储服务就绪（MinIO、MySQL、Redis）
- [x] 向量数据库就绪（Milvus）
- [x] 认证服务就绪（Keycloak）
- [x] 监控服务就绪（Prometheus、Grafana）

---

## Sprint 2: L2 数据底座验证 (2周)

**状态**: ✅ 已完成

### 目标

验证 Alldata 数据集注册与读取功能

### 任务清单

| 任务 | 负责人 | 预计工时 | 状态 |
|------|--------|----------|------|
| Alldata API 服务开发 | Backend | 24h | ✅ |
| 数据集注册接口开发 | Backend | 8h | ✅ |
| 数据集查询接口开发 | Backend | 8h | ✅ |
| MinIO 集成测试 | QA | 8h | ✅ |
| Cube SDK 数据读取接口 | Backend | 12h | ✅ |
| 端到端测试 | QA | 8h | ✅ |

### 交付物

- [x] Alldata API 服务
- [x] 数据集 CRUD 接口
- [x] Cube 数据读取 SDK

### 验收标准

```bash
# 注册数据集
curl -X POST http://alldata-api/api/v1/datasets \
  -d '{"name": "test", "path": "s3://bucket/data/"}'

# 查询数据集
curl http://alldata-api/api/v1/datasets/ds-001

# Cube SDK 读取
python -c "from cube_sdk import Dataset; ds = Dataset.get('ds-001'); print(ds.read())"
```

---

## Sprint 3: L3 模型服务验证 (2周)

**状态**: ✅ 已完成

### 目标

验证 Cube 模型推理服务（OpenAI 兼容 API）

### 任务清单

| 任务 | 负责人 | 预计工时 | 状态 |
|------|--------|----------|------|
| vLLM 部署配置 | ML Engineer | 8h | ✅ |
| 模型下载与加载 | ML Engineer | 8h | ✅ |
| OpenAI 兼容接口配置 | ML Engineer | 8h | ✅ |
| Istio Gateway 配置 | DevOps | 4h | ✅ |
| 模型服务测试 | QA | 8h | ✅ |
| Bisheng 调用测试 | Backend | 8h | ✅ |

### 交付物

- [x] vLLM 推理服务
- [x] OpenAI 兼容 API
- [x] Bisheng 调用示例

### 验收标准

```bash
# 列出模型
curl http://cube-serving/v1/models

# 聊天补全
curl -X POST http://cube-serving/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen", "messages": [{"role": "user", "content": "你好"}]}'
```

---

## Sprint 4: L4 应用层验证 (2周)

**状态**: ✅ 已完成

### 目标

验证 Bisheng 应用编排服务

### 任务清单

| 任务 | 负责人 | 预计工时 | 状态 |
|------|--------|----------|------|
| Bisheng API 服务开发 | Backend | 16h | ✅ |
| 模型调用集成 | Backend | 8h | ✅ |
| 数据集查询集成 | Backend | 8h | ✅ |
| 简单 RAG 流水线 | Backend | 16h | ✅ |
| 前端基础页面 | Frontend | 16h | ✅ |
| 聊天历史记录 | Frontend | 8h | 🟡 |
| 工作流编辑器 | Frontend | 16h | ✅ |

### 交付物

- [x] Bisheng API 服务
- [x] 模型调用功能
- [x] 数据集查询功能
- [x] RAG Demo
- [x] 前端 35+ 页面/组件
- [x] React Flow 工作流编辑器

### 验收标准

- Bisheng 可调用 Cube 模型服务
- Bisheng 可查询 Alldata 数据集
- RAG 流水线端到端可用

---

## Sprint 5: 端到端集成与 Demo (1周)

**状态**: ⚪ 未开始

### 目标

完成端到端集成验证，准备 Demo 演示

### 任务清单

| 任务 | 负责人 | 预计工时 | 状态 |
|------|--------|----------|------|
| 端到端流程测试 | QA | 8h | ⚪ |
| Bug 修复 | All | 16h | ⚪ |
| Demo 场景准备 | All | 8h | ⚪ |
| Demo 演示文稿 | PM | 4h | ⚪ |
| 文档整理 | All | 4h | ⚪ |

### 交付物

- [ ] 端到端测试报告
- [ ] Demo 演示视频/PPT
- [ ] 用户手册初稿

### 验收标准

- 三大集成点全部验证通过
- Demo 演示流畅无报错
- 文档完整可用

---

## 每日站会模板

### 时间

每天 10:00，限时 15 分钟

### 格式

| 人员 | 昨日完成 | 今日计划 | 阻塞问题 |
|------|----------|----------|----------|
| @张三 | 完成数据集注册接口 | 开发查询接口 | 无 |
| @李四 | 完成 vLLM 部署 | 配置 Istio Gateway | GPU 不足 |

---

## Sprint 评审模板

### 评审议程

1. Sprint 目标回顾 (5min)
2. 交付物演示 (20min)
3. 遗留问题讨论 (10min)
4. 下一 Sprint 计划 (10min)

### 评审检查清单

- [ ] 所有 Story 完成
- [ ] 测试用例通过
- [ ] 代码已 Review
- [ ] 文档已更新

---

## 风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| GPU 资源不足 | Sprint 3 延期 | 使用小模型或云 GPU |
| 人员变动 | Sprint 延期 | 交叉培训，知识共享 |
| 需求变更 | Sprint 返工 | 锁定 Scope，变更走评审 |
| 集成问题 | Sprint 4/5 延期 | 提前进行集成测试 |

---

## 更新记录

| 日期 | Sprint | 更新内容 |
|------|--------|----------|
| 2024-01-23 | - | 创建 Sprint 计划模板 |
| 2025-01-23 | 0-1 | 标记 Sprint 0-1 为已完成 |
| 2025-01-23 | 2-4 | 更新 Sprint 2-4 状态为进行中 |
| 2025-01-23 | - | 标记为开源项目，负责人为"欢迎贡献" |
