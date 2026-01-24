# OpenAI Proxy

OpenAI 兼容的代理服务，提供统一的 LLM API 接口。

## 功能

- OpenAI API 兼容接口
- 多模型支持（OpenAI、Azure、本地模型）
- 请求路由和负载均衡
- 速率限制
- Token 计数
- 请求日志

## 配置

### 环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `OPENAI_API_KEY` | OpenAI API 密钥 | *可选* |
| `OPENAI_BASE_URL` | OpenAI API 基础 URL | `https://api.openai.com/v1` |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI 密钥 | *可选* |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI 端点 | *可选* |
| `DEFAULT_MODEL` | 默认模型 | `gpt-4o-mini` |
| `RATE_LIMIT_RPM` | 每分钟请求限制 | `60` |
| `PORT` | 服务端口 | `8000` |

## 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 运行服务
uvicorn main:app --host 0.0.0.0 --port 8000

# 运行测试
pytest tests/
```

## API 端点

- `GET /health` - 健康检查
- `GET /v1/models` - 列出可用模型
- `POST /v1/chat/completions` - 聊天补全
- `POST /v1/completions` - 文本补全
- `POST /v1/embeddings` - 文本嵌入

## 使用示例

```python
import openai

client = openai.OpenAI(
    api_key="your-api-key",
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)
print(response.choices[0].message.content)
```
