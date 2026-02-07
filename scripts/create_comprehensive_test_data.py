#!/usr/bin/env python3
"""
创建完整测试数据脚本 - 为 DataOps 平台所有页面生成演示数据
Usage:
    python scripts/create_comprehensive_test_data.py
"""

import os
import sys
import random
import string
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import pymysql
except ImportError:
    print("Installing pymysql...")
    os.system("pip install pymysql -q")
    import pymysql


def get_connection():
    """获取数据库连接"""
    return pymysql.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', '3306')),
        user=os.getenv('MYSQL_USER', 'onedata'),
        password=os.getenv('MYSQL_PASSWORD', 'dev123'),
        database=os.getenv('MYSQL_DATABASE', 'onedata'),
        charset='utf8mb4'
    )


def random_id(prefix=None):
    """生成随机ID"""
    if prefix:
        return f"{prefix}_{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}"
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))


def random_date(days_ago=30):
    """生成随机日期"""
    return datetime.now() - timedelta(days=random.randint(0, days_ago), hours=random.randint(0, 23))


def create_tables(cursor):
    """创建缺失的表"""
    print("检查并创建缺失的表...")

    # 创建 metadata_tables 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metadata_tables (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            table_name VARCHAR(128) NOT NULL,
            database_name VARCHAR(128) NOT NULL,
            description TEXT,
            row_count BIGINT DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_table_db (table_name, database_name)
        )
    """)
    print("  ✓ metadata_tables")

    # 创建 metadata_columns 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metadata_columns (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            table_name VARCHAR(128) NOT NULL,
            database_name VARCHAR(128) NOT NULL,
            column_name VARCHAR(128) NOT NULL,
            column_type VARCHAR(64) NOT NULL,
            is_nullable BOOLEAN DEFAULT TRUE,
            description TEXT,
            position INT NOT NULL
        )
    """)
    print("  ✓ metadata_columns")

    # 创建 dataset_columns 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dataset_columns (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            dataset_id VARCHAR(64) NOT NULL,
            column_name VARCHAR(128) NOT NULL,
            column_type VARCHAR(64) NOT NULL,
            is_nullable BOOLEAN DEFAULT TRUE,
            description TEXT,
            position INT NOT NULL
        )
    """)
    print("  ✓ dataset_columns")


def create_test_data():
    """创建完整测试数据"""
    conn = get_connection()
    cursor = conn.cursor()

    # 创建缺失的表
    create_tables(cursor)

    print("\n开始创建测试数据...")

    # ==================== 1. 数据源 (datasources) ====================
    print("\n1. 数据源...")

    datasources = [
        ('ds_mysql_001', '生产MySQL数据库', 'mysql', 'connected'),
        ('ds_pg_001', '数仓PostgreSQL', 'postgresql', 'connected'),
        ('ds_oracle_001', 'ERP Oracle', 'oracle', 'connected'),
        ('ds_mongo_001', '日志MongoDB', 'mongodb', 'connected'),
        ('ds_clickhouse_001', '分析ClickHouse', 'clickhouse', 'error'),
        ('ds_redis_001', '缓存Redis', 'redis', 'connected'),
        ('ds_es_001', '日志Elasticsearch', 'elasticsearch', 'connected'),
        ('ds_hive_001', '大数据Hive', 'hive', 'disconnected'),
    ]

    for source_id, name, type_, status in datasources:
        cursor.execute("SELECT COUNT(*) FROM datasources WHERE source_id = %s", (source_id,))
        if cursor.fetchone()[0] == 0:
            connection_config = json.dumps({'host': f'{type_}.example.com', 'port': 3306, 'database': 'db'})
            tags = json.dumps([type_, 'data'])
            cursor.execute("""
                INSERT INTO datasources (source_id, name, description, type, connection_config, status, tags, created_by, last_connected)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (source_id, name, f'{name}连接', type_, connection_config, status, tags, 'admin', random_date()))
            print(f"  ✓ {name}")

    # ==================== 2. 元数据表和列 ====================
    print("\n2. 元数据表...")

    # 清空并重建
    cursor.execute("DELETE FROM metadata_columns WHERE 1=1")
    cursor.execute("DELETE FROM metadata_tables WHERE 1=1")

    # 重建数据库
    cursor.execute("DELETE FROM metadata_databases WHERE 1=1")
    for db_name, desc, owner in [('prod_db', '生产数据库', 'admin'), ('warehouse', '数仓数据库', 'admin'), ('analytics', '分析数据库', 'bi')]:
        cursor.execute("INSERT INTO metadata_databases (database_name, description, owner) VALUES (%s, %s, %s)", (db_name, desc, owner))

    # 元数据表定义
    tables_def = [
        # prod_db
        ('users', 'prod_db', '用户表', 1000000, [
            ('id', 'BIGINT', '用户ID'),
            ('username', 'VARCHAR(50)', '用户名'),
            ('email', 'VARCHAR(100)', '邮箱'),
            ('phone', 'VARCHAR(20)', '手机号'),
            ('status', 'INT', '状态'),
        ]),
        ('orders', 'prod_db', '订单表', 5000000, [
            ('id', 'BIGINT', '订单ID'),
            ('user_id', 'BIGINT', '用户ID'),
            ('amount', 'DECIMAL(10,2)', '金额'),
            ('status', 'VARCHAR(20)', '状态'),
        ]),
        ('products', 'prod_db', '商品表', 10000, [
            ('id', 'BIGINT', '商品ID'),
            ('name', 'VARCHAR(255)', '商品名'),
            ('price', 'DECIMAL(10,2)', '价格'),
            ('stock', 'INT', '库存'),
        ]),
        # warehouse
        ('dim_users', 'warehouse', '用户维度表', 1000000, [
            ('user_key', 'BIGINT', '代理键'),
            ('user_id', 'BIGINT', '源ID'),
            ('city', 'VARCHAR(50)', '城市'),
        ]),
        ('fact_orders', 'warehouse', '订单事实表', 10000000, [
            ('order_key', 'BIGINT', '代理键'),
            ('user_key', 'BIGINT', '用户键'),
            ('amount', 'DECIMAL(10,2)', '金额'),
        ]),
        # analytics
        ('daily_stats', 'analytics', '日统计表', 365, [
            ('stat_date', 'DATE', '日期'),
            ('orders', 'INT', '订单数'),
            ('revenue', 'DECIMAL(15,2)', '收入'),
        ]),
    ]

    for table_name, db_name, desc, row_count, columns in tables_def:
        cursor.execute("""
            INSERT INTO metadata_tables (table_name, database_name, description, row_count)
            VALUES (%s, %s, %s, %s)
        """, (table_name, db_name, desc, row_count))

        for pos, (col_name, col_type, col_desc) in enumerate(columns, 1):
            cursor.execute("""
                INSERT INTO metadata_columns (table_name, database_name, column_name, column_type, description, position)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (table_name, db_name, col_name, col_type, col_desc, pos))

        print(f"  ✓ {db_name}.{table_name} ({len(columns)}列)")

    # ==================== 3. 数据集 (datasets) ====================
    print("\n3. 数据集...")

    datasets = [
        ('ds_users_raw', '用户原始数据', 's3://data/raw/users/', 'parquet', 50000000, [
            ('user_id', 'BIGINT', '用户ID'),
            ('event_time', 'TIMESTAMP', '事件时间'),
            ('event_type', 'VARCHAR(50)', '事件类型'),
        ]),
        ('ds_orders_daily', '订单日汇总', 's3://data/warehouse/orders/', 'parquet', 3650, [
            ('order_date', 'DATE', '日期'),
            ('order_count', 'INT', '订单数'),
            ('total_amount', 'DECIMAL(15,2)', '总金额'),
        ]),
        ('ds_products', '产品目录', 's3://data/products/', 'parquet', 100000, [
            ('product_id', 'BIGINT', '商品ID'),
            ('name', 'VARCHAR(255)', '名称'),
            ('category', 'VARCHAR(50)', '分类'),
            ('price', 'DECIMAL(10,2)', '价格'),
        ]),
        ('ds_logs_stream', '实时日志流', 'kafka://app-logs', 'json', 0, [
            ('timestamp', 'BIGINT', '时间戳'),
            ('level', 'VARCHAR(20)', '级别'),
            ('message', 'TEXT', '消息'),
        ]),
    ]

    for dataset_id, name, path, format, row_count, columns in datasets:
        cursor.execute("SELECT COUNT(*) FROM datasets WHERE dataset_id = %s", (dataset_id,))
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO datasets (dataset_id, name, description, storage_type, storage_path, format, row_count, status, tags)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (dataset_id, name, f'{name}描述', 's3' if 's3' in path else 'kafka', path, format, row_count, 'active', '[]'))

            for pos, (col_name, col_type, col_desc) in enumerate(columns, 1):
                cursor.execute("""
                    INSERT INTO dataset_columns (dataset_id, column_name, column_type, is_nullable, description, position)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (dataset_id, col_name, col_type, False, col_desc, pos))

            print(f"  ✓ {name} ({len(columns)}列)")

    # ==================== 4. 数据标准 (data_standards) ====================
    print("\n4. 数据标准...")

    standards = [
        ('STD_USER_ID', '用户ID命名规范', 'naming', 'user_id'),
        ('STD_DATE_FMT', '日期格式标准', 'format', 'TIMESTAMP'),
        ('STD_EMAIL', '邮箱格式', 'validation', 'email'),
        ('STD_PRICE', '金额字段', 'datatype', 'DECIMAL'),
    ]

    for standard_id, name, category, rule_type in standards:
        cursor.execute("SELECT COUNT(*) FROM data_standards WHERE standard_id = %s", (standard_id,))
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO data_standards (standard_id, name, description, category, rule_type, status, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (standard_id, name, f'{name}描述', category, rule_type, 'active', 'admin'))
            print(f"  ✓ {name}")

    # ==================== 5. 质量规则 (quality_rules) ====================
    print("\n5. 质量规则...")

    rules = [
        ('R001', '用户ID非空', 'not_null', 'users', 'user_id', 'high'),
        ('R002', '邮箱格式', 'regex', 'users', 'email', 'medium'),
        ('R003', '金额非负', 'range', 'orders', 'amount', 'critical'),
    ]

    for rule_id, name, rule_type, table, column, severity in rules:
        cursor.execute("SELECT COUNT(*) FROM quality_rules WHERE rule_id = %s", (rule_id,))
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO quality_rules (rule_id, name, description, rule_type, target_table, target_column, severity, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (rule_id, name, f'{name}描述', rule_type, table, column, severity, 'admin'))
            print(f"  ✓ {name}")

    # ==================== 6. 扫描任务 (sensitivity_scan_tasks) ====================
    print("\n6. 扫描任务...")

    scans = [
        ('scan_prod_001', 'prod_db', 'completed', 15, 23, 45),
        ('scan_warehouse_001', 'warehouse', 'completed', 8, 12, 30),
        ('scan_logs_001', 'prod_db', 'active', 0, 0, 0),
    ]

    for task_id, db, status, pii, fin, cred in scans:
        cursor.execute("SELECT COUNT(*) FROM sensitivity_scan_tasks WHERE task_id = %s", (task_id,))
        if cursor.fetchone()[0] == 0:
            # 使用列名列表避免 databases 关键字问题
            cursor.execute("""
                INSERT INTO sensitivity_scan_tasks (task_id, target_type, target_name, status, pii_count, financial_count, credential_count, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (task_id, 'database', f'{db}扫描', status, pii, fin, cred, 'admin'))
            print(f"  ✓ {db}扫描")

    # ==================== 7. 数据服务 (data_services) ====================
    print("\n7. 数据服务...")

    services = [
        ('svc_user_profile', '用户画像API', 'GET', '/api/v1/data/users'),
        ('svc_order_stats', '订单统计API', 'GET', '/api/v1/data/orders/stats'),
        ('svc_recommend', '推荐API', 'POST', '/api/v1/ml/recommend'),
    ]

    for service_id, name, method, path in services:
        cursor.execute("SELECT COUNT(*) FROM data_services WHERE service_id = %s", (service_id,))
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO data_services (service_id, name, description, service_type, method, path, status, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (service_id, name, f'{name}描述', 'api', method, path, 'active', 'admin'))
            print(f"  ✓ {name}")

    # ==================== 8. BI 报表 ====================
    print("\n8. BI 报表...")

    dashboards = [
        ('dash_sales', '销售数据看板', '销售分析', [
            ('chart_sales_trend', '销售额趋势', 'line'),
            ('chart_category_share', '品类占比', 'pie'),
        ]),
        ('dash_users', '用户增长分析', '用户分析', [
            ('chart_user_growth', '用户新增趋势', 'line'),
            ('chart_retention', '留存率', 'bar'),
        ]),
        ('dash_ops', '运营监控大屏', '运营分析', [
            ('chart_realtime_orders', '实时订单', 'gauge'),
            ('chart_gmv', 'GMV趋势', 'area'),
        ]),
    ]

    for dash_id, dash_name, dash_category, charts in dashboards:
        cursor.execute("SELECT COUNT(*) FROM bi_dashboards WHERE dashboard_id = %s", (dash_id,))
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO bi_dashboards (dashboard_id, name, description, created_by)
                VALUES (%s, %s, %s, %s)
            """, (dash_id, dash_name, f'{dash_name}描述', 'admin'))

            for chart_id, chart_name, chart_type in charts:
                cursor.execute("""
                    INSERT INTO bi_charts (chart_id, name, dashboard_id, chart_type, config, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (chart_id, chart_name, dash_id, chart_type, '{}', 'admin'))

            print(f"  ✓ {dash_name} ({len(charts)}图表)")

    # ==================== 9. 告警规则 (alert_rules) ====================
    print("\n9. 告警规则...")

    alerts = [
        ('alert_quality', '数据质量告警', 'quality_score', 60.0, 'high'),
        ('alert_etl', 'ETL任务失败', 'etl_task_status', 1.0, 'critical'),
        ('alert_delay', '数据延迟', 'data_delay_minutes', 30.0, 'medium'),
    ]

    for rule_id, name, metric_name, threshold, severity in alerts:
        cursor.execute("SELECT COUNT(*) FROM alert_rules WHERE rule_id = %s", (rule_id,))
        if cursor.fetchone()[0] == 0:
            channels = json.dumps(['email', 'webhook'])
            cursor.execute("""
                INSERT INTO alert_rules (rule_id, name, description, metric_name, `condition`, threshold, severity, notification_channels, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (rule_id, name, f'{name}描述', metric_name, '<', threshold, severity, channels, 'admin'))
            print(f"  ✓ {name}")

    # ==================== 10. API 密钥 (api_keys) ====================
    print("\n10. API 密钥...")

    keys = [
        ('key_data_platform', '数据分析平台', 'read'),
        ('key_etl_task', 'ETL任务', 'write'),
        ('key_third_party', '第三方工具', 'read'),
    ]

    for key_id, name, key_type in keys:
        cursor.execute("SELECT COUNT(*) FROM api_keys WHERE key_id = %s", (key_id,))
        if cursor.fetchone()[0] == 0:
            key_hash = hash(key_id + str(random_id())) % 10000000000
            cursor.execute("""
                INSERT INTO api_keys (key_id, key_hash, name, description, rate_limit, status, user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (key_id, key_hash, name, f'{name}API', 10000, 'active', 'admin'))
            print(f"  ✓ {name}")

    # 提交
    conn.commit()
    print("\n✅ 测试数据创建完成！")

    # 统计
    print("\n数据统计:")
    tables = [
        ('datasources', '数据源'),
        ('metadata_databases', '元数据库'),
        ('metadata_tables', '元数据表'),
        ('metadata_columns', '元数据列'),
        ('datasets', '数据集'),
        ('dataset_columns', '数据集列'),
        ('data_standards', '数据标准'),
        ('quality_rules', '质量规则'),
        ('sensitivity_scan_tasks', '扫描任务'),
        ('data_services', '数据服务'),
        ('bi_dashboards', 'BI报表'),
        ('bi_charts', 'BI图表'),
        ('alert_rules', '告警规则'),
        ('api_keys', 'API密钥'),
    ]

    for table_name, display_name in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  {display_name}: {count}")

    cursor.close()
    conn.close()


if __name__ == '__main__':
    create_test_data()
