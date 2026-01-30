# ONE-DATA-STUDIO

<div align="center">

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18.3-blue.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.4-blue.svg)](https://www.typescriptlang.org/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.27%2B-326ce5.svg)](https://kubernetes.io/)
[![Docker](https://img.shields.io/badge/Docker-20.10%2B-2496ED.svg)](https://www.docker.com/)

Enterprise-Grade DataOps + MLOps + LLMOps Converged Platform

*From Raw Data to Intelligent Applications — All in One Platform*

[Features](#-features) | [Quick Start](#-quick-start) | [Architecture](#-architecture) | [Use Cases](#-use-cases) | [Comparison](#-comparison-with-alternatives) | [Documentation](#-documentation) | [简体中文](README_ZH.md)

</div>

---

## What is ONE-DATA-STUDIO?

ONE-DATA-STUDIO is an open-source enterprise platform that uniquely converges three critical AI infrastructure layers into a unified system:

| Layer | Name | Description |
| ------- | ------ | ------------- |
| Data | DataOps Platform | Data integration, ETL, governance, feature store, and vector storage |
| Model | MLOps Platform | Jupyter notebooks, distributed training, model registry, and serving |
| Agent | LLMOps Platform | RAG pipelines, agent orchestration, workflow builder, and prompt management |

Unlike traditional platforms that treat these as separate silos, ONE-DATA-STUDIO creates seamless integration points between layers, enabling enterprises to build end-to-end AI solutions from raw data to production applications.

### Key Value Propositions

1. Complete Value Chain: Raw data → Governed datasets → Trained models → Deployed applications
2. Unified Governance: Single pane of glass for data lineage, model lineage, and application logs
3. Private & Secure: Deploy entirely on-premises with your own data, compute, and models
4. Production-Ready: Battle-tested with enterprise-grade security, monitoring, and scalability

---

## Features

### Data Layer (DataOps)

| Feature | Description | Implementation |
| --------- | ------------- | ---------------- |
| Data Integration | Connect to 50+ data sources (databases, APIs, files) | Flask-based connectors with async I/O |
| ETL Pipelines | Visual pipeline builder with Flink/Spark execution | Declarative DAG definitions |
| Metadata Management | Automatic schema discovery and cataloging | OpenMetadata integration |
| Data Quality | Rule-based validation and anomaly detection | Custom quality engine |
| Data Lineage | Track data flow from source to consumption | Column-level lineage tracking |
| Feature Store | Unified feature management for ML models | MinIO + versioned datasets |
| Vector Storage | High-performance vector database for RAG | Milvus 2.3 integration |

### Model Layer (MLOps)

| Feature | Description | Implementation |
| --------- | ------------- | ---------------- |
| Notebook Environment | JupyterHub with GPU support | K8s-native deployment |
| Distributed Training | Multi-GPU, multi-node training | Ray integration |
| Model Registry | Version control for models | MLflow-compatible API |
| Model Serving | High-throughput inference | vLLM with OpenAI-compatible API |
| Experiment Tracking | Log metrics, parameters, artifacts | Built-in tracking system |
| A/B Deployment | Gradual rollout with traffic splitting | Istio service mesh |

### Agent Layer (LLMOps)

| Feature | Description | Implementation |
| --------- | ------------- | ---------------- |
| RAG Pipeline | End-to-end retrieval-augmented generation | LangChain + Milvus |
| Agent Orchestration | Multi-agent systems with tool use | Custom agent framework |
| Visual Workflow | Drag-and-drop workflow builder | ReactFlow canvas |
| Prompt Management | Template library with versioning | A/B testing support |
| Knowledge Base | Document ingestion and chunking | PDF, DOCX, Markdown support |
| Text-to-SQL | Natural language database queries | Metadata-enhanced prompts |
| Token Tracking | Usage monitoring and cost control | Per-request token counting |

### Platform Administration

| Feature | Description | Implementation |
| --------- | ------------- | ---------------- |
| Identity Management | SSO with OIDC/SAML support | Keycloak 23.0 |
| Access Control | Fine-grained RBAC | Role-based permissions |
| Multi-tenancy | Isolated workspaces | Namespace-level isolation |
| Audit Logging | Comprehensive activity tracking | Searchable audit trail |
| Observability | Metrics, traces, logs | Prometheus + Grafana + Jaeger |

---

## Architecture

### Four-Layer Architecture

```
┌───────────────────────────────────────────────────────────────────────────┐
│                     L4 APPLICATION LAYER (Agent)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │ RAG Pipeline│  │Agent System │  │ Workflow    │  │ Text-to-SQL │       │
│  │ • Embedding │  │ • Planning  │  │ • ReactFlow │  │ • Schema    │       │
│  │ • Retrieval │  │ • Tool Use  │  │ • Nodes     │  │ • Query Gen │       │
│  │ • Generation│  │ • Memory    │  │ • Execution │  │ • Results   │       │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘       │
└───────────────────────────────────────────────────────────────────────────┘
                        ↕ OpenAI-Compatible API / Metadata Injection
┌───────────────────────────────────────────────────────────────────────────┐
│                    L3 ALGORITHM ENGINE LAYER (Model)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │ Notebook    │  │ Distributed │  │ Model       │  │ Inference   │       │
│  │ • Jupyter   │  │ Training    │  │ Registry    │  │ • vLLM      │       │
│  │ • GPU       │  │ • Ray       │  │ • Versions  │  │ • Batching  │       │
│  │ • Kernels   │  │ • Multi-GPU │  │ • Artifacts │  │ • Scaling   │       │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘       │
└───────────────────────────────────────────────────────────────────────────┘
                        ↕ Dataset Mounting / Feature Retrieval
┌───────────────────────────────────────────────────────────────────────────┐
│                    L2 DATA FOUNDATION LAYER (Data)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │ Integration │  │ ETL Engine  │  │ Governance  │  │ Storage     │       │
│  │ • Connectors│  │ • Flink     │  │ • Metadata  │  │ • MinIO     │       │
│  │ • CDC       │  │ • Spark     │  │ • Quality   │  │ • Milvus    │       │
│  │ • Streaming │  │ • Transform │  │ • Lineage   │  │ • Redis     │       │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘       │
└───────────────────────────────────────────────────────────────────────────┘
                        ↕ Storage Protocol / Resource Scheduling
┌───────────────────────────────────────────────────────────────────────────┐
│                    L1 INFRASTRUCTURE LAYER (Kubernetes)                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │ Compute     │  │ Storage     │  │ Network     │  │ Observability│      │
│  │ • CPU Pool  │  │ • PVC       │  │ • Istio     │  │ • Prometheus│       │
│  │ • GPU Pool  │  │ • MinIO     │  │ • Ingress   │  │ • Grafana   │       │
│  │ • Auto-scale│  │ • HDFS      │  │ • DNS       │  │ • Jaeger    │       │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘       │
└───────────────────────────────────────────────────────────────────────────┘
```

### Core Services

| Service | Port | Framework | Description |
| --------- | ------ | ----------- | ------------- |
| web | 3000 | React + Vite | Main application frontend |
| agent-api | 8000 | Flask | LLMOps orchestration service |
| data-api | 8001 | Flask | Data governance service |
| model-api | 8002 | FastAPI | MLOps management service |
| openai-proxy | 8003 | FastAPI | OpenAI-compatible proxy |
| admin-api | 8004 | Flask | Platform administration |
| ocr-service | 8005 | FastAPI | Document recognition |
| behavior-service | 8006 | Flask | User analytics |

### Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Integration Points                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────┐     Data → Model (90%)      ┌──────────┐                  │
│  │   Data   │ ─────────────────────────▶  │  Model   │                  │
│  │  Layer   │   • Unified storage (MinIO) │  Layer   │                  │
│  │          │   • Dataset versioning      │          │                  │
│  │          │   • Auto dataset registry   │          │                  │
│  └──────────┘                             └──────────┘                  │
│       │                                        │                        │
│       │                                        │                        │
│       │  Data → Agent (75%)    Model → Agent (85%)                      │
│       │  • Metadata injection  • OpenAI API                             │
│       │  • Text-to-SQL         • vLLM serving                           │
│       │  • Schema context      • Model routing                          │
│       ▼                                        ▼                        │
│                        ┌──────────┐                                     │
│                        │  Agent   │                                     │
│                        │  Layer   │                                     │
│                        └──────────┘                                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

| Requirement | Version | Notes |
| ------------ | --------- | ------- |
| Docker | 20.10+ | Required for all deployment options |
| Docker Compose | 2.0+ | For local development |
| Node.js | 18+ | For frontend development |
| Python | 3.10+ | For backend development |
| kubectl | 1.25+ | For Kubernetes deployment |
| Helm | 3.x | For Helm deployment |

### Option 1: Docker Compose (Development)

```bash
# Clone the repository
git clone https://github.com/iannil/one-data-studio.git
cd one-data-studio

# Configure environment
cp .env.example .env
# Edit .env to set passwords: MYSQL_PASSWORD, REDIS_PASSWORD, MINIO_SECRET_KEY, etc.

# Start all services
docker-compose -f deploy/local/docker-compose.yml up -d

# Check status
docker-compose -f deploy/local/docker-compose.yml ps

# View logs
docker-compose -f deploy/local/docker-compose.yml logs -f
```

Using Makefile:

```bash
make dev          # Start development environment
make dev-status   # Check service status
make dev-logs     # View service logs
make dev-stop     # Stop all services
make dev-clean    # Clean up volumes
```

### Option 2: Kubernetes (Production)

```bash
# Create a local Kind cluster (for testing)
make kind-cluster

# Install with Kustomize
kubectl apply -k deploy/kubernetes/overlays/production

# Or install with Helm
helm install one-data deploy/helm/charts/one-data \
  --namespace one-data \
  --create-namespace \
  --values deploy/helm/charts/one-data/values-production.yaml

# Check status
kubectl get pods -n one-data

# Forward ports for local access
make forward
```

### Access the Platform

| Service | URL | Credentials |
| --------- | ----- | ------------- |
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

## Use Cases

### 1. Enterprise Knowledge Center

Scenario: Enterprises have scattered documents across departments — policies, procedures, technical docs, FAQs. Employees struggle to find information quickly.

Solution with ONE-DATA-STUDIO:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Document   │    │   Data      │    │   Agent     │    │   Chat      │
│  Sources    │───▶│   Layer     │───▶│   Layer     │───▶│   Interface │
│             │    │             │    │             │    │             │
│ • PDF       │    │ • Chunking  │    │ • RAG       │    │ • Q&A       │
│ • DOCX      │    │ • Embedding │    │ • Reranking │    │ • Citations │
│ • Markdown  │    │ • Milvus    │    │ • Generation│    │ • History   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

Benefits:

- 70% reduction in time-to-answer for employee queries
- Automatic document updates with versioning
- Source citations for every answer

### 2. ChatBI (Business Intelligence)

Scenario: Business users need data insights but can't write SQL. They depend on data analysts for every query, creating bottlenecks.

Solution with ONE-DATA-STUDIO:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Natural    │    │   Data      │    │   Agent     │    │   Visual    │
│  Language   │───▶│   Layer     │───▶│   Layer     │───▶│   Results   │
│   Query     │    │             │    │             │    │             │
│             │    │ • Metadata  │    │ • Text2SQL  │    │ • Charts    │
│ "Show Q4    │    │ • Schema    │    │ • Query     │    │ • Tables    │
│  sales by   │    │ • Relations │    │ • Validate  │    │ • Export    │
│  region"    │    │ • Context   │    │ • Execute   │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

Benefits:

- Self-service analytics without SQL knowledge
- 80% reduction in data analyst workload for ad-hoc queries
- Metadata-enhanced accuracy for complex queries

### 3. Private LLM Deployment

Scenario: Enterprises want to use LLMs but have strict data privacy requirements. Cloud APIs are not an option.

Solution with ONE-DATA-STUDIO:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Private    │    │   Model     │    │   OpenAI    │    │   Agent     │
│   Data      │───▶│   Layer     │───▶│   Proxy     │───▶│   Apps      │
│             │    │             │    │             │    │             │
│ • Training  │    │ • Fine-tune │    │ • Compat API│    │ • Chat      │
│   Data      │    │ • vLLM      │    │ • Routing   │    │ • RAG       │
│ • Documents │    │ • Multi-GPU │    │ • Rate Limit│    │ • Workflow  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

Benefits:

- 100% on-premises deployment
- OpenAI-compatible API for easy integration
- Cost control with private GPU clusters

### 4. Industrial Quality Inspection

Scenario: Manufacturing lines generate sensor data. Detecting anomalies early prevents costly defects and downtime.

Solution with ONE-DATA-STUDIO:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  IoT        │    │   Data      │    │   Model     │    │   Alerting  │
│  Sensors    │───▶│   Layer     │───▶│   Layer     │───▶│   System    │
│             │    │             │    │             │    │             │
│ • Temp      │    │ • Streaming │    │ • Anomaly   │    │ • Threshold │
│ • Pressure  │    │ • Feature   │    │ • Detection │    │ • Dashboard │
│ • Vibration │    │ • Store     │    │ • Real-time │    │ • Actions   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

Benefits:

- Real-time anomaly detection at sub-second latency
- Unified feature store for training and inference
- Traceability from prediction to source data

### 5. Custom AI Workflow Automation

Scenario: Complex business processes require multiple AI capabilities — document extraction, decision making, and action execution.

Solution with ONE-DATA-STUDIO:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Visual Workflow Builder                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐          │
│  │ Trigger │───▶│  OCR    │───▶│  LLM    │───▶│ Action  │          │
│  │ (Email) │    │ Extract │    │ Decide  │    │ Execute │          │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘          │
│                      │              │              │                 │
│                      ▼              ▼              ▼                 │
│               ┌──────────────────────────────────────┐              │
│               │          Execution Engine            │              │
│               │  • Parallel execution                │              │
│               │  • Error handling                    │              │
│               │  • State management                  │              │
│               └──────────────────────────────────────┘              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

Benefits:

- No-code workflow creation with visual builder
- Combine any AI capability in a single flow
- Built-in scheduling and monitoring

---

## ⚖️ Comparison with Alternatives

### vs. Standalone Platforms

| Aspect | ONE-DATA-STUDIO | Separate Tools |
| -------- | ----------------- | ---------------- |
| Data + ML + LLM | Single integrated platform | 3+ separate tools (Airflow + MLflow + LangChain) |
| Data-to-Model Pipeline | Native integration | Manual data export/import |
| Model-to-App Pipeline | OpenAI-compatible API | Custom integration code |
| Unified Governance | Single audit trail | Scattered logs |
| Learning Curve | One platform to learn | Multiple tools to master |
| Deployment | Single Helm chart | Multiple deployments |
| Cost | Single infrastructure | Multiple infrastructures |

### vs. Cloud Platforms

| Aspect | ONE-DATA-STUDIO | Cloud Platforms (Databricks, SageMaker, Vertex AI) |
| -------- | ----------------- | --------------------------------------------------- |
| Deployment | On-premises, any cloud, hybrid | Vendor-locked cloud |
| Data Privacy | Data stays on-premises | Data in vendor's cloud |
| Pricing | Open source (free) | Usage-based (expensive at scale) |
| Customization | Full source code access | Limited customization |
| LLM Integration | Built-in LLMOps layer | Separate LLM tools needed |
| Vendor Lock-in | None | High |

### vs. Other Open Source Platforms

| Feature | ONE-DATA-STUDIO | LangChain | MLflow | Apache Airflow |
| --------- | ----------------- | ----------- | -------- | ---------------- |
| Data Integration | ✅ Full | ❌ No | ❌ No | ✅ Basic |
| ETL Pipelines | ✅ Visual | ❌ No | ❌ No | ✅ Code-based |
| Feature Store | ✅ Built-in | ❌ No | ❌ No | ❌ No |
| Vector Storage | ✅ Milvus | ✅ Integration | ❌ No | ❌ No |
| Model Training | ✅ Distributed | ❌ No | ✅ Tracking only | ❌ No |
| Model Serving | ✅ vLLM | ❌ No | ✅ Basic | ❌ No |
| RAG Pipeline | ✅ Full | ✅ Full | ❌ No | ❌ No |
| Agent Framework | ✅ Built-in | ✅ Primary | ❌ No | ❌ No |
| Visual Workflow | ✅ ReactFlow | ❌ No | ❌ No | ❌ Code-based |
| Web UI | ✅ Full | ❌ No | ✅ Tracking UI | ✅ DAG UI |
| Multi-tenancy | ✅ Full | ❌ No | ❌ No | ❌ Limited |
| Enterprise Auth | ✅ Keycloak | ❌ No | ❌ No | ❌ Limited |

### When to Choose ONE-DATA-STUDIO

✅ Best fit for:

- Enterprises needing complete data-to-application pipeline
- Organizations requiring on-premises deployment
- Teams wanting unified platform instead of tool sprawl
- Companies with both structured data and document knowledge needs
- Projects requiring full audit trail and governance

❌ Consider alternatives if:

- You only need a single capability (e.g., just MLflow for experiment tracking)
- You're a cloud-first organization comfortable with vendor lock-in
- You need minimal infrastructure and prefer SaaS solutions
- Your team size is very small (< 5 people) with simple needs

---

## Technical Specifications

### Code Statistics

| Component | Files | Lines of Code |
| ----------- | ------- | --------------- |
| Python Backend | 289 | ~142,000 |
| TypeScript Frontend | 232 | ~120,000 |
| Test Code | 135+ | ~32,000 |
| Deployment Config | 155+ | ~15,000 |
| Total | 630+ | ~300,000 |

### Technology Stack

Frontend:

- React 18.3 with TypeScript 5.4
- Ant Design 5.14 for UI components
- ReactFlow 11.10 for workflow canvas
- Zustand 4.5 for state management
- React Query 5.24 for server state
- Vite 5.1 for build tooling

Backend:

- Python 3.10+ runtime
- Flask 3.0 for Data/Agent/Admin APIs
- FastAPI for Model/Proxy APIs
- SQLAlchemy 2.0 with Alembic migrations
- Celery for background tasks

Storage:

- MySQL 8.0 for relational data
- Redis 7.0 for caching and sessions
- MinIO for S3-compatible object storage
- Milvus 2.3 for vector embeddings
- Elasticsearch 8.10 for search

Infrastructure:

- Kubernetes 1.27+ for orchestration
- Helm 3.x for package management
- Istio for service mesh
- Keycloak 23.0 for identity management
- Prometheus + Grafana for monitoring
- Jaeger for distributed tracing

### Security Features

| Category | Features |
| ---------- | ---------- |
| Authentication | JWT tokens, Keycloak SSO, OIDC/SAML support |
| Authorization | RBAC, fine-grained permissions, multi-tenant isolation |
| Network | TLS/HTTPS, HSTS headers, CORS configuration |
| Data | SQL injection protection, input sanitization, encryption at rest |
| Audit | Comprehensive logging, searchable audit trail, compliance support |

### Performance Characteristics

| Metric | Value | Notes |
| -------- | ------- | ------- |
| API Response Time | < 100ms (p95) | For metadata operations |
| RAG Query Latency | < 2s (p95) | Including retrieval and generation |
| Vector Search | < 50ms | For 10M+ vectors |
| Concurrent Users | 1000+ | With proper resource allocation |
| Model Inference | Depends on model | vLLM provides high throughput |

---

## Project Structure

```
one-data-studio/
├── services/                     # Backend microservices
│   ├── data-api/                 # Data governance API (Flask)
│   │   ├── app/
│   │   │   ├── routes/           # API endpoints
│   │   │   ├── services/         # Business logic
│   │   │   ├── models/           # Database models
│   │   │   └── schemas/          # Request/response schemas
│   │   └── requirements.txt
│   ├── agent-api/                # LLMOps orchestration API (Flask)
│   │   ├── app/
│   │   │   ├── routes/           # Workflow, RAG, Agent endpoints
│   │   │   ├── services/         # Execution engine, RAG service
│   │   │   ├── core/             # LLM clients, embeddings
│   │   │   └── tools/            # Agent tools
│   │   └── requirements.txt
│   ├── model-api/                # MLOps management API (FastAPI)
│   │   ├── app/
│   │   │   ├── routers/          # Model, training, serving endpoints
│   │   │   ├── services/         # K8s integration, job management
│   │   │   └── schemas/          # Pydantic schemas
│   │   └── requirements.txt
│   ├── openai-proxy/             # OpenAI-compatible proxy (FastAPI)
│   │   ├── app/
│   │   │   ├── routers/          # Chat, completions, embeddings
│   │   │   ├── services/         # Model routing, rate limiting
│   │   │   └── middleware/       # Token counting, cost tracking
│   │   └── requirements.txt
│   ├── admin-api/                # Platform administration (Flask)
│   ├── ocr-service/              # Document recognition (FastAPI)
│   ├── behavior-service/         # User analytics (Flask)
│   └── shared/                   # Shared modules
│       ├── auth/                 # JWT, permissions
│       ├── storage/              # MinIO, file handling
│       ├── cache/                # Redis utilities
│       └── utils/                # Common utilities
├── web/                          # Frontend application
│   ├── src/
│   │   ├── components/           # Reusable UI components
│   │   │   ├── common/           # Buttons, inputs, modals
│   │   │   ├── workflow/         # ReactFlow nodes and edges
│   │   │   └── charts/           # Data visualization
│   │   ├── pages/                # Page components
│   │   │   ├── data/             # Data platform pages
│   │   │   ├── model/            # Model platform pages
│   │   │   ├── agent/            # Agent platform pages
│   │   │   └── admin/            # Admin pages
│   │   ├── services/             # API clients
│   │   ├── stores/               # Zustand state stores
│   │   ├── hooks/                # Custom React hooks
│   │   ├── utils/                # Utility functions
│   │   └── locales/              # i18n translations (en, zh)
│   ├── public/                   # Static assets
│   └── package.json
├── deploy/                       # Deployment configurations
│   ├── local/                    # Docker Compose
│   │   ├── docker-compose.yml    # Main compose file
│   │   └── docker-compose.*.yml  # Service overlays
│   ├── kubernetes/               # Kubernetes manifests
│   │   ├── base/                 # Kustomize base
│   │   └── overlays/             # dev, staging, production
│   ├── helm/                     # Helm charts
│   │   └── charts/one-data/      # Main chart
│   ├── dockerfiles/              # Dockerfile for each service
│   ├── argocd/                   # ArgoCD applications
│   └── monitoring/               # Prometheus, Grafana configs
├── tests/                        # Test suites
│   ├── unit/                     # Unit tests by service
│   ├── integration/              # API integration tests
│   ├── e2e/                      # Playwright end-to-end tests
│   └── performance/              # Load testing scripts
├── docs/                         # Documentation
│   ├── 01-architecture/          # Architecture docs
│   ├── 02-integration/           # Integration guides
│   ├── 06-development/           # Development guides
│   ├── 07-operations/            # Operations guides
│   └── 08-user-guide/            # User documentation
└── examples/                     # Usage examples
    ├── langchain/                # LangChain integration
    ├── python/                   # Python SDK examples
    └── workflows/                # Workflow definitions
```

---

## Documentation

| Document | Description |
| ---------- | ------------- |
| [Platform Overview](docs/01-architecture/platform-overview.md) | High-level architecture and concepts |
| [Four-Layer Stack](docs/01-architecture/four-layer-stack.md) | Detailed layer descriptions |
| [Integration Guide](docs/02-integration/integration-overview.md) | How layers connect |
| [API Specifications](docs/02-integration/api-specifications.md) | REST API documentation |
| [Development Guide](docs/06-development/poc-playbook.md) | Local development setup |
| [Operations Guide](docs/07-operations/operations-guide.md) | Production deployment |
| [User Guide](docs/08-user-guide/getting-started.md) | End-user documentation |

---

## Contributing

We welcome contributions from the community!

### Development Setup

```bash
# Backend development
cd services/agent-api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
python app.py

# Frontend development
cd web
npm install
npm run dev
```

### Code Standards

| Language | Standards |
| ---------- | ----------- |
| Python | PEP 8, use `logging` (not `print`), type hints |
| TypeScript | ESLint + Prettier, avoid `console.log` |
| Git | Conventional commits, small atomic changes |

### Testing

```bash
# Run Python tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=services/ --cov-report=html

# Run frontend tests
cd web && npm test

# Run E2E tests
cd tests/e2e && npx playwright test
```

### Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make changes and add tests
4. Ensure tests pass: `pytest tests/ && cd web && npm test`
5. Commit with clear message: `git commit -m 'feat: add amazing feature'`
6. Push and create Pull Request

---

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

```
Copyright 2024-2026 ONE-DATA-STUDIO Contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
```

---

## Acknowledgments

Built with and inspired by:

- [OpenMetadata](https://open-metadata.org/) - Open source metadata platform
- [Ray](https://github.com/ray-project/ray) - Distributed computing framework
- [vLLM](https://github.com/vllm-project/vllm) - High-throughput LLM serving
- [LangChain](https://github.com/langchain-ai/langchain) - LLM application framework
- [Milvus](https://github.com/milvus-io/milvus) - Vector database
- [ReactFlow](https://reactflow.dev/) - Node-based graph editor

---

## Community

- Issues: [GitHub Issues](https://github.com/iannil/one-data-studio/issues)
- Discussions: [GitHub Discussions](https://github.com/iannil/one-data-studio/discussions)

---

<div align="center">

Built with ❤️ by the ONE-DATA-STUDIO Community

If you find this project useful, please consider giving it a ⭐!

[Back to Top](#one-data-studio)

</div>
