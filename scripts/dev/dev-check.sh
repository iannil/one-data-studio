#!/bin/bash
# ONE-DATA-STUDIO 开发环境健康检查脚本
#
# 使用方法:
#   ./scripts/dev/dev-check.sh [命令] [选项]
#
# 命令:
#   health   - 检查服务健康状态
#   ports    - 检查端口占用
#   deps     - 检查依赖版本
#   disk     - 检查磁盘使用
#   network  - 检查网络连接
#   all      - 执行所有检查

set -e

# 加载共享函数库
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# ==================== 默认配置 ====================

COMMAND="all"
VERBOSE=false
FIX_ISSUES=false

# ==================== 解析参数 ====================

show_check_help() {
    show_help \
        "ONE-DATA-STUDIO 开发环境健康检查脚本" \
        "dev-check.sh [命令] [选项]" \
        "命令:
  health   检查服务健康状态（Docker 容器、HTTP 端点）
  ports    检查端口占用情况
  deps     检查依赖版本（Docker、Node、Python 等）
  disk     检查磁盘空间和 Docker 资源使用
  network  检查网络连接
  all      执行所有检查（默认）

选项:
  -v, --verbose  显示详细信息
  --fix          尝试自动修复发现的问题
  -h, --help     显示帮助信息" \
        "  dev-check.sh              # 执行所有检查
  dev-check.sh health       # 仅检查健康状态
  dev-check.sh ports        # 仅检查端口
  dev-check.sh -v all       # 详细模式"
}

# 获取命令
if [ $# -gt 0 ] && [[ ! "$1" =~ ^- ]]; then
    COMMAND=$1
    shift
fi

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            export DEBUG=1
            shift
            ;;
        --fix)
            FIX_ISSUES=true
            shift
            ;;
        -h|--help)
            show_check_help
            exit 0
            ;;
        -*)
            log_error "未知选项: $1"
            show_check_help
            exit 1
            ;;
        *)
            shift
            ;;
    esac
done

# ==================== 检查函数 ====================

# 检查结果计数
PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

# 记录检查结果
check_pass() {
    echo -e "  ${GREEN}✓${NC} $1"
    PASS_COUNT=$((PASS_COUNT + 1))
}

check_warn() {
    echo -e "  ${YELLOW}⚠${NC} $1"
    WARN_COUNT=$((WARN_COUNT + 1))
}

check_fail() {
    echo -e "  ${RED}✗${NC} $1"
    FAIL_COUNT=$((FAIL_COUNT + 1))
}

# 检查服务健康状态
check_health() {
    echo -e "${BOLD}服务健康检查${NC}"
    echo ""

    # 检查 Docker
    if docker info &>/dev/null; then
        check_pass "Docker 服务运行正常"
    else
        check_fail "Docker 服务未运行"
        return
    fi

    # 检查各服务容器状态
    echo ""
    echo "  容器状态:"

    for service in $ALL_SERVICES; do
        local status=$(get_service_status "$service")
        local container_name=$(get_container_name "$service")

        case $status in
            healthy)
                check_pass "$service: 健康"
                ;;
            running)
                check_warn "$service: 运行中（无健康检查）"
                ;;
            unhealthy)
                check_fail "$service: 不健康"
                if [ "$VERBOSE" = true ]; then
                    echo "      日志: docker logs --tail 10 $container_name"
                fi
                ;;
            exited)
                check_warn "$service: 已退出"
                ;;
            not_created)
                if [ "$VERBOSE" = true ]; then
                    echo -e "      ${CYAN}-${NC} $service: 未创建"
                fi
                ;;
            *)
                check_warn "$service: $status"
                ;;
        esac
    done

    # HTTP 端点检查
    echo ""
    echo "  HTTP 端点:"

    for service in $ALL_SERVICES; do
        if is_service_running "$service"; then
            local url=$(get_health_url "$service")
            if [ -n "$url" ]; then
                if curl -sf "$url" &>/dev/null; then
                    check_pass "$service: $url"
                else
                    check_fail "$service: $url 无响应"
                fi
            fi
        fi
    done

    echo ""
}

# 检查端口占用
check_ports() {
    echo -e "${BOLD}端口检查${NC}"
    echo ""

    local port_services="mysql redis minio milvus etcd bisheng-api alldata-api cube-api openai-proxy web-frontend prometheus grafana jaeger loki"

    for service in $port_services; do
        local port=$(get_service_port "$service")

        if [ -n "$port" ]; then
            # 检查端口是否被 one-data 容器占用（正常情况）
            if is_service_running "$service"; then
                check_pass "端口 $port ($service): 已被服务占用"
            else
                # 检查是否被其他进程占用
                if lsof -i ":$port" -sTCP:LISTEN &>/dev/null; then
                    local pid=$(lsof -t -i ":$port" -sTCP:LISTEN 2>/dev/null | head -1)
                    local process=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
                    check_warn "端口 $port ($service): 被 $process (PID: $pid) 占用"
                else
                    if [ "$VERBOSE" = true ]; then
                        echo -e "      ${CYAN}-${NC} 端口 $port ($service): 空闲"
                    fi
                fi
            fi
        fi
    done

    echo ""
}

# 检查依赖版本
check_deps() {
    echo -e "${BOLD}依赖版本检查${NC}"
    echo ""

    # Docker
    if command -v docker &>/dev/null; then
        local docker_version=$(docker --version | awk '{print $3}' | tr -d ',')
        check_pass "Docker: $docker_version"
    else
        check_fail "Docker: 未安装"
    fi

    # Docker Compose
    if command -v docker-compose &>/dev/null; then
        local compose_version=$(docker-compose --version | awk '{print $4}' | tr -d ',')
        check_pass "Docker Compose: $compose_version"
    elif docker compose version &>/dev/null; then
        local compose_version=$(docker compose version | awk '{print $4}')
        check_pass "Docker Compose (V2): $compose_version"
    else
        check_fail "Docker Compose: 未安装"
    fi

    # Node.js
    if command -v node &>/dev/null; then
        local node_version=$(node --version)
        local major_version=$(echo "$node_version" | cut -d. -f1 | tr -d 'v')
        if [ "$major_version" -ge 18 ]; then
            check_pass "Node.js: $node_version"
        else
            check_warn "Node.js: $node_version（建议 v18+）"
        fi
    else
        check_warn "Node.js: 未安装（前端开发需要）"
    fi

    # npm
    if command -v npm &>/dev/null; then
        local npm_version=$(npm --version)
        check_pass "npm: $npm_version"
    fi

    # Python
    if command -v python3 &>/dev/null; then
        local python_version=$(python3 --version | awk '{print $2}')
        local major_minor=$(echo "$python_version" | cut -d. -f1,2)
        if [ "$(echo "$major_minor >= 3.9" | bc)" -eq 1 ] 2>/dev/null || [[ "$major_minor" > "3.8" ]]; then
            check_pass "Python: $python_version"
        else
            check_warn "Python: $python_version（建议 3.9+）"
        fi
    else
        check_warn "Python: 未安装"
    fi

    # Git
    if command -v git &>/dev/null; then
        local git_version=$(git --version | awk '{print $3}')
        check_pass "Git: $git_version"
    else
        check_warn "Git: 未安装"
    fi

    # curl
    if command -v curl &>/dev/null; then
        check_pass "curl: 已安装"
    else
        check_warn "curl: 未安装"
    fi

    # jq (可选)
    if command -v jq &>/dev/null; then
        local jq_version=$(jq --version 2>/dev/null || echo "unknown")
        check_pass "jq: $jq_version"
    else
        if [ "$VERBOSE" = true ]; then
            echo -e "      ${CYAN}-${NC} jq: 未安装（可选，用于 JSON 处理）"
        fi
    fi

    echo ""
}

# 检查磁盘使用
check_disk() {
    echo -e "${BOLD}磁盘使用检查${NC}"
    echo ""

    # 项目目录磁盘空间
    local disk_usage=$(df -h "$PROJECT_ROOT" | tail -1)
    local used_percent=$(echo "$disk_usage" | awk '{print $5}' | tr -d '%')
    local available=$(echo "$disk_usage" | awk '{print $4}')

    if [ "$used_percent" -lt 80 ]; then
        check_pass "磁盘空间: ${used_percent}% 已用，${available} 可用"
    elif [ "$used_percent" -lt 90 ]; then
        check_warn "磁盘空间: ${used_percent}% 已用，${available} 可用（建议清理）"
    else
        check_fail "磁盘空间不足: ${used_percent}% 已用，${available} 可用"
    fi

    # Docker 磁盘使用
    if docker info &>/dev/null; then
        echo ""
        echo "  Docker 资源使用:"

        local docker_df=$(docker system df 2>/dev/null)

        # 镜像
        local images_size=$(echo "$docker_df" | grep "Images" | awk '{print $3}')
        local images_count=$(echo "$docker_df" | grep "Images" | awk '{print $2}')
        echo "      镜像: $images_count 个，$images_size"

        # 容器
        local containers_size=$(echo "$docker_df" | grep "Containers" | awk '{print $3}')
        local containers_count=$(echo "$docker_df" | grep "Containers" | awk '{print $2}')
        echo "      容器: $containers_count 个，$containers_size"

        # 卷
        local volumes_size=$(echo "$docker_df" | grep "Volumes" | awk '{print $3}')
        local volumes_count=$(echo "$docker_df" | grep "Volumes" | awk '{print $2}')
        echo "      数据卷: $volumes_count 个，$volumes_size"

        # 构建缓存
        local cache_size=$(echo "$docker_df" | grep "Build Cache" | awk '{print $3}')
        echo "      构建缓存: $cache_size"

        # 检查可回收空间
        local reclaimable=$(docker system df 2>/dev/null | tail -1 | grep -oP '\d+\.?\d*[KMGT]?B' | tail -1 || echo "0")
        if [ -n "$reclaimable" ] && [ "$reclaimable" != "0B" ]; then
            check_warn "可回收空间: $reclaimable（使用 'make dev-clean -d' 清理）"
        fi
    fi

    echo ""
}

# 检查网络连接
check_network() {
    echo -e "${BOLD}网络检查${NC}"
    echo ""

    # Docker 网络
    if docker network ls | grep -q "one-data-network"; then
        check_pass "Docker 网络 one-data-network 存在"
    else
        check_warn "Docker 网络 one-data-network 不存在（将在启动时创建）"
    fi

    # 外部连接
    if curl -sf --max-time 5 "https://registry.hub.docker.com/v2/" &>/dev/null; then
        check_pass "Docker Hub 连接正常"
    else
        check_warn "Docker Hub 连接失败（可能影响镜像拉取）"
    fi

    # 内部服务连接
    echo ""
    echo "  服务间连接:"

    local running_services=()
    for service in "${ALL_SERVICES[@]}"; do
        if is_service_running "$service"; then
            running_services+=("$service")
        fi
    done

    if [ ${#running_services[@]} -gt 1 ]; then
        # 检查 API 服务是否能连接数据库
        if is_service_running "bisheng-api" && is_service_running "mysql"; then
            local container_name="${CONTAINER_NAMES[bisheng-api]}"
            if docker exec "$container_name" python -c "import pymysql; pymysql.connect(host='mysql', port=3306)" 2>/dev/null; then
                check_pass "bisheng-api → mysql 连接正常"
            else
                check_warn "bisheng-api → mysql 连接未验证"
            fi
        fi

        if is_service_running "bisheng-api" && is_service_running "redis"; then
            local container_name="${CONTAINER_NAMES[bisheng-api]}"
            if docker exec "$container_name" python -c "import redis; redis.Redis(host='redis', port=6379).ping()" 2>/dev/null; then
                check_pass "bisheng-api → redis 连接正常"
            else
                check_warn "bisheng-api → redis 连接未验证"
            fi
        fi
    else
        echo "      （需要至少两个服务运行才能检查）"
    fi

    echo ""
}

# 显示检查汇总
show_summary() {
    print_separator

    local total=$((PASS_COUNT + WARN_COUNT + FAIL_COUNT))

    echo ""
    echo -e "${BOLD}检查汇总:${NC}"
    echo -e "  ${GREEN}通过: $PASS_COUNT${NC}"
    echo -e "  ${YELLOW}警告: $WARN_COUNT${NC}"
    echo -e "  ${RED}失败: $FAIL_COUNT${NC}"
    echo ""

    if [ $FAIL_COUNT -gt 0 ]; then
        log_error "存在 $FAIL_COUNT 个问题需要解决"
        return 1
    elif [ $WARN_COUNT -gt 0 ]; then
        log_warn "存在 $WARN_COUNT 个警告"
        return 0
    else
        log_success "所有检查通过"
        return 0
    fi
}

# ==================== 主函数 ====================

main() {
    print_header "开发环境健康检查"

    case $COMMAND in
        health)
            check_health
            ;;
        ports)
            check_ports
            ;;
        deps)
            check_deps
            ;;
        disk)
            check_disk
            ;;
        network)
            check_network
            ;;
        all)
            check_deps
            check_disk
            check_ports
            check_health
            check_network
            ;;
        *)
            log_error "未知命令: $COMMAND"
            show_check_help
            exit 1
            ;;
    esac

    show_summary
}

main
