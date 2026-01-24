# ONE-DATA-STUDIO

<div align="center">

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18.3-blue.svg)](https://reactjs.org/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.27%2B-326ce5.svg)](https://kubernetes.io/)

**企业级 DataOps + MLOps + LLMOps 融合平台**

[功能特性](#功能特性) • [快速开始](#快速开始) • [架构设计](#架构设计) • [文档](#文档) • [贡献指南](#贡献指南) • [English](README.md)

</div>

---

## 项目简介

**ONE-DATA-STUDIO** 是一个开源的企业级平台，融合了三个关键的 AI 基础设施层：

- **Alldata** - 数据治理与开发平台（DataOps 层）
- **Cube Studio** - 云原生 MLOps 平台（模型/计算层）
- **Bisheng** - 大模型应用开发平台（LLMOps 层）

该平台打通了从**原始数据治理**到**模型训练部署**，再到**生成式AI应用构建**的完整价值链。

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
- 面向 RAG 应用的向量存储

### 机器学习运营 (MLOps)

- Jupyter Notebook 开发环境
- 基于 Ray 的分布式模型训练
- 模型注册和版本管理
- 基于 vLLM 的模型服务（OpenAI 兼容 API）

### 大模型运营 (LLMOps)

- RAG（检索增强生成）流水线
- Agent 编排和工作流构建器
- Prompt 管理和模板
- 知识库管理

## 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    L4 应用编排层 (Bisheng)                       │
│                    RAG 流水线 | Agent 编排                        │
└─────────────────────────────────────────────────────────────────┘
                              ↕ OpenAI API / 元数据
┌─────────────────────────────────────────────────────────────────┐
│                   L3 算法引擎层 (Cube Studio)                    │
│              Notebook | 分布式训练 | 模型服务化                   │
└─────────────────────────────────────────────────────────────────┘
                              ↕ 挂载数据卷
┌─────────────────────────────────────────────────────────────────┐
│                    L2 数据底座层 (Alldata)                       │
│          数据集成 | ETL | 数据治理 | 特征存储 | 向量存储           │
└─────────────────────────────────────────────────────────────────┘
                              ↕ 存储协议
┌─────────────────────────────────────────────────────────────────┐
│                    L1 基础设施层 (Kubernetes)                    │
│              CPU/GPU 资源池 | 存储 | 网络 | 监控                  │
└─────────────────────────────────────────────────────────────────┘
```

## 核心集成点

| 集成方向 | 描述 | 完成度 |
|----------|------|--------|
| **Alldata → Cube** | 统一存储协议与数据集版本化 | 90% |
| **Cube → Bisheng** | OpenAI 兼容的模型即服务 API | 85% |
| **Alldata → Bisheng** | 基于元数据的 Text-to-SQL | 75% |

## 技术栈

### 前端

- **React 18.3** + TypeScript
- **Ant Design 5.14** UI 组件库
- **React Router 6.22** 路由管理
- **React Query 5.24** 服务端状态管理
- **Zustand 4.5** 客户端状态管理
- **Vite 5.1** 构建工具

### 后端服务

- **Python 3.10+** (FastAPI/Flask)
- **MySQL 8.0** 持久化存储
- **Redis 7.0** 缓存
- **MinIO** S3 兼容对象存储
- **Milvus 2.3** 向量数据库

### 基础设施

- **Kubernetes 1.27+** 容器编排
- **Helm 3.13+** 包管理
- **Prometheus + Grafana** 监控
- **Keycloak** 认证服务

## 快速开始

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- kubectl 1.25+ (Kubernetes 部署需要)
- Helm 3.x (Helm 部署需要)

### 方式一：Docker Compose（推荐开发环境）

```bash
# 克隆仓库
git clone https://github.com/one-data-studio/one-data-studio.git
cd one-data-studio

# 启动所有服务
docker-compose -f deploy/local/docker-compose.yml up -d

# 查看服务状态
docker-compose -f deploy/local/docker-compose.yml ps
```

### 方式二：Kubernetes（推荐生产环境）

```bash
# 创建 Kind 集群
make kind-cluster

# 部署所有服务
make install

# 查看状态
make status

# 转发端口访问服务
make forward
```

### 访问平台

| 服务 | 地址 | 凭据 |
|------|------|------|
| Web UI | <http://localhost:3000> | 开发模式：无需认证 |
| Alldata API | <http://localhost:8001> | - |
| Bisheng API | <http://localhost:8000> | - |
| OpenAI Proxy | <http://localhost:8003> | - |
| MinIO 控制台 | <http://localhost:9001> | 见 `.env` 配置 |
| Prometheus | <http://localhost:9090> | - |
| Grafana | <http://localhost:3001> | admin/admin |

## 项目结构

```
one-data-studio/
├── services/               # 后端服务
│   ├── alldata-api/        # 数据治理 API (Flask)
│   ├── bisheng-api/        # 应用编排 API (Flask)
│   ├── openai-proxy/       # OpenAI 兼容代理 (FastAPI)
│   ├── cube-api/           # 模型服务 API (FastAPI)
│   └── shared/             # 共享模块 (认证、存储)
├── web/                    # 前端应用 (React + TypeScript)
├── deploy/                 # 部署配置
│   ├── local/              # Docker Compose 文件
│   ├── kubernetes/         # Kubernetes 清单文件
│   ├── helm/               # Helm Charts
│   ├── dockerfiles/        # Docker 构建文件
│   └── scripts/            # 部署脚本
├── scripts/                # 运维脚本
├── tests/                  # 测试文件
├── docs/                   # 文档
└── examples/               # 使用示例
```

## 应用场景

### 企业知识中台

统一管理企业文档知识，提供智能问答能力。

### ChatBI

用自然语言查询数据库，自动生成报表。

### 工业质检

传感器数据实时分析，实现预测性维护。

## 文档

- [快速开始指南](QUICKSTART.md)
- [架构概览](docs/01-architecture/platform-overview.md)
- [API 规范](docs/02-integration/api-specifications.md)
- [开发指南](docs/05-development/poc-playbook.md)
- [用户手册](docs/07-user-guide/getting-started.md)

## 贡献指南

我们欢迎社区贡献！

### 开发环境搭建

```bash
# 后端开发
cd services/bisheng-api
pip install -r requirements.txt
python app.py

# 前端开发
cd web
npm install
npm run dev
```

### 代码规范

- **Python**：遵循 PEP 8，使用 `logging` 而非 `print()`
- **TypeScript**：遵循 ESLint 规则，避免 `console.log`（仅保留 `console.error`）
- **提交信息**：使用清晰的提交说明

### 测试

```bash
# 运行所有测试
pytest tests/

# 运行覆盖率测试
pytest tests/ --cov=services/ --cov-report=html

# 运行前端测试
cd web && npm test
```

### 拉取请求

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 路线图

- [ ] 增强向量搜索能力
- [ ] Kafka 实时数据流
- [ ] 多模型编排
- [ ] 高级 Agent 框架
- [ ] 性能优化和基准测试
- [ ] 增强安全特性

## 开源许可

本项目采用 Apache License 2.0 开源协议 - 详见 [LICENSE](LICENSE) 文件。

```
Copyright 2024 ONE-DATA-STUDIO Contributors

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

- [Alldata](https://github.com/Computing-Data/Alldata) - 数据治理平台
- [Cube Studio](https://github.com/tencentmusic/cube-studio) - 云原生 MLOps 平台
- [Bisheng](https://github.com/Tencent/Bisheng) - 大模型应用开发平台

## 联系我们

- **官网**: <https://one-data-studio.io>
- **文档**: <https://docs.one-data-studio.io>
- **问题反馈**: <https://github.com/one-data-studio/one-data-studio/issues>

---

<div align="center">

**由 ONE-DATA-STUDIO 社区用 ❤️ 构建**

</div>
