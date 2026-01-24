#!/bin/bash
# ONE-DATA-STUDIO 完整集成测试脚本
# 运行所有 API 和集成测试

set -e

echo "==> ONE-DATA-STUDIO 完整测试脚本"
echo ""

# 默认端口配置 (与 docker-compose.yml 一致)
BISHENG_API_URL="${BISHENG_API_URL:-http://localhost:8000}"
ALLDATA_API_URL="${ALLDATA_API_URL:-http://localhost:8001}"
CUBE_API_URL="${CUBE_API_URL:-http://localhost:8002}"
OPENAI_PROXY_URL="${OPENAI_PROXY_URL:-http://localhost:8003}"

# 测试计数器
PASSED=0
FAILED=0

# 测试函数
test_endpoint() {
    local name="$1"
    local url="$2"
    local expected_status="${3:-200}"

    echo -n "  测试 ${name}... "

    status=$(curl -s -o /dev/null -w "%{http_code}" "${url}" 2>/dev/null || echo "000")

    if [ "${status}" = "${expected_status}" ]; then
        echo "通过 (${status})"
        ((PASSED++))
        return 0
    else
        echo "失败 (期望 ${expected_status}, 实际 ${status})"
        ((FAILED++))
        return 1
    fi
}

# 1. 健康检查测试
echo "==> 1. 健康检查测试"
test_endpoint "Bisheng API 健康检查" "${BISHENG_API_URL}/health"
test_endpoint "Alldata API 健康检查" "${ALLDATA_API_URL}/health"
test_endpoint "Cube API 健康检查" "${CUBE_API_URL}/api/v1/health"
test_endpoint "OpenAI Proxy 健康检查" "${OPENAI_PROXY_URL}/health"
echo ""

# 2. API 端点测试
echo "==> 2. API 端点测试"
test_endpoint "Bisheng 工作流列表" "${BISHENG_API_URL}/api/v1/workflows"
test_endpoint "Bisheng 会话列表" "${BISHENG_API_URL}/api/v1/conversations"
test_endpoint "Alldata 元数据列表" "${ALLDATA_API_URL}/api/v1/metadata/databases"
test_endpoint "Alldata 数据集列表" "${ALLDATA_API_URL}/api/v1/datasets"
echo ""

# 3. 聊天功能测试
echo "==> 3. 聊天功能测试"
echo -n "  测试简单聊天... "
response=$(curl -s -X POST "${BISHENG_API_URL}/api/v1/chat" \
    -H "Content-Type: application/json" \
    -d '{"message": "你好"}' 2>/dev/null || echo '{"error": true}')

if echo "${response}" | grep -q '"error"'; then
    echo "失败"
    ((FAILED++))
else
    echo "通过"
    ((PASSED++))
fi
echo ""

# 4. 运行 pytest 测试 (如果存在)
echo "==> 4. 运行 pytest 测试"
if [ -d "tests" ]; then
    echo "  运行单元测试..."
    if python -m pytest tests/unit/ -v --tb=short 2>/dev/null; then
        echo "  单元测试通过"
        ((PASSED++))
    else
        echo "  单元测试失败"
        ((FAILED++))
    fi

    echo "  运行集成测试..."
    if python -m pytest tests/integration/ -v --tb=short 2>/dev/null; then
        echo "  集成测试通过"
        ((PASSED++))
    else
        echo "  集成测试失败"
        ((FAILED++))
    fi
else
    echo "  跳过 (tests 目录不存在)"
fi
echo ""

# 5. 测试结果汇总
echo "==> 测试结果汇总"
echo "  通过: ${PASSED}"
echo "  失败: ${FAILED}"
echo ""

if [ "${FAILED}" -gt 0 ]; then
    echo "==> 测试未全部通过"
    exit 1
else
    echo "==> 所有测试通过!"
    exit 0
fi
