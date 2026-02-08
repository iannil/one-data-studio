#!/bin/bash
# =============================================================================
# ONE-DATA-STUDIO E2E PostgreSQL 多数据库初始化脚本
# =============================================================================
#
# 功能：创建多个 E2E 测试数据库并初始化表结构
# 端口：5438 (独立 E2E 测试端口)
#
# 使用方法：
#   docker exec -i e2e-postgres /docker-entrypoint-initdb.d/01-init-postgres.sh
#
# =============================================================================

set -e

# 获取传入的参数
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-e2e_ecommerce_pg}"

# 创建额外数据库的函数
create_database() {
    local db_name=$1
    echo "Creating database: $db_name"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
        CREATE DATABASE $db_name;
EOSQL
}

# 创建多个 E2E 测试数据库
create_database "e2e_ecommerce_pg"
create_database "e2e_user_mgmt_pg"
create_database "e2e_logs_pg"

echo "E2E PostgreSQL databases created successfully!"
