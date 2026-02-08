#!/bin/bash
# ONE-DATA-STUDIO 本地开发环境 - 重启所有服务
#
# 此脚本重启所有本地开发服务
#
# 使用方法:
#   ./restart-all.sh             # 重启所有服务
#   ./restart-all.sh --apps-only # 仅重启应用服务
#   ./restart-all.sh --infra-only # 仅重启基础设施

set -e

# 加载共享函数
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# ==================== 配置 ====================

APPS_ONLY=false
INFRA_ONLY=false

# ==================== 解析参数 ====================

while [[ $# -gt 0 ]]; do
    case $1 in
        --apps-only)
            APPS_ONLY=true
            shift
            ;;
        --infra-only)
            INFRA_ONLY=true
            shift
            ;;
        -h|--help)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --apps-only     仅重启应用服务（本地）"
            echo "  --infra-only    仅重启基础设施服务（Docker）"
            echo "  -h, --help      显示帮助信息"
            echo ""
            echo "示例:"
            echo "  $0              # 重启所有服务"
            echo "  $0 --apps-only  # 仅重启 Web 和 API 服务"
            echo "  $0 --infra-only # 仅重启 MySQL, Redis 等"
            exit 0
            ;;
        *)
            log_error "未知选项: $1"
            exit 1
            ;;
    esac
done

# ==================== 主函数 ====================

main() {
    print_header "重启本地开发环境"

    # 先停止
    if [ "$INFRA_ONLY" = false ]; then
        "$SCRIPT_DIR/stop-all.sh" --apps-only
    fi

    if [ "$APPS_ONLY" = false ]; then
        "$SCRIPT_DIR/stop-all.sh" --infra-only
    fi

    # 等待完全停止
    sleep 2

    # 再启动
    if [ "$APPS_ONLY" = false ]; then
        "$SCRIPT_DIR/start-all.sh" "${INFRA_ONLY:+--infra-only}"
    fi

    if [ "$INFRA_ONLY" = false ]; then
        "$SCRIPT_DIR/start-all.sh" "${APPS_ONLY:+--apps-only}"
    fi

    log_success "本地开发环境已重启"
}

main
