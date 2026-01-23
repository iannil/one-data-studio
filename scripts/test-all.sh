#!/bin/bash
# test-all.sh - 运行所有集成测试

set -e

ALDATA_URL="${ALDATA_URL:-http://localhost:8080}"
CUBE_URL="${CUBE_URL:-http://localhost:8000}"
BISHENG_URL="${BISHENG_URL:-http://localhost:8081}"

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

test_name() {
    echo -e "\n${YELLOW}测试: $1${NC}"
}

test_pass() {
    echo -e "${GREEN}✓ 通过${NC}: $1"
    ((PASSED++))
}

test_fail() {
    echo -e "${RED}✗ 失败${NC}: $1"
    ((FAILED++))
}

# ============================================
# 测试 1: 健康检查
# ============================================
test_section "健康检查"

test_name "Alldata API 健康检查"
if curl -sf "${ALDATA_URL}/api/v1/health" | grep -q "healthy"; then
    test_pass "Alldata API"
else
    test_fail "Alldata API"
fi

test_name "Cube 模型服务健康检查"
if curl -sf "${CUBE_URL}/v1/models" | grep -q "object"; then
    test_pass "Cube API"
else
    test_fail "Cube API"
fi

test_name "Bisheng API 健康检查"
if curl -sf "${BISHENG_URL}/api/v1/health" | grep -q "healthy"; then
    test_pass "Bisheng API"
else
    test_fail "Bisheng API"
fi

# ============================================
# 测试 2: Alldata 数据集 API
# ============================================
test_section "Alldata 数据集 API"

test_name "获取数据集列表"
DS_LIST=$(curl -sf "${ALDATA_URL}/api/v1/datasets")
if echo "$DS_LIST" | jq -e '.code == 0' > /dev/null; then
    test_pass "数据集列表"
else
    test_fail "数据集列表"
fi

test_name "创建新数据集"
CREATE_RESULT=$(curl -sf -X POST "${ALDATA_URL}/api/v1/datasets" \
    -H "Content-Type: application/json" \
    -d '{"name":"test_dataset","storage_path":"s3://test/","format":"csv"}')
if echo "$CREATE_RESULT" | jq -e '.code == 0' > /dev/null; then
    DS_ID=$(echo "$CREATE_RESULT" | jq -r '.data.dataset_id')
    test_pass "创建数据集 ($DS_ID)"
else
    test_fail "创建数据集"
    DS_ID=""
fi

if [ -n "$DS_ID" ]; then
    test_name "获取数据集详情"
    DS_DETAIL=$(curl -sf "${ALDATA_URL}/api/v1/datasets/${DS_ID}")
    if echo "$DS_DETAIL" | jq -e '.code == 0' > /dev/null; then
        test_pass "获取数据集详情"
    else
        test_fail "获取数据集详情"
    fi

    test_name "删除数据集"
    DELETE_RESULT=$(curl -sf -X DELETE "${ALDATA_URL}/api/v1/datasets/${DS_ID}")
    if echo "$DELETE_RESULT" | jq -e '.code == 0' > /dev/null; then
        test_pass "删除数据集"
    else
        test_fail "删除数据集"
    fi
fi

# ============================================
# 测试 3: Cube 模型服务
# ============================================
test_section "Cube 模型服务"

test_name "列出可用模型"
MODELS=$(curl -sf "${CUBE_URL}/v1/models")
if echo "$MODELS" | jq -e '.object == "list"' > /dev/null; then
    MODEL_ID=$(echo "$MODELS" | jq -r '.data[0].id')
    test_pass "列出模型 ($MODEL_ID)"
else
    test_fail "列出模型"
    MODEL_ID=""
fi

if [ -n "$MODEL_ID" ]; then
    test_name "聊天补全"
    CHAT_RESULT=$(curl -sf -X POST "${CUBE_URL}/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -d "{\"model\":\"$MODEL_ID\",\"messages\":[{\"role\":\"user\",\"content\":\"1+1=\"}],\"max_tokens\":10}")
    if echo "$CHAT_RESULT" | jq -e '.choices[0].message.content' > /dev/null; then
        test_pass "聊天补全"
    else
        test_fail "聊天补全"
    fi
fi

# ============================================
# 测试 4: Bisheng 应用层
# ============================================
test_section "Bisheng 应用层"

test_name "Bisheng 调用 Cube 模型"
BISHENG_CHAT=$(curl -sf -X POST "${BISHENG_URL}/api/v1/chat" \
    -H "Content-Type: application/json" \
    -d '{"message":"测试"}')
if echo "$BISHENG_CHAT" | jq -e '.code == 0' > /dev/null; then
    test_pass "Bisheng 调用模型"
else
    test_fail "Bisheng 调用模型"
fi

test_name "Bisheng 查询 Alldata 数据集"
BISHENG_DS=$(curl -sf "${BISHENG_URL}/api/v1/datasets")
if echo "$BISHENG_DS" | jq -e '.code == 0' > /dev/null; then
    test_pass "Bisheng 查询数据集"
else
    test_fail "Bisheng 查询数据集"
fi

test_name "RAG 查询"
RAG_RESULT=$(curl -sf -X POST "${BISHENG_URL}/api/v1/rag/query" \
    -H "Content-Type: application/json" \
    -d '{"question":"什么是 ONE-DATA-STUDIO?"}')
if echo "$RAG_RESULT" | jq -e '.code == 0' > /dev/null; then
    test_pass "RAG 查询"
else
    test_fail "RAG 查询"
fi

# ============================================
# 测试结果
# ============================================
echo ""
echo "================================"
echo "测试结果"
echo "================================"
echo -e "通过: ${GREEN}${PASSED}${NC}"
echo -e "失败: ${RED}${FAILED}${NC}"
echo "总计: $((PASSED + FAILED))"
echo "================================"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}所有测试通过！${NC}"
    exit 0
else
    echo -e "\n${RED}有测试失败！${NC}"
    exit 1
fi
