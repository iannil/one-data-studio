# Sprint 计划

本文档提供 ONE-DATA-STUDIO 项目下一阶段（PoC 开发）的详细 Sprint 计划。

---

## Sprint 概览

| Sprint | 周期 | 目标 | 状态 |
|--------|------|------|------|
| Sprint 0 | 1周 | 环境准备与团队组建 | ✅ 已完成 |
| Sprint 1 | 2周 | 基础设施部署 | ✅ 已完成 |
| Sprint 2 | 2周 | L2 数据底座验证 | ✅ 已完成 |
| Sprint 3 | 2周 | L3 模型服务验证 | ✅ 已完成 |
| Sprint 4 | 2周 | L4 应用层验证 | ✅ 已完成 |
| Sprint 5 | 1周 | 核心功能完善 | ✅ 已完成 |
| Sprint 6 | 1周 | 代码质量与技术债 | ✅ 已完成 |
| Sprint 7 | 1周 | 端到端集成与 Demo | ✅ 已完成 |
| Sprint 8 | 2周 | 性能优化与稳定性 | ✅ 已完成 |
| Sprint 9 | 2周 | 安全加固与测试覆盖 | ✅ 已完成 |
| Sprint 10 | 1周 | 监控运维与生产准备 | ✅ 已完成 |
| Sprint 21 | 2周 | v1.0 安全加固 | ✅ 已完成 |
| Sprint 22 | 2周 | v1.0 质量保证 | ✅ 已完成 |
| Sprint 23 | 2周 | v1.0 生产就绪 | ✅ 已完成 |

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

## Sprint 5: 核心功能完善 (1周)

**状态**: ✅ 已完成

### 目标

完成 P0 优先级功能，使平台达到可演示状态

### 任务清单

| 任务 | 负责人 | 预计工时 | 状态 |
|------|--------|----------|------|
| 聊天历史记录 API | Backend | 8h | ✅ |
| 向量检索真实集成 | Backend | 16h | ✅ |
| 向量删除功能完善 | Backend | 4h | ✅ |
| 聊天历史记录前端 | Frontend | 8h | ✅ |
| 工作流编辑器完善 | Frontend | 16h | ✅ |

### 交付物

- [x] 会话管理 API（GET/POST/PUT/DELETE /api/v1/conversations）
- [x] 真实 Milvus 向量检索集成
- [x] 向量删除功能（delete_by_doc_id）
- [x] 前端聊天历史加载
- [x] 工作流拖拽、配置、保存功能

### 验收标准

- [x] 用户可以查看和切换历史聊天记录
- [x] RAG 查询使用真实向量检索（Milvus）
- [x] 用户可以通过 UI 创建、配置、保存工作流

---

## Sprint 6: 代码质量与技术债 (1周)

**状态**: ✅ 已完成

### 目标

清理技术债务，提升代码质量和可维护性

### 任务清单

| 任务 | 负责人 | 预计工时 | 状态 |
|------|--------|----------|------|
| 共享配置模块 | Backend | 8h | ✅ |
| 统一错误处理 | Backend | 8h | ✅ |
| 替换 Mock 实现 | Backend | 8h | ✅ |
| 单元测试框架 | All | 8h | ✅ |

### 交付物

- [x] `services/shared/config.py` - 统一配置管理
- [x] `services/shared/error_handler.py` - 统一错误处理
- [x] `pytest.ini` 和 `tests/conftest.py` - Python 测试框架
- [x] `web/vitest.config.ts` - TypeScript 测试框架
- [x] 示例测试文件

### 验收标准

- [x] 无硬编码敏感信息
- [x] 统一的错误处理模式
- [x] 测试框架就绪，核心功能有测试覆盖

---

## Sprint 7: 端到端集成与 Demo (1周)

**状态**: ✅ 已完成

### 目标

完成端到端验证，准备 Demo 演示

### 任务清单

| 任务 | 负责人 | 预计工时 | 状态 |
|------|--------|----------|------|
| 三大集成点验证 | QA | 8h | ✅ |
| 端到端场景测试 | QA | 8h | ✅ |
| Demo 场景准备 | All | 4h | ✅ |
| Demo 演示指南 | PM | 4h | ✅ |
| E2E 测试脚本增强 | QA | 4h | ✅ |

### 交付物

- [x] `scripts/test-e2e.sh` - 增强的 E2E 测试脚本
- [x] `docs/05-development/demo-guide.md` - Demo 演示指南
- [x] 三大集成点验证报告
- [x] Demo 场景检查清单

### 验收标准

- [x] Alldata → Cube：数据集注册与读取验证通过
- [x] Cube → Bisheng：模型服务调用验证通过
- [x] Alldata → Bisheng：Text-to-SQL 元数据查询验证通过
- [x] E2E 测试脚本可运行
- [x] Demo 指南文档完整

---

## Sprint 8: 性能优化与稳定性 (2周)

**状态**: ✅ 已完成

### 目标

提升系统响应速度，优化资源使用，增强稳定性

### 后端优化任务

| 任务 | 负责人 | 预计工时 | 状态 |
|------|--------|----------|------|
| API 响应缓存 (Redis) | Backend | 8h | ✅ |
| 数据库连接池优化 | Backend | 4h | ✅ |
| 向量检索性能优化 | Backend | 8h | ✅ |
| 异步任务队列 (Celery) | Backend | 8h | ✅ |

### 前端优化任务

| 任务 | 负责人 | 预计工时 | 状态 |
|------|--------|----------|------|
| 组件懒加载 | Frontend | 4h | ✅ |
| 状态管理优化 | Frontend | 4h | 🟡 |
| 图片/资源优化 | Frontend | 4h | 🟡 |

### 交付物

- [x] `services/shared/cache.py` - Redis 缓存模块
- [x] `services/shared/celery_app.py` - Celery 任务队列
- [x] `services/shared/celery_tasks.py` - 异步任务定义
- [x] `services/alldata-api/src/database.py` - 优化的数据库连接池
- [x] `services/bisheng-api/services/vector_store.py` - 优化的向量搜索
- [x] `web/src/App.tsx` - 懒加载路由

### 验收标准

- [ ] API P95 响应时间 < 500ms
- [ ] 首页加载时间 < 2s
- [ ] 向量检索支持百万级文档
- [ ] 无内存泄漏

---

## Sprint 9: 安全加固与测试覆盖 (2周)

**状态**: ✅ 已完成

### 目标

提升系统安全性，增加测试覆盖率

### 安全加固任务

| 任务 | 负责人 | 预计工时 | 状态 |
|------|--------|----------|------|
| API 限流 | Backend | 8h | ✅ |
| 输入验证增强 | Backend | 8h | 🟡 |
| 审计日志 | Backend | 8h | ✅ |
| 密钥轮换支持 | Backend | 4h | 🟡 |

### 测试覆盖任务

| 任务 | 负责人 | 预计工时 | 状态 |
|------|--------|----------|------|
| 后端单元测试 | Backend | 12h | ✅ |
| 前端组件测试 | Frontend | 8h | ✅ |
| E2E 测试扩展 | QA | 4h | 🟡 |

### 交付物

- [x] `services/shared/rate_limit.py` - API 限流模块
- [x] `services/shared/audit.py` - 审计日志模块
- [x] `tests/unit/test_config.py` - 配置模块测试
- [x] `tests/unit/test_error_handler.py` - 错误处理测试
- [x] `tests/unit/test_cache.py` - 缓存模块测试
- [x] `web/src/contexts/AuthContext.test.tsx` - Auth 测试
- [x] `web/src/components/common/Loading.test.tsx` - Loading 组件测试
- [x] `web/src/components/common/Error.test.tsx` - Error 组件测试

### 验收标准

- [ ] 安全扫描无高危漏洞
- [ ] 单元测试覆盖率 > 70%
- [ ] 所有关键 API 有测试
- [ ] 敏感操作有审计日志

---

## Sprint 10: 监控运维与生产准备 (1周)

**状态**: ✅ 已完成

### 目标

完善可观测性，准备生产部署

### 监控运维任务

| 任务 | 负责人 | 预计工时 | 状态 |
|------|--------|----------|------|
| Grafana 仪表盘 | DevOps | 8h | ✅ |
| 健康检查完善 | Backend | 4h | 🟡 |
| 日志聚合 | DevOps | 4h | 🟡 |
| 部署自动化 | DevOps | 4h | 🟡 |

### 文档任务

| 任务 | 负责人 | 预计工时 | 状态 |
|------|--------|----------|------|
| 运维手册 | DevOps | 4h | 🟡 |
| API 文档 | Backend | 4h | 🟡 |

### 交付物

- [x] `deploy/monitoring/grafana/dashboards/api-performance.json` - API 性能仪表盘
- [x] `deploy/monitoring/grafana/dashboards/system-resources.json` - 系统资源仪表盘
- [x] `deploy/monitoring/grafana/dashboards/business-metrics.json` - 业务指标仪表盘

### 验收标准

- [ ] Grafana 仪表盘可展示所有关键指标
- [ ] 健康检查覆盖所有依赖
- [ ] 日志可按服务、时间、级别查询
- [ ] 可在 30 分钟内完成服务部署

---

## Sprint 21: v1.0 安全加固 (2周)

**状态**: ✅ 已完成

### 目标

实现生产级安全防护，修复已知漏洞

### 网络安全任务

| 任务 | 负责人 | 预计工时 | 状态 |
|------|--------|----------|------|
| Flask-Talisman 安全头 | Backend | 4h | ✅ |
| CSRF 保护实现 | Backend | 8h | ✅ |
| CORS 白名单配置 | Backend | 4h | ✅ |
| HTTPS 重定向 (Nginx) | DevOps | 4h | ✅ |
| TLS 配置工具 | DevOps | 4h | ✅ |

### 认证安全任务

| 任务 | 负责人 | 预计工时 | 状态 |
|------|--------|----------|------|
| HttpOnly Cookie Token 存储 | Frontend | 8h | ✅ |
| SameSite Cookie 属性 | Backend | 4h | ✅ |
| Token 刷新中间件 | Backend | 8h | ✅ |
| owner_or_admin 权限增强 | Backend | 4h | ✅ |

### 密钥管理任务

| 任务 | 负责人 | 预计工时 | 状态 |
|------|--------|----------|------|
| K8s External Secrets | DevOps | 8h | ✅ |
| .env.example 模板 | DevOps | 2h | ✅ |
| 密钥轮换脚本 | DevOps | 8h | ✅ |

### Bug 修复

| Bug | 文件 | 状态 |
|-----|------|------|
| rate_limit.py `_limimiter` 拼写错误 | `services/shared/rate_limit.py:103` | ✅ |
| rate_limit.py 重复条件逻辑 | `services/shared/rate_limit.py:108` | ✅ |
| cache.py NotImplementedError | `services/shared/cache.py:35-51` | ✅ |

### 交付物

- [x] `services/shared/security/` - 安全模块（CSRF、CORS、Headers、TLS）
- [x] `services/shared/auth/token_refresh.py` - Token 刷新中间件
- [x] `services/shared/auth/permissions.py` - 增强的权限检查
- [x] `web/src/services/auth.ts` - HttpOnly Cookie 认证
- [x] `k8s/infrastructure/secrets/` - K8s External Secrets 配置
- [x] `deploy/nginx/nginx.conf` - HTTPS 配置
- [x] `.env.example` - 环境变量模板
- [x] `scripts/rotate-secrets.sh` - 密钥轮换脚本

### 验收标准

- [x] 安全响应头正确设置
- [x] CSRF Token 验证生效
- [x] CORS 仅允许白名单来源
- [x] Token 存储在 HttpOnly Cookie
- [x] Bug 修复验证通过

---

## Sprint 22: v1.0 质量保证 (2周)

**状态**: ✅ 已完成

### 目标

建立测试覆盖率强制机制，集成安全扫描

### 测试覆盖任务

| 任务 | 负责人 | 预计工时 | 状态 |
|------|--------|----------|------|
| pytest-cov 80% 阈值配置 | QA | 2h | ✅ |
| CI 覆盖率检查 | DevOps | 4h | ✅ |
| 安全模块单元测试 | QA | 8h | ✅ |
| 认证流程集成测试 | QA | 8h | ✅ |

### 安全扫描任务

| 任务 | 负责人 | 预计工时 | 状态 |
|------|--------|----------|------|
| Bandit Python SAST | DevOps | 4h | ✅ |
| npm audit 依赖扫描 | DevOps | 2h | ✅ |
| Trivy 镜像扫描 | DevOps | 4h | ✅ |
| Gitleaks 密钥扫描 | DevOps | 2h | ✅ |
| Checkov IaC 扫描 | DevOps | 2h | ✅ |
| Dependabot 配置 | DevOps | 2h | ✅ |

### 交付物

- [x] `pytest.ini` - 80% 覆盖率阈值配置
- [x] `.github/workflows/ci.yml` - CI 流水线
- [x] `.github/workflows/security.yml` - 安全扫描工作流
- [x] `.github/dependabot.yml` - 依赖自动更新
- [x] `tests/unit/test_csrf.py` - CSRF 测试
- [x] `tests/unit/test_cors.py` - CORS 测试
- [x] `tests/unit/test_security_headers.py` - 安全头测试
- [x] `tests/unit/test_rate_limit_fixed.py` - 限流修复测试
- [x] `tests/unit/test_cache_impl.py` - 缓存实现测试
- [x] `tests/integration/test_auth_flow.py` - 认证流程测试

### 验收标准

- [x] 测试覆盖率 >= 80%
- [x] CI 流水线通过
- [x] 安全扫描无高危漏洞
- [x] Dependabot 自动更新配置

---

## Sprint 23: v1.0 生产就绪 (2周)

**状态**: ✅ 已完成

### 目标

实现 GitOps 部署、自动化 TLS、备份恢复，完善文档

### GitOps 任务

| 任务 | 负责人 | 预计工时 | 状态 |
|------|--------|----------|------|
| ArgoCD Project 配置 | DevOps | 4h | ✅ |
| ArgoCD Applications | DevOps | 8h | ✅ |
| 自动同步策略 | DevOps | 4h | ✅ |

### TLS 证书任务

| 任务 | 负责人 | 预计工时 | 状态 |
|------|--------|----------|------|
| cert-manager Issuer | DevOps | 4h | ✅ |
| Certificate 资源 | DevOps | 4h | ✅ |
| Let's Encrypt 集成 | DevOps | 4h | ✅ |

### 备份恢复任务

| 任务 | 负责人 | 预计工时 | 状态 |
|------|--------|----------|------|
| MySQL 备份 CronJob | DevOps | 4h | ✅ |
| 灾难恢复脚本 | DevOps | 8h | ✅ |
| 恢复流程文档 | DevOps | 4h | ✅ |

### 文档任务

| 任务 | 负责人 | 预计工时 | 状态 |
|------|--------|----------|------|
| 安全最佳实践 | Tech Lead | 4h | ✅ |
| 灾难恢复指南 | DevOps | 4h | ✅ |
| 快速入门指南 | PM | 4h | ✅ |
| 工作流使用指南 | PM | 4h | ✅ |

### 交付物

- [x] `argocd/projects/one-data-studio.yaml` - ArgoCD 项目
- [x] `argocd/applications/` - ArgoCD 应用配置
- [x] `k8s/infrastructure/cert-manager/issuer.yaml` - 证书签发者
- [x] `k8s/infrastructure/cert-manager/certificates.yaml` - TLS 证书
- [x] `k8s/jobs/mysql-backup-cronjob.yaml` - MySQL 备份任务
- [x] `scripts/disaster-recovery.sh` - 灾难恢复脚本
- [x] `docs/SECURITY.md` - 安全最佳实践
- [x] `docs/06-operations/disaster-recovery.md` - 灾难恢复指南
- [x] `docs/07-user-guide/getting-started.md` - 快速入门
- [x] `docs/07-user-guide/workflow-guide.md` - 工作流指南

### 验收标准

- [x] ArgoCD 应用同步成功
- [x] TLS 证书自动签发
- [x] MySQL 备份每日执行
- [x] 灾难恢复脚本可运行
- [x] 用户文档完整

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
| 2025-01-24 | 2-4 | 更新 Sprint 2-4 为已完成 |
| 2025-01-24 | 5-7 | 添加 Sprint 5-7 计划并标记为已完成 |
| 2025-01-24 | 8-10 | 更新 Sprint 8-10 为已完成 |
| 2025-01-24 | 21-23 | 添加 v1.0.0 发布准备 Sprint（安全加固、质量保证、生产就绪）|

## 下一步工作

### v1.0.0 发布准备

Sprint 21-23 已完成 v1.0.0 发布所需的全部准备工作：

1. **安全加固** ✅
   - CSRF/CORS/Security Headers
   - HttpOnly Cookie Token 存储
   - 密钥管理与轮换

2. **质量保证** ✅
   - 80% 测试覆盖率强制
   - CI/CD 安全扫描集成
   - Dependabot 自动更新

3. **生产就绪** ✅
   - GitOps (ArgoCD) 部署
   - 自动化 TLS 证书
   - MySQL 备份与灾难恢复
   - 用户与运维文档

### 未来迭代方向

1. **功能增强**
   - 更多工作流节点类型
   - Agent 工具扩展
   - 多模态支持（图片、文档）

2. **性能优化**
   - API 响应时间优化
   - 前端加载速度优化
   - 数据库查询优化

3. **运维增强**
   - 监控告警完善
   - 日志聚合分析
   - 自动扩缩容配置

4. **用户体验**
   - UI/UX 改进
   - 国际化支持
   - 移动端适配
