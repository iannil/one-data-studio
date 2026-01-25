#!/bin/bash
# ONE-DATA-STUDIO 开发环境清理脚本
#
# 使用方法:
#   ./scripts/dev/dev-clean.sh [选项]
#
# 示例:
#   ./scripts/dev/dev-clean.sh -l       # 清理日志
#   ./scripts/dev/dev-clean.sh -d       # 清理 Docker 资源
#   ./scripts/dev/dev-clean.sh -a       # 清理所有

set -e

# 加载共享函数库
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# ==================== 默认配置 ====================

CLEAN_LOGS=false
CLEAN_TEMP=false
CLEAN_DOCKER=false
CLEAN_NPM=false
CLEAN_PIP=false
CLEAN_ALL=false
DRY_RUN=false

# ==================== 解析参数 ====================

show_clean_help() {
    show_help \
        "ONE-DATA-STUDIO 开发环境清理脚本" \
        "dev-clean.sh [选项]" \
        "  -l, --logs     清理日志文件
  -t, --temp     清理临时文件
  -d, --docker   清理 Docker 资源（悬挂镜像、未使用网络等）
  -n, --npm      清理 npm 缓存和 node_modules
  -p, --pip      清理 pip 缓存
  -a, --all      清理所有
  --dry-run      预览将被删除的内容（不实际删除）
  -h, --help     显示帮助信息" \
        "  dev-clean.sh -l           # 清理日志
  dev-clean.sh -d           # 清理 Docker
  dev-clean.sh -a           # 清理所有
  dev-clean.sh --dry-run -a # 预览所有清理"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -l|--logs)
            CLEAN_LOGS=true
            shift
            ;;
        -t|--temp)
            CLEAN_TEMP=true
            shift
            ;;
        -d|--docker)
            CLEAN_DOCKER=true
            shift
            ;;
        -n|--npm)
            CLEAN_NPM=true
            shift
            ;;
        -p|--pip)
            CLEAN_PIP=true
            shift
            ;;
        -a|--all)
            CLEAN_ALL=true
            CLEAN_LOGS=true
            CLEAN_TEMP=true
            CLEAN_DOCKER=true
            CLEAN_NPM=true
            CLEAN_PIP=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            show_clean_help
            exit 0
            ;;
        -*)
            log_error "未知选项: $1"
            show_clean_help
            exit 1
            ;;
        *)
            shift
            ;;
    esac
done

# 如果没有指定任何清理选项，显示帮助
if [ "$CLEAN_LOGS" = false ] && [ "$CLEAN_TEMP" = false ] && \
   [ "$CLEAN_DOCKER" = false ] && [ "$CLEAN_NPM" = false ] && \
   [ "$CLEAN_PIP" = false ]; then
    show_clean_help
    exit 0
fi

# ==================== 清理函数 ====================

# 计算目录大小
get_dir_size() {
    local dir=$1
    if [ -d "$dir" ]; then
        du -sh "$dir" 2>/dev/null | cut -f1
    else
        echo "0"
    fi
}

# 安全删除
safe_remove() {
    local path=$1
    local description=$2

    if [ "$DRY_RUN" = true ]; then
        if [ -e "$path" ]; then
            local size=$(get_dir_size "$path")
            log_info "[DRY-RUN] 将删除: $path ($size)"
        fi
    else
        if [ -e "$path" ]; then
            rm -rf "$path"
            log_success "已删除: $description"
        fi
    fi
}

# 清理日志文件
clean_logs() {
    log_step "清理日志文件..."

    local total_size=0

    # 清理项目日志目录
    local log_dirs=(
        "$PROJECT_ROOT/logs"
        "$PROJECT_ROOT/services/alldata-api/logs"
        "$PROJECT_ROOT/services/bisheng-api/logs"
        "$PROJECT_ROOT/services/openai-proxy/logs"
        "$PROJECT_ROOT/services/cube-api/logs"
    )

    for dir in "${log_dirs[@]}"; do
        if [ -d "$dir" ]; then
            if [ "$DRY_RUN" = true ]; then
                local size=$(get_dir_size "$dir")
                log_info "[DRY-RUN] 将清理: $dir ($size)"
            else
                find "$dir" -type f \( -name "*.log" -o -name "*.log.*" \) -delete 2>/dev/null
                log_success "已清理: $dir"
            fi
        fi
    done

    # 清理 Python 日志文件
    if [ "$DRY_RUN" = true ]; then
        local py_logs=$(find "$PROJECT_ROOT" -type f -name "*.log" 2>/dev/null | wc -l | tr -d ' ')
        log_info "[DRY-RUN] 将删除 $py_logs 个 .log 文件"
    else
        find "$PROJECT_ROOT" -type f -name "*.log" -delete 2>/dev/null || true
    fi

    log_success "日志清理完成"
}

# 清理临时文件
clean_temp() {
    log_step "清理临时文件..."

    # Python 缓存
    if [ "$DRY_RUN" = true ]; then
        local pycache=$(find "$PROJECT_ROOT" -type d -name "__pycache__" 2>/dev/null | wc -l | tr -d ' ')
        log_info "[DRY-RUN] 将删除 $pycache 个 __pycache__ 目录"
    else
        find "$PROJECT_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        log_success "已清理 __pycache__ 目录"
    fi

    # .pyc 文件
    if [ "$DRY_RUN" = true ]; then
        local pyc=$(find "$PROJECT_ROOT" -type f -name "*.pyc" 2>/dev/null | wc -l | tr -d ' ')
        log_info "[DRY-RUN] 将删除 $pyc 个 .pyc 文件"
    else
        find "$PROJECT_ROOT" -type f -name "*.pyc" -delete 2>/dev/null || true
        log_success "已清理 .pyc 文件"
    fi

    # pytest 缓存
    safe_remove "$PROJECT_ROOT/.pytest_cache" "pytest 缓存"
    safe_remove "$PROJECT_ROOT/tests/.pytest_cache" "tests pytest 缓存"

    # mypy 缓存
    safe_remove "$PROJECT_ROOT/.mypy_cache" "mypy 缓存"

    # coverage 文件
    safe_remove "$PROJECT_ROOT/.coverage" "coverage 数据"
    safe_remove "$PROJECT_ROOT/htmlcov" "coverage HTML 报告"

    # .DS_Store
    if [ "$DRY_RUN" = true ]; then
        local ds=$(find "$PROJECT_ROOT" -type f -name ".DS_Store" 2>/dev/null | wc -l | tr -d ' ')
        log_info "[DRY-RUN] 将删除 $ds 个 .DS_Store 文件"
    else
        find "$PROJECT_ROOT" -type f -name ".DS_Store" -delete 2>/dev/null || true
    fi

    log_success "临时文件清理完成"
}

# 清理 Docker 资源
clean_docker() {
    log_step "清理 Docker 资源..."

    if ! check_docker; then
        log_warn "Docker 不可用，跳过 Docker 清理"
        return
    fi

    if [ "$DRY_RUN" = true ]; then
        # 预览悬挂镜像
        local dangling=$(docker images -f "dangling=true" -q 2>/dev/null | wc -l | tr -d ' ')
        log_info "[DRY-RUN] 将删除 $dangling 个悬挂镜像"

        # 预览未使用的卷
        local volumes=$(docker volume ls -qf "dangling=true" 2>/dev/null | wc -l | tr -d ' ')
        log_info "[DRY-RUN] 将删除 $volumes 个未使用的卷"

        # 预览未使用的网络
        local networks=$(docker network ls -qf "type=custom" 2>/dev/null | wc -l | tr -d ' ')
        log_info "[DRY-RUN] 将检查 $networks 个自定义网络"

        return
    fi

    # 清理悬挂镜像
    log_info "清理悬挂镜像..."
    docker image prune -f 2>/dev/null || true

    # 清理已停止的容器（仅 one-data 相关）
    log_info "清理已停止的容器..."
    docker ps -a --filter "name=one-data" --filter "status=exited" -q 2>/dev/null | \
        xargs -r docker rm 2>/dev/null || true

    # 清理未使用的网络
    log_info "清理未使用的网络..."
    docker network prune -f 2>/dev/null || true

    # 询问是否清理构建缓存
    if confirm "是否清理 Docker 构建缓存?"; then
        docker builder prune -f 2>/dev/null || true
        log_success "已清理构建缓存"
    fi

    log_success "Docker 资源清理完成"
}

# 清理 npm 缓存
clean_npm() {
    log_step "清理 npm 资源..."

    local web_dir="$PROJECT_ROOT/web"

    if [ -d "$web_dir" ]; then
        # node_modules
        if [ -d "$web_dir/node_modules" ]; then
            local size=$(get_dir_size "$web_dir/node_modules")
            if [ "$DRY_RUN" = true ]; then
                log_info "[DRY-RUN] 将删除 node_modules ($size)"
            else
                if confirm "删除 node_modules ($size)?"; then
                    rm -rf "$web_dir/node_modules"
                    log_success "已删除 node_modules"
                fi
            fi
        fi

        # Vite 缓存
        safe_remove "$web_dir/.vite" "Vite 缓存"
        safe_remove "$web_dir/node_modules/.vite" "Vite node_modules 缓存"

        # 构建输出
        safe_remove "$web_dir/dist" "构建输出"
    fi

    # npm 缓存
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] 将清理 npm 缓存"
    else
        if confirm "清理 npm 全局缓存?"; then
            npm cache clean --force 2>/dev/null || true
            log_success "已清理 npm 缓存"
        fi
    fi

    log_success "npm 资源清理完成"
}

# 清理 pip 缓存
clean_pip() {
    log_step "清理 pip 资源..."

    # 虚拟环境
    local venv_dirs=(
        "$PROJECT_ROOT/venv"
        "$PROJECT_ROOT/.venv"
        "$PROJECT_ROOT/env"
        "$PROJECT_ROOT/services/alldata-api/venv"
        "$PROJECT_ROOT/services/bisheng-api/venv"
        "$PROJECT_ROOT/services/openai-proxy/venv"
    )

    for dir in "${venv_dirs[@]}"; do
        if [ -d "$dir" ]; then
            local size=$(get_dir_size "$dir")
            if [ "$DRY_RUN" = true ]; then
                log_info "[DRY-RUN] 将删除虚拟环境: $dir ($size)"
            else
                if confirm "删除虚拟环境 $dir ($size)?"; then
                    rm -rf "$dir"
                    log_success "已删除 $dir"
                fi
            fi
        fi
    done

    # pip 缓存
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] 将清理 pip 缓存"
    else
        if confirm "清理 pip 缓存?"; then
            pip cache purge 2>/dev/null || python3 -m pip cache purge 2>/dev/null || true
            log_success "已清理 pip 缓存"
        fi
    fi

    log_success "pip 资源清理完成"
}

# ==================== 主函数 ====================

main() {
    print_header "开发环境清理"

    if [ "$DRY_RUN" = true ]; then
        log_warn "预览模式 - 不会实际删除任何文件"
        echo ""
    fi

    # 执行清理
    [ "$CLEAN_LOGS" = true ] && clean_logs
    [ "$CLEAN_TEMP" = true ] && clean_temp
    [ "$CLEAN_DOCKER" = true ] && clean_docker
    [ "$CLEAN_NPM" = true ] && clean_npm
    [ "$CLEAN_PIP" = true ] && clean_pip

    echo ""
    if [ "$DRY_RUN" = true ]; then
        log_info "预览完成 - 使用不带 --dry-run 的命令执行实际清理"
    else
        log_success "清理完成"
    fi
}

main
