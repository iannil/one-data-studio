#!/bin/bash
# =============================================================================
# ONE-DATA-STUDIO E2E 测试数据生成主脚本
# =============================================================================
#
# 功能：为 Playwright E2E 测试生成完整测试数据
# 端口：MySQL 3316, PostgreSQL 5442
#
# 使用方法：
#   bash scripts/test-data/init-test-data.sh [--count 5000] [--verify]
#
# =============================================================================

set -e

# 配置
MYSQL_PORT="${MYSQL_PORT:-3316}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-testroot123}"
POSTGRES_PORT="${POSTGRES_PORT:-5442}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-testpg123}"
DATA_COUNT="${DATA_COUNT:-5000}"
VERIFY_DATA="${VERIFY_DATA:-false}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --count)
            DATA_COUNT="$2"
            shift 2
            ;;
        --verify)
            VERIFY_DATA="true"
            shift
            ;;
        --mysql-port)
            MYSQL_PORT="$2"
            shift 2
            ;;
        --postgres-port)
            POSTGRES_PORT="$2"
            shift 2
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "============================================================================"
echo "ONE-DATA-STUDIO E2E Test Data Generator"
echo "============================================================================"
log_info "MySQL Port: $MYSQL_PORT"
log_info "PostgreSQL Port: $POSTGRES_PORT"
log_info "Target Data Count: $DATA_COUNT"
log_info "Verify Data: $VERIFY_DATA"
echo "============================================================================"

# =============================================================================
# 步骤 1: 检查 Docker 容器状态
# =============================================================================

log_info "Step 1: Checking Docker containers..."

# 检查 MySQL 容器
if docker ps | grep -q "test-mysql"; then
    log_info "MySQL test container is running"
else
    log_warn "MySQL test container is not running"
    log_info "Starting MySQL test container..."
    docker-compose -f deploy/local/docker-compose.ui-test.yml up -d mysql-test
    sleep 10
fi

# 检查 PostgreSQL 容器
if docker ps | grep -q "test-postgres"; then
    log_info "PostgreSQL test container is running"
else
    log_warn "PostgreSQL test container is not running"
    log_info "Starting PostgreSQL test container..."
    docker-compose -f deploy/local/docker-compose.ui-test.yml up -d postgres-test
    sleep 10
fi

# =============================================================================
# 步骤 2: 等待数据库就绪
# =============================================================================

log_info "Step 2: Waiting for databases to be ready..."

# 等待 MySQL
while ! docker exec test-mysql mysqladmin ping -h localhost -u root -ptestroot123 --silent; do
    log_info "Waiting for MySQL to be ready..."
    sleep 2
done
log_info "MySQL is ready!"

# 等待 PostgreSQL
while ! docker exec test-postgres pg_isready -U postgres > /dev/null 2>&1; do
    log_info "Waiting for PostgreSQL to be ready..."
    sleep 2
done
log_info "PostgreSQL is ready!"

# =============================================================================
# 步骤 3: 运行 Python 数据生成器
# =============================================================================

log_info "Step 3: Generating test data using Python..."

cd /Users/iannil/Code/zproducts/one-data-studio

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 is not installed"
    exit 1
fi

# 安装依赖（如果需要）
if ! python3 -c "import pymysql" 2>/dev/null; then
    log_info "Installing pymysql..."
    pip3 install pymysql
fi

if ! python3 -c "import psycopg2" 2>/dev/null; then
    log_info "Installing psycopg2-binary..."
    pip3 install psycopg2-binary
fi

# 运行数据生成脚本
log_info "Running test data generator..."
python3 scripts/test_data/generate_test_data.py \
    --db all \
    --count "$DATA_COUNT" \
    --mysql-host localhost \
    --mysql-port "$MYSQL_PORT" \
    --mysql-user "$MYSQL_USER" \
    --mysql-password "$MYSQL_PASSWORD" \
    --postgres-host localhost \
    --postgres-port "$POSTGRES_PORT" \
    --postgres-user "$POSTGRES_USER" \
    --postgres-password "$POSTGRES_PASSWORD" \
    --verbose

# =============================================================================
# 步骤 4: 验证数据
# =============================================================================

if [ "$VERIFY_DATA" = "true" ]; then
    log_info "Step 4: Verifying generated data..."

    # MySQL 验证
    log_info "MySQL Data Summary:"
    docker exec -i test-mysql mysql -u root -ptestroot123 -e "
        SELECT 'test_ecommerce.users' AS table_name, COUNT(*) AS row_count FROM test_ecommerce.users
        UNION ALL
        SELECT 'test_ecommerce.products', COUNT(*) FROM test_ecommerce.products
        UNION ALL
        SELECT 'test_ecommerce.orders', COUNT(*) FROM test_ecommerce.orders
        UNION ALL
        SELECT 'test_ecommerce.order_items', COUNT(*) FROM test_ecommerce.order_items
        UNION ALL
        SELECT 'test_user_mgmt.employees', COUNT(*) FROM test_user_mgmt.employees
        UNION ALL
        SELECT 'test_logs.operation_logs', COUNT(*) FROM test_logs.operation_logs;
    "

    # PostgreSQL 验证
    log_info "PostgreSQL Data Summary:"
    docker exec -i test-postgres psql -U postgres -d test_ecommerce_pg -c "
        SELECT 'users' AS table_name, COUNT(*) AS row_count FROM users
        UNION ALL
        SELECT 'products', COUNT(*) FROM products
        UNION ALL
        SELECT 'orders', COUNT(*) FROM orders
        UNION ALL
        SELECT 'order_items', COUNT(*) FROM order_items;
    "
fi

# =============================================================================
# 完成
# =============================================================================

echo ""
echo "============================================================================"
log_info "Test data generation completed!"
echo "============================================================================"
log_info "MySQL (:$MYSQL_PORT):"
echo "  - Database: test_ecommerce, test_user_mgmt, test_logs"
echo "  - User: $MYSQL_USER"
echo "  - Password: $MYSQL_PASSWORD"
echo ""
log_info "PostgreSQL (:$POSTGRES_PORT):"
echo "  - Database: test_ecommerce_pg, test_user_mgmt_pg, test_logs_pg"
echo "  - User: $POSTGRES_USER"
echo "  - Password: $POSTGRES_PASSWORD"
echo "============================================================================"
log_info "You can now run the E2E tests:"
echo "  HEADLESS=false npx playwright test tests/e2e/manual-test-workflow.spec.ts --project=manual-test"
echo "============================================================================"
