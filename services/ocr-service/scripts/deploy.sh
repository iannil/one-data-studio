#!/bin/bash
#
# OCR服务部署脚本
# 用于快速部署和测试OCR服务
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OCR_SERVICE_DIR="${PROJECT_DIR}/services/ocr-service"
DEPLOY_DIR="${PROJECT_DIR}/deploy/local"
API_URL="${API_URL:-http://localhost:8007}"

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 打印标题
print_header() {
    echo ""
    echo "================================"
    echo "  $1"
    echo "================================"
    echo ""
}

# 检查Docker
check_docker() {
    print_header "检查Docker"

    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi

    log_success "Docker环境检查通过"
}

# 构建服务
build_service() {
    print_header "构建OCR服务"

    cd "${PROJECT_DIR}"

    log_info "构建OCR服务镜像..."
    docker-compose -f "${DEPLOY_DIR}/docker-compose.yml" build ocr-service

    log_success "镜像构建完成"
}

# 启动服务
start_service() {
    print_header "启动OCR服务"

    cd "${PROJECT_DIR}"

    log_info "启动服务..."
    docker-compose -f "${DEPLOY_DIR}/docker-compose.yml" up -d ocr-service

    log_info "等待服务启动..."
    sleep 10

    # 检查服务状态
    if docker ps | grep -q "onedata-ocr-service"; then
        log_success "OCR服务启动成功"
    else
        log_error "OCR服务启动失败"
        exit 1
    fi
}

# 健康检查
health_check() {
    print_header "健康检查"

    log_info "检查服务状态..."

    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if curl -s "${API_URL}/health" | grep -q "healthy"; then
            log_success "服务健康检查通过"
            return 0
        fi

        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done

    echo ""
    log_error "服务健康检查失败"
    return 1
}

# 加载默认模板
load_templates() {
    print_header "加载默认模板"

    log_info "加载模板..."

    response=$(curl -s -X POST "${API_URL}/api/v1/ocr/templates/load-defaults")

    if echo "$response" | grep -q "message"; then
        log_success "模板加载成功"
    else
        log_warning "模板加载可能失败"
        echo "响应: $response"
    fi
}

# 测试API
test_api() {
    print_header "测试API"

    log_info "测试服务信息..."
    curl -s "${API_URL}/" | python3 -m json.tool || true

    echo ""

    log_info "测试支持的文档类型..."
    curl -s "${API_URL}/api/v1/ocr/templates/types" | python3 -m json.tool || true
}

# 查看日志
view_logs() {
    print_header "查看服务日志"

    docker logs -f --tail 50 onedata-ocr-service
}

# 停止服务
stop_service() {
    print_header "停止OCR服务"

    cd "${PROJECT_DIR}"

    log_info "停止服务..."
    docker-compose -f "${DEPLOY_DIR}/docker-compose.yml" stop ocr-service

    log_success "服务已停止"
}

# 重启服务
restart_service() {
    stop_service
    start_service
    health_check
}

# 清理服务
clean_service() {
    print_header "清理OCR服务"

    cd "${PROJECT_DIR}"

    log_info "停止并删除容器..."
    docker-compose -f "${DEPLOY_DIR}/docker-compose.yml" rm -f ocr-service

    log_info "清理镜像..."
    docker rmi onedata-ocr-service 2>/dev/null || true

    log_success "清理完成"
}

# 运行测试
run_tests() {
    print_header "运行测试"

    cd "${OCR_SERVICE_DIR}"

    if [ -f "scripts/verify_implementation.py" ]; then
        log_info "运行验证脚本..."
        python3 scripts/verify_implementation.py
    fi

    if [ -f "scripts/batch_test.py" ]; then
        log_info "运行批量测试..."
        python3 scripts/batch_test.py
    fi
}

# 性能测试
run_perf_test() {
    print_header "性能测试"

    cd "${OCR_SERVICE_DIR}"

    if [ -f "scripts/performance_test.py" ]; then
        python3 scripts/performance_test.py
    else
        log_warning "性能测试脚本不存在"
    fi
}

# 显示状态
show_status() {
    print_header "服务状态"

    cd "${PROJECT_DIR}"

    docker-compose -f "${DEPLOY_DIR}/docker-compose.yml" ps
}

# 显示帮助
show_help() {
    cat << EOF
OCR服务部署脚本

用法: $0 [命令]

命令:
  build       构建服务镜像
  start       启动服务
  stop        停止服务
  restart     重启服务
  status      查看服务状态
  logs        查看服务日志
  health      健康检查
  templates   加载默认模板
  test        测试API
  test-all    运行所有测试
  perf        性能测试
  clean       清理服务
  deploy      完整部署 (build + start + health + templates + test)
  help        显示帮助

示例:
  $0 deploy       # 完整部署
  $0 start        # 仅启动服务
  $0 logs         # 查看日志
  $0 test         # 测试API

环境变量:
  API_URL        API地址 (默认: http://localhost:8007)

EOF
}

# 主函数
main() {
    local command="${1:-help}"

    case "$command" in
        build)
            check_docker
            build_service
            ;;
        start)
            check_docker
            start_service
            ;;
        stop)
            stop_service
            ;;
        restart)
            restart_service
            ;;
        status)
            show_status
            ;;
        logs)
            view_logs
            ;;
        health)
            health_check
            ;;
        templates)
            load_templates
            ;;
        test)
            test_api
            ;;
        test-all)
            run_tests
            ;;
        perf)
            run_perf_test
            ;;
        clean)
            clean_service
            ;;
        deploy)
            check_docker
            build_service
            start_service
            health_check
            load_templates
            test_api
            log_success "部署完成！"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
