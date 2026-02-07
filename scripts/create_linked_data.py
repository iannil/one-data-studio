#!/usr/bin/env python3
"""
创建真实关联的测试数据 - 各页面数据相互关联
"""

import os
import sys
import json
import random
import string
from datetime import datetime, timedelta
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import pymysql
except ImportError:
    os.system("pip install pymysql -q")
    import pymysql


def get_connection():
    return pymysql.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', '3306')),
        user=os.getenv('MYSQL_USER', 'onedata'),
        password=os.getenv('MYSQL_PASSWORD', 'dev123'),
        database=os.getenv('MYSQL_DATABASE', 'onedata'),
        charset='utf8mb4'
    )


def random_id(prefix=None):
    if prefix:
        return f"{prefix}_{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}"
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))


def create_linked_data():
    """创建相互关联的测试数据"""
    conn = get_connection()
    cursor = conn.cursor()

    print("开始创建关联测试数据...")

    # ==================== 清理旧数据 ====================
    print("\n清理旧数据...")
    tables_to_clear = [
        'datasources',
        'metadata_columns', 'metadata_tables', 'metadata_databases',
        'dataset_columns', 'datasets',
        'data_lineage', 'data_lineage_events',
        'etl_tasks', 'etl_task_logs'
    ]
    for table in tables_to_clear:
        try:
            cursor.execute(f"DELETE FROM {table} WHERE 1=1")
        except:
            pass
    print("  ✓ 清理完成")

    # ==================== 1. 创建关联的数据源和元数据库 ====================
    print("\n1. 创建数据源和元数据库（关联）...")

    # 数据源定义 - 包含 database_name 用于关联
    datasources = [
        {
            'source_id': 'ds_mysql_prod',
            'name': '生产数据库MySQL',
            'type': 'mysql',
            'database_name': 'prod_db',
            'host': 'prod-mysql.internal',
            'port': 3306,
            'connection_config': {'host': 'prod-mysql.internal', 'port': 3306, 'database': 'prod_db'}
        },
        {
            'source_id': 'ds_pg_dw',
            'name': '数据仓库PostgreSQL',
            'type': 'postgresql',
            'database_name': 'warehouse',
            'host': 'dw-pg.internal',
            'port': 5432,
            'connection_config': {'host': 'dw-pg.internal', 'port': 5432, 'database': 'warehouse'}
        },
        {
            'source_id': 'ds_oracle_erp',
            'name': 'ERP Oracle',
            'type': 'oracle',
            'database_name': 'erp_db',
            'host': 'erp-oracle.internal',
            'port': 1521,
            'connection_config': {'host': 'erp-oracle.internal', 'port': 1521, 'service_name': 'ERPPROD'}
        },
        {
            'source_id': 'ds_mongo_logs',
            'name': '日志MongoDB',
            'type': 'mongodb',
            'database_name': 'log_db',
            'host': 'log-mongo.internal',
            'port': 27017,
            'connection_config': {'host': 'log-mongo.internal', 'port': 27017, 'database': 'log_db'}
        },
    ]

    # 1. 先创建元数据库（作为数据源的映射）
    databases = {
        'prod_db': {'name': '生产数据库', 'description': '核心业务数据库', 'owner': 'data-admin'},
        'warehouse': {'name': '数据仓库', 'description': '企业级数据仓库', 'owner': 'data-admin'},
        'erp_db': {'name': 'ERP数据库', 'description': 'ERP系统数据库', 'owner': 'erp-admin'},
        'log_db': {'name': '日志数据库', 'description': '应用日志数据库', 'owner': 'ops-admin'},
    }

    for db_id, db_info in databases.items():
        cursor.execute("""
            INSERT INTO metadata_databases (database_name, description, owner)
            VALUES (%s, %s, %s)
        """, (db_id, db_info['description'], db_info['owner']))

    # 2. 创建数据源（包含 database_name 字段用于关联）
    for ds in datasources:
        connection_config = json.dumps({
            'host': ds['host'],
            'port': ds['port'],
            'database': ds.get('database_name', ''),
            'service_name': ds.get('service_name', ''),
        })
        tags = json.dumps([ds['type'], 'production' if 'prod' in ds['source_id'] else 'warehouse'])

        cursor.execute("""
            INSERT INTO datasources (source_id, name, description, type, connection_config, status, tags, created_by, last_connected)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (ds['source_id'], ds['name'], f'{ds["name"]}连接', ds['type'], connection_config,
              'connected', tags, 'admin', datetime.now()))
        print(f"  ✓ {ds['name']} -> {ds['database_name']}")

    # ==================== 2. 创建元数据表（关联到数据源） ====================
    print("\n2. 创建元数据表（关联到数据源）...")

    tables_def = [
        # prod_db 表
        ('users', 'prod_db', 'ds_mysql_prod', '用户表', 1000000, [
            ('id', 'BIGINT', '用户ID', 'restricted', 'pii', '主键'),
            ('username', 'VARCHAR(50)', '用户名', 'public', 'none', ''),
            ('email', 'VARCHAR(100)', '邮箱', 'confidential', 'pii', ''),
            ('phone', 'VARCHAR(20)', '手机', 'confidential', 'pii', ''),
            ('status', 'TINYINT', '状态', 'public', 'none', ''),
            ('created_at', 'TIMESTAMP', '创建时间', 'public', 'none', ''),
        ]),
        ('orders', 'prod_db', 'ds_mysql_prod', '订单表', 5000000, [
            ('id', 'BIGINT', '订单ID', 'public', 'none', '主键'),
            ('user_id', 'BIGINT', '用户ID', 'confidential', 'pii', '外键 -> users.id'),
            ('product_id', 'BIGINT', '商品ID', 'public', 'none', '外键 -> products.id'),
            ('amount', 'DECIMAL(10,2)', '订单金额', 'confidential', 'financial', ''),
            ('status', 'VARCHAR(20)', '状态', 'public', 'none', ''),
            ('order_date', 'DATE', '订单日期', 'public', 'none', ''),
        ]),
        ('products', 'prod_db', 'ds_mysql_prod', '商品表', 10000, [
            ('id', 'BIGINT', '商品ID', 'public', 'none', '主键'),
            ('name', 'VARCHAR(255)', '商品名称', 'public', 'none', ''),
            ('category_id', 'INT', '分类ID', 'public', 'none', '外键 -> categories.id'),
            ('price', 'DECIMAL(10,2)', '价格', 'confidential', 'financial', ''),
            ('stock', 'INT', '库存', 'internal', 'none', ''),
        ]),

        # warehouse 表
        ('dim_users', 'warehouse', 'ds_mysql_prod', '用户维度表', 1000000, [
            ('user_key', 'BIGINT', '代理键', 'public', 'none', '主键'),
            ('user_id', 'BIGINT', '源系统用户ID', 'confidential', 'pii', '来源 -> prod_db.users'),
            ('city', 'VARCHAR(50)', '城市', 'internal', 'none', ''),
            ('province', 'VARCHAR(50)', '省份', 'internal', 'none', ''),
            ('country', 'VARCHAR(50)', '国家', 'public', 'none', ''),
            ('effective_date', 'DATE', '生效日期', 'public', 'none', ''),
        ]),
        ('fact_orders', 'warehouse', 'ds_mysql_prod', '订单事实表', 10000000, [
            ('order_key', 'BIGINT', '代理键', 'public', 'none', '主键'),
            ('user_key', 'BIGINT', '用户代理键', 'confidential', 'pii', '外键 -> dim_users.user_key'),
            ('product_key', 'BIGINT', '商品代理键', 'internal', 'none', ''),
            ('order_date_key', 'INT', '日期代理键', 'public', 'none', ''),
            ('order_amount', 'DECIMAL(10,2)', '订单金额', 'confidential', 'financial', ''),
            ('order_count', 'INT', '订单数量', 'internal', 'none', ''),
        ]),
        ('fact_daily_summary', 'warehouse', 'ds_mysql_prod', '日汇总表', 3650, [
            ('date_key', 'INT', '日期键', 'public', 'none', '主键'),
            ('order_count', 'INT', '订单数量', 'internal', 'none', ''),
            ('total_amount', 'DECIMAL(15,2)', '总金额', 'confidential', 'financial', ''),
            ('new_user_count', 'INT', '新用户数', 'internal', 'none', ''),
            ('active_user_count', 'INT', '活跃用户数', 'internal', 'none', ''),
        ]),

        # erp_db 表
        ('gl_balances', 'erp_db', 'ds_oracle_erp', '总账余额表', 500000, [
            ('code_combination', 'VARCHAR(50)', '科目组合', 'public', 'none', '主键'),
            ('period_name', 'VARCHAR(20)', '会计期间', 'public', 'none', ''),
            ('currency', 'VARCHAR(10)', '币种', 'public', 'none', ''),
            ('period_net_dr', 'DECIMAL(15,2)', '借方金额', 'confidential', 'financial', ''),
            ('period_net_cr', 'DECIMAL(15,2)', '贷方金额', 'confidential', 'financial', ''),
        ]),
    ]

    for table_name, db_name, source_id, desc, row_count, columns in tables_def:
        cursor.execute("""
            INSERT INTO metadata_tables (table_name, database_name, description, row_count)
            VALUES (%s, %s, %s, %s)
        """, (table_name, db_name, desc, row_count))

        for pos, (col_name, col_type, col_desc, sensitivity, sensitivity_type, ref) in enumerate(columns, 1):
            # 解析引用信息
            ref_table = None
            if ref and '->' in ref:
                ref_table = ref.split('->')[-1].strip()

            semantic_tags = []
            if '主键' in col_desc:
                semantic_tags.append('primary_key')
            if '外键' in col_desc:
                semantic_tags.append('foreign_key')

            cursor.execute("""
                INSERT INTO metadata_columns (table_name, database_name, column_name, column_type,
                    is_nullable, description, position, sensitivity_level, sensitivity_type, semantic_tags)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (table_name, db_name, col_name, col_type,
                  False if 'NOT NULL' in col_desc or col_name == 'id' else True,
                  col_desc, pos, sensitivity, sensitivity_type,
                  json.dumps(semantic_tags) if semantic_tags else None))

        print(f"  ✓ {db_name}.{table_name} <- {source_id}")

    # ==================== 3. 创建数据集（关联到源表） ====================
    print("\n3. 创建数据集（关联到源表）...")

    datasets = [
        {
            'dataset_id': 'ds_users_raw',
            'name': '用户行为原始数据',
            'source_table': 'users',
            'source_database': 'prod_db',
            'source_id': 'ds_mysql_prod',
            'storage_path': 's3://data-lake/raw/prod_db/users/',
            'format': 'parquet',
            'row_count': 50000000,
            'columns': [
                ('user_id', 'BIGINT', '用户ID', '源: prod_db.users'),
                ('event_time', 'TIMESTAMP', '事件时间', ''),
                ('event_type', 'VARCHAR(50)', '事件类型', ''),
                ('page_url', 'VARCHAR(500)', '页面URL', ''),
            ],
            'lineage_source': 'prod_db.users'
        },
        {
            'dataset_id': 'ds_orders_fact',
            'name': '订单事实数据',
            'source_table': 'fact_orders',
            'source_database': 'warehouse',
            'source_id': 'ds_mysql_prod',  # 通过ETL同步
            'storage_path': 's3://data-lake/warehouse/fact_orders/',
            'format': 'parquet',
            'row_count': 10000000,
            'columns': [
                ('order_key', 'BIGINT', '代理键', ''),
                ('user_key', 'BIGINT', '用户键', '关联: dim_users'),
                ('order_date_key', 'INT', '日期键', ''),
                ('order_amount', 'DECIMAL(10,2)', '订单金额', ''),
                ('order_count', 'INT', '订单数量', ''),
            ],
            'lineage_source': 'warehouse.fact_orders -> prod_db.orders'
        },
        {
            'dataset_id': 'ds_products',
            'name': '商品全量数据',
            'source_table': 'products',
            'source_database': 'prod_db',
            'source_id': 'ds_mysql_prod',
            'storage_path': 's3://data-lake/prod_db/products/',
            'format': 'parquet',
            'row_count': 10000,
            'columns': [
                ('product_id', 'BIGINT', '商品ID', ''),
                ('name', 'VARCHAR(255)', '商品名称', ''),
                ('category_id', 'INT', '分类ID', ''),
                ('price', 'DECIMAL(10,2)', '价格', ''),
                ('stock', 'INT', '库存', ''),
                ('updated_at', 'TIMESTAMP', '更新时间', ''),
            ],
            'lineage_source': 'prod_db.products'
        },
        {
            'dataset_id': 'ds_gl_balances',
            'name': '总账余额快照',
            'source_table': 'gl_balances',
            'source_database': 'erp_db',
            'source_id': 'ds_oracle_erp',
            'storage_path': 's3://data-lake/erp_db/gl_balances/',
            'format': 'parquet',
            'row_count': 500000,
            'columns': [
                ('code_combination', 'VARCHAR(50)', '科目组合', ''),
                ('period_name', 'VARCHAR(20)', '会计期间', ''),
                ('currency', 'VARCHAR(10)', '币种', ''),
                ('period_net_dr', 'DECIMAL(15,2)', '借方', ''),
                ('period_net_cr', 'DECIMAL(15,2)', '贷方', ''),
            ],
            'lineage_source': 'erp_db.gl_balances'
        },
    ]

    for ds in datasets:
        # 插入数据集
        cursor.execute("""
            INSERT INTO datasets (dataset_id, name, description, storage_type, storage_path, format, row_count, status, tags)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (ds['dataset_id'], ds['name'],
              f'源表: {ds["source_database"]}.{ds["source_table"]}',
              's3' if 's3' in ds['storage_path'] else 'parquet',
              ds['storage_path'], ds['format'], ds['row_count'], 'active', '[]'))

        # 插入列
        for pos, (col_name, col_type, col_desc, ref) in enumerate(ds['columns'], 1):
            cursor.execute("""
                INSERT INTO dataset_columns (dataset_id, column_name, column_type, is_nullable, description, position)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (ds['dataset_id'], col_name, col_type, True, col_desc, pos))

        # 插入数据血缘关系（如果表存在）
        try:
            cursor.execute("""
                INSERT INTO data_lineage (source_table, source_database, target_dataset_id, target_table, transformation_type, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (f"{ds['source_database']}.{ds['source_table']}", ds['source_database'],
                  ds['dataset_id'], f"{ds['source_database']}.{ds['source_table']}_sync",
                  'sync', datetime.now()))
        except:
            pass  # 表可能不存在

        print(f"  ✓ {ds['name']} <- {ds['source_database']}.{ds['source_table']}")

    # ==================== 4. 创建 ETL 任务（关联到数据源和数据集）================
    print("\n4. 创建 ETL 任务（关联到数据源和数据集）...")

    etl_tasks = [
        {
            'task_id': 'etl_sync_users',
            'name': '用户数据同步',
            'task_type': 'sync',
            'engine_type': 'kettle',
            'source_id': 'ds_mysql_prod',
            'source_type': 'mysql',
            'source_table': 'users',
            'source_database': 'prod_db',
            'target_id': 'ds_mysql_prod',
            'target_type': 'mysql',
            'target_table': 'dim_users',
            'target_database': 'warehouse',
            'target_dataset_id': 'ds_users_raw',
            'schedule_type': 'cron',
            'schedule': '0 */2 * * *',
        },
        {
            'task_id': 'etl_orders_fact',
            'name': '订单数据入仓',
            'task_type': 'extract',
            'engine_type': 'kettle',
            'source_id': 'ds_mysql_prod',
            'source_type': 'mysql',
            'source_table': 'orders',
            'source_database': 'prod_db',
            'target_id': 'ds_pg_dw',
            'target_type': 'postgresql',
            'target_table': 'fact_orders',
            'target_database': 'warehouse',
            'target_dataset_id': 'ds_orders_fact',
            'schedule_type': 'cron',
            'schedule': '0 1 * * *',
        },
        {
            'task_id': 'etl_products_snapshot',
            'name': '商品快照同步',
            'task_type': 'sync',
            'engine_type': 'kettle',
            'source_id': 'ds_mysql_prod',
            'source_type': 'mysql',
            'source_table': 'products',
            'source_database': 'prod_db',
            'target_id': 'ds_minio_lake',
            'target_type': 'minio',
            'target_table': 'products',
            'target_database': 'data_lake',
            'target_dataset_id': 'ds_products',
            'schedule_type': 'cron',
            'schedule': '0 3 * * *',
        },
        {
            'task_id': 'etl_gl_balances',
            'name': 'ERP总账同步',
            'task_type': 'extract',
            'engine_type': 'kettle',
            'source_id': 'ds_oracle_erp',
            'source_type': 'oracle',
            'source_table': 'gl_balances',
            'source_database': 'erp_db',
            'target_id': 'ds_minio_lake',
            'target_type': 'minio',
            'target_table': 'gl_balances',
            'target_database': 'data_lake',
            'target_dataset_id': 'ds_gl_balances',
            'schedule_type': 'cron',
            'schedule': '0 4 * * *',
        },
    ]

    for task in etl_tasks:
        # 构建 source_config 和 target_config
        source_config = {
            'datasource_id': task['source_id'],
            'table': task['source_table'],
            'database': task['source_database'],
            'query': f"SELECT * FROM {task['source_database']}.{task['source_table']}"
        }
        target_config = {
            'datasource_id': task.get('target_id', ''),
            'table': task['target_table'],
            'database': task.get('target_database', ''),
            'dataset_id': task.get('target_dataset_id', ''),
        }
        schedule_config = {'cron': task['schedule']}

        # 将源表信息存放在 source_config 和 source_query 中
        source_query = f"SELECT * FROM {task['source_database']}.{task['source_table']}"

        cursor.execute("""
            INSERT INTO etl_tasks (task_id, name, description, task_type, engine_type,
                source_type, source_config, source_query, target_type, target_config, target_table,
                schedule_type, schedule_config, created_by, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (task['task_id'], task['name'], f'{task["name"]}说明', task['task_type'], task['engine_type'],
              task['source_type'], json.dumps(source_config), source_query,
              task['target_type'], json.dumps(target_config), task['target_table'],
              task['schedule_type'], json.dumps(schedule_config), 'admin', 'active'))

        print(f"  ✓ {task['name']}: {task['source_database']}.{task['source_table']} -> {task.get('target_database', 'data_lake')}.{task['target_table']}")

    # ==================== 5. 创建数据血缘事件（记录表之间的血缘关系）================
    print("\n5. 创建数据血缘关系...")

    # 创建 data_lineage_events 表（如果不存在）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS data_lineage_events (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            event_type VARCHAR(32) NOT NULL,
            source_table VARCHAR(255) NOT NULL,
            source_database VARCHAR(128) NOT NULL,
            source_type VARCHAR(32) NOT NULL,
            source_id VARCHAR(64),
            target_table VARCHAR(255),
            target_database VARCHAR(128),
            target_type VARCHAR(32),
            target_id VARCHAR(64),
            transformation_description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    lineage_events = [
        ('SYNC', 'users', 'prod_db', 'mysql', 'ds_mysql_prod', 'dim_users', 'warehouse', 'postgresql', None, '用户同步：仅同步必要字段'),
        ('SYNC', 'orders', 'prod_db', 'mysql', 'ds_mysql_prod', 'fact_orders', 'warehouse', 'postgresql', None, '订单入仓：维度建模'),
        ('EXTRACT', 'products', 'prod_db', 'mysql', 'ds_mysql_prod', 'products', 'data_lake', 'minio', 'ds_products', '商品快照：全量导出'),
        ('EXTRACT', 'gl_balances', 'erp_db', 'oracle', 'ds_oracle_erp', 'gl_balances', 'data_lake', 'minio', 'ds_gl_balances', 'ERP总账：每日抽取'),
        ('AGGREGATE', 'fact_orders', 'warehouse', 'postgresql', None, 'fact_daily_summary', 'warehouse', 'postgresql', None, '订单汇总：按日聚合'),
    ]

    for event_type, src_table, src_db, src_type, src_id, tgt_table, tgt_db, tgt_type, tgt_id, desc in lineage_events:
        cursor.execute("""
            INSERT INTO data_lineage_events (event_type, source_table, source_database, source_type, source_id,
                target_table, target_database, target_type, target_id, transformation_description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (event_type, src_table, src_db, src_type, src_id, tgt_table, tgt_db, tgt_type, tgt_id, desc))

        print(f"  ✓ {event_type}: {src_db}.{src_table} -> {tgt_db}.{tgt_table}")

    # 提交
    conn.commit()
    print("\n✅ 关联数据创建完成！")

    # ==================== 验证关联 ====================
    print("\n=== 数据关联验证 ===")

    print("\n1. 数据源 -> 元数据表:")
    cursor.execute("""
        SELECT ds.source_id, ds.name, ds.type,
               JSON_UNQUOTE(JSON_EXTRACT(ds.connection_config, '$.database')) as db_name,
               COUNT(mt.table_name) as table_count
        FROM datasources ds
        LEFT JOIN metadata_tables mt ON mt.database_name = JSON_UNQUOTE(JSON_EXTRACT(ds.connection_config, '$.database'))
        GROUP BY ds.source_id, ds.name, ds.type, db_name
    """)
    for row in cursor.fetchall():
        print(f"  {row[1]} ({row[2]}) -> {row[3]} ({row[4]} 表)")

    print("\n2. 元数据表 -> 数据集:")
    cursor.execute("""
        SELECT mt.table_name, mt.database_name, d.dataset_id, d.name
        FROM metadata_tables mt
        JOIN datasets d ON d.description LIKE CONCAT('%', mt.table_name, '%')
        ORDER BY mt.database_name, mt.table_name
    """)
    for row in cursor.fetchall():
        print(f"  {row[1]}.{row[0]} -> {row[3]}")

    print("\n3. ETL 任务链:")
    cursor.execute("""
        SELECT t.name,
               JSON_UNQUOTE(JSON_EXTRACT(t.source_config, '$.database')) as source_db,
               JSON_UNQUOTE(JSON_EXTRACT(t.source_config, '$.table')) as source_table,
               JSON_UNQUOTE(JSON_EXTRACT(t.target_config, '$.database')) as target_db,
               t.target_table,
               JSON_UNQUOTE(JSON_EXTRACT(t.target_config, '$.dataset_id')) as target_dataset
        FROM etl_tasks t
        ORDER BY source_db, source_table
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}.{row[2]} -> {row[3]}.{row[4]} (数据集: {row[5]})")

    print("\n4. 数据血缘事件:")
    cursor.execute("""
        SELECT event_type, source_table, source_database, target_table, target_database
        FROM data_lineage_events
        ORDER BY source_database, source_table
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}.{row[2]} -> {row[3]}.{row[4]}")

    cursor.close()
    conn.close()


if __name__ == '__main__':
    create_linked_data()
