#!/bin/bash
# ONE-DATA-STUDIO MLOps Stage Status Check Script
#
# This script checks the status of MLOps stage services
#
# Usage:
#   ./deploy/scripts/status-mlops.sh [options]
#
# Options:
#   --verbose    Show detailed status for each service
#   --json       Output status in JSON format
#   --watch      Continuously monitor status (refresh every 5s)
#   --help       Show this help message

set -e

# ==================== Configuration ====================
STAGE="mlops"
STAGE_PREFIX="82xx"

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
check_mlops_status() {
    local verbose=$1
    local json_output=$2

    if [ "$json_output" = "true" ]; then
        echo "{"
        echo "  \"stage\": \"$STAGE\","
        echo "  \"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\","
        echo "  \"services\": {"
    fi

    # MLOps services definition
    declare -A SERVICES=(
        ["MySQL"]="one-data-mysql:3306"
        ["Redis"]="one-data-redis:6379"
        ["MinIO"]="one-data-minio:9000"
        ["model-api"]="one-data-model-api-mlops:8202"
        ["Label Studio"]="one-data-label-studio-mlops:8209"
        ["Label Studio DB"]="one-data-label-studio-pg-mlops:5434"
        ["vLLM Chat"]="one-data-vllm-chat-mlops:8210"
        ["vLLM Embed"]="one-data-vllm-embed-mlops:8211"
        ["Ollama"]="one-data-ollama-mlops:8134"
        ["OCR Service"]="one-data-ocr-service-mlops:8207"
        ["Behavior Service"]="one-data-behavior-service-mlops:8208"
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
    echo "MLOps Stage 详细状态"
    echo "========================================"
    echo ""

    # Show container details
    echo "容器详情:"
    echo ""

    local containers=(
        "one-data-mysql"
        "one-data-redis"
        "one-data-minio"
        "one-data-model-api-mlops"
        "one-data-label-studio-mlops"
        "one-data-label-studio-pg-mlops"
        "one-data-vllm-chat-mlops"
        "one-data-vllm-embed-mlops"
        "one-data-ollama-mlops"
        "one-data-ocr-service-mlops"
        "one-data-behavior-service-mlops"
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
        -f "name=one-data-model-api-mlops" \
        -f "name=one-data-vllm-chat-mlops" \
        -f "name=one-data-ocr-service-mlops" \
        2>/dev/null || echo "  无法获取资源使用信息"
    echo ""

    # Show GPU status if available
    if command -v nvidia-smi &> /dev/null; then
        echo "GPU 状态:"
        echo ""
        nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total --format=csv,noheader 2>/dev/null | sed 's/^/  /' || echo "  无法获取 GPU 信息"
        echo ""
    fi

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

    # Show loaded models
    echo "已加载的模型:"
    echo ""
    if docker ps -q -f name="one-data-vllm-chat-mlops" | grep -q .; then
        echo "  vLLM Chat:"
        docker exec one-data-vllm-chat-mlops curl -s http://localhost:8000/v1/models 2>/dev/null | grep -o '"id":"[^"]*"' | sed 's/"id":"\(.*\)"/    - \1/' || echo "    无法获取模型信息"
    fi
    if docker ps -q -f name="one-data-ollama-mlops" | grep -q .; then
        echo "  Ollama:"
        docker exec one-data-ollama-mlops curl -s http://localhost:11434/api/tags 2>/dev/null | grep -o '"name":"[^"]*"' | sed 's/"name":"\(.*\)"/    - \1/' || echo "    无法获取模型信息"
    fi
    echo ""
}

# ==================== Main ====================
if [ "$WATCH_MODE" = "true" ]; then
    print_banner "MLOps" "Monitoring Mode (Ctrl+C to exit)"
    while true; do
        clear
        check_mlops_status "$VERBOSE" "$JSON_OUTPUT"
        sleep 5
    done
elif [ "$VERBOSE" = "true" ]; then
    show_verbose_status
else
    print_banner "MLOps" "Service Status"
    check_mlops_status "$VERBOSE" "$JSON_OUTPUT"
fi

echo ""
echo "管理命令:"
echo "  启动服务: ./deploy/scripts/start-mlops.sh"
echo "  停止服务: ./deploy/scripts/stop-mlops.sh"
echo "  查看日志: docker logs -f [container_name]"
echo ""
