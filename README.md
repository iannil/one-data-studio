# ONE-DATA-STUDIO

<div align="center">

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18.3-blue.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.4-blue.svg)](https://www.typescriptlang.org/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.27%2B-326ce5.svg)](https://kubernetes.io/)
[![Docker](https://img.shields.io/badge/Docker-20.10%2B-2496ED.svg)](https://www.docker.com/)

**Enterprise-Grade DataOps + MLOps + LLMOps Converged Platform**

[Features](#features) | [Quick Start](#quick-start) | [Architecture](#architecture) | [Documentation](#documentation) | [Contributing](#contributing) | [简体中文](README_ZH.md)

</div>

---

## Overview

**ONE-DATA-STUDIO** is an open-source enterprise platform that converges three critical AI infrastructure layers:

- **Alldata** - Data governance and development platform (DataOps layer)
- **Cube Studio** - Cloud-native MLOps platform (Model/Compute layer)
- **Bisheng** - LLM application development platform (LLMOps layer)

This platform bridges the complete value chain from **raw data governance** to **model training/deployment**, and finally to **generative AI application construction**.

## Why ONE-DATA-STUDIO?

### Break Down Data & AI Silos

Data teams (using Alldata) and algorithm teams (using Cube Studio) often work in isolation. Our integration enables a **seamless Feature Store** where algorithm engineers can directly access high-quality, governed data without redundant cleaning efforts.

### Unified Structured & Unstructured Data

Alldata excels at structured data while Bisheng handles unstructured documents. Combined, enterprises can build **"ChatBI"**—querying both document knowledge bases and database sales reports using natural language (Text-to-SQL).

### Complete Private LLM Deployment Loop

Many enterprises want to use Bisheng for applications but lack model fine-tuning capabilities, or have models trained via Cube Studio but lack application-building tools.

**All three combined = Private Data (Alldata) + Private Compute/Models (Cube Studio) + Private Applications (Bisheng)**. This constitutes the most secure enterprise AGI solution.

### Full Lifecycle Governance

From data lineage (Alldata) to model lineage (Cube Studio) to application logs, the entire chain is traceable. If an AI answer is incorrect, you can trace whether it's a Prompt issue, model overfitting, or dirty source data.

## Features

### Data Operations (DataOps)

- Data integration and ETL pipelines
- Metadata management and data governance
- Feature store for ML models
- Vector storage for RAG applications (Milvus)

### Machine Learning Operations (MLOps)

- Jupyter Notebook development environment
- Distributed model training with Ray
- Model registry and versioning
- Model serving with vLLM (OpenAI-compatible API)

### LLM Operations (LLMOps)

- RAG (Retrieval-Augmented Generation) pipelines
- Agent orchestration and visual workflow builder
- Prompt management and templates
- Knowledge base management

### Platform Administration

- Unified user management with Keycloak SSO
- Role-based access control (RBAC)
- Multi-tenant support
- Comprehensive audit logging

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 L4 Application Layer (Bisheng)                  │
│             RAG Pipeline | Agent Orchestration | Workflow       │
└─────────────────────────────────────────────────────────────────┘
                              ↕ OpenAI API / Metadata
┌─────────────────────────────────────────────────────────────────┐
│                L3 Algorithm Engine Layer (Cube Studio)          │
│             Notebook | Distributed Training | Model Serving     │
└─────────────────────────────────────────────────────────────────┘
                              ↕ Mount Data Volumes
┌─────────────────────────────────────────────────────────────────┐
│                  L2 Data Foundation Layer (Alldata)             │
│        Data Integration | ETL | Governance | Vector Store       │
└─────────────────────────────────────────────────────────────────┘
                              ↕ Storage Protocol
┌─────────────────────────────────────────────────────────────────┐
│                  L1 Infrastructure Layer (Kubernetes)           │
│             CPU/GPU Pool | Storage | Network | Monitoring       │
└─────────────────────────────────────────────────────────────────┘
```

## Key Integrations

| Integration | Description | Status |
| ------------- | ------------- | -------- |
| **Alldata → Cube** | Unified storage protocol with dataset versioning | 90% |
| **Cube → Bisheng** | OpenAI-compatible model serving API | 85% |
| **Alldata → Bisheng** | Metadata-based Text-to-SQL | 75% |

## Tech Stack

### Frontend

| Technology | Version | Purpose |
| ------------ | --------- | --------- |
| React | 18.3 | UI Framework |
| TypeScript | 5.4 | Type Safety |
| Ant Design | 5.14 | UI Components |
| React Router | 6.22 | Navigation |
| React Query | 5.24 | Server State |
| Zustand | 4.5 | Client State |
| ReactFlow | 11.10 | Workflow Canvas |
| Vite | 5.1 | Build Tool |
| Vitest | 1.3 | Testing |

### Backend Services

| Technology | Version | Purpose |
| ------------ | --------- | --------- |
| Python | 3.10+ | Runtime |
| Flask | - | Web Framework (Alldata, Bisheng) |
| FastAPI | - | Web Framework (OpenAI Proxy, Cube) |
| MySQL | 8.0 | Persistent Storage |
| Redis | 7.0 | Caching & Session |
| MinIO | Latest | S3-compatible Object Storage |
| Milvus | 2.3 | Vector Database |
| OpenMetadata | 1.3 | Metadata Governance Platform |
| Elasticsearch | 8.10 | Search Engine (OpenMetadata) |

### Infrastructure

| Technology | Version | Purpose |
| ------------ | --------- | --------- |
| Kubernetes | 1.27+ | Container Orchestration |
| Docker | 20.10+ | Containerization |
| Helm | 3.13+ | Package Management |
| Keycloak | 23.0 | Identity & Access Management |
| Prometheus | - | Metrics Collection |
| Grafana | - | Monitoring Dashboard |

## Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Node.js 18+ (for frontend development)
- Python 3.10+ (for backend development)
- kubectl 1.25+ (for Kubernetes deployment)
- Helm 3.x (for Helm deployment)

### Option 1: Docker Compose (Recommended for Development)

```bash
# Clone the repository
git clone https://github.com/iannil/one-data-studio.git
cd one-data-studio

# Copy environment configuration
cp .env.example .env
# Edit .env and set required passwords (MYSQL_PASSWORD, REDIS_PASSWORD, etc.)

# Start all services
docker-compose -f deploy/local/docker-compose.yml up -d

# Check service status
docker-compose -f deploy/local/docker-compose.yml ps
```

Or use the Makefile shortcuts:

```bash
make dev        # Start development environment
make dev-status # Check service status
make dev-logs   # View service logs
make dev-stop   # Stop all services
```

### Option 2: Kubernetes (Recommended for Production)

```bash
# Create Kind cluster (for local testing)
make kind-cluster

# Deploy all services
make install

# Check status
make status

# Forward ports to access services
make forward
```

### Access the Platform

| Service | URL | Description |
| --------- | ----- | ------------- |
| Web UI | <http://localhost:3000> | Main application interface |
| Bisheng API | <http://localhost:8000> | Application orchestration API |
| Alldata API | <http://localhost:8001> | Data governance API |
| Cube API | <http://localhost:8002> | Model service API |
| OpenAI Proxy | <http://localhost:8003> | OpenAI-compatible proxy |
| Admin API | <http://localhost:8004> | Platform administration API |
| OpenMetadata | <http://localhost:8585> | Metadata governance platform |
| Keycloak | <http://localhost:8080> | Identity management |
| MinIO Console | <http://localhost:9001> | Object storage console |
| Prometheus | <http://localhost:9090> | Metrics dashboard |
| Grafana | <http://localhost:3001> | Monitoring (admin/admin) |

## Project Structure

```
one-data-studio/
├── services/                 # Backend services
│   ├── alldata-api/          # Data governance API (Flask)
│   ├── bisheng-api/          # Application orchestration API (Flask)
│   ├── cube-api/             # Model service API (FastAPI)
│   ├── openai-proxy/         # OpenAI-compatible proxy (FastAPI)
│   ├── admin-api/            # Platform administration API (Flask)
│   └── shared/               # Shared modules (auth, storage, utils)
├── web/                      # Frontend application (React + TypeScript)
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── pages/            # Page components
│   │   ├── services/         # API clients
│   │   ├── stores/           # Zustand state stores
│   │   └── locales/          # i18n translations
│   └── public/               # Static assets
├── deploy/                   # Deployment configurations
│   ├── local/                # Docker Compose files
│   ├── kubernetes/           # Kubernetes manifests
│   ├── helm/                 # Helm charts
│   ├── dockerfiles/          # Docker build files
│   └── scripts/              # Deployment scripts
├── scripts/                  # Development & operations scripts
│   └── dev/                  # Development environment scripts
├── tests/                    # Test files
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── e2e/                  # End-to-end tests
├── docs/                     # Documentation
│   ├── 01-architecture/      # Architecture documentation
│   ├── 02-integration/       # Integration guides
│   ├── 05-development/       # Development guides
│   ├── 06-operations/        # Operations guides
│   └── 07-user-guide/        # User documentation
└── examples/                 # Usage examples
    ├── langchain/            # LangChain integration examples
    ├── python/               # Python SDK examples
    └── workflows/            # Workflow definition examples
```

## Use Cases

### Enterprise Knowledge Center

Unified management of enterprise document knowledge with intelligent Q&A capabilities. Combine internal documents, policies, and procedures into a searchable knowledge base with natural language queries.

### ChatBI (Business Intelligence)

Query databases using natural language with automatic report generation. Connect to your data warehouse and ask questions like "Show me last quarter's sales by region" - the system generates SQL and visualizes results.

### Industrial Quality Inspection

Real-time sensor data analysis with predictive maintenance. Process streaming IoT data, train anomaly detection models, and deploy them for real-time monitoring.

### Custom AI Applications

Build sophisticated AI applications using the visual workflow builder. Combine RAG, agents, and tools to create customer service bots, document processors, or research assistants.

## Documentation

- [Architecture Overview](docs/01-architecture/platform-overview.md)
- [Four-Layer Stack](docs/01-architecture/four-layer-stack.md)
- [Integration Guide](docs/02-integration/integration-overview.md)
- [API Specifications](docs/02-integration/api-specifications.md)
- [Development Guide](docs/05-development/poc-playbook.md)
- [Operations Guide](docs/06-operations/operations-guide.md)
- [User Guide](docs/07-user-guide/getting-started.md)

## Contributing

We welcome contributions from the community!

### Development Setup

```bash
# Backend development
cd services/bisheng-api
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py

# Frontend development
cd web
npm install
npm run dev
```

### Code Style

- **Python**: Follow PEP 8, use `logging` instead of `print()`
- **TypeScript**: Follow ESLint rules, avoid `console.log` (use `console.error` only for errors)
- **Commits**: Use clear, descriptive commit messages

### Testing

```bash
# Run all Python tests
pytest tests/

# Run with coverage
pytest tests/ --cov=services/ --cov-report=html

# Run frontend tests
cd web && npm test

# Run frontend tests with UI
cd web && npm run test:ui
```

### Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes and add tests
4. Ensure all tests pass (`pytest tests/ && cd web && npm test`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Roadmap

- [ ] Enhanced vector search with hybrid retrieval
- [ ] Real-time data streaming with Kafka integration
- [ ] Multi-model orchestration and routing
- [ ] Advanced Agent framework with tool learning
- [ ] Performance optimization and benchmarking
- [ ] Enhanced security features (audit logging, encryption)
- [ ] Mobile-responsive UI improvements
- [ ] Plugin system for extensibility

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

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

## Acknowledgments

This project builds upon the shoulders of giants:

- [OpenMetadata](https://open-metadata.org/) - Open source metadata platform (optional integration)
- [Cube Studio](https://github.com/tencentmusic/cube-studio) - Cloud-native MLOps platform
- [Bisheng](https://github.com/dataelement/bisheng) - LLM application development platform

## Community

- **Issues**: [GitHub Issues](https://github.com/iannil/one-data-studio/issues)
- **Discussions**: [GitHub Discussions](https://github.com/iannil/one-data-studio/discussions)

---

<div align="center">

**Built with care by the ONE-DATA-STUDIO Community**

If you find this project useful, please consider giving it a star!

</div>
