#!/bin/bash
# ONE-DATA-STUDIO Common Functions Library
#
# This library provides shared functions for all stage-specific scripts
# Source this file in your scripts: source "$(dirname "${BASH_SOURCE[0]}")/common-functions.sh"

# ==================== Color Definitions ====================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# ==================== Logging Functions ====================
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_debug() {
    if [ "${DEBUG:-false}" = "true" ]; then
        echo -e "${CYAN}[DEBUG]${NC} $1"
    fi
}

# ==================== Banner Functions ====================
print_banner() {
    local stage=$1
    local description=$2

    echo ""
    echo "========================================"
    echo "ONE-DATA-STUDIO ${stage} Stage"
    echo "${description}"
    echo "========================================"
    echo ""
}

print_stage_info() {
    local stage=$1
    local prefix=$2

    echo ""
    echo "========================================"
    echo "Stage: ${stage}"
    echo "Port Prefix: ${prefix}"
    echo "========================================"
    echo ""
}

# ==================== Path Functions ====================
get_script_dir() {
    echo "$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
}

get_project_root() {
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
    echo "$(cd "${script_dir}/../.." && pwd)"
}

get_deploy_dir() {
    local project_root
    project_root="$(get_project_root)"
    echo "${project_root}/deploy"
}

get_local_deploy_dir() {
    local project_root
    project_root="$(get_project_root)"
    echo "${project_root}/deploy/local"
}

# ==================== Docker Functions ====================
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        return 1
    fi
    log_info "Docker 版本: $(docker --version)"
    return 0
}

check_docker_compose() {
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        return 1
    fi

    # Use docker-compose if available, otherwise use docker compose
    if command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    else
        echo "docker compose"
    fi
}

get_docker_compose_cmd() {
    if command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    else
        echo "docker compose"
    fi
}

# ==================== Environment Functions ====================
load_env_file() {
    local env_file="${1:-.env}"

    if [ -f "$env_file" ]; then
        log_info "加载环境变量: $env_file"
        # Export variables, ignoring comments and empty lines
        set -a
        source <(cat "$env_file" | grep -v '^#' | grep -v '^$')
        set +a
        return 0
    else
        log_warn "环境变量文件不存在: $env_file"
        return 1
    fi
}

check_required_env_vars() {
    local vars=("$@")
    local missing=()

    for var in "${vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing+=("$var")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        log_error "缺少必需的环境变量:"
        for var in "${missing[@]}"; do
            echo "  - $var"
        done
        return 1
    fi

    return 0
}

# ==================== Port Functions ====================
check_port_available() {
    local port=$1
    local service_name=${2:-service}

    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        log_warn "端口 $port 已被占用 (service: $service_name)"
        return 1
    fi
    return 0
}

wait_for_port() {
    local port=$1
    local service_name=$2
    local max_wait=${3:-60}
    local count=0

    log_info "等待 $service_name 端口 $port..."

    while [ $count -lt $max_wait ]; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 || \
           nc -z localhost $port >/dev/null 2>&1; then
            log_success "$service_name 端口 $port 已就绪"
            return 0
        fi
        ((count++))
        sleep 2
        echo -n "."
    done

    log_error "$service_name 端口 $port 未就绪（等待 ${max_wait} 秒后超时）"
    return 1
}

kill_port_process() {
    local port=$1

    local pid
    pid=$(lsof -ti:$port 2>/dev/null)

    if [ -n "$pid" ]; then
        log_warn "终止占用端口 $port 的进程 (PID: $pid)"
        kill -9 $pid 2>/dev/null || true
        sleep 1
    fi
}

# ==================== Health Check Functions ====================
health_check_http() {
    local service_name=$1
    local url=$2
    local max_wait=${3:-60}
    local count=0

    log_debug "检查 $service_name 健康状态: $url"

    while [ $count -lt $max_wait ]; do
        if curl -sf "$url" >/dev/null 2>&1; then
            log_success "$service_name 健康检查通过"
            return 0
        fi
        ((count++))
        sleep 2
        echo -n "."
    done

    log_error "$service_name 健康检查失败（等待 ${max_wait} 秒后超时）"
    return 1
}

wait_for_container_health() {
    local container_name=$1
    local max_wait=${2:-120}
    local count=0

    log_debug "等待容器 $container_name 健康检查通过..."

    while [ $count -lt $max_wait ]; do
        local status
        status=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "starting")

        if [ "$status" = "healthy" ]; then
            log_success "$container_name 健康检查通过"
            return 0
        fi

        if [ "$status" = "unhealthy" ]; then
            log_warn "$container_name 状态异常 (unhealthy)"
            return 1
        fi

        ((count++))
        sleep 3
        echo -n "."
    done

    log_warn "$container_name 健康检查超时，但继续执行"
    return 0
}

check_container_running() {
    local container_name=$1

    if docker ps -q -f name="$container_name" | grep -q .; then
        return 0
    else
        return 1
    fi
}

# ==================== Service Status Functions ====================
get_service_status() {
    local container_name=$1
    local status="unknown"

    if docker ps -q -f name="$container_name" | grep -q .; then
        status="running"
        # Check health status if available
        local health_status
        health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "")
        if [ -n "$health_status" ]; then
            status="$health_status"
        fi
    elif docker ps -a -q -f name="$container_name" | grep -q .; then
        status="stopped"
    else
        status="not_found"
    fi

    echo "$status"
}

print_service_status() {
    local service_name=$1
    local container_name=$2
    local port=$3
    local health_url=$4

    local status
    status=$(get_service_status "$container_name")

    case $status in
        running|healthy)
            echo -e "  ${service_name}: ${GREEN}● Running${NC} (:$port)"
            ;;
        unhealthy)
            echo -e "  ${service_name}: ${YELLOW}● Unhealthy${NC} (:$port)"
            ;;
        stopped)
            echo -e "  ${service_name}: ${RED}○ Stopped${NC} (:$port)"
            ;;
        not_found)
            echo -e "  ${service_name}: ${RED}○ Not Found${NC} (:$port)"
            ;;
        *)
            echo -e "  ${service_name}: ${YELLOW}● Unknown${NC} (:$port)"
            ;;
    esac
}

# ==================== Network Functions ====================
create_network_if_not_exists() {
    local network_name=$1

    if ! docker network ls -q -f name="$network_name" | grep -q .; then
        log_info "创建网络: $network_name"
        docker network create "$network_name" >/dev/null 2>&1
    else
        log_debug "网络已存在: $network_name"
    fi
}

# ==================== Cleanup Functions ====================
remove_stopped_containers() {
    log_info "清理已停止的容器..."
    docker container prune -f >/dev/null 2>&1
}

remove_dangling_images() {
    log_info "清理悬空镜像..."
    docker image prune -f >/dev/null 2>&1
}

# ==================== Stage Configuration ====================
get_stage_ports() {
    local stage=$1

    case $stage in
        dataops)
            echo "8100:8199"
            ;;
        mlops)
            echo "8200:8299"
            ;;
        llmops)
            echo "8300:8399"
            ;;
        *)
            echo "8000:8099"
            ;;
    esac
}

get_stage_network() {
    local stage=$1

    case $stage in
        dataops)
            echo "one-data-dataops-network"
            ;;
        mlops)
            echo "one-data-mlops-network"
            ;;
        llmops)
            echo "one-data-llmops-network"
            ;;
        *)
            echo "one-data-network"
            ;;
    esac
}

get_stage_project_name() {
    local stage=$1

    case $stage in
        dataops)
            echo "one-data-dataops"
            ;;
        mlops)
            echo "one-data-mlops"
            ;;
        llmops)
            echo "one-data-llmops"
            ;;
        *)
            echo "one-data"
            ;;
    esac
}

# ==================== Validation Functions ====================
validate_stage() {
    local stage=$1

    case $stage in
        dataops|mlops|llmops)
            return 0
            ;;
        *)
            log_error "无效的 stage: $stage"
            log_error "支持的 stage: dataops, mlops, llmops"
            return 1
            ;;
    esac
}

# ==================== Progress Functions ====================
show_progress() {
    local current=$1
    local total=$2
    local message=${3:-Processing}

    local percent=$((current * 100 / total))
    local filled=$((percent / 2))
    local empty=$((50 - filled))

    printf "\r${message}: ["
    printf "%${filled}s" | tr ' ' '='
    printf "%${empty}s" | tr ' ' ' '
    printf "] %d%%" "$percent"
}

# ==================== Summary Functions ====================
print_summary() {
    local stage=$1
    local prefix=$2
    shift 2
    local services=("$@")

    echo ""
    echo "========================================"
    echo "Summary: ${stage} Stage"
    echo "========================================"
    echo ""
    echo "服务列表:"

    for service in "${services[@]}"; do
        IFS=':' read -r name port url <<< "$service"
        if [ -n "$url" ]; then
            echo "  $name: http://localhost:$port$url"
        else
            echo "  $name: :$port"
        fi
    done

    echo ""
    echo "管理命令:"
    echo "  查看日志: docker-compose -f deploy/local/docker-compose.${stage}.yml logs -f [service]"
    echo "  停止服务: ./deploy/scripts/stop-${stage}.sh"
    echo "  查看状态: ./deploy/scripts/status-${stage}.sh"
    echo ""
}

# ==================== Export Functions ====================
# Export functions for use in subshells
export -f log_info log_error log_warn log_step log_success log_debug
export -f print_banner print_stage_info
export -f check_docker check_docker_compose get_docker_compose_cmd
export -f load_env_file check_required_env_vars
export -f check_port_available wait_for_port kill_port_process
export -f health_check_http wait_for_container_health check_container_running
export -f print_service_status
export -f create_network_if_not_exists
export -f remove_stopped_containers remove_dangling_images
export -f get_stage_ports get_stage_network get_stage_project_name
export -f validate_stage
export -f show_progress print_summary
