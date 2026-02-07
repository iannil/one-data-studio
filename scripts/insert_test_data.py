#!/usr/bin/env python3
"""
快速插入测试数据脚本 - 匹配实际数据库结构
"""
import os
import sys
import random
import string
import json
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    import pymysql
except ImportError:
    os.system("pip install pymysql -q")
    import pymysql


def get_connection():
    """获取数据库连接"""
    return pymysql.connect(
        host="localhost",
        port=3306,
        user="root",
        password="rootdev123",
        database="onedata",
        charset="utf8mb4"
    )


def random_id(prefix=""):
    """生成随机ID"""
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    if prefix:
        return f"{prefix}{random_part}"
    return random_part


def random_date(days_ago=30):
    """生成随机日期"""
    return datetime.now() - timedelta(days=random.randint(0, days_ago), hours=random.randint(0, 23))


def insert_test_data():
    """插入测试数据"""
    conn = get_connection()
    cursor = conn.cursor()

    print("开始插入测试数据...")

    # ==================== 插入角色 ====================
    print("\n1. 插入角色...")
    roles = [
        ("data_admin", "数据管理员", "负责数据治理、元数据管理", "system", 1),
        ("data_engineer", "数据工程师", "负责ETL任务开发", "system", 2),
        ("ai_developer", "AI开发者", "负责模型训练、知识库管理", "system", 3),
        ("data_analyst", "数据分析师", "负责数据分析、BI报表", "system", 4),
        ("system_admin", "系统管理员", "负责系统配置、用户管理", "system", 5),
    ]

    for role_id, name, desc, role_type, priority in roles:
        try:
            cursor.execute("""
                INSERT INTO roles (role_id, name, description, role_type, is_system, is_active, priority, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (role_id, name, desc, role_type, 1, 1, priority, "system"))
        except pymysql.err.IntegrityError:
            pass  # 已存在则跳过

    # ==================== 插入用户 ====================
    print("2. 插入用户...")
    users = []
    role_list = ["data_admin", "data_engineer", "ai_developer", "data_analyst", "system_admin"]

    user_count = {"data_admin": 2, "data_engineer": 5, "ai_developer": 5, "data_analyst": 8, "system_admin": 3}

    user_id = 1
    for role, count in user_count.items():
        for i in range(count):
            u_id = random_id("user_")
            username = f"{role}_{i+1}"
            email = f"{role}_{i+1}@example.com"
            display_name = f"测试用户{i+1}"
            department = {"data_admin": "数据治理部", "data_engineer": "数据工程部",
                          "ai_developer": "AI研发部", "data_analyst": "数据分析部",
                          "system_admin": "系统运维部"}[role]

            try:
                cursor.execute("""
                    INSERT INTO users (user_id, username, email, display_name, phone, department, status, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (u_id, username, email, display_name, "13800138000", department, "active", "system"))
                users.append((u_id, role))
                user_id += 1
            except pymysql.err.IntegrityError:
                pass

    # 插入用户角色关联
    print("3. 插入用户角色关联...")
    for u_id, role in users:
        try:
            cursor.execute("""
                INSERT INTO user_roles (user_id, role_id)
                VALUES (%s, %s)
            """, (u_id, role))
        except pymysql.err.IntegrityError:
            pass

    # ==================== 插入数据源 ====================
    print("4. 插入数据源...")
    datasources = [
        ("MySQL生产库", "mysql", {"host": "prod-db", "port": 3306, "database": "production"}),
        ("PostgreSQL数仓", "postgresql", {"host": "warehouse", "port": 5432, "database": "dw"}),
        ("MongoDB日志", "mongodb", {"host": "log-db", "port": 27017, "database": "app_logs"}),
        ("Hive数据湖", "hive", {"host": "hive", "port": 10000, "database": "data_lake"}),
    ]

    for name, ds_type, conn_config in datasources:
        ds_id = random_id("ds_")
        try:
            cursor.execute("""
                INSERT INTO datasources (source_id, name, description, type, connection_config, status, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (ds_id, f"{name}数据源", f"{name}连接配置", ds_type,
                 json.dumps(conn_config), "active", "admin"))
        except pymysql.err.IntegrityError:
            pass

    # ==================== 插入元数据库 ====================
    print("5. 插入元数据库...")
    db_names = ["production", "warehouse", "analytics", "logs", "erp"]
    for db_name in db_names:
        try:
            cursor.execute("""
                INSERT INTO metadata_databases (database_name, description, owner)
                VALUES (%s, %s, %s)
            """, (db_name, f"{db_name}数据库", "data-team"))
        except pymysql.err.IntegrityError:
            pass

    # ==================== 插入元数据表 ====================
    print("6. 插入元数据表...")
    table_configs = [
        ("production", "users", "用户表", 1000000),
        ("production", "orders", "订单表", 5000000),
        ("production", "products", "商品表", 10000),
        ("warehouse", "dim_users", "用户维度表", 1000000),
        ("warehouse", "fact_orders", "订单事实表", 5000000),
        ("warehouse", "fact_daily_summary", "日汇总表", 3650),
        ("analytics", "user_events", "用户行为表", 100000000),
        ("analytics", "page_views", "页面浏览表", 500000000),
        ("logs", "app_logs", "应用日志表", 1000000000),
        ("logs", "access_logs", "访问日志表", 500000000),
        ("erp", "gl_balances", "总账余额表", 100000),
        ("erp", "ap_detail", "应付明细表", 500000),
        ("erp", "ar_detail", "应收明细表", 600000),
    ]

    for db_name, table_name, desc, row_count in table_configs:
        try:
            cursor.execute("""
                INSERT INTO metadata_tables (table_name, database_name, description, row_count)
                VALUES (%s, %s, %s, %s)
            """, (table_name, db_name, desc, row_count))
        except pymysql.err.IntegrityError:
            pass

    # ==================== 插入元数据列（含敏感字段）====================
    print("7. 插入元数据列...")
    column_configs = [
        # 敏感列 - 手机号
        ("production", "users", "phone", "varchar(20)", "手机号", "phone", "confidential"),
        ("production", "users", "mobile", "varchar(20)", "备用手机", "phone", "confidential"),
        ("production", "users", "id_card", "varchar(20)", "身份证号", "id_card", "restricted"),
        ("production", "users", "email", "varchar(100)", "邮箱", "email", "internal"),
        ("production", "users", "password", "varchar(255)", "密码", "password", "restricted"),
        ("production", "users", "bank_card", "varchar(30)", "银行卡", "bank_card", "restricted"),
        ("production", "users", "real_name", "varchar(50)", "真实姓名", "name", "internal"),
        ("production", "users", "home_address", "varchar(200)", "家庭地址", "address", "internal"),
        # 更多敏感列
        ("production", "orders", "buyer_phone", "varchar(20)", "买家手机", "phone", "confidential"),
        ("production", "orders", "receiver_phone", "varchar(20)", "收货人手机", "phone", "confidential"),
        ("production", "orders", "receiver_idcard", "varchar(20)", "身份证", "id_card", "restricted"),
        ("production", "orders", "receiver_name", "varchar(50)", "收货人姓名", "name", "internal"),
        ("production", "orders", "receiver_address", "varchar(300)", "收货地址", "address", "internal"),
        ("warehouse", "dim_users", "phone_number", "varchar(20)", "电话号码", "phone", "confidential"),
        ("warehouse", "dim_users", "email_address", "varchar(100)", "邮箱", "email", "internal"),
        ("warehouse", "dim_users", "id_card_no", "varchar(20)", "身份证号", "id_card", "restricted"),
        ("warehouse", "dim_users", "user_name", "varchar(50)", "用户姓名", "name", "internal"),
        ("analytics", "user_events", "device_id", "varchar(64)", "设备ID", "device", "internal"),
        ("analytics", "user_events", "session_id", "varchar(64)", "会话ID", "session", "internal"),
        ("logs", "app_logs", "user_ip", "varchar(50)", "用户IP", "ip", "internal"),
        ("logs", "access_logs", "visitor_id", "varchar(64)", "访客ID", "visitor", "internal"),
    ]

    position = 1
    for db_name, table_name, col_name, col_type, desc, sens_type, sens_level in column_configs:
        # 检查表是否存在
        cursor.execute("""
            SELECT id FROM metadata_tables WHERE table_name=%s AND database_name=%s
        """, (table_name, db_name))
        if not cursor.fetchone():
            continue

        try:
            cursor.execute("""
                INSERT INTO metadata_columns (table_name, database_name, column_name, column_type, is_nullable, description, position, sensitivity_type, sensitivity_level)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (table_name, db_name, col_name, col_type, 1, desc, position, sens_type, sens_level))
            position += 1
        except pymysql.err.IntegrityError:
            pass

    # ==================== 插入数据资产 ====================
    print("8. 插入数据资产...")
    assets = [
        ("用户基础信息表", "users", "production", "用户数据", 90, "S"),
        ("订单主表", "orders", "production", "交易数据", 95, "S"),
        ("商品信息表", "products", "production", "产品数据", 85, "A"),
        ("用户维度表", "dim_users", "warehouse", "用户数据", 88, "A"),
        ("订单事实表", "fact_orders", "warehouse", "交易数据", 92, "A"),
        ("用户行为事件", "user_events", "analytics", "行为数据", 75, "B"),
        ("应用日志", "app_logs", "logs", "日志数据", 70, "B"),
        ("总账余额", "gl_balances", "erp", "财务数据", 80, "A"),
    ]

    for name, table, db, category, score, grade in assets:
        asset_id = random_id("asset_")
        try:
            cursor.execute("""
                INSERT INTO data_assets (asset_id, name, source_type, database_name, table_name, description, asset_type, total_score, grade, owner, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (asset_id, name, "mysql", db, table, f"{name}资产", "table", score, grade, "data-team", "admin"))
        except pymysql.err.IntegrityError:
            pass

    # ==================== 插入敏感数据扫描任务 ====================
    print("9. 插入敏感数据扫描任务...")
    scan_tasks = [
        ("用户表敏感数据扫描", "production", "users"),
        ("订单表敏感数据扫描", "production", "orders"),
        ("数仓敏感数据扫描", "warehouse", "dim_users"),
    ]

    for name, db, table in scan_tasks:
        task_id = random_id("scan_")
        try:
            cursor.execute("""
                INSERT INTO sensitivity_scan_tasks (task_id, name, description, status, started_at, finished_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (task_id, name, f"扫描{table}表的敏感字段", "completed", random_date(60), random_date(30)))
        except pymysql.err.IntegrityError:
            pass

    # ==================== 插入敏感数据扫描结果 ====================
    print("10. 插入敏感数据扫描结果...")
    sensitive_results = [
        ("phone", "users", "production", "phone", "confidential", 95),
        ("phone", "users", "production", "mobile", "confidential", 90),
        ("id_card", "users", "production", "id_card", "restricted", 98),
        ("email", "users", "production", "email", "internal", 92),
        ("password", "users", "production", "password", "restricted", 100),
        ("bank_card", "users", "production", "bank_card", "restricted", 97),
        ("phone", "orders", "production", "buyer_phone", "confidential", 93),
        ("id_card", "orders", "production", "receiver_idcard", "restricted", 99),
    ]

    for sens_type, table, db, col_name, sens_level, confidence in sensitive_results:
        result_id = random_id("sres_")
        try:
            cursor.execute("""
                INSERT INTO sensitivity_scan_results (result_id, table_name, database_name, column_name, sensitive_type, sensitivity_level, confidence)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (result_id, table, db, col_name, sens_type, sens_level, confidence))
        except pymysql.err.IntegrityError:
            pass

    # ==================== 插入脱敏规则 ====================
    print("11. 插入脱敏规则...")
    masking_rules = [
        ("手机号脱敏规则", "phone", "partial_mask", "3***4", "138****1234"),
        ("身份证脱敏规则", "id_card", "partial_mask", "6***4", "110101****1234"),
        ("银行卡脱敏规则", "bank_card", "partial_mask", "4***4", "6222****1234"),
        ("邮箱脱敏规则", "email", "partial_mask", "1***@domain", "t***@example.com"),
        ("密码哈希规则", "password", "hash", "", "hash存储"),
    ]

    for name, col_pattern, strategy, format_pattern, example in masking_rules:
        rule_id = random_id("mask_")
        try:
            cursor.execute("""
                INSERT INTO masking_rules (rule_id, rule_name, column_pattern, strategy, format_pattern, example_before, example_after, is_enabled, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (rule_id, name, col_pattern, strategy, format_pattern, "原始值", example, 1, "admin"))
        except pymysql.err.IntegrityError:
            pass

    # ==================== 插入数据血缘 ====================
    print("12. 插入数据血缘...")
    lineage_edges = [
        ("production", "users", "warehouse", "dim_users", "sync"),
        ("production", "orders", "warehouse", "fact_orders", "sync"),
        ("production", "products", "warehouse", "dim_products", "sync"),
        ("warehouse", "fact_orders", "warehouse", "fact_daily_summary", "aggregate"),
    ]

    edge_id = 1
    for src_db, src_tbl, tgt_db, tgt_tbl, trans_type in lineage_edges:
        try:
            cursor.execute("""
                INSERT INTO data_lineage (source_table_id, source_table_name, source_database, target_table_id, target_table_name, target_database)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (f"tbl_{edge_id:04d}", src_tbl, src_db, f"tbl_{edge_id+1:04d}", tgt_tbl, tgt_db))
            edge_id += 2
        except pymysql.err.IntegrityError:
            pass

    # ==================== 插入知识库 ====================
    print("13. 插入知识库...")
    knowledge_bases = [
        ("产品知识库", "product_docs", 5),
        ("技术文档库", "tech_docs", 5),
        ("FAQ知识库", "faq_docs", 5),
    ]

    for kb_name, code, doc_count in knowledge_bases:
        kb_id = random_id("kb_")
        try:
            cursor.execute("""
                INSERT INTO knowledge_bases (kb_id, name, description, collection_name, document_count, created_by)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (kb_id, kb_name, f"{kb_name}知识库", code, doc_count, "admin"))
        except pymysql.err.IntegrityError:
            pass

    # ==================== 插入预警规则 ====================
    print("14. 插入预警规则...")
    alert_rules = [
        ("数据质量告警", "data_quality", "warning", "null_rate > 0.5"),
        ("ETL失败告警", "etl_failure", "critical", "task_status = 'failed'"),
        ("数据量异常告警", "data_anomaly", "warning", "row_count < expected * 0.5"),
        ("慢查询告警", "performance", "warning", "query_time > 60"),
    ]

    for name, alert_type, level, condition in alert_rules:
        rule_id = random_id("rule_")
        try:
            cursor.execute("""
                INSERT INTO alert_rules (rule_id, rule_name, alert_type, alert_level, condition, description, is_enabled, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (rule_id, name, alert_type, level, condition, f"{name}规则", 1, "admin"))
        except pymysql.err.IntegrityError:
            pass

    # ==================== 提交事务 ====================
    conn.commit()
    print("\n✅ 测试数据插入完成!")

    # ==================== 统计数据 ====================
    print("\n数据统计:")
    tables = [
        ("roles", "角色"),
        ("users", "用户"),
        ("user_roles", "用户角色"),
        ("datasources", "数据源"),
        ("metadata_databases", "元数据库"),
        ("metadata_tables", "元数据表"),
        ("metadata_columns", "元数据列"),
        ("data_assets", "数据资产"),
        ("sensitivity_scan_tasks", "扫描任务"),
        ("sensitivity_scan_results", "扫描结果"),
        ("masking_rules", "脱敏规则"),
        ("data_lineage", "数据血缘"),
        ("knowledge_bases", "知识库"),
        ("alert_rules", "预警规则"),
        ("etl_tasks", "ETL任务"),
    ]

    for table_name, display_name in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  {display_name}: {count} 条")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    insert_test_data()
