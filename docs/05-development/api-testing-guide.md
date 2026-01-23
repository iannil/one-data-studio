# API 测试指南

本文档提供 ONE-DATA-STUDIO 平台各 API 接口的测试用例和测试方法。

---

## 测试环境准备

### 1.1 获取认证 Token

```bash
# 方式 1: 使用客户端凭证获取 Token
CLIENT_ID="one-data-client"
CLIENT_SECRET="your-client-secret"
TOKEN_URL="https://keycloak.example.com/realms/one-data/protocol/openid-connect/token"

TOKEN=$(curl -s -X POST $TOKEN_URL \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET" \
  -d "grant_type=client_credentials" | jq -r '.access_token')

echo $TOKEN
```

### 1.2 配置测试环境变量

```bash
# API 端点
export ALDATA_API_URL="http://localhost:8080"
export CUBE_API_URL="http://localhost:8000"
export BISHENG_API_URL="http://localhost:8081"

# 认证信息（如需要）
export API_TOKEN="your-api-token"

# 通用 curl 配置
export CURL_OPTS="-s -H 'Content-Type: application/json'"
export CURL_AUTH="-H 'Authorization: Bearer $API_TOKEN'"
```

### 1.3 安装测试工具

```bash
# jq - JSON 处理工具
brew install jq  # macOS
# apt install jq # Ubuntu

# httpie - 更友好的 HTTP 客户端
brew install httpie

# Postman（可选）
# 下载: https://www.postman.com/downloads/
```

---

## 集成点一：Alldata API 测试

### 2.1 健康检查

```bash
curl $ALDATA_API_URL/api/v1/health
```

**预期响应：**
```json
{
    "code": 0,
    "message": "healthy"
}
```

### 2.2 数据集注册

```bash
curl -X POST $ALDATA_API_URL/api/v1/datasets \
  -H "Content-Type: application/json" \
  $CURL_AUTH \
  -d '{
    "name": "test_dataset_v1.0",
    "description": "测试数据集",
    "storage_type": "s3",
    "storage_path": "s3://test-bucket/data/",
    "format": "parquet",
    "schema": {
        "columns": [
            {"name": "id", "type": "INT64", "description": "ID"},
            {"name": "value", "type": "DOUBLE", "description": "值"}
        ]
    },
    "tags": ["test"]
}' | jq '.'
```

**验证点：**
- [ ] 返回 HTTP 200
- [ ] code 字段为 0
- [ ] 包含 dataset_id

### 2.3 查询数据集

```bash
# 获取数据集列表
curl $ALDATA_API_URL/api/v1/datasets $CURL_AUTH | jq '.'

# 获取特定数据集
DATASET_ID="ds-001"
curl $ALDATA_API_URL/api/v1/datasets/$DATASET_ID $CURL_AUTH | jq '.'
```

**验证点：**
- [ ] 列表包含注册的数据集
- [ ] schema 信息正确

### 2.4 更新数据集

```bash
curl -X PUT $ALDATA_API_URL/api/v1/datasets/$DATASET_ID \
  -H "Content-Type: application/json" \
  $CURL_AUTH \
  -d '{
    "description": "更新后的描述",
    "tags": ["test", "updated"]
}' | jq '.'
```

### 2.5 删除数据集

```bash
curl -X DELETE $ALDATA_API_URL/api/v1/datasets/$DATASET_ID \
  $CURL_AUTH | jq '.'
```

### 2.6 获取访问凭证

```bash
curl -X POST $ALDATA_API_URL/api/v1/datasets/$DATASET_ID/credentials \
  -H "Content-Type: application/json" \
  $CURL_AUTH \
  -d '{
    "purpose": "training",
    "duration_seconds": 3600
}' | jq '.'
```

**验证点：**
- [ ] 返回临时凭证
- [ ] expires_at 时间正确

---

## 集成点二：Cube 模型服务 API 测试

### 3.1 列出可用模型

```bash
curl $CUBE_API_URL/v1/models $CURL_AUTH | jq '.'
```

**预期响应：**
```json
{
    "object": "list",
    "data": [
        {
            "id": "Qwen/Qwen-0.5B-Chat",
            "object": "model",
            "owned_by": "cube-studio"
        }
    ]
}
```

### 3.2 聊天补全（非流式）

```bash
curl -X POST $CUBE_API_URL/v1/chat/completions \
  -H "Content-Type: application/json" \
  $CURL_AUTH \
  -d '{
    "model": "Qwen/Qwen-0.5B-Chat",
    "messages": [
        {"role": "system", "content": "你是一个智能助手。"},
        {"role": "user", "content": "北京是中国的首都吗？"}
    ],
    "temperature": 0.7,
    "max_tokens": 100
}' | jq '.'
```

**验证点：**
- [ ] 返回 HTTP 200
- [ ] choices 数组非空
- [ ] finish_reason 为 "stop"
- [ ] usage 统计正确

### 3.3 聊天补全（流式）

```bash
curl -X POST $CUBE_API_URL/v1/chat/completions \
  -H "Content-Type: application/json" \
  $CURL_AUTH \
  -d '{
    "model": "Qwen/Qwen-0.5B-Chat",
    "messages": [
        {"role": "user", "content": "讲个笑话"}
    ],
    "stream": true
}'
```

**验证点：**
- [ ] 返回 SSE 流
- [ ] 每个 data 块格式正确
- [ ] 最后返回 `data: [DONE]`

### 3.4 文本补全

```bash
curl -X POST $CUBE_API_URL/v1/completions \
  -H "Content-Type: application/json" \
  $CURL_AUTH \
  -d '{
    "model": "Qwen/Qwen-0.5B-Chat",
    "prompt": "人工智能是",
    "max_tokens": 50
}' | jq '.'
```

### 3.5 嵌入向量

```bash
curl -X POST $CUBE_API_URL/v1/embeddings \
  -H "Content-Type: application/json" \
  $CURL_AUTH \
  -d '{
    "model": "bge-base-zh",
    "input": ["这是一段测试文本"]
}' | jq '.'
```

**验证点：**
- [ ] 返回 embedding 数组
- [ ] 维度符合模型规格（如 768）

### 3.6 模型部署

```bash
curl -X POST $CUBE_API_URL/api/v1/models/deploy \
  -H "Content-Type: application/json" \
  $CURL_AUTH \
  -d '{
    "model_name": "qwen-14b-chat",
    "model_path": "s3://models/qwen-14b/",
    "replicas": 1,
    "resources": {
        "gpu": {"count": 1},
        "cpu": "4",
        "memory": "16Gi"
    }
}' | jq '.'
```

### 3.7 查询模型状态

```bash
MODEL_ID="model-123"
curl $CUBE_API_URL/api/v1/models/$MODEL_ID/status \
  $CURL_AUTH | jq '.'
```

---

## 集成点三：元数据 API 测试

### 4.1 获取数据库列表

```bash
curl $ALDATA_API_URL/api/v1/metadata/databases \
  $CURL_AUTH | jq '.'
```

### 4.2 获取表列表

```bash
curl $ALDATA_API_URL/api/v1/metadata/databases/sales_dw/tables \
  $CURL_AUTH | jq '.'
```

### 4.3 获取表详情

```bash
curl $ALDATA_API_URL/api/v1/metadata/databases/sales_dw/tables/orders \
  $CURL_AUTH | jq '.'
```

**验证点：**
- [ ] 返回完整的表结构
- [ ] columns 数组包含字段信息
- [ ] relations 包含关联关系

### 4.4 智能表搜索

```bash
curl -X POST $ALDATA_API_URL/api/v1/metadata/tables/search \
  -H "Content-Type: application/json" \
  $CURL_AUTH \
  -d '{
    "query": "销售订单",
    "limit": 5
}' | jq '.'
```

### 4.5 SQL 验证

```bash
curl -X POST $ALDATA_API_URL/api/v1/query/validate \
  -H "Content-Type: application/json" \
  $CURL_AUTH \
  -d '{
    "database": "sales_dw",
    "sql": "SELECT COUNT(*) FROM orders WHERE created_at >= ?"
}' | jq '.'
```

**验证点：**
- [ ] valid 字段为 true
- [ ] 返回参数信息

### 4.6 SQL 执行

```bash
curl -X POST $ALDATA_API_URL/api/v1/query/execute \
  -H "Content-Type: application/json" \
  $CURL_AUTH \
  -d '{
    "database": "sales_dw",
    "sql": "SELECT COUNT(*) as total, SUM(amount) as sum FROM orders",
    "timeout_seconds": 30
}' | jq '.'
```

**验证点：**
- [ ] status 为 "completed"
- [ ] rows 包含查询结果
- [ ] execution_time_ms 合理

---

## 端到端集成测试

### 5.1 完整数据流测试

```bash
#!/bin/bash
# 端到端测试脚本

echo "=== 端到端集成测试 ==="

# 1. Alldata 注册数据集
echo "[1/5] 注册数据集..."
DS_RESPONSE=$(curl -s -X POST $ALDATA_API_URL/api/v1/datasets \
  -H "Content-Type: application/json" \
  $CURL_AUTH \
  -d '{
    "name": "e2e_test_dataset",
    "storage_path": "s3://test/e2e/",
    "format": "csv"
}')

DATASET_ID=$(echo $DS_RESPONSE | jq -r '.data.dataset_id')
echo "数据集 ID: $DATASET_ID"

# 2. Cube 调用模型
echo "[2/5] 测试模型服务..."
CHAT_RESPONSE=$(curl -s -X POST $CUBE_API_URL/v1/chat/completions \
  -H "Content-Type: application/json" \
  $CURL_AUTH \
  -d '{
    "model": "Qwen/Qwen-0.5B-Chat",
    "messages": [{"role": "user", "content": "你好"}],
    "max_tokens": 50
}')

REPLY=$(echo $CHAT_RESPONSE | jq -r '.choices[0].message.content')
echo "模型回复: $REPLY"

# 3. Bisheng 调用数据集
echo "[3/5] 查询数据集..."
curl -s $BISHENG_API_URL/api/v1/datasets | jq '.'

# 4. Bisheng 调用模型
echo "[4/5] 跨平台调用模型..."
curl -s -X POST $BISHENG_API_URL/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "测试消息"}' | jq '.'

# 5. 清理测试数据
echo "[5/5] 清理测试数据..."
curl -s -X DELETE $ALDATA_API_URL/api/v1/datasets/$DATASET_ID \
  $CURL_AUTH | jq '.'

echo "=== 测试完成 ==="
```

---

## 自动化测试

### 6.1 Pytest 测试套件

```python
# test_api.py
import pytest
import requests

class TestAlldataAPI:
    base_url = "http://localhost:8080"

    def test_health(self):
        """测试健康检查接口"""
        response = requests.get(f"{self.base_url}/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    def test_create_dataset(self):
        """测试创建数据集"""
        payload = {
            "name": "pytest_dataset",
            "storage_path": "s3://test/",
            "format": "csv"
        }
        response = requests.post(
            f"{self.base_url}/api/v1/datasets",
            json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "dataset_id" in data["data"]

    def test_list_datasets(self):
        """测试查询数据集列表"""
        response = requests.get(f"{self.base_url}/api/v1/datasets")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert isinstance(data["data"], list)


class TestCubeAPI:
    base_url = "http://localhost:8000"

    def test_list_models(self):
        """测试列出模型"""
        response = requests.get(f"{self.base_url}/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "list"

    def test_chat_completion(self):
        """测试聊天补全"""
        payload = {
            "model": "Qwen/Qwen-0.5B-Chat",
            "messages": [{"role": "user", "content": "你好"}],
            "max_tokens": 50
        }
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["choices"]) > 0
```

运行测试：
```bash
pip install pytest requests
pytest test_api.py -v
```

### 6.2 Postman Collection

导出为 Postman Collection 后可导入 Postman 使用：

```json
{
    "info": {
        "name": "ONE-DATA-STUDIO API Tests",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    },
    "variable": [
        {
            "key": "base_url",
            "value": "http://localhost:8080"
        },
        {
            "key": "api_token",
            "value": "your-token-here"
        }
    ],
    "item": [
        {
            "name": "Alldata API",
            "item": [
                {
                    "name": "Health Check",
                    "request": {
                        "method": "GET",
                        "url": "{{base_url}}/api/v1/health"
                    }
                },
                {
                    "name": "List Datasets",
                    "request": {
                        "method": "GET",
                        "header": [
                            {
                                "key": "Authorization",
                                "value": "Bearer {{api_token}}"
                            }
                        ],
                        "url": "{{base_url}}/api/v1/datasets"
                    }
                }
            ]
        }
    ]
}
```

---

## 性能测试

### 7.1 使用 Apache Bench

```bash
# 安装
brew install httpd  # macOS 包含 ab

# 测试健康检查接口
ab -n 1000 -c 10 \
   -H "Authorization: Bearer $API_TOKEN" \
   $ALDATA_API_URL/api/v1/health

# 测试聊天接口（创建 JSON 文件）
cat << 'EOF' > chat_payload.json
{
    "model": "Qwen/Qwen-0.5B-Chat",
    "messages": [{"role": "user", "content": "你好"}],
    "max_tokens": 50
}
EOF

ab -n 100 -c 5 -p chat_payload.json -T application/json \
   -H "Authorization: Bearer $API_TOKEN" \
   $CUBE_API_URL/v1/chat/completions
```

### 7.2 使用 wrk

```bash
# 安装
brew install wrk

# 测试 GET 接口
wrk -t4 -c100 -d30s --latency \
    -H "Authorization: Bearer $API_TOKEN" \
    $ALDATA_API_URL/api/v1/datasets
```

---

## 测试检查清单

### 功能测试

- [ ] 所有健康检查接口返回正常
- [ ] 数据集 CRUD 操作正常
- [ ] 模型推理接口返回正确结果
- [ ] 元数据查询返回正确结构
- [ ] SQL 验证和执行正常工作

### 集成测试

- [ ] Alldata → Cube 数据集可读取
- [ ] Cube → Bisheng 模型调用成功
- [ ] Alldata → Bisheng 元数据查询成功
- [ ] 端到端流程完整通过

### 非功能测试

- [ ] 认证/鉴权正常工作
- [ ] 错误响应符合规范
- [ ] 接口响应时间在可接受范围
- [ ] 限流策略生效
- [ ] 日志正常输出

---

## 更新记录

| 日期 | 版本 | 更新内容 | 更新人 |
|------|------|----------|--------|
| 2024-01-23 | v1.0 | 初始版本，API 测试指南 | Claude |
