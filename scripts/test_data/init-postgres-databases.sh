#!/bin/bash
# =============================================================================
# PostgreSQL 测试数据库初始化脚本
# =============================================================================
#
# 功能：在 PostgreSQL 容器启动时自动创建测试数据库并执行初始化
#
# =============================================================================

set -e

# 配置
POSTGRES_USER="${POSTGRES_USER:-postgres}"

# 创建测试数据库
echo "Creating PostgreSQL test databases..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    -- 创建电商测试数据库
    CREATE DATABASE test_ecommerce_pg;

    -- 创建用户管理测试数据库
    CREATE DATABASE test_user_mgmt_pg;

    -- 创建产品测试数据库
    CREATE DATABASE test_product_pg;

    -- 创建日志测试数据库
    CREATE DATABASE test_logs_pg;

    -- 授予权限
    GRANT ALL PRIVILEGES ON DATABASE test_ecommerce_pg TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON DATABASE test_user_mgmt_pg TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON DATABASE test_product_pg TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON DATABASE test_logs_pg TO $POSTGRES_USER;
EOSQL

echo "PostgreSQL test databases created successfully!"

# 等待数据库创建完成
sleep 2

# 初始化电商数据库（作为示例）
echo "Initializing test_ecommerce_pg database..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname test_ecommerce_pg <<-EOSQL
    -- 商品分类表
    CREATE TABLE IF NOT EXISTS categories (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        parent_id INTEGER,
        level INTEGER DEFAULT 0,
        sort_order INTEGER DEFAULT 0,
        is_active BOOLEAN DEFAULT true,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- 用户表
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) NOT NULL UNIQUE,
        email VARCHAR(100) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        nickname VARCHAR(50),
        gender VARCHAR(10),
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- 商品表
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        category_id INTEGER NOT NULL,
        product_name VARCHAR(200) NOT NULL,
        product_code VARCHAR(50) UNIQUE NOT NULL,
        description TEXT,
        price NUMERIC(10,2) NOT NULL,
        stock_quantity INTEGER DEFAULT 0,
        status VARCHAR(20) DEFAULT 'draft',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES categories(id)
    );

    -- 订单表
    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        order_no VARCHAR(50) UNIQUE NOT NULL,
        user_id INTEGER NOT NULL,
        total_amount NUMERIC(10,2) NOT NULL,
        actual_amount NUMERIC(10,2) NOT NULL,
        status VARCHAR(20) DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    -- 订单详情表
    CREATE TABLE IF NOT EXISTS order_items (
        id SERIAL PRIMARY KEY,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        unit_price NUMERIC(10,2) NOT NULL,
        quantity INTEGER NOT NULL,
        subtotal NUMERIC(10,2) NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id)
    );

    -- 插入示例分类
    INSERT INTO categories (name, parent_id, level, sort_order) VALUES
    ('电子产品', NULL, 1, 1),
    ('服装鞋帽', NULL, 1, 2),
    ('食品饮料', NULL, 1, 3),
    ('手机', 1, 2, 1),
    ('电脑', 1, 2, 2)
    ON CONFLICT DO NOTHING;

    -- 插入示例用户
    INSERT INTO users (username, email, password_hash, nickname) VALUES
    ('test_user_1', 'test1@example.com', 'hash', '测试用户1'),
    ('test_user_2', 'test2@example.com', 'hash', '测试用户2'),
    ('test_user_3', 'test3@example.com', 'hash', '测试用户3')
    ON CONFLICT (username) DO NOTHING;

    -- 插入示例商品
    INSERT INTO products (category_id, product_name, product_code, description, price, stock_quantity, status) VALUES
    (1, 'iPhone 15', 'PRD001', '苹果手机', 7999.00, 100, 'on_sale'),
    (1, '华为 Mate 60', 'PRD002', '华为手机', 6999.00, 150, 'on_sale'),
    (2, '小米笔记本', 'PRD003', '笔记本电脑', 4999.00, 80, 'on_sale')
    ON CONFLICT (product_code) DO NOTHING;
EOSQL

echo "PostgreSQL test databases initialization completed!"
