# Alldata API

数据治理与开发平台 API 服务。

## 功能

- 数据集 CRUD 操作
- 元数据管理
- MinIO 文件存储集成
- SQL 查询执行
- JWT 认证授权
- Prometheus 指标埋点

## 配置

### 环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `MYSQL_HOST` | MySQL 主机 | `localhost` |
| `MYSQL_PORT` | MySQL 端口 | `3306` |
| `MYSQL_USER` | MySQL 用户 | `one_data` |
| `MYSQL_PASSWORD` | MySQL 密码 | *必需* |
| `MYSQL_DATABASE` | 数据库名 | `one_data` |
| `MINIO_ENDPOINT` | MinIO 端点 | `localhost:9000` |
| `MINIO_ACCESS_KEY` | MinIO 访问密钥 | *必需* |
| `MINIO_SECRET_KEY` | MinIO 密钥 | *必需* |
| `AUTH_MODE` | 是否启用认证 | `true` |
| `JWT_SECRET_KEY` | JWT 密钥 | *必需* |
| `PORT` | 服务端口 | `8080` |

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

- `GET /api/v1/health` - 健康检查
- `GET /api/v1/datasets` - 列出数据集
- `POST /api/v1/datasets` - 创建数据集
- `GET /api/v1/datasets/{id}` - 获取数据集详情
- `PUT /api/v1/datasets/{id}` - 更新数据集
- `DELETE /api/v1/datasets/{id}` - 删除数据集
- `POST /api/v1/query/execute` - 执行 SQL 查询
- `GET /api/v1/metadata/databases` - 列出数据库
- `GET /api/v1/metadata/databases/{db}/tables` - 列出表
