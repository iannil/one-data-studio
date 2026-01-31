# Phase 1-3 集成组件用户指南

> 本文档介绍 Phase 1-3 技术优化中新增的组件使用方法。

## 目录

1. [Label Studio 数据标注](#1-label-studio-数据标注)
2. [Great Expectations 数据质量](#2-great-expectations-数据质量)
3. [Ollama LLM 后端](#3-ollama-llm-后端)
4. [Apache Hop ETL 引擎](#4-apache-hop-etl-引擎)
5. [ShardingSphere 透明脱敏](#5-shardingsphere-透明脱敏)
6. [监控指标与 Grafana](#6-监控指标与-grafana)

---

## 1. Label Studio 数据标注

### 1.1 概述

Label Studio 用于 SFT 微调数据准备、OCR 结果校验、NER 标注等场景。

### 1.2 启动服务

```bash
# Docker Compose 启动（包含 labeling profile）
docker-compose --profile labeling up -d label-studio

# 验证服务
curl http://localhost:8085/health
```

### 1.3 创建标注项目

**通过 Model-API 代理层**:

```bash
# 创建 NER 标注项目
curl -X POST http://localhost:8002/api/v1/labeling/projects \
  -H "Content-Type: application/json" \
  -d '{
    "title": "NER 标注项目",
    "label_config": "<View><Labels name=\"label\" toName=\"text\"><Label value=\"PER\"/><Label value=\"ORG\"/><Label value=\"LOC\"/></Labels><Text name=\"text\" value=\"$text\"/></View>"
  }'
```

### 1.4 导入标注任务

```bash
# 从文件导入
curl -X POST http://localhost:8002/api/v1/labeling/projects/1/import \
  -H "Content-Type: application/json" \
  -d '{
    "tasks": [
      {"data": {"text": "北京是中国首都"}},
      {"data": {"text": "张三在阿里巴巴工作"}}
    ]
  }'
```

### 1.5 导出标注结果

```bash
# 导出 JSON 格式
curl http://localhost:8002/api/v1/labeling/projects/1/export?format=JSON

# 导出为 SFT 训练格式
curl http://localhost:8002/api/v1/labeling/projects/1/export?format=SFT
```

### 1.6 OCR 校验流程

1. OCR 服务处理图片，生成识别结果
2. 将 OCR 结果导入 Label Studio 作为预标注
3. 人工校验并修正错误
4. 导出校验后的数据用于训练

---

## 2. Great Expectations 数据质量

### 2.1 概述

Great Expectations (GE) 提供 300+ 内置数据质量规则，与 ETL 流程联动实现自动校验。

### 2.2 支持的期望类型

| 类型 | 示例 | 说明 |
|------|------|------|
| 完整性 | `expect_column_values_to_not_be_null` | 非空校验 |
| 唯一性 | `expect_column_values_to_be_unique` | 唯一性校验 |
| 格式 | `expect_column_values_to_match_regex` | 正则匹配 |
| 范围 | `expect_column_values_to_be_between` | 数值范围 |
| 集合 | `expect_column_values_to_be_in_set` | 枚举值校验 |

### 2.3 创建质量规则

```bash
# 创建 Expectation Suite
curl -X POST http://localhost:8001/api/v1/quality/expectation-suites \
  -H "Content-Type: application/json" \
  -d '{
    "suite_name": "user_data_suite",
    "data_asset_name": "users",
    "expectations": [
      {
        "expectation_type": "expect_column_values_to_not_be_null",
        "kwargs": {"column": "email"}
      },
      {
        "expectation_type": "expect_column_values_to_match_regex",
        "kwargs": {"column": "phone", "regex": "^1[3-9]\\d{9}$"}
      }
    ]
  }'
```

### 2.4 执行质量校验

```bash
# 手动触发校验
curl -X POST http://localhost:8001/api/v1/quality/validate \
  -H "Content-Type: application/json" \
  -d '{
    "suite_name": "user_data_suite",
    "database": "production",
    "table": "users"
  }'
```

### 2.5 查看质量报告

```bash
# 获取校验结果
curl http://localhost:8001/api/v1/quality/validations/latest?suite=user_data_suite

# 响应示例
{
  "success": false,
  "statistics": {
    "evaluated_expectations": 10,
    "successful_expectations": 8,
    "unsuccessful_expectations": 2
  },
  "results": [
    {
      "expectation_type": "expect_column_values_to_not_be_null",
      "column": "email",
      "success": false,
      "unexpected_count": 150,
      "unexpected_percent": 1.5
    }
  ]
}
```

### 2.6 ETL 联动

在 ETL 任务配置中启用 GE 校验：

```json
{
  "name": "sync_users",
  "enable_quality_check": true,
  "quality_suite": "user_data_suite",
  "quality_action_on_failure": "warn"  // warn | stop | skip_row
}
```

---

## 3. Ollama LLM 后端

### 3.1 概述

Ollama 作为轻量级 LLM 后端，适用于开发测试环境和资源受限场景。

### 3.2 启动服务

```bash
# Docker Compose 启动
docker-compose --profile llm up -d ollama

# 拉取模型
docker exec -it one-data-ollama ollama pull qwen2.5:7b
```

### 3.3 切换 LLM 后端

**方式一：环境变量配置**

```bash
# 在 .env 文件中配置
LLM_BACKEND=ollama  # 可选：vllm | ollama | openai

# 或启动时指定
docker-compose up -d openai-proxy LLM_BACKEND=ollama
```

**方式二：API 调用时指定**

```bash
# 使用 Ollama 后端
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-LLM-Backend: ollama" \
  -d '{
    "model": "qwen2.5:7b",
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

### 3.4 查看可用模型

```bash
# 列出 Ollama 已安装模型
curl http://localhost:8000/v1/models?backend=ollama

# 列出所有后端的模型
curl http://localhost:8000/v1/models
```

### 3.5 后端健康状态

```bash
curl http://localhost:8000/v1/backends/health

# 响应示例
{
  "vllm": {"healthy": true, "models": ["Qwen2.5-1.5B-Instruct"]},
  "ollama": {"healthy": true, "models": ["qwen2.5:7b", "llama3:8b"]},
  "openai": {"healthy": false, "error": "API key not configured"}
}
```

---

## 4. Apache Hop ETL 引擎

### 4.1 概述

Apache Hop 作为 Kettle 的现代替代，与现有 Kettle 形成双引擎架构。

### 4.2 启动服务

```bash
# Docker Compose 启动（包含 etl profile）
docker-compose --profile etl up -d hop-server

# 验证服务
curl http://localhost:8182/api/v1/server/status
```

### 4.3 引擎选择

| engine_type | 行为 |
|-------------|------|
| `auto` | 优先 Hop，不可用时回退 Kettle |
| `hop` | 仅使用 Hop |
| `kettle` | 仅使用 Kettle |

### 4.4 创建 ETL 任务

```bash
# 使用 Hop 引擎
curl -X POST http://localhost:8001/api/v1/etl/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sync_users",
    "source_database": "source_db",
    "source_table": "users",
    "target_database": "target_db",
    "target_table": "users_cleaned",
    "engine_type": "hop",
    "enable_ai_cleaning": true
  }'
```

### 4.5 查看引擎状态

```bash
# 查看所有引擎状态
curl http://localhost:8001/api/v1/etl/engines

# 响应示例
{
  "hop": {
    "enabled": true,
    "status": "available",
    "pipelines_active": 3
  },
  "kettle": {
    "enabled": true,
    "status": "available",
    "transformations_active": 1
  }
}
```

### 4.6 Hop Server 详情

```bash
curl http://localhost:8001/api/v1/etl/hop-status

# 响应示例
{
  "status": "running",
  "version": "2.8.0",
  "pipelines": [
    {"name": "sync_users", "status": "Finished", "rows_written": 10000}
  ],
  "workflows": []
}
```

---

## 5. ShardingSphere 透明脱敏

### 5.1 概述

ShardingSphere 在 SQL 代理层实现透明脱敏，对应用无侵入。

### 5.2 启动服务

```bash
# Docker Compose 启动（包含 security profile）
docker-compose --profile security up -d shardingsphere-proxy

# 验证服务
curl http://localhost:8001/api/v1/masking/shardingsphere/status
```

### 5.3 从敏感扫描生成规则

```bash
# 先执行敏感扫描
curl -X POST http://localhost:8001/api/v1/sensitivity/scan \
  -H "Content-Type: application/json" \
  -d '{"database": "test_db", "table": "users"}'

# 从扫描结果生成脱敏规则
curl -X POST http://localhost:8001/api/v1/masking/shardingsphere/generate-rules \
  -H "Content-Type: application/json" \
  -d '{
    "database": "test_db",
    "table": "users",
    "sensitivity_results": [
      {"column_name": "phone", "sensitivity_type": "phone"},
      {"column_name": "email", "sensitivity_type": "email"},
      {"column_name": "id_card", "sensitivity_type": "id_card"}
    ]
  }'
```

### 5.4 应用脱敏规则

```bash
curl -X POST http://localhost:8001/api/v1/masking/shardingsphere/apply-rules \
  -H "Content-Type: application/json" \
  -d '{
    "database": "test_db",
    "rules_sql": "CREATE MASK RULE t_user (COLUMNS((NAME=phone, TYPE(NAME=MASK_FIRST_N_LAST_M, PROPERTIES(first-n=3, last-m=4, replace-char=*)))));"
  }'
```

### 5.5 查看已生效规则

```bash
curl http://localhost:8001/api/v1/masking/shardingsphere/rules/test_db

# 响应示例
{
  "database": "test_db",
  "rules": [
    {
      "table": "users",
      "column": "phone",
      "algorithm": "MASK_FIRST_N_LAST_M",
      "params": {"first-n": 3, "last-m": 4}
    },
    {
      "table": "users",
      "column": "email",
      "algorithm": "MASK_BEFORE_SPECIAL_CHARS",
      "params": {"special-chars": "@"}
    }
  ]
}
```

### 5.6 脱敏效果示例

| 原始值 | 脱敏后 | 算法 |
|--------|--------|------|
| 13812345678 | 138****5678 | MASK_FIRST_N_LAST_M |
| test@example.com | ****@example.com | MASK_BEFORE_SPECIAL_CHARS |
| 310123199001011234 | 310123********1234 | MASK_FIRST_N_LAST_M |

### 5.7 通过 ShardingSphere 查询

```bash
# 连接 ShardingSphere Proxy（MySQL 协议）
mysql -h localhost -P 3307 -u root -p

# 查询将自动脱敏
SELECT phone, email FROM users LIMIT 5;
-- 返回: 138****5678, ****@example.com
```

---

## 6. 监控指标与 Grafana

### 6.1 概述

所有 Phase 1-3 组件均已集成 Prometheus 指标，可通过 Grafana 监控。

### 6.2 指标端点

| 服务 | 端点 | 说明 |
|------|------|------|
| Data API | `/metrics` | ETL、质量、脱敏指标 |
| Model API | `/metrics` | 标注、LLM 指标 |
| OpenAI Proxy | `/metrics` | LLM 后端指标 |

### 6.3 主要指标

**ETL 指标**:
- `etl_executions_total{engine, status}` - 执行次数
- `etl_execution_duration_seconds{engine}` - 执行耗时
- `etl_rows_processed_total{engine}` - 处理行数
- `etl_engine_health{engine}` - 引擎健康状态 (1=健康)

**数据质量指标**:
- `quality_validations_total{engine, result}` - 校验次数
- `quality_validation_duration_seconds{engine}` - 校验耗时
- `quality_pass_rate{suite}` - 规则通过率

**LLM 指标**:
- `llm_requests_total{backend, model, status}` - 请求次数
- `llm_request_duration_seconds{backend}` - 请求延迟
- `llm_tokens_total{backend, type}` - Token 使用量
- `llm_backend_health{backend}` - 后端健康状态

**脱敏指标**:
- `masking_queries_total{database}` - 脱敏查询次数
- `masking_query_duration_seconds{database}` - 查询延迟
- `masking_proxy_health` - 代理健康状态

**标注指标**:
- `labeling_tasks_total{project}` - 任务创建数
- `labeling_annotations_total{project}` - 标注提交数
- `labeling_tasks_pending{project}` - 待处理任务数

### 6.4 Grafana Dashboard

访问 Grafana: `http://localhost:3001`

导入 Dashboard:
1. 进入 Dashboards -> Import
2. 上传 `deploy/kubernetes/infrastructure/monitoring/grafana/dashboards/integration-components.json`

Dashboard 包含:
- ETL 引擎执行监控面板
- 数据质量通过率仪表盘
- LLM 后端健康与延迟图表
- 透明脱敏查询监控
- 数据标注进度追踪

### 6.5 告警配置示例

```yaml
# Prometheus 告警规则
groups:
- name: phase123_alerts
  rules:
  - alert: ETLEngineUnhealthy
    expr: etl_engine_health == 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "ETL 引擎 {{ $labels.engine }} 不健康"

  - alert: LLMBackendDown
    expr: llm_backend_health == 0
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "LLM 后端 {{ $labels.backend }} 离线"

  - alert: QualityPassRateLow
    expr: quality_pass_rate < 0.9
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "数据质量通过率低于 90%"
```

---

## 附录：快速参考

### 环境变量配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_BACKEND` | `vllm` | LLM 后端 (vllm/ollama/openai) |
| `ETL_ENGINE` | `auto` | ETL 引擎 (auto/hop/kettle) |
| `HOP_ENABLED` | `false` | 启用 Hop Server |
| `SHARDINGSPHERE_ENABLED` | `false` | 启用 ShardingSphere |
| `GE_ENABLED` | `false` | 启用 Great Expectations |
| `LABEL_STUDIO_ENABLED` | `false` | 启用 Label Studio |

### Docker Compose Profiles

```bash
# 启用所有 Phase 1-3 组件
docker-compose --profile etl --profile security --profile labeling --profile llm up -d

# 仅启用 ETL 组件 (Hop + Kettle)
docker-compose --profile etl up -d

# 仅启用安全组件 (ShardingSphere)
docker-compose --profile security up -d
```

### API 端点汇总

| 功能 | 方法 | 端点 |
|------|------|------|
| ETL 引擎状态 | GET | `/api/v1/etl/engines` |
| Hop 状态 | GET | `/api/v1/etl/hop-status` |
| 创建 ETL 任务 | POST | `/api/v1/etl/orchestrate` |
| 质量校验 | POST | `/api/v1/quality/validate` |
| 脱敏状态 | GET | `/api/v1/masking/shardingsphere/status` |
| 生成脱敏规则 | POST | `/api/v1/masking/shardingsphere/generate-rules` |
| 应用脱敏规则 | POST | `/api/v1/masking/shardingsphere/apply-rules` |
| LLM 后端健康 | GET | `/v1/backends/health` |
| 标注项目列表 | GET | `/api/v1/labeling/projects` |

---

> 更新时间：2026-01-31
