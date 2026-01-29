#!/bin/bash
# ONE-DATA-STUDIO 端到端测试脚本
# 测试完整的用户场景流程

set -e

echo "==> ONE-DATA-STUDIO 端到端测试脚本"
echo ""

# 默认端口配置
AGENT_API_URL="${AGENT_API_URL:-http://localhost:8000}"
DATA_API_URL="${DATA_API_URL:-http://localhost:8001}"
MODEL_API_URL="${MODEL_API_URL:-http://localhost:8002}"
# 兼容旧名称
BISHENG_API_URL="${BISHENG_API_URL:-${AGENT_API_URL}}"
ALLDATA_API_URL="${ALLDATA_API_URL:-${DATA_API_URL}}"
CUBE_API_URL="${CUBE_API_URL:-${MODEL_API_URL}}"

# 测试计数器
PASSED=0
FAILED=0
SKIPPED=0

# 彩色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() {
    echo -e "${GREEN}通过${NC}"
    ((PASSED++))
}

fail() {
    echo -e "${RED}失败${NC}: $1"
    ((FAILED++))
}

skip() {
    echo -e "${YELLOW}跳过${NC}: $1"
    ((SKIPPED++))
}

# 检查服务是否可用
echo "==> 检查服务状态..."
for service in "Agent:${AGENT_API_URL}/health" "Data:${DATA_API_URL}/health" "Model:${MODEL_API_URL}/api/v1/health"; do
    name="${service%%:*}"
    url="${service#*:}"
    echo -n "  ${name} API... "
    if curl -s -f "${url}" > /dev/null 2>&1; then
        pass
    else
        fail "服务不可用"
    fi
done
echo ""

# E2E 场景 1: 创建并执行工作流
echo "==> E2E 场景 1: 工作流生命周期"
echo -n "  1.1 创建工作流... "
workflow_response=$(curl -s -X POST "${AGENT_API_URL}/api/v1/workflows" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "E2E Test Workflow",
        "description": "端到端测试工作流",
        "nodes": [],
        "edges": []
    }' 2>/dev/null || echo '{"error": true}')

if echo "${workflow_response}" | grep -q '"id"'; then
    workflow_id=$(echo "${workflow_response}" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
    pass
    echo "      工作流 ID: ${workflow_id}"
else
    fail "无法创建工作流"
    workflow_id=""
fi

if [ -n "${workflow_id}" ]; then
    echo -n "  1.2 获取工作流详情... "
    if curl -s -f "${AGENT_API_URL}/api/v1/workflows/${workflow_id}" > /dev/null 2>&1; then
        pass
    else
        fail "无法获取工作流"
    fi

    echo -n "  1.3 删除工作流... "
    if curl -s -X DELETE "${AGENT_API_URL}/api/v1/workflows/${workflow_id}" > /dev/null 2>&1; then
        pass
    else
        fail "无法删除工作流"
    fi
fi
echo ""

# E2E 场景 2: 聊天对话
echo "==> E2E 场景 2: 聊天对话流程"
echo -n "  2.1 发送聊天消息... "
chat_response=$(curl -s -X POST "${AGENT_API_URL}/api/v1/chat" \
    -H "Content-Type: application/json" \
    -d '{"message": "你好，请介绍一下你自己"}' 2>/dev/null || echo '{"error": true}')

if echo "${chat_response}" | grep -qE '"(response|message|content)"'; then
    pass
else
    fail "聊天响应无效"
fi

echo -n "  2.2 获取会话列表... "
if curl -s -f "${BISHENG_API_URL}/api/v1/conversations" > /dev/null 2>&1; then
    pass
else
    fail "无法获取会话列表"
fi
echo ""

# E2E 场景 3: 元数据查询
echo "==> E2E 场景 3: 元数据操作"
echo -n "  3.1 获取数据库列表... "
if curl -s -f "${ALLDATA_API_URL}/api/v1/metadata/databases" > /dev/null 2>&1; then
    pass
else
    fail "无法获取数据库列表"
fi

echo -n "  3.2 获取数据集列表... "
if curl -s -f "${ALLDATA_API_URL}/api/v1/datasets" > /dev/null 2>&1; then
    pass
else
    fail "无法获取数据集列表"
fi
echo ""

# E2E 场景 4: 模型服务
echo "==> E2E 场景 4: 模型服务"
echo -n "  4.1 获取可用模型列表... "
if curl -s -f "${CUBE_API_URL}/api/v1/models" > /dev/null 2>&1; then
    pass
else
    skip "模型服务可能未配置"
fi
echo ""

# 测试结果汇总
echo "==> 端到端测试结果"
echo "  通过: ${PASSED}"
echo "  失败: ${FAILED}"
echo "  跳过: ${SKIPPED}"
echo ""

if [ "${FAILED}" -gt 0 ]; then
    echo -e "${RED}==> 端到端测试未全部通过${NC}"
    exit 1
else
    echo -e "${GREEN}==> 端到端测试通过!${NC}"
    exit 0
fi
