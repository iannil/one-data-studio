#!/bin/bash

# DataOps 全流程 E2E 测试运行脚本
# 演示从数据接入到数据利用的完整 DataOps 流程

set -e

echo "========================================"
echo "DataOps 全流程 E2E 测试"
echo "========================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# 确保测试结果目录存在
mkdir -p test-results/dataops

# 检查 Docker 服务
echo "📋 检查 Docker 服务状态..."
if docker ps &>/dev/null; then
    echo -e "${GREEN}✓${NC} Docker 服务运行中"
else
    echo -e "${RED}✗${NC} Docker 服务未运行，请先启动 Docker"
    echo "   提示: docker-compose -f deploy/local/docker-compose.yml up -d"
    exit 1
fi

# 检查前端开发服务器
echo ""
echo "📋 检查前端开发服务器..."
if curl -s http://localhost:3000 >/dev/null; then
    echo -e "${GREEN}✓${NC} 前端服务运行中 (http://localhost:3000)"
else
    echo -e "${YELLOW}⚠${NC} 前端服务未运行，正在启动..."
    cd web && npm run dev &
    WEB_PID=$!
    cd ..
    echo "   等待前端服务启动..."
    sleep 5
fi

# 检查后端 API
echo ""
echo "📋 检查后端 API 服务..."
if curl -s http://localhost:8001/api/v1/health >/dev/null; then
    echo -e "${GREEN}✓${NC} Data API 运行中 (http://localhost:8001)"
else
    echo -e "${YELLOW}⚠${NC} Data API 未运行（测试将使用 Mock 数据）"
fi

# 运行 Playwright 测试
echo ""
echo "========================================"
echo "运行 DataOps 全流程 E2E 测试"
echo "========================================"
echo ""

# 检查 Playwright 是否安装
if ! npx playwright --version >/dev/null 2>&1; then
    echo "安装 Playwright 浏览器..."
    npx playwright install --with-deps chromium
fi

# 运行测试
echo "开始测试..."
echo ""

# 执行测试 - 使用 data-ops-full 项目
npx playwright test --project=data-ops-full full-workflow \
    --reporter=html,list \
    --output-dir=test-results/dataops \
    "$@"

# 测试结果
echo ""
echo "========================================"
echo "测试完成"
echo "========================================"
echo ""
echo "📊 查看测试报告:"
echo "   npx playwright show-report"
echo ""
echo "📸 查看测试截图:"
echo "   ls -la test-results/dataops/"
echo ""
echo "🌐 查看测试报告 (HTML):"
echo "   open test-results/dataops/index.html"
echo ""

# 清理
if [ ! -z "$WEB_PID" ]; then
    echo "停止前端开发服务器 (PID: $WEB_PID)"
    kill $WEB_PID 2>/dev/null || true
fi

echo -e "${GREEN}测试流程执行完毕${NC}"
