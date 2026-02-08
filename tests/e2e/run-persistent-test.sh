#!/bin/bash
# ONE-DATA-STUDIO Persistent E2E Test Runner
# 完整的端到端测试执行脚本

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

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "========================================"
echo "ONE-DATA-STUDIO Persistent E2E Test"
echo "========================================"
echo "Project Root: $PROJECT_ROOT"
echo ""

# ========================================
# Step 1: 启动持久化测试数据库
# ========================================
log_info "Step 1: 启动持久化测试数据库..."
cd "$PROJECT_ROOT/deploy/local"

# 停止旧容器（如果存在）
docker-compose -f docker-compose.persistent-test.yml down -v 2>/dev/null || true

# 启动新容器
docker-compose -f docker-compose.persistent-test.yml up -d

log_info "等待数据库启动..."
sleep 30

# 验证容器状态
if docker ps | grep -q "persistent-test-mysql"; then
    log_success "MySQL 测试数据库已启动 (端口 3325)"
else
    log_error "MySQL 测试数据库启动失败"
    exit 1
fi

if docker ps | grep -q "persistent-test-postgres"; then
    log_success "PostgreSQL 测试数据库已启动 (端口 5450)"
else
    log_error "PostgreSQL 测试数据库启动失败"
    exit 1
fi

# ========================================
# Step 2: 生成测试数据
# ========================================
log_info "Step 2: 生成测试数据..."
cd "$PROJECT_ROOT"

# 等待数据库完全就绪
log_info "等待数据库完全就绪..."
sleep 20

# 生成 MySQL 测试数据
log_info "生成 MySQL 测试数据..."
python scripts/test_data/generate_test_data.py \
    --db mysql \
    --count 6000 \
    --persistent-test \
    --verify

# 生成 PostgreSQL 测试数据
log_info "生成 PostgreSQL 测试数据..."
python scripts/test_data/generate_test_data.py \
    --db postgres \
    --count 4000 \
    --persistent-test \
    --verify

log_success "测试数据生成完成"

# ========================================
# Step 3: 检查前端服务
# ========================================
log_info "Step 3: 检查前端服务..."
cd "$PROJECT_ROOT"

if ! curl -s http://localhost:3000 > /dev/null 2>&1; then
    log_warning "前端服务未运行"
    log_info "请先启动前端服务: cd web && npm run dev"
    read -p "是否继续测试? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "测试已取消"
        exit 0
    fi
else
    log_success "前端服务正在运行"
fi

# ========================================
# Step 4: 运行 Playwright 测试
# ========================================
log_info "Step 4: 运行 Playwright 端到端测试..."
cd "$PROJECT_ROOT"

# 确定运行模式
HEADLESS_MODE=${HEADLESS:-false}
log_info "Headless 模式: $HEADLESS_MODE"

# 运行测试
HEADLESS=$HEADLESS_MODE npx playwright test tests/e2e/persistent-full-workflow.spec.ts --project=persistent-test

# ========================================
# Step 5: 显示测试结果
# ========================================
log_info "Step 5: 测试执行完成..."
echo ""
echo "========================================"
echo "测试结果"
echo "========================================"
echo ""
echo "查看日志:"
echo "  cat test-results/logs/final-report.txt"
echo ""
echo "查看实时日志:"
echo "  cat test-results/logs/realtime-log.json"
echo ""
echo "查看截图:"
echo "  ls test-results/logs/*.png"
echo ""
echo "查看测试状态:"
echo "  cat test-results/persistent-test-state.json"
echo ""
echo "手动验证:"
echo "  1. 访问 http://localhost:3000/"
echo "  2. 数据源管理 (/data/datasources)"
echo "  3. 元数据管理 (/data/metadata)"
echo "  4. 特征管理 (/data/features)"
echo "  5. 数据标准 (/data/standards)"
echo "  6. 数据资产 (/data/assets)"
echo ""
echo "========================================"
echo "测试数据已保留，可用于手动验证"
echo "========================================"
