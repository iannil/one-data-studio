#!/bin/bash
# ONE-DATA-STUDIO 测试执行脚本
# 支持运行不同类型和级别的测试

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 显示帮助信息
show_help() {
    cat << EOF
ONE-DATA-STUDIO 测试执行脚本

用法: ./run_tests.sh [选项]

选项:
    -t, --type TYPE          测试类型: unit(单元), integration(集成), e2e(端到端), all(所有)
    -l, --level LEVEL        测试级别: p0(P0), p1(P1), p2(P2), all(所有)
    -m, --module MODULE      指定测试模块
    -k, --keyword KEYWORD    运行匹配关键字的测试
    -c, --coverage          生成覆盖率报告
    -r, --report            生成 HTML 测试报告
    -v, --verbose           详细输出
    -h, --help             显示帮助信息

示例:
    ./run_tests.sh -t unit -l p0                    # 运行所有P0单元测试
    ./run_tests.sh -m test_data_administrator       # 运行数据管理员测试
    ./run_tests.sh -k "敏感数据"                   # 运行包含"敏感数据"的测试
    ./run_tests.sh -t all -c -r                    # 运行所有测试并生成报告

按角色运行测试:
    ./run_tests.sh --role data_administrator       # 数据管理员
    ./run_tests.sh --role data_engineer           # 数据工程师
    ./run_tests.sh --role ai_engineer              # 算法工程师
    ./run_tests.sh --role business_user           # 业务用户
    ./run_tests.sh --role system_admin             # 系统管理员
EOF
}

# 默认参数
TEST_TYPE="all"
TEST_LEVEL="all"
TEST_MODULE=""
KEYWORD=""
COVERAGE=0
REPORT=0
VERBOSE=0
ROLE=""

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -l|--level)
            TEST_LEVEL="$2"
            shift 2
            ;;
        -m|--module)
            TEST_MODULE="$2"
            shift 2
            ;;
        -k|--keyword)
            KEYWORD="$2"
            shift 2
            ;;
        -c|--coverage)
            COVERAGE=1
            shift
            ;;
        -r|--report)
            REPORT=1
            shift
            ;;
        -v|--verbose)
            VERBOSE=1
            shift
            ;;
        --role)
            ROLE="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

# 基础 pytest 命令
PYTEST_CMD="pytest"

# 添加详细输出
if [ $VERBOSE -eq 1 ]; then
    PYTEST_CMD="$PYTEST_CMD -v -s"
fi

# 添加覆盖率
if [ $COVERAGE -eq 1 ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=services --cov=shared --cov-report=html --cov-report=term"
fi

# 添加 HTML 报告
if [ $REPORT -eq 1 ]; then
    mkdir -p reports/html
    PYTEST_CMD="$PYTEST_CMD --html=reports/html/index.html --self-contained-html"
fi

# 根据测试类型设置路径
case $TEST_TYPE in
    unit)
        TEST_PATH="tests/unit"
        ;;
    integration)
        TEST_PATH="tests/integration"
        PYTEST_CMD="$PYTEST_CMD -m integration"
        ;;
    e2e)
        TEST_PATH="tests/e2e"
        PYTEST_CMD="npx playwright test"
        ;;
    all)
        TEST_PATH="tests"
        ;;
esac

# 根据角色设置路径
if [ -n "$ROLE" ]; then
    case $ROLE in
        data_administrator)
            TEST_PATH="tests/unit/test_data_administrator"
            ;;
        data_engineer)
            TEST_PATH="tests/unit/test_data_engineer"
            ;;
        ai_engineer)
            TEST_PATH="tests/unit/test_ai_engineer"
            ;;
        business_user)
            TEST_PATH="tests/unit/test_business_user"
            ;;
        system_admin)
            TEST_PATH="tests/unit/test_system_admin"
            ;;
    esac
fi

# 根据级别设置标记
if [ "$TEST_LEVEL" != "all" ]; then
    PYTEST_CMD="$PYTEST_CMD -m $TEST_LEVEL"
fi

# 添加模块限定
if [ -n "$TEST_MODULE" ]; then
    PYTEST_CMD="$PYTEST_CMD tests/unit/$TEST_MODULE"
fi

# 添加关键字
if [ -n "$KEYWORD" ]; then
    PYTEST_CMD="$PYTEST_CMD -k $KEYWORD"
fi

# 显示执行信息
print_info "执行测试..."
echo "  测试类型: $TEST_TYPE"
echo "  测试级别: $TEST_LEVEL"
echo "  测试路径: $TEST_PATH"
echo "  覆盖率: $([ $COVERAGE -eq 1 ] && echo '是' || echo '否')"
echo "  HTML报告: $([ $REPORT -eq 1 ] && echo '是' || echo '否')"

# 创建报告目录
mkdir -p reports/html reports/coverage

# 执行测试
echo ""
print_info "运行命令: $PYTEST_CMD $TEST_PATH"
echo ""

eval "$PYTEST_CMD $TEST_PATH"
EXIT_CODE=$?

# 显示结果
echo ""
if [ $EXIT_CODE -eq 0 ]; then
    print_info "测试执行成功 ✓"
    if [ $REPORT -eq 1 ]; then
        echo "  HTML报告: file://$(pwd)/reports/html/index.html"
    fi
    if [ $COVERAGE -eq 1 ]; then
        echo "  覆盖率报告: file://$(pwd)/htmlcov/index.html"
    fi
else
    print_error "测试执行失败 ✗"
fi

exit $EXIT_CODE
