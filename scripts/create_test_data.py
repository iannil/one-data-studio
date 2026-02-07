#!/usr/bin/env python3
"""
创建测试数据脚本 - 为 DataOps 平台生成演示数据
Usage:
    python scripts/create_test_data.py
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


def create_test_data():
    """创建测试数据"""
    conn = get_connection()
    cursor = conn.cursor()

    print("开始创建测试数据...")

    # ==================== ETL 任务数据 ====================
    print("\n1. 创建 ETL 任务...")

    etl_tasks = [
        {
            'name': '用户数据同步',
            'task_type': 'sync',
            'engine_type': 'kettle',
            'status': 'active',
            'source_type': 'mysql',
            'source_config': {'host': 'prod-db', 'port': 3306, 'database': 'users', 'table': 'users'},
            'target_type': 'mysql',
            'target_config': {'host': 'warehouse', 'port': 3306, 'database': 'dw', 'table': 'dim_users'},
            'target_table': 'dim_users',
            'schedule_type': 'cron',
            'schedule_config': {'expression': '0 */2 * * *', 'timezone': 'Asia/Shanghai'},
            'description': '从生产数据库同步用户数据到数仓'
        },
        {
            'name': '订单数据抽取',
            'task_type': 'extract',
            'engine_type': 'kettle',
            'status': 'active',
            'source_type': 'postgresql',
            'source_config': {'host': 'prod-db', 'port': 5432, 'database': 'orders', 'table': 'orders'},
            'target_type': 'minio',
            'target_config': {'bucket': 'data-lake', 'prefix': 'orders', 'format': 'parquet'},
            'schedule_type': 'cron',
            'schedule_config': {'expression': '0 1 * * *', 'timezone': 'Asia/Shanghai'},
            'description': '每日抽取订单数据到数据湖'
        },
        {
            'name': '产品目录更新',
            'task_type': 'sync',
            'engine_type': 'kettle',
            'status': 'paused',
            'source_type': 'api',
            'source_config': {'url': 'https://api.example.com/products', 'method': 'GET'},
            'target_type': 'mysql',
            'target_config': {'host': 'warehouse', 'port': 3306, 'database': 'dw', 'table': 'dim_products'},
            'target_table': 'dim_products',
            'schedule_type': 'cron',
            'schedule_config': {'expression': '0 3 * * *', 'timezone': 'Asia/Shanghai'},
            'description': '从产品API同步产品目录'
        },
        {
            'name': '日志数据归档',
            'task_type': 'archive',
            'engine_type': 'seatunnel',
            'status': 'active',
            'source_type': 'kafka',
            'source_config': {'bootstrap_servers': 'kafka:9092', 'topic': 'app-logs'},
            'target_type': 'minio',
            'target_config': {'bucket': 'archive', 'prefix': 'logs', 'format': 'json'},
            'schedule_type': 'realtime',
            'schedule_config': {},
            'description': '实时归档应用日志到对象存储'
        },
        {
            'name': '指标计算任务',
            'task_type': 'transform',
            'engine_type': 'sql',
            'status': 'active',
            'source_type': 'mysql',
            'source_config': {'host': 'warehouse', 'port': 3306, 'database': 'dw'},
            'target_type': 'mysql',
            'target_config': {'host': 'bi_db', 'port': 3306, 'database': 'bi', 'table': 'metrics'},
            'target_table': 'daily_metrics',
            'schedule_type': 'cron',
            'schedule_config': {'expression': '0 */4 * * *', 'timezone': 'Asia/Shanghai'},
            'description': '计算并更新业务指标'
        },
    ]

    for task in etl_tasks:
        task_id = random_id('etl')
        created = random_date()
        run_count = random.randint(10, 1000)
        success_count = random.randint(8, run_count)
        fail_count = run_count - success_count

        cursor.execute("""
            INSERT INTO etl_tasks (task_id, name, description, task_type, engine_type, status,
                source_type, source_config, target_type, target_config, target_table,
                schedule_type, schedule_config, created_by, created_at, updated_at,
                run_count, success_count, fail_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            task_id, task['name'], task['description'], task['task_type'], task['engine_type'], task['status'],
            task['source_type'], json.dumps(task['source_config']), task['target_type'], json.dumps(task['target_config']),
            task.get('target_table'), task['schedule_type'], json.dumps(task['schedule_config']),
            'admin', created, datetime.now(), run_count, success_count, fail_count
        ))
        print(f"  ✓ 创建 ETL 任务: {task['name']}")

    # ==================== ETL 任务日志 ====================
    print("\n2. 创建 ETL 任务日志...")
    cursor.execute("SELECT task_id FROM etl_tasks")
    task_ids = [row[0] for row in cursor.fetchall()]

    for task_id in task_ids:
        for i in range(5):
            status = random.choice(['success', 'running', 'failed', 'success', 'success'])
            duration = random.randint(30, 300) if status != 'failed' else None
            rows_written = random.randint(100, 50000) if status == 'success' else None
            error = 'Connection timeout' if status == 'failed' else None

            started = random_date()
            finished = started + timedelta(seconds=duration) if duration else None

            cursor.execute("""
                INSERT INTO etl_task_logs (log_id, task_id, status, started_at, finished_at,
                    duration_seconds, rows_written, error_message, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (random_id('log'), task_id, status, started, finished, duration, rows_written, error, datetime.now()))

    print(f"  ✓ 创建 {len(task_ids) * 5} 条任务日志")

    # ==================== 工作流数据 ====================
    print("\n3. 创建工作流...")

    workflows = [
        {'name': 'RAG 知识库问答', 'type': 'rag', 'status': 'active', 'description': '用户文档问答工作流'},
        {'name': 'SQL 查询助手', 'type': 'text2sql', 'status': 'active', 'description': '自然语言转SQL'},
        {'name': '数据分析助手', 'type': 'analysis', 'status': 'paused', 'description': '自动化数据分析'},
        {'name': '客户服务机器人', 'type': 'chatbot', 'status': 'active', 'description': '智能客服系统'},
    ]

    for wf in workflows:
        wf_id = random_id('wf')
        definition = {
            'version': '1.0',
            'nodes': [
                {'id': 'input-1', 'type': 'input', 'position': {'x': 100, 'y': 100}},
                {'id': 'llm-1', 'type': 'llm', 'position': {'x': 300, 'y': 100}},
                {'id': 'output-1', 'type': 'output', 'position': {'x': 500, 'y': 100}}
            ],
            'edges': [
                {'source': 'input-1', 'target': 'llm-1'},
                {'source': 'llm-1', 'target': 'output-1'}
            ]
        }

        cursor.execute("""
            INSERT INTO workflows (workflow_id, name, type, status, description, definition, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (wf_id, wf['name'], wf['type'], wf['status'], wf['description'], json.dumps(definition), 'admin'))
        print(f"  ✓ 创建工作流: {wf['name']}")

    # ==================== 工作流执行记录 ====================
    print("\n4. 创建工作流执行记录...")
    cursor.execute("SELECT workflow_id FROM workflows")
    wf_ids = [row[0] for row in cursor.fetchall()]

    for wf_id in wf_ids:
        for i in range(10):
            status = random.choice(['completed', 'running', 'failed', 'completed', 'completed'])
            started = random_date()
            duration = random.randint(5, 60) if status != 'running' else None
            completed = started + timedelta(seconds=duration) if duration else None

            cursor.execute("""
                INSERT INTO workflow_executions (execution_id, workflow_id, status, started_at, completed_at,
                    duration_ms, inputs, outputs, error)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (random_id('exec'), wf_id, status, started, completed, duration * 1000 if duration else None,
                  '{}', json.dumps({'result': 'success'}) if status == 'completed' else None,
                  'Task timeout' if status == 'failed' else None))

    print(f"  ✓ 创建 {len(wf_ids) * 10} 条执行记录")

    # ==================== 对话数据 ====================
    print("\n5. 创建对话...")
    conversations = [
        {'title': '数据分析咨询', 'first_message': '如何分析用户增长趋势？'},
        {'title': 'SQL查询帮助', 'first_message': '查询销售额前10的产品'},
        {'title': '文档检索', 'first_message': '查找关于数据治理的文档'},
        {'title': '报表生成', 'first_message': '生成本月销售报表'},
        {'title': '技术支持', 'first_message': '如何配置数据源连接？'},
    ]

    # 先检查是否有 conversation_messages 表
    cursor.execute("SHOW TABLES LIKE 'conversation_messages'")
    has_messages_table = cursor.fetchone() is not None

    for conv in conversations:
        conv_id = random_id('conv')
        created = random_date()

        cursor.execute("""
            INSERT INTO conversations (conversation_id, user_id, title, model, message_count, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (conv_id, 'user', conv['title'], 'gpt-4o-mini', 2, created, datetime.now()))

        if has_messages_table:
            # 添加用户消息
            cursor.execute("""
                INSERT INTO conversation_messages (conversation_id, role, content, created_at)
                VALUES (%s, %s, %s, %s)
            """, (conv_id, 'user', conv['first_message'], datetime.now()))

            # 添加助手回复
            cursor.execute("""
                INSERT INTO conversation_messages (conversation_id, role, content, created_at)
                VALUES (%s, %s, %s, %s)
            """, (conv_id, 'assistant', f'这是关于"{conv["title"]}"的回复内容...', datetime.now()))

        print(f"  ✓ 创建对话: {conv['title']}")

    # ==================== 知识库数据 ====================
    print("\n6. 创建知识库...")

    knowledge_bases = [
        {'name': '产品文档库', 'code': 'product_docs', 'description': '产品使用手册和技术文档'},
        {'name': '技术知识库', 'code': 'tech_docs', 'description': '开发规范和架构设计文档'},
        {'name': '客户FAQ', 'code': 'customer_faq', 'description': '常见问题解答'},
        {'name': '数据字典', 'code': 'data_dictionary', 'description': '数据库表结构和字段说明'},
    ]

    for kb in knowledge_bases:
        kb_id = random_id('kb')
        collection_name = kb['code']

        cursor.execute("""
            INSERT INTO knowledge_bases (kb_id, name, description, collection_name, embedding_model,
                chunk_size, chunk_overlap, created_by, status, document_count, vector_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (kb_id, kb['name'], kb['description'], collection_name, 'text-embedding-ada-002',
              500, 50, 'admin', 'active', 5, 20))

        # 添加索引文档
        for i in range(5):
            doc_id = random_id('doc')
            title = f'{kb["name"]} - 文档{i+1}'
            content = f'这是{kb["name"]}中的第{i+1}个文档内容。包含了详细的说明和示例...'

            cursor.execute("""
                INSERT INTO indexed_documents (doc_id, collection_name, title, content, chunk_count, created_by)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (doc_id, collection_name, title, content, 4, 'admin'))

        print(f"  ✓ 创建知识库: {kb['name']} (含5个文档)")

    # ==================== 数据资产 ====================
    print("\n7. 创建数据资产...")

    data_assets = [
        {
            'name': '用户表',
            'code': 'users',
            'asset_type': 'table',
            'source_type': 'mysql',
            'database_name': 'prod_db',
            'table_name': 'users',
            'description': '用户基础信息表',
            'row_count': 1000000,
            'tags': ['PII', '核心数据']
        },
        {
            'name': '订单表',
            'code': 'orders',
            'asset_type': 'table',
            'source_type': 'mysql',
            'database_name': 'prod_db',
            'table_name': 'orders',
            'description': '订单交易数据',
            'row_count': 5000000,
            'tags': ['CONFIDENTIAL', '交易数据']
        },
        {
            'name': '产品表',
            'code': 'products',
            'asset_type': 'table',
            'source_type': 'mysql',
            'database_name': 'prod_db',
            'table_name': 'products',
            'description': '商品目录信息',
            'row_count': 10000,
            'tags': ['PUBLIC']
        },
        {
            'name': '日志数据',
            'code': 'logs',
            'asset_type': 'collection',
            'source_type': 'mongodb',
            'database_name': 'log_db',
            'table_name': 'app_logs',
            'description': '系统访问日志',
            'row_count': 50000000,
            'tags': ['INTERNAL', '日志']
        },
        {
            'name': '用户行为',
            'code': 'user_events',
            'asset_type': 'table',
            'source_type': 'postgresql',
            'database_name': 'analytics',
            'table_name': 'user_events',
            'description': '用户行为事件',
            'row_count': 100000000,
            'tags': ['INTERNAL', '行为分析']
        },
    ]

    for asset in data_assets:
        asset_id = random_id('asset')
        created = random_date()

        cursor.execute("""
            INSERT INTO data_assets (asset_id, name, description, asset_type, source_type,
                source_name, database_name, schema_name, table_name, row_count, tags,
                owner, status, created_at, updated_at, last_sync_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (asset_id, asset['name'], asset['description'], asset['asset_type'], asset['source_type'],
              asset['code'], asset['database_name'], asset['database_name'], asset['table_name'],
              asset['row_count'], json.dumps(asset['tags']), 'data-admin', 'active', created, datetime.now(), datetime.now()))
        print(f"  ✓ 创建数据资产: {asset['name']}")

    # ==================== 元数据数据库 ====================
    print("\n8. 创建元数据数据库...")

    metadata_dbs = [
        {'name': '生产数据库', 'description': '生产主数据库', 'owner': 'db-admin'},
        {'name': '数仓数据库', 'description': '数据仓库', 'owner': 'db-admin'},
        {'name': '分析数据库', 'description': '业务分析库', 'owner': 'bi-team'},
        {'name': '日志数据库', 'description': '日志存储', 'owner': 'ops-team'},
    ]

    for db in metadata_dbs:
        cursor.execute("""
            INSERT INTO metadata_databases (database_name, description, owner)
            VALUES (%s, %s, %s)
        """, (db['name'], db['description'], db['owner']))
        print(f"  ✓ 创建元数据数据库: {db['name']}")

    # ==================== 提交事务 ====================
    conn.commit()
    print("\n✅ 测试数据创建完成！")

    # ==================== 统计数据 ====================
    print("\n数据统计:")
    tables = [
        ('etl_tasks', 'ETL 任务'),
        ('etl_task_logs', 'ETL 任务日志'),
        ('workflows', '工作流'),
        ('workflow_executions', '工作流执行记录'),
        ('conversations', '对话'),
        ('knowledge_bases', '知识库'),
        ('indexed_documents', '索引文档'),
        ('data_assets', '数据资产'),
        ('metadata_databases', '元数据数据库')
    ]

    for table_name, display_name in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  {display_name}: {count} 条记录")

    cursor.close()
    conn.close()


if __name__ == '__main__':
    create_test_data()
