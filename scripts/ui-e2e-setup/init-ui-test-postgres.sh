#!/bin/bash
# =============================================================================
# ONE-DATA-STUDIO UI E2E PostgreSQL 多数据库初始化脚本
# =============================================================================
#
# 功能：创建多个 UI E2E 测试数据库并初始化表结构
# 端口：5440 (独立 UI E2E 测试端口)
#
# 使用方法：
#   docker exec -i ui-test-postgres /docker-entrypoint-initdb.d/01-init-postgres.sh
#
# =============================================================================

set -e

# 获取传入的参数
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-ui_test_ecommerce_pg}"

# 创建额外数据库的函数
create_database() {
    local db_name=$1
    echo "Creating database: $db_name"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
        CREATE DATABASE $db_name;
EOSQL
}

# 创建多个 UI E2E 测试数据库
create_database "ui_test_ecommerce_pg"
create_database "ui_test_user_mgmt_pg"
create_database "ui_test_logs_pg"

echo "UI E2E PostgreSQL databases created successfully!"
