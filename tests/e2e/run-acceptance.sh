#!/bin/bash
# ONE-DATA-STUDIO 验收测试运行脚本
# 一键启动环境并运行完整的 E2E 测试套件

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env.test"

# 加载环境变量
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
    log_info "已加载测试环境配置: $ENV_FILE"
else
    log_warn "未找到测试环境配置文件，使用默认值"
fi

# ============================================
# 解析命令行参数
# ============================================
HEADLESS=false
UI_MODE=false
DEBUG_MODE=false
SPECIFIC_TEST=""
BROWSER="chromium"
CLEANUP=false
SKIP_SETUP=false
REPORT_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --headless)
            HEADLESS=true
            shift
            ;;
        --ui)
            UI_MODE=true
            shift
            ;;
        --debug)
            DEBUG_MODE=true
            shift
            ;;
        --test)
            SPECIFIC_TEST="$2"
            shift 2
            ;;
        --browser)
            BROWSER="$2"
            shift 2
            ;;
        --cleanup)
            CLEANUP=true
            shift
            ;;
        --skip-setup)
            SKIP_SETUP=true
            shift
            ;;
        --report)
            REPORT_ONLY=true
            shift
            ;;
        --help)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --headless      无头模式运行（不显示浏览器）"
            echo "  --ui            UI 模式运行（交互式）"
            echo "  --debug         调试模式运行"
            echo "  --test FILE     运行特定测试文件"
            echo "  --browser BROWSER 指定浏览器 (chromium|firefox|webkit)"
            echo "  --cleanup       测试后清理环境"
            echo "  --skip-setup    跳过环境启动"
            echo "  --report        仅显示报告"
            echo "  --help          显示此帮助信息"
            echo ""
            echo "示例:"
            echo "  $0 --ui              # UI 模式运行"
            echo "  $0 --test core-pages-deep.spec.ts  # 运行特定测试"
            echo "  $0 --headless        # 无头模式运行"
            exit 0
            ;;
        *)
            log_error "未知参数: $1"
            echo "使用 --help 查看帮助信息"
            exit 1
            ;;
    esac
done

# ============================================
# 仅显示报告
# ============================================
if [ "$REPORT_ONLY" = true ]; then
    log_info "打开测试报告..."
    cd "$SCRIPT_DIR"
    npx playwright show-report
    exit 0
fi

# ============================================
# 检查依赖
# ============================================
log_step "步骤 1/6: 检查依赖..."

if ! command -v node &> /dev/null; then
    log_error "Node.js 未安装，请先安装 Node.js"
    exit 1
fi
log_info "✓ Node.js 已安装: $(node --version)"

if ! command -v docker &> /dev/null; then
    log_error "Docker 未安装，请先安装 Docker"
    exit 1
fi
log_info "✓ Docker 已安装: $(docker --version | cut -d' ' -f3)"

# 检查 Playwright 浏览器
if [ ! -d "$SCRIPT_DIR/node_modules/playwright" ]; then
    log_info "安装 Playwright 浏览器..."
    cd "$SCRIPT_DIR"
    npx playwright install
fi

# ============================================
# 启动测试环境
# ============================================
if [ "$SKIP_SETUP" = false ]; then
    log_step "步骤 2/6: 启动测试环境..."

    if [ -f "$SCRIPT_DIR/setup-test-env.sh" ]; then
        bash "$SCRIPT_DIR/setup-test-env.sh"
    else
        log_warn "未找到测试环境启动脚本，跳过环境启动"
    fi
else
    log_info "跳过环境启动"
fi

# ============================================
# 等待服务就绪
# ============================================
log_step "步骤 3/6: 等待服务就绪..."

check_service() {
    local url=$1
    local name=$2
    local max_wait=${3:-60}
    local count=0

    while [ $count -lt $max_wait ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            log_info "✓ $name 已就绪"
            return 0
        fi
        count=$((count + 1))
        sleep 2
    done

    log_warn "$name 未在 $max_wait_wait 秒内就绪"
    return 1
}

check_service "http://localhost:${AGENT_API_PORT:-8000}/api/v1/health" "Agent API" 60
check_service "http://localhost:${DATA_API_PORT:-8001}/api/v1/health" "Data API" 60
check_service "http://localhost:${MODEL_API_PORT:-8002}/api/v1/health" "Model API" 60
check_service "http://localhost:${KEYCLOAK_PORT:-8080}/health/ready" "Keycloak" 120

# ============================================
# 初始化测试数据
# ============================================
log_step "步骤 4/6: 初始化测试数据..."

if [ -f "$SCRIPT_DIR/setup/seed-data.py" ]; then
    if command -v python3 &> /dev/null; then
        python3 "$SCRIPT_DIR/setup/seed-data.py" || log_warn "测试数据初始化失败"
    else
        log_warn "Python3 未安装，跳过测试数据初始化"
    fi
else
    log_info "未找到测试数据初始化脚本"
fi

# ============================================
# 运行测试
# ============================================
log_step "步骤 5/6: 运行 Playwright 测试..."
log_info ""

cd "$SCRIPT_DIR"

# 构建测试命令
TEST_CMD="npx playwright test"

# 添加浏览器选项
if [ -n "$BROWSER" ]; then
    TEST_CMD="$TEST_CMD --project=$BROWSER-acceptance"
fi

# 添加有头模式选项
if [ "$HEADLESS" = true ]; then
    TEST_CMD="$TEST_CMD --headed=false"
else
    TEST_CMD="$TEST_CMD --headed=true"
fi

# 添加特定测试
if [ -n "$SPECIFIC_TEST" ]; then
    TEST_CMD="$TEST_CMD $SPECIFIC_TEST"
fi

# UI 模式
if [ "$UI_MODE" = true ]; then
    TEST_CMD="npx playwright test --ui"
fi

# 调试模式
if [ "$DEBUG_MODE" = true ]; then
    TEST_CMD="npx playwright test --debug"
fi

# 设置环境变量
export HEADED=$([ "$HEADLESS" = false ] && echo "true" || echo "false")
export BASE_URL="http://localhost:${WEB_PORT:-3000}"
export AGENT_API_URL="http://localhost:${AGENT_API_PORT:-8000}"
export DATA_API_URL="http://localhost:${DATA_API_PORT:-8001}"
export MODEL_API_URL="http://localhost:${MODEL_API_PORT:-8002}"
export OPENAI_API_URL="http://localhost:${OPENAI_PROXY_PORT:-8003}"
export KEYCLOAK_URL="http://localhost:${KEYCLOAK_PORT:-8080}"

# 执行测试
log_info "执行命令: $TEST_CMD"
eval $TEST_CMD
TEST_EXIT_CODE=$?

log_info ""

# ============================================
# 生成报告
# ============================================
log_step "步骤 6/6: 生成测试报告..."

# 合并 JSON 报告（如果需要）
if [ -f "test-results/results.json" ]; then
    log_info "✓ JSON 报告已生成: test-results/results.json"
fi

if [ -f "test-results/junit.xml" ]; then
    log_info "✓ JUnit 报告已生成: test-results/junit.xml"
fi

# HTML 报告
log_info "✓ HTML 报告已生成: playwright-report/index.html"

# ============================================
# 测试结果摘要
# ============================================
log_info ""
log_info "======================================"
log_info "测试执行完成"
log_info "======================================"

if [ $TEST_EXIT_CODE -eq 0 ]; then
    log_info "✓ 所有测试通过"
else
    log_warn "✗ 有测试失败 (退出码: $TEST_EXIT_CODE)"
fi

log_info ""
log_info "查看报告:"
log_info "  npm run test:report"
log_info "  或 $0 --report"
log_info ""

# ============================================
# 清理环境（可选）
# ============================================
if [ "$CLEANUP" = true ]; then
    log_info "清理测试环境..."
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
    docker compose -f "$PROJECT_ROOT/deploy/local/docker-compose.yml" -p onedata-test down -v
    log_info "✓ 测试环境已清理"
fi

exit $TEST_EXIT_CODE
