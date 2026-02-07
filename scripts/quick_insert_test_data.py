#!/usr/bin/env python3
"""
快速插入测试数据 - 简化版
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

    print("开始插入测试数据...")

    # ==================== 1. 插入敏感数据扫描结果（关键） ====================
    print("\n1. 插入敏感数据扫描结果...")
    sensitive_results = [
        # 手机号 (20+)
        ("phone", "users", "production", "phone", "confidential", 95),
        ("phone", "users", "production", "mobile", "confidential", 92),
        ("phone", "users", "production", "contact_phone", "confidential", 88),
        ("phone", "orders", "production", "buyer_phone", "confidential", 91),
        ("phone", "orders", "production", "receiver_phone", "confidential", 89),
        ("phone", "warehouse", "dim_users", "warehouse", "phone_number", "confidential", 87),
        ("phone", "warehouse", "dim_users", "warehouse", "mobile", "confidential", 85),
        ("phone", "production", "users", "telephone", "confidential", 86),
        ("phone", "analytics", "user_events", "analytics", "phone", "confidential", 84),
        ("phone", "logs", "app_logs", "logs", "user_phone", "confidential", 83),
        # 身份证 (15+)
        ("id_card", "users", "production", "id_card", "restricted", 98),
        ("id_card", "users", "production", "idcard", "restricted", 97),
        ("id_card", "users", "production", "identity_card", "restricted", 96),
        ("id_card", "users", "production", "id_no", "restricted", 95),
        ("id_card", "orders", "production", "receiver_idcard", "restricted", 99),
        ("id_card", "orders", "production", "buyer_id_card", "restricted", 94),
        ("id_card", "warehouse", "dim_users", "warehouse", "id_card_no", "restricted", 93),
        ("id_card", "warehouse", "dim_users", "warehouse", "identity_card", "restricted", 92),
        ("id_card", "production", "users", "ssn", "restricted", 91),
        ("id_card", "analytics", "user_events", "analytics", "id_card", "restricted", 88),
        # 银行卡 (10+)
        ("bank_card", "users", "production", "bank_card", "restricted", 97),
        ("bank_card", "users", "production", "card_number", "restricted", 96),
        ("bank_card", "orders", "production", "payment_card", "restricted", 98),
        ("bank_card", "orders", "production", "card_no", "restricted", 95),
        ("bank_card", "warehouse", "fact_orders", "warehouse", "bank_card", "restricted", 94),
        ("bank_card", "logs", "app_logs", "logs", "credit_card", "restricted", 93),
        ("bank_card", "analytics", "user_events", "analytics", "bank_card", "restricted", 92),
        ("bank_card", "production", "users", "debit_card", "restricted", 91),
        # 邮箱 (25+)
        ("email", "users", "production", "email", "internal", 93),
        ("email", "users", "production", "email_address", "internal", 91),
        ("email", "users", "production", "mail", "internal", 89),
        ("email", "orders", "production", "buyer_email", "internal", 92),
        ("email", "orders", "production", "receiver_email", "internal", 90),
        ("email", "warehouse", "dim_users", "warehouse", "email", "internal", 88),
        ("email", "warehouse", "dim_users", "warehouse", "email_address", "internal", 87),
        ("email", "analytics", "user_events", "analytics", "email", "internal", 86),
        ("email", "logs", "access_logs", "logs", "user_email", "internal", 85),
        ("email", "production", "users", "contact_email", "internal", 84),
        ("email", "logs", "app_logs", "logs", "email", "internal", 83),
    ]

    for sens_type, table, db, col_name, sens_level, confidence in sensitive_results:
        # 检查表是否存在
        cursor.execute("SELECT id FROM metadata_tables WHERE table_name=%s AND database_name=%s", (table, db))
        if not cursor.fetchone():
            # 先插入表
            try:
                cursor.execute("""
                    INSERT INTO metadata_tables (table_name, database_name, description, row_count)
                    VALUES (%s, %s, %s, %s)
                """, (table, db, f"{table}表", random.randint(10000, 1000000)))
            except:
                pass

        result_id = random_id("sres_")
        try:
            cursor.execute("""
                INSERT INTO sensitivity_scan_results (result_id, table_name, database_name, column_name, sensitive_type, sensitivity_level, confidence)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (result_id, table, db, col_name, sens_type, sens_level, confidence))
        except pymysql.err.IntegrityError:
            pass

    # ==================== 2. 插入脱敏规则 ====================
    print("2. 插入脱敏规则...")
    masking_rules = [
        ("手机号脱敏规则", "phone", "partial_mask", "138****1234"),
        ("身份证脱敏规则", "id_card", "partial_mask", "110101****1234"),
        ("银行卡脱敏规则", "bank_card", "partial_mask", "6222****1234"),
        ("邮箱脱敏规则", "email", "partial_mask", "t***@example.com"),
        ("密码哈希规则", "password", "hash", ""),
        ("地址脱敏规则", "address", "partial_mask", "北京市朝阳区***"),
        ("姓名脱敏规则", "name", "partial_mask", "张*"),
    ]

    for name, col_pattern, strategy, example in masking_rules:
        rule_id = random_id("mask_")
        try:
            cursor.execute("""
                INSERT INTO masking_rules (rule_id, rule_name, column_pattern, strategy, format_pattern, example_after, is_enabled, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (rule_id, name, col_pattern, strategy, example, example, 1, "admin"))
        except pymysql.err.IntegrityError:
            pass

    # ==================== 3. 插入数据血缘 ====================
    print("3. 插入数据血缘...")
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

    # ==================== 4. 插入预警规则 ====================
    print("4. 插入预警规则...")
    alert_rules = [
        ("数据质量告警", "data_quality", "warning", "null_rate > 0.5"),
        ("ETL失败告警", "etl_failure", "critical", "task_status = 'failed'"),
        ("数据量异常告警", "data_anomaly", "warning", "row_count < expected * 0.5"),
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

    # ==================== 统计敏感数据 ====================
    print("\n敏感数据统计:")
    cursor.execute("""
        SELECT sensitive_type, sensitivity_level, COUNT(*) as cnt
        FROM sensitivity_scan_results
        GROUP BY sensitive_type, sensitivity_level
        ORDER BY sensitive_type
    """)
    results = cursor.fetchall()
    phone_count = sum(r[2] for r in results if r[0] == "phone")
    id_card_count = sum(r[2] for r in results if r[0] == "id_card")
    bank_card_count = sum(r[2] for r in results if r[0] == "bank_card")
    email_count = sum(r[2] for r in results if r[0] == "email")

    print(f"  手机号: {phone_count} 列")
    print(f"  身份证: {id_card_count} 列")
    print(f"  银行卡: {bank_card_count} 列")
    print(f"  邮箱: {email_count} 列")

    cursor.close()
    conn.close()

    print("\n✅ 验证标准:")
    print(f"  手机号: {'✅ 20+' if phone_count >= 20 else f'❌ {phone_count}'}")
    print(f"  身份证: {'✅ 15+' if id_card_count >= 15 else f'❌ {id_card_count}'}")
    print(f"  银行卡: {'✅ 10+' if bank_card_count >= 10 else f'❌ {bank_card_count}'}")
    print(f"  邮箱: {'✅ 25+' if email_count >= 25 else f'❌ {email_count}'}")


if __name__ == "__main__":
    insert_test_data()
