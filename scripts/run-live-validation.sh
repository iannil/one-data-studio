#!/bin/bash
# DataOps 真实 API 验证测试运行脚本
# 非 headless 模式运行，连接真实后端 API

set -e

# 脚本所在目录的父目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    cat << EOF
DataOps 真实 API 验证测试运行脚本

用法: $0 [选项]

选项:
    -h, --help          显示此帮助信息
    -d, --debug         调试模式（打开 Playwright Inspector）
    -H, --headless      使用 headless 模式（默认为非 headless）
    -u, --update        更新 Playwright 浏览器
    -p, --project       指定项目名称（默认: data-ops-live）
    -t, --test          运行单个测试文件
    -b, --base-url      指定基础 URL（默认: http://localhost:3000）

示例:
    $0                              # 默认模式运行（非 headless）
    $0 -H                           # Headless 模式运行
    $0 -d                           # 调试模式
    $0 -t "data-ops-live-validation.spec.ts"  # 运行单个测试
    $0 -b "https://staging.example.com"       # 使用指定环境

EOF
}

# 默认参数
HEADLESS=false
DEBUG=false
UPDATE_BROWSERS=false
PROJECT="data-ops-live"
TEST_FILE=""
BASE_URL=""

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -d|--debug)
            DEBUG=true
            shift
            ;;
        -H|--headless)
            HEADLESS=true
            shift
            ;;
        -u|--update)
            UPDATE_BROWSERS=true
            shift
            ;;
        -p|--project)
            PROJECT="$2"
            shift 2
            ;;
        -t|--test)
            TEST_FILE="$2"
            shift 2
            ;;
        -b|--base-url)
            BASE_URL="$2"
            shift 2
            ;;
        *)
            print_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 打印配置信息
print_info "DataOps 真实 API 验证测试"
echo ""
print_info "配置:"
echo "  项目: $PROJECT"
echo "  Headless: $HEADLESS"
echo "  调试模式: $DEBUG"
if [ -n "$BASE_URL" ]; then
    echo "  基础 URL: $BASE_URL"
fi
if [ -n "$TEST_FILE" ]; then
    echo "  测试文件: $TEST_FILE"
fi
echo ""

# 更新浏览器
if [ "$UPDATE_BROWSERS" = true ]; then
    print_info "更新 Playwright 浏览器..."
    npx playwright install --with-deps
    print_success "浏览器更新完成"
    echo ""
fi

# 构建命令
CMD="npx playwright test"

# 添加项目参数
CMD="$CMD --project=$PROJECT"

# 添加 headless 参数
if [ "$HEADLESS" = true ]; then
    CMD="$CMD --headed=false"
else
    CMD="$CMD --headed=false"
    export HEADLESS="false"
fi

# 添加调试参数
if [ "$DEBUG" = true ]; then
    CMD="$CMD --debug"
fi

# 添加测试文件参数
if [ -n "$TEST_FILE" ]; then
    CMD="$CMD $TEST_FILE"
fi

# 添加 base URL 参数
if [ -n "$BASE_URL" ]; then
    CMD="$CMD --base-url=$BASE_URL"
fi

# 检查后端是否运行
if [ -z "$BASE_URL" ]; then
    print_info "检查后端服务..."
    if ! curl -s http://localhost:3000 > /dev/null 2>&1; then
        print_warning "前端服务 (http://localhost:3000) 似乎未运行"
        print_info "请确保前端服务已启动: cd web && npm run dev"
    fi
    if ! curl -s http://localhost:5001 > /dev/null 2>&1; then
        print_warning "后端服务 (http://localhost:5001) 似乎未运行"
        print_info "请确保后端服务已启动: docker-compose -f deploy/local/docker-compose.yml up -d"
    fi
    echo ""
fi

# 创建截图目录
mkdir -p test-results/screenshots/live

# 运行测试
print_info "运行测试..."
echo ""

# 运行命令并捕获退出代码
if eval "$CMD"; then
    echo ""
    print_success "测试完成！"
    echo ""
    print_info "报告文件位置:"
    echo "  HTML 报告: playwright-report/index.html"
    echo "  JSON 报告: test-results.json"
    echo "  截图目录: test-results/screenshots/live/"
    exit 0
else
    EXIT_CODE=$?
    echo ""
    print_error "测试失败，退出代码: $EXIT_CODE"
    echo ""
    print_info "查看详细报告:"
    echo "  npx playwright show-report"
    exit $EXIT_CODE
fi
