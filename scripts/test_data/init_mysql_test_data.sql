-- =============================================================================
-- ONE-DATA-STUDIO 数据治理平台测试数据初始化脚本 (MySQL)
-- =============================================================================
--
-- 功能：创建电商、用户管理、产品、日志等业务场景的测试数据库和表
-- 预估数据量：20,000+ 行
--
-- 使用方法：
--   docker exec -i test-mysql mysql -uroot -prootdev123 < init_mysql_test_data.sql
--
-- =============================================================================

-- =============================================================================
-- 第一部分：创建测试数据库
-- =============================================================================

CREATE DATABASE IF NOT EXISTS test_ecommerce CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS test_user_mgmt CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS test_product CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS test_logs CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- =============================================================================
-- 第二部分：电商模块 (test_ecommerce)
-- =============================================================================

USE test_ecommerce;

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
('手机', 1, 2, 1),
('电脑', 1, 2, 2),
('男装', 2, 2, 1),
('女装', 2, 2, 2),
('零食', 3, 2, 1),
('饮料', 3, 2, 2);

-- =============================================================================
-- 第三部分：用户管理模块 (test_user_mgmt)
-- =============================================================================

USE test_user_mgmt;

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
('后端开发组', 1, 2, 1),
('前端开发组', 1, 2, 2),
('测试组', 1, 2, 3);

-- 插入角色数据
INSERT INTO roles (role_name, role_code, description, is_system) VALUES
('超级管理员', 'super_admin', '系统超级管理员，拥有所有权限', 1),
('管理员', 'admin', '系统管理员', 1),
('普通用户', 'user', '普通用户', 0),
('访客', 'guest', '访客用户，只读权限', 0),
('部门经理', 'dept_manager', '部门经理角色', 0);

-- 插入权限数据
INSERT INTO permissions (permission_name, permission_code, resource_type, resource_path) VALUES
('用户管理', 'user:manage', 'user', '/api/users'),
('用户查看', 'user:view', 'user', '/api/users/*'),
('用户创建', 'user:create', 'user', '/api/users'),
('用户编辑', 'user:edit', 'user', '/api/users/*'),
('用户删除', 'user:delete', 'user', '/api/users/*'),
('角色管理', 'role:manage', 'role', '/api/roles'),
('权限管理', 'permission:manage', 'permission', '/api/permissions'),
('部门管理', 'dept:manage', 'dept', '/api/departments'),
('数据源管理', 'datasource:manage', 'datasource', '/api/datasources'),
('元数据管理', 'metadata:manage', 'metadata', '/api/metadata'),
('数据资产管理', 'asset:manage', 'asset', '/api/assets');

-- =============================================================================
-- 第四部分：产品模块 (test_product)
-- =============================================================================

USE test_product;

-- 供应商表
CREATE TABLE IF NOT EXISTS suppliers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    supplier_name VARCHAR(200) NOT NULL COMMENT '供应商名称',
    supplier_code VARCHAR(50) UNIQUE NOT NULL COMMENT '供应商编码',
    contact_person VARCHAR(100) COMMENT '联系人',
    contact_phone VARCHAR(20) COMMENT '联系电话',
    contact_email VARCHAR(100) COMMENT '联系邮箱',
    address VARCHAR(500) COMMENT '地址',
    status ENUM('active', 'inactive', 'blacklisted') DEFAULT 'active' COMMENT '状态',
    credit_level ENUM('A', 'B', 'C', 'D') DEFAULT 'B' COMMENT '信用等级',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_supplier_code (supplier_code),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='供应商表';

-- 产品目录表
CREATE TABLE IF NOT EXISTS product_catalog (
    id INT PRIMARY KEY AUTO_INCREMENT,
    catalog_name VARCHAR(200) NOT NULL COMMENT '产品目录名称',
    catalog_code VARCHAR(50) UNIQUE NOT NULL COMMENT '目录编码',
    parent_id INT DEFAULT NULL COMMENT '父目录ID',
    level INT DEFAULT 1 COMMENT '层级',
    description VARCHAR(500) COMMENT '描述',
    is_active TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_catalog_code (catalog_code),
    INDEX idx_parent_id (parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='产品目录表';

-- 产品规格表
CREATE TABLE IF NOT EXISTS product_specs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL COMMENT '产品ID',
    spec_name VARCHAR(100) NOT NULL COMMENT '规格名称',
    spec_code VARCHAR(50) NOT NULL COMMENT '规格编码',
    spec_value VARCHAR(500) COMMENT '规格值',
    unit VARCHAR(20) COMMENT '单位',
    spec_type ENUM('dimension', 'weight', 'material', 'color', 'other') DEFAULT 'other' COMMENT '规格类型',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_product_id (product_id),
    INDEX idx_spec_code (spec_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='产品规格表';

-- 库存表
CREATE TABLE IF NOT EXISTS inventory (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL COMMENT '产品ID',
    warehouse_id INT NOT NULL COMMENT '仓库ID',
    quantity INT DEFAULT 0 COMMENT '库存数量',
    available_quantity INT DEFAULT 0 COMMENT '可用数量',
    locked_quantity INT DEFAULT 0 COMMENT '锁定数量',
    min_stock INT DEFAULT 0 COMMENT '最小库存',
    max_stock INT DEFAULT 0 COMMENT '最大库存',
    last_in_at DATETIME COMMENT '最后入库时间',
    last_out_at DATETIME COMMENT '最后出库时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_product_warehouse (product_id, warehouse_id),
    INDEX idx_product_id (product_id),
    INDEX idx_warehouse_id (warehouse_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库存表';

-- 插入产品目录数据
INSERT INTO product_catalog (catalog_name, catalog_code, parent_id, level) VALUES
('电子产品', 'ELEC', NULL, 1),
('服装', 'CLOTH', NULL, 1),
('食品', 'FOOD', NULL, 1),
('家居', 'HOME', NULL, 1);

-- =============================================================================
-- 第五部分：日志模块 (test_logs)
-- =============================================================================

USE test_logs;

-- 操作日志表
CREATE TABLE IF NOT EXISTS operation_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id INT COMMENT '操作用户ID',
    username VARCHAR(50) COMMENT '用户名',
    operation VARCHAR(100) NOT NULL COMMENT '操作类型',
    module VARCHAR(50) COMMENT '所属模块',
    resource_type VARCHAR(50) COMMENT '资源类型',
    resource_id VARCHAR(100) COMMENT '资源ID',
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

-- =============================================================================
-- 第六部分：创建存储过程用于批量生成测试数据
-- =============================================================================

DELIMITER ;

USE test_ecommerce;

DELIMITER //

CREATE PROCEDURE IF NOT EXISTS generate_users(IN count INT)
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE username VARCHAR(50);
    DECLARE email VARCHAR(100);
    WHILE i <= count DO
        SET username = CONCAT('user_', LPAD(i, 5, '0'));
        SET email = CONCAT(username, '@example.com');
        INSERT INTO users (username, email, password_hash, nickname, gender, status)
        VALUES (username, email, 'hashed_password', CONCAT('用户', i), ELT(FLOOR(1 + RAND() * 3), 'male', 'female', 'other'), ELT(FLOOR(1 + RAND() * 2), 'active', 'inactive'));
        SET i = i + 1;
    END WHILE;
END //

-- 生成商品测试数据的存储过程
CREATE PROCEDURE IF NOT EXISTS generate_products(IN count INT)
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE product_code VARCHAR(50);
    WHILE i <= count DO
        SET product_code = CONCAT('PRD', DATE_FORMAT(NOW(), '%Y%m%d'), LPAD(i, 6, '0'));
        INSERT INTO products (category_id, product_name, product_code, description, price, cost_price, stock_quantity, status)
        VALUES (
            FLOOR(1 + RAND() * 10),
            CONCAT('测试商品', i),
            product_code,
            CONCAT('这是测试商品', i, '的描述信息'),
            ROUND(10 + RAND() * 990, 2),
            ROUND(5 + RAND() * 500, 2),
            FLOOR(10 + RAND() * 1000),
            ELT(FLOOR(1 + RAND() * 3), 'on_sale', 'off_sale', 'draft')
        );
        SET i = i + 1;
    END WHILE;
END //

-- 生成订单测试数据的存储过程
CREATE PROCEDURE IF NOT EXISTS generate_orders(IN count INT)
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE order_no VARCHAR(50);
    DECLARE user_id INT;
    DECLARE total_amount DECIMAL(10,2);
    WHILE i <= count DO
        SET order_no = CONCAT('ORD', DATE_FORMAT(NOW(), '%Y%m%d%H%i%s'), LPAD(i, 4, '0'));
        SET user_id = FLOOR(1 + RAND() * 1000);
        SET total_amount = ROUND(50 + RAND() * 5000, 2);
        INSERT INTO orders (order_no, user_id, total_amount, actual_amount, status, receiver_name, receiver_phone, receiver_address)
        VALUES (
            order_no,
            user_id,
            total_amount,
            total_amount,
            ELT(FLOOR(1 + RAND() * 5), 'pending', 'paid', 'shipped', 'completed', 'cancelled'),
            CONCAT('收货人', user_id),
            CONCAT('138', LPAD(FLOOR(RAND() * 100000000), 8, '0')),
            CONCAT('测试地址', i, '号')
        );
        SET i = i + 1;
    END WHILE;
END //

-- 生成订单详情测试数据的存储过程
CREATE PROCEDURE IF NOT EXISTS generate_order_items(IN count INT)
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE order_id INT;
    DECLARE product_id INT;
    DECLARE quantity INT;
    WHILE i <= count DO
        SET order_id = FLOOR(1 + RAND() * 2000);
        SET product_id = FLOOR(1 + RAND() * 500);
        SET quantity = FLOOR(1 + RAND() * 5);
        INSERT INTO order_items (order_id, product_id, product_name, product_code, unit_price, quantity, subtotal)
        SELECT order_id, product_id, p.product_name, p.product_code, p.price, quantity, p.price * quantity
        FROM products p WHERE p.id = product_id;
        SET i = i + 1;
    END WHILE;
END //

DELIMITER ;

USE test_logs;

DELIMITER //

CREATE PROCEDURE IF NOT EXISTS generate_operation_logs(IN count INT)
BEGIN
    DECLARE i INT DEFAULT 1;
    WHILE i <= count DO
        INSERT INTO operation_logs (user_id, username, operation, module, resource_type, ip_address, request_method, request_url, response_status, response_time)
        VALUES (
            FLOOR(1 + RAND() * 500),
            CONCAT('user_', LPAD(FLOOR(1 + RAND() * 500), 5, '0')),
            ELT(FLOOR(1 + RAND() * 5), 'CREATE', 'UPDATE', 'DELETE', 'QUERY', 'LOGIN'),
            ELT(FLOOR(1 + RAND() * 6), 'user', 'order', 'product', 'datasource', 'metadata', 'asset'),
            ELT(FLOOR(1 + RAND() * 5), 'user', 'table', 'column', 'api', 'config'),
            CONCAT('192.168.', FLOOR(RAND() * 255), '.', FLOOR(RAND() * 255)),
            ELT(FLOOR(1 + RAND() * 4), 'GET', 'POST', 'PUT', 'DELETE'),
            CONCAT('/api/v1/', ELT(FLOOR(1 + RAND() * 6), 'users', 'orders', 'products', 'datasources', 'metadata', 'assets')),
            ELT(FLOOR(1 + RAND() * 3), 200, 400, 500),
            FLOOR(10 + RAND() * 500)
        );
        SET i = i + 1;
    END WHILE;
END //

-- 生成访问日志测试数据的存储过程
CREATE PROCEDURE IF NOT EXISTS generate_access_logs(IN count INT)
BEGIN
    DECLARE i INT DEFAULT 1;
    WHILE i <= count DO
        INSERT INTO access_logs (session_id, user_id, username, ip_address, user_agent, request_url, request_method, response_status, response_time)
        VALUES (
            CONCAT('session_', MD5(CONCAT(i, RAND())))),
            FLOOR(1 + RAND() * 500),
            CONCAT('user_', LPAD(FLOOR(1 + RAND() * 500), 5, '0')),
            CONCAT('192.168.', FLOOR(RAND() * 255), '.', FLOOR(RAND() * 255)),
            ELT(FLOOR(1 + RAND() * 4), 'Mozilla/5.0 (Windows)', 'Mozilla/5.0 (Macintosh)', 'Mozilla/5.0 (Linux)', 'Mobile Safari'),
            CONCAT('/api/v1/', ELT(FLOOR(1 + RAND() * 6), 'users', 'orders', 'products', 'datasources', 'metadata', 'assets')),
            ELT(FLOOR(1 + RAND() * 4), 'GET', 'POST', 'PUT', 'DELETE'),
            ELT(FLOOR(1 + RAND() * 3), 200, 400, 500),
            FLOOR(10 + RAND() * 500)
        );
        SET i = i + 1;
    END WHILE;
END //

DELIMITER ;

-- =============================================================================
-- 第七部分：生成初始测试数据
-- =============================================================================

-- 生成用户数据 (1000条)
CALL generate_users(1000);

-- 生成商品数据 (500条)
CALL generate_products(500);

-- 生成订单数据 (2000条)
CALL generate_orders(2000);

-- 生成订单详情数据 (5000条)
CALL generate_order_items(5000);

DELIMITER ;

-- 切换到日志数据库
USE test_logs;

DELIMITER //

CREATE PROCEDURE IF NOT EXISTS generate_operation_logs(IN count INT)
BEGIN
    DECLARE i INT DEFAULT 1;
    WHILE i <= count DO
        INSERT INTO operation_logs (user_id, username, operation, module, resource_type, ip_address, request_method, request_url, response_status, response_time)
        VALUES (
            FLOOR(1 + RAND() * 500),
            CONCAT('user_', LPAD(FLOOR(1 + RAND() * 500), 5, '0')),
            ELT(FLOOR(1 + RAND() * 5), 'CREATE', 'UPDATE', 'DELETE', 'QUERY', 'LOGIN'),
            ELT(FLOOR(1 + RAND() * 6), 'user', 'order', 'product', 'datasource', 'metadata', 'asset'),
            ELT(FLOOR(1 + RAND() * 5), 'user', 'table', 'column', 'api', 'config'),
            CONCAT('192.168.', FLOOR(RAND() * 255), '.', FLOOR(RAND() * 255)),
            ELT(FLOOR(1 + RAND() * 4), 'GET', 'POST', 'PUT', 'DELETE'),
            CONCAT('/api/v1/', ELT(FLOOR(1 + RAND() * 6), 'users', 'orders', 'products', 'datasources', 'metadata', 'assets')),
            ELT(FLOOR(1 + RAND() * 3), 200, 400, 500),
            FLOOR(10 + RAND() * 500)
        );
        SET i = i + 1;
    END WHILE;
END //

CREATE PROCEDURE IF NOT EXISTS generate_access_logs(IN count INT)
BEGIN
    DECLARE i INT DEFAULT 1;
    WHILE i <= count DO
        INSERT INTO access_logs (session_id, user_id, username, ip_address, user_agent, request_url, request_method, response_status, response_time)
        VALUES (
            CONCAT('session_', MD5(CONCAT(i, RAND())))),
            FLOOR(1 + RAND() * 500),
            CONCAT('user_', LPAD(FLOOR(1 + RAND() * 500), 5, '0')),
            CONCAT('192.168.', FLOOR(RAND() * 255), '.', FLOOR(RAND() * 255)),
            ELT(FLOOR(1 + RAND() * 4), 'Mozilla/5.0 (Windows)', 'Mozilla/5.0 (Macintosh)', 'Mozilla/5.0 (Linux)', 'Mobile Safari'),
            CONCAT('/api/v1/', ELT(FLOOR(1 + RAND() * 6), 'users', 'orders', 'products', 'datasources', 'metadata', 'assets')),
            ELT(FLOOR(1 + RAND() * 4), 'GET', 'POST', 'PUT', 'DELETE'),
            ELT(FLOOR(1 + RAND() * 3), 200, 400, 500),
            FLOOR(10 + RAND() * 500)
        );
        SET i = i + 1;
    END WHILE;
END //

DELIMITER ;

-- 生成操作日志数据 (5000条)
CALL generate_operation_logs(5000);

-- 生成访问日志数据 (10000条)
CALL generate_access_logs(10000);

-- =============================================================================
-- 完成提示
-- =============================================================================

SELECT 'Test data initialization completed!' AS message;
SELECT COUNT(*) AS user_count FROM test_ecommerce.users;
SELECT COUNT(*) AS product_count FROM test_ecommerce.products;
SELECT COUNT(*) AS order_count FROM test_ecommerce.orders;
SELECT COUNT(*) AS order_item_count FROM test_ecommerce.order_items;
SELECT COUNT(*) AS operation_log_count FROM test_logs.operation_logs;
SELECT COUNT(*) AS access_log_count FROM test_logs.access_logs;
