-- =============================================================================
-- ONE-DATA-STUDIO Persistent Test 数据初始化脚本 (PostgreSQL)
-- =============================================================================
--
-- 功能：创建持久化测试数据库和表，数据保留供手动验证
-- 端口：5450 (独立持久化测试端口)
-- 预估数据量：5,000+ 行
--
-- 使用方法：
--   PGPASSWORD=persistentpg123 psql -h localhost -p 5450 -U postgres -d persistent_ecommerce_pg -f init_persistent_postgres.sql
--
-- =============================================================================

\set ON_ERROR_STOP on

-- =============================================================================
-- 电商模块 (persistent_ecommerce_pg)
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

CREATE INDEX IF NOT EXISTS idx_categories_parent_id ON categories(parent_id);
CREATE INDEX IF NOT EXISTS idx_categories_is_active ON categories(is_active);

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

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

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

CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_product_code ON products(product_code);
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);
CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);

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

CREATE INDEX IF NOT EXISTS idx_orders_order_no ON orders(order_no);
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);

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

CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);

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

CREATE INDEX IF NOT EXISTS idx_shopping_cart_user_id ON shopping_cart(user_id);

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

-- 创建生成用户数据的函数
CREATE OR REPLACE FUNCTION generate_persistent_users(count INTEGER) RETURNS void AS $$
DECLARE
    i INTEGER := 1;
    username VARCHAR(50);
    email VARCHAR(100);
BEGIN
    WHILE i <= count LOOP
        username := 'persistent_pg_user_' || LPAD(i::TEXT, 5, '0');
        email := username || '@persistent.pg.test';
        INSERT INTO users (username, email, password_hash, nickname, gender, status)
        VALUES (
            username,
            email,
            'hashed_password',
            '持久化PG用户' || i,
            (ARRAY['male', 'female', 'other'])[floor(random() * 3 + 1)],
            (ARRAY['active', 'inactive'])[floor(random() * 2 + 1)]
        );
        i := i + 1;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- 创建生成商品数据的函数
CREATE OR REPLACE FUNCTION generate_persistent_products(count INTEGER) RETURNS void AS $$
DECLARE
    i INTEGER := 1;
    product_code VARCHAR(50);
    brands TEXT[] := ARRAY['Apple', '华为', '小米', 'OPPO', 'vivo', '三星', '戴尔', '联想'];
BEGIN
    WHILE i <= count LOOP
        product_code := 'PERSIST_PG_PRD' || TO_CHAR(CURRENT_DATE, 'YYYYMMDD') || LPAD(i::TEXT, 6, '0');
        INSERT INTO products (category_id, product_name, product_code, description, price, cost_price, stock_quantity, status, brand)
        VALUES (
            floor(random() * 18 + 1),
            '持久化PG测试商品' || i,
            product_code,
            '这是持久化PG测试商品' || i || '的详细描述信息',
            round((10 + random() * 9990)::NUMERIC, 2),
            round((5 + random() * 5000)::NUMERIC, 2),
            floor(10 + random() * 1000),
            (ARRAY['on_sale', 'off_sale', 'draft'])[floor(random() * 3 + 1)],
            brands[floor(random() * array_length(brands, 1) + 1)]
        );
        i := i + 1;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- 创建生成订单数据的函数
CREATE OR REPLACE FUNCTION generate_persistent_orders(count INTEGER) RETURNS void AS $$
DECLARE
    i INTEGER := 1;
    order_no VARCHAR(50);
    user_id INTEGER;
    total_amount NUMERIC(10,2);
    statuses TEXT[] := ARRAY['pending', 'paid', 'shipped', 'completed', 'cancelled'];
    payment_methods TEXT[] := ARRAY['alipay', 'wechat', 'credit_card', 'bank_transfer'];
BEGIN
    WHILE i <= count LOOP
        order_no := 'PERSIST_PG_ORD' || TO_CHAR(CURRENT_TIMESTAMP, 'YYYYMMDDHH24MISS') || LPAD(i::TEXT, 4, '0');
        user_id := floor(random() * 500 + 1);
        total_amount := round((50 + random() * 5000)::NUMERIC, 2);
        INSERT INTO orders (order_no, user_id, total_amount, actual_amount, status, payment_method, receiver_name, receiver_phone, receiver_address)
        VALUES (
            order_no,
            user_id,
            total_amount,
            total_amount,
            statuses[floor(random() * array_length(statuses, 1) + 1)],
            payment_methods[floor(random() * array_length(payment_methods, 1) + 1)],
            '持久化PG收货人' || user_id,
            '138' || LPAD(floor(random() * 100000000)::TEXT, 8, '0'),
            '持久化PG测试地址' || i || '号'
        );
        i := i + 1;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- 创建生成订单详情数据的函数
CREATE OR REPLACE FUNCTION generate_persistent_order_items(count INTEGER) RETURNS void AS $$
DECLARE
    i INTEGER := 1;
    order_id INTEGER;
    product_id INTEGER;
    quantity INTEGER;
BEGIN
    WHILE i <= count LOOP
        order_id := floor(random() * 800 + 1);
        product_id := floor(random() * 300 + 1);
        quantity := floor(random() * 5 + 1);
        INSERT INTO order_items (order_id, product_id, product_name, product_code, unit_price, quantity, subtotal)
        SELECT order_id, product_id, p.product_name, p.product_code, p.price, quantity, round((p.price * quantity)::NUMERIC, 2)
        FROM products p WHERE p.id = product_id;
        i := i + 1;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- 生成初始测试数据（较小数量用于 PostgreSQL）
SELECT generate_persistent_users(500);
SELECT generate_persistent_products(300);
SELECT generate_persistent_orders(800);
SELECT generate_persistent_order_items(1500);

-- 显示数据统计
DO $$
BEGIN
    RAISE NOTICE 'Persistent PostgreSQL Test data initialization completed!';
END $$;

SELECT 'users' AS table_name, COUNT(*) AS row_count FROM users
UNION ALL
SELECT 'products', COUNT(*) FROM products
UNION ALL
SELECT 'orders', COUNT(*) FROM orders
UNION ALL
SELECT 'order_items', COUNT(*) FROM order_items;
