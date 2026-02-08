#!/bin/bash
# ONE-DATA-STUDIO 本地开发环境 - 共享函数库
#
# 此脚本用于本地开发环境：
# - 基础设施服务（MySQL, Redis, MinIO 等）运行在 Docker 中
# - 应用服务（Web, API）直接在本地运行

# 注意：不使用 set -e，因为此脚本被 source 时会影响调用脚本

# ==================== 路径配置 ====================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WEB_DIR="$PROJECT_ROOT/web"
DEPLOY_DIR="$PROJECT_ROOT/deploy/local"
SERVICES_DIR="$PROJECT_ROOT/services"
PID_DIR="$PROJECT_ROOT/.local-dev-pids"
LOG_DIR="$PROJECT_ROOT/.local-dev-logs"

# 创建必要的目录
mkdir -p "$PID_DIR"
mkdir -p "$LOG_DIR"

# ==================== 颜色定义 ====================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ==================== 日志函数 ====================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_header() {
    echo ""
    echo -e "${BOLD}========================================${NC}"
    echo -e "${BOLD}$1${NC}"
    echo -e "${BOLD}========================================${NC}"
    echo ""
}

# ==================== 基础设施服务配置 ====================

# Docker Compose 文件（仅包含基础设施服务）
INFRA_COMPOSE="$DEPLOY_DIR/docker-compose.infra.yml"

# 如果不存在独立的 infra compose 文件，使用默认 compose
if [ ! -f "$INFRA_COMPOSE" ]; then
    INFRA_COMPOSE="$DEPLOY_DIR/docker-compose.yml"
fi

# 基础设施服务列表
INFRA_SERVICES="mysql redis minio etcd milvus"

# ==================== 应用服务配置 ====================

# Node.js 版本
NODE_VERSION=${NODE_VERSION:-"18"}

# Python 版本 (使用 pyenv Python 3.12.11 以兼容所有依赖)
PYTHON_VERSION=${PYTHON_VERSION:-"3.12"}
PYTHON_CMD="${PYENV_ROOT:-$HOME/.pyenv}/versions/3.12.11/bin/python3"

# 服务端口配置 (使用函数而非关联数组，兼容 bash 3.x)
get_service_port() {
    case "$1" in
        web) echo "3000" ;;
        data-api) echo "8001" ;;
        agent-api) echo "8000" ;;
        admin-api) echo "8004" ;;
        model-api) echo "8002" ;;
        openai-proxy) echo "8003" ;;
        ocr-service) echo "8007" ;;
        behavior-service) echo "8008" ;;
        *) echo "" ;;
    esac
}

# ==================== 环境变量配置 ====================

# 默认数据库连接（与 deploy/local/.env 保持一致）
export DATABASE_URL="${DATABASE_URL:-mysql+pymysql://onedata:dev123@localhost:3306/onedata}"
export REDIS_URL="${REDIS_URL:-redis://:redisdev123@localhost:6379/0}"

# MinIO 配置
export MINIO_ENDPOINT="${MINIO_ENDPOINT:-localhost:9000}"
export MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
export MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin123}"

# Milvus 配置
export MILVUS_HOST="${MILVUS_HOST:-localhost}"
export MILVUS_PORT="${MILVUS_PORT:-19530}"

# 认证配置（开发环境默认关闭）
export AUTH_MODE="${AUTH_MODE:-false}"

# Model API 配置
export MODEL_DATABASE_URL="${MODEL_DATABASE_URL:-mysql+pymysql://onedata:dev123@localhost:3306/model_db}"

# ==================== 工具函数 ====================

# 检查 Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        return 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker 服务未运行，请先启动 Docker"
        return 1
    fi

    return 0
}

# 检查 Node.js
check_node() {
    if ! command -v node &> /dev/null; then
        log_error "Node.js 未安装，请先安装 Node.js $NODE_VERSION+"
        return 1
    fi

    local current_version=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$current_version" -lt 18 ]; then
        log_error "Node.js 版本过低 (当前: $current_version, 需要: 18+)"
        return 1
    fi

    return 0
}

# 检查 Python
check_python() {
    # 优先使用 pyenv Python 3.12
    if [ -f "$PYTHON_CMD" ]; then
        return 0
    fi

    # 回退到系统 python3
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        return 0
    fi

    log_error "Python 3 未安装，请先安装 Python $PYTHON_VERSION+"
    return 1
}

# 检查端口是否被占用
check_port() {
    local port=$1
    local service=${2:-"service"}

    if lsof -i ":$port" -sTCP:LISTEN &>/dev/null; then
        local pid=$(lsof -t -i ":$port" -sTCP:LISTEN 2>/dev/null | head -1)
        log_warn "端口 $port ($service) 已被占用 (PID: $pid)"
        return 1
    fi

    return 0
}

# 获取服务 PID 文件路径
get_pid_file() {
    local service=$1
    echo "$PID_DIR/$service.pid"
}

# 检查服务是否运行
is_service_running() {
    local service=$1
    local pid_file=$(get_pid_file "$service")

    if [ ! -f "$pid_file" ]; then
        return 1
    fi

    local pid=$(cat "$pid_file")
    if ps -p "$pid" > /dev/null 2>&1; then
        return 0
    fi

    # PID 文件存在但进程不存在，清理
    rm -f "$pid_file"
    return 1
}

# 停止服务
stop_service() {
    local service=$1
    local pid_file=$(get_pid_file "$service")

    if [ ! -f "$pid_file" ]; then
        log_info "$service 未运行"
        return 0
    fi

    local pid=$(cat "$pid_file")
    if ps -p "$pid" > /dev/null 2>&1; then
        log_info "停止 $service (PID: $pid)..."
        kill "$pid"
        # 等待进程结束
        local count=0
        while ps -p "$pid" > /dev/null 2>&1 && [ $count -lt 10 ]; do
            sleep 1
            count=$((count + 1))
        done

        # 如果还没结束，强制杀死
        if ps -p "$pid" > /dev/null 2>&1; then
            log_warn "强制停止 $service..."
            kill -9 "$pid"
        fi

        log_success "$service 已停止"
    fi

    rm -f "$pid_file"
}

# 等待服务就绪
wait_for_service() {
    local url=$1
    local service=${2:-"service"}
    local timeout=${3:-60}
    local count=0

    log_info "等待 $service 服务就绪..."

    while [ $count -lt $timeout ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            log_success "$service 已就绪"
            return 0
        fi

        count=$((count + 2))
        sleep 2
    done

    log_warn "$service 等待超时"
    return 1
}

# 加载环境变量
load_env() {
    local env_file="$PROJECT_ROOT/.env"

    if [ -f "$env_file" ]; then
        log_debug "加载环境变量: $env_file"
        set -a
        source "$env_file"
        set +a
    fi

    # 加载 deploy/local/.env
    local local_env="$DEPLOY_DIR/.env"
    if [ -f "$local_env" ]; then
        set -a
        source "$local_env"
        set +a
    fi
}

log_debug() {
    if [ "${DEBUG:-}" = "1" ] || [ "${DEBUG:-}" = "true" ]; then
        echo -e "${CYAN}[DEBUG]${NC} $1"
    fi
}

# 显示帮助信息
show_help() {
    local script_name=$(basename "$0")
    local description=${1:-"本地开发环境工具脚本"}
    local usage=${2:-"$script_name [选项]"}
    local options=${3:-""}
    local examples=${4:-""}

    echo ""
    echo -e "${BOLD}$description${NC}"
    echo ""
    echo -e "${BOLD}用法:${NC}"
    echo "  $usage"

    if [ -n "$options" ]; then
        echo ""
        echo -e "${BOLD}选项:${NC}"
        echo -e "$options"
    fi

    if [ -n "$examples" ]; then
        echo ""
        echo -e "${BOLD}示例:${NC}"
        echo -e "$examples"
    fi

    echo ""
}
