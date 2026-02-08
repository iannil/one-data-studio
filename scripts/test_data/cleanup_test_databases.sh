#!/bin/bash
# 清理现有测试数据库的数据
# 用途：在运行新的持久化测试前清理现有测试数据

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "========================================"
echo "清理现有测试数据库"
echo "========================================"

# 清理 MySQL 端口 3316 (Manual Test)
if docker ps | grep -q "manual-test-mysql"; then
    log_info "清理 MySQL (端口 3316)..."
    docker exec -i manual-test-mysql mysql -uroot -ptestroot123 <<EOF
DROP DATABASE IF EXISTS test_ecommerce;
DROP DATABASE IF EXISTS test_user_mgmt;
DROP DATABASE IF EXISTS test_logs;
CREATE DATABASE test_ecommerce CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE test_user_mgmt CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE test_logs CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EOF
    log_success "MySQL (端口 3316) 清理完成"
else
    log_warning "manual-test-mysql 容器未运行，跳过"
fi

# 清理 PostgreSQL 端口 5442 (Manual Test)
if docker ps | grep -q "manual-test-postgres"; then
    log_info "清理 PostgreSQL (端口 5442)..."
    docker exec -i manual-test-postgres psql -U postgres -d postgres <<EOF
DROP DATABASE IF EXISTS test_ecommerce_pg;
DROP DATABASE IF EXISTS test_user_mgmt_pg;
CREATE DATABASE test_ecommerce_pg;
CREATE DATABASE test_user_mgmt_pg;
EOF
    log_success "PostgreSQL (端口 5442) 清理完成"
else
    log_warning "manual-test-postgres 容器未运行，跳过"
fi

# 清理 MySQL 端口 3310 (E2E Test)
if docker ps | grep -q "e2e-mysql"; then
    log_info "清理 MySQL (端口 3310)..."
    docker exec -i e2e-mysql mysql -uroot -pe2eroot123 <<EOF
DROP DATABASE IF EXISTS e2e_ecommerce;
DROP DATABASE IF EXISTS e2e_user_mgmt;
DROP DATABASE IF EXISTS e2e_logs;
CREATE DATABASE e2e_ecommerce CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE e2e_user_mgmt CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE e2e_logs CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EOF
    log_success "MySQL (端口 3310) 清理完成"
else
    log_warning "e2e-mysql 容器未运行，跳过"
fi

# 清理 PostgreSQL 端口 5438 (E2E Test)
if docker ps | grep -q "e2e-postgres"; then
    log_info "清理 PostgreSQL (端口 5438)..."
    docker exec -i e2e-postgres psql -U postgres -d postgres <<EOF
DROP DATABASE IF EXISTS e2e_ecommerce_pg;
DROP DATABASE IF EXISTS e2e_user_mgmt_pg;
CREATE DATABASE e2e_ecommerce_pg;
CREATE DATABASE e2e_user_mgmt_pg;
EOF
    log_success "PostgreSQL (端口 5438) 清理完成"
else
    log_warning "e2e-postgres 容器未运行，跳过"
fi

echo "========================================"
log_success "清理完成！"
echo "========================================"
