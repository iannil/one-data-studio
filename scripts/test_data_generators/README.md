# 测试数据生成器

用户全生命周期测试数据的模块化生成系统。

## 概述

本系统提供了一套完整的测试数据生成工具，支持225个测试用例的数据需求，覆盖5种用户角色、10个业务领域的数据生成。

## 功能特性

- **模块化设计**: 每个生成器可独立使用
- **依赖管理**: 自动解析和满足模块间的依赖关系
- **幂等性**: 支持重复生成而不会产生重复数据
- **敏感数据**: 完整的敏感字段覆盖（手机、身份证、银行卡、邮箱）
- **多存储支持**: MySQL、MinIO、Milvus、Redis
- **Mock模式**: 无需数据库连接即可测试

## 目录结构

```
scripts/test_data_generators/
├── __init__.py                 # 统一入口
├── base.py                     # 基础类和工具
├── config.py                   # 配置定义
├── cli.py                      # 命令行接口
├── generators/                 # 数据生成器
│   ├── user_generator.py       # 用户和权限
│   ├── datasource_generator.py # 数据源和元数据
│   ├── etl_generator.py        # ETL任务
│   ├── sensitive_generator.py  # 敏感数据
│   ├── asset_generator.py      # 数据资产
│   ├── lineage_generator.py    # 数据血缘
│   ├── ml_generator.py         # ML模型
│   ├── knowledge_generator.py  # 知识库
│   ├── bi_generator.py         # BI报表
│   └── alert_generator.py      # 预警规则
├── storage/                    # 存储管理
│   ├── mysql_manager.py        # MySQL管理
│   ├── minio_manager.py        # MinIO管理
│   ├── milvus_manager.py       # Milvus管理
│   └── redis_manager.py        # Redis管理
└── validators/                 # 数据验证
    └── data_validator.py       # 完整性验证
```

## 快速开始

### 安装依赖

```bash
pip install pymysql redis
# 可选: MinIO和Milvus支持
pip install minio pymilvus
```

### 配置环境变量

```bash
# MySQL配置
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=your_password
export MYSQL_DATABASE=onedata

# Redis配置（可选）
export REDIS_HOST=localhost
export REDIS_PORT=6379

# MinIO配置（可选）
export MINIO_ENDPOINT=localhost:9000
export MINIO_ACCESS_KEY=minioadmin
export MINIO_SECRET_KEY=minioadmin

# Milvus配置（可选）
export MILVUS_HOST=localhost
export MILVUS_PORT=19530
```

### 使用命令行接口

```bash
# 生成全部测试数据
python -m scripts.test_data_generators generate --all

# 生成指定模块
python -m scripts.test_data_generators generate --module user,datasource,etl

# 使用Mock模式（不连接数据库）
python -m scripts.test_data_generators generate --all --mock

# 清理测试数据
python -m scripts.test_data_generators cleanup --all

# 验证数据完整性
python -m scripts.test_data_generators validate

# 查看数据统计
python -m scripts.test_data_generators status
```

### 使用Python API

```python
from scripts.test_data_generators import (
    generate_all_data,
    GeneratorQuantities,
    get_mysql_manager,
)

# 自定义配置
config = GeneratorQuantities(
    data_administrator_count=3,
    datasource_count=10,
    etl_task_count=30,
)

# 生成数据
data = generate_all_data(config)

# 或单独使用某个生成器
from scripts.test_data_generators import UserGenerator

user_gen = UserGenerator(config)
users = user_gen.generate()
```

## 生成器详情

### UserGenerator - 用户生成器

生成用户、角色、权限数据。

| 数据 | 数量 | 说明 |
|------|------|------|
| users | 23+ | 5种角色用户 |
| roles | 5 | 系统角色 |
| permissions | 60+ | 角色权限 |
| user_roles | 23+ | 用户角色关联 |

**角色类型**:
- `data_administrator` - 数据管理员
- `data_engineer` - 数据工程师
- `ai_developer` - AI开发者
- `data_analyst` - 数据分析师
- `system_administrator` - 系统管理员

### DatasourceGenerator - 数据源生成器

生成数据源和完整元数据。

| 数据 | 数量 | 说明 |
|------|------|------|
| datasources | 8 | MySQL/PostgreSQL/MongoDB等 |
| databases | 14 | 元数据库 |
| tables | 140 | 元数据表 |
| columns | 1200+ | 元数据列（含敏感标注） |

**敏感字段覆盖**:
- 手机号: 20+ 列
- 身份证: 15+ 列
- 银行卡: 10+ 列
- 邮箱: 25+ 列

### ETLGenerator - ETL任务生成器

生成ETL任务和执行日志。

| 数据 | 数量 | 说明 |
|------|------|------|
| etl_tasks | 20 | 同步/抽取/加载/转换/归档 |
| etl_task_logs | 60+ | 执行日志 |

### SensitiveGenerator - 敏感数据生成器

生成敏感数据扫描和脱敏规则。

| 数据 | 数量 | 说明 |
|------|------|------|
| scan_tasks | 5 | 扫描任务 |
| scan_results | 75 | 扫描结果 |
| masking_rules | 10 | 脱敏规则 |

### AssetGenerator - 数据资产生成器

生成数据资产和价值历史。

| 数据 | 数量 | 说明 |
|------|------|------|
| assets | 140 | 数据资产（S/A/B/C等级） |
| categories | 10 | 资产分类 |
| value_history | 280 | 价值历史 |

### LineageGenerator - 数据血缘生成器

生成数据血缘边和事件。

| 数据 | 数量 | 说明 |
|------|------|------|
| lineage_edges | 38 | 血缘边 |
| lineage_events | 38 | 血缘事件 |

### MLGenerator - ML模型生成器

生成机器学习模型相关数据。

| 数据 | 数量 | 说明 |
|------|------|------|
| ml_models | 7 | 分类/回归/推荐等模型 |
| model_versions | 15 | 模型版本 |
| model_deployments | 10 | 模型部署 |

### KnowledgeGenerator - 知识库生成器

生成知识库和向量数据。

| 数据 | 数量 | 说明 |
|------|------|------|
| knowledge_bases | 3 | 知识库 |
| documents | 15 | 索引文档 |
| vectors | 150+ | 向量数据（需Milvus） |

### BIGenerator - BI报表生成器

生成BI仪表板和图表。

| 数据 | 数量 | 说明 |
|------|------|------|
| bi_dashboards | 3 | 仪表板 |
| bi_charts | 12 | 图表（线图/柱图/饼图等） |

### AlertGenerator - 预警规则生成器

生成预警规则和历史。

| 数据 | 数量 | 说明 |
|------|------|------|
| alert_rules | 7 | 预警规则 |
| alert_history | 70+ | 预警历史 |

## 数据关联

```
Users → Roles → Permissions
Users → DataSources → Databases → Tables → Columns
Tables → SensitivityScan → SensitivityResults
Tables → DataAssets
Tables → ETLTask → ETLLog
Tables → BIChart → BIDashboard
Tables → AlertRule
Tables → LineageEdge
Dataset → MLModel → ModelVersion → ModelDeployment
Users → KnowledgeBase → Document → MilvusVector
```

## 敏感数据脱敏

| 类型 | 列名模式 | 脱敏策略 | 示例 |
|------|----------|----------|------|
| 手机号 | phone, mobile | partial_mask | 138****1234 |
| 身份证 | id_card, idcard | partial_mask | 110101****1234 |
| 银行卡 | bank_card, card_number | partial_mask | 6222****1234 |
| 邮箱 | email | partial_mask | t***@domain.com |
| 密码 | password, passwd | sha256 | hash存储 |

## 验证标准

生成完成后，数据应满足：

1. **225个测试用例前置条件**: 所有测试用例的前置条件都能满足
2. **敏感字段覆盖**:
   - 手机号: 20+ 列
   - 身份证: 15+ 列
   - 银行卡: 10+ 列
   - 邮箱: 25+ 列
3. **数据关联完整**: ETL任务的源表/目标表存在，血缘节点有效
4. **多存储覆盖**: MySQL有数据，Milvus有向量，MinIO有文件

## 高级配置

### 自定义生成数量

```python
from scripts.test_data_generators import GeneratorQuantities

config = GeneratorQuantities(
    # 用户数量
    data_administrator_count=3,
    data_engineer_count=8,

    # 数据源数量
    datasource_count=10,
    tables_per_database=15,

    # ETL数量
    etl_task_count=30,

    # 资产数量
    asset_count=200,
)
```

### 自定义敏感数据模式

```python
from scripts.test_data_generators.config import SENSITIVE_PATTERNS

SENSITIVE_PATTERNS["custom_phone"] = SensitivePattern(
    name="custom_phone",
    description="自定义手机号",
    column_patterns=["mobile_phone", "contact_number"],
    sample_values=["13800138000"],
    sensitivity_level="confidential",
    mask_function="partial_mask",
)
```

## 故障排除

### 数据库连接失败

```bash
# 检查MySQL服务
mysql -h localhost -u root -p

# 使用Mock模式测试
python -m scripts.test_data_generators generate --all --mock
```

### 表不存在

生成器会检查表是否存在，如果表不存在会跳过保存。请确保数据库schema已创建。

### 权限问题

确保数据库用户有以下权限：
- SELECT, INSERT, UPDATE, DELETE
- CREATE, INDEX（如果需要创建表）

## 开发指南

### 添加新的生成器

1. 在 `generators/` 目录创建新文件
2. 继承 `BaseGenerator`
3. 实现 `generate()` 方法
4. 实现 `save()` 和 `cleanup()` 方法
5. 在 `generators/__init__.py` 中导出

```python
from ..base import BaseGenerator

class MyGenerator(BaseGenerator):
    def generate(self):
        data = [{"id": 1, "name": "test"}]
        self.store_data("my_data", data)
        return self.get_all_data()

    def save(self):
        if self.storage:
            # 保存到数据库
            pass

    def cleanup(self):
        if self.storage:
            # 清理数据
            pass
```

### 添加新的存储后端

1. 在 `storage/` 目录创建新文件
2. 实现与现有管理器相同的接口
3. 在 `storage/__init__.py` 中导出

## 许可

MIT License
