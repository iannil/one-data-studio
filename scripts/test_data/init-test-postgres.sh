#!/bin/bash
# =============================================================================
# PostgreSQL 测试数据库初始化脚本 (UI E2E 测试)
# =============================================================================
#
# 功能：在 PostgreSQL 容器启动时自动创建测试数据库并执行初始化
# 端口：5442
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

    -- 创建日志测试数据库
    CREATE DATABASE test_logs_pg;

    -- 授予权限
    GRANT ALL PRIVILEGES ON DATABASE test_ecommerce_pg TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON DATABASE test_user_mgmt_pg TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON DATABASE test_logs_pg TO $POSTGRES_USER;
EOSQL

echo "PostgreSQL test databases created successfully!"

# 等待数据库创建完成
sleep 2

# 初始化电商数据库
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

    CREATE INDEX idx_categories_parent_id ON categories(parent_id);
    CREATE INDEX idx_categories_is_active ON categories(is_active);

    -- 用户表
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) NOT NULL UNIQUE,
        email VARCHAR(100) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        nickname VARCHAR(50),
        avatar VARCHAR(255),
        gender VARCHAR(10) CHECK (gender IN ('male', 'female', 'other')),
        birth_date DATE,
        phone VARCHAR(20),
        status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'banned')),
        last_login_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX idx_users_email ON users(email);
    CREATE INDEX idx_users_status ON users(status);
    CREATE INDEX idx_users_created_at ON users(created_at);

    -- 商品表
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        category_id INTEGER NOT NULL,
        product_name VARCHAR(200) NOT NULL,
        product_code VARCHAR(50) UNIQUE NOT NULL,
        description TEXT,
        price NUMERIC(10,2) NOT NULL,
        cost_price NUMERIC(10,2),
        stock_quantity INTEGER DEFAULT 0,
        sales_count INTEGER DEFAULT 0,
        image_url VARCHAR(500),
        status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'on_sale', 'off_sale', 'out_of_stock')),
        weight NUMERIC(8,2),
        brand VARCHAR(100),
        tags JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES categories(id)
    );

    CREATE INDEX idx_products_category_id ON products(category_id);
    CREATE INDEX idx_products_product_code ON products(product_code);
    CREATE INDEX idx_products_status ON products(status);
    CREATE INDEX idx_products_price ON products(price);

    -- 订单表
    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        order_no VARCHAR(50) UNIQUE NOT NULL,
        user_id INTEGER NOT NULL,
        total_amount NUMERIC(10,2) NOT NULL,
        discount_amount NUMERIC(10,2) DEFAULT 0,
        actual_amount NUMERIC(10,2) NOT NULL,
        status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'shipped', 'completed', 'cancelled', 'refunded')),
        payment_method VARCHAR(20) CHECK (payment_method IN ('alipay', 'wechat', 'credit_card', 'bank_transfer')),
        payment_time TIMESTAMP,
        shipment_time TIMESTAMP,
        completion_time TIMESTAMP,
        receiver_name VARCHAR(50),
        receiver_phone VARCHAR(20),
        receiver_address VARCHAR(500),
        remark VARCHAR(500),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE INDEX idx_orders_order_no ON orders(order_no);
    CREATE INDEX idx_orders_user_id ON orders(user_id);
    CREATE INDEX idx_orders_status ON orders(status);
    CREATE INDEX idx_orders_created_at ON orders(created_at);

    -- 订单详情表
    CREATE TABLE IF NOT EXISTS order_items (
        id SERIAL PRIMARY KEY,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        product_name VARCHAR(200) NOT NULL,
        product_code VARCHAR(50) NOT NULL,
        unit_price NUMERIC(10,2) NOT NULL,
        quantity INTEGER NOT NULL,
        subtotal NUMERIC(10,2) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id)
    );

    CREATE INDEX idx_order_items_order_id ON order_items(order_id);
    CREATE INDEX idx_order_items_product_id ON order_items(product_id);

    -- 购物车表
    CREATE TABLE IF NOT EXISTS shopping_cart (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
        UNIQUE (user_id, product_id)
    );

    CREATE INDEX idx_shopping_cart_user_id ON shopping_cart(user_id);

    -- 插入商品分类数据
    INSERT INTO categories (name, parent_id, level, sort_order) VALUES
    ('电子产品', NULL, 1, 1),
    ('服装鞋帽', NULL, 1, 2),
    ('食品饮料', NULL, 1, 3),
    ('家居用品', NULL, 1, 4),
    ('手机', 1, 2, 1),
    ('电脑', 1, 2, 2),
    ('男装', 2, 2, 1),
    ('女装', 2, 2, 2),
    ('零食', 3, 2, 1),
    ('饮料', 3, 2, 2)
    ON CONFLICT DO NOTHING;

    -- 创建生成用户数据的函数
    CREATE OR REPLACE FUNCTION generate_users(count INTEGER) RETURNS void AS $$
    DECLARE
        i INTEGER := 1;
        username VARCHAR(50);
        email VARCHAR(100);
    BEGIN
        WHILE i <= count LOOP
            username := 'user_' || LPAD(i::TEXT, 5, '0');
            email := username || '@example.com';
            INSERT INTO users (username, email, password_hash, nickname, gender, status)
            VALUES (
                username,
                email,
                'hashed_password',
                '用户' || i,
                (ARRAY['male', 'female', 'other'])[floor(random() * 3 + 1)],
                (ARRAY['active', 'inactive'])[floor(random() * 2 + 1)]
            );
            i := i + 1;
        END LOOP;
    END;
    $$ LANGUAGE plpgsql;

    -- 创建生成商品数据的函数
    CREATE OR REPLACE FUNCTION generate_products(count INTEGER) RETURNS void AS $$
    DECLARE
        i INTEGER := 1;
        product_code VARCHAR(50);
    BEGIN
        WHILE i <= count LOOP
            product_code := 'PRD' || TO_CHAR(CURRENT_DATE, 'YYYYMMDD') || LPAD(i::TEXT, 6, '0');
            INSERT INTO products (category_id, product_name, product_code, description, price, cost_price, stock_quantity, status)
            VALUES (
                floor(random() * 10 + 1),
                '测试商品' || i,
                product_code,
                '这是测试商品' || i || '的描述信息',
                round((10 + random() * 990)::NUMERIC, 2),
                round((5 + random() * 500)::NUMERIC, 2),
                floor(10 + random() * 1000),
                (ARRAY['on_sale', 'off_sale', 'draft'])[floor(random() * 3 + 1)]
            );
            i := i + 1;
        END LOOP;
    END;
    $$ LANGUAGE plpgsql;

    -- 创建生成订单数据的函数
    CREATE OR REPLACE FUNCTION generate_orders(count INTEGER) RETURNS void AS $$
    DECLARE
        i INTEGER := 1;
        order_no VARCHAR(50);
        user_id INTEGER;
        total_amount NUMERIC(10,2);
    BEGIN
        WHILE i <= count LOOP
            order_no := 'ORD' || TO_CHAR(CURRENT_TIMESTAMP, 'YYYYMMDDHH24MISS') || LPAD(i::TEXT, 4, '0');
            user_id := floor(random() * 1000 + 1);
            total_amount := round((50 + random() * 5000)::NUMERIC, 2);
            INSERT INTO orders (order_no, user_id, total_amount, actual_amount, status, receiver_name, receiver_phone, receiver_address)
            VALUES (
                order_no,
                user_id,
                total_amount,
                total_amount,
                (ARRAY['pending', 'paid', 'shipped', 'completed', 'cancelled'])[floor(random() * 5 + 1)],
                '收货人' || user_id,
                '138' || LPAD(floor(random() * 100000000)::TEXT, 8, '0'),
                '测试地址' || i || '号'
            );
            i := i + 1;
        END LOOP;
    END;
    $$ LANGUAGE plpgsql;

    -- 创建生成订单详情数据的函数
    CREATE OR REPLACE FUNCTION generate_order_items(count INTEGER) RETURNS void AS $$
    DECLARE
        i INTEGER := 1;
        order_id INTEGER;
        product_id INTEGER;
        quantity INTEGER;
    BEGIN
        WHILE i <= count LOOP
            order_id := floor(random() * 2000 + 1);
            product_id := floor(random() * 500 + 1);
            quantity := floor(random() * 5 + 1);
            INSERT INTO order_items (order_id, product_id, product_name, product_code, unit_price, quantity, subtotal)
            SELECT order_id, product_id, p.product_name, p.product_code, p.price, quantity, p.price * quantity
            FROM products p WHERE p.id = product_id;
            i := i + 1;
        END LOOP;
    END;
    $$ LANGUAGE plpgsql;

    -- 生成初始测试数据
    SELECT generate_users(1000);
    SELECT generate_products(500);
    SELECT generate_orders(2000);
    SELECT generate_order_items(5000);
EOSQL

echo "test_ecommerce_pg database initialized successfully!"

# 初始化用户管理数据库
echo "Initializing test_user_mgmt_pg database..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname test_user_mgmt_pg <<-EOSQL
    -- 部门表
    CREATE TABLE IF NOT EXISTS departments (
        id SERIAL PRIMARY KEY,
        dept_name VARCHAR(100) NOT NULL,
        parent_id INTEGER,
        level INTEGER DEFAULT 1,
        manager_id INTEGER,
        description VARCHAR(500),
        sort_order INTEGER DEFAULT 0,
        is_active BOOLEAN DEFAULT true,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX idx_departments_parent_id ON departments(parent_id);
    CREATE INDEX idx_departments_is_active ON departments(is_active);

    -- 角色表
    CREATE TABLE IF NOT EXISTS roles (
        id SERIAL PRIMARY KEY,
        role_name VARCHAR(50) NOT NULL UNIQUE,
        role_code VARCHAR(50) NOT NULL UNIQUE,
        description VARCHAR(500),
        is_system BOOLEAN DEFAULT false,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX idx_roles_role_code ON roles(role_code);

    -- 权限表
    CREATE TABLE IF NOT EXISTS permissions (
        id SERIAL PRIMARY KEY,
        permission_name VARCHAR(100) NOT NULL,
        permission_code VARCHAR(100) NOT NULL UNIQUE,
        resource_type VARCHAR(50),
        resource_path VARCHAR(200),
        description VARCHAR(500),
        parent_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX idx_permissions_permission_code ON permissions(permission_code);
    CREATE INDEX idx_permissions_resource_type ON permissions(resource_type);

    -- 员工表
    CREATE TABLE IF NOT EXISTS employees (
        id SERIAL PRIMARY KEY,
        employee_no VARCHAR(50) UNIQUE NOT NULL,
        username VARCHAR(50) NOT NULL UNIQUE,
        full_name VARCHAR(100) NOT NULL,
        email VARCHAR(100) NOT NULL UNIQUE,
        phone VARCHAR(20),
        dept_id INTEGER,
        position VARCHAR(100),
        status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'resigned')),
        hire_date DATE,
        birth_date DATE,
        gender VARCHAR(10) CHECK (gender IN ('male', 'female', 'other')),
        avatar VARCHAR(255),
        last_login_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (dept_id) REFERENCES departments(id)
    );

    CREATE INDEX idx_employees_employee_no ON employees(employee_no);
    CREATE INDEX idx_employees_dept_id ON employees(dept_id);
    CREATE INDEX idx_employees_status ON employees(status);

    -- 插入部门数据
    INSERT INTO departments (dept_name, parent_id, level, sort_order) VALUES
    ('技术部', NULL, 1, 1),
    ('产品部', NULL, 1, 2),
    ('运营部', NULL, 1, 3),
    ('市场部', NULL, 1, 4),
    ('人力资源部', NULL, 1, 5)
    ON CONFLICT DO NOTHING;

    -- 插入角色数据
    INSERT INTO roles (role_name, role_code, description, is_system) VALUES
    ('超级管理员', 'super_admin', '系统超级管理员', true),
    ('管理员', 'admin', '系统管理员', true),
    ('普通用户', 'user', '普通用户', false)
    ON CONFLICT (role_code) DO NOTHING;

    -- 插入权限数据
    INSERT INTO permissions (permission_name, permission_code, resource_type, resource_path) VALUES
    ('用户管理', 'user:manage', 'user', '/api/users'),
    ('角色管理', 'role:manage', 'role', '/api/roles'),
    ('部门管理', 'dept:manage', 'dept', '/api/departments'),
    ('数据源管理', 'datasource:manage', 'datasource', '/api/datasources')
    ON CONFLICT (permission_code) DO NOTHING;
EOSQL

echo "test_user_mgmt_pg database initialized successfully!"

# 初始化日志数据库
echo "Initializing test_logs_pg database..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname test_logs_pg <<-EOSQL
    -- 操作日志表
    CREATE TABLE IF NOT EXISTS operation_logs (
        id BIGSERIAL PRIMARY KEY,
        user_id INTEGER,
        username VARCHAR(50),
        operation VARCHAR(100) NOT NULL,
        module VARCHAR(50),
        resource_type VARCHAR(50),
        resource_id VARCHAR(100),
        ip_address VARCHAR(50),
        user_agent VARCHAR(500),
        request_method VARCHAR(10),
        request_url VARCHAR(500),
        request_params TEXT,
        response_status INTEGER,
        response_time INTEGER,
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX idx_operation_logs_user_id ON operation_logs(user_id);
    CREATE INDEX idx_operation_logs_operation ON operation_logs(operation);
    CREATE INDEX idx_operation_logs_module ON operation_logs(module);
    CREATE INDEX idx_operation_logs_created_at ON operation_logs(created_at);

    -- 访问日志表
    CREATE TABLE IF NOT EXISTS access_logs (
        id BIGSERIAL PRIMARY KEY,
        session_id VARCHAR(100),
        user_id INTEGER,
        username VARCHAR(50),
        ip_address VARCHAR(50),
        user_agent VARCHAR(500),
        referer VARCHAR(500),
        request_url VARCHAR(500) NOT NULL,
        request_method VARCHAR(10),
        response_status INTEGER,
        response_time INTEGER,
        bytes_sent INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX idx_access_logs_session_id ON access_logs(session_id);
    CREATE INDEX idx_access_logs_user_id ON access_logs(user_id);
    CREATE INDEX idx_access_logs_ip_address ON access_logs(ip_address);
    CREATE INDEX idx_access_logs_created_at ON access_logs(created_at);

    -- 创建生成日志数据的函数
    CREATE OR REPLACE FUNCTION generate_operation_logs(count INTEGER) RETURNS void AS $$
    DECLARE
        i INTEGER := 1;
    BEGIN
        WHILE i <= count LOOP
            INSERT INTO operation_logs (user_id, username, operation, module, resource_type, ip_address, request_method, request_url, response_status, response_time)
            VALUES (
                floor(random() * 500 + 1),
                'user_' || LPAD(floor(random() * 500 + 1)::TEXT, 5, '0'),
                (ARRAY['CREATE', 'UPDATE', 'DELETE', 'QUERY', 'LOGIN'])[floor(random() * 5 + 1)],
                (ARRAY['user', 'order', 'product', 'datasource', 'metadata'])[floor(random() * 5 + 1)],
                (ARRAY['user', 'table', 'column', 'api'])[floor(random() * 4 + 1)],
                '192.168.' || floor(random() * 255) || '.' || floor(random() * 255),
                (ARRAY['GET', 'POST', 'PUT', 'DELETE'])[floor(random() * 4 + 1)],
                '/api/v1/' || (ARRAY['users', 'orders', 'products', 'datasources'])[floor(random() * 4 + 1)],
                (ARRAY[200, 400, 500])[floor(random() * 3 + 1)],
                floor(10 + random() * 500)
            );
            i := i + 1;
        END LOOP;
    END;
    $$ LANGUAGE plpgsql;

    CREATE OR REPLACE FUNCTION generate_access_logs(count INTEGER) RETURNS void AS $$
    DECLARE
        i INTEGER := 1;
    BEGIN
        WHILE i <= count LOOP
            INSERT INTO access_logs (session_id, user_id, username, ip_address, user_agent, request_url, request_method, response_status, response_time)
            VALUES (
                'session_' || md5(i::TEXT || random()::TEXT),
                floor(random() * 500 + 1),
                'user_' || LPAD(floor(random() * 500 + 1)::TEXT, 5, '0'),
                '192.168.' || floor(random() * 255) || '.' || floor(random() * 255),
                (ARRAY['Mozilla/5.0 (Windows)', 'Mozilla/5.0 (Macintosh)', 'Mozilla/5.0 (Linux)'])[floor(random() * 3 + 1)],
                '/api/v1/' || (ARRAY['users', 'orders', 'products'])[floor(random() * 3 + 1)],
                (ARRAY['GET', 'POST', 'PUT'])[floor(random() * 3 + 1)],
                (ARRAY[200, 400, 500])[floor(random() * 3 + 1)],
                floor(10 + random() * 500)
            );
            i := i + 1;
        END LOOP;
    END;
    $$ LANGUAGE plpgsql;

    -- 生成初始日志数据
    SELECT generate_operation_logs(5000);
    SELECT generate_access_logs(10000);
EOSQL

echo "test_logs_pg database initialized successfully!"

# 显示数据统计
echo ""
echo "============================================================================"
echo "PostgreSQL Test Data Summary"
echo "============================================================================"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname test_ecommerce_pg -t -A <<-EOSQL
    SELECT 'users' AS table_name, COUNT(*) AS row_count FROM users
    UNION ALL
    SELECT 'products', COUNT(*) FROM products
    UNION ALL
    SELECT 'orders', COUNT(*) FROM orders
    UNION ALL
    SELECT 'order_items', COUNT(*) FROM order_items;
EOSQL

echo ""
echo "PostgreSQL test databases initialization completed!"
echo "============================================================================"
