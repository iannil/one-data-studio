#!/bin/bash
# ONE-DATA-STUDIO 分阶段测试脚本
#
# 用途: 在 16GB 内存限制下，分阶段启动和测试服务
# 用法: ./test-phased.sh [phase|all|clean]
#   phase: 1-7, 指定测试阶段
#   all: 运行全部阶段
#   clean: 清理所有容器和卷
#
# 示例:
#   ./test-phased.sh 1      # 仅运行阶段 1
#   ./test-phased.sh all    # 运行全部阶段
#   ./test-phased.sh clean  # 清理环境

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/test-logs/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

# 加载环境变量
if [ -f "${SCRIPT_DIR}/.env" ]; then
    export $(cat "${SCRIPT_DIR}/.env" | grep -v '^#' | grep -v '^$' | xargs)
else
    echo -e "${RED}错误: .env 文件不存在，请先创建 .env 文件${NC}"
    echo "提示: cp .env.example .env"
    exit 1
fi

# 日志函数
log() {
    local level=$1
    shift
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*"
    echo -e "$msg" | tee -a "$LOG_DIR/test.log"
}

log_info() { log "INFO" "$@"; }
log_success() { log -e "${GREEN}SUCCESS${NC} $*"; }
log_warning() { log -e "${YELLOW}WARNING${NC} $*"; }
log_error() { log -e "${RED}ERROR${NC} $*"; }
log_phase() { log -e "${BLUE}PHASE${NC} $*"; }

# Docker Compose 命令
DOCKER_COMPOSE="docker-compose -f ${SCRIPT_DIR}/docker-compose.yml"

# 健康检查函数
wait_for_service() {
    local service_name=$1
    local health_check_url=$2
    local max_wait=${3:-60}
    local wait_time=0

    log_info "等待 $service_name 启动..."

    while [ $wait_time -lt $max_wait ]; do
        if curl -sf "$health_check_url" > /dev/null 2>&1; then
            log_success "$service_name 已就绪"
            return 0
        fi
        sleep 2
        wait_time=$((wait_time + 2))
        echo -n "."
    done

    log_error "$service_name 启动超时"
    return 1
}

wait_for_container_health() {
    local container_name=$1
    local max_wait=${2:-60}
    local wait_time=0

    log_info "等待容器 $container_name 健康检查通过..."

    while [ $wait_time -lt $max_wait ]; do
        if docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null | grep -q "healthy"; then
            log_success "$container_name 健康检查通过"
            return 0
        fi
        sleep 2
        wait_time=$((wait_time + 2))
        echo -n "."
    done

    log_warning "$container_name 健康检查未通过，继续执行"
    return 0
}

# 获取内存使用
get_memory_usage() {
    docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}\t{{.MemPerc}}" 2>/dev/null | tee -a "$LOG_DIR/memory.log" || true
}

# 阶段 1: 基础设施验证
phase1_infrastructure() {
    log_phase "=== 阶段 1: 基础设施验证 (A 组: mysql, redis, minio) ==="

    log_info "启动基础设施服务..."
    $DOCKER_COMPOSE up -d mysql redis minio

    log_info "等待服务启动..."
    sleep 10

    # MySQL 健康检查
    log_info "检查 MySQL..."
    if docker exec one-data-mysql mysqladmin ping -h localhost -u root -p${MYSQL_ROOT_PASSWORD} 2>/dev/null; then
        log_success "MySQL 连接正常"
    else
        log_error "MySQL 连接失败"
        return 1
    fi

    # Redis 健康检查
    log_info "检查 Redis..."
    if docker exec one-data-redis redis-cli -a ${REDIS_PASSWORD} ping 2>/dev/null | grep -q PONG; then
        log_success "Redis 连接正常"
    else
        log_error "Redis 连接失败"
        return 1
    fi

    # MinIO 健康检查
    log_info "检查 MinIO..."
    if curl -sf http://localhost:9000/minio/health/live > /dev/null 2>&1; then
        log_success "MinIO 健康检查通过"
    else
        log_error "MinIO 健康检查失败"
        return 1
    fi

    # 记录服务状态
    $DOCKER_COMPOSE ps | tee -a "$LOG_DIR/phase1-services.log"
    get_memory_usage

    # 运行测试
    log_info "运行基础设施测试..."
    cd "$PROJECT_ROOT"
    if pytest tests/integration/test_phase1_infrastructure.py -v --tb=short 2>&1 | tee -a "$LOG_DIR/phase1-tests.log"; then
        log_success "阶段 1 测试通过"
    else
        log_warning "阶段 1 测试有失败，请查看日志"
    fi

    log_success "阶段 1 完成"
}

# 阶段 2: 元数据与向量数据库验证
phase2_metadata() {
    log_phase "=== 阶段 2: 元数据与向量数据库验证 (A+B 组) ==="

    log_info "启动元数据服务..."
    $DOCKER_COMPOSE up -d etcd milvus elasticsearch openmetadata

    log_info "等待服务启动..."
    sleep 20

    # 等待 etcd
    wait_for_container_health "one-data-etcd" 60

    # 等待 Milvus
    log_info "检查 Milvus..."
    if wait_for_service "Milvus" "http://localhost:19530/healthz" 120; then
        log_success "Milvus 已就绪"
    else
        log_warning "Milvus 未就绪，继续执行"
    fi

    # 等待 Elasticsearch
    log_info "检查 Elasticsearch..."
    if wait_for_service "Elasticsearch" "http://localhost:9200/_cluster/health" 120; then
        log_success "Elasticsearch 已就绪"
    else
        log_warning "Elasticsearch 未就绪，继续执行"
    fi

    # 等待 OpenMetadata
    log_info "检查 OpenMetadata..."
    if wait_for_service "OpenMetadata" "http://localhost:8585/api/v1/system/version" 180; then
        log_success "OpenMetadata 已就绪"
    else
        log_warning "OpenMetadata 未就绪，继续执行"
    fi

    # 记录服务状态
    $DOCKER_COMPOSE ps | tee -a "$LOG_DIR/phase2-services.log"
    get_memory_usage

    # 运行测试
    log_info "运行元数据服务测试..."
    cd "$PROJECT_ROOT"
    if pytest tests/integration/test_phase2_metadata.py -v --tb=short 2>&1 | tee -a "$LOG_DIR/phase2-tests.log"; then
        log_success "阶段 2 测试通过"
    else
        log_warning "阶段 2 测试有失败，请查看日志"
    fi

    log_success "阶段 2 完成"
}

# 阶段 3: 核心 API 服务验证
phase3_apis() {
    log_phase "=== 阶段 3: 核心 API 服务验证 (A+B+C 组) ==="

    log_info "启动核心 API 服务..."
    $DOCKER_COMPOSE up -d data-api admin-api openai-proxy

    log_info "等待 API 服务启动..."
    sleep 15

    # data-api 健康检查
    log_info "检查 data-api..."
    if wait_for_service "data-api" "http://localhost:8001/api/v1/health" 60; then
        log_success "data-api 已就绪"
    else
        log_warning "data-api 未就绪"
    fi

    # admin-api 健康检查
    log_info "检查 admin-api..."
    if wait_for_service "admin-api" "http://localhost:8004/api/v1/health" 60; then
        log_success "admin-api 已就绪"
    else
        log_warning "admin-api 未就绪"
    fi

    # openai-proxy 健康检查
    log_info "检查 openai-proxy..."
    if wait_for_service "openai-proxy" "http://localhost:8003/health" 60; then
        log_success "openai-proxy 已就绪"
    else
        log_warning "openai-proxy 未就绪"
    fi

    # 记录服务状态
    $DOCKER_COMPOSE ps | tee -a "$LOG_DIR/phase3-services.log"
    get_memory_usage

    # 运行测试
    log_info "运行 API 服务测试..."
    cd "$PROJECT_ROOT"
    if pytest tests/integration/test_phase3_apis.py -v --tb=short 2>&1 | tee -a "$LOG_DIR/phase3-tests.log"; then
        log_success "阶段 3 测试通过"
    else
        log_warning "阶段 3 测试有失败，请查看日志"
    fi

    log_success "阶段 3 完成"
}

# 阶段 4: Agent 和模型服务验证
phase4_agent() {
    log_phase "=== 阶段 4: Agent 和模型服务验证 (A+B+C+D 组) ==="

    log_info "启动 AI/Agent 服务..."
    $DOCKER_COMPOSE up -d agent-api model-api

    log_info "等待服务启动..."
    sleep 15

    # agent-api 健康检查
    log_info "检查 agent-api..."
    if wait_for_service "agent-api" "http://localhost:8000/api/v1/health" 60; then
        log_success "agent-api 已就绪"
    else
        log_warning "agent-api 未就绪"
    fi

    # model-api 健康检查
    log_info "检查 model-api..."
    if wait_for_service "model-api" "http://localhost:8002/api/v1/health" 60; then
        log_success "model-api 已就绪"
    else
        log_warning "model-api 未就绪"
    fi

    # 记录服务状态
    $DOCKER_COMPOSE ps | tee -a "$LOG_DIR/phase4-services.log"
    get_memory_usage

    # 运行测试
    log_info "运行 AI/Agent 服务测试..."
    cd "$PROJECT_ROOT"
    if pytest tests/integration/test_phase4_agent.py -v --tb=short 2>&1 | tee -a "$LOG_DIR/phase4-tests.log"; then
        log_success "阶段 4 测试通过"
    else
        log_warning "阶段 4 测试有失败，请查看日志"
    fi

    log_success "阶段 4 完成"
}

# 阶段 5: 前端集成验证
phase5_frontend() {
    log_phase "=== 阶段 5: 前端集成验证 (A+B+C+D+E 组) ==="

    log_info "启动前端服务..."
    $DOCKER_COMPOSE up -d web-frontend

    log_info "等待前端启动..."
    sleep 15

    # 前端健康检查
    log_info "检查 web-frontend..."
    if wait_for_service "web-frontend" "http://localhost:3000" 60; then
        log_success "web-frontend 已就绪"
    else
        log_warning "web-frontend 未就绪"
    fi

    # 记录服务状态
    $DOCKER_COMPOSE ps | tee -a "$LOG_DIR/phase5-services.log"
    get_memory_usage

    # 运行测试
    log_info "运行前端集成测试..."
    cd "$PROJECT_ROOT"
    if pytest tests/integration/test_phase5_frontend.py -v --tb=short 2>&1 | tee -a "$LOG_DIR/phase5-tests.log"; then
        log_success "阶段 5 测试通过"
    else
        log_warning "阶段 5 测试有失败，请查看日志"
    fi

    log_success "阶段 5 完成"
}

# 阶段 6: 扩展服务验证
phase6_extensions() {
    log_phase "=== 阶段 6: 扩展服务验证 (需要释放内存) ==="

    log_warning "此阶段需要停止部分服务以释放内存"

    # 停止内存密集型服务
    log_info "停止 openmetadata 和 elasticsearch..."
    $DOCKER_COMPOSE stop openmetadata elasticsearch 2>/dev/null || true

    sleep 5

    log_info "启动扩展服务..."
    $DOCKER_COMPOSE up -d ocr-service behavior-service keycloak

    log_info "等待服务启动..."
    sleep 15

    # ocr-service 健康检查
    log_info "检查 ocr-service..."
    if wait_for_service "ocr-service" "http://localhost:8007/health" 60; then
        log_success "ocr-service 已就绪"
    else
        log_warning "ocr-service 未就绪"
    fi

    # behavior-service 健康检查
    log_info "检查 behavior-service..."
    if wait_for_service "behavior-service" "http://localhost:8008/health" 60; then
        log_success "behavior-service 已就绪"
    else
        log_warning "behavior-service 未就绪"
    fi

    # keycloak 健康检查
    log_info "检查 keycloak..."
    if wait_for_service "keycloak" "http://localhost:8080/health" 60; then
        log_success "keycloak 已就绪"
    else
        log_warning "keycloak 未就绪"
    fi

    # 记录服务状态
    $DOCKER_COMPOSE ps | tee -a "$LOG_DIR/phase6-services.log"
    get_memory_usage

    # 运行测试
    log_info "运行扩展服务测试..."
    cd "$PROJECT_ROOT"
    if pytest tests/integration/test_phase6_extensions.py -v --tb=short 2>&1 | tee -a "$LOG_DIR/phase6-tests.log"; then
        log_success "阶段 6 测试通过"
    else
        log_warning "阶段 6 测试有失败，请查看日志"
    fi

    log_success "阶段 6 完成"
}

# 阶段 7: 重型服务验证 (独立测试)
phase7_heavy() {
    log_phase "=== 阶段 7: 重型服务验证 (独立测试) ==="

    log_warning "此阶段需要独立运行，请确保有足够的内存"
    read -p "是否继续? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "跳过阶段 7"
        return 0
    fi

    log_info "启动 Kettle ETL..."
    $DOCKER_COMPOSE up -d kettle

    log_info "等待 Kettle 启动..."
    if wait_for_service "Kettle" "http://localhost:8088/spoon/spoon" 180; then
        log_success "Kettle 已就绪"
    fi

    log_info "启动 Superset..."
    $DOCKER_COMPOSE up -d superset superset-cache

    log_info "等待 Superset 启动..."
    if wait_for_service "Superset" "http://localhost:8088/health" 180; then
        log_success "Superset 已就绪"
    fi

    # 记录服务状态
    $DOCKER_COMPOSE ps | tee -a "$LOG_DIR/phase7-services.log"
    get_memory_usage

    log_success "阶段 7 完成"
}

# 清理环境
clean_environment() {
    log_phase "=== 清理环境 ==="

    log_info "停止所有容器..."
    $DOCKER_COMPOSE down

    log_warning "是否删除数据卷? 这将删除所有数据!"
    read -p "删除数据卷? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "删除数据卷..."
        $DOCKER_COMPOSE down -v
    fi

    log_success "清理完成"
}

# 显示状态
show_status() {
    log_phase "=== 当前服务状态 ==="
    $DOCKER_COMPOSE ps
    echo ""
    log_info "内存使用情况:"
    get_memory_usage
}

# 主函数
main() {
    local command=${1:-all}

    case $command in
        1)
            phase1_infrastructure
            ;;
        2)
            phase1_infrastructure
            phase2_metadata
            ;;
        3)
            phase1_infrastructure
            phase2_metadata
            phase3_apis
            ;;
        4)
            phase1_infrastructure
            phase2_metadata
            phase3_apis
            phase4_agent
            ;;
        5)
            phase1_infrastructure
            phase2_metadata
            phase3_apis
            phase4_agent
            phase5_frontend
            ;;
        6)
            phase1_infrastructure
            phase2_metadata
            phase3_apis
            phase4_agent
            phase6_extensions
            ;;
        7)
            phase7_heavy
            ;;
        all)
            log_phase "=== 运行全部阶段测试 (1-6) ==="
            phase1_infrastructure
            phase2_metadata
            phase3_apis
            phase4_agent
            phase5_frontend
            log_warning "阶段 6 和 7 需要手动运行"
            ;;
        clean)
            clean_environment
            ;;
        status)
            show_status
            ;;
        *)
            echo "用法: $0 [1-7|all|clean|status]"
            echo ""
            echo "阶段说明:"
            echo "  1     - 基础设施验证 (mysql, redis, minio)"
            echo "  2     - 元数据与向量数据库 (阶段1 + etcd, milvus, elasticsearch, openmetadata)"
            echo "  3     - 核心 API 服务 (阶段2 + data-api, admin-api, openai-proxy)"
            echo "  4     - Agent 和模型服务 (阶段3 + agent-api, model-api)"
            echo "  5     - 前端集成 (阶段4 + web-frontend)"
            echo "  6     - 扩展服务 (需要停止部分服务释放内存)"
            echo "  7     - 重型服务 (Kettle, Superset - 独立测试)"
            echo "  all   - 运行阶段 1-5"
            echo "  clean - 清理所有容器和卷"
            echo "  status- 显示当前状态"
            exit 1
            ;;
    esac

    log_success "测试日志保存在: $LOG_DIR"
    echo ""
    log_info "查看日志:"
    echo "  cat $LOG_DIR/test.log"
}

main "$@"
