# 技术选型优化评估与开发规划

> **项目**: ONE-DATA-STUDIO
> **日期**: 2026-01-30
> **版本**: v1.0
> **状态**: 评审中

---

## 一、背景与目标

### 1.1 项目当前状态

ONE-DATA-STUDIO 当前版本 v1.3.2，项目规模：

| 维度 | 数据 |
|------|------|
| 总代码量 | 295,000+ 行 |
| Python 后端 | 274 文件，142,887 行 |
| TypeScript 前端 | 216 文件（130+ 页面），120,334 行 |
| 后端服务 | 7 个微服务，460+ API 端点，60+ 数据库模型 |
| 前端模块 | 10+ 服务模块，200+ API 函数 |
| 测试代码 | 143+ 文件，32,500+ 行 |
| 集成技术 | 20+ 第三方技术组件 |
| 部署方式 | Docker Compose（开发）+ Kubernetes（生产） |

### 1.2 LITE 方案概述

LITE 方案是一种**基座平台 + 组件集成 + 薄二开层**的架构思路，以腾讯音乐开源的 **Cube-Studio** 作为基座平台，复用其 Pipeline 编排、模型管理、在线 IDE、数据标注等能力，大幅减少自研代码量。其核心技术选型包括：

| 层次 | LITE 方案技术选型 |
|------|------------------|
| 基座平台 | Cube-Studio（Pipeline 编排、模型管理、在线 IDE、数据标注） |
| 元数据管理 | DataHub |
| 数据同步 | Apache SeaTunnel + DolphinScheduler |
| ETL 引擎 | Apache Hop（Kettle 开源替代） |
| AI 引擎 | Cube-Studio 集成 vLLM/Ollama |
| 数据质量 | Great Expectations |
| BI 分析 | Apache Superset |
| 数据安全 | Apache ShardingSphere（透明脱敏） |
| 数据标注 | Label Studio |
| 前端 | 统一门户聚合 Cube-Studio/Superset/DataHub 前端 UI |
| 部署 | k3s 轻量 Kubernetes |

### 1.3 本文档目标

1. 对当前技术栈与 LITE 方案进行逐层对比分析
2. 基于对比结果给出组件级优化建议（保留 / 迁移 / 新增 / 不采纳）
3. 制定分阶段实施路线图，衔接现有 `roadmap.md` 的 v1.5 / v2.0 版本规划

### 1.4 相关文档

| 文档 | 路径 | 关系 |
|------|------|------|
| 技术栈清单 | `docs/01-architecture/tech-stack.md` | 架构设计阶段的技术选型参考 |
| 路线图 | `docs/05-planning/roadmap.md` | 版本规划（v1.5 / v2.0 衔接） |
| 功能增强实施计划 | `docs/05-planning/implementation-plan.md` | 功能层面的增强计划（26 天） |

---

## 二、技术选型逐层对比

### 2.1 基座平台

| 能力域 | 当前项目 | LITE 方案 | 差异分析 |
|--------|---------|-----------|---------|
| 基座平台 | **自研** (Flask/FastAPI 微服务) | **Cube-Studio** (腾讯音乐开源) | **根本性差异**。当前是 7 个自研微服务（~460 API），LITE 方案以 Cube-Studio 为基座复用其 Pipeline 编排、模型管理、在线 IDE、数据标注等能力，大幅减少自研代码量 |
| 在线 IDE | 未实现（Model-API 有 IDE 接口定义但无实际集成） | Cube-Studio 内置 Jupyter/VSCode/RStudio | 当前缺失，LITE 方案开箱即用 |
| Pipeline 编排 | 自研 Workflow 引擎（ReactFlow 可视化 + 15+ 节点类型） | Cube-Studio 拖拽式 Pipeline | 当前已有完整自研实现，迁移需评估自定义节点的兼容性 |
| 数据标注 | 未实现 | Cube-Studio 集成 **Label Studio** | 当前缺失 |
| 多集群调度 | Kubernetes client 库集成，Helm charts | Cube-Studio K8s 多集群 + **k3s** | 当前用标准 K8s，LITE 方案建议轻量化 k3s |

### 2.2 元数据与数据资产

| 能力域 | 当前项目 | LITE 方案 | 差异分析 |
|--------|---------|-----------|---------|
| 元数据管理 | **OpenMetadata 1.3.1** + Elasticsearch 8.10.2 | **DataHub** | **核心差异**。两者都是企业级元数据平台，但技术栈不同：OpenMetadata 用 MySQL+ES，DataHub 用 MySQL+ES+Kafka+GMS。当前已有 OpenMetadata 同步服务的实际代码集成 |
| 数据血缘 | 自研 LineageNode/LineageEdge 模型 + OpenLineage 事件服务 | DataHub Ingestion 自动采集 | 当前混合模式（自研+OpenLineage），LITE 方案依赖 DataHub 原生血缘 |
| 资产目录 | 自研 DataAsset 模型 + AI 价值评估 | DataHub 复用 | 当前自研资产目录含 AI 搜索和价值评估能力，这些在 DataHub 中需二开 |

### 2.3 数据同步与 ETL

| 能力域 | 当前项目 | LITE 方案 | 差异分析 |
|--------|---------|-----------|---------|
| 数据同步/CDC | **Apache SeaTunnel 2.3.3** | **Apache SeaTunnel** | **一致** |
| 任务调度 | **Apache DolphinScheduler 3.2.0** + Celery 5.3.4 + APScheduler | **DolphinScheduler** | **基本一致**，当前额外使用 Celery 做异步任务、APScheduler 做轻量定时任务 |
| ETL 引擎 | **Pentaho Kettle (Webspoon 0.9.0.27)** + Carte 远程执行 | **Apache Hop** (Kettle 开源替代) | **关键差异**。Hop 是 Kettle 原作者的重构版本，API 兼容但架构更现代。当前已有 Webspoon Web 端集成和 Carte API 调用代码，迁移到 Hop 需改造集成层 |
| 消息队列 | **Kafka** (confluent-kafka + kafka-python) | 未明确（SeaTunnel 内置） | 当前已有 Kafka 流处理服务（KafkaStreamService），LITE 方案未单独列出 |

### 2.4 AI 引擎

| 能力域 | 当前项目 | LITE 方案 | 差异分析 |
|--------|---------|-----------|---------|
| LLM 推理 | **vLLM** (两实例：chat + embed) | **Cube-Studio 集成 vLLM/Ollama** | 模型引擎一致（vLLM），但 LITE 方案额外支持 **Ollama** 作为轻量替代。当前未集成 Ollama |
| 默认模型 | Chat: Qwen2.5-1.5B-Instruct; Embed: bge-base-zh-v1.5 | 未指定 | 当前已有明确的模型配置 |
| OCR | **PaddleOCR 2.7.0.3** + Tesseract + EasyOCR（多引擎） | **PaddleOCR** | **基本一致**，当前实现更丰富（多引擎 fallback） |
| 数据质量 | 自研 QualityRule/QualityTask 模型 + AI 清洗规则推荐 | **Great Expectations** | **差异**。当前是自研质量检测，LITE 方案用 Great Expectations（业界标准），功能更丰富但需集成 |
| RAG/知识库 | **LangChain 0.1.14** + **Milvus v2.3.0** + 自研混合检索 | Cube-Studio 内置 RAG | 当前已有完整 RAG 实现（混合检索+重排序），LITE 方案依赖 Cube-Studio 的 RAG 能力 |
| NL2SQL | 自研 Text2SQL 模块（vLLM + 元数据注入） | 二开 NL2SQL 服务 | **一致**，均为二开实现 |
| 向量数据库 | **Milvus v2.3.0** (含 etcd + MinIO) | 未明确 | LITE 方案未提及向量数据库选型，当前 Milvus 是 RAG 核心依赖 |

### 2.5 BI 分析

| 能力域 | 当前项目 | LITE 方案 | 差异分析 |
|--------|---------|-----------|---------|
| BI 平台 | **Apache Superset 3.1.0** | **Apache Superset** | **一致** |
| BI 集成方式 | 独立部署 + iframe/API 集成 | 统一门户嵌入 | 集成方式类似 |

### 2.6 数据安全

| 能力域 | 当前项目 | LITE 方案 | 差异分析 |
|--------|---------|-----------|---------|
| 数据脱敏 | 自研 MaskingRule 模型 + 自研敏感数据扫描（正则+LLM） | **Apache ShardingSphere** 透明脱敏 | **核心差异**。ShardingSphere 在 SQL 代理层拦截实现透明脱敏，对应用无侵入；当前自研方案在应用层实现，灵活但覆盖面有限 |
| 敏感数据识别 | 自研 SensitivityPattern + LLM 辅助识别 | 正则 + LLM | **基本一致** |
| 权限管控 | 自研 RBAC + Keycloak | 未明确 | 当前更完善 |

### 2.7 认证与安全

| 能力域 | 当前项目 | LITE 方案 | 差异分析 |
|--------|---------|-----------|---------|
| 身份认证 | **Keycloak 23.0** (OAuth2/OIDC) + 自研 JWT | 未明确（Cube-Studio 自带认证） | LITE 方案未单独规划认证组件，可能依赖 Cube-Studio 内置能力 |
| SSO 支持 | OIDC/SAML/CAS/OAuth2/微信/钉钉 | 未明确 | 当前更全面 |

### 2.8 监控与可观测性

| 能力域 | 当前项目 | LITE 方案 | 差异分析 |
|--------|---------|-----------|---------|
| 指标监控 | **Prometheus v2.47.0** | **Prometheus** | **一致** |
| 可视化 | **Grafana 10.1.0** | **Grafana** | **一致** |
| 分布式追踪 | **Jaeger 1.50** + OpenTelemetry | 未提及 | 当前更完善，LITE 方案未规划追踪 |
| 日志聚合 | **Loki 2.9.0** | 未提及 | 当前已有，LITE 方案未规划 |

### 2.9 前端与门户

| 能力域 | 当前项目 | LITE 方案 | 差异分析 |
|--------|---------|-----------|---------|
| 前端框架 | **自研** React 18 + TypeScript + Ant Design（216 TSX 文件，120K+ 行） | **统一门户**嵌入 Cube-Studio/Superset/DataHub 前端 | **根本性差异**。当前完全自研前端，LITE 方案通过门户聚合三个现成前端 UI，自研部分大幅减少 |
| 工作流编辑器 | ReactFlow 自研（15+ 节点类型） | Cube-Studio Pipeline 编辑器 | 当前自研更灵活，但维护成本高 |

### 2.10 存储层

| 能力域 | 当前项目 | LITE 方案 | 差异分析 |
|--------|---------|-----------|---------|
| 关系数据库 | **MySQL 8.0**（主库）+ **PostgreSQL 15.4**（仅 DolphinScheduler） | MySQL/PostgreSQL | **基本一致** |
| 对象存储 | **MinIO** | **MinIO** | **一致** |
| 缓存 | **Redis 7** | **Redis** | **一致** |

### 2.11 汇总对比矩阵

| 对比维度 | 相同 | 当前项目有 / LITE 无 | LITE 有 / 当前项目无 |
|---------|------|---------------------|---------------------|
| **基座** | — | 自研微服务架构 | Cube-Studio |
| **同步/调度** | SeaTunnel, DolphinScheduler | Celery, APScheduler, Kafka | — |
| **ETL** | — | Kettle/Webspoon | Apache Hop |
| **元数据** | — | OpenMetadata | DataHub |
| **BI** | Superset | — | — |
| **AI/LLM** | vLLM, PaddleOCR | Milvus, LangChain, 多引擎 OCR | Ollama, Great Expectations |
| **安全** | — | Keycloak, 自研脱敏 | ShardingSphere |
| **监控** | Prometheus, Grafana | Jaeger, Loki, OpenTelemetry | — |
| **标注** | — | — | Label Studio |
| **前端** | — | 自研 React 全栈 (120K+ 行) | 门户聚合模式 |
| **存储** | MySQL, MinIO, Redis | PostgreSQL, Milvus, ES, etcd | — |

---

## 三、优化建议

### 核心判断：不建议整体迁移到 LITE 方案

| 维度 | 分析 |
|------|------|
| 沉没成本 | 当前项目已投入大量开发资源，前后端代码成熟度较高 |
| 迁移风险 | 以 Cube-Studio 为基座意味着重写大部分业务逻辑，风险不可控 |
| 功能差异 | 当前项目在 RAG、认证、可观测性等方面比 LITE 方案更完善 |
| 定制灵活性 | 自研架构对业务定制更灵活，Cube-Studio 有其固有约束 |

**建议策略：渐进式优化，取长补短。**

### 3.1 建议保留的现有组件（8 项）

| 序号 | 组件 | 理由 |
|------|------|------|
| 1 | **自研微服务架构** (Flask/FastAPI) | 已成熟，业务契合度高，继续演进 |
| 2 | **OpenMetadata** | 已有集成代码，切换到 DataHub 收益不明显 |
| 3 | **Milvus + LangChain** | RAG 能力是核心竞争力，LITE 方案未覆盖 |
| 4 | **Keycloak** | 企业级认证，多协议 SSO，比 Cube-Studio 内置认证更强 |
| 5 | **监控四件套** (Prometheus + Grafana + Jaeger + Loki) | 可观测性体系完整，LITE 方案缺少追踪和日志聚合 |
| 6 | **SeaTunnel + DolphinScheduler** | 与 LITE 方案一致，无需变动 |
| 7 | **Apache Superset** | 与 LITE 方案一致，无需变动 |
| 8 | **自研前端** (React + TypeScript + Ant Design) | 120K+ 行成熟代码，定制灵活，已有 130+ 页面 |

### 3.2 建议渐进式迁移/增强（3 项）

#### 3.2.1 Kettle → Apache Hop（中优先级）

| 维度 | 说明 |
|------|------|
| 当前状态 | Pentaho Kettle (Webspoon 0.9.0.27) + Carte 远程执行 |
| 迁移理由 | Hop 是 Kettle 原作者重构版本，社区更活跃，云原生支持更好，Kettle 已进入维护模式 |
| 兼容性 | Hop 可导入 Kettle 转换/作业文件，迁移成本可控 |
| 实施建议 | (1) 新 ETL 任务用 Hop 开发；(2) 存量任务逐步迁移；(3) 保留 Kettle 兼容层过渡期 |
| 风险点 | Webspoon 集成代码需改造为 Hop Server API |
| 代码影响 | 新增 `services/data-api/integrations/hop/` 集成模块 |

#### 3.2.2 自研数据质量 → Great Expectations 补充（中优先级）

| 维度 | 说明 |
|------|------|
| 当前状态 | 自研 QualityRule/QualityTask + AI 规则推荐 |
| 引入理由 | GE 是业界标准，内置 300+ 期望（Expectation），覆盖面远超自研 |
| 集成方式 | GE 作为底层引擎，自研 AI 规则推荐调用 GE API 生成 Expectation Suite |
| 实施建议 | (1) 先在数据同步任务后集成 GE 校验；(2) 自研 UI 对接 GE 的 Data Docs |
| 代码影响 | 新增 `services/data-api/integrations/great_expectations/` |

#### 3.2.3 自研脱敏 → ShardingSphere 增强（低优先级）

| 维度 | 说明 |
|------|------|
| 当前状态 | 应用层自研 MaskingRule + 敏感扫描 |
| 引入理由 | SQL 层脱敏对应用无侵入，覆盖面更广（包括 BI、直连查询） |
| 适用场景 | 读库脱敏、报表脱敏、第三方系统查询 |
| 保留自研 | 应用层脱敏仍用于 API 返回值精细控制 |
| 实施建议 | (1) 先在只读副本前部署 ShardingSphere Proxy；(2) 与自研敏感扫描联动，自动生成脱敏规则 |
| 风险点 | 引入新的数据库代理层，需评估性能影响 |

### 3.3 建议新增组件（3 项）

#### 3.3.1 Label Studio（高优先级）

| 维度 | 说明 |
|------|------|
| 当前状态 | 无数据标注能力 |
| 需求场景 | SFT 微调数据准备、OCR 结果校验、NER 标注 |
| 集成方式 | 独立部署 Label Studio OSS + iframe 嵌入或 API 对接 |
| 实施建议 | (1) 部署 Label Studio OSS；(2) 在 Model-API 增加 `/api/v1/labeling/` 代理层；(3) 前端新增 `LabelingPage` 嵌入 |

#### 3.3.2 Ollama（低优先级）

| 维度 | 说明 |
|------|------|
| 当前状态 | 仅 vLLM（生产级，但资源要求高） |
| 适用场景 | 开发测试环境、小模型推理、资源受限场景 |
| 集成方式 | OpenAI-Proxy 增加 Ollama 后端（与 vLLM 并列） |
| 实施建议 | 配置开关：`LLM_BACKEND=vllm|ollama`，API 兼容无需改上层 |

#### 3.3.3 JupyterHub - 在线 IDE（低优先级）

| 维度 | 说明 |
|------|------|
| 当前状态 | Model-API 有 IDE 接口定义但无实际服务 |
| 适用场景 | 数据探索、模型调试、特征工程 |
| 推荐方案 | JupyterHub（与 Cube-Studio 方案一致，生态成熟） |
| 实施建议 | (1) K8s 部署 JupyterHub；(2) 对接 Keycloak 认证；(3) 挂载 MinIO 数据卷 |

### 3.4 不建议采纳（3 项）

| 序号 | 组件 | 不采纳理由 |
|------|------|-----------|
| 1 | **Cube-Studio 作为基座** | 需重写大部分业务代码（460+ API），ROI 不合理；当前自研架构业务契合度高且定制灵活 |
| 2 | **DataHub 替代 OpenMetadata** | 功能相近，当前已有 OpenMetadata 集成代码，切换无明显收益；两者均支持 MySQL+ES，迁移成本与技术债务不成比例 |
| 3 | **k3s 替代标准 K8s** | k3s 适合边缘/轻量场景，当前标准 K8s + Helm 更适合企业级生产环境，且已有成熟的部署脚本和 Helm Charts |

---

## 四、开发规划

### Phase 1：补齐短板

**目标**：引入 LITE 方案中当前项目缺失的关键能力

| 序号 | 任务 | 优先级 | 主要工作 |
|------|------|--------|---------|
| 1 | 部署 Label Studio | 高 | Docker Compose 添加 Label Studio 服务；Model-API 新增 `/api/v1/labeling/` 代理层；前端 `LabelingPage` 嵌入 |
| 2 | 引入 Great Expectations | 中 | 新增 `integrations/great_expectations/` 模块；在数据同步任务后集成 GE 校验；UI 对接 GE Data Docs |
| 3 | OpenAI-Proxy 增加 Ollama 后端 | 低 | 新增 Ollama 适配器；`LLM_BACKEND` 配置开关；开发/测试环境验证 |

**与 `implementation-plan.md` 衔接**：Phase 1 的 Label Studio 可与 implementation-plan 中模块三（数据加工融合）的 OCR 结果校验联动；Great Expectations 补充模块四（数据分析挖掘）的质量检测能力。

### Phase 2：渐进迁移

**目标**：对需要迁移的组件启动 POC 验证和增量切换

| 序号 | 任务 | 优先级 | 主要工作 |
|------|------|--------|---------|
| 1 | Apache Hop 新任务试点 | 中 | 部署 Hop Server；新增 `integrations/hop/` 模块；新 ETL 任务用 Hop 开发 |
| 2 | Hop Server 集成层开发 | 中 | 替换 Webspoon/Carte API 调用为 Hop Server API；保留 Kettle 兼容层 |
| 3 | ShardingSphere 透明脱敏 POC | 低 | 只读副本前部署 ShardingSphere Proxy；与自研敏感扫描联动；性能基准测试 |

**与 `implementation-plan.md` 衔接**：Phase 2 的 Hop 迁移衔接 implementation-plan 中模块一（1.3 Kettle 联动增强）和模块二（数据感知汇聚）的 ETL 流程升级。

### Phase 3：存量迁移与深化

**目标**：完成组件迁移的收尾工作，进入生产稳定状态

| 序号 | 任务 | 优先级 | 主要工作 |
|------|------|--------|---------|
| 1 | Kettle 存量任务迁移到 Hop | 中 | 利用 Hop 的 Kettle 导入功能；逐批迁移存量转换/作业；验证与回归测试 |
| 2 | ShardingSphere 生产部署 | 低 | 基于 POC 结果决策；若通过则部署到生产读库前；配置脱敏规则联动 |
| 3 | JupyterHub 在线 IDE 集成 | 低 | K8s 部署 JupyterHub；对接 Keycloak 认证；挂载 MinIO 数据卷 |

---

## 五、里程碑与交付物

### 5.1 各阶段里程碑

| 阶段 | 里程碑 | 交付物 | 验收标准 |
|------|--------|--------|---------|
| **Phase 1** | M1: Label Studio 集成完成 | Label Studio 部署 + API 代理层 + 前端嵌入页 | 可通过前端创建标注项目、提交标注任务、导出标注数据 |
| | M2: Great Expectations 集成完成 | GE 集成模块 + 质量校验流程 + Data Docs 对接 | 数据同步后自动触发 GE 校验，质量报告可在前端查看 |
| | M3: Ollama 后端上线 | OpenAI-Proxy Ollama 适配器 | 配置 `LLM_BACKEND=ollama` 后可正常调用推理 API |
| **Phase 2** | M4: Hop Server 试点上线 | Hop 集成模块 + 新任务试点 | 至少 3 个新 ETL 任务通过 Hop 运行 |
| | M5: ShardingSphere POC 完成 | POC 报告 + 性能基准测试 | 脱敏准确率 100%，性能损耗 < 15% |
| **Phase 3** | M6: Kettle 存量迁移完成 | 所有 ETL 任务迁移到 Hop | 全部存量任务通过 Hop 运行，Kettle 依赖完全移除 |
| | M7: 在线 IDE 上线 | JupyterHub 部署 + 认证对接 | 用户可通过前端跳转到 JupyterHub，SSO 免登录 |

### 5.2 版本规划衔接

本规划与 `roadmap.md` 版本规划的衔接关系：

| 版本 | 计划时间 | roadmap.md 主要特性 | 本规划对应阶段 |
|------|----------|-------------------|--------------|
| **v1.5** | 2025 Q2 | 企业级特性、多租户 | Phase 1（补齐短板：Label Studio、GE、Ollama） |
| **v2.0** | 2026 | AutoML、智能增强 | Phase 2-3（渐进迁移：Hop、ShardingSphere、JupyterHub） |

**具体衔接说明**：

- **v1.5 新增**：在原有多租户、聊天历史、向量检索、工作流编辑器基础上，增加 Label Studio 数据标注、Great Expectations 数据质量引擎、Ollama 轻量推理后端
- **v2.0 新增**：在原有 AutoML、自动特征工程、多模态基础上，增加 Apache Hop ETL 引擎、ShardingSphere 透明脱敏（如 POC 通过）、JupyterHub 在线 IDE

---

## 六、风险评估

| 风险项 | 风险等级 | 影响范围 | 应对措施 |
|--------|---------|---------|---------|
| **Hop 迁移兼容性** | 中 | ETL 全流程 | Hop 支持导入 Kettle 文件，但自定义插件/步骤需逐个验证；保留 Kettle 兼容层作为过渡 |
| **ShardingSphere 性能影响** | 中 | 数据库查询延迟 | 先 POC 基准测试，设定性能损耗阈值（< 15%）；仅部署在只读副本前 |
| **Label Studio 版本兼容** | 低 | 数据标注功能 | 使用 OSS 稳定版本；API 集成而非深度耦合，可独立升级 |
| **Great Expectations 学习曲线** | 低 | 开发效率 | GE 文档完善，Python API 友好；可参考现有自研质量规则逐步对接 |
| **Ollama 模型质量差异** | 低 | 推理结果一致性 | 仅用于开发/测试环境；生产环境保持 vLLM |
| **JupyterHub 安全隔离** | 中 | 多用户环境安全 | 对接 Keycloak 认证；K8s namespace 隔离；限制资源配额 |

---

## 七、决策记录

| 决策编号 | 决策内容 | 理由 | 替代方案 | 决策日期 |
|---------|---------|------|---------|---------|
| D-001 | 不采纳 Cube-Studio 作为基座平台 | 460+ API 重写 ROI 不合理，自研架构定制灵活 | 整体迁移到 Cube-Studio | 2026-01-30 |
| D-002 | 保留 OpenMetadata，不切换 DataHub | 功能相近，已有集成代码，切换无明显收益 | 迁移到 DataHub | 2026-01-30 |
| D-003 | 保留标准 K8s，不切换 k3s | 标准 K8s 更适合企业级生产环境 | 切换到 k3s | 2026-01-30 |
| D-004 | 渐进式迁移 Kettle → Apache Hop | Kettle 进入维护模式，Hop 社区更活跃，支持导入迁移 | 继续使用 Kettle | 2026-01-30 |
| D-005 | 引入 Great Expectations 作为数据质量引擎 | 业界标准，300+ 内置 Expectation，保留自研 AI 规则作为上层 | 继续纯自研数据质量 | 2026-01-30 |
| D-006 | 评估引入 ShardingSphere 透明脱敏 | SQL 层脱敏覆盖面广（含 BI/直连），先 POC 再决策 | 继续纯应用层脱敏 | 2026-01-30 |
| D-007 | 新增 Label Studio 数据标注 | 当前完全缺失数据标注能力，SFT/NER 等场景需要 | Cube-Studio 内置标注（已排除） | 2026-01-30 |
| D-008 | 新增 Ollama 轻量推理后端 | 降低开发/测试环境资源门槛，API 兼容无需改上层 | 仅使用 vLLM | 2026-01-30 |
| D-009 | 规划 JupyterHub 在线 IDE | 填补在线开发环境缺口，与 Keycloak 认证联动 | code-server (VS Code in browser) | 2026-01-30 |

---

## 附录：目标功能覆盖度现状

基于 35 项目标功能的逐项对比：

| 状态 | 数量 | 占比 | 说明 |
|------|------|------|------|
| 已实现 | 27 | 77% | 工作台、数据规划、数据汇聚、数据开发（主体）、数据分析（主体）、数据资产、安全权限（主体）、统一支撑（主体）、系统运维（主体） |
| 部分实现 | 7 | 20% | 数据标签管理、数据融合配置、缺失值填充、ETL 数据联动、个人中心（登录记录/开票）、统一身份认证（飞书）、租户管理 |
| 未实现 | 1 | 3% | 财务开票信息管理 |

此外，当前项目包含大量**目标清单未列出**的功能（MLOps + LLMOps 领域）：

| 功能域 | 具体功能 |
|--------|---------|
| 模型开发 (MLOps) | 实验管理、训练任务、模型注册中心、AI Hub、ML Pipeline、LLM 微调、数据标注 |
| 模型服务 | 在线推理服务、资源池管理（GPU/CPU）、模型监控、HuggingFace 集成、K8s 训练 |
| AI 应用 (LLMOps) | AI Chat、Prompt 管理、知识库（RAG）、Workflow 可视化编排（15+ 节点类型）、Agent 管理、Text2SQL、模型评估、SFT 微调、应用发布 |
| 数据开发扩展 | 特征存储、数据血缘可视化、实时流处理（Kafka）、离线开发、Notebook、SQL Lab |
| 运营分析 | 用户行为分析（热力图/漏斗/留存）、用户画像与分群、成本分析报表 |
| 基础设施 | OpenAI 兼容代理网关（vLLM/OpenAI 双后端）、分布式追踪、熔断器模式 |

---

## 更新记录

| 日期 | 版本 | 更新内容 | 更新人 |
|------|------|----------|--------|
| 2026-01-30 | v1.0 | 初始版本：技术选型对比、优化建议、开发规划 | Claude |
