#!/usr/bin/env python3
"""
Admin API 默认角色初始化脚本

用途：在数据库中创建默认角色，确保用户管理功能正常工作
"""

import os
import sys
from sqlalchemy import create_engine, text

# 数据库连接配置
DB_HOST = os.getenv('DB_HOST', 'mysql')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'test123')
DB_NAME = os.getenv('DB_NAME', 'onedata')

DEFAULT_ROLES = [
    ('role_admin', 'admin', '系统管理员', '拥有所有权限的系统管理员', 'system', 1, 1),
    ('role_user', 'user', '普通用户', '普通用户角色', 'business', 1, 10),
    ('role_data_engineer', 'data_engineer', '数据工程师', '数据工程师角色', 'technical', 1, 5),
    ('role_data_admin', 'data_admin', '数据管理员', '数据管理员角色', 'technical', 1, 5),
    ('role_algorithm_engineer', 'algorithm_engineer', '算法工程师', '算法工程师角色', 'technical', 1, 5),
    ('role_business_user', 'business_user', '业务用户', '业务用户角色', 'business', 1, 10),
]

def init_roles():
    """初始化默认角色"""
    engine = create_engine(
        f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}',
        echo=False
    )

    with engine.connect() as conn:
        # 检查现有角色
        result = conn.execute(text('SELECT role_id, name FROM roles'))
        existing_roles = {row[0]: row[1] for row in result}
        print(f"现有角色: {existing_roles}")

        # 添加缺失的角色
        for role_id, name, display_name, description, role_type, is_active, priority in DEFAULT_ROLES:
            if role_id not in existing_roles:
                print(f"添加角色: {display_name} ({role_id})")
                conn.execute(text('''
                    INSERT INTO roles (role_id, name, display_name, description, role_type, is_system, is_active, priority, created_by)
                    VALUES (:role_id, :name, :display_name, :description, :role_type, 1, :is_active, :priority, 'system')
                '''), {
                    'role_id': role_id,
                    'name': name,
                    'display_name': display_name,
                    'description': description,
                    'role_type': role_type,
                    'is_active': is_active,
                    'priority': priority,
                })
                conn.commit()
            else:
                print(f"角色已存在: {display_name} ({role_id})")

        # 列出所有角色
        result = conn.execute(text('SELECT role_id, name, display_name FROM roles ORDER BY priority'))
        print("\n当前数据库中的角色:")
        for row in result:
            print(f"  - {row[2]} ({row[0]})")

if __name__ == '__main__':
    try:
        init_roles()
        print("\n角色初始化完成!")
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)
