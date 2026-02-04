# 分阶段测试指南

> **最后更新**: 2026-02-04
> **目的**: 在 16GB 内存限制下，通过分阶段局部启动和测试，验证所有模块功能的完整度和可靠性

---

## 一、概述

本指南适用于资源受限环境（如 16GB 内存本地开发环境）下的系统测试。通过分阶段启动服务并进行验证，确保各模块功能正常。

### 硬件限制

```
内存: 16 GB
CPU: 8 核
存储: 926 GB (105 GB 可用)
平台: macOS (Darwin 25.2.0)
```

### 测试原则

1. **增量测试**: 按服务依赖关系分阶段启动
2. **及时清理**: 每阶段测试完成后清理不必要的服务
3. **资源监控**: 实时监控内存使用情况
4. **问题隔离**: 确保问题可以被快速定位

---

## 二、服务分组

### A 组：基础设施层（~4GB）

| 服务 | 内存 | 端口 | 用途 |
|------|------|------|------|
| mysql | 512MB-1GB | 3306 | 主数据库 |
| redis | 128MB | 6379 | 缓存 |
| minio | 256MB | 9000,9001 | 对象存储 |

### B 组：元数据治理（~3.5GB）

| 服务 | 内存 | 端口 | 用途 |
|------|------|------|------|
| etcd | 128MB | 2379 | Milvus 依赖 |
| milvus | 2GB | 19530,9091 | 向量数据库 |
| elasticsearch | 512MB | 9200,9300 | 搜索引擎 |
| openmetadata | 1GB | 8585 | 元数据治理 |

### C 组：核心 API 服务（~2GB）

| 服务 | 内存 | 端口 | 用途 |
|------|------|------|------|
| data-api | 256MB | 8001 | 数据治理 API |
| admin-api | 256MB | 8004 | 管理后台 API |
| openai-proxy | 256MB | 8003 | OpenAI 兼容代理 |

### D 组：AI/Agent 服务（~1.5GB）

| 服务 | 内存 | 端口 | 用途 |
|------|------|------|------|
| agent-api | 256MB | 8000 | 应用编排 API |
| model-api | 256MB | 8002 | 模型管理 API |

### E 组：前端（~128MB）

| 服务 | 内存 | 端口 | 用途 |
|------|------|------|------|
| web-frontend | 128MB | 3000 | 前端应用 |

### F 组：扩展服务（可选，~2.5GB）

| 服务 | 内存 | 端口 | 用途 |
|------|------|------|------|
| ocr-service | 512MB | 8007 | OCR 识别 |
| behavior-service | 128MB | 8008 | 行为分析 |
| keycloak | 512MB | 8080 | 认证 |

### G 组：重型服务（可选，~6GB+）

| 服务 | 内存 | 端口 | 用途 |
|------|------|------|------|
| kettle | 2GB | 8088,8181 | ETL 引擎 |
| superset | 2GB | 8088 | BI 分析 |
| dolphinscheduler | 1.5GB | 12345,25333,25334 | 工作流调度 |

---

## 三、快速开始

### 3.1 环境准备

```bash
# 1. 配置环境变量
cd deploy/local
cp .env.example .env
# 编辑 .env 文件，设置必要的密码

# 2. 给测试脚本添加执行权限
chmod +x test-phased.sh

# 3. 验证 Docker 可用
docker --version
docker-compose --version
```

### 3.2 运行测试

```bash
# 运行特定阶段
./test-phased.sh 1    # 仅阶段 1
./test-phased.sh 2    # 阶段 1+2
./test-phased.sh 3    # 阶段 1+2+3
./test-phased.sh all  # 阶段 1-5

# 查看状态
./test-phased.sh status

# 清理环境
./test-phased.sh clean
```

---

## 四、阶段详情

### 阶段 1：基础设施验证（A 组）

**目标**: 验证 MySQL、Redis、MinIO 正常运行

**启动服务**:
```bash
cd deploy/local
docker-compose up -d mysql redis minio
```

**健康检查**:
```bash
# MySQL
docker exec one-data-mysql mysqladmin ping -h localhost

# Redis
docker exec one-data-redis redis-cli -a ${REDIS_PASSWORD} ping

# MinIO
curl http://localhost:9000/minio/health/live
```

**测试脚本**:
```bash
pytest tests/integration/test_phase1_infrastructure.py -v
```

**预期结果**:
- MySQL 可连接，可创建表和插入数据
- Redis 可读写，支持各种数据结构
- MinIO 可创建 bucket 和上传下载对象

---

### 阶段 2：元数据与向量数据库（A+B 组）

**目标**: 验证 Milvus、Elasticsearch、OpenMetadata

**启动服务**:
```bash
docker-compose up -d etcd milvus elasticsearch openmetadata
```

**健康检查**:
```bash
# Milvus
curl http://localhost:19530/healthz

# Elasticsearch
curl http://localhost:9200/_cluster/health

# OpenMetadata
curl http://localhost:8585/api/v1/system/version
```

**测试脚本**:
```bash
pytest tests/integration/test_phase2_metadata.py -v
```

**预期结果**:
- Milvus 可创建集合和插入向量
- Elasticsearch 可创建索引和搜索
- OpenMetadata API 可访问

---

### 阶段 3：核心 API 服务（A+B+C 组）

**目标**: 验证 data-api、admin-api、openai-proxy

**启动服务**:
```bash
docker-compose up -d data-api admin-api openai-proxy
```

**健康检查**:
```bash
# data-api
curl http://localhost:8001/api/v1/health

# admin-api
curl http://localhost:8004/api/v1/health

# openai-proxy
curl http://localhost:8003/health
```

**测试脚本**:
```bash
pytest tests/integration/test_phase3_apis.py -v
```

**预期结果**:
- data-api 可管理数据源和元数据
- admin-api 可管理用户和权限
- openai-proxy 可路由模型请求

---

### 阶段 4：Agent 和模型服务（A+B+C+D 组）

**目标**: 验证 agent-api、model-api

**启动服务**:
```bash
docker-compose up -d agent-api model-api
```

**健康检查**:
```bash
# agent-api
curl http://localhost:8000/api/v1/health

# model-api
curl http://localhost:8002/api/v1/health
```

**测试脚本**:
```bash
pytest tests/integration/test_phase4_agent.py -v
```

**预期结果**:
- agent-api 可创建和执行工作流
- model-api 可注册和部署模型

---

### 阶段 5：前端集成（A+B+C+D+E 组）

**目标**: 验证前后端集成

**启动服务**:
```bash
docker-compose up -d web-frontend
```

**健康检查**:
```bash
curl http://localhost:3000
```

**测试脚本**:
```bash
pytest tests/integration/test_phase5_frontend.py -v
```

**预期结果**:
- 前端页面可加载
- API 调用正常
- 基本用户流程可用

---

### 阶段 6：扩展服务（需释放内存）

**目标**: 验证 OCR、行为分析、认证服务

**操作步骤**:
```bash
# 1. 停止部分服务释放内存
docker-compose stop openmetadata elasticsearch

# 2. 启动扩展服务
docker-compose up -d ocr-service behavior-service keycloak
```

**测试脚本**:
```bash
pytest tests/integration/test_phase6_extensions.py -v
```

---

### 阶段 7：重型服务（独立测试）

**目标**: 验证 ETL、BI、调度服务

**注意**: 此阶段需要独立运行，停止其他所有服务

---

## 五、测试清单

### 服务状态检查表

| 服务 | 健康检查 | 功能测试 | 集成测试 | 状态 |
|------|----------|----------|----------|------|
| mysql | ☐ | ☐ | ☐ | ⬜ |
| redis | ☐ | ☐ | ☐ | ⬜ |
| minio | ☐ | ☐ | ☐ | ⬜ |
| etcd | ☐ | ☐ | ☐ | ⬜ |
| milvus | ☐ | ☐ | ☐ | ⬜ |
| elasticsearch | ☐ | ☐ | ☐ | ⬜ |
| openmetadata | ☐ | ☐ | ☐ | ⬜ |
| data-api | ☐ | ☐ | ☐ | ⬜ |
| admin-api | ☐ | ☐ | ☐ | ⬜ |
| openai-proxy | ☐ | ☐ | ☐ | ⬜ |
| agent-api | ☐ | ☐ | ☐ | ⬜ |
| model-api | ☐ | ☐ | ☐ | ⬜ |
| web-frontend | ☐ | ☐ | ☐ | ⬜ |
| ocr-service | ☐ | ☐ | ☐ | ⬜ |
| behavior-service | ☐ | ☐ | ☐ | ⬜ |
| keycloak | ☐ | ☐ | ☐ | ⬜ |

### 功能模块测试

| 功能模块 | 测试文件 | 状态 |
|----------|----------|------|
| 基础设施 | test_phase1_infrastructure.py | ⬜ |
| 元数据服务 | test_phase2_metadata.py | ⬜ |
| API 服务 | test_phase3_apis.py | ⬜ |
| Agent/模型 | test_phase4_agent.py | ⬜ |
| 前端集成 | test_phase5_frontend.py | ⬜ |
| 扩展服务 | test_phase6_extensions.py | ⬜ |

---

## 六、常见问题

### 6.1 内存不足

**症状**: 服务启动失败或响应缓慢

**解决方案**:
```bash
# 查看内存使用
docker stats --no-stream

# 停止不必要的服务
docker-compose stop <service-name>

# 清理未使用的资源
docker system prune -a
```

### 6.2 端口冲突

**症状**: 服务无法启动，提示端口已被占用

**解决方案**:
```bash
# 查看端口占用
lsof -i :<port>

# 停止占用端口的服务
kill -9 <pid>
```

### 6.3 数据持久化

**症状**: 数据在容器重启后丢失

**解决方案**:
```bash
# 检查卷挂载
docker volume ls

# 备份数据
docker run --rm -v one-data-mysql-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/mysql-backup.tar.gz /data
```

---

## 七、测试报告模板

### 阶段测试报告

```markdown
# 阶段 X 测试报告

**日期**: YYYY-MM-DD
**测试人**: 姓名
**环境**: macOS 16GB

## 测试范围
- 服务列表
- 测试项目

## 测试结果
| 项目 | 结果 | 备注 |
|------|------|------|
| 项目1 | ✅/❌ | 说明 |

## 发现的问题
1. 问题描述
   - 重现步骤
   - 预期结果
   - 实际结果

## 资源使用
- 峰值内存: X GB
- 平均内存: X GB

## 下一步行动
- [ ] 修复问题1
- [ ] 验证修复
```

---

## 八、附录

### A. 端口映射

| 服务 | 内部端口 | 外部端口 | 协议 |
|------|----------|----------|------|
| mysql | 3306 | 3306 | TCP |
| redis | 6379 | 6379 | TCP |
| minio | 9000 | 9000 | HTTP |
| minio-console | 9001 | 9001 | HTTP |
| etcd | 2379 | 2379 | HTTP |
| milvus | 19530 | 19530 | TCP |
| elasticsearch | 9200 | 9200 | HTTP |
| openmetadata | 8585 | 8585 | HTTP |
| data-api | 8001 | 8001 | HTTP |
| admin-api | 8004 | 8004 | HTTP |
| openai-proxy | 8000 | 8003 | HTTP |
| agent-api | 8000 | 8000 | HTTP |
| model-api | 8002 | 8002 | HTTP |
| web-frontend | 80 | 3000 | HTTP |
| ocr-service | 8007 | 8007 | HTTP |
| behavior-service | 8008 | 8008 | HTTP |
| keycloak | 8080 | 8080 | HTTP |

### B. 环境变量参考

参考 `deploy/local/.env.example` 获取完整的环境变量列表。

### C. 相关文档

- [部署指南](./README.md)
- [硬件要求](./hardware-requirements.md)
- [测试用例](./../../tests/README.md)
