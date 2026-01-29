# ONE-DATA-STUDIO 项目依赖评估报告

## 评估概述

本报告对 ONE-DATA-STUDIO 项目所依赖的平台、服务和开源产品进行全面梳理。

---

## 项目架构说明

本项目包含三个自研微服务（非外部依赖）：
- `services/data-api/` - 数据治理 API（DataOps）
- `services/model-api/` - MLOps API
- `services/agent-api/` - LLMOps API

这些是项目内部实现的服务，通过 HTTP 相互调用（如 `http://data-api:8080`）。

---

## 一、基础设施层依赖

### 容器与编排
| 平台/工具 | 版本 | 许可证 | 用途 |
|----------|------|--------|------|
| Kubernetes | 1.27+ | Apache 2.0 | 容器编排与集群管理 |
| Docker | - | Apache 2.0 | 容器运行时 |
| Helm | 3.13+ | Apache 2.0 | K8s 应用包管理 |
| Istio | 1.19+ | Apache 2.0 | 服务网格、流量管理、mTLS |

### 监控与可观测性
| 平台/工具 | 版本 | 许可证 | 用途 |
|----------|------|--------|------|
| Prometheus | 2.47+ | Apache 2.0 | 指标采集与告警 |
| Grafana | 10.x | AGPLv3 | 监控可视化 |
| Loki | 2.9+ | AGPLv3 | 日志聚合 |
| Jaeger | - | Apache 2.0 | 分布式链路追踪 |
| OpenTelemetry | 1.22.0 | Apache 2.0 | 可观测性框架 |

---

## 二、数据库与存储

### 关系型数据库
| 数据库 | 版本 | 许可证 | 用途 |
|-------|------|--------|------|
| **MySQL** | 8.0+ | GPL v2 | 核心业务数据库 |

### 缓存与消息队列
| 服务 | 版本 | 许可证 | 用途 |
|-----|------|--------|------|
| **Redis** | 7.0+ | BSD | 缓存、会话、消息队列 |
| Apache Kafka | 3.6+ | Apache 2.0 | 高吞吐消息队列（可选） |
| RabbitMQ | 3.12+ | MPL 2.0 | 消息队列（备选） |
| **Celery** | 5.3.4 | BSD | Python 分布式任务队列 |

### 向量数据库
| 数据库 | 版本 | 许可证 | 用途 |
|-------|------|--------|------|
| **Milvus** | 2.3+ | Apache 2.0 | 向量存储与检索（推荐） |
| **etcd** | v3.5.5 | Apache 2.0 | Milvus 元数据存储 |
| PgVector | 0.5+ | PostgreSQL | PostgreSQL 向量扩展（备选） |

### 搜索引擎
| 服务 | 版本 | 许可证 | 用途 |
|-----|------|--------|------|
| **Elasticsearch** | 8.10.2 | SSPL/Elastic | 全文搜索、日志索引 |

### 对象存储
| 服务 | 版本 | 许可证 | 用途 |
|-----|------|--------|------|
| **MinIO** | RELEASE.2023+ | AGPLv3 | S3 兼容对象存储 |
| AWS S3 | - | 商业 | 云存储（可选替代） |
| HDFS | - | Apache 2.0 | 分布式文件系统 |

---

## 三、数据处理与 ETL

| 平台/工具 | 版本 | 许可证 | 用途 |
|----------|------|--------|------|
| Apache Flink | 1.17+ | Apache 2.0 | 流式数据处理 |
| Apache Spark | 3.5+ | Apache 2.0 | 批量数据处理 |
| **Pentaho Kettle (Webspoon)** | 0.9.0.27 | LGPL/Apache | Web 化 ETL 设计与执行 |
| SeaTunnel | 2.3+ | Apache 2.0 | 数据集成工具 |
| DolphinScheduler | 3.2+ | Apache 2.0 | 工作流调度 |

---

## 四、元数据与治理

| 平台 | 版本 | 许可证 | 用途 |
|-----|------|--------|------|
| **OpenMetadata** | 1.3.1 | Apache 2.0 | 元数据管理与数据治理 |
| DataHub | 0.12+ | Apache 2.0 | 元数据管理（备选） |
| Apache Atlas | - | Apache 2.0 | 企业级元数据（备选） |

---

## 五、AI/ML 推理与框架

### LLM 推理引擎
| 服务 | 版本 | 许可证 | 用途 |
|-----|------|--------|------|
| **vLLM** | 0.3+ | Apache 2.0 | 高性能 LLM 推理（推荐） |
| TensorRT-LLM (TGI) | 1.3+ | Apache 2.0 | 文本生成推理（备选） |

### 深度学习框架
| 框架 | 版本 | 许可证 | 用途 |
|-----|------|--------|------|
| PyTorch | 2.1+ | BSD | 深度学习模型训练 |
| **PaddlePaddle** | 2.6.0 | Apache 2.0 | 飞桨深度学习框架（OCR） |

### 分布式计算
| 框架 | 版本 | 许可证 | 用途 |
|-----|------|--------|------|
| Ray | 2.8+ | Apache 2.0 | 分布式计算与推理 |
| Volcano | 1.9+ | Apache 2.0 | K8s 批量调度器 |
| JupyterHub | 3.0+ | BSD | 多租户 Notebook 环境 |

---

## 六、LLM 应用框架

| 框架 | 版本 | 许可证 | 用途 |
|-----|------|--------|------|
| **LangChain** | 0.1.14 | MIT | LLM 应用编排（Agent、Chain） |
| LlamaIndex | 0.9+ | MIT | RAG 数据框架 |
| **OpenAI SDK** | 1.10.0+ | MIT | OpenAI API 客户端 |

---

## 七、OCR 与文档处理

| 工具 | 版本 | 许可证 | 用途 |
|-----|------|--------|------|
| **PaddleOCR** | 2.7.0.3 | Apache 2.0 | 中文 OCR 识别 |
| **PaddleNLP** | 2.6.0+ | Apache 2.0 | NLP 任务（UIE 信息提取） |
| PyMuPDF | 1.23.8 | AGPL | PDF 处理 |
| pdf2image | 1.16.3 | MIT | PDF 转图片 |
| pdfplumber | 0.10.3 | MIT | PDF 表格提取 |
| python-docx | 1.1.0 | MIT | Word 文档处理 |
| openpyxl | 3.1.2 | MIT | Excel 文件处理 |
| Camelot | 0.11.0 | MIT | 表格数据提取 |
| Tabula | 2.9.0 | MIT | PDF 表格提取 |

---

## 八、认证与安全

| 服务 | 版本 | 许可证 | 用途 |
|-----|------|--------|------|
| **Keycloak** | 23.0+ | Apache 2.0 | 统一身份认证（SSO/OIDC） |
| OPA | 0.60+ | Apache 2.0 | 策略引擎 |
| HashiCorp Vault | 1.15+ | BSL | 密钥管理（可选） |

---

## 九、Python 后端依赖

### Web 框架
| 框架 | 版本 | 使用服务 |
|-----|------|---------|
| **Flask** | 3.0.0 | data-api, agent-api, model-api, admin-api, openai-proxy |
| **FastAPI** | 0.109.0 | behavior-service, ocr-service |
| Uvicorn | 0.27.0 | ASGI 服务器 |
| Werkzeug | 3.0.1 | WSGI 工具库 |

### ORM 与数据库
| 库 | 版本 | 用途 |
|---|------|------|
| **SQLAlchemy** | 2.0.23+ | ORM 框架 |
| **PyMySQL** | 1.1.0 | MySQL 驱动 |
| **Alembic** | 1.13.0 | 数据库迁移 |
| **pymilvus** | 2.3.7 | Milvus 客户端 |
| **minio** | 7.2.0 | MinIO 客户端 |
| **redis** | 5.0.1 | Redis 客户端 |

### HTTP 客户端
| 库 | 版本 | 用途 |
|---|------|------|
| requests | 2.31.0 | 同步 HTTP |
| **httpx** | 0.25.2+ | 异步 HTTP |
| aiohttp | 3.9.5 | 异步 HTTP 框架 |

### 认证与安全
| 库 | 版本 | 用途 |
|---|------|------|
| **PyJWT** | 2.8.0 | JWT 令牌 |
| cryptography | 41.0.7 | 加密库 |
| bcrypt | 4.0.0 | 密码哈希 |

### 配置与验证
| 库 | 版本 | 用途 |
|---|------|------|
| **Pydantic** | 2.5.2+ | 数据验证 |
| jsonschema | 4.20.0 | JSON Schema |
| python-dotenv | 1.0.0 | 环境变量 |

### 调度与任务
| 库 | 版本 | 用途 |
|---|------|------|
| APScheduler | 3.10.4 | 定时调度 |
| croniter | 2.0.1 | Cron 解析 |

### 日志与监控
| 库 | 版本 | 用途 |
|---|------|------|
| loguru | 0.7.2 | 现代日志库 |
| prometheus-client | 0.19.0 | Prometheus 指标 |
| opentelemetry-* | 1.22.0 | 链路追踪 |

### WebSocket
| 库 | 版本 | 用途 |
|---|------|------|
| flask-socketio | 5.3.6 | WebSocket 支持 |
| python-socketio | 5.11.0 | Socket.IO |

---

## 十、前端技术栈

### 核心框架
| 技术 | 版本 | 用途 |
|-----|------|------|
| **React** | 18.3.1 | UI 框架 |
| **TypeScript** | 5.4.0 | 类型安全 |
| **Vite** | 5.1.0 | 构建工具 |

### UI 组件库
| 库 | 版本 | 用途 |
|---|------|------|
| **Ant Design** | 5.14.0 | 企业级 UI |
| Ant Design Icons | 5.3.0 | 图标库 |

### 状态管理
| 库 | 版本 | 用途 |
|---|------|------|
| **Zustand** | 4.5.0 | 轻量状态管理 |
| **TanStack React Query** | 5.24.0 | 服务器状态 |

### 路由与通信
| 库 | 版本 | 用途 |
|---|------|------|
| React Router DOM | 6.22.0 | 客户端路由 |
| **Axios** | 1.6.7 | HTTP 请求 |

### 国际化
| 库 | 版本 | 用途 |
|---|------|------|
| **i18next** | 25.8.0 | 国际化框架 |
| react-i18next | 16.5.3 | React 集成 |

### 数据可视化
| 库 | 版本 | 用途 |
|---|------|------|
| **Cytoscape** | 3.33.1 | 图数据可视化 |
| **ReactFlow** | 11.10.0 | 流程图组件 |

### 代码编辑器
| 库 | 版本 | 用途 |
|---|------|------|
| @uiw/react-codemirror | 4.21.0 | 代码编辑器 |
| @codemirror/lang-sql | 6.6.0 | SQL 语法高亮 |

### 文本处理
| 库 | 版本 | 用途 |
|---|------|------|
| react-markdown | 9.0.0 | Markdown 渲染 |
| marked | 12.0.0 | Markdown 解析 |
| dompurify | 3.0.8 | XSS 防护 |

### 测试框架
| 库 | 版本 | 用途 |
|---|------|------|
| **Vitest** | 1.3.1 | 单元测试 |
| @testing-library/react | 14.2.1 | React 测试 |
| jsdom | 24.0.0 | DOM 模拟 |

### 代码质量
| 库 | 版本 | 用途 |
|---|------|------|
| **ESLint** | 8.57.0 | 代码检查 |
| **Prettier** | 3.2.5 | 代码格式化 |

---

## 十一、Docker 基础镜像

| 用途 | 基础镜像 | 说明 |
|-----|---------|------|
| Python 后端 | **python:3.10.14-slim** | 所有后端服务 |
| 前端开发/构建 | **node:20-alpine** | 开发与构建阶段 |
| 前端生产 | **nginx:alpine** | 静态文件服务 |

---

## 十二、外部 API 与服务

| 服务 | 类型 | 用途 |
|-----|------|------|
| OpenAI API | 商业 API | LLM 推理（可选） |
| HuggingFace Hub | 模型仓库 | 模型下载 |
| GitHub | 代码托管 | 版本控制 |

---

## 十三、依赖统计汇总

| 类别 | 数量 | 备注 |
|-----|------|------|
| 基础设施组件 | 10+ | K8s, Docker, Istio, 监控栈 |
| 数据库与存储 | 8 | MySQL, Redis, Milvus, MinIO, ES 等 |
| 数据处理/ETL | 5 | Flink, Spark, Kettle 等 |
| AI/ML 框架 | 8 | vLLM, PyTorch, Paddle, LangChain 等 |
| Python 后端库 | 50+ | Flask, FastAPI, SQLAlchemy 等 |
| 前端依赖 | 40+ | React, Ant Design, Vite 等 |
| 外部服务容器 | 6 | MySQL, Redis, Milvus, MinIO, ES, Keycloak |

---

## 十四、关键风险与注意事项

### 许可证风险
| 依赖 | 许可证 | 风险级别 | 说明 |
|-----|--------|---------|------|
| Elasticsearch | SSPL | ⚠️ 中 | 需评估商业使用条款 |
| Grafana | AGPLv3 | ⚠️ 中 | 需开源修改代码 |
| MinIO | AGPLv3 | ⚠️ 中 | 需开源修改代码 |
| PyMuPDF | AGPL | ⚠️ 中 | 商业使用需付费 |
| HashiCorp Vault | BSL | ⚠️ 中 | 商业竞争限制 |

### 版本兼容性
- Python 要求 >= 3.10
- Node.js 要求 >= 20.x
- MySQL 8.0+（重要：与 5.7 有重大变化）
- Kubernetes 1.27+

### 中文支持
- PaddleOCR/PaddleNLP：中文 OCR 首选
- 向量嵌入：推荐 BAAI 系列模型

---

## 结论

ONE-DATA-STUDIO 是一个技术栈丰富的企业级平台，依赖约 **100+ 开源组件**，覆盖：
- **DataOps** (数据治理)
- **MLOps** (模型训练)
- **LLMOps** (AI 应用)

所有核心依赖均为开源，支持私有化部署，无商业锁定。

---

## 更新记录

| 日期 | 版本 | 更新内容 | 更新人 |
|------|------|----------|--------|
| 2026-01-29 | v1.0 | 初始版本，完成全面依赖评估 | Claude |
