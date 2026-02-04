# ONE-DATA-STUDIO 开发环境硬件要求评估

> **评估日期**: 2026-02-04
> **目的**: 评估启动全部服务所需的硬件配置

---

## 一、当前系统配置

```bash
# 检测结果
内存: 16 GB
CPU: 8 核
存储: 926 GB 总容量，105 GB 可用
平台: macOS (Darwin 25.2.0)
```

**结论**: 当前配置为 16GB 内存，低于核心服务推荐的最低配置（16-24GB）。建议按需启动服务或升级内存。

---

## 二、服务清单

### 2.1 核心基础设施服务（无 Profile）

| 服务 | 用途 | 镜像 | 内存基准 | CPU |
|------|------|------|----------|-----|
| mysql | 主数据库 | mysql:8.0 | 512MB - 1GB | 0.5-1 核 |
| redis | 缓存 | redis:7-alpine | 128MB | 0.5 核 |
| minio | 对象存储 | minio/minio:latest | 256MB | 0.5 核 |
| etcd | Milvus 依赖 | quay.io/coreos/etcd:v3.5.5 | 128MB | 0.5 核 |
| milvus | 向量数据库 | milvusdb/milvus:v2.3.0 | 2GB+ | 2-4 核 |
| elasticsearch | 搜索引擎 | docker.elastic.co/elasticsearch:8.10.2 | 512MB (-Xms512m -Xmx512m) | 1 核 |
| openmetadata | 元数据治理 | openmetadata/server:1.3.1 | 1GB | 1 核 |
| keycloak | 认证授权 | quay.io/keycloak/keycloak:23.0 | 512MB | 0.5 核 |
| kettle | ETL 引擎 | hiromuhota/webspoon:0.9.0.27 | 2GB (-Xms512m -Xmx2g) | 1-2 核 |

**核心基础设施小计**: ~7.5GB

### 2.2 应用服务（无 Profile）

| 服务 | 端口 | 内存 | 用途 |
|------|------|------|------|
| agent-api | 8000 | 256MB | 应用编排 API |
| data-api | 8001 | 256MB | 数据治理 API |
| model-api | 8002 | 256MB | 模型管理 API |
| openai-proxy | 8003 | 256MB | OpenAI 兼容代理 |
| admin-api | 8004 | 256MB | 管理后台 API |
| ocr-service | 8007 | 512MB | OCR 文档识别 |
| behavior-service | 8008 | 128MB | 用户行为分析 |
| web-frontend | 3000 | 128MB | 前端应用 |

**应用服务小计**: ~2GB

### 2.3 可选服务（Profile: etl）

| 服务 | 内存 | 用途 |
|------|------|------|
| hop-server | 256MB | Apache Hop ETL 引擎 |

### 2.4 可选服务（Profile: security）

| 服务 | 内存 | 用途 |
|------|------|------|
| shardingsphere-proxy | 512MB | 数据脱敏代理 |

### 2.5 AI/ML 服务（Profile: ai）

| 服务 | 内存 | GPU | 用途 |
|------|------|-----|------|
| vllm-chat | 4-16GB | 可选 | LLM 文本生成 |
| vllm-embed | 4-8GB | 可选 | 文本向量化 |
| ollama | 512MB | CPU 模式 | 备选 LLM 服务 |

**AI 服务小计**: 8-24GB

### 2.6 数据标注服务（无 Profile）

| 服务 | 内存 | 用途 |
|------|------|------|
| label-studio-postgresql | 128MB | Label Studio 数据库 |
| label-studio | 1GB | 数据标注平台 |

**数据标注小计**: ~1.1GB

### 2.7 工作流调度服务（无 Profile）

| 服务 | 内存 | 用途 |
|------|------|------|
| zookeeper | 256MB | DolphinScheduler 依赖 |
| dolphinscheduler-postgresql | 256MB | DolphinScheduler 数据库 |
| dolphinscheduler-api | 1GB | 工作流调度 |

**工作流调度小计**: ~1.5GB

### 2.8 BI 分析服务（无 Profile）

| 服务 | 内存 | 用途 |
|------|------|------|
| superset-cache | 64MB | Superset 缓存 |
| superset | 2GB | BI 分析平台 |

**BI 服务小计**: ~2GB

### 2.9 数据集成服务（无 Profile）

| 服务 | 内存 | 用途 |
|------|------|------|
| seatunnel-zookeeper | 256MB | SeaTunnel 依赖 |
| seatunnel | 2GB (-Xms2g -Xmx2g) | 数据集成引擎 |

**数据集成小计**: ~2.25GB

---

## 三、内存占用详细估算

### 3.1 无 Profile 启动（核心服务）

| 类别 | 服务 | 内存小计 |
|------|------|----------|
| 数据库 | MySQL + Redis + etcd + PostgreSQL x2 | ~2.5GB |
| 存储 | MinIO | ~256MB |
| 向量 | Milvus | ~2GB |
| 搜索 | Elasticsearch | ~512MB |
| 元数据 | OpenMetadata | ~1GB |
| 认证 | Keycloak | ~512MB |
| ETL | Kettle | ~2GB |
| 应用 APIs | 7 个服务 | ~2GB |
| 前端 | web-frontend | ~128MB |
| 数据标注 | Label Studio + PG | ~1.1GB |
| 工作流调度 | DolphinScheduler + ZK + PG | ~1.5GB |
| BI 分析 | Superset + 缓存 | ~2GB |
| 数据集成 | SeaTunnel + ZK | ~2.25GB |
| 其他 | OCR + Behavior | ~640MB |
| **总计** | | **~18.5GB** |

### 3.2 添加 AI Profile（CPU 推理模式）

| 类别 | 内存小计 |
|------|----------|
| 核心服务 | ~18.5GB |
| vllm-chat (CPU) | 8-16GB |
| vllm-embed (CPU) | 4-8GB |
| ollama | 512MB |
| **总计** | **~31-43GB** |

### 3.3 添加 AI Profile（GPU 加速模式）

| 类别 | 内存小计 |
|------|----------|
| 核心服务 | ~18.5GB |
| vllm-chat (GPU) | 4-8GB (模型在 GPU 中) |
| vllm-embed (GPU) | 2-4GB (模型在 GPU 中) |
| ollama | 512MB |
| **总计** | **~25-31GB** |

### 3.4 最小启动方案（按需启动）

```bash
# 仅启动核心开发服务
docker-compose up -d \
  mysql redis minio etcd milvus \
  elasticsearch openmetadata keycloak \
  agent-api data-api openai-proxy admin-api model-api \
  ocr-service behavior-service web-frontend
```

| 服务列表 | 内存占用 |
|----------|----------|
| 数据库: MySQL + Redis + etcd | ~1.5GB |
| 存储: MinIO | ~256MB |
| 向量: Milvus | ~2GB |
| 搜索: Elasticsearch | ~512MB |
| 元数据: OpenMetadata | ~1GB |
| 认证: Keycloak | ~512MB |
| 应用 APIs (6 个) | ~1.5GB |
| 前端 | ~128MB |
| OCR + Behavior | ~640MB |
| **最小启动总计** | **~8GB** |

---

## 四、硬件配置建议

### 4.1 最小配置（核心开发）

```
内存: 16GB - 24GB
CPU: 4-8 核
存储: 50GB SSD
GPU: 不需要
适用场景: 基础功能开发，不涉及 AI 推理
```

### 4.2 推荐开发配置

```
内存: 32GB - 64GB
CPU: 8-16 核
存储: 100GB SSD (NVMe 推荐)
GPU: 可选 (NVIDIA 8GB+ VRAM)
适用场景: 全栈开发，包含 AI 功能测试
```

### 4.3 完整配置（全部服务）

```
内存: 64GB - 128GB
CPU: 16-32 核
存储: 200GB+ SSD (NVMe)
GPU: 推荐 (1-2x NVIDIA 16GB+ VRAM)
适用场景: 生产环境模拟，性能测试
```

---

## 五、按使用场景推荐

### 5.1 轻量开发（个人开发者 - 当前配置适用）

**目标**: 核心功能开发，不涉及 AI 模型

```
配置: 16GB RAM, 8核 CPU, 100GB SSD
启动命令:
  docker-compose up -d \
    mysql redis minio etcd milvus \
    elasticsearch openmetadata keycloak \
    agent-api data-api openai-proxy admin-api model-api \
    web-frontend

预期内存占用: ~8GB
```

### 5.2 全栈开发（含 AI，推荐升级）

**目标**: 完整功能测试，包括 AI 功能

```
配置: 64GB RAM, 12核 CPU, 200GB SSD, GPU 可选
启动命令:
  docker-compose --profile ai up -d

预期内存占用:
  - CPU 推理: 31-43GB
  - GPU 加速: 25-31GB
```

### 5.3 团队开发（生产级）

**目标**: 生产环境模拟，性能测试

```
配置: 128GB RAM, 16-32核 CPU, 400GB NVMe SSD, GPU 必须
启动命令:
  docker-compose --profile ai --profile etl --profile security up -d

预期内存占用: 40-60GB
```

---

## 六、优化建议

### 6.1 Docker 资源限制

在 docker-compose.yml 中添加资源限制：

```yaml
services:
  mysql:
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  milvus:
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
```

### 6.2 按需启动服务

```bash
# 场景 1: 仅核心服务（最小化）
docker-compose up -d mysql redis agent-api data-api web-frontend

# 场景 2: 核心服务 + 向量搜索
docker-compose up -d mysql redis minio milvus etcd agent-api data-api web-frontend

# 场景 3: 核心服务 + 元数据治理
docker-compose up -d \
  mysql redis elasticsearch openmetadata \
  agent-api data-api web-frontend

# 场景 4: 添加 AI 服务（需要更多内存）
docker-compose --profile ai up -d
```

### 6.3 开发环境优化

1. **使用内存映射减少内存占用**
   - Milvus 配置使用内存映射存储

2. **限制数据库保留日志大小**
   - MySQL: 限制 binlog 保留天数
   - PostgreSQL: 限制 WAL 保留

3. **禁用不必要的服务**
   - DolphinScheduler（如果不需要工作流调度）
   - Superset（如果不需要 BI 分析）
   - SeaTunnel（如果不需要数据集成）

4. **使用更小的模型进行开发测试**
   ```bash
   # 使用 1.5B 模型而非 7B
   VLLM_CHAT_MODEL=Qwen/Qwen2.5-1.5B-Instruct
   ```

5. **调整 Elasticsearch 内存**
   ```yaml
   environment:
     - "ES_JAVA_OPTS=-Xms256m -Xmx256m"  # 从 512m 降至 256m
   ```

### 6.4 macOS 特定优化

```bash
# 增加 Docker Desktop 内存限制
# Settings -> Resources -> Memory: 设置为 12GB+ (留 4GB 给系统)

# 使用带数据卷的容器减少内存占用
# 已在 docker-compose.yml 中配置 volumes
```

---

## 七、验证步骤

### 7.1 检查硬件资源

```bash
# macOS
sysctl -n hw.memsize | awk '{print $1/1024/1024/1024 " GB"}'
sysctl -n hw.ncpu
df -h /

# Linux
free -h
nproc
df -h
```

### 7.2 监控 Docker 资源

```bash
# 实时监控所有容器
docker stats

# 查看容器资源使用（无 stream）
docker stats --no-stream

# 查看容器状态
docker ps --format "table {{.Names}}\t{{.Status}}"

# 查看镜像大小
docker images --format "table {{.Repository}}\t{{.Size}}"
```

### 7.3 检查服务健康状态

```bash
# 检查所有服务健康状态
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "healthy|unhealthy"

# 检查特定服务日志
docker logs one-data-mysql --tail 50
docker logs one-data-agent-api --tail 50
```

---

## 八、结论与建议

### 8.1 当前配置分析

```
硬件: 16GB RAM, 8 核 CPU, 926GB 存储
评估: 勉强满足核心开发需求
```

### 8.2 针对当前配置的建议

1. **使用最小启动方案**
   ```bash
   # 仅启动核心服务（约 8GB 内存）
   docker-compose up -d \
     mysql redis minio etcd milvus \
     elasticsearch openmetadata keycloak \
     agent-api data-api openai-proxy admin-api model-api \
     web-frontend
   ```

2. **避免启动的服务**
   - AI 服务（vllm-chat, vllm-embed, ollama）
   - BI 分析（superset）
   - 工作流调度（dolphinscheduler-*）
   - 数据集成（seatunnel-*）

3. **如需 AI 功能**
   - 使用外部 API（如 OpenAI、通义千问等）
   - 或升级内存至 32GB+

### 8.3 个人开发者（推荐配置）

```
MacBook Pro M2/M3 Pro/Max
- 内存: 32GB 或更高
- 存储: 512GB SSD (外接也可用于 Docker 数据)
- 适用: 全栈开发 + AI 功能测试
```

### 8.4 团队开发服务器

```
Linux 服务器
- 内存: 128GB
- CPU: 16 核
- 存储: 500GB NVMe SSD
- GPU: NVIDIA A10/L40 (24GB)
- 适用: 生产环境模拟 + 多人并发开发
```

### 8.5 云开发环境

```
AWS/阿里云/腾讯云
- 起步: g4ad.xlarge (16GB, 4核)
- 推荐: g4ad.2xlarge (32GB, 8核) 或更高
- 完整: g4ad.4xlarge (64GB, 16核) + GPU
```

---

## 九、快速参考

### 9.1 内存速查表

| 启动模式 | 内存需求 | 适用场景 |
|----------|----------|----------|
| 最小（仅数据库+API） | 4-6GB | 基础 API 开发 |
| 核心（含向量+元数据） | 8-12GB | 数据治理开发 |
| 标准（含 BI+工作流） | 16-24GB | 全栈开发 |
| 完整（含 AI CPU） | 32-48GB | AI 功能开发 |
| 完整（含 AI GPU） | 24-32GB | AI 性能优化 |

### 9.2 启动命令速查

```bash
# 最小开发
docker-compose up -d mysql redis agent-api data-api web-frontend

# 核心开发
docker-compose up -d mysql redis minio etcd milvus \
  elasticsearch openmetadata keycloak \
  agent-api data-api openai-proxy admin-api model-api web-frontend

# 添加 AI
docker-compose --profile ai up -d

# 添加 ETL
docker-compose --profile etl up -d

# 添加安全
docker-compose --profile security up -d

# 全部服务
docker-compose --profile ai --profile etl --profile security up -d
```

---

*本文档将根据实际服务变化持续更新*
