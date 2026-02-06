#!/bin/bash
# ONE-DATA-STUDIO All Stages Status Check Script
#
# This script checks the status of all three stages (DataOps, MLOps, LLMOps)
#
# Usage:
#   ./deploy/scripts/status-all.sh [options]
#
# Options:
#   --verbose    Show detailed status for each service
#   --json       Output status in JSON format
#   --watch      Continuously monitor status (refresh every 5s)
#   --help       Show this help message

set -e

# ==================== Configuration ====================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common functions
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
check_all_status() {
    local verbose=$1
    local json_output=$2

    if [ "$json_output" = "true" ]; then
        echo "{"
        echo "  \"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\","
        echo "  \"stages\": {"
        echo "    \"dataops\": {"
        "$SCRIPT_DIR/status-dataops.sh" --json | tail -n +2 | head -n -1 | sed 's/^/      /'
        echo "    },"
        echo "    \"mlops\": {"
        "$SCRIPT_DIR/status-mlops.sh" --json | tail -n +2 | head -n -1 | sed 's/^/      /'
        echo "    },"
        echo "    \"llmops\": {"
        "$SCRIPT_DIR/status-llmops.sh" --json | tail -n +2 | head -n -1 | sed 's/^/      /'
        echo "    }"
        echo "  }"
        echo "}"
    else
        echo ""
        echo "========================================"
        echo "ONE-DATA-STUDIO 全平台状态"
        echo "========================================"
        echo ""

        # DataOps Status
        echo "=== DataOps 阶段 (81xx) ==="
        "$SCRIPT_DIR/status-dataops.sh" 2>/dev/null || echo "  无法获取状态"
        echo ""

        # MLOps Status
        echo "=== MLOps 阶段 (82xx) ==="
        "$SCRIPT_DIR/status-mlops.sh" 2>/dev/null || echo "  无法获取状态"
        echo ""

        # LLMOps Status
        echo "=== LLMOps 阶段 (83xx) ==="
        "$SCRIPT_DIR/status-llmops.sh" 2>/dev/null || echo "  无法获取状态"
        echo ""

        # Summary
        echo "========================================"
        echo "端口分配:"
        echo "  DataOps: 81xx"
        echo "  MLOps:   82xx"
        echo "  LLMOps:  83xx"
        echo "========================================"
    fi
}

# ==================== Verbose Mode ====================
show_verbose_status() {
    echo ""
    echo "========================================"
    echo "ONE-DATA-STUDIO 详细状态"
    echo "========================================"
    echo ""

    # Show all containers
    echo "所有 ONE-DATA-STUDIO 容器:"
    echo ""

    local containers
    containers=$(docker ps -a --format "{{.Names}}" --filter "name=one-data-" 2>/dev/null || echo "")

    if [ -z "$containers" ]; then
        echo "  没有找到 ONE-DATA-STUDIO 容器"
    else
        echo "$containers" | while read -r container; do
            echo "  $container:"
            echo "    状态: $(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "unknown")"
            local health
            health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "N/A")
            [ "$health" != "N/A" ] && echo "    健康检查: $health"
            echo "    镜像: $(docker inspect --format='{{.Config.Image}}' "$container" 2>/dev/null | cut -d: -f2 | cut -d@ -f1 || echo "unknown")"

            # Determine stage
            if [[ "$container" == *"-dataops"* ]]; then
                echo "    阶段: DataOps"
            elif [[ "$container" == *"-mlops"* ]]; then
                echo "    阶段: MLOps"
            elif [[ "$container" == *"-llmops"* ]]; then
                echo "    阶段: LLMOps"
            else
                echo "    阶段: 共享服务"
            fi
            echo ""
        done
    fi

    # Show resource usage
    echo "资源使用:"
    echo ""
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" \
        --filter "name=one-data-" 2>/dev/null || echo "  无法获取资源使用信息"
    echo ""

    # Show network info
    echo "网络:"
    echo ""
    docker network ls --filter "name=one-data" --format "  {{.Name}}: {{.Driver}}" 2>/dev/null || echo "  无法获取网络信息"
    echo ""

    # Show volumes
    echo "数据卷:"
    echo ""
    docker volume ls --filter "name=one-data" --format "  {{.Name}}" 2>/dev/null || echo "  无法获取数据卷信息"
    echo ""
}

# ==================== Main ====================
if [ "$WATCH_MODE" = "true" ]; then
    print_banner "ALL STAGES" "Monitoring Mode (Ctrl+C to exit)"
    while true; do
        clear
        check_all_status "$VERBOSE" "$JSON_OUTPUT"
        sleep 5
    done
elif [ "$VERBOSE" = "true" ]; then
    show_verbose_status
else
    print_banner "ALL STAGES" "Service Status"
    check_all_status "$VERBOSE" "$JSON_OUTPUT"
fi

echo ""
echo "管理命令:"
echo "  启动 DataOps: ./deploy/scripts/start-dataops.sh"
echo "  启动 MLOps:   ./deploy/scripts/start-mlops.sh"
echo "  启动 LLMOps:  ./deploy/scripts/start-llmops.sh"
echo "  停止 DataOps: ./deploy/scripts/stop-dataops.sh"
echo "  停止 MLOps:   ./deploy/scripts/stop-mlops.sh"
echo "  停止 LLMOps:  ./deploy/scripts/stop-llmops.sh"
echo ""
