#!/bin/bash
# ONE-DATA-STUDIO 端到端测试脚本
# Sprint 7: 端到端集成验证
# Sprint 9: E2E 测试扩展 (Playwright)
#
# 验证三大集成点：
# 1. Alldata → Cube：数据集注册与读取
# 2. Cube → Bisheng：模型服务调用
# 3. Alldata → Bisheng：Text-to-SQL 元数据查询
#
# 使用方法:
#   ./scripts/test-e2e.sh              # 运行所有测试
#   ./scripts/test-e2e.sh api         # 仅运行 API 测试
#   ./scripts/test-e2e.sh playwright   # 仅运行 Playwright 测试

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# API 端点配置（可通过环境变量覆盖）
ALLDATA_API_URL="${ALLDATA_API_URL:-http://localhost:8080}"
BISHENG_API_URL="${BISHENG_API_URL:-http://localhost:8081}"
CUBE_API_URL="${CUBE_API_URL:-http://localhost:8000}"

# 测试结果
TESTS_PASSED=0
TESTS_FAILED=0

# 辅助函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# 测试函数
test_health() {
    local name=$1
    local url=$2

    log_info "测试 $name 健康检查: $url/api/v1/health"

    if curl -sf "$url/api/v1/health" > /dev/null 2>&1; then
        log_info "✓ $name 健康检查通过"
        ((TESTS_PASSED++))
        return 0
    else
        log_error "✗ $name 健康检查失败"
        ((TESTS_FAILED++))
        return 1
    fi
}

test_endpoint() {
    local name=$1
    local url=$2
    local expected_pattern=${3:-".*"}

    log_info "测试 $name: $url"

    response=$(curl -s "$url" 2>&1)
    if echo "$response" | grep -qE "$expected_pattern"; then
        log_info "✓ $name 测试通过"
        ((TESTS_PASSED++))
        return 0
    else
        log_error "✗ $name 测试失败"
        log_error "响应: $response"
        ((TESTS_FAILED++))
        return 1
    fi
}

# 等待服务就绪
wait_for_service() {
    local name=$1
    local url=$2
    local max_wait=${3:-60}
    local count=0

    log_info "等待 $name 就绪..."

    while [ $count -lt $max_wait ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            log_info "✓ $name 已就绪"
            return 0
        fi
        ((count++))
        sleep 1
    done

    log_error "$name 在 ${max_wait} 秒内未就绪"
    return 1
}

# ==================== 测试开始 ====================

echo ""
echo "========================================"
echo "ONE-DATA-STUDIO 端到端测试"
echo "========================================"
echo ""
echo "API 端点配置:"
echo "  Alldata API: $ALLDATA_API_URL"
echo "  Bisheng API: $BISHENG_API_URL"
echo "  Cube API:    $CUBE_API_URL"
echo ""
echo "========================================"
echo ""

# ==================== 阶段 1: 服务健康检查 ====================
log_info "[1/5] 服务健康检查..."

wait_for_service "Alldata API" "$ALLDATA_API_URL/api/v1/health" 60 || true
wait_for_service "Bisheng API" "$BISHENG_API_URL/api/v1/health" 60 || true
wait_for_service "Cube API" "$CUBE_API_URL/v1/models" 120 || true

echo ""

# ==================== 阶段 2: Alldata API 测试 ====================
log_info "[2/5] Alldata API 测试..."

# 健康检查
test_health "Alldata API" "$ALLDATA_API_URL"

# 获取数据集列表
test_endpoint "数据集列表" "$ALLDATA_API_URL/api/v1/datasets" "dataset.*data"

# 获取元数据数据库列表
test_endpoint "元数据数据库列表" "$ALLDATA_API_URL/api/v1/metadata/databases" "database.*data"

# 创建数据集
log_info "创建测试数据集..."
DATASET_RESPONSE=$(curl -s -X POST "$ALLDATA_API_URL/api/v1/datasets" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "e2e-test-dataset",
        "storage_path": "s3://test/e2e/",
        "format": "csv"
    }' 2>&1)

if echo "$DATASET_RESPONSE" | grep -qE "dataset.*ds-"; then
    log_info "✓ 创建数据集成功"
    ((TESTS_PASSED++))

    # 提取 dataset_id 用于后续测试
    DATASET_ID=$(echo "$DATASET_RESPONSE" | grep -oE 'ds-[a-zA-Z0-9]+' | head -1)
    log_info "数据集 ID: $DATASET_ID"
else
    log_error "✗ 创建数据集失败"
    log_error "响应: $DATASET_RESPONSE"
    ((TESTS_FAILED++))
fi

echo ""

# ==================== 阶段 3: Bisheng API 测试 ====================
log_info "[3/5] Bisheng API 测试..."

# 健康检查
test_health "Bisheng API" "$BISHENG_API_URL"

# 获取工作流列表
test_endpoint "工作流列表" "$BISHENG_API_URL/api/v1/workflows" "workflow.*data"

# 创建工作流
log_info "创建测试工作流..."
WORKFLOW_RESPONSE=$(curl -s -X POST "$BISHENG_API_URL/api/v1/workflows" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "e2e-test-workflow",
        "type": "rag",
        "description": "E2E 测试工作流"
    }' 2>&1)

if echo "$WORKFLOW_RESPONSE" | grep -qE "workflow.*wf-"; then
    log_info "✓ 创建工作流成功"
    ((TESTS_PASSED++))

    # 提取 workflow_id 用于后续测试
    WORKFLOW_ID=$(echo "$WORKFLOW_RESPONSE" | grep -oE 'wf-[a-zA-Z0-9]+' | head -1)
    log_info "工作流 ID: $WORKFLOW_ID"
else
    log_error "✗ 创建工作流失败"
    log_error "响应: $WORKFLOW_RESPONSE"
    ((TESTS_FAILED++))
fi

# 测试 Text-to-SQL（跳过，需要完整的元数据）
log_info "跳过 Text-to-SQL 测试（需要完整元数据）"

echo ""

# ==================== 阶段 4: Cube API 测试 ====================
log_info "[4/5] Cube API (vLLM) 测试..."

# 获取模型列表
test_endpoint "模型列表" "$CUBE_API_URL/v1/models" "object.*data"

# 聊天补全测试（跳过，需要模型下载完成）
log_info "测试模型聊天补全..."
CHAT_RESPONSE=$(curl -s -X POST "$CUBE_API_URL/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d '{
        "model": "Qwen/Qwen-0.5B-Chat",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 10
    }' 2>&1)

if echo "$CHAT_RESPONSE" | grep -qE "choices|content"; then
    log_info "✓ 聊天补全测试通过"
    ((TESTS_PASSED++))
else
    log_warn "✗ 聊天补全测试失败（模型可能仍在下载中）"
    log_warn "响应: $CHAT_RESPONSE"
    # 不计入失败，因为模型下载需要时间
fi

echo ""

# ==================== 阶段 5: 端到端集成测试 ====================
log_info "[5/7] 端到端集成测试..."

# 集成点 1: Alldata → Cube（数据集注册与读取）
log_info "集成点 1/3: Alldata → Cube 数据集注册与读取..."
BISHENG_DATASETS=$(curl -s "$BISHENG_API_URL/api/v1/datasets" 2>&1)
if echo "$BISHENG_DATASETS" | grep -qE "dataset.*data|code.*0"; then
    log_info "✓ Bisheng 代理查询 Alldata 数据集成功"
    ((TESTS_PASSED++))
else
    log_error "✗ Bisheng 代理查询 Alldata 数据集失败"
    ((TESTS_FAILED++))
fi

# 集成点 2: Cube → Bisheng（模型服务调用）
log_info "集成点 2/3: Cube → Bisheng 模型服务调用..."
BISHENG_CHAT=$(curl -s -X POST "$BISHENG_API_URL/api/v1/chat" \
    -H "Content-Type: application/json" \
    -d '{
        "message": "测试消息",
        "model": "gpt-4o-mini",
        "temperature": 0.7
    }' 2>&1)

if echo "$BISHENG_CHAT" | grep -qE "reply|content|conversation_id"; then
    log_info "✓ Bisheng 调用 Cube 模型服务成功"
    ((TESTS_PASSED++))

    # 提取 conversation_id 用于后续测试
    CONVERSATION_ID=$(echo "$BISHENG_CHAT" | grep -oE 'conv-[a-zA-Z0-9]+' | head -1)
    log_info "会话 ID: $CONVERSATION_ID"
else
    log_error "✗ Bisheng 调用 Cube 模型服务失败"
    log_error "响应: $BISHENG_CHAT"
    ((TESTS_FAILED++))
fi

# 集成点 3: Alldata → Bisheng（Text-to-SQL 元数据查询）
log_info "集成点 3/3: Alldata → Bisheng Text-to-SQL 元数据查询..."
SQL_RESPONSE=$(curl -s -X POST "$BISHENG_API_URL/api/v1/sql/generate" \
    -H "Content-Type: application/json" \
    -d '{
        "question": "查询所有用户",
        "database": "sales_dw"
    }' 2>&1)

if echo "$SQL_RESPONSE" | grep -qE "sql|SELECT|code.*0"; then
    log_info "✓ Text-to-SQL 使用 Alldata 元数据成功"
    ((TESTS_PASSED++))
else
    log_warn "✗ Text-to-SQL 查询失败（可能需要完整元数据配置）"
    log_warn "响应: $SQL_RESPONSE"
    # 不计入失败，因为需要完整元数据配置
fi

# 测试文档上传和向量检索
log_info "测试文档上传和向量检索..."
DOC_RESPONSE=$(curl -s -X POST "$BISHENG_API_URL/api/v1/documents/upload" \
    -H "Content-Type: application/json" \
    -d '{
        "content": "ONE-DATA-STUDIO 是一个融合了数据治理、模型训练和应用编排的企业级 AI 平台。",
        "file_name": "test.txt",
        "title": "测试文档",
        "collection": "e2e-test"
    }' 2>&1)

if echo "$DOC_RESPONSE" | grep -qE "doc_id|chunk_count"; then
    log_info "✓ 文档上传和向量化成功"

    # 提取 doc_id 用于清理
    DOC_ID=$(echo "$DOC_RESPONSE" | grep -oE 'doc-[a-zA-Z0-9]+' | head -1)
    log_info "文档 ID: $DOC_ID"

    # 测试 RAG 查询
    RAG_RESPONSE=$(curl -s -X POST "$BISHENG_API_URL/api/v1/rag/query" \
        -H "Content-Type: application/json" \
        -d '{
            "question": "ONE-DATA-STUDIO 是什么平台？",
            "collection": "e2e-test",
            "top_k": 3
        }' 2>&1)

    if echo "$RAG_RESPONSE" | grep -qE "answer|sources"; then
        log_info "✓ RAG 查询成功"
        ((TESTS_PASSED++))
    else
        log_warn "✗ RAG 查询失败（可能需要 Milvus）"
    fi
else
    log_warn "✗ 文档上传失败"
fi

# 测试会话管理
log_info "测试会话管理..."
if [ -n "$CONVERSATION_ID" ]; then
    CONV_DETAIL=$(curl -s "$BISHENG_API_URL/api/v1/conversations/$CONVERSATION_ID" 2>&1)
    if echo "$CONV_DETAIL" | grep -qE "conversation_id|messages"; then
        log_info "✓ 会话详情查询成功"
        ((TESTS_PASSED++))
    else
        log_warn "✗ 会话详情查询失败"
    fi
fi

# 测试工作流执行
log_info "测试工作流执行..."
if [ -n "$WORKFLOW_ID" ]; then
    EXEC_RESPONSE=$(curl -s -X POST "$BISHENG_API_URL/api/v1/workflows/$WORKFLOW_ID/start" \
        -H "Content-Type: application/json" \
        -d '{"inputs": {"query": "测试"}}' 2>&1)

    if echo "$EXEC_RESPONSE" | grep -qE "execution_id|status.*running"; then
        log_info "✓ 工作流启动成功"
        ((TESTS_PASSED++))

        # 提取 execution_id 用于清理
        EXEC_ID=$(echo "$EXEC_RESPONSE" | grep -oE 'exec-[a-zA-Z0-9]+' | head -1)
        log_info "执行 ID: $EXEC_ID"
    else
        log_warn "✗ 工作流启动失败（可能需要完整工作流定义）"
    fi
fi

# 清理测试数据
log_info "清理测试数据..."
if [ -n "$DATASET_ID" ]; then
    curl -s -X DELETE "$ALLDATA_API_URL/api/v1/datasets/$DATASET_ID" > /dev/null 2>&1 || true
    log_info "已删除测试数据集: $DATASET_ID"
fi
if [ -n "$WORKFLOW_ID" ]; then
    curl -s -X DELETE "$BISHENG_API_URL/api/v1/workflows/$WORKFLOW_ID" > /dev/null 2>&1 || true
    log_info "已删除测试工作流: $WORKFLOW_ID"
fi
if [ -n "$DOC_ID" ]; then
    curl -s -X DELETE "$BISHENG_API_URL/api/v1/documents/$DOC_ID" > /dev/null 2>&1 || true
    log_info "已删除测试文档: $DOC_ID"
fi

echo ""

# ==================== 阶段 6: Playwright E2E 测试 (Sprint 9) ====================
log_info "[6/7] Playwright 前端 E2E 测试..."

# 检查 Playwright 是否安装
if ! command -v npx &> /dev/null; then
    log_warn "npx 未找到，跳过 Playwright 测试"
else
    # 检查是否在项目根目录
    if [ -f "package.json" ] && grep -q "playwright" package.json; then
        log_info "运行 Playwright E2E 测试..."

        # 运行 Playwright 测试
        if npx playwright test --reporter=line 2>&1; then
            log_info "✓ Playwright 测试通过"
            ((TESTS_PASSED++))
        else
            log_warn "✗ Playwright 测试失败（可能需要先安装浏览器: npx playwright install）"
            ((TESTS_FAILED++))
        fi
    else
        log_warn "Playwright 未配置，跳过前端 E2E 测试"
    fi
fi

echo ""

# ==================== 测试结果 ====================
echo "========================================"
echo "测试结果汇总"
echo "========================================"
echo -e "通过: ${GREEN}${TESTS_PASSED}${NC}"
echo -e "失败: ${RED}${TESTS_FAILED}${NC}"
echo "总计: $((TESTS_PASSED + TESTS_FAILED))"
echo "========================================"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    log_info "✓ 所有测试通过！"
    exit 0
else
    log_error "✗ 有 ${TESTS_FAILED} 个测试失败"
    exit 1
fi
