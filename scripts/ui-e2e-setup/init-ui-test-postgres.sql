-- =============================================================================
-- ONE-DATA-STUDIO UI E2E 测试数据初始化脚本 (PostgreSQL)
-- =============================================================================
--
-- 功能：创建 UI E2E 测试的表结构和示例数据
-- 端口：5440 (独立 UI E2E 测试端口)
--
-- 使用方法：
--   PGPASSWORD=uitestpg123 psql -h localhost -p 5440 -U postgres -d ui_test_ecommerce_pg -f init-ui-test-postgres.sql
--
-- =============================================================================

\set ON_ERROR_STOP on

-- =============================================================================
-- 电商模块 (ui_test_ecommerce_pg)
-- =============================================================================

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
('运动户外', NULL, 1, 5),
('手机', 1, 2, 1),
('电脑', 1, 2, 2),
('数码配件', 1, 2, 3),
('男装', 2, 2, 1),
('女装', 2, 2, 2),
('运动装', 2, 2, 3),
('零食', 3, 2, 1),
('饮料', 3, 2, 2),
('生鲜', 3, 2, 3),
('家具', 4, 2, 1),
('家纺', 4, 2, 2),
('健身器材', 5, 2, 1),
('户外装备', 5, 2, 2)
ON CONFLICT DO NOTHING;

-- 插入示例用户数据
INSERT INTO users (username, email, password_hash, nickname, gender, status) VALUES
('ui_test_pg_user_001', 'ui_test_pg_001@example.com', 'hashed_password', 'UI测试PG用户1', 'male', 'active'),
('ui_test_pg_user_002', 'ui_test_pg_002@example.com', 'hashed_password', 'UI测试PG用户2', 'female', 'active'),
('ui_test_pg_user_003', 'ui_test_pg_003@example.com', 'hashed_password', 'UI测试PG用户3', 'other', 'active')
ON CONFLICT (username) DO NOTHING;

-- 插入示例商品数据
INSERT INTO products (category_id, product_name, product_code, description, price, cost_price, stock_quantity, status, brand) VALUES
(1, 'UI测试PG手机1', 'UI_TEST_PG_PRD001', '这是UI测试PG手机1的描述', 3999.00, 3000.00, 100, 'on_sale', '测试品牌'),
(1, 'UI测试PG手机2', 'UI_TEST_PG_PRD002', '这是UI测试PG手机2的描述', 4999.00, 3800.00, 50, 'on_sale', '测试品牌'),
(2, 'UI测试PG笔记本', 'UI_TEST_PG_PRD003', '这是UI测试PG笔记本的描述', 6999.00, 5500.00, 30, 'on_sale', '测试品牌'),
(3, 'UI测试PG零食', 'UI_TEST_PG_PRD004', '这是UI测试PG零食的描述', 19.90, 10.00, 500, 'on_sale', '测试食品品牌')
ON CONFLICT (product_code) DO NOTHING;

-- 插入示例订单数据
INSERT INTO orders (order_no, user_id, total_amount, actual_amount, status, payment_method, receiver_name, receiver_phone, receiver_address) VALUES
('UI_TEST_PG_ORD001', 1, 3999.00, 3999.00, 'completed', 'alipay', 'UI测试PG收货人1', '13800000001', 'UI测试PG地址1号'),
('UI_TEST_PG_ORD002', 2, 4999.00, 4999.00, 'paid', 'wechat', 'UI测试PG收货人2', '13800000002', 'UI测试PG地址2号')
ON CONFLICT (order_no) DO NOTHING;

-- 插入示例订单详情数据
INSERT INTO order_items (order_id, product_id, product_name, product_code, unit_price, quantity, subtotal) VALUES
(1, 1, 'UI测试PG手机1', 'UI_TEST_PG_PRD001', 3999.00, 1, 3999.00),
(2, 2, 'UI测试PG手机2', 'UI_TEST_PG_PRD002', 4999.00, 1, 4999.00);

-- 显示数据统计
DO $$
BEGIN
    RAISE NOTICE 'UI E2E PostgreSQL Test data initialization completed!';
END $$;

SELECT 'users' AS table_name, COUNT(*) AS row_count FROM users
UNION ALL
SELECT 'products', COUNT(*) FROM products
UNION ALL
SELECT 'orders', COUNT(*) FROM orders
UNION ALL
SELECT 'order_items', COUNT(*) FROM order_items;
