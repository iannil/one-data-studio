# Cube API

云原生 MLOps 平台 API 服务。

## 功能

- 模型服务管理
- 训练任务调度
- 模型版本管理
- 推理服务
- Kubernetes 集成

## 配置

### 环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `DATABASE_URL` | 数据库连接 URL | *必需* |
| `KUBERNETES_NAMESPACE` | K8s 命名空间 | `one-data-cube` |
| `MODEL_STORAGE_PATH` | 模型存储路径 | `/models` |
| `VLLM_ENDPOINT` | vLLM 服务端点 | `http://localhost:8000` |
| `PORT` | 服务端口 | `8082` |

## 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 运行服务
python app.py

# 运行测试
pytest tests/
```

## API 端点

### 模型管理
- `GET /api/v1/models` - 列出模型
- `POST /api/v1/models` - 注册模型
- `GET /api/v1/models/{id}` - 获取模型详情
- `DELETE /api/v1/models/{id}` - 删除模型

### 训练任务
- `GET /api/v1/training-jobs` - 列出训练任务
- `POST /api/v1/training-jobs` - 创建训练任务
- `GET /api/v1/training-jobs/{id}` - 获取任务详情
- `DELETE /api/v1/training-jobs/{id}` - 取消任务

### 推理服务
- `GET /api/v1/deployments` - 列出部署
- `POST /api/v1/deployments` - 创建部署
- `DELETE /api/v1/deployments/{id}` - 删除部署
- `POST /v1/chat/completions` - OpenAI 兼容推理

## 与其他服务集成

Cube API 与其他服务的集成：

- **Bisheng API**: 提供模型推理服务
- **Alldata API**: 获取训练数据集
- **MinIO**: 模型存储
