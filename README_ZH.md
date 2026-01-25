# ONE-DATA-STUDIO

<div align="center">

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18.3-blue.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.4-blue.svg)](https://www.typescriptlang.org/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.27%2B-326ce5.svg)](https://kubernetes.io/)
[![Docker](https://img.shields.io/badge/Docker-20.10%2B-2496ED.svg)](https://www.docker.com/)

**企业级 DataOps + MLOps + LLMOps 融合平台**

[功能特性](#功能特性) | [快速开始](#快速开始) | [架构设计](#架构设计) | [文档](#文档) | [贡献指南](#贡献指南) | [English](README.md)

</div>

---

## 项目简介

**ONE-DATA-STUDIO** 是一个开源的企业级平台，融合了三个关键的 AI 基础设施层：

- **Alldata** - 数据治理与开发平台（DataOps 层）
- **Cube Studio** - 云原生 MLOps 平台（模型/计算层）
- **Bisheng** - 大模型应用开发平台（LLMOps 层）

该平台打通了从**原始数据治理**到**模型训练部署**，再到**生成式 AI 应用构建**的完整价值链。

## 为什么选择 ONE-DATA-STUDIO？

### 打破数据与 AI 的孤岛

数据团队（使用 Alldata）和算法团队（使用 Cube Studio）往往各自为政。我们的整合实现了**无缝的特征平台**，算法工程师可以直接使用经过治理的高质量数据，无需重复清洗。

### 结构化与非结构化数据的统一

Alldata 擅长处理结构化数据，Bisheng 擅长处理非结构化文档。两者结合后，企业可以构建**"ChatBI"**——既能查询文档知识库，又能用自然语言查询数据库中的销售报表（Text-to-SQL）。

### 私有化大模型落地的完整闭环

许多企业只想用 Bisheng 做应用，但缺乏模型微调能力；或者只有 Cube Studio 训练了模型，但缺乏好用的应用构建工具。

**三者结合 = 私有数据 (Alldata) + 私有算力/模型 (Cube Studio) + 私有应用 (Bisheng)**。这构成了最安全的企业级 AGI 解决方案。

### 全生命周期治理

从数据血缘（Alldata）到模型血缘（Cube Studio）再到应用日志，整个链路可追溯。如果 AI 回答出错，可以一路追溯是 Prompt 问题、模型过拟合，还是原始数据本身就是脏数据。

## 功能特性

### 数据运营 (DataOps)

- 数据集成和 ETL 流水线
- 元数据管理和数据治理
- 面向机器学习的特征存储
- 面向 RAG 应用的向量存储（Milvus）

### 机器学习运营 (MLOps)

- Jupyter Notebook 开发环境
- 基于 Ray 的分布式模型训练
- 模型注册和版本管理
- 基于 vLLM 的模型服务（OpenAI 兼容 API）

### 大模型运营 (LLMOps)

- RAG（检索增强生成）流水线
- Agent 编排和可视化工作流构建器
- Prompt 管理和模板
- 知识库管理

### 平台管理

- 基于 Keycloak 的统一用户管理和 SSO
- 基于角色的访问控制（RBAC）
- 多租户支持
- 全面的审计日志

## 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    L4 应用编排层 (Bisheng)                        │
│                RAG 流水线 | Agent 编排 | 工作流                    │
└─────────────────────────────────────────────────────────────────┘
                              ↕ OpenAI API / 元数据
┌─────────────────────────────────────────────────────────────────┐
│                   L3 算法引擎层 (Cube Studio)                     │
│               Notebook | 分布式训练 | 模型服务化                    │
└─────────────────────────────────────────────────────────────────┘
                              ↕ 挂载数据卷
┌─────────────────────────────────────────────────────────────────┐
│                    L2 数据底座层 (Alldata)                        │
│           数据集成 | ETL | 数据治理 | 特征存储 | 向量存储            │
└─────────────────────────────────────────────────────────────────┘
                              ↕ 存储协议
┌─────────────────────────────────────────────────────────────────┐
│                    L1 基础设施层 (Kubernetes)                     │
│              CPU/GPU 资源池 | 存储 | 网络 | 监控                   │
└─────────────────────────────────────────────────────────────────┘
```

## 核心集成点

| 集成方向 | 描述 | 完成度 |
| ---------- | ------ | -------- |
| **Alldata → Cube** | 统一存储协议与数据集版本化 | 90% |
| **Cube → Bisheng** | OpenAI 兼容的模型即服务 API | 85% |
| **Alldata → Bisheng** | 基于元数据的 Text-to-SQL | 75% |

## 技术栈

### 前端

| 技术 | 版本 | 用途 |
| ------ | ------ | ------ |
| React | 18.3 | UI 框架 |
| TypeScript | 5.4 | 类型安全 |
| Ant Design | 5.14 | UI 组件库 |
| React Router | 6.22 | 路由管理 |
| React Query | 5.24 | 服务端状态管理 |
| Zustand | 4.5 | 客户端状态管理 |
| ReactFlow | 11.10 | 工作流画布 |
| Vite | 5.1 | 构建工具 |
| Vitest | 1.3 | 测试框架 |

### 后端服务

| 技术 | 版本 | 用途 |
| ------ | ------ | ------ |
| Python | 3.10+ | 运行时 |
| Flask | - | Web 框架 (Alldata, Bisheng) |
| FastAPI | - | Web 框架 (OpenAI Proxy, Cube) |
| MySQL | 8.0 | 持久化存储 |
| Redis | 7.0 | 缓存和会话 |
| MinIO | Latest | S3 兼容对象存储 |
| Milvus | 2.3 | 向量数据库 |

### 基础设施

| 技术 | 版本 | 用途 |
| ------ | ------ | ------ |
| Kubernetes | 1.27+ | 容器编排 |
| Docker | 20.10+ | 容器化 |
| Helm | 3.13+ | 包管理 |
| Keycloak | 23.0 | 身份认证与访问管理 |
| Prometheus | - | 指标采集 |
| Grafana | - | 监控面板 |

## 快速开始

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- Node.js 18+（前端开发需要）
- Python 3.10+（后端开发需要）
- kubectl 1.25+（Kubernetes 部署需要）
- Helm 3.x（Helm 部署需要）

### 方式一：Docker Compose（推荐开发环境）

```bash
# 克隆仓库
git clone https://github.com/one-data-studio/one-data-studio.git
cd one-data-studio

# 复制环境配置
cp .env.example .env
# 编辑 .env 文件，设置必要的密码（MYSQL_PASSWORD, REDIS_PASSWORD 等）

# 启动所有服务
docker-compose -f deploy/local/docker-compose.yml up -d

# 查看服务状态
docker-compose -f deploy/local/docker-compose.yml ps
```

或使用 Makefile 快捷命令：

```bash
make dev        # 启动开发环境
make dev-status # 查看服务状态
make dev-logs   # 查看服务日志
make dev-stop   # 停止所有服务
```

### 方式二：Kubernetes（推荐生产环境）

```bash
# 创建 Kind 集群（本地测试用）
make kind-cluster

# 部署所有服务
make install

# 查看状态
make status

# 转发端口访问服务
make forward
```

### 访问平台

| 服务 | 地址 | 说明 |
| ------ | ------ | ------ |
| Web UI | <http://localhost:3000> | 主应用界面 |
| Bisheng API | <http://localhost:8000> | 应用编排 API |
| Alldata API | <http://localhost:8001> | 数据治理 API |
| Cube API | <http://localhost:8002> | 模型服务 API |
| OpenAI Proxy | <http://localhost:8003> | OpenAI 兼容代理 |
| Admin API | <http://localhost:8004> | 平台管理 API |
| Keycloak | <http://localhost:8080> | 身份管理 |
| MinIO 控制台 | <http://localhost:9001> | 对象存储控制台 |
| Prometheus | <http://localhost:9090> | 指标监控 |
| Grafana | <http://localhost:3001> | 监控面板 (admin/admin) |

## 项目结构

```
one-data-studio/
├── services/                 # 后端服务
│   ├── alldata-api/          # 数据治理 API (Flask)
│   ├── bisheng-api/          # 应用编排 API (Flask)
│   ├── cube-api/             # 模型服务 API (FastAPI)
│   ├── openai-proxy/         # OpenAI 兼容代理 (FastAPI)
│   ├── admin-api/            # 平台管理 API (Flask)
│   └── shared/               # 共享模块（认证、存储、工具）
├── web/                      # 前端应用 (React + TypeScript)
│   ├── src/
│   │   ├── components/       # 可复用 UI 组件
│   │   ├── pages/            # 页面组件
│   │   ├── services/         # API 客户端
│   │   ├── stores/           # Zustand 状态存储
│   │   └── locales/          # i18n 翻译文件
│   └── public/               # 静态资源
├── deploy/                   # 部署配置
│   ├── local/                # Docker Compose 文件
│   ├── kubernetes/           # Kubernetes 清单文件
│   ├── helm/                 # Helm Charts
│   ├── dockerfiles/          # Docker 构建文件
│   └── scripts/              # 部署脚本
├── scripts/                  # 开发和运维脚本
│   └── dev/                  # 开发环境脚本
├── tests/                    # 测试文件
│   ├── unit/                 # 单元测试
│   ├── integration/          # 集成测试
│   └── e2e/                  # 端到端测试
├── docs/                     # 文档
│   ├── 01-architecture/      # 架构文档
│   ├── 02-integration/       # 集成指南
│   ├── 05-development/       # 开发指南
│   ├── 06-operations/        # 运维指南
│   └── 07-user-guide/        # 用户文档
└── examples/                 # 使用示例
    ├── langchain/            # LangChain 集成示例
    ├── python/               # Python SDK 示例
    └── workflows/            # 工作流定义示例
```

## 应用场景

### 企业知识中台

统一管理企业文档知识，提供智能问答能力。将内部文档、政策和流程整合为可搜索的知识库，支持自然语言查询。

### ChatBI（商业智能）

用自然语言查询数据库，自动生成报表。连接数据仓库后，可以直接提问"显示上季度各地区的销售数据"——系统自动生成 SQL 并可视化结果。

### 工业质检

传感器数据实时分析，实现预测性维护。处理流式 IoT 数据，训练异常检测模型，部署到生产环境进行实时监控。

### 自定义 AI 应用

使用可视化工作流构建器创建复杂的 AI 应用。结合 RAG、Agent 和工具，构建客服机器人、文档处理器或研究助手。

## 文档

- [架构概览](docs/01-architecture/platform-overview.md)
- [四层架构](docs/01-architecture/four-layer-stack.md)
- [集成指南](docs/02-integration/integration-overview.md)
- [API 规范](docs/02-integration/api-specifications.md)
- [开发指南](docs/05-development/poc-playbook.md)
- [运维指南](docs/06-operations/operations-guide.md)
- [用户手册](docs/07-user-guide/getting-started.md)

## 贡献指南

我们欢迎社区贡献！

### 开发环境搭建

```bash
# 后端开发
cd services/bisheng-api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py

# 前端开发
cd web
npm install
npm run dev
```

### 代码规范

- **Python**：遵循 PEP 8，使用 `logging` 而非 `print()`
- **TypeScript**：遵循 ESLint 规则，避免 `console.log`（仅在错误时使用 `console.error`）
- **提交信息**：使用清晰的描述性提交说明

### 测试

```bash
# 运行所有 Python 测试
pytest tests/

# 运行覆盖率测试
pytest tests/ --cov=services/ --cov-report=html

# 运行前端测试
cd web && npm test

# 运行前端测试（带 UI）
cd web && npm run test:ui
```

### 拉取请求流程

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 进行修改并添加测试
4. 确保所有测试通过 (`pytest tests/ && cd web && npm test`)
5. 提交更改 (`git commit -m 'Add amazing feature'`)
6. 推送到分支 (`git push origin feature/amazing-feature`)
7. 创建 Pull Request

## 路线图

- [ ] 增强向量搜索（混合检索）
- [ ] Kafka 实时数据流集成
- [ ] 多模型编排和路由
- [ ] 高级 Agent 框架（工具学习）
- [ ] 性能优化和基准测试
- [ ] 增强安全特性（审计日志、加密）
- [ ] 移动端响应式 UI 改进
- [ ] 插件系统支持扩展

## 开源许可

本项目采用 Apache License 2.0 开源协议 - 详见 [LICENSE](LICENSE) 文件。

```
Copyright 2024-2025 ONE-DATA-STUDIO Contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

## 致谢

本项目建立在以下优秀开源项目的基础之上：

- [Alldata](https://github.com/Computing-Data/Alldata) - 数据治理平台
- [Cube Studio](https://github.com/tencentmusic/cube-studio) - 云原生 MLOps 平台
- [Bisheng](https://github.com/dataelement/bisheng) - 大模型应用开发平台

## 社区

- **问题反馈**: [GitHub Issues](https://github.com/one-data-studio/one-data-studio/issues)
- **讨论交流**: [GitHub Discussions](https://github.com/one-data-studio/one-data-studio/discussions)

---

<div align="center">

**由 ONE-DATA-STUDIO 社区用心构建**

如果这个项目对您有帮助，欢迎给我们一个 Star！

</div>
