# ONE-DATA-STUDIO 文档中心

本文档目录提供 ONE-DATA-STUDIO 项目的完整文档索引。

> **提示**: 首次访问请先阅读 [项目 README](../README.md) 或 [中文版 README](../README_ZH.md) 了解项目概况。

---

## 快速导航

| 文档类型 | 链接 | 说明 |
|----------|------|------|
| 项目 README | [英文](../README.md) / [中文](../README_ZH.md) | 项目概述 |
| 快速开始 | [QUICKSTART](../QUICKSTART.md) | 30 分钟搭建 PoC 环境 |
| 当前状态 | [current-status](03-progress/current-status.md) | 项目进度追踪 |
| 路线图 | [roadmap](05-planning/roadmap.md) | 开发计划与里程碑 |
| 代码审计 | [code-audit](03-progress/code-audit-2026-01-28.md) | 最新代码审计报告 |

---

## 目录结构

```
docs/
├── 00-project/          # 项目概览
├── 01-architecture/     # 架构设计
├── 02-integration/      # 集成方案
├── 03-progress/         # 进度追踪
├── 04-testing/          # 测试文档
├── 05-planning/         # 规划文档
├── 06-development/      # 开发指南
├── 07-operations/       # 运维指南
├── 08-user-guide/       # 用户手册
├── 09-requirements/     # 需求文档
└── 99-archived/         # 归档文档
```

---

## 00 - 项目概览

| 文档 | 说明 |
|------|------|
| [README](00-project/README.md) | 仓库概述和使用指南 |

---

## 01 - 架构设计

| 文档 | 说明 |
|------|------|
| [平台概览](01-architecture/platform-overview.md) | 平台概念与价值主张 |
| [四层架构](01-architecture/four-layer-stack.md) | L1-L4 架构详解 |
| [应用场景](01-architecture/use-cases.md) | 典型应用场景介绍 |
| [技术栈](01-architecture/tech-stack.md) | 技术选型与版本决策 |
| [依赖评估](01-architecture/dependency-assessment.md) | 项目依赖全面评估报告 |

---

## 02 - 集成方案

| 文档 | 说明 |
|------|------|
| [集成总览](02-integration/integration-overview.md) | 三个集成点概览 |
| [Data - Cube](02-integration/alldata-cube.md) | 数据与训练连接 |
| [Cube - Agent](02-integration/cube-bisheng.md) | 模型与应用连接 |
| [Data - Agent](02-integration/alldata-bisheng.md) | 结构化数据与LLM |
| [Behavior Service](02-integration/behavior-service.md) | 用户行为分析服务 |
| [时序图](02-integration/sequence-diagrams.md) | 研发态/运行态流程图 |
| [API 规范](02-integration/api-specifications.md) | 三大集成点 API 接口规范 |
| [API 参考](02-integration/api-reference.md) | API 端点参考文档 |
| [安全设计](02-integration/security-design.md) | 认证鉴权与权限管理方案 |
| [部署架构](02-integration/deployment-architecture.md) | K8s 部署架构与 Helm Chart |
| [用户生命周期](02-integration/user-lifecycle.md) | 用户全生命周期管理 |

---

## 03 - 进度追踪

| 文档 | 说明 |
|------|------|
| [当前状态](03-progress/current-status.md) | 项目进度、里程碑、待办事项 |
| [技术债务清单](03-progress/tech-debt.md) | 技术债务追踪和偿还计划 |

---

## 04 - 测试文档

| 文档 | 说明 |
|------|------|
| [测试计划](04-testing/test-plan.md) | 测试计划和测试策略 |
| [用户生命周期测试用例](04-testing/user-lifecycle-test-cases.md) | 用户生命周期端到端测试用例 |
| [最终改进建议](04-testing/final-improvements.md) | 测试改进建议总结 |

---

## 05 - 规划文档

| 文档 | 说明 |
|------|------|
| [路线图](05-planning/roadmap.md) | 开发计划、里程碑、版本规划 |
| [功能增强计划](05-planning/implementation-plan.md) | 智能大数据平台功能增强计划 (26天工作量) |

---

## 06 - 开发指南

| 文档 | 说明 |
|------|------|
| [PoC 实施手册](06-development/poc-playbook.md) | PoC 环境搭建指南 |
| [API 测试指南](06-development/api-testing-guide.md) | API 测试用例与方法 |
| [代码清理指南](06-development/cleanup-guide.md) | 代码清理最佳实践 |
| [K8s 故障排查](06-development/troubleshooting-k8s.md) | Kubernetes 环境故障排查 |
| [Demo 指南](06-development/demo-guide.md) | 演示环境准备指南 |
| [环境检查清单](06-development/environment-checklist.md) | 开发环境检查清单 |
| [Sprint 计划](06-development/sprint-plan.md) | Sprint 开发计划 |

---

## 07 - 运维指南

| 文档 | 说明 |
|------|------|
| [部署指南](07-operations/deployment.md) | 生产环境部署指南 |
| [运维手册](07-operations/operations-guide.md) | 日常运维操作手册 |
| [Docker 故障排查](07-operations/troubleshooting-docker.md) | Docker Compose 环境故障排查 |
| [故障排查](07-operations/troubleshooting.md) | 通用故障排查指南 |
| [性能调优](07-operations/performance-tuning.md) | 性能优化指南 |
| [灾备恢复](07-operations/disaster-recovery.md) | 灾备与恢复方案 |
| [安全扫描报告](07-operations/security-scan-report.md) | 安全扫描与审计报告 |
| [安全加固](07-operations/security-hardening.md) | 安全加固指南 |

---

## 08 - 用户手册

| 文档 | 说明 |
|------|------|
| [快速入门](08-user-guide/getting-started.md) | 用户快速入门指南 |
| [工作流指南](08-user-guide/workflow-guide.md) | 工作流创建与使用 |

---

## 09 - 需求文档

| 文档 | 说明 |
|------|------|
| [平台建设需求](09-requirements/platform-requirements.md) | 智能大数据平台核心功能需求 |

---

## 文档更新记录

| 日期 | 更新内容 |
|------|----------|
| 2026-01-29 | 新增项目依赖全面评估报告 `01-architecture/dependency-assessment.md` |
| 2026-01-29 | 文档整理：归档过时测试文档，创建技术债务清单，添加 Behavior Service 文档，创建代码清理指南 |
| 2026-01-28 | 文档整理：修复目录编号冲突，归类散落文档，更新代码统计，创建代码审计报告 |
| 2025-01-24 | 删除重复文档 `99-archived/implementation-status.md`，内容已合并到 `03-progress/current-status.md` |
| 2025-01-24 | 更新 Sprint 计划，基于代码实际状态重评估 |
| 2025-01-24 | 添加 06-operations 和 07-user-guide 索引，重命名故障排查文档 |
| 2024-01-23 | 完成设计阶段全部文档，新建开发指南目录 |
| 2024-01-15 | 初始文档结构创建 |

---

## 贡献指南

文档遵循以下规范：

1. **中文编写**：所有文档使用中文
2. **Mermaid 图表**：架构图和流程图使用 Mermaid 语法
3. **Markdown 格式**：遵循 GitHub Flavored Markdown
4. **版本控制**：重要更新请在文末添加更新记录
