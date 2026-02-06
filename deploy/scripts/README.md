# ONE-DATA-STUDIO 部署脚本

本目录包含部署和测试相关的脚本。

## 脚本说明

### 阶段独立运维脚本 (Stage Operations)

这些脚本允许独立启动、停止和检查三个阶段的服务。

#### 启动脚本 (Start Scripts)

| 脚本 | 说明 | 端口范围 |
|------|------|----------|
| `start-dataops.sh` | 启动 DataOps 阶段服务 (数据治理、ETL、BI) | 81xx |
| `start-mlops.sh` | 启动 MLOps 阶段服务 (模型训练、推理) | 82xx |
| `start-llmops.sh` | 启动 LLMOps 阶段服务 (Agent 编排、应用) | 83xx |

#### 停止脚本 (Stop Scripts)

| 脚本 | 说明 |
|------|------|
| `stop-dataops.sh` | 停止 DataOps 阶段服务 |
| `stop-mlops.sh` | 停止 MLOps 阶段服务 |
| `stop-llmops.sh` | 停止 LLMOps 阶段服务 |

#### 状态检查脚本 (Status Scripts)

| 脚本 | 说明 |
|------|------|
| `status-dataops.sh` | 检查 DataOps 阶段服务状态 |
| `status-mlops.sh` | 检查 MLOps 阶段服务状态 |
| `status-llmops.sh` | 检查 LLMOps 阶段服务状态 |
| `status-all.sh` | 检查所有阶段服务状态 |

#### 公共函数库

| 脚本 | 说明 |
|------|------|
| `common-functions.sh` | 共享函数库 (被其他脚本 source) |

### 部署脚本

| 脚本 | 说明 |
|------|------|
| `deploy-phase1.sh` | 阶段1: 基础设施部署 (数据库、存储) |
| `deploy-phase2.sh` | 阶段2: 应用服务部署 |
| `deploy-all.sh` | 完整部署 (phase1 + phase2) |
| `deploy.sh` | 通用部署脚本 |
| `rollback.sh` | 回滚部署 |
| `blue-green-deploy.sh` | 蓝绿部署 |

### 清理脚本

| 脚本 | 说明 |
|------|------|
| `clean.sh` | 清理所有 K8s 资源 |

### 测试脚本

| 脚本 | 说明 |
|------|------|
| `test-all.sh` | 运行所有集成测试 |
| `test-e2e.sh` | 端到端测试 |

### 辅助脚本

| 脚本 | 说明 |
|------|------|
| `install-kind.sh` | 安装 Kind 本地 K8s 集群 |
| `port-forward.sh` | 启动端口转发 |
| `validate-secrets.sh` | 验证密钥配置 |

## 使用方法

### 阶段独立运维

```bash
# 启动单个阶段
./deploy/scripts/start-dataops.sh    # 数据治理
./deploy/scripts/start-mlops.sh      # 模型训练
./deploy/scripts/start-llmops.sh     # 应用编排

# 查看状态
./deploy/scripts/status-all.sh

# 停止阶段
./deploy/scripts/stop-dataops.sh
./deploy/scripts/stop-mlops.sh
./deploy/scripts/stop-llmops.sh
```

### 并发运行多个阶段

三个阶段使用不同的端口前缀，可以并发运行：

```bash
# 同时启动三个阶段
./deploy/scripts/start-dataops.sh &
./deploy/scripts/start-mlops.sh &
./deploy/scripts/start-llmops.sh &
wait

# 查看所有状态
./deploy/scripts/status-all.sh --verbose
```

### 选项说明

启动脚本支持以下选项：

```bash
# 跳过共享基础设施（如果已运行）
./start-dataops.sh --no-infrastructure

# 跳过 GPU 相关服务
./start-mlops.sh --no-gpu

# Dry run 模式（不实际启动）
./start-llmops.sh --dry-run

# 详细输出
./start-dataops.sh --verbose

# 停止并删除所有数据卷
./stop-dataops.sh --remove-volumes
```

状态检查脚本支持以下选项：

```bash
# 详细状态（包含资源使用、日志等）
./status-dataops.sh --verbose

# JSON 格式输出
./status-all.sh --json

# 监控模式（每 5 秒刷新）
./status-mlops.sh --watch
```

### 完整部署

```bash
cd deploy/scripts
./deploy-all.sh

# 清理资源
./clean.sh

# 运行测试
./test-all.sh

# 端口转发
./port-forward.sh
```

## 端口分配

| 阶段 | 端口范围 | 核心服务 |
|------|----------|----------|
| DataOps | 81xx | OpenMetadata:8585, Kettle:8180, Superset:8188, data-api:8101 |
| MLOps | 82xx | model-api:8202, Label Studio:8209, vLLM:8210/8211, Ollama:8134 |
| LLMOps | 83xx | agent-api:8300, openai-proxy:8303, web:8305, Keycloak:8380 |

共享基础设施端口（所有阶段复用）：
- MySQL: 3306
- Redis: 6379
- MinIO: 9000/9001
- Milvus: 19530

## 运维脚本

运维相关脚本（灾难恢复、密钥轮换）位于 `/scripts/` 目录。
