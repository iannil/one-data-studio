#!/bin/bash
# ONE-DATA-STUDIO DataOps Stage Status Check Script
#
# This script checks the status of DataOps stage services
#
# Usage:
#   ./deploy/scripts/status-dataops.sh [options]
#
# Options:
#   --verbose    Show detailed status for each service
#   --json       Output status in JSON format
#   --watch      Continuously monitor status (refresh every 5s)
#   --help       Show this help message

set -e

# ==================== Configuration ====================
STAGE="dataops"
STAGE_PREFIX="81xx"

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common-functions.sh"

# Parse command line arguments
VERBOSE=false
JSON_OUTPUT=false
WATCH_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose)
            VERBOSE=true
            shift
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --watch)
            WATCH_MODE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --verbose    Show detailed status for each service"
            echo "  --json       Output status in JSON format"
            echo "  --watch      Continuously monitor status (refresh every 5s)"
            echo "  --help       Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# ==================== Status Check Function ====================
check_dataops_status() {
    local verbose=$1
    local json_output=$2

    if [ "$json_output" = "true" ]; then
        echo "{"
        echo "  \"stage\": \"$STAGE\","
        echo "  \"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\","
        echo "  \"services\": {"
    fi

    # DataOps services definition
    declare -A SERVICES=(
        ["MySQL"]="one-data-mysql:3306"
        ["Redis"]="one-data-redis:6379"
        ["MinIO"]="one-data-minio:9000"
        ["Milvus"]="one-data-milvus-dataops:19530"
        ["Elasticsearch"]="one-data-elasticsearch-dataops:9200"
        ["OpenMetadata"]="one-data-openmetadata-dataops:8585"
        ["Kettle"]="one-data-kettle-dataops:8180"
        ["Keycloak"]="one-data-keycloak-dataops:8180"
        ["DolphinScheduler"]="one-data-dolphinscheduler-dataops:8123"
        ["Superset Cache"]="one-data-superset-cache-dataops:6380"
        ["Superset"]="one-data-superset-dataops:8188"
        ["data-api"]="one-data-data-api-dataops:8101"
    )

    local first=true
    local running_count=0
    local total_count=${#SERVICES[@]}

    for service in "${!SERVICES[@]}"; do
        IFS=':' read -r container port <<< "${SERVICES[$service]}"

        local status
        status=$(get_service_status "$container")

        if [ "$json_output" = "true" ]; then
            [ "$first" = "false" ] && echo ","
            first=false
            echo "    \"$service\": {"
            echo "      \"container\": \"$container\","
            echo "      \"port\": $port,"
            echo "      \"status\": \"$status\""
            echo -n "    }"
        else
            print_service_status "$service" "$container" "$port"
            if [ "$status" = "running" ] || [ "$status" = "healthy" ]; then
                ((running_count++))
            fi
        fi
    done

    if [ "$json_output" = "true" ]; then
        echo ""
        echo "  },"
        echo "  \"summary\": {"
        echo "    \"total\": $total_count,"
        echo "    \"running\": $running_count"
        echo "  }"
        echo "}"
    else
        echo ""
        echo "========================================"
        echo "总计: $running_count/$total_count 服务运行中"
        echo "========================================"
    fi

    # Return 0 if all running, 1 otherwise
    [ "$running_count" -eq "$total_count" ] && return 0 || return 1
}

# ==================== Verbose Mode ====================
show_verbose_status() {
    echo ""
    echo "========================================"
    echo "DataOps Stage 详细状态"
    echo "========================================"
    echo ""

    # Show container details
    echo "容器详情:"
    echo ""

    local containers=(
        "one-data-mysql"
        "one-data-redis"
        "one-data-minio"
        "one-data-milvus-dataops"
        "one-data-etcd-dataops"
        "one-data-elasticsearch-dataops"
        "one-data-openmetadata-dataops"
        "one-data-kettle-dataops"
        "one-data-keycloak-dataops"
        "one-data-dolphinscheduler-dataops"
        "one-data-superset-dataops"
        "one-data-data-api-dataops"
    )

    for container in "${containers[@]}"; do
        if docker ps -a -q -f name="$container" | grep -q .; then
            echo "  $container:"
            echo "    状态: $(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "unknown")"
            local health
            health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "N/A")
            [ "$health" != "N/A" ] && echo "    健康检查: $health"
            echo "    镜像: $(docker inspect --format='{{.Config.Image}}' "$container" 2>/dev/null | cut -d: -f2 | cut -d@ -f1 || echo "unknown")"

            local ports
            ports=$(docker port "$container" 2>/dev/null || echo "")
            if [ -n "$ports" ]; then
                echo "    端口映射: $ports"
            fi
            echo ""
        fi
    done

    # Show resource usage
    echo "资源使用:"
    echo ""
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" \
        -f "name=one-data-mysql" \
        -f "name=one-data-redis" \
        -f "name=one-data-minio" \
        -f "name=one-data-milvus-dataops" \
        -f "name=one-data-openmetadata-dataops" \
        -f "name=one-data-kettle-dataops" \
        -f "name=one-data-data-api-dataops" \
        2>/dev/null || echo "  无法获取资源使用信息"
    echo ""

    # Show recent logs for unhealthy services
    echo "最近日志 (异常服务):"
    echo ""
    for container in "${containers[@]}"; do
        local status
        status=$(get_service_status "$container")
        if [ "$status" = "unhealthy" ] || [ "$status" = "stopped" ]; then
            echo "  $container (最近 5 条):"
            docker logs --tail 5 "$container" 2>/dev/null | sed 's/^/    /' || echo "    无法获取日志"
            echo ""
        fi
    done
}

# ==================== Main ====================
if [ "$WATCH_MODE" = "true" ]; then
    print_banner "DataOps" "Monitoring Mode (Ctrl+C to exit)"
    while true; do
        clear
        check_dataops_status "$VERBOSE" "$JSON_OUTPUT"
        sleep 5
    done
elif [ "$VERBOSE" = "true" ]; then
    show_verbose_status
else
    print_banner "DataOps" "Service Status"
    check_dataops_status "$VERBOSE" "$JSON_OUTPUT"
fi

echo ""
echo "管理命令:"
echo "  启动服务: ./deploy/scripts/start-dataops.sh"
echo "  停止服务: ./deploy/scripts/stop-dataops.sh"
echo "  查看日志: docker logs -f [container_name]"
echo ""
