# 测试数据初始化脚本

本目录包含数据治理平台端到端测试所需的数据库初始化脚本和数据生成工具。

## 目录结构

```
scripts/test_data/
├── init_mysql_test_data.sql        # MySQL 测试数据初始化 SQL
├── init_postgres_test_data.sql     # PostgreSQL 测试数据初始化 SQL
├── init-postgres-databases.sh      # PostgreSQL 数据库创建脚本
├── generate_test_data.py           # Python 数据生成工具
└── README.md                       # 本文件
```

## 快速开始

### 方式一：使用 Docker Compose（推荐）

```bash
# 启动测试数据库容器
docker-compose -f deploy/local/docker-compose.test.yml up -d mysql postgres

# 等待数据库就绪（约 10-15 秒）
docker-compose -f deploy/local/docker-compose.test.yml logs -f

# 查看容器状态
docker-compose -f deploy/local/docker-compose.test.yml ps
```

### 方式二：手动执行 SQL

#### MySQL

```bash
# 执行 MySQL 初始化脚本
docker exec -i test-mysql mysql -uroot -prootdev123 < scripts/test_data/init_mysql_test_data.sql

# 或使用本地 MySQL
mysql -h localhost -P 3306 -uroot -prootdev123 < scripts/test_data/init_mysql_test_data.sql
```

#### PostgreSQL

```bash
# 首先创建数据库（脚本会自动执行）
docker exec test-postgres psql -U postgres -c "CREATE DATABASE test_ecommerce_pg;"

# 执行 PostgreSQL 初始化脚本
docker exec -i test-postgres psql -U postgres -d test_ecommerce_pg < scripts/test_data/init_postgres_test_data.sql

# 或使用本地 PostgreSQL
PGPASSWORD=postgresdev123 psql -h localhost -p 5434 -U postgres -d test_ecommerce_pg -f scripts/test_data/init_postgres_test_data.sql
```

### 方式三：使用 Python 生成工具

```bash
# 安装依赖
pip install pymysql psycopg2-binary faker

# 生成 MySQL 测试数据（默认 20000 条）
python scripts/test_data/generate_test_data.py --db mysql

# 生成 PostgreSQL 测试数据
python scripts/test_data/generate_test_data.py --db postgres

# 同时生成两种数据库的数据
python scripts/test_data/generate_test_data.py --db all

# 自定义数据量
python scripts/test_data/generate_test_data.py --db mysql --count 50000

# 自定义数据库连接
python scripts/test_data/generate_test_data.py \
    --db mysql \
    --mysql-host localhost \
    --mysql-port 3306 \
    --mysql-user root \
    --mysql-password yourpassword
```

## 测试数据结构

### MySQL 测试数据库

| 数据库名称 | 用途 | 主要表 | 预估行数 |
|-----------|------|--------|----------|
| `test_ecommerce` | 电商模块 | users, products, orders, order_items, categories, shopping_cart | 9,500+ |
| `test_user_mgmt` | 用户管理模块 | employees, departments, roles, permissions, role_permissions | 800+ |
| `test_product` | 产品模块 | product_catalog, product_specs, inventory, suppliers | 2,500+ |
| `test_logs` | 日志模块 | operation_logs, access_logs | 15,000+ |

### PostgreSQL 测试数据库

| 数据库名称 | 用途 | 主要表 | 预估行数 |
|-----------|------|--------|----------|
| `test_ecommerce_pg` | 电商模块 | users, products, orders, order_items, categories | 9,500+ |
| `test_user_mgmt_pg` | 用户管理模块 | employees, departments, roles, permissions | 800+ |
| `test_product_pg` | 产品模块 | product_catalog, product_specs, inventory, suppliers | 2,500+ |
| `test_logs_pg` | 日志模块 | operation_logs, access_logs | 15,000+ |

### 详细表结构

#### 电商模块 (test_ecommerce)

| 表名 | 说明 | 字段数 | 预估行数 |
|------|------|--------|----------|
| categories | 商品分类表 | 8 | 50+ |
| users | 用户表 | 13 | 1000+ |
| products | 商品表 | 18 | 500+ |
| orders | 订单表 | 17 | 2000+ |
| order_items | 订单详情表 | 8 | 5000+ |
| shopping_cart | 购物车表 | 6 | 1000+ |

#### 用户管理模块 (test_user_mgmt)

| 表名 | 说明 | 字段数 | 预估行数 |
|------|------|--------|----------|
| departments | 部门表 | 8 | 50+ |
| roles | 角色表 | 6 | 20+ |
| permissions | 权限表 | 8 | 100+ |
| role_permissions | 角色权限关联表 | 3 | 200+ |
| employees | 员工表 | 14 | 500+ |

#### 产品模块 (test_product)

| 表名 | 说明 | 字段数 | 预估行数 |
|------|------|--------|----------|
| product_catalog | 产品目录 | 8 | 300+ |
| product_specs | 产品规格 | 7 | 1000+ |
| inventory | 库存表 | 10 | 1000+ |
| suppliers | 供应商表 | 11 | 100+ |

#### 日志模块 (test_logs)

| 表名 | 说明 | 字段数 | 预估行数 |
|------|------|--------|----------|
| operation_logs | 操作日志 | 13 | 5000+ |
| access_logs | 访问日志 | 11 | 10000+ |

## 数据库连接配置

### MySQL

```yaml
host: localhost
port: 3306
user: root
password: rootdev123
```

### PostgreSQL

```yaml
host: localhost
port: 5434
user: postgres
password: postgresdev123
```

## 验证数据生成

### MySQL

```bash
# 连接到 MySQL
docker exec -it test-mysql mysql -uroot -prootdev123

# 执行验证查询
SELECT 'test_ecommerce.users' AS table_name, COUNT(*) AS row_count FROM test_ecommerce.users
UNION ALL
SELECT 'test_ecommerce.products', COUNT(*) FROM test_ecommerce.products
UNION ALL
SELECT 'test_ecommerce.orders', COUNT(*) FROM test_ecommerce.orders
UNION ALL
SELECT 'test_logs.operation_logs', COUNT(*) FROM test_logs.operation_logs
UNION ALL
SELECT 'test_logs.access_logs', COUNT(*) FROM test_logs.access_logs;
```

### PostgreSQL

```bash
# 连接到 PostgreSQL
docker exec -it test-postgres psql -U postgres -d test_ecommerce_pg

# 执行验证查询
SELECT 'users' AS table_name, COUNT(*) AS row_count FROM users
UNION ALL
SELECT 'products', COUNT(*) FROM products
UNION ALL
SELECT 'orders', COUNT(*) FROM orders;
```

## 清理测试数据

```bash
# 停止并删除测试容器
docker-compose -f deploy/local/docker-compose.test.yml down

# 删除数据卷（清空所有数据）
docker-compose -f deploy/local/docker-compose.test.yml down -v

# 重新启动（空数据库）
docker-compose -f deploy/local/docker-compose.test.yml up -d
```

## 故障排除

### MySQL 连接失败

```bash
# 检查 MySQL 容器状态
docker ps | grep test-mysql

# 查看 MySQL 日志
docker logs test-mysql

# 等待 MySQL 就绪
docker exec test-mysql mysqladmin ping -h localhost -uroot -prootdev123
```

### PostgreSQL 连接失败

```bash
# 检查 PostgreSQL 容器状态
docker ps | grep test-postgres

# 查看 PostgreSQL 日志
docker logs test-postgres

# 等待 PostgreSQL 就绪
docker exec test-postgres pg_isready -U postgres
```

### 数据生成失败

1. 确认数据库服务已启动并可连接
2. 检查数据库用户权限
3. 确认端口没有被其他服务占用
4. 查看详细日志使用 `--verbose` 参数

## 注意事项

1. **端口冲突**：如果本地已运行 MySQL (3306) 或 PostgreSQL (5432)，请修改 docker-compose.test.yml 中的端口映射
2. **密码安全**：生产环境请修改默认密码
3. **数据量**：大量数据生成可能需要较长时间，建议分批生成
4. **资源限制**：Docker 容器默认资源限制可能影响数据生成性能

## 维护记录

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-02-08 | 1.0.0 | 初始版本，支持 MySQL 和 PostgreSQL 测试数据生成 |
