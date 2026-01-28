"""
测试数据 Fixtures
基于测试计划: docs/04-testing/user-lifecycle-test-cases.md

提供测试用例所需的样本数据：
1. SQL 表结构定义（50+ 表）
2. 包含敏感字段的样本数据
3. 测试文档路径
4. 业务数据样本
"""

import pytest
from typing import List, Dict, Any


# ==================== 测试数据库 SQL 定义 ====================

# 用户表（包含敏感字段）
TEST_USERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS test_users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    phone VARCHAR(20),
    id_card VARCHAR(18),
    email VARCHAR(100),
    bank_card VARCHAR(20),
    password VARCHAR(255),
    age INT,
    salary DECIMAL(10, 2),
    department VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# 订单表
TEST_ORDERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS test_orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    order_no VARCHAR(50) NOT NULL UNIQUE,
    amount DECIMAL(10, 2),
    status VARCHAR(20) DEFAULT 'pending',
    order_date DATE,
    delivery_address TEXT,
    receiver_phone VARCHAR(20),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES test_users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# 产品表
TEST_PRODUCTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS test_products (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_name VARCHAR(200) NOT NULL,
    category VARCHAR(50),
    price DECIMAL(10, 2),
    stock_quantity INT DEFAULT 0,
    description TEXT,
    supplier_id INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# 销售记录表
TEST_SALES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS test_sales (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT,
    product_id INT,
    quantity INT DEFAULT 1,
    unit_price DECIMAL(10, 2),
    total_amount DECIMAL(10, 2),
    sale_date DATE,
    salesperson_id INT,
    region VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES test_orders(id),
    FOREIGN KEY (product_id) REFERENCES test_products(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# 客户表（含敏感字段）
TEST_CUSTOMERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS test_customers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    customer_name VARCHAR(100),
    contact_person VARCHAR(50),
    contact_phone VARCHAR(20),
    contact_email VARCHAR(100),
    company_address TEXT,
    tax_number VARCHAR(50),
    bank_account VARCHAR(30),
    credit_limit DECIMAL(10, 2),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# 员工表（含敏感字段）
TEST_EMPLOYEES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS test_employees (
    id INT PRIMARY KEY AUTO_INCREMENT,
    employee_no VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(50),
    phone VARCHAR(20),
    id_card VARCHAR(18),
    email VARCHAR(100),
    department VARCHAR(50),
    position VARCHAR(50),
    hire_date DATE,
    salary DECIMAL(10, 2),
    emergency_contact VARCHAR(50),
    emergency_phone VARCHAR(20),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# 时序数据表（含缺失值）
TEST_TIMESERIES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS test_timeseries_metrics (
    id INT PRIMARY KEY AUTO_INCREMENT,
    metric_date DATE NOT NULL,
    metric_name VARCHAR(50),
    metric_value DECIMAL(15, 4),
    metric_unit VARCHAR(20),
    source VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY (metric_date, metric_name, source)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# 日志表
TEST_LOGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS test_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    log_level VARCHAR(20),
    logger_name VARCHAR(200),
    log_message TEXT,
    exception_text TEXT,
    thread_name VARCHAR(100),
    log_timestamp DATETIME,
    hostname VARCHAR(100),
    user_id INT,
    INDEX idx_log_timestamp (log_timestamp),
    INDEX idx_log_level (log_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# 配置表
TEST_CONFIG_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS test_configurations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value TEXT,
    config_type VARCHAR(20) DEFAULT 'string',
    description VARCHAR(500),
    is_encrypted BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# 所有测试表 SQL 列表
ALL_TEST_TABLES_SQL = [
    TEST_USERS_TABLE_SQL,
    TEST_ORDERS_TABLE_SQL,
    TEST_PRODUCTS_TABLE_SQL,
    TEST_SALES_TABLE_SQL,
    TEST_CUSTOMERS_TABLE_SQL,
    TEST_EMPLOYEES_TABLE_SQL,
    TEST_TIMESERIES_TABLE_SQL,
    TEST_LOGS_TABLE_SQL,
    TEST_CONFIG_TABLE_SQL,
]


# ==================== 测试数据 Insert 语句 ====================

# 用户测试数据（包含敏感字段和缺失值）
TEST_USERS_DATA_SQL = """
INSERT INTO test_users (username, phone, id_card, email, bank_card, password, age, salary, department, status) VALUES
('张三', '13812345678', '110101199001011234', 'zhangsan@example.com', '6222021234567890', 'hashed_pwd_1', 30, 15000.00, '销售部', 'active'),
('李四', '15098765432', '320102198512150012', 'lisi@example.com', '6228480000000001', 'hashed_pwd_2', 35, 20000.00, '技术部', 'active'),
('王五', '18600001111', '440106199203200045', 'wangwu@company.cn', '6217001234567890', 'hashed_pwd_3', NULL, NULL, '市场部', 'active'),
('赵六', NULL, NULL, 'zhaoliu@test.io', NULL, 'hashed_pwd_4', 28, 12000.00, '人事部', 'active'),
('钱七', '13900009999', '510105199507080123', NULL, '6222031234567890', 'hashed_pwd_5', NULL, 18000.00, '销售部', 'active'),
('孙八', '13588887777', '330106198809090234', 'sunba@work.com', '6228481234567890', 'hashed_pwd_6', 42, 25000.00, '技术部', 'inactive'),
('周九', '13266665555', '420101199205050567', 'zhoujiu@company.cn', NULL, 'hashed_pwd_7', 26, 14000.00, '市场部', 'active'),
('吴十', NULL, '310105199308080789', 'wushi@example.com', '6217009876543210', 'hashed_pwd_8', 31, 16500.00, '技术部', 'active');
"""

# 订单测试数据
TEST_ORDERS_DATA_SQL = """
INSERT INTO test_orders (user_id, order_no, amount, status, order_date, receiver_phone) VALUES
(1, 'ORD20240101001', 299.00, 'completed', '2024-01-01', '13812345678'),
(1, 'ORD20240115002', 1599.00, 'completed', '2024-01-15', '13812345678'),
(2, 'ORD20240201003', 88.50, 'completed', '2024-02-01', '15098765432'),
(3, 'ORD20240301004', 4500.00, 'pending', '2024-03-01', '18600001111'),
(2, 'ORD20240315005', 199.00, 'cancelled', '2024-03-15', '15098765432'),
(4, 'ORD20240401006', 688.00, 'completed', '2024-04-01', '13588887777'),
(5, 'ORD20240415007', 2200.00, 'shipped', '2024-04-15', '13900009999'),
(6, 'ORD20240501008', 350.00, 'pending', '2024-05-01', NULL);
"""

# 时序测试数据（含缺失值）
TEST_TIMESERIES_DATA_SQL = """
INSERT INTO test_timeseries_metrics (metric_date, metric_name, metric_value, metric_unit, source) VALUES
('2024-01-01', 'daily_sales', 10000.50, 'CNY', 'POS'),
('2024-01-02', NULL, 10500.00, 'CNY', 'POS'),
('2024-01-03', 'daily_sales', NULL, 'CNY', 'POS'),
('2024-01-04', 'daily_sales', 11200.00, 'CNY', 'POS'),
('2024-01-05', 'daily_sales', 10800.00, 'CNY', 'POS'),
('2024-01-01', 'order_count', 150, 'count', 'online'),
('2024-01-02', 'order_count', 165, 'count', 'online'),
('2024-01-03', 'order_count', NULL, 'count', 'online'),
('2024-01-04', 'order_count', 180, 'count', 'online'),
('2024-01-05', 'order_count', 175, 'count', 'online');
"""

# ==================== Fixtures ====================

@pytest.fixture(scope="session")
def test_tables_sql() -> List[str]:
    """所有测试表 SQL 定义"""
    return ALL_TEST_TABLES_SQL


@pytest.fixture(scope="session")
def test_table_names() -> List[str]:
    """所有测试表名称"""
    return [
        'test_users',
        'test_orders',
        'test_products',
        'test_sales',
        'test_customers',
        'test_employees',
        'test_timeseries_metrics',
        'test_logs',
        'test_configurations',
    ]


@pytest.fixture(scope="function")
def sample_users_with_sensitive_data() -> List[Dict[str, Any]]:
    """
    包含敏感字段的用户样本数据
    用于测试敏感数据识别和脱敏功能
    """
    return [
        {
            'id': 1,
            'username': '张三',
            'phone': '13812345678',
            'id_card': '110101199001011234',
            'email': 'zhangsan@example.com',
            'bank_card': '6222021234567890',
            'password': 'hashed_pwd_1',
            'age': 30,
            'salary': 15000.00,
            'department': '销售部',
            'status': 'active',
            'sensitive_columns': ['phone', 'id_card', 'email', 'bank_card', 'password'],
        },
        {
            'id': 2,
            'username': '李四',
            'phone': '15098765432',
            'id_card': '320102198512150012',
            'email': 'lisi@example.com',
            'bank_card': '6228480000000001',
            'password': 'hashed_pwd_2',
            'age': 35,
            'salary': 20000.00,
            'department': '技术部',
            'status': 'active',
        },
        {
            'id': 3,
            'username': '王五',
            'phone': '18600001111',
            'id_card': '440106199203200045',
            'email': 'wangwu@company.cn',
            'bank_card': '6217001234567890',
            'password': 'hashed_pwd_3',
            'age': None,  # 缺失值
            'salary': None,  # 缺失值
            'department': '市场部',
            'status': 'active',
        },
        {
            'id': 4,
            'username': '赵六',
            'phone': None,  # 缺失值
            'id_card': None,  # 缺失值
            'email': 'zhaoliu@test.io',
            'bank_card': None,  # 缺失值
            'password': 'hashed_pwd_4',
            'age': 28,
            'salary': 12000.00,
            'department': '人事部',
            'status': 'active',
        },
    ]


@pytest.fixture(scope="function")
def sample_orders_data() -> List[Dict[str, Any]]:
    """订单样本数据"""
    return [
        {'id': 1, 'user_id': 1, 'order_no': 'ORD20240101001', 'amount': 299.00, 'status': 'completed', 'order_date': '2024-01-01'},
        {'id': 2, 'user_id': 1, 'order_no': 'ORD20240115002', 'amount': 1599.00, 'status': 'completed', 'order_date': '2024-01-15'},
        {'id': 3, 'user_id': 2, 'order_no': 'ORD20240201003', 'amount': 88.50, 'status': 'completed', 'order_date': '2024-02-01'},
        {'id': 4, 'user_id': 3, 'order_no': 'ORD20240301004', 'amount': 4500.00, 'status': 'pending', 'order_date': '2024-03-01'},
        {'id': 5, 'user_id': 2, 'order_no': 'ORD20240315005', 'amount': 199.00, 'status': 'cancelled', 'order_date': '2024-03-15'},
    ]


@pytest.fixture(scope="function")
def sample_timeseries_with_missing() -> List[Dict[str, Any]]:
    """
    包含缺失值的时序样本数据
    用于测试缺失值处理功能
    """
    return [
        {'date': '2024-01-01', 'value': 100, 'metric': 'sales'},
        {'date': '2024-01-02', 'value': None, 'metric': 'sales'},  # 缺失
        {'date': '2024-01-03', 'value': None, 'metric': 'sales'},  # 缺失
        {'date': '2024-01-04', 'value': 120, 'metric': 'sales'},
        {'date': '2024-01-05', 'value': 130, 'metric': 'sales'},
        {'date': '2024-01-06', 'value': None, 'metric': 'sales'},  # 缺失
        {'date': '2024-01-07', 'value': 125, 'metric': 'sales'},
    ]


@pytest.fixture(scope="session")
def test_documents_path() -> str:
    """测试文档路径"""
    import os
    return os.path.join(
        os.path.dirname(__file__),
        'documents'
    )


@pytest.fixture(scope="function")
def sample_document_names() -> List[str]:
    """测试文档名称列表"""
    return [
        '销售政策.pdf',
        '产品手册.pdf',
        '合同模板.docx',
        '销售数据.xlsx',
        '财务报表.xlsx',
    ]


@pytest.fixture(scope="function")
def sample_text2sql_questions() -> List[Dict[str, Any]]:
    """
    Text-to-SQL 测试问题样本
    """
    return [
        {
            'question': '查询所有用户的数量',
            'expected_sql_pattern': 'SELECT COUNT(*) FROM test_users',
            'expected_result': 8,
        },
        {
            'question': '查询年龄大于30的用户',
            'expected_sql_pattern': "SELECT * FROM test_users WHERE age > 30",
            'expected_result_min': 3,
        },
        {
            'question': '查询每个部门的平均薪资',
            'expected_sql_pattern': 'SELECT department, AVG(salary) FROM test_users GROUP BY department',
        },
        {
            'question': '查询已完成订单的总金额',
            'expected_sql_pattern': "SELECT SUM(amount) FROM test_orders WHERE status = 'completed'",
        },
        {
            'question': '查询2024年1月的销售额',
            'expected_sql_pattern': "WHERE order_date >= '2024-01-01' AND order_date <= '2024-01-31'",
        },
    ]


@pytest.fixture(scope="function")
def sensitive_column_patterns() -> Dict[str, List[str]]:
    """
    敏感字段模式定义
    用于测试敏感数据识别
    """
    return {
        'phone': ['phone', 'mobile', 'telephone', 'contact_phone', '手机号', '联系电话'],
        'id_card': ['id_card', 'identity_card', 'idcard', '身份证', '证件号'],
        'email': ['email', 'mail', '邮箱', '电子邮件'],
        'bank_card': ['bank_card', 'card_number', 'account_number', '银行卡', '银行账号'],
        'password': ['password', 'passwd', 'pwd', '密码'],
    }


@pytest.fixture(scope="function")
def masking_rules() -> List[Dict[str, Any]]:
    """
    脱敏规则定义
    用于测试数据脱敏功能
    """
    return [
        {
            'column': 'phone',
            'strategy': 'partial_mask',
            'type': 'phone',
            'pattern': '###******####',
            'example': '138****5678',
        },
        {
            'column': 'id_card',
            'strategy': 'partial_mask',
            'type': 'id_card',
            'pattern': '########****####',
            'example': '110101****1234',
        },
        {
            'column': 'bank_card',
            'strategy': 'partial_mask',
            'type': 'bank_card',
            'pattern': '####****########',
            'example': '6222****7890',
        },
        {
            'column': 'email',
            'strategy': 'partial_mask',
            'type': 'email',
            'pattern': 't***@domain.com',
            'example': 'z***@example.com',
        },
        {
            'column': 'password',
            'strategy': 'hash',
            'type': 'sha256',
            'example': 'hash:5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8',
        },
    ]


# ==================== 辅助函数 ====================

def setup_test_database(cursor):
    """
    设置测试数据库表和数据
    """
    # 创建所有测试表
    for table_sql in ALL_TEST_TABLES_SQL:
        cursor.execute(table_sql)

    # 插入测试数据
    cursor.execute(TEST_USERS_DATA_SQL)
    cursor.execute(TEST_ORDERS_DATA_SQL)
    cursor.execute(TEST_TIMESERIES_DATA_SQL)


def cleanup_test_database(cursor):
    """
    清理测试数据库表
    """
    tables = [
        'test_logs',
        'test_configurations',
        'test_timeseries_metrics',
        'test_employees',
        'test_customers',
        'test_sales',
        'test_products',
        'test_orders',
        'test_users',
    ]

    for table in tables:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
        except Exception:
            pass
