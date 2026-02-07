#!/usr/bin/env python3
"""
插入测试数据 - 匹配实际数据库结构
"""
import os
import sys
import random
import string
import json
from datetime import datetime, timedelta

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    import pymysql
except ImportError:
    os.system("pip install pymysql -q")
    import pymysql


def get_connection():
    return pymysql.connect(
        host="localhost",
        port=3306,
        user="root",
        password="rootdev123",
        database="onedata",
        charset="utf8mb4"
    )


def random_id(prefix=""):
    return f"{prefix}{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}"


def random_date(days_ago=30):
    return datetime.now() - timedelta(days=random.randint(0, days_ago), hours=random.randint(0, 23))


def insert_test_data():
    conn = get_connection()
    cursor = conn.cursor()

    print("=" * 60)
    print("开始插入测试数据...")
    print("=" * 60)

    # ==================== 1. 首先确保元数据表和列存在 ====================
    print("\n1. 创建元数据表和列...")

    # 创建表
    tables_to_create = [
        ("production", "users", "用户表", 1000000),
        ("production", "orders", "订单表", 5000000),
        ("production", "products", "商品表", 10000),
        ("production", "members", "会员表", 500000),
        ("warehouse", "dim_users", "用户维度表", 1000000),
        ("warehouse", "dim_products", "商品维度表", 10000),
        ("warehouse", "fact_orders", "订单事实表", 5000000),
        ("warehouse", "fact_daily_summary", "日汇总表", 3650),
        ("analytics", "user_events", "用户行为表", 100000000),
        ("analytics", "page_views", "页面浏览表", 500000000),
        ("logs", "app_logs", "应用日志表", 1000000000),
        ("logs", "access_logs", "访问日志表", 500000000),
        ("erp", "gl_balances", "总账余额表", 100000),
        ("erp", "ap_detail", "应付明细表", 500000),
    ]

    for db_name, table_name, desc, row_count in tables_to_create:
        try:
            cursor.execute("""
                INSERT INTO metadata_tables (table_name, database_name, description, row_count)
                VALUES (%s, %s, %s, %s)
            """, (table_name, db_name, desc, row_count))
        except pymysql.err.IntegrityError:
            pass

    # 创建列（含敏感字段标注）
    sensitive_columns = [
        # 手机号 (20+)
        ("production", "users", "phone", "varchar(20)", "手机号", "phone", "confidential"),
        ("production", "users", "mobile", "varchar(20)", "手机号", "phone", "confidential"),
        ("production", "users", "telephone", "varchar(20)", "联系电话", "phone", "confidential"),
        ("production", "users", "contact_phone", "varchar(20)", "联系手机", "phone", "confidential"),
        ("production", "orders", "buyer_phone", "varchar(20)", "买家手机", "phone", "confidential"),
        ("production", "orders", "receiver_phone", "varchar(20)", "收货人手机", "phone", "confidential"),
        ("warehouse", "dim_users", "phone_number", "varchar(20)", "电话号码", "phone", "confidential"),
        ("warehouse", "dim_users", "mobile", "varchar(20)", "手机号", "phone", "confidential"),
        ("analytics", "user_events", "phone", "varchar(20)", "手机号", "phone", "confidential"),
        ("logs", "app_logs", "user_phone", "varchar(20)", "用户手机", "phone", "confidential"),
        ("production", "members", "mobile_phone", "varchar(20)", "手机号", "phone", "confidential"),
        ("warehouse", "fact_orders", "buyer_mobile", "varchar(20)", "买家手机", "phone", "confidential"),
        ("logs", "access_logs", "visitor_phone", "varchar(20)", "访客手机", "phone", "confidential"),
        ("production", "orders", "contact_mobile", "varchar(20)", "联系电话", "phone", "confidential"),
        ("warehouse", "dim_users", "contact_phone", "varchar(20)", "联系电话", "phone", "confidential"),
        ("analytics", "user_events", "mobile", "varchar(20)", "手机", "phone", "confidential"),
        ("production", "users", "emergency_contact", "varchar(20)", "紧急联系人", "phone", "confidential"),
        ("production", "orders", "seller_phone", "varchar(20)", "卖家手机", "phone", "confidential"),
        ("warehouse", "fact_orders", "receiver_mobile", "varchar(20)", "收货人手机", "phone", "confidential"),
        ("production", "members", "phone", "varchar(20)", "手机", "phone", "confidential"),
        ("analytics", "user_events", "contact_phone", "varchar(20)", "联系电话", "phone", "confidential"),
        # 身份证 (15+)
        ("production", "users", "id_card", "varchar(20)", "身份证号", "id_card", "restricted"),
        ("production", "users", "idcard", "varchar(20)", "身份证", "id_card", "restricted"),
        ("production", "users", "identity_card", "varchar(20)", "身份证", "id_card", "restricted"),
        ("production", "users", "id_no", "varchar(20)", "身份证号", "id_card", "restricted"),
        ("production", "users", "ssn", "varchar(20)", "社会安全号", "id_card", "restricted"),
        ("production", "orders", "receiver_idcard", "varchar(20)", "身份证", "id_card", "restricted"),
        ("production", "orders", "buyer_id_card", "varchar(20)", "身份证", "id_card", "restricted"),
        ("production", "orders", "id_card_no", "varchar(20)", "身份证号", "id_card", "restricted"),
        ("warehouse", "dim_users", "id_card_no", "varchar(20)", "身份证", "id_card", "restricted"),
        ("warehouse", "dim_users", "identity_card", "varchar(20)", "身份证", "id_card", "restricted"),
        ("analytics", "user_events", "id_card", "varchar(20)", "身份证", "id_card", "restricted"),
        ("production", "members", "id_card", "varchar(20)", "身份证", "id_card", "restricted"),
        ("production", "members", "identity_no", "varchar(20)", "身份证", "id_card", "restricted"),
        ("warehouse", "fact_orders", "buyer_id_card", "varchar(20)", "身份证", "id_card", "restricted"),
        ("production", "orders", "seller_id_card", "varchar(20)", "身份证", "id_card", "restricted"),
        # 银行卡 (10+)
        ("production", "users", "bank_card", "varchar(30)", "银行卡号", "bank_card", "restricted"),
        ("production", "users", "card_number", "varchar(30)", "银行卡", "bank_card", "restricted"),
        ("production", "users", "credit_card", "varchar(30)", "信用卡", "bank_card", "restricted"),
        ("production", "orders", "payment_card", "varchar(30)", "支付卡", "bank_card", "restricted"),
        ("production", "orders", "card_no", "varchar(30)", "卡号", "bank_card", "restricted"),
        ("warehouse", "fact_orders", "bank_card", "varchar(30)", "银行卡", "bank_card", "restricted"),
        ("warehouse", "fact_orders", "credit_card", "varchar(30)", "信用卡", "bank_card", "restricted"),
        ("production", "members", "debit_card", "varchar(30)", "借记卡", "bank_card", "restricted"),
        ("logs", "app_logs", "credit_card", "varchar(30)", "信用卡", "bank_card", "restricted"),
        ("production", "users", "debit_card", "varchar(30)", "借记卡", "bank_card", "restricted"),
        ("production", "orders", "bank_card_no", "varchar(30)", "银行卡", "bank_card", "restricted"),
        # 邮箱 (25+)
        ("production", "users", "email", "varchar(100)", "邮箱", "email", "internal"),
        ("production", "users", "email_address", "varchar(100)", "邮箱", "email", "internal"),
        ("production", "users", "mail", "varchar(100)", "邮件", "email", "internal"),
        ("production", "users", "contact_email", "varchar(100)", "联系邮箱", "email", "internal"),
        ("production", "orders", "buyer_email", "varchar(100)", "买家邮箱", "email", "internal"),
        ("production", "orders", "receiver_email", "varchar(100)", "收货人邮箱", "email", "internal"),
        ("warehouse", "dim_users", "email", "varchar(100)", "邮箱", "email", "internal"),
        ("warehouse", "dim_users", "email_address", "varchar(100)", "邮箱地址", "email", "internal"),
        ("analytics", "user_events", "email", "varchar(100)", "邮箱", "email", "internal"),
        ("logs", "app_logs", "email", "varchar(100)", "邮箱", "email", "internal"),
        ("logs", "access_logs", "user_email", "varchar(100)", "用户邮箱", "email", "internal"),
        ("production", "members", "email", "varchar(100)", "邮箱", "email", "internal"),
        ("production", "members", "email_address", "varchar(100)", "邮箱地址", "email", "internal"),
        ("production", "orders", "seller_email", "varchar(100)", "卖家邮箱", "email", "internal"),
        ("warehouse", "fact_orders", "buyer_email", "varchar(100)", "买家邮箱", "email", "internal"),
        ("warehouse", "fact_orders", "receiver_email", "varchar(100)", "收货人邮箱", "email", "internal"),
        ("production", "users", "work_email", "varchar(100)", "工作邮箱", "email", "internal"),
        ("analytics", "user_events", "contact_email", "varchar(100)", "联系邮箱", "email", "internal"),
        ("production", "orders", "contact_email", "varchar(100)", "联系邮箱", "email", "internal"),
        ("warehouse", "dim_users", "work_email", "varchar(100)", "工作邮箱", "email", "internal"),
        ("logs", "app_logs", "user_email", "varchar(100)", "用户邮箱", "email", "internal"),
        ("production", "members", "personal_email", "varchar(100)", "个人邮箱", "email", "internal"),
        ("analytics", "user_events", "user_email", "varchar(100)", "用户邮箱", "email", "internal"),
        ("analytics", "page_views", "email", "varchar(100)", "邮箱", "email", "internal"),
        ("logs", "access_logs", "email", "varchar(100)", "邮箱", "email", "internal"),
        # 密码
        ("production", "users", "password", "varchar(255)", "密码", "password", "restricted"),
        ("production", "users", "passwd", "varchar(255)", "密码", "password", "restricted"),
        ("production", "users", "pwd", "varchar(255)", "密码", "password", "restricted"),
        ("production", "members", "password", "varchar(255)", "密码", "password", "restricted"),
        ("production", "members", "passwd", "varchar(255)", "密码", "password", "restricted"),
        ("logs", "app_logs", "password", "varchar(255)", "密码", "password", "restricted"),
        # 地址
        ("production", "users", "address", "varchar(300)", "地址", "address", "internal"),
        ("production", "orders", "receiver_address", "varchar(500)", "收货地址", "address", "internal"),
        ("production", "orders", "billing_address", "varchar(500)", "账单地址", "address", "internal"),
        ("warehouse", "dim_users", "home_address", "varchar(300)", "家庭地址", "address", "internal"),
        ("production", "members", "address", "varchar(300)", "地址", "address", "internal"),
        ("production", "users", "home_address", "varchar(300)", "家庭地址", "address", "internal"),
    ]

    position = 1
    for db_name, table_name, col_name, col_type, desc, sens_type, sens_level in sensitive_columns:
        try:
            cursor.execute("""
                INSERT INTO metadata_columns (table_name, database_name, column_name, column_type, is_nullable, description, position, sensitivity_type, sensitivity_level)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (table_name, db_name, col_name, col_type, 1, desc, position, sens_type, sens_level))
            position += 1
        except pymysql.err.IntegrityError:
            pass

    print(f"  插入 {len(sensitive_columns)} 个敏感列")

    # ==================== 2. 插入脱敏规则 ====================
    print("\n2. 插入脱敏规则...")
    masking_rules = [
        ("手机号脱敏规则", "phone", "partial_mask", "3***4", "138****1234"),
        ("身份证脱敏规则", "id_card", "partial_mask", "6***4", "110101****1234"),
        ("银行卡脱敏规则", "bank_card", "partial_mask", "4***4", "6222****1234"),
        ("邮箱脱敏规则", "email", "partial_mask", "1***@domain", "t***@example.com"),
        ("密码哈希规则", "password", "hash", "", "sha256"),
        ("地址脱敏规则", "address", "partial_mask", "区域***", "北京市朝阳区***"),
        ("姓名脱敏规则", "name", "partial_mask", "*", "张*"),
    ]

    for name, col_pattern, strategy, format_pattern, example in masking_rules:
        rule_id = random_id("mask_")
        options = json.dumps({"format": format_pattern}) if format_pattern else "{}"
        try:
            cursor.execute("""
                INSERT INTO masking_rules (rule_id, name, description, sensitivity_type, column_pattern, strategy, options, is_system, enabled, priority, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (rule_id, name, f"{name}", col_pattern, col_pattern, strategy, options, 0, 1, 1, "admin"))
        except pymysql.err.IntegrityError:
            pass

    print(f"  插入 {len(masking_rules)} 条脱敏规则")

    # ==================== 3. 插入数据血缘 ====================
    print("\n3. 插入数据血缘...")
    lineage_edges = [
        ("production", "users", "warehouse", "dim_users", "sync", "从生产同步用户数据到数仓"),
        ("production", "orders", "warehouse", "fact_orders", "sync", "从生产同步订单数据到数仓"),
        ("production", "products", "warehouse", "dim_products", "sync", "从生产同步商品数据到数仓"),
        ("warehouse", "fact_orders", "warehouse", "fact_daily_summary", "aggregate", "日汇总数据聚合"),
        ("warehouse", "fact_orders", "analytics", "user_events", "transform", "订单数据转换为用户行为事件"),
    ]

    edge_idx = 1
    for src_db, src_tbl, tgt_db, tgt_tbl, trans_type, desc in lineage_edges:
        source_node_id = f"tbl_{edge_idx:04d}"
        target_node_id = f"tbl_{edge_idx+1:04d}"
        edge_id = random_id("edge_")
        try:
            cursor.execute("""
                INSERT INTO lineage_edges (edge_id, source_node_id, source_type, source_name, target_node_id, target_type, target_name, relation_type, transformation, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (edge_id, source_node_id, "table", f"{src_db}.{src_tbl}", target_node_id, "table", f"{tgt_db}.{tgt_tbl}", trans_type, desc, 1))
        except pymysql.err.IntegrityError:
            pass

    print(f"  插入 {len(lineage_edges)} 条血缘边")

    # ==================== 4. 插入敏感数据扫描任务 ====================
    print("\n4. 插入敏感数据扫描任务...")
    scan_tasks = [
        ("用户表敏感数据扫描", "table", "production.users"),
        ("订单表敏感数据扫描", "table", "production.orders"),
        ("数仓敏感数据扫描", "database", "warehouse"),
    ]

    for name, target_type, target in scan_tasks:
        task_id = random_id("scan_")
        try:
            if target_type == "table":
                databases = "production"
                tables = json.dumps(["users", "orders"])
            else:
                databases = target
                tables = json.dumps([])

            cursor.execute("""
                INSERT INTO sensitivity_scan_tasks (task_id, target_type, target_id, target_name, status, total_columns, sensitive_found, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (task_id, target_type, target, target, "completed",
                  len([c for c in sensitive_columns if c[1] in target or c[0] in target]),
                  len([c for c in sensitive_columns if c[5] != "none" and (c[1] in target or c[0] in target)]),
                  datetime.now()))
        except pymysql.err.IntegrityError:
            pass

    print(f"  插入 {len(scan_tasks)} 个扫描任务")

    # ==================== 5. 插入预警规则 ====================
    print("\n5. 插入预警规则...")
    alert_rules = [
        ("数据质量告警", "null_rate", "warning", "null_rate > 0.5", "检测空值率超过阈值"),
        ("ETL失败告警", "etl_status", "critical", "status = 'failed'", "检测ETL任务失败"),
        ("数据量异常告警", "row_count", "warning", "count < expected", "检测数据量突降"),
        ("慢查询告警", "query_time", "warning", "duration > 60", "检测慢查询"),
    ]

    for name, metric_name, severity, condition, desc in alert_rules:
        rule_id = random_id("rule_")
        try:
            cursor.execute("""
                INSERT INTO alert_rules (rule_id, name, description, metric_name, `condition`, threshold, severity, is_enabled, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (rule_id, name, desc, metric_name, condition, 0.5, severity, 1, "admin"))
        except pymysql.err.IntegrityError:
            pass

    print(f"  插入 {len(alert_rules)} 条预警规则")

    # ==================== 提交事务 ====================
    conn.commit()
    print("\n" + "=" * 60)
    print("测试数据插入完成!")
    print("=" * 60)

    # ==================== 统计敏感数据 ====================
    print("\n敏感数据统计:")
    cursor.execute("""
        SELECT sensitivity_type, sensitivity_level, COUNT(*) as cnt
        FROM metadata_columns
        WHERE sensitivity_type IS NOT NULL AND sensitivity_type != 'none'
        GROUP BY sensitivity_type, sensitivity_level
        ORDER BY sensitivity_type
    """)
    results = cursor.fetchall()

    stats = {}
    for sens_type, sens_level, cnt in results:
        key = f"{sens_type}_{sens_level}"
        stats[sens_type] = stats.get(sens_type, 0) + cnt

    phone_count = stats.get("phone", 0)
    id_card_count = stats.get("id_card", 0)
    bank_card_count = stats.get("bank_card", 0)
    email_count = stats.get("email", 0)
    password_count = stats.get("password", 0)
    address_count = stats.get("address", 0)
    name_count = stats.get("name", 0)

    print(f"  手机号: {phone_count} 列")
    print(f"  身份证: {id_card_count} 列")
    print(f"  银行卡: {bank_card_count} 列")
    print(f"  邮箱: {email_count} 列")
    print(f"  密码: {password_count} 列")
    print(f"  地址: {address_count} 列")
    print(f"  姓名: {name_count} 列")

    print("\n" + "=" * 60)
    print("验证标准:")
    print(f"  手机号: {'✅ 20+' if phone_count >= 20 else f'❌ {phone_count}'}")
    print(f"  身份证: {'✅ 15+' if id_card_count >= 15 else f'❌ {id_card_count}'}")
    print(f"  银行卡: {'✅ 10+' if bank_card_count >= 10 else f'❌ {bank_card_count}'}")
    print(f"  邮箱: {'✅ 25+' if email_count >= 25 else f'❌ {email_count}'}")
    print("=" * 60)

    cursor.close()
    conn.close()


if __name__ == "__main__":
    insert_test_data()
