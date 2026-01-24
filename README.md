# ONE-DATA-STUDIO

<div align="center">

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18.3-blue.svg)](https://reactjs.org/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.27%2B-326ce5.svg)](https://kubernetes.io/)

**Enterprise-Grade DataOps + MLOps + LLMOps Converged Platform**

[Features](#features) • [Quick Start](#quick-start) • [Architecture](#architecture) • [Documentation](#documentation) • [Contributing](#contributing) • [简体中文](README_ZH.md)

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

- Data integration and EEL pipelines
- Metadata management and data governance
- Feature store for ML models
- Vector storage for RAG applications

### Machine Learning Operations (MLOps)

- Jupyter Notebook development environment
- Distributed model training with Ray
- Model registry and versioning
- Model serving with vLLM (OpenAI-compatible API)

### LLM Operations (LLMOps)

- RAG (Retrieval-Augmented Generation) pipelines
- Agent orchestration and workflow builder
- Prompt management and templates
- Knowledge base management

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  L4 Application Layer (Bisheng)                  │
│                   RAG Pipeline | Agent Orchestration              │
└─────────────────────────────────────────────────────────────────┘
                              ↕ OpenAI API / Metadata
┌─────────────────────────────────────────────────────────────────┐
│                 L3 Algorithm Engine Layer (Cube Studio)          │
│              Notebook | Distributed Training | Model Serving     │
└─────────────────────────────────────────────────────────────────┘
                              ↕ Mount Data Volumes
┌─────────────────────────────────────────────────────────────────┐
│                   L2 Data Foundation Layer (Alldata)             │
│         Data Integration | ETL | Governance | Vector Store       │
└─────────────────────────────────────────────────────────────────┘
                              ↕ Storage Protocol
┌─────────────────────────────────────────────────────────────────┐
│                   L1 Infrastructure Layer (Kubernetes)           │
│              CPU/GPU Pool | Storage | Network | Monitoring       │
└─────────────────────────────────────────────────────────────────┘
```

## Key Integrations

| Integration | Description | Status |
|-------------|-------------|--------|
| **Alldata → Cube** | Unified storage protocol with dataset versioning | 90% |
| **Cube → Bisheng** | OpenAI-compatible model serving API | 85% |
| **Alldata → Bisheng** | Metadata-based Text-to-SQL | 75% |

## Tech Stack

### Frontend

- **React 18.3** with TypeScript
- **Ant Design 5.14** UI components
- **React Router 6.22** for navigation
- **React Query 5.24** for server state
- **Zustand 4.5** for client state
- **Vite 5.1** for building

### Backend Services

- **Python 3.10+** with FastAPI/Flask
- **MySQL 8.0** for persistent storage
- **Redis 7.0** for caching
- **MinIO** for S3-compatible object storage
- **Milvus 2.3** for vector database

### Infrastructure

- **Kubernetes 1.27+** for orchestration
- **Helm 3.13+** for package management
- **Prometheus + Grafana** for monitoring
- **Keycloak** for authentication

## Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- kubectl 1.25+ (for Kubernetes deployment)
- Helm 3.x (for Helm deployment)

### Option 1: Docker Compose (Recommended for Development)

```bash
# Clone the repository
git clone https://github.com/one-data-studio/one-data-studio.git
cd one-data-studio

# Start all services
docker-compose -f deploy/local/docker-compose.yml up -d

# Check service status
docker-compose -f deploy/local/docker-compose.yml ps
```

### Option 2: Kubernetes (Recommended for Production)

```bash
# Create Kind cluster
make kind-cluster

# Deploy all services
make install

# Check status
make status

# Forward ports to access services
make forward
```

### Access the Platform

| Service | URL | Credentials |
|---------|-----|-------------|
| Web UI | <http://localhost:3000> | Development mode: no auth |
| Alldata API | <http://localhost:8001> | - |
| Bisheng API | <http://localhost:8000> | - |
| OpenAI Proxy | <http://localhost:8003> | - |
| MinIO Console | <http://localhost:9001> | See `.env` |
| Prometheus | <http://localhost:9090> | - |
| Grafana | <http://localhost:3001> | admin/admin |

## Project Structure

```
one-data-studio/
├── services/               # Backend services
│   ├── alldata-api/        # Data governance API (Flask)
│   ├── bisheng-api/        # Application orchestration API (Flask)
│   ├── openai-proxy/       # OpenAI-compatible proxy (FastAPI)
│   ├── cube-api/           # Model service API (FastAPI)
│   └── shared/             # Shared modules (auth, storage)
├── web/                    # Frontend application (React + TypeScript)
├── deploy/                 # Deployment configurations
│   ├── local/              # Docker Compose files
│   ├── kubernetes/         # Kubernetes manifests
│   ├── helm/               # Helm charts
│   ├── dockerfiles/        # Docker build files
│   └── scripts/            # Deployment scripts
├── scripts/                # Operations scripts
├── tests/                  # Test files
├── docs/                   # Documentation
└── examples/               # Usage examples
```

## Use Cases

### Enterprise Knowledge Center

Unified management of enterprise document knowledge with intelligent Q&A capabilities.

### ChatBI

Query databases using natural language with automatic report generation.

### Industrial Quality Inspection

Real-time sensor data analysis with predictive maintenance.

## Documentation

- [Quick Start Guide](QUICKSTART.md)
- [Architecture Overview](docs/01-architecture/platform-overview.md)
- [API Specifications](docs/02-integration/api-specifications.md)
- [Development Guide](docs/05-development/poc-playbook.md)
- [User Guide](docs/07-user-guide/getting-started.md)

## Contributing

We welcome contributions from the community!

### Development Setup

```bash
# Backend development
cd services/bisheng-api
pip install -r requirements.txt
python app.py

# Frontend development
cd web
npm install
npm run dev
```

### Code Style

- **Python**: Follow PEP 8, use `logging` instead of `print()`
- **TypeScript**: Follow ESLint rules, avoid `console.log` (use `console.error` only)
- **Commits**: Use clear commit messages

### Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=services/ --cov-report=html

# Run frontend tests
cd web && npm test
```

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Roadmap

- [ ] Enhanced vector search capabilities
- [ ] Real-time data streaming with Kafka
- [ ] Multi-model orchestration
- [ ] Advanced Agent framework
- [ ] Performance optimization and benchmarking
- [ ] Enhanced security features

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

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

## Acknowledgments

- [Alldata](https://github.com/Computing-Data/Alldata) - Data governance platform
- [Cube Studio](https://github.com/tencentmusic/cube-studio) - Cloud-native MLOps platform
- [Bisheng](https://github.com/Tencent/Bisheng) - LLM application development platform

## Contact

- **Website**: <https://one-data-studio.io>
- **Documentation**: <https://docs.one-data-studio.io>
- **Issues**: <https://github.com/one-data-studio/one-data-studio/issues>

---

<div align="center">

**Built with ❤️ by the ONE-DATA-STUDIO Community**

</div>
