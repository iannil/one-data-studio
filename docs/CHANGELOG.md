# Changelog

本文档记录 ONE-DATA-STUDIO 项目的版本变更历史。

---

## [1.3.2] - 2026-01-29

### Added

- `docs/01-architecture/dependency-assessment.md` - 项目依赖全面评估报告
  - 基础设施层依赖（K8s、Docker、Istio、监控栈）
  - 数据库与存储（MySQL、Redis、Milvus、MinIO、ES）
  - 数据处理与 ETL（Flink、Spark、Kettle）
  - AI/ML 推理与框架（vLLM、PyTorch、PaddlePaddle）
  - OCR 与文档处理（PaddleOCR、PyMuPDF）
  - Python 后端依赖（50+ 库）
  - 前端技术栈（40+ 库）
  - 许可证风险评估与注意事项

---

## [1.3.1] - 2026-01-29

### Changed

#### 文档整理与项目梳理

**文档归档**
- 归档过时测试文档到 `docs/99-archived/testing-2025/`（7个文件）
- 更新 `docs/04-testing/README.md`，移除已归档文档链接
- 合并代码审计报告到 `docs/03-progress/current-status.md`

**新增文档**
- `docs/03-progress/tech-debt.md` - 技术债务清单
- `docs/02-integration/behavior-service.md` - Behavior Service 集成文档
- `docs/06-development/cleanup-guide.md` - 代码清理指南

**文档索引更新**
- 更新 `docs/README.md`，添加 Behavior Service 链接
- 更新测试文档索引，添加测试统计信息

### Removed

- `tests/run_tests.py` - 与 `tests/run_tests.sh` 功能重复，删除 Python 版本

### Fixed

- 更新 `.gitignore`，添加 `coverage.xml`、`*.xml`、`reports/` 等测试生成文件

---

## [1.3.0] - 2026-01-28

### Changed

#### 文档整理与更新

**目录编号修复**
- 修复 `03-testing` 与 `03-progress` 编号冲突
- 重新编号: `03-testing` → `04-testing`, `04-planning` → `05-planning`, `05-development` → `06-development`, `06-operations` → `07-operations`, `07-user-guide` → `08-user-guide`
- 新建 `09-requirements/` 需求文档目录

**散落文档归类**
- `docs/user-lifecycle.md` → `docs/02-integration/user-lifecycle.md`
- `docs/implementation-plan.md` → `docs/05-planning/implementation-plan.md`
- `docs/智能大数据平台建设内容v2.txt` → `docs/09-requirements/platform-requirements.md`（转换为 Markdown）

**代码统计更新**
- Python 后端: 86+ → 274 文件, 142,887 行
- TypeScript 前端: 62+ → 216 文件, 120,334 行
- 测试代码: 24+ → 71 文件, 30,111 行
- 部署配置: 30+ → 155 文件

### Added

- `docs/03-progress/code-audit-2026-01-28.md` - 代码审计报告
- `docs/09-requirements/platform-requirements.md` - 原始需求文档（Markdown 版）
- `docs/09-requirements/README.md` - 需求文档目录说明
- 服务完成度矩阵（8 个服务的详细状态）
- 技术债务清单（TODO 项、未部署服务）

---

## [1.2.0] - 2025-01-24

### Added

#### Sprint 32: 开发体验优化

**工作流版本控制**
- `services/agent-api/services/workflow_diff.py` - 工作流差异比较服务
  - `WorkflowVersion` 版本数据模型
  - `WorkflowDiffEngine` 差异计算引擎
  - `WorkflowVersionManager` 版本管理器
  - 节点/边/元数据级别差异比较
  - 版本回滚支持
  - 统一差异文本输出
- `web/src/components/workflow/VersionHistory.tsx` - 版本历史组件
  - 版本列表展示
  - 版本对比功能
  - 回滚确认对话框
  - 差异可视化（节点/边/原始）

**Token 成本追踪**
- `services/agent-api/services/cost_tracker.py` - 成本追踪服务
  - `CostTracker` 成本追踪器
  - `TokenCounter` Token 计数工具（支持 tiktoken）
  - `CostRecord` 成本记录数据模型
  - `CostSummary` 成本汇总报表
  - 按模型/用户/工作流维度统计
  - 预算检查和剩余预算查询
  - 每日成本分解
  - `@track_cost` 装饰器自动追踪
- `web/src/pages/admin/CostReportPage.tsx` - 成本报表页面
  - 统计卡片（总成本/总Token/平均成本）
  - 每日成本趋势图
  - 模型成本分布饼图
  - 用户排行榜
  - 详细记录表格
  - CSV 导出功能

---

#### Sprint 31: 生产就绪增强

**告警规则配置**
- `deploy/monitoring/prometheus/rules/alerts.yaml` - Prometheus 告警规则
  - API 性能告警（延迟、错误率）
  - Pod 健康告警（重启、内存、CPU）
  - 数据库告警（MySQL、Milvus）
  - 存储告警（磁盘、PVC）
  - 断路器告警
  - 证书过期告警
  - LLM 服务告警

**AlertManager 集成**
- `deploy/monitoring/alertmanager/config.yaml` - AlertManager 配置
  - 告警路由（按严重程度/团队）
  - Slack 通知（多频道）
  - PagerDuty 集成（关键告警）
  - 抑制规则（防止告警风暴）
- `deploy/monitoring/alertmanager/templates/slack.tmpl` - 通知模板
  - Slack 消息模板
  - PagerDuty 描述模板
  - Email HTML 模板

**断路器监控**
- `services/shared/circuit_breaker.py` - Prometheus 指标导出
  - `circuit_breaker_state` 状态 Gauge
  - `circuit_breaker_calls_total` 调用计数器
  - `circuit_breaker_failures_total` 失败计数器
  - `circuit_breaker_rejected_total` 拒绝计数器
  - `circuit_breaker_failure_rate` 失败率 Gauge
  - `circuit_breaker_call_duration_seconds` 延迟直方图
- `deploy/monitoring/grafana/dashboards/circuit-breaker.json` - 断路器仪表盘
  - 状态总览面板
  - 失败率时序图
  - 调用率时序图
  - 拒绝率时序图
  - 延迟分位数图
  - 状态时间线

**灾难恢复完善**
- `scripts/disaster-recovery.sh` - 完整恢复脚本
  - `restore_milvus()` Milvus 向量库恢复
  - `restore_minio()` MinIO 对象存储恢复
  - `test_restore()` 恢复测试（staging 环境）
  - `calculate_rto()` RTO 计算

---

#### Sprint 30: API 成熟度提升

**速率限制响应头**
- `services/shared/rate_limit.py` - RFC 6585 响应头
  - `RateLimitChecker` 限制检查器
  - `RateLimitHeaders` 响应头数据类
  - `rate_limit_middleware` 自动添加响应头中间件
  - X-RateLimit-Limit/Remaining/Reset 头
  - Retry-After 头（限流时）

**API 版本化**
- `services/shared/api_versioning.py` - 版本化框架
  - `APIVersion` 版本数据类
  - `VersionStatus` 状态枚举（CURRENT/BETA/DEPRECATED/SUNSET/RETIRED）
  - `@api_version` 装饰器
  - `version_router` 路由中间件
  - 弃用警告响应头
  - Sunset 日期支持

**动态 RBAC**
- `services/shared/auth/permissions.py` - 动态权限管理
  - `DynamicRBACManager` 动态角色管理器
  - 角色 CRUD 操作
  - 权限继承支持
  - 数据库持久化
- `services/shared/models/rbac.py` - RBAC ORM 模型
  - `Role` 角色模型（支持继承）
  - `Permission` 权限模型
  - `RolePermission` 关联模型
  - `UserRole` 用户角色关联
- `web/src/pages/admin/RolesPage.tsx` - 角色管理页面
  - 角色列表
  - 角色创建/编辑对话框
  - 权限分配

---

#### Sprint 29: 企业安全强化

**数据加密**
- `services/shared/security/encryption.py` - AES-256-GCM 加密服务
  - `EncryptionService` 加密服务类
  - PBKDF2 密钥派生
  - 密钥版本管理
  - 密钥轮换支持
  - `EncryptedField` SQLAlchemy 描述符
- `scripts/rotate-encryption-keys.sh` - 密钥轮换脚本

**审计日志持久化**
- `services/shared/models/audit.py` - 审计日志 ORM 模型
  - `AuditLog` 模型
  - 复合索引优化查询
- `services/shared/audit.py` - 审计日志服务增强
  - `_persist_to_database()` 异步批量写入
  - `query()` 日志查询方法
  - `get_statistics()` 统计汇总
- `k8s/jobs/audit-cleanup-cronjob.yaml` - 审计日志清理任务

**租户配额强制**
- `services/shared/multitenancy.py` - 配额检查增强
  - `@check_quota()` 装饰器
  - 配额使用量追踪
  - 配额预警通知

---

## [1.0.0-rc] - 2025-01-24

### Added

#### Sprint 23: 生产就绪

**GitOps 部署 (ArgoCD)**
- `argocd/projects/one-data-studio.yaml` - ArgoCD 项目配置
  - 源仓库白名单
  - 目标集群和命名空间限制
  - RBAC 角色定义
- `argocd/applications/agent-api.yaml` - Agent API 应用
- `argocd/applications/web-frontend.yaml` - Web 前端应用
- 自动同步、自愈、清理策略配置

**TLS 证书自动化 (cert-manager)**
- `k8s/infrastructure/cert-manager/issuer.yaml` - 证书签发者
  - Let's Encrypt 生产/测试环境
  - 自签名证书
  - 内部 CA
- `k8s/infrastructure/cert-manager/certificates.yaml` - TLS 证书
  - 应用域名证书
  - API 域名证书
  - 内部服务证书

**备份与灾难恢复**
- `k8s/jobs/mysql-backup-cronjob.yaml` - MySQL 每日备份
  - 每天 2:00 AM 执行
  - 30 天保留策略
  - 上传至 MinIO
- `scripts/disaster-recovery.sh` - 灾难恢复脚本
  - 备份列表查询
  - MySQL 恢复
  - 备份验证
  - 全量恢复

**用户与运维文档**
- `docs/SECURITY.md` - 安全最佳实践
  - Token 安全
  - RBAC 角色
  - 网络安全
  - 密钥管理
  - 审计日志
  - 事件响应
- `docs/06-operations/disaster-recovery.md` - 灾难恢复指南
  - RTO/RPO 目标
  - 备份策略
  - 恢复流程
  - 验证清单
- `docs/07-user-guide/getting-started.md` - 快速入门
  - 部署方式
  - 首次访问
  - 核心功能示例
- `docs/07-user-guide/workflow-guide.md` - 工作流使用指南
  - 节点类型说明
  - 创建步骤
  - 高级功能
  - 最佳实践

---

## [0.9.2] - 2025-01-24

### Added

#### Sprint 22: 质量保证

**测试覆盖率强制**
- `pytest.ini` - 80% 覆盖率阈值
  - pytest-cov 集成
  - HTML/XML 报告生成
  - 覆盖率失败阈值
- `.github/workflows/ci.yml` - CI 流水线
  - 后端测试（Python 3.11）
  - 前端测试（Node.js 20）
  - Docker 构建验证
  - 覆盖率报告上传

**安全扫描集成**
- `.github/workflows/security.yml` - 安全扫描工作流
  - Bandit Python SAST
  - npm audit 依赖扫描
  - Trivy 容器扫描
  - Gitleaks 密钥扫描
  - Checkov IaC 扫描
  - SARIF 格式上传
- `.github/dependabot.yml` - 依赖自动更新
  - pip 每周更新
  - npm 每周更新
  - Docker 每周更新
  - GitHub Actions 每周更新

**新增测试**
- `tests/unit/test_csrf.py` - CSRF 保护测试
- `tests/unit/test_cors.py` - CORS 配置测试
- `tests/unit/test_security_headers.py` - 安全头测试
- `tests/unit/test_rate_limit_fixed.py` - 限流修复测试
- `tests/unit/test_cache_impl.py` - 缓存实现测试
- `tests/integration/test_auth_flow.py` - 认证流程集成测试

---

## [0.9.1] - 2025-01-24

### Added

#### Sprint 21: 安全加固

**安全模块** - `services/shared/security/`
- `csrf.py` - CSRF 保护
  - Double Submit Cookie 模式
  - Token 生成与验证
  - Flask 装饰器
- `cors.py` - CORS 配置
  - 来源白名单
  - 生产环境限制
  - 凭据处理
- `headers.py` - 安全响应头
  - HSTS (1年有效期)
  - Content-Security-Policy
  - X-Frame-Options: DENY
  - X-Content-Type-Options: nosniff
  - X-XSS-Protection
  - Referrer-Policy
- `tls.py` - TLS 配置
  - HTTPS 强制中间件
  - Nginx TLS 配置生成

**认证安全增强**
- `services/shared/auth/token_refresh.py` - Token 刷新中间件
  - 自动刷新即将过期的 Token
  - HttpOnly Cookie 设置
  - SameSite=Lax 属性
- `services/shared/auth/permissions.py` - 权限检查增强
  - `owner_or_admin` 装饰器重构
  - `create_owner_checker` 工厂函数
  - 资源所有者回调支持
- `web/src/services/auth.ts` - 前端认证重构
  - 从 localStorage 迁移到 HttpOnly Cookie
  - 非敏感数据使用 sessionStorage
  - CSRF Token 获取函数

**密钥管理**
- `k8s/infrastructure/secrets/` - K8s External Secrets
  - Secret Store 配置
  - External Secret 定义（MySQL、Redis、MinIO、JWT、OpenAI、Keycloak）
- `deploy/nginx/nginx.conf` - HTTPS 配置
  - HTTP→HTTPS 重定向
  - TLS 1.2+ 现代加密套件
  - 安全响应头
- `.env.example` - 环境变量模板
- `scripts/rotate-secrets.sh` - 密钥轮换脚本
  - JWT 密钥轮换
  - 数据库密码轮换
  - Redis 密码轮换
  - MinIO 密钥轮换
  - --dry-run 模式

### Fixed

#### Bug 修复
- `services/shared/rate_limit.py:103` - 修复 `_limimiter` 拼写错误为 `_limiter`
- `services/shared/rate_limit.py:108` - 修复重复条件逻辑 `not config.redis.enabled and not config.redis.enabled`
- `services/shared/cache.py` - 实现 CacheBackend 接口
  - 移除 NotImplementedError
  - 添加 MemoryCache 类（带 TTL 支持）
  - 自动清理过期缓存

---

## [0.4.0] - 2025-01-24

### Added

#### Sprint 8: 前端性能优化
- **React Query 缓存策略** - `web/src/services/queryClient.ts`
  - 分层缓存策略（REALTIME、SHORT、MEDIUM、LONG、STATIC）
  - 智能失效映射（Mutation 自动失效相关查询）
  - 后台刷新和离线优先支持
  - 扩展 QueryKeys 覆盖所有 API

- **Vite 构建优化** - `web/vite.config.ts`
  - 智能分包策略（antd-icons 独立分离）
  - Tree-shaking 优化配置
  - 资源内联阈值和压缩配置
  - 目标升级到 ES2020

- **Zustand Store 选择器** - `web/src/store/createSelectors.ts`
  - 自动生成类型安全选择器
  - 浅比较选择器避免不必要渲染
  - 记忆化选择器工具
  - 批量更新辅助函数

#### Sprint 9: 安全加固
- **JWT 密钥轮换** - `services/shared/config.py`
  - JWTConfig 类支持多密钥管理
  - 平滑轮换机制（过渡期内旧密钥仍有效）
  - 自动生成密钥 ID
  - 验证时尝试所有有效密钥

- **输入验证集成**
  - Data API 数据集创建接口添加验证装饰器
  - Agent API 聊天、工作流、Text2SQL 接口添加验证
  - SQL 注入检测装饰器

- **E2E 测试扩展** - `tests/e2e/`
  - `test_workflow_e2e.py` - 工作流 CRUD、执行、调度测试
  - `test_agent_e2e.py` - Agent 模板、工具、RAG 场景测试

#### Sprint 10: 监控与部署
- **深度健康检查**
  - Data API: 数据库、MinIO、Redis 连通性检查
  - Agent API: 数据库、Redis、Milvus、上游服务检查
  - 返回延迟指标和资源统计

- **日志聚合配置** - `deploy/monitoring/`
  - `promtail-k8s-config.yaml` - Kubernetes 原生日志采集
  - Pod 自动发现和标签匹配
  - 多种日志格式解析（JSON、Python、Nginx）
  - 健康检查和 metrics 日志过滤

- **部署自动化** - `deploy/scripts/deploy-all.sh`
  - 一键部署脚本支持 local/k8s/kind 环境
  - 依赖服务健康等待
  - 分阶段部署（基础设施 -> 应用 -> 监控）
  - 部署验证和状态报告

- **运维手册** - `docs/06-operations/operations-guide.md`
  - 日常运维操作指南
  - 备份恢复流程
  - 故障排查步骤
  - 扩缩容配置

- **性能测试脚本** - `tests/performance/`
  - `api-load.js` - k6 API 负载测试（100+ 并发用户）
  - `vector-search.js` - 向量检索性能测试
  - 自动生成 HTML 报告

### Changed

#### 文档更新
- `docs/02-integration/api-reference.md` - 添加健康检查接口文档
- Sprint 8-10 标记为已完成

### Performance Targets

| 指标 | 目标 | 状态 |
|------|------|------|
| API P95 响应时间 | < 500ms | ✅ 可测试 |
| 向量检索延迟 | < 100ms | ✅ 可测试 |
| 首页加载时间 | < 2s | ✅ 优化完成 |
| Bundle 大小 | < 500KB (gzip) | ✅ 分包优化 |

---

## [0.3.0] - 2025-01-24

### Added

#### 共享模块 (Sprint 6)
- **配置管理** - `services/shared/config.py`
  - 统一配置接口，支持环境变量和配置文件
  - DatabaseConfig, MinIOConfig, MilvusConfig, OpenAIConfig, KeycloakConfig
  - 生产环境配置验证
- **错误处理** - `services/shared/error_handler.py`
  - 统一错误响应格式
  - ErrorCode 常量定义
  - APIError 基类和子类 (ValidationError, NotFoundError, UnauthorizedError, etc.)
  - Flask 错误处理器注册器
  - 错误捕获装饰器

#### 测试框架 (Sprint 6)
- **Python 测试**
  - `pytest.ini` - Pytest 配置文件
  - `tests/conftest.py` - 共享 fixtures
  - 支持 --runslow, --with-db, --with-milvus, --with-minio 选项
- **前端测试**
  - `web/vitest.config.ts` - Vitest 配置文件
  - `web/src/test/setup.ts` - 测试设置
  - `web/src/test/utils.test.ts` - 示例测试
  - 更新 `web/package.json` 添加测试脚本

#### 文档 (Sprint 7)
- **Demo 指南** - `docs/05-development/demo-guide.md`
  - 准备阶段检查清单
  - 核心场景演示步骤（数据治理、RAG、Text2SQL、工作流、Agent）
  - 三大集成验证方法
  - 故障排查指南
  - FAQ 和演示检查清单

#### 增强的测试脚本 (Sprint 7)
- **E2E 测试** - `scripts/test-e2e.sh`
  - 三大集成点验证
  - 文档上传和向量检索测试
  - 会话管理测试
  - 工作流执行测试
  - 自动清理测试数据

### Changed

#### Sprint 状态更新
- Sprint 5-7 标记为已完成
- 更新 `docs/05-development/sprint-plan.md`

### Fixed

#### 已解决的技术债
- 配置管理统一化（不再依赖硬编码）
- 错误处理标准化
- 测试框架就绪

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
- **Data API** (Flask)
  - 数据集注册、查询、更新、删除接口
  - 元数据查询接口
  - MinIO 数据源集成
  - 数据库模型和迁移

- **OpenAI Proxy** (FastAPI)
  - OpenAI 兼容 API (`/v1/chat/completions`)
  - 模型列表接口 (`/v1/models`)
  - 流式响应支持 (SSE)

- **Agent API** (Flask)
  - 工作流 CRUD 接口
  - 工作流执行接口
  - Prompt 模板管理
  - 知识库文档管理
  - 向量集合列表
  - 引擎节点系统（RAG、LLM 节点）

#### 部署
- **Docker Compose** 完整服务编排
  - Web 前端
  - Data API
  - OpenAI Proxy
  - Agent API
  - MySQL、Redis、MinIO、Keycloak
- **Kubernetes** 部署配置
  - 基础设施服务 (MySQL, Redis, MinIO, Milvus, Keycloak)
  - 应用服务 (Data API, Agent API, OpenAI Proxy, Web Frontend, vLLM Serving)
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

无已知严重问题

---

## Version History

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.3.2 | 2026-01-29 | 新增项目依赖全面评估报告 |
| 1.3.1 | 2026-01-29 | 文档整理：归档过时测试文档，创建技术债务清单 |
| 1.3.0 | 2026-01-28 | 文档整理：目录编号修复、散落文档归类、代码统计更新、代码审计报告 |
| 1.2.0 | 2025-01-24 | Sprint 32 完成：工作流版本控制、Token 成本追踪 |
| 1.0.0-rc | 2025-01-24 | Sprint 23 完成：GitOps、TLS 自动化、备份恢复、用户文档 |
| 0.9.2 | 2025-01-24 | Sprint 22 完成：80% 测试覆盖率、CI/CD 安全扫描、Dependabot |
| 0.9.1 | 2025-01-24 | Sprint 21 完成：CSRF/CORS/Headers、HttpOnly Cookie、密钥管理 |
| 0.4.0 | 2025-01-24 | Sprint 8-10 完成：性能优化、安全加固、监控运维、E2E 测试 |
| 0.3.0 | 2025-01-24 | Sprint 5-7 完成：测试框架、Demo 指南、E2E 测试 |
| 0.2.0 | 2025-01-24 | 新增 10+ 页面，Agent 系统，调度系统 |
| 0.1.0 | 2025-01-23 | 开发中版本，PoC 阶段 |

---

## 贡献指南

欢迎贡献！请查看：
- 架构设计：`docs/01-architecture/`
- API 规范：`docs/02-integration/api-specifications.md`
- 开发指南：`docs/05-development/`
