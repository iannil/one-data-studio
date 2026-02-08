#!/usr/bin/env python3
"""
ONE-DATA-STUDIO 测试数据生成器

功能：
- 生成 MySQL 测试数据
- 生成 PostgreSQL 测试数据
- 支持自定义数据量
- 支持数据校验

使用方法：
    python generate_test_data.py --db mysql --count 1000
    python generate_test_data.py --db postgres --count 1000
    python generate_test_data.py --db all --count 5000

依赖：
    pip install pymysql psycopg2-binary faker
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import random
import string

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# 数据生成器基类
# =============================================================================

class TestDataGenerator:
    """测试数据生成器基类"""

    def __init__(self, config: Dict[str, Any], e2e_mode: bool = False, persistent_mode: bool = False):
        self.config = config
        self.conn = None
        self.cursor = None
        self.e2e_mode = e2e_mode
        self.persistent_mode = persistent_mode
        # 根据模式使用不同的数据库名称
        if persistent_mode:
            self.db_ecommerce = "persistent_ecommerce"
            self.db_user_mgmt = "persistent_user_mgmt"
            self.db_logs = "persistent_logs"
        elif e2e_mode:
            self.db_ecommerce = "e2e_ecommerce"
            self.db_user_mgmt = "e2e_user_mgmt"
            self.db_logs = "e2e_logs"
        else:
            self.db_ecommerce = "test_ecommerce"
            self.db_user_mgmt = "test_user_mgmt"
            self.db_logs = "test_logs"
        self.default_ports = {
            'mysql': 3308,  # 测试环境 MySQL 端口
            'e2e_mysql': 3310,  # E2E MySQL 端口
            'manual_test_mysql': 3316,  # Manual Test MySQL 端口 (UI E2E)
            'postgres': 5436,  # 测试环境 PostgreSQL 端口
            'e2e_postgres': 5438,  # E2E PostgreSQL 端口
            'manual_test_postgres': 5442  # Manual Test PostgreSQL 端口 (UI E2E)
        }

        # 数据量验证阈值
        self.min_data_threshold = 1000  # 最少数据量

    def connect(self):
        """建立数据库连接"""
        raise NotImplementedError

    def close(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def generate_users(self, count: int) -> int:
        """生成用户数据"""
        raise NotImplementedError

    def generate_products(self, count: int) -> int:
        """生成商品数据"""
        raise NotImplementedError

    def generate_orders(self, count: int) -> int:
        """生成订单数据"""
        raise NotImplementedError

    def generate_order_items(self, count: int) -> int:
        """生成订单详情数据"""
        raise NotImplementedError

    def generate_logs(self, count: int) -> int:
        """生成日志数据"""
        raise NotImplementedError

    def validate_data(self) -> Dict[str, int]:
        """验证数据量"""
        raise NotImplementedError


# =============================================================================
# MySQL 数据生成器
# =============================================================================

class MySQLTestDataGenerator(TestDataGenerator):
    """MySQL 测试数据生成器"""

    def connect(self):
        import pymysql
        self.conn = pymysql.connect(
            host=self.config.get('host', 'localhost'),
            port=self.config.get('port', 3306),
            user=self.config.get('user', 'root'),
            password=self.config.get('password', 'rootdev123'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        self.cursor = self.conn.cursor()
        logger.info(f"Connected to MySQL at {self.config.get('host')}:{self.config.get('port')}")

    def generate_users(self, count: int) -> int:
        """生成用户数据"""
        sql = f"""
        INSERT INTO {self.db_ecommerce}.users (username, email, password_hash, nickname, gender, status)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        genders = ['male', 'female', 'other']
        statuses = ['active', 'inactive']

        batch_size = 1000
        inserted = 0

        for i in range(0, count, batch_size):
            batch_count = min(batch_size, count - i)
            values = []
            for j in range(batch_count):
                idx = i + j + 1
                username = f'user_{idx:05d}'
                email = f'{username}@example.com'
                values.append((
                    username,
                    email,
                    'hashed_password',
                    f'用户{idx}',
                    random.choice(genders),
                    random.choice(statuses)
                ))

            self.cursor.executemany(sql, values)
            self.conn.commit()
            inserted += batch_count
            logger.info(f"Generated {inserted}/{count} users")

        return inserted

    def generate_products(self, count: int) -> int:
        """生成商品数据"""
        sql = f"""
        INSERT INTO {self.db_ecommerce}.products (category_id, product_name, product_code, description, price, cost_price, stock_quantity, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        statuses = ['on_sale', 'off_sale', 'draft']
        brands = ['Apple', '华为', '小米', 'OPPO', 'vivo', '三星', '索尼', '戴尔', '联想']

        batch_size = 500
        inserted = 0

        for i in range(0, count, batch_size):
            batch_count = min(batch_size, count - i)
            values = []
            for j in range(batch_count):
                idx = i + j + 1
                product_code = f'PRD{datetime.now().strftime("%Y%m%d")}{idx:06d}'
                brand = random.choice(brands)
                price = round(random.uniform(10, 10000), 2)

                values.append((
                    random.randint(1, 10),
                    f'{brand}测试商品{idx}',
                    product_code,
                    f'这是{brand}测试商品{idx}的详细描述信息，包含产品特点、规格参数等内容。',
                    price,
                    round(price * random.uniform(0.5, 0.8), 2),
                    random.randint(10, 1000),
                    random.choice(statuses)
                ))

            self.cursor.executemany(sql, values)
            self.conn.commit()
            inserted += batch_count
            logger.info(f"Generated {inserted}/{count} products")

        return inserted

    def generate_orders(self, count: int) -> int:
        """生成订单数据"""
        sql = f"""
        INSERT INTO {self.db_ecommerce}.orders (order_no, user_id, total_amount, actual_amount, status, receiver_name, receiver_phone, receiver_address)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        statuses = ['pending', 'paid', 'shipped', 'completed', 'cancelled']

        # 先获取实际的用户数量，确保 user_id 在有效范围内
        try:
            self.cursor.execute(f"SELECT COUNT(*) as cnt FROM {self.db_ecommerce}.users")
            user_count = self.cursor.fetchone()['cnt']
            if user_count is None or user_count == 0:
                user_count = 100  # 默认值
        except:
            user_count = 100

        batch_size = 500
        inserted = 0

        for i in range(0, count, batch_size):
            batch_count = min(batch_size, count - i)
            values = []
            for j in range(batch_count):
                idx = i + j + 1
                # 使用实际用户数量范围内的随机值
                user_id = random.randint(1, max(1, user_count))
                total_amount = round(random.uniform(50, 5000), 2)

                values.append((
                    f'ORD{datetime.now().strftime("%Y%m%d%H%M%S")}{idx:04d}',
                    user_id,
                    total_amount,
                    total_amount,
                    random.choice(statuses),
                    f'收货人{user_id}',
                    f'138{random.randint(10000000, 99999999)}',
                    f'测试省测试市测试区测试街道{idx}号'
                ))

            self.cursor.executemany(sql, values)
            self.conn.commit()
            inserted += batch_count
            logger.info(f"Generated {inserted}/{count} orders")

        return inserted

    def generate_order_items(self, count: int) -> int:
        """生成订单详情数据"""
        # 先获取商品信息
        self.cursor.execute(f"SELECT id, price, product_name, product_code FROM {self.db_ecommerce}.products LIMIT 1000")
        products = self.cursor.fetchall()

        if not products:
            logger.warning("No products found, skipping order items generation")
            return 0

        # 获取实际订单数量
        try:
            self.cursor.execute(f"SELECT COUNT(*) as cnt FROM {self.db_ecommerce}.orders")
            order_count = self.cursor.fetchone()['cnt']
            if order_count is None or order_count == 0:
                order_count = 100  # 默认值
        except:
            order_count = 100

        sql = f"""
        INSERT INTO {self.db_ecommerce}.order_items (order_id, product_id, product_name, product_code, unit_price, quantity, subtotal)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        batch_size = 1000
        inserted = 0

        for i in range(0, count, batch_size):
            batch_count = min(batch_size, count - i)
            values = []
            for j in range(batch_count):
                # 使用实际订单数量范围内的随机值
                order_id = random.randint(1, max(1, order_count))
                product = random.choice(products)
                quantity = random.randint(1, 5)
                subtotal = round(product['price'] * quantity, 2)

                values.append((
                    order_id,
                    product['id'],
                    product['product_name'],
                    product['product_code'],
                    product['price'],
                    quantity,
                    subtotal
                ))

            self.cursor.executemany(sql, values)
            self.conn.commit()
            inserted += batch_count
            logger.info(f"Generated {inserted}/{count} order items")

        return inserted

    def generate_logs(self, count: int) -> int:
        """生成日志数据"""
        operation_sql = f"""
        INSERT INTO {self.db_logs}.operation_logs (user_id, username, operation, module, resource_type, ip_address, request_method, request_url, response_status, response_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        access_sql = f"""
        INSERT INTO {self.db_logs}.access_logs (session_id, user_id, username, ip_address, user_agent, request_url, request_method, response_status, response_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        operations = ['CREATE', 'UPDATE', 'DELETE', 'QUERY', 'LOGIN', 'LOGOUT']
        modules = ['user', 'order', 'product', 'datasource', 'metadata', 'asset']
        resource_types = ['user', 'table', 'column', 'api', 'config']
        request_methods = ['GET', 'POST', 'PUT', 'DELETE']
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
        ]

        batch_size = 2000
        inserted_ops = 0
        inserted_access = 0

        # 生成操作日志 (count * 0.3)
        op_count = int(count * 0.3)

        for i in range(0, op_count, batch_size):
            batch_count = min(batch_size, op_count - i)
            values = []
            for j in range(batch_count):
                user_id = random.randint(1, 500)
                values.append((
                    user_id,
                    f'user_{user_id:05d}',
                    random.choice(operations),
                    random.choice(modules),
                    random.choice(resource_types),
                    f'192.168.{random.randint(1, 255)}.{random.randint(1, 255)}',
                    random.choice(request_methods),
                    f'/api/v1/{random.choice(modules)}',
                    random.choice([200, 200, 200, 400, 500]),
                    random.randint(10, 500)
                ))

            self.cursor.executemany(operation_sql, values)
            self.conn.commit()
            inserted_ops += batch_count

        # 生成访问日志 (count * 0.7)
        access_count = count - op_count

        for i in range(0, access_count, batch_size):
            batch_count = min(batch_size, access_count - i)
            values = []
            for j in range(batch_count):
                user_id = random.randint(1, 500)
                values.append((
                    f'session_{random.randint(100000, 999999)}',
                    user_id if random.random() > 0.3 else None,
                    f'user_{user_id:05d}' if random.random() > 0.3 else None,
                    f'192.168.{random.randint(1, 255)}.{random.randint(1, 255)}',
                    random.choice(user_agents),
                    f'/api/v1/{random.choice(modules)}',
                    random.choice(request_methods),
                    random.choice([200, 200, 200, 400, 500]),
                    random.randint(10, 500)
                ))

            self.cursor.executemany(access_sql, values)
            self.conn.commit()
            inserted_access += batch_count

        logger.info(f"Generated {inserted_ops} operation logs and {inserted_access} access logs")
        return inserted_ops + inserted_access

    def validate_data(self) -> Dict[str, int]:
        """验证 MySQL 数据量"""
        result = {}

        try:
            # 验证用户数据
            self.cursor.execute(f"SELECT COUNT(*) FROM {self.db_ecommerce}.users")
            result['users'] = self.cursor.fetchone()['COUNT(*)']

            # 验证商品数据
            self.cursor.execute(f"SELECT COUNT(*) FROM {self.db_ecommerce}.products")
            result['products'] = self.cursor.fetchone()['COUNT(*)']

            # 验证订单数据
            self.cursor.execute(f"SELECT COUNT(*) FROM {self.db_ecommerce}.orders")
            result['orders'] = self.cursor.fetchone()['COUNT(*)']

            # 验证订单详情数据
            self.cursor.execute(f"SELECT COUNT(*) FROM {self.db_ecommerce}.order_items")
            result['order_items'] = self.cursor.fetchone()['COUNT(*)']

            # 验证操作日志
            self.cursor.execute(f"SELECT COUNT(*) FROM {self.db_logs}.operation_logs")
            result['operation_logs'] = self.cursor.fetchone()['COUNT(*)']

            # 验证访问日志
            self.cursor.execute(f"SELECT COUNT(*) FROM {self.db_logs}.access_logs")
            result['access_logs'] = self.cursor.fetchone()['COUNT(*)']

        except Exception as e:
            logger.error(f"Data validation failed: {e}")

        return result


# =============================================================================
# PostgreSQL 数据生成器
# =============================================================================

class PostgresTestDataGenerator(TestDataGenerator):
    """PostgreSQL 测试数据生成器"""

    def connect(self):
        import psycopg2
        self.conn = psycopg2.connect(
            host=self.config.get('host', 'localhost'),
            port=self.config.get('port', 5436),
            user=self.config.get('user', 'postgres'),
            password=self.config.get('password', 'postgresdev123'),
            database=self.config.get('database', 'test_ecommerce_pg')
        )
        self.cursor = self.conn.cursor()
        logger.info(f"Connected to PostgreSQL at {self.config.get('host')}:{self.config.get('port')}")

    def generate_users(self, count: int) -> int:
        """生成用户数据"""
        sql = """
        INSERT INTO users (username, email, password_hash, nickname, gender, status)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (username) DO NOTHING
        """
        genders = ['male', 'female', 'other']
        statuses = ['active', 'inactive']

        batch_size = 1000
        inserted = 0

        for i in range(0, count, batch_size):
            batch_count = min(batch_size, count - i)
            values = []
            for j in range(batch_count):
                idx = i + j + 1
                username = f'user_{idx:05d}'
                email = f'{username}@example.com'
                values.append((
                    username,
                    email,
                    'hashed_password',
                    f'用户{idx}',
                    random.choice(genders),
                    random.choice(statuses)
                ))

            self.cursor.executemany(sql, values)
            self.conn.commit()
            inserted += self.cursor.rowcount
            logger.info(f"Generated {inserted}/{count} users")

        return inserted

    def generate_products(self, count: int) -> int:
        """生成商品数据"""
        sql = """
        INSERT INTO products (category_id, product_name, product_code, description, price, cost_price, stock_quantity, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        statuses = ['on_sale', 'off_sale', 'draft']
        brands = ['Apple', '华为', '小米', 'OPPO', 'vivo', '三星', '戴尔', '联想']

        batch_size = 500
        inserted = 0

        for i in range(0, count, batch_size):
            batch_count = min(batch_size, count - i)
            values = []
            for j in range(batch_count):
                idx = i + j + 1
                product_code = f'PRD{datetime.now().strftime("%Y%m%d")}{idx:06d}'
                brand = random.choice(brands)
                price = round(random.uniform(10, 10000), 2)

                values.append((
                    random.randint(1, 10),
                    f'{brand}测试商品{idx}',
                    product_code,
                    f'这是{brand}测试商品{idx}的详细描述信息',
                    price,
                    round(price * random.uniform(0.5, 0.8), 2),
                    random.randint(10, 1000),
                    random.choice(statuses)
                ))

            self.cursor.executemany(sql, values)
            self.conn.commit()
            inserted += self.cursor.rowcount
            logger.info(f"Generated {inserted}/{count} products")

        return inserted

    def generate_orders(self, count: int) -> int:
        """生成订单数据"""
        sql = """
        INSERT INTO orders (order_no, user_id, total_amount, actual_amount, status, receiver_name, receiver_phone, receiver_address)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        statuses = ['pending', 'paid', 'shipped', 'completed', 'cancelled']

        # 获取实际的用户数量
        try:
            self.cursor.execute("SELECT COUNT(*) as cnt FROM users")
            user_count = self.cursor.fetchone()[0]
            if user_count is None or user_count == 0:
                user_count = 100
        except:
            user_count = 100

        batch_size = 500
        inserted = 0

        for i in range(0, count, batch_size):
            batch_count = min(batch_size, count - i)
            values = []
            for j in range(batch_count):
                idx = i + j + 1
                # 使用实际用户数量范围内的随机值
                user_id = random.randint(1, max(1, user_count))
                total_amount = round(random.uniform(50, 5000), 2)

                values.append((
                    f'ORD{datetime.now().strftime("%Y%m%d%H%M%S")}{idx:04d}',
                    user_id,
                    total_amount,
                    total_amount,
                    random.choice(statuses),
                    f'收货人{user_id}',
                    f'138{random.randint(10000000, 99999999)}',
                    f'测试地址{idx}号'
                ))

            self.cursor.executemany(sql, values)
            self.conn.commit()
            inserted += self.cursor.rowcount
            logger.info(f"Generated {inserted}/{count} orders")

        return inserted

    def generate_logs(self, count: int) -> int:
        """生成日志数据（仅支持操作日志）"""
        # PostgreSQL 日志数据库需要单独连接，这里简化处理
        logger.info("Log generation for PostgreSQL not implemented in this version")
        return 0

    def validate_data(self) -> Dict[str, int]:
        """验证 PostgreSQL 数据量"""
        result = {}

        try:
            # 验证用户数据
            self.cursor.execute("SELECT COUNT(*) FROM users")
            result['users'] = self.cursor.fetchone()[0]

            # 验证商品数据
            self.cursor.execute("SELECT COUNT(*) FROM products")
            result['products'] = self.cursor.fetchone()[0]

            # 验证订单数据
            self.cursor.execute("SELECT COUNT(*) FROM orders")
            result['orders'] = self.cursor.fetchone()[0]

            # 验证订单详情数据
            self.cursor.execute("SELECT COUNT(*) FROM order_items")
            result['order_items'] = self.cursor.fetchone()[0]

        except Exception as e:
            logger.error(f"Data validation failed: {e}")

        return result


# =============================================================================
# 主函数
# =============================================================================

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='ONE-DATA-STUDIO 测试数据生成器')
    parser.add_argument('--db', choices=['mysql', 'postgres', 'all'], default='mysql',
                        help='数据库类型 (默认: mysql)')
    parser.add_argument('--count', type=int, default=20000,
                        help='总数据量 (默认: 20000)')
    parser.add_argument('--e2e', action='store_true',
                        help='E2E 模式：使用 E2E 端口 (3310/5438) 和数据库')
    parser.add_argument('--manual-test', action='store_true',
                        help='Manual Test 模式：使用 Manual Test 端口 (3316/5442) 和数据库')
    parser.add_argument('--persistent-test', action='store_true',
                        help='Persistent Test 模式：使用 Persistent Test 端口 (3325/5450) 和数据库')
    parser.add_argument('--mysql-host', default='localhost',
                        help='MySQL 主机 (默认: localhost)')
    parser.add_argument('--mysql-port', type=int, default=3308,
                        help='MySQL 端口 (默认: 3308, E2E模式: 3310, Manual Test模式: 3316, Persistent模式: 3325)')
    parser.add_argument('--mysql-user', default='root',
                        help='MySQL 用户 (默认: root)')
    parser.add_argument('--mysql-password', default='rootdev123',
                        help='MySQL 密码 (默认: rootdev123, E2E模式: e2eroot123, Manual Test模式: testroot123, Persistent模式: persistent123)')
    parser.add_argument('--postgres-host', default='localhost',
                        help='PostgreSQL 主机 (默认: localhost)')
    parser.add_argument('--postgres-port', type=int, default=5436,
                        help='PostgreSQL 端口 (默认: 5436, E2E模式: 5438, Manual Test模式: 5442, Persistent模式: 5450)')
    parser.add_argument('--postgres-user', default='postgres',
                        help='PostgreSQL 用户 (默认: postgres)')
    parser.add_argument('--postgres-password', default='postgresdev123',
                        help='PostgreSQL 密码 (默认: postgresdev123, E2E模式: e2epostgres123, Manual Test模式: testpg123, Persistent模式: persistentpg123)')
    parser.add_argument('--verify', action='store_true',
                        help='验证生成数据量')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='详细输出')

    args = parser.parse_args()

    # E2E 模式参数覆盖
    if args.e2e:
        args.mysql_port = 3310
        args.mysql_password = 'e2eroot123'
        args.postgres_port = 5438
        args.postgres_password = 'e2epostgres123'
        logger.info("E2E mode enabled: MySQL port=3310, PostgreSQL port=5438")

    # Manual Test 模式参数覆盖
    if args.manual_test:
        args.mysql_port = 3316
        args.mysql_password = 'testroot123'
        args.postgres_port = 5442
        args.postgres_password = 'testpg123'
        logger.info("Manual Test mode enabled: MySQL port=3316, PostgreSQL port=5442")

    # Persistent Test 模式参数覆盖
    if args.persistent_test:
        args.mysql_port = 3325
        args.mysql_password = 'persistent123'
        args.postgres_port = 5450
        args.postgres_password = 'persistentpg123'
        logger.info("Persistent Test mode enabled: MySQL port=3325, PostgreSQL port=5450")

    return args


def generate_mysql_data(args) -> bool:
    """生成 MySQL 测试数据"""
    config = {
        'host': args.mysql_host,
        'port': args.mysql_port,
        'user': args.mysql_user,
        'password': args.mysql_password,
    }

    e2e_mode = getattr(args, 'e2e', False)
    persistent_mode = getattr(args, 'persistent_test', False)
    generator = MySQLTestDataGenerator(config, e2e_mode=e2e_mode, persistent_mode=persistent_mode)

    try:
        generator.connect()

        # 按比例分配数据
        user_count = int(args.count * 0.05)  # 5%
        product_count = int(args.count * 0.025)  # 2.5%
        order_count = int(args.count * 0.10)  # 10%
        order_item_count = int(args.count * 0.25)  # 25%
        log_count = args.count - user_count - product_count - order_count - order_item_count  # 剩余

        logger.info(f"Starting MySQL data generation:")
        logger.info(f"  - Users: {user_count}")
        logger.info(f"  - Products: {product_count}")
        logger.info(f"  - Orders: {order_count}")
        logger.info(f"  - Order Items: {order_item_count}")
        logger.info(f"  - Logs: {log_count}")

        generator.generate_users(user_count)
        generator.generate_products(product_count)
        generator.generate_orders(order_count)
        generator.generate_order_items(order_item_count)
        generator.generate_logs(log_count)

        # 验证数据量
        if args.verify:
            logger.info("Verifying generated data...")
            data_summary = generator.validate_data()
            for table, count in data_summary.items():
                logger.info(f"  - {table}: {count} records")
                if count < generator.min_data_threshold and table in ['users', 'products', 'orders']:
                    logger.warning(f"  Warning: {table} count is below minimum threshold ({generator.min_data_threshold})")

        logger.info("MySQL data generation completed successfully!")
        return True

    except Exception as e:
        logger.error(f"MySQL data generation failed: {e}")
        return False
    finally:
        generator.close()


def generate_postgres_data(args) -> bool:
    """生成 PostgreSQL 测试数据"""
    e2e_mode = getattr(args, 'e2e', False)
    manual_test_mode = getattr(args, 'manual_test', False)
    persistent_mode = getattr(args, 'persistent_test', False)

    # 根据模式选择数据库名称
    if persistent_mode:
        database_name = 'persistent_ecommerce_pg'
    elif e2e_mode:
        database_name = 'e2e_ecommerce_pg'
    elif manual_test_mode:
        database_name = 'test_ecommerce_pg'
    else:
        database_name = 'test_ecommerce_pg'

    config = {
        'host': args.postgres_host,
        'port': args.postgres_port,
        'user': args.postgres_user,
        'password': args.postgres_password,
        'database': database_name,
    }

    generator = PostgresTestDataGenerator(config, e2e_mode=e2e_mode, persistent_mode=persistent_mode)

    try:
        generator.connect()

        # 按比例分配数据
        user_count = int(args.count * 0.05)
        product_count = int(args.count * 0.025)
        order_count = int(args.count * 0.10)

        logger.info(f"Starting PostgreSQL data generation:")
        logger.info(f"  - Database: {database_name}")
        logger.info(f"  - Users: {user_count}")
        logger.info(f"  - Products: {product_count}")
        logger.info(f"  - Orders: {order_count}")

        generator.generate_users(user_count)
        generator.generate_products(product_count)
        generator.generate_orders(order_count)

        # 验证数据量
        if args.verify:
            logger.info("Verifying generated data...")
            data_summary = generator.validate_data()
            for table, count in data_summary.items():
                logger.info(f"  - {table}: {count} records")
                if count < generator.min_data_threshold and table in ['users', 'products', 'orders']:
                    logger.warning(f"  Warning: {table} count is below minimum threshold ({generator.min_data_threshold})")

        logger.info("PostgreSQL data generation completed successfully!")
        return True

    except Exception as e:
        logger.error(f"PostgreSQL data generation failed: {e}")
        return False
    finally:
        generator.close()


def main():
    """主函数"""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    start_time = datetime.now()

    logger.info("=" * 60)
    logger.info("ONE-DATA-STUDIO 测试数据生成器")
    logger.info("=" * 60)
    logger.info(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"数据库类型: {args.db}")
    logger.info(f"目标数据量: {args.count}")
    logger.info("=" * 60)

    success = True

    if args.db in ['mysql', 'all']:
        if not generate_mysql_data(args):
            success = False

    if args.db in ['postgres', 'all']:
        if not generate_postgres_data(args):
            success = False

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    logger.info("=" * 60)
    if success:
        logger.info("数据生成完成!")
    else:
        logger.error("数据生成失败!")
    logger.info(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"总耗时: {duration:.2f} 秒")
    logger.info("=" * 60)

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
