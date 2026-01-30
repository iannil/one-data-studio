# ONE-DATA-STUDIO

<div align="center">

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18.3-blue.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.4-blue.svg)](https://www.typescriptlang.org/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.27%2B-326ce5.svg)](https://kubernetes.io/)
[![Docker](https://img.shields.io/badge/Docker-20.10%2B-2496ED.svg)](https://www.docker.com/)

企业级 DataOps + MLOps + LLMOps 融合平台

*从原始数据到智能应用 —— 一站式解决方案*

[功能特性](#-功能特性) | [快速开始](#-快速开始) | [架构设计](#-架构设计) | [应用场景](#-应用场景) | [竞品对比](#-竞品对比) | [文档](#-文档) | [English](README.md)

</div>

---

## 什么是 ONE-DATA-STUDIO？

ONE-DATA-STUDIO 是一个开源的企业级平台，将三个关键的 AI 基础设施层融合为一个统一系统：

| 层级 | 名称 | 描述 |
| ------ | ------ | ------ |
| Data | 数据运营平台 | 数据集成、ETL、治理、特征存储、向量存储 |
| Model | 机器学习平台 | Jupyter Notebook、分布式训练、模型注册、模型服务 |
| Agent | 大模型应用平台 | RAG 流水线、Agent 编排、工作流构建、Prompt 管理 |

与将这三层作为独立系统的传统平台不同，ONE-DATA-STUDIO 在各层之间创建了无缝的集成点，使企业能够从原始数据构建端到端的 AI 解决方案直至生产应用。

### 核心价值

1. 完整价值链：原始数据 → 治理后的数据集 → 训练好的模型 → 部署的应用
2. 统一治理：数据血缘、模型血缘、应用日志的统一视图
3. 私有安全：完全本地化部署，数据、算力、模型全在企业内部
4. 生产就绪：企业级安全、监控、可扩展性经过实战验证

---

## 功能特性

### Data 层（数据运营）

| 功能 | 描述 | 实现方式 |
| ------ | ------ | ---------- |
| 数据集成 | 连接 50+ 种数据源（数据库、API、文件） | Flask 连接器 + 异步 I/O |
| ETL 流水线 | 可视化流水线构建器，支持 Flink/Spark 执行 | 声明式 DAG 定义 |
| 元数据管理 | 自动 Schema 发现和编目 | OpenMetadata 集成 |
| 数据质量 | 规则验证和异常检测 | 自定义质量引擎 |
| 数据血缘 | 追踪从源到消费的数据流 | 列级血缘追踪 |
| 特征存储 | 统一的 ML 模型特征管理 | MinIO + 版本化数据集 |
| 向量存储 | 面向 RAG 的高性能向量数据库 | Milvus 2.3 集成 |

### Model 层（机器学习运营）

| 功能 | 描述 | 实现方式 |
| ------ | ------ | ---------- |
| Notebook 环境 | 支持 GPU 的 JupyterHub | K8s 原生部署 |
| 分布式训练 | 多 GPU、多节点训练 | Ray 集成 |
| 模型注册 | 模型版本控制 | MLflow 兼容 API |
| 模型服务 | 高吞吐量推理 | vLLM + OpenAI 兼容 API |
| 实验追踪 | 记录指标、参数、产物 | 内置追踪系统 |
| A/B 部署 | 渐进式发布和流量分割 | Istio 服务网格 |

### Agent 层（大模型运营）

| 功能 | 描述 | 实现方式 |
| ------ | ------ | ---------- |
| RAG 流水线 | 端到端检索增强生成 | LangChain + Milvus |
| Agent 编排 | 支持工具使用的多 Agent 系统 | 自定义 Agent 框架 |
| 可视化工作流 | 拖拽式工作流构建器 | ReactFlow 画布 |
| Prompt 管理 | 带版本控制的模板库 | 支持 A/B 测试 |
| 知识库 | 文档摄取和分块 | 支持 PDF、DOCX、Markdown |
| Text-to-SQL | 自然语言数据库查询 | 元数据增强的 Prompt |
| Token 追踪 | 用量监控和成本控制 | 按请求统计 Token |

### 平台管理

| 功能 | 描述 | 实现方式 |
| ------ | ------ | ---------- |
| 身份管理 | 支持 OIDC/SAML 的 SSO | Keycloak 23.0 |
| 访问控制 | 细粒度 RBAC | 基于角色的权限 |
| 多租户 | 隔离的工作空间 | 命名空间级隔离 |
| 审计日志 | 全面的活动追踪 | 可搜索的审计轨迹 |
| 可观测性 | 指标、链路追踪、日志 | Prometheus + Grafana + Jaeger |

---

## 架构设计

### 四层架构

```
┌───────────────────────────────────────────────────────────────────────────┐
│                       L4 应用编排层 (Agent)                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ RAG 流水线  │   │ Agent 系统   │  │ 工作流       │  │ Text-to-SQL │      │
│  │ • 嵌入      │   │ • 规划      │  │ • ReactFlow │  │ • Schema    │      │
│  │ • 检索      │   │ • 工具调用   │  │ • 节点       │  │ • SQL 生成  │      │
│  │ • 生成      │   │ • 记忆      │  │ • 执行       │  │ • 结果      │      │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │
└───────────────────────────────────────────────────────────────────────────┘
                        ↕ OpenAI 兼容 API / 元数据注入
┌───────────────────────────────────────────────────────────────────────────┐
│                       L3 算法引擎层 (Model)                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ Notebook    │  │ 分布式      │  │ 模型        │  │ 推理        │      │
│  │ • Jupyter   │  │ 训练        │  │ 注册中心    │  │ • vLLM      │      │
│  │ • GPU       │  │ • Ray       │  │ • 版本      │  │ • 批处理    │      │
│  │ • 内核      │  │ • 多 GPU    │  │ • 产物      │  │ • 弹性伸缩  │      │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │
└───────────────────────────────────────────────────────────────────────────┘
                        ↕ 数据集挂载 / 特征获取
┌───────────────────────────────────────────────────────────────────────────┐
│                       L2 数据底座层 (Data)                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ 数据集成     │  │ ETL 引擎     │  │ 数据治理     │  │ 存储        │      │
│  │ • 连接器     │  │ • Flink     │  │ • 元数据    │  │ • MinIO     │      │
│  │ • CDC       │  │ • Spark     │  │ • 质量      │  │ • Milvus    │      │
│  │ • 流式       │  │ • 转换      │  │ • 血缘      │  │ • Redis     │      │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │
└───────────────────────────────────────────────────────────────────────────┘
                        ↕ 存储协议 / 资源调度
┌───────────────────────────────────────────────────────────────────────────┐
│                       L1 基础设施层 (Kubernetes)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ 计算        │  │ 存储         │  │ 网络         │  │ 可观测性    │      │
│  │ • CPU 池    │  │ • PVC       │  │ • Istio     │  │ • Prometheus│      │
│  │ • GPU 池    │  │ • MinIO     │  │ • Ingress   │  │ • Grafana   │      │
│  │ • 自动伸缩  │  │ • HDFS      │  │ • DNS       │  │ • Jaeger    │      │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │
└───────────────────────────────────────────────────────────────────────────┘
```

### 核心服务

| 服务 | 端口 | 框架 | 描述 |
| ------ | ------ | ------ | ------ |
| web | 3000 | React + Vite | 主应用前端 |
| agent-api | 8000 | Flask | LLMOps 编排服务 |
| data-api | 8001 | Flask | 数据治理服务 |
| model-api | 8002 | FastAPI | MLOps 管理服务 |
| openai-proxy | 8003 | FastAPI | OpenAI 兼容代理 |
| admin-api | 8004 | Flask | 平台管理 |
| ocr-service | 8005 | FastAPI | 文档识别 |
| behavior-service | 8006 | Flask | 用户分析 |

### 集成架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            集成点                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────┐     Data → Model (90%)      ┌──────────┐                  │
│  │   Data   │ ─────────────────────────▶  │  Model   │                  │
│  │   层     │   • 统一存储（MinIO）        │   层     │                  │
│  │          │   • 数据集版本化             │          │                  │
│  │          │   • 自动数据集注册           │          │                  │
│  └──────────┘                             └──────────┘                  │
│       │                                        │                         │
│       │                                        │                         │
│       │  Data → Agent (75%)    Model → Agent (85%)                      │
│       │  • 元数据注入          • OpenAI API                              │
│       │  • Text-to-SQL         • vLLM 服务                              │
│       │  • Schema 上下文       • 模型路由                                │
│       ▼                                        ▼                         │
│                        ┌──────────┐                                      │
│                        │  Agent   │                                      │
│                        │   层     │                                      │
│                        └──────────┘                                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 快速开始

### 前置要求

| 要求 | 版本 | 说明 |
| ------ | ------ | ------ |
| Docker | 20.10+ | 所有部署方式都需要 |
| Docker Compose | 2.0+ | 本地开发使用 |
| Node.js | 18+ | 前端开发使用 |
| Python | 3.10+ | 后端开发使用 |
| kubectl | 1.25+ | Kubernetes 部署使用 |
| Helm | 3.x | Helm 部署使用 |

### 方式一：Docker Compose（开发环境）

```bash
# 克隆仓库
git clone https://github.com/iannil/one-data-studio.git
cd one-data-studio

# 配置环境
cp .env.example .env
# 编辑 .env 设置密码：MYSQL_PASSWORD, REDIS_PASSWORD, MINIO_SECRET_KEY 等

# 启动所有服务
docker-compose -f deploy/local/docker-compose.yml up -d

# 查看状态
docker-compose -f deploy/local/docker-compose.yml ps

# 查看日志
docker-compose -f deploy/local/docker-compose.yml logs -f
```

使用 Makefile：

```bash
make dev          # 启动开发环境
make dev-status   # 查看服务状态
make dev-logs     # 查看服务日志
make dev-stop     # 停止所有服务
make dev-clean    # 清理数据卷
```

### 方式二：Kubernetes（生产环境）

```bash
# 创建本地 Kind 集群（用于测试）
make kind-cluster

# 使用 Kustomize 安装
kubectl apply -k deploy/kubernetes/overlays/production

# 或使用 Helm 安装
helm install one-data deploy/helm/charts/one-data \
  --namespace one-data \
  --create-namespace \
  --values deploy/helm/charts/one-data/values-production.yaml

# 查看状态
kubectl get pods -n one-data

# 转发端口以本地访问
make forward
```

### 访问平台

| 服务 | 地址 | 凭证 |
| ------ | ------ | ------ |
| Web UI | <http://localhost:3000> | - |
| Agent API | <http://localhost:8000/docs> | - |
| Data API | <http://localhost:8001/docs> | - |
| Model API | <http://localhost:8002/docs> | - |
| OpenAI Proxy | <http://localhost:8003/docs> | API Key |
| Keycloak | <http://localhost:8080> | admin/admin |
| MinIO | <http://localhost:9001> | minioadmin/minioadmin |
| Grafana | <http://localhost:3001> | admin/admin |
| Prometheus | <http://localhost:9090> | - |

---

## 应用场景

### 1. 企业知识中台

场景：企业各部门有大量分散的文档——政策、流程、技术文档、FAQ。员工难以快速找到所需信息。

ONE-DATA-STUDIO 解决方案：

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  文档       │    │   Data      │    │   Agent     │    │   对话      │
│  来源       │───▶│   层        │───▶│   层        │───▶│   界面      │
│             │    │             │    │             │    │             │
│ • PDF       │    │ • 分块      │    │ • RAG       │    │ • 问答      │
│ • DOCX      │    │ • 嵌入      │    │ • 重排序    │    │ • 引用      │
│ • Markdown  │    │ • Milvus    │    │ • 生成      │    │ • 历史      │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

收益：

- 员工查询响应时间减少 70%
- 自动文档更新和版本控制
- 每个回答都有来源引用

### 2. ChatBI（对话式商业智能）

场景：业务人员需要数据洞察但不会写 SQL。每次查询都依赖数据分析师，形成瓶颈。

ONE-DATA-STUDIO 解决方案：

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  自然语言   │    │   Data      │    │   Agent     │    │   可视化    │
│  查询       │───▶│   层        │───▶│   层        │───▶│   结果      │
│             │    │             │    │             │    │             │
│             │    │ • 元数据    │    │ • Text2SQL  │    │ • 图表      │
│ "显示Q4     │    │ • Schema    │    │ • 查询      │    │ • 表格      │
│  各地区     │    │ • 关系      │    │ • 验证      │    │ • 导出      │
│  销售额"   │    │ • 上下文    │    │ • 执行      │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

收益：

- 无需 SQL 知识即可自助分析
- 数据分析师临时查询工作量减少 80%
- 元数据增强的复杂查询准确性

### 3. 私有化大模型部署

场景：企业想使用大模型但有严格的数据隐私要求。云端 API 不是可选项。

ONE-DATA-STUDIO 解决方案：

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  私有       │    │   Model     │    │   OpenAI    │    │   Agent     │
│  数据       │───▶│   层        │───▶│   Proxy     │───▶│   应用      │
│             │    │             │    │             │    │             │
│ • 训练      │    │ • 微调      │    │ • 兼容 API  │    │ • 对话      │
│   数据      │    │ • vLLM      │    │ • 路由      │    │ • RAG       │
│ • 文档      │    │ • 多 GPU    │    │ • 限流      │    │ • 工作流    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

收益：

- 100% 本地化部署
- OpenAI 兼容 API，易于集成
- 私有 GPU 集群成本可控

### 4. 工业质检

场景：生产线产生传感器数据。提前检测异常可以防止高成本的缺陷和停机。

ONE-DATA-STUDIO 解决方案：

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  IoT        │    │   Data      │    │   Model     │    │   告警      │
│  传感器     │───▶│   层        │───▶│   层        │───▶│   系统      │
│             │    │             │    │             │    │             │
│ • 温度      │    │ • 流式      │    │ • 异常      │    │ • 阈值      │
│ • 压力      │    │ • 特征      │    │ • 检测      │    │ • 仪表盘    │
│ • 振动      │    │ • 存储      │    │ • 实时      │    │ • 动作      │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

收益：

- 亚秒级实时异常检测
- 训练和推理统一特征存储
- 从预测到源数据的全链路可追溯

### 5. 自定义 AI 工作流自动化

场景：复杂业务流程需要多种 AI 能力——文档提取、决策制定、动作执行。

ONE-DATA-STUDIO 解决方案：

```
┌─────────────────────────────────────────────────────────────────────┐
│                      可视化工作流构建器                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐          │
│  │ 触发器  │───▶│  OCR    │───▶│  LLM    │───▶│ 动作    │          │
│  │ (邮件)  │    │ 提取    │    │ 决策    │    │ 执行    │          │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘          │
│                      │              │              │                 │
│                      ▼              ▼              ▼                 │
│               ┌──────────────────────────────────────┐              │
│               │           执行引擎                    │              │
│               │  • 并行执行                           │              │
│               │  • 错误处理                           │              │
│               │  • 状态管理                           │              │
│               └──────────────────────────────────────┘              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

收益：

- 可视化构建器零代码创建工作流
- 单个流程组合任意 AI 能力
- 内置调度和监控

---

## 竞品对比

### 对比独立平台

| 方面 | ONE-DATA-STUDIO | 独立工具组合 |
| ------ | ----------------- | -------------- |
| Data + ML + LLM | 单一集成平台 | 3+ 个独立工具（Airflow + MLflow + LangChain） |
| 数据到模型流水线 | 原生集成 | 手动数据导出/导入 |
| 模型到应用流水线 | OpenAI 兼容 API | 自定义集成代码 |
| 统一治理 | 单一审计轨迹 | 分散的日志 |
| 学习曲线 | 学习一个平台 | 掌握多个工具 |
| 部署 | 单个 Helm Chart | 多个部署 |
| 成本 | 单一基础设施 | 多套基础设施 |

### 对比云平台

| 方面 | ONE-DATA-STUDIO | 云平台（Databricks、SageMaker、Vertex AI） |
| ------ | ----------------- | ------------------------------------------- |
| 部署 | 本地、任何云、混合 | 锁定特定云厂商 |
| 数据隐私 | 数据留在本地 | 数据在厂商云中 |
| 定价 | 开源（免费） | 按用量计费（规模化后昂贵） |
| 定制化 | 完整源代码访问 | 有限定制 |
| LLM 集成 | 内置 LLMOps 层 | 需要独立 LLM 工具 |
| 厂商锁定 | 无 | 高 |

### 对比其他开源平台

| 功能 | ONE-DATA-STUDIO | LangChain | MLflow | Apache Airflow |
| ------ | ----------------- | ----------- | -------- | ---------------- |
| 数据集成 | ✅ 完整 | ❌ 无 | ❌ 无 | ✅ 基础 |
| ETL 流水线 | ✅ 可视化 | ❌ 无 | ❌ 无 | ✅ 代码式 |
| 特征存储 | ✅ 内置 | ❌ 无 | ❌ 无 | ❌ 无 |
| 向量存储 | ✅ Milvus | ✅ 集成 | ❌ 无 | ❌ 无 |
| 模型训练 | ✅ 分布式 | ❌ 无 | ✅ 仅追踪 | ❌ 无 |
| 模型服务 | ✅ vLLM | ❌ 无 | ✅ 基础 | ❌ 无 |
| RAG 流水线 | ✅ 完整 | ✅ 完整 | ❌ 无 | ❌ 无 |
| Agent 框架 | ✅ 内置 | ✅ 主要功能 | ❌ 无 | ❌ 无 |
| 可视化工作流 | ✅ ReactFlow | ❌ 无 | ❌ 无 | ❌ 代码式 |
| Web UI | ✅ 完整 | ❌ 无 | ✅ 追踪 UI | ✅ DAG UI |
| 多租户 | ✅ 完整 | ❌ 无 | ❌ 无 | ❌ 有限 |
| 企业认证 | ✅ Keycloak | ❌ 无 | ❌ 无 | ❌ 有限 |

### 何时选择 ONE-DATA-STUDIO

✅ 最适合：

- 需要完整数据到应用流水线的企业
- 需要本地化部署的组织
- 希望统一平台而非工具碎片化的团队
- 同时有结构化数据和文档知识需求的公司
- 需要完整审计轨迹和治理的项目

❌ 考虑其他方案如果：

- 只需要单一能力（如只需要 MLflow 做实验追踪）
- 云优先组织且接受厂商锁定
- 需要最小基础设施且偏好 SaaS 方案
- 团队规模很小（< 5 人）且需求简单

---

## 技术规格

### 代码统计

| 组件 | 文件数 | 代码行数 |
| ------ | -------- | ---------- |
| Python 后端 | 289 | ~142,000 |
| TypeScript 前端 | 232 | ~120,000 |
| 测试代码 | 135+ | ~32,000 |
| 部署配置 | 155+ | ~15,000 |
| 总计 | 630+ | ~300,000 |

### 技术栈

前端：

- React 18.3 + TypeScript 5.4
- Ant Design 5.14 UI 组件
- ReactFlow 11.10 工作流画布
- Zustand 4.5 状态管理
- React Query 5.24 服务端状态
- Vite 5.1 构建工具

后端：

- Python 3.10+ 运行时
- Flask 3.0（Data/Agent/Admin API）
- FastAPI（Model/Proxy API）
- SQLAlchemy 2.0 + Alembic 迁移
- Celery 后台任务

存储：

- MySQL 8.0 关系数据
- Redis 7.0 缓存和会话
- MinIO S3 兼容对象存储
- Milvus 2.3 向量嵌入
- Elasticsearch 8.10 搜索

基础设施：

- Kubernetes 1.27+ 编排
- Helm 3.x 包管理
- Istio 服务网格
- Keycloak 23.0 身份管理
- Prometheus + Grafana 监控
- Jaeger 分布式追踪

### 安全特性

| 类别 | 功能 |
| ------ | ------ |
| 认证 | JWT Token、Keycloak SSO、OIDC/SAML 支持 |
| 授权 | RBAC、细粒度权限、多租户隔离 |
| 网络 | TLS/HTTPS、HSTS 头、CORS 配置 |
| 数据 | SQL 注入防护、输入净化、静态加密 |
| 审计 | 全面日志、可搜索审计轨迹、合规支持 |

### 性能指标

| 指标 | 值 | 说明 |
| ------ | ----- | ------ |
| API 响应时间 | < 100ms (p95) | 元数据操作 |
| RAG 查询延迟 | < 2s (p95) | 包含检索和生成 |
| 向量搜索 | < 50ms | 1000万+ 向量 |
| 并发用户 | 1000+ | 适当资源分配下 |
| 模型推理 | 取决于模型 | vLLM 提供高吞吐 |

---

## 项目结构

```
one-data-studio/
├── services/                     # 后端微服务
│   ├── data-api/                 # 数据治理 API (Flask)
│   │   ├── app/
│   │   │   ├── routes/           # API 端点
│   │   │   ├── services/         # 业务逻辑
│   │   │   ├── models/           # 数据库模型
│   │   │   └── schemas/          # 请求/响应 Schema
│   │   └── requirements.txt
│   ├── agent-api/                # LLMOps 编排 API (Flask)
│   │   ├── app/
│   │   │   ├── routes/           # 工作流、RAG、Agent 端点
│   │   │   ├── services/         # 执行引擎、RAG 服务
│   │   │   ├── core/             # LLM 客户端、嵌入
│   │   │   └── tools/            # Agent 工具
│   │   └── requirements.txt
│   ├── model-api/                # MLOps 管理 API (FastAPI)
│   │   ├── app/
│   │   │   ├── routers/          # 模型、训练、服务端点
│   │   │   ├── services/         # K8s 集成、任务管理
│   │   │   └── schemas/          # Pydantic Schema
│   │   └── requirements.txt
│   ├── openai-proxy/             # OpenAI 兼容代理 (FastAPI)
│   │   ├── app/
│   │   │   ├── routers/          # 对话、补全、嵌入
│   │   │   ├── services/         # 模型路由、限流
│   │   │   └── middleware/       # Token 统计、成本追踪
│   │   └── requirements.txt
│   ├── admin-api/                # 平台管理 (Flask)
│   ├── ocr-service/              # 文档识别 (FastAPI)
│   ├── behavior-service/         # 用户分析 (Flask)
│   └── shared/                   # 共享模块
│       ├── auth/                 # JWT、权限
│       ├── storage/              # MinIO、文件处理
│       ├── cache/                # Redis 工具
│       └── utils/                # 通用工具
├── web/                          # 前端应用
│   ├── src/
│   │   ├── components/           # 可复用 UI 组件
│   │   │   ├── common/           # 按钮、输入框、弹窗
│   │   │   ├── workflow/         # ReactFlow 节点和边
│   │   │   └── charts/           # 数据可视化
│   │   ├── pages/                # 页面组件
│   │   │   ├── data/             # 数据平台页面
│   │   │   ├── model/            # 模型平台页面
│   │   │   ├── agent/            # Agent 平台页面
│   │   │   └── admin/            # 管理页面
│   │   ├── services/             # API 客户端
│   │   ├── stores/               # Zustand 状态存储
│   │   ├── hooks/                # 自定义 React Hooks
│   │   ├── utils/                # 工具函数
│   │   └── locales/              # i18n 翻译（en, zh）
│   ├── public/                   # 静态资源
│   └── package.json
├── deploy/                       # 部署配置
│   ├── local/                    # Docker Compose
│   │   ├── docker-compose.yml    # 主 Compose 文件
│   │   └── docker-compose.*.yml  # 服务覆盖
│   ├── kubernetes/               # Kubernetes 清单
│   │   ├── base/                 # Kustomize 基础
│   │   └── overlays/             # dev, staging, production
│   ├── helm/                     # Helm Charts
│   │   └── charts/one-data/      # 主 Chart
│   ├── dockerfiles/              # 各服务 Dockerfile
│   ├── argocd/                   # ArgoCD 应用
│   └── monitoring/               # Prometheus、Grafana 配置
├── tests/                        # 测试套件
│   ├── unit/                     # 按服务单元测试
│   ├── integration/              # API 集成测试
│   ├── e2e/                      # Playwright 端到端测试
│   └── performance/              # 负载测试脚本
├── docs/                         # 文档
│   ├── 01-architecture/          # 架构文档
│   ├── 02-integration/           # 集成指南
│   ├── 06-development/           # 开发指南
│   ├── 07-operations/            # 运维指南
│   └── 08-user-guide/            # 用户文档
└── examples/                     # 使用示例
    ├── langchain/                # LangChain 集成
    ├── python/                   # Python SDK 示例
    └── workflows/                # 工作流定义
```

---

## 文档

| 文档 | 描述 |
| ------ | ------ |
| [平台概览](docs/01-architecture/platform-overview.md) | 高层架构和概念 |
| [四层架构](docs/01-architecture/four-layer-stack.md) | 详细层级描述 |
| [集成指南](docs/02-integration/integration-overview.md) | 层间连接方式 |
| [API 规范](docs/02-integration/api-specifications.md) | REST API 文档 |
| [开发指南](docs/06-development/poc-playbook.md) | 本地开发设置 |
| [运维指南](docs/07-operations/operations-guide.md) | 生产部署 |
| [用户手册](docs/08-user-guide/getting-started.md) | 终端用户文档 |

---

## 贡献指南

我们欢迎社区贡献！

### 开发环境搭建

```bash
# 后端开发
cd services/agent-api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
python app.py

# 前端开发
cd web
npm install
npm run dev
```

### 代码规范

| 语言 | 规范 |
| ------ | ------ |
| Python | PEP 8，使用 `logging`（非 `print`），类型注解 |
| TypeScript | ESLint + Prettier，避免 `console.log` |
| Git | 约定式提交，小步原子提交 |

### 测试

```bash
# 运行 Python 测试
pytest tests/ -v

# 带覆盖率运行
pytest tests/ --cov=services/ --cov-report=html

# 运行前端测试
cd web && npm test

# 运行 E2E 测试
cd tests/e2e && npx playwright test
```

### Pull Request 流程

1. Fork 仓库
2. 创建特性分支：`git checkout -b feature/amazing-feature`
3. 进行修改并添加测试
4. 确保测试通过：`pytest tests/ && cd web && npm test`
5. 清晰的提交信息：`git commit -m 'feat: 添加 amazing 功能'`
6. 推送并创建 Pull Request

---

## 开源许可

本项目采用 Apache License 2.0 许可证 - 详见 [LICENSE](LICENSE) 文件。

```
Copyright 2024-2026 ONE-DATA-STUDIO Contributors

根据 Apache 许可证 2.0 版本（"许可证"）授权；
除非符合许可证，否则您不得使用此文件。
您可以在以下网址获取许可证副本：

    http://www.apache.org/licenses/LICENSE-2.0
```

---

## 致谢

基于以下优秀项目构建：

- [OpenMetadata](https://open-metadata.org/) - 开源元数据平台
- [Ray](https://github.com/ray-project/ray) - 分布式计算框架
- [vLLM](https://github.com/vllm-project/vllm) - 高吞吐量 LLM 服务
- [LangChain](https://github.com/langchain-ai/langchain) - LLM 应用框架
- [Milvus](https://github.com/milvus-io/milvus) - 向量数据库
- [ReactFlow](https://reactflow.dev/) - 节点图编辑器

---

## 社区

- 问题反馈：[GitHub Issues](https://github.com/iannil/one-data-studio/issues)
- 讨论交流：[GitHub Discussions](https://github.com/iannil/one-data-studio/discussions)

---

<div align="center">

由 ONE-DATA-STUDIO 社区用心构建

如果这个项目对您有帮助，欢迎给我们一个 ⭐！

[返回顶部](#one-data-studio)

</div>
