# 快速初始化演示数据指南

## 问题说明

以下页面默认没有数据：
- 数据源 (`/data/datasources`)
- 数据集 (`/datasets`)
- 元数据管理 (`/metadata`)
- 版本对比 (`/metadata/versions`)
- 特征存储 (`/data/features`)
- 数据标准 (`/data/standards`)
- 数据资产 (`/data/assets`)
- 数据服务 (`/data/services`)

## 解决方案

### 方法 1: 使用快速初始化脚本（推荐）

```bash
# 确保服务正在运行
cd deploy/local
docker-compose up -d

# 运行初始化脚本
python scripts/init-demo-data.py

# 查看数据状态
python scripts/init-demo-data.py --status

# 如果 API 地址不同，指定 URL
python scripts/init-demo-data.py --url http://localhost:8080
```

### 方法 2: 使用完整的测试数据生成器

```bash
# 生成全部测试数据
python -m scripts.test_data_generators generate --all

# 生成特定模块数据
python -m scripts.test_data_generators generate --module datasource,dataset

# 查看数据状态
python -m scripts.test_data_generators status

# 清理测试数据
python -m scripts.test_data_generators cleanup --all
```

### 方法 3: 通过前端界面手动创建

1. **创建数据源**:
   - 访问 `http://localhost:3000/data/datasources`
   - 点击"新建"按钮
   - 填写数据源信息（类型、主机、端口、数据库名等）
   - 点击"保存"

2. **创建数据集**:
   - 访问 `http://localhost:3000/datasets`
   - 点击"新建数据集"
   - 填写数据集信息
   - 点击"保存"

3. **创建特征**:
   - 访问 `http://localhost:3000/data/features`
   - 点击"创建特征"
   - 填写特征信息
   - 点击"保存"

## 初始化数据后

刷新浏览器页面，数据将显示在相应页面中。

## 已创建的示例数据

快速初始化脚本会创建：

| 类型 | 数量 | 示例 |
|------|------|------|
| 数据源 | 3 | MySQL 生产库、PostgreSQL 分析库、MongoDB 用户行为库 |
| 数据集 | 2 | 用户数据集、订单数据集 |
| 特征组 | 1 | 用户特征组 |
| 特征 | 2 | 用户活跃度、平均订单金额 |
| 数据标准 | 3 | 用户名规范、邮箱格式、手机号格式 |
| 数据资产 | 2 | 用户表、订单表 |
| 数据服务 | 1 | 用户查询API |

## 故障排除

### 服务无法连接

```bash
# 检查服务状态
docker-compose ps

# 重启服务
docker-compose restart data-api

# 查看服务日志
docker-compose logs -f data-api
```

### API 返回 401/403 认证错误

说明需要登录认证。在开发环境，可以：

1. 先登录系统获取 token
2. 或者在后端暂时关闭认证要求

### 数据库表不存在

```bash
# 初始化数据库表
docker-compose exec data-api python -c "
from services.data_api.src.main import db_manager
from services.data_api.models import *
db_manager.create_all_tables()
"
```

## 相关文件

- 初始化脚本: `scripts/init-demo-data.py`
- 测试数据生成器: `scripts/test_data_generators/`
- API 接口: `services/data-api/src/main.py`
- 数据模型: `services/data-api/models/`
