#!/bin/bash
#
# 用户生命周期测试 - 测试运行脚本
# 用于运行用户生命周期测试套件
#

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
PROJECT="${PROJECT:-user-lifecycle}"
REPORTER="${REPORTER:-list}"
WORKERS="${WORKERS:-4}"

# 解析参数
while [[ $# -gt 0 ]]; do
  case $1 in
    -p|--project)
      PROJECT="$2"
      shift 2
      ;;
    -r|--reporter)
      REPORTER="$2"
      shift 2
      ;;
    -w|--workers)
      WORKERS="$2"
      shift 2
      ;;
    -h|--help)
      echo "用户生命周期测试运行脚本"
      echo ""
      echo "用法: $0 [选项]"
      echo ""
      echo "选项:"
      echo "  -p, --project PROJECT   测试项目 (default: user-lifecycle)"
      echo "                           可选: user-lifecycle, user-lifecycle-fast"
      echo "  -r, --reporter REPORTER  报告器 (default: list)"
      echo "                           可选: list, html, json, junit"
      echo "  -w, --workers WORKERS    并发数 (default: 4)"
      echo "  -h, --help              显示帮助信息"
      echo ""
      echo "示例:"
      echo "  $0                      # 运行默认测试"
      echo "  $0 -p user-lifecycle-fast  # 运行快速测试"
      echo "  $0 -r html              # 生成 HTML 报告"
      exit 0
      ;;
    *)
      echo -e "${RED}未知选项: $1${NC}"
      echo "使用 -h 查看帮助信息"
      exit 1
      ;;
  esac
done

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}用户生命周期测试${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "项目: $PROJECT"
echo "报告器: $REPORTER"
echo "并发数: $WORKERS"
echo ""

# 检查环境变量
if [ -z "$BASE_URL" ]; then
  echo -e "${YELLOW}警告: BASE_URL 未设置，使用默认值 http://localhost:3000${NC}"
  export BASE_URL="http://localhost:3000"
fi

if [ -z "$agent_API_URL" ]; then
  echo -e "${YELLOW}警告: agent_API_URL 未设置${NC}"
fi

echo "BASE_URL: $BASE_URL"
echo ""

# 检查依赖
echo -e "${YELLOW}检查依赖...${NC}"
if ! command -v npx &> /dev/null; then
  echo -e "${RED}错误: 未找到 npx${NC}"
  echo "请安装 Node.js 和 npm"
  exit 1
fi

if ! npx playwright --version &> /dev/null; then
  echo -e "${YELLOW}安装 Playwright...${NC}"
  npx playwright install
fi
echo -e "${GREEN}依赖检查完成${NC}"
echo ""

# 运行测试
echo -e "${GREEN}开始运行测试...${NC}"
echo ""

START_TIME=$(date +%s)

npx playwright test \
  --project="$PROJECT" \
  --reporter="$REPORTER" \
  --workers="$WORKERS"

EXIT_CODE=$?

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo -e "${BLUE}========================================${NC}"

if [ $EXIT_CODE -eq 0 ]; then
  echo -e "${GREEN}测试完成！${NC}"
else
  echo -e "${RED}测试失败，退出码: $EXIT_CODE${NC}"
fi

echo "耗时: ${DURATION}秒"
echo -e "${BLUE}========================================${NC}"

# 如果是 HTML 报告，自动打开
if [ "$REPORTER" = "html" ]; then
  echo ""
  echo -e "${YELLOW}打开测试报告...${NC}"
  npx playwright show-report
fi

exit $EXIT_CODE
