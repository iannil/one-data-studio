#!/bin/bash
# ONE-DATA-STUDIO 开发环境运维脚本 - 共享函数库
#
# 此文件提供所有开发环境脚本的共享配置和工具函数
# 使用方法: source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
#
# 兼容 Bash 3.x（macOS 默认版本）

# ==================== 路径配置 ====================

# 获取脚本目录和项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Docker Compose 配置文件路径
COMPOSE_DIR="$PROJECT_ROOT/deploy/local"
COMPOSE_FILE="$COMPOSE_DIR/docker-compose.yml"
COMPOSE_MONITORING_FILE="$COMPOSE_DIR/docker-compose.monitoring.yml"

# 环境变量文件
ENV_FILE="$PROJECT_ROOT/.env"
ENV_DEV_FILE="$PROJECT_ROOT/deploy/local/.env"

# 备份目录
BACKUP_DIR="$PROJECT_ROOT/backups"

# ==================== 颜色定义 ====================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

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

log_debug() {
    if [ "${DEBUG:-}" = "1" ] || [ "${DEBUG:-}" = "true" ]; then
        echo -e "${CYAN}[DEBUG]${NC} $1"
    fi
}

# 打印标题
print_header() {
    echo ""
    echo -e "${BOLD}========================================${NC}"
    echo -e "${BOLD}$1${NC}"
    echo -e "${BOLD}========================================${NC}"
    echo ""
}

# 打印分隔线
print_separator() {
    echo "----------------------------------------"
}

# ==================== 服务配置 ====================

# 基础设施服务（数据库、缓存、存储）
INFRA_SERVICES="mysql redis minio etcd milvus"

# 应用服务
APP_SERVICES="agent-api data-api openai-proxy model-api web-frontend"

# 监控服务
MONITORING_SERVICES="prometheus grafana jaeger loki"

# 所有服务
ALL_SERVICES="$INFRA_SERVICES $APP_SERVICES"

# ==================== 服务查找函数（替代关联数组）====================

# 解析服务别名
resolve_service_alias() {
    local input=$1
    case "$input" in
        o|openai|proxy) echo "openai-proxy" ;;
        w|web|frontend) echo "web-frontend" ;;
        m|db) echo "mysql" ;;
        r|cache) echo "redis" ;;
        s|storage) echo "minio" ;;
        vector) echo "milvus" ;;
        *) echo "$input" ;;
    esac
}

# 获取服务端口
get_service_port() {
    local service=$1
    case "$service" in
        mysql) echo "3306" ;;
        redis) echo "6379" ;;
        minio) echo "9000" ;;
        minio-console) echo "9001" ;;
        milvus) echo "19530" ;;
        etcd) echo "2379" ;;
        agent-api) echo "8000" ;;
        data-api) echo "8001" ;;
        model-api) echo "8002" ;;
        openai-proxy) echo "8003" ;;
        web-frontend) echo "3000" ;;
        prometheus) echo "9090" ;;
        grafana) echo "3001" ;;
        jaeger) echo "16686" ;;
        loki) echo "3100" ;;
        *) echo "" ;;
    esac
}

# 获取服务健康检查 URL
get_health_url() {
    local service=$1
    case "$service" in
        agent-api) echo "http://localhost:8000/api/v1/health" ;;
        data-api) echo "http://localhost:8001/api/v1/health" ;;
        model-api) echo "http://localhost:8002/api/v1/health" ;;
        openai-proxy) echo "http://localhost:8003/health" ;;
        web-frontend) echo "http://localhost:3000" ;;
        minio) echo "http://localhost:9000/minio/health/live" ;;
        prometheus) echo "http://localhost:9090/-/healthy" ;;
        grafana) echo "http://localhost:3001/api/health" ;;
        *) echo "" ;;
    esac
}

# 获取容器名称
get_container_name() {
    local service=$1
    case "$service" in
        mysql) echo "one-data-mysql" ;;
        redis) echo "one-data-redis" ;;
        minio) echo "one-data-minio" ;;
        milvus) echo "one-data-milvus" ;;
        etcd) echo "one-data-etcd" ;;
        agent-api) echo "one-data-agent-api" ;;
        data-api) echo "one-data-data-api" ;;
        openai-proxy) echo "one-data-openai-proxy" ;;
        model-api) echo "one-data-model-api" ;;
        web-frontend) echo "one-data-web" ;;
        prometheus) echo "one-data-prometheus" ;;
        grafana) echo "one-data-grafana" ;;
        jaeger) echo "one-data-jaeger" ;;
        loki) echo "one-data-loki" ;;
        *) echo "one-data-$service" ;;
    esac
}

# ==================== Docker Compose 封装函数 ====================

# 执行 docker-compose 命令
dc() {
    docker-compose -f "$COMPOSE_FILE" "$@"
}

# 执行带监控的 docker-compose 命令
dc_with_monitoring() {
    docker-compose -f "$COMPOSE_FILE" -f "$COMPOSE_MONITORING_FILE" "$@"
}

# 检查服务是否运行
is_service_running() {
    local service=$1
    local container_name=$(get_container_name "$service")

    docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${container_name}$"
}

# 获取服务状态
get_service_status() {
    local service=$1
    local container_name=$(get_container_name "$service")

    if ! docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q "^${container_name}$"; then
        echo "not_created"
        return
    fi

    local status=$(docker inspect --format='{{.State.Status}}' "$container_name" 2>/dev/null)
    local health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no_healthcheck{{end}}' "$container_name" 2>/dev/null)

    if [ "$status" = "running" ]; then
        if [ "$health" = "healthy" ]; then
            echo "healthy"
        elif [ "$health" = "unhealthy" ]; then
            echo "unhealthy"
        else
            echo "running"
        fi
    else
        echo "$status"
    fi
}

# ==================== 工具函数 ====================

# 检查 Docker 是否可用
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

# 检查 docker-compose 是否可用
check_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        return 0
    fi

    if docker compose version &> /dev/null; then
        return 0
    fi

    log_error "Docker Compose 未安装"
    return 1
}

# 检查端口是否被占用
check_port() {
    local port=$1
    local service=${2:-"unknown"}

    if lsof -i ":$port" -sTCP:LISTEN &>/dev/null; then
        local pid=$(lsof -t -i ":$port" -sTCP:LISTEN 2>/dev/null | head -1)
        local process=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
        log_warn "端口 $port ($service) 已被占用，进程: $process (PID: $pid)"
        return 1
    fi

    return 0
}

# 检查所有必需端口
check_required_ports() {
    local conflicts=0

    for service in $@; do
        local port=$(get_service_port "$service")
        if [ -n "$port" ] && ! is_service_running "$service"; then
            if ! check_port "$port" "$service"; then
                conflicts=$((conflicts + 1))
            fi
        fi
    done

    return $conflicts
}

# 等待服务健康
wait_for_health() {
    local service=$1
    local timeout=${2:-60}
    local interval=${3:-2}
    local count=0

    log_info "等待 $service 服务就绪..."

    while [ $count -lt $timeout ]; do
        local status=$(get_service_status "$service")

        if [ "$status" = "healthy" ] || [ "$status" = "running" ]; then
            log_success "$service 已就绪"
            return 0
        fi

        if [ "$status" = "exited" ] || [ "$status" = "dead" ]; then
            log_error "$service 启动失败（状态: $status）"
            return 1
        fi

        count=$((count + interval))
        sleep $interval
    done

    log_warn "$service 等待超时（${timeout}秒）"
    return 1
}

# 等待 HTTP 健康检查
wait_for_http() {
    local url=$1
    local service=${2:-"service"}
    local timeout=${3:-60}
    local count=0

    log_info "等待 $service HTTP 响应..."

    while [ $count -lt $timeout ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            log_success "$service HTTP 检查通过"
            return 0
        fi

        count=$((count + 2))
        sleep 2
    done

    log_warn "$service HTTP 检查超时"
    return 1
}

# 确认操作
confirm() {
    local message=${1:-"确认继续?"}
    local default=${2:-"n"}

    if [ "$default" = "y" ]; then
        read -p "$message (Y/n): " -n 1 -r REPLY
    else
        read -p "$message (y/N): " -n 1 -r REPLY
    fi
    echo

    if [ "$default" = "y" ]; then
        [[ ! $REPLY =~ ^[Nn]$ ]]
    else
        [[ $REPLY =~ ^[Yy]$ ]]
    fi
}

# 确认危险操作（需要输入特定文本）
confirm_dangerous() {
    local action=$1
    local confirm_text=${2:-"YES"}

    log_warn "这是一个危险操作: $action"
    read -p "请输入 '$confirm_text' 确认: " input

    [ "$input" = "$confirm_text" ]
}

# 格式化文件大小
format_size() {
    local size=$1

    if [ $size -ge 1073741824 ]; then
        echo "$(echo "scale=2; $size / 1073741824" | bc 2>/dev/null || awk "BEGIN {printf \"%.2f\", $size / 1073741824}") GB"
    elif [ $size -ge 1048576 ]; then
        echo "$(echo "scale=2; $size / 1048576" | bc 2>/dev/null || awk "BEGIN {printf \"%.2f\", $size / 1048576}") MB"
    elif [ $size -ge 1024 ]; then
        echo "$(echo "scale=2; $size / 1024" | bc 2>/dev/null || awk "BEGIN {printf \"%.2f\", $size / 1024}") KB"
    else
        echo "$size B"
    fi
}

# 格式化时间间隔
format_duration() {
    local seconds=$1

    if [ $seconds -ge 86400 ]; then
        echo "$(($seconds / 86400))d $((($seconds % 86400) / 3600))h"
    elif [ $seconds -ge 3600 ]; then
        echo "$(($seconds / 3600))h $(($seconds % 3600 / 60))m"
    elif [ $seconds -ge 60 ]; then
        echo "$(($seconds / 60))m $(($seconds % 60))s"
    else
        echo "${seconds}s"
    fi
}

# 加载环境变量
load_env() {
    local env_file=${1:-"$ENV_DEV_FILE"}

    if [ -f "$env_file" ]; then
        log_debug "加载环境变量: $env_file"
        set -a
        source "$env_file"
        set +a
        return 0
    fi

    # 尝试加载项目根目录的 .env
    if [ -f "$ENV_FILE" ]; then
        log_debug "加载环境变量: $ENV_FILE"
        set -a
        source "$ENV_FILE"
        set +a
        return 0
    fi

    log_warn "未找到环境变量文件"
    return 1
}

# 检查必需的环境变量
check_required_env() {
    local missing=""

    for var in "$@"; do
        eval "val=\${$var:-}"
        if [ -z "$val" ]; then
            if [ -z "$missing" ]; then
                missing="$var"
            else
                missing="$missing $var"
            fi
        fi
    done

    if [ -n "$missing" ]; then
        log_error "缺少必需的环境变量: $missing"
        log_info "请在 .env 文件中设置这些变量"
        return 1
    fi

    return 0
}

# 显示帮助信息
show_help() {
    local script_name=$(basename "$0")
    local description=${1:-"开发环境工具脚本"}
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

# 遍历服务列表的辅助函数
for_each_service() {
    local services="$1"
    local callback="$2"

    for service in $services; do
        $callback "$service"
    done
}

# ==================== 初始化检查 ====================

# 在脚本被 source 时不执行初始化检查
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    log_error "此脚本应该被 source，而不是直接执行"
    exit 1
fi
