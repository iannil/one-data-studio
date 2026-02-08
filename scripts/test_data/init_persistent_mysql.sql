-- =============================================================================
-- ONE-DATA-STUDIO Persistent Test 数据初始化脚本 (MySQL)
-- =============================================================================
--
-- 功能：创建持久化测试数据库和表，数据保留供手动验证
-- 端口：3325 (独立持久化测试端口)
-- 预估数据量：10,000+ 行
--
-- 使用方法：
--   docker exec -i persistent-test-mysql mysql -uroot -ppersistent123 < init_persistent_mysql.sql
--
-- =============================================================================

-- =============================================================================
-- 第一部分：创建持久化测试数据库
-- =============================================================================

CREATE DATABASE IF NOT EXISTS persistent_ecommerce CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS persistent_user_mgmt CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS persistent_logs CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- =============================================================================
-- 第二部分：电商模块 (persistent_ecommerce)
-- =============================================================================

USE persistent_ecommerce;

-- 商品分类表
CREATE TABLE IF NOT EXISTS categories (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL COMMENT '分类名称',
    parent_id INT DEFAULT NULL COMMENT '父分类ID',
    level INT DEFAULT 0 COMMENT '分类层级',
    sort_order INT DEFAULT 0 COMMENT '排序',
    is_active TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_parent_id (parent_id),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品分类表';

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    email VARCHAR(100) NOT NULL UNIQUE COMMENT '邮箱',
    password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希',
    nickname VARCHAR(50) COMMENT '昵称',
    avatar VARCHAR(255) COMMENT '头像URL',
    gender ENUM('male', 'female', 'other') DEFAULT 'other' COMMENT '性别',
    birth_date DATE COMMENT '生日',
    phone VARCHAR(20) COMMENT '手机号',
    status ENUM('active', 'inactive', 'banned') DEFAULT 'active' COMMENT '状态',
    last_login_at DATETIME COMMENT '最后登录时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 商品表
CREATE TABLE IF NOT EXISTS products (
    id INT PRIMARY KEY AUTO_INCREMENT,
    category_id INT NOT NULL COMMENT '分类ID',
    product_name VARCHAR(200) NOT NULL COMMENT '商品名称',
    product_code VARCHAR(50) UNIQUE NOT NULL COMMENT '商品编码',
    description TEXT COMMENT '商品描述',
    price DECIMAL(10,2) NOT NULL COMMENT '价格',
    cost_price DECIMAL(10,2) COMMENT '成本价',
    stock_quantity INT DEFAULT 0 COMMENT '库存数量',
    sales_count INT DEFAULT 0 COMMENT '销量',
    image_url VARCHAR(500) COMMENT '主图URL',
    status ENUM('draft', 'on_sale', 'off_sale', 'out_of_stock') DEFAULT 'draft' COMMENT '状态',
    weight DECIMAL(8,2) COMMENT '重量(克)',
    brand VARCHAR(100) COMMENT '品牌',
    tags JSON COMMENT '标签',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    INDEX idx_category_id (category_id),
    INDEX idx_product_code (product_code),
    INDEX idx_status (status),
    INDEX idx_price (price),
    FULLTEXT idx_product_name (product_name, description)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品表';

-- 订单表
CREATE TABLE IF NOT EXISTS orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_no VARCHAR(50) UNIQUE NOT NULL COMMENT '订单号',
    user_id INT NOT NULL COMMENT '用户ID',
    total_amount DECIMAL(10,2) NOT NULL COMMENT '订单总金额',
    discount_amount DECIMAL(10,2) DEFAULT 0 COMMENT '优惠金额',
    actual_amount DECIMAL(10,2) NOT NULL COMMENT '实际支付金额',
    status ENUM('pending', 'paid', 'shipped', 'completed', 'cancelled', 'refunded') DEFAULT 'pending' COMMENT '订单状态',
    payment_method ENUM('alipay', 'wechat', 'credit_card', 'bank_transfer') COMMENT '支付方式',
    payment_time DATETIME COMMENT '支付时间',
    shipment_time DATETIME COMMENT '发货时间',
    completion_time DATETIME COMMENT '完成时间',
    receiver_name VARCHAR(50) COMMENT '收货人姓名',
    receiver_phone VARCHAR(20) COMMENT '收货人电话',
    receiver_address VARCHAR(500) COMMENT '收货地址',
    remark VARCHAR(500) COMMENT '备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_order_no (order_no),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';

-- 订单详情表
CREATE TABLE IF NOT EXISTS order_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL COMMENT '订单ID',
    product_id INT NOT NULL COMMENT '商品ID',
    product_name VARCHAR(200) NOT NULL COMMENT '商品名称',
    product_code VARCHAR(50) NOT NULL COMMENT '商品编码',
    unit_price DECIMAL(10,2) NOT NULL COMMENT '单价',
    quantity INT NOT NULL COMMENT '数量',
    subtotal DECIMAL(10,2) NOT NULL COMMENT '小计',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id),
    INDEX idx_order_id (order_id),
    INDEX idx_product_id (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单详情表';

-- 购物车表
CREATE TABLE IF NOT EXISTS shopping_cart (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL COMMENT '用户ID',
    product_id INT NOT NULL COMMENT '商品ID',
    quantity INT NOT NULL DEFAULT 1 COMMENT '数量',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    UNIQUE KEY uk_user_product (user_id, product_id),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='购物车表';

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
('户外装备', 5, 2, 2);

-- =============================================================================
-- 第三部分：用户管理模块 (persistent_user_mgmt)
-- =============================================================================

USE persistent_user_mgmt;

-- 部门表
CREATE TABLE IF NOT EXISTS departments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    dept_name VARCHAR(100) NOT NULL COMMENT '部门名称',
    parent_id INT DEFAULT NULL COMMENT '父部门ID',
    level INT DEFAULT 1 COMMENT '层级',
    manager_id INT DEFAULT NULL COMMENT '部门负责人ID',
    description VARCHAR(500) COMMENT '描述',
    sort_order INT DEFAULT 0 COMMENT '排序',
    is_active TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_parent_id (parent_id),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='部门表';

-- 角色表
CREATE TABLE IF NOT EXISTS roles (
    id INT PRIMARY KEY AUTO_INCREMENT,
    role_name VARCHAR(50) NOT NULL UNIQUE COMMENT '角色名称',
    role_code VARCHAR(50) NOT NULL UNIQUE COMMENT '角色编码',
    description VARCHAR(500) COMMENT '描述',
    is_system TINYINT(1) DEFAULT 0 COMMENT '是否系统角色',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_role_code (role_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色表';

-- 权限表
CREATE TABLE IF NOT EXISTS permissions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    permission_name VARCHAR(100) NOT NULL COMMENT '权限名称',
    permission_code VARCHAR(100) NOT NULL UNIQUE COMMENT '权限编码',
    resource_type VARCHAR(50) COMMENT '资源类型',
    resource_path VARCHAR(200) COMMENT '资源路径',
    description VARCHAR(500) COMMENT '描述',
    parent_id INT DEFAULT NULL COMMENT '父权限ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_permission_code (permission_code),
    INDEX idx_resource_type (resource_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='权限表';

-- 角色权限关联表
CREATE TABLE IF NOT EXISTS role_permissions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    role_id INT NOT NULL COMMENT '角色ID',
    permission_id INT NOT NULL COMMENT '权限ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE,
    UNIQUE KEY uk_role_permission (role_id, permission_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色权限关联表';

-- 员工表
CREATE TABLE IF NOT EXISTS employees (
    id INT PRIMARY KEY AUTO_INCREMENT,
    employee_no VARCHAR(50) UNIQUE NOT NULL COMMENT '员工编号',
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    full_name VARCHAR(100) NOT NULL COMMENT '姓名',
    email VARCHAR(100) NOT NULL UNIQUE COMMENT '邮箱',
    phone VARCHAR(20) COMMENT '手机号',
    dept_id INT COMMENT '部门ID',
    position VARCHAR(100) COMMENT '职位',
    status ENUM('active', 'inactive', 'resigned') DEFAULT 'active' COMMENT '状态',
    hire_date DATE COMMENT '入职日期',
    birth_date DATE COMMENT '生日',
    gender ENUM('male', 'female', 'other') DEFAULT 'other' COMMENT '性别',
    avatar VARCHAR(255) COMMENT '头像URL',
    last_login_at DATETIME COMMENT '最后登录时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (dept_id) REFERENCES departments(id),
    INDEX idx_employee_no (employee_no),
    INDEX idx_dept_id (dept_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='员工表';

-- 插入部门数据
INSERT INTO departments (dept_name, parent_id, level, sort_order) VALUES
('技术部', NULL, 1, 1),
('产品部', NULL, 1, 2),
('运营部', NULL, 1, 3),
('市场部', NULL, 1, 4),
('人力资源部', NULL, 1, 5),
('财务部', NULL, 1, 6),
('后端开发组', 1, 2, 1),
('前端开发组', 1, 2, 2),
('测试组', 1, 2, 3),
('运维组', 1, 2, 4),
('产品设计组', 2, 2, 1),
('用户运营组', 3, 2, 1),
('内容运营组', 3, 2, 2),
('品牌推广组', 4, 2, 1),
('数字营销组', 4, 2, 2);

-- 插入角色数据
INSERT INTO roles (role_name, role_code, description, is_system) VALUES
('超级管理员', 'super_admin', '系统超级管理员，拥有所有权限', 1),
('管理员', 'admin', '系统管理员', 1),
('数据分析师', 'data_analyst', '数据分析师角色，可以查看和分析数据', 0),
('数据开发工程师', 'data_engineer', '数据开发工程师角色', 0),
('普通用户', 'user', '普通用户', 0),
('访客', 'guest', '访客用户，只读权限', 0),
('部门经理', 'dept_manager', '部门经理角色', 0);

-- 插入权限数据
INSERT INTO permissions (permission_name, permission_code, resource_type, resource_path) VALUES
('数据源管理', 'datasource:manage', 'datasource', '/api/v1/datasources'),
('数据源查看', 'datasource:view', 'datasource', '/api/v1/datasources'),
('数据源创建', 'datasource:create', 'datasource', '/api/v1/datasources'),
('数据源编辑', 'datasource:edit', 'datasource', '/api/v1/datasources'),
('数据源删除', 'datasource:delete', 'datasource', '/api/v1/datasources'),
('元数据管理', 'metadata:manage', 'metadata', '/api/v1/metadata'),
('元数据查看', 'metadata:view', 'metadata', '/api/v1/metadata'),
('元数据扫描', 'metadata:scan', 'metadata', '/api/v1/metadata/scan'),
('数据资产管理', 'asset:manage', 'asset', '/api/v1/assets'),
('资产查看', 'asset:view', 'asset', '/api/v1/assets'),
('资产注册', 'asset:register', 'asset', '/api/v1/assets'),
('特征管理', 'feature:manage', 'feature', '/api/v1/features'),
('数据标准', 'standard:manage', 'standard', '/api/v1/standards'),
('用户管理', 'user:manage', 'user', '/api/v1/users'),
('角色管理', 'role:manage', 'role', '/api/v1/roles');

-- =============================================================================
-- 第四部分：日志模块 (persistent_logs)
-- =============================================================================

USE persistent_logs;

-- 操作日志表
CREATE TABLE IF NOT EXISTS operation_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id INT COMMENT '操作用户ID',
    username VARCHAR(50) COMMENT '用户名',
    operation VARCHAR(100) NOT NULL COMMENT '操作类型',
    module VARCHAR(50) COMMENT '所属模块',
    resource_type VARCHAR(50) COMMENT '资源类型',
    resource_id VARCHAR(100) COMMENT '资源ID',
    resource_name VARCHAR(200) COMMENT '资源名称',
    ip_address VARCHAR(50) COMMENT 'IP地址',
    user_agent VARCHAR(500) COMMENT '用户代理',
    request_method VARCHAR(10) COMMENT '请求方法',
    request_url VARCHAR(500) COMMENT '请求URL',
    request_params TEXT COMMENT '请求参数',
    response_status INT COMMENT '响应状态码',
    response_time INT COMMENT '响应时间(ms)',
    error_message TEXT COMMENT '错误信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_operation (operation),
    INDEX idx_module (module),
    INDEX idx_resource_type (resource_type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='操作日志表';

-- 访问日志表
CREATE TABLE IF NOT EXISTS access_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    session_id VARCHAR(100) COMMENT '会话ID',
    user_id INT COMMENT '用户ID',
    username VARCHAR(50) COMMENT '用户名',
    ip_address VARCHAR(50) COMMENT 'IP地址',
    user_agent VARCHAR(500) COMMENT '用户代理',
    referer VARCHAR(500) COMMENT '来源URL',
    request_url VARCHAR(500) NOT NULL COMMENT '请求URL',
    request_method VARCHAR(10) COMMENT '请求方法',
    response_status INT COMMENT '响应状态码',
    response_time INT COMMENT '响应时间(ms)',
    bytes_sent INT COMMENT '发送字节数',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    INDEX idx_user_id (user_id),
    INDEX idx_ip_address (ip_address),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='访问日志表';

-- 数据变更日志表
CREATE TABLE IF NOT EXISTS data_change_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    table_name VARCHAR(100) NOT NULL COMMENT '表名',
    database_name VARCHAR(100) NOT NULL COMMENT '数据库名',
    operation_type ENUM('INSERT', 'UPDATE', 'DELETE') NOT NULL COMMENT '操作类型',
    record_id VARCHAR(100) COMMENT '记录ID',
    old_values JSON COMMENT '旧值',
    new_values JSON COMMENT '新值',
    changed_fields JSON COMMENT '变更字段',
    changed_by VARCHAR(50) COMMENT '变更人',
    change_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '变更时间',
    INDEX idx_table_name (table_name),
    INDEX idx_database_name (database_name),
    INDEX idx_operation_type (operation_type),
    INDEX idx_change_time (change_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据变更日志表';

-- =============================================================================
-- 第五部分：创建存储过程用于批量生成测试数据
-- =============================================================================

USE persistent_ecommerce;

DELIMITER //

-- 生成用户数据的存储过程
CREATE PROCEDURE IF NOT EXISTS generate_persistent_users(IN count INT)
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE username VARCHAR(50);
    DECLARE email VARCHAR(100);
    WHILE i <= count DO
        SET username = CONCAT('persistent_user_', LPAD(i, 5, '0'));
        SET email = CONCAT(username, '@persistent.test');
        INSERT INTO users (username, email, password_hash, nickname, gender, status)
        VALUES (
            username,
            email,
            'hashed_password',
            CONCAT('持久化测试用户', i),
            ELT(FLOOR(1 + RAND() * 3), 'male', 'female', 'other'),
            ELT(FLOOR(1 + RAND() * 2), 'active', 'inactive')
        );
        SET i = i + 1;
    END WHILE;
END //

-- 生成商品数据的存储过程
CREATE PROCEDURE IF NOT EXISTS generate_persistent_products(IN count INT)
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE product_code VARCHAR(50);
    WHILE i <= count DO
        SET product_code = CONCAT('PERSIST_PRD', DATE_FORMAT(NOW(), '%Y%m%d'), LPAD(i, 6, '0'));
        INSERT INTO products (category_id, product_name, product_code, description, price, cost_price, stock_quantity, status, brand)
        VALUES (
            FLOOR(1 + RAND() * 18),
            CONCAT('持久化测试商品', i),
            product_code,
            CONCAT('这是持久化测试商品', i, '的详细描述信息，包含产品特点、规格参数等内容。'),
            ROUND(10 + RAND() * 9990, 2),
            ROUND(5 + RAND() * 5000, 2),
            FLOOR(10 + RAND() * 1000),
            ELT(FLOOR(1 + RAND() * 3), 'on_sale', 'off_sale', 'draft'),
            ELT(FLOOR(1 + RAND() * 9), 'Apple', '华为', '小米', 'OPPO', 'vivo', '三星', '索尼', '戴尔', '联想')
        );
        SET i = i + 1;
    END WHILE;
END //

-- 生成订单数据的存储过程
CREATE PROCEDURE IF NOT EXISTS generate_persistent_orders(IN count INT)
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE order_no VARCHAR(50);
    DECLARE user_id INT;
    DECLARE total_amount DECIMAL(10,2);
    WHILE i <= count DO
        SET order_no = CONCAT('PERSIST_ORD', DATE_FORMAT(NOW(), '%Y%m%d%H%i%s'), LPAD(i, 4, '0'));
        SET user_id = FLOOR(1 + RAND() * 1000);
        SET total_amount = ROUND(50 + RAND() * 5000, 2);
        INSERT INTO orders (order_no, user_id, total_amount, actual_amount, status, payment_method, receiver_name, receiver_phone, receiver_address)
        VALUES (
            order_no,
            user_id,
            total_amount,
            total_amount,
            ELT(FLOOR(1 + RAND() * 5), 'pending', 'paid', 'shipped', 'completed', 'cancelled'),
            ELT(FLOOR(1 + RAND() * 4), 'alipay', 'wechat', 'credit_card', 'bank_transfer'),
            CONCAT('持久化测试收货人', user_id),
            CONCAT('138', LPAD(FLOOR(RAND() * 100000000), 8, '0')),
            CONCAT('持久化测试省持久化测试市持久化测试区持久化测试街道', i, '号')
        );
        SET i = i + 1;
    END WHILE;
END //

-- 生成订单详情数据的存储过程
CREATE PROCEDURE IF NOT EXISTS generate_persistent_order_items(IN count INT)
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE order_id INT;
    DECLARE product_id INT;
    DECLARE quantity INT;
    WHILE i <= count DO
        SET order_id = FLOOR(1 + RAND() * 1500);
        SET product_id = FLOOR(1 + RAND() * 500);
        SET quantity = FLOOR(1 + RAND() * 5);
        INSERT INTO order_items (order_id, product_id, product_name, product_code, unit_price, quantity, subtotal)
        SELECT order_id, product_id, p.product_name, p.product_code, p.price, quantity, ROUND(p.price * quantity, 2)
        FROM products p WHERE p.id = product_id;
        SET i = i + 1;
    END WHILE;
END //

DELIMITER ;

-- 生成初始测试数据（较小数量）
CALL generate_persistent_users(1000);
CALL generate_persistent_products(500);
CALL generate_persistent_orders(1500);
CALL generate_persistent_order_items(3000);

-- =============================================================================
-- 完成提示
-- =============================================================================

SELECT 'Persistent Test MySQL data initialization completed!' AS message;

-- 显示各数据库的表统计
SELECT 'persistent_ecommerce' AS database_name, TABLE_NAME, TABLE_ROWS
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'persistent_ecommerce'
ORDER BY TABLE_NAME;

SELECT 'persistent_user_mgmt' AS database_name, TABLE_NAME, TABLE_ROWS
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'persistent_user_mgmt'
ORDER BY TABLE_NAME;

SELECT 'persistent_logs' AS database_name, TABLE_NAME, TABLE_ROWS
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'persistent_logs'
ORDER BY TABLE_NAME;
