#!/bin/bash
# ONE-DATA-STUDIO Phase 2 部署脚本
# 部署 Web 前端到 Kubernetes

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印函数
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    print_info "检查依赖..."

    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi

    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl 未安装，请先安装 kubectl"
        exit 1
    fi

    if ! command -v kind &> /dev/null; then
        print_error "kind 未安装，请先安装 kind"
        exit 1
    fi

    print_info "依赖检查通过"
}

# 检查 Kind 集群
check_cluster() {
    print_info "检查 Kind 集群..."

    if ! kind get clusters | grep -q "one-data"; then
        print_error "Kind 集群 'one-data' 不存在"
        print_info "请先运行: make kind-cluster"
        exit 1
    fi

    print_info "Kind 集群检查通过"
}

# 构建 Docker 镜像
build_image() {
    print_info "构建 Web 前端 Docker 镜像..."

    cd "$(dirname "$0")/.."
    docker build -t one-data-web:latest web/

    print_info "Docker 镜像构建完成"
}

# 加载镜像到 Kind
load_image() {
    print_info "加载镜像到 Kind 集群..."

    kind load docker-image one-data-web:latest --name one-data

    print_info "镜像已加载到 Kind 集群"
}

# 部署到 Kubernetes
deploy_k8s() {
    print_info "部署 Web 前端到 Kubernetes..."

    kubectl apply -f k8s/applications/web-frontend.yaml

    print_info "等待 Pod 就绪..."
    kubectl wait --for=condition=ready pod -l app=web-frontend -n one-data-web --timeout=120s

    print_info "Web 前端已部署"
}

# 显示状态
show_status() {
    print_info "部署状态："
    echo ""
    kubectl get pods -n one-data-web
    echo ""
    kubectl get svc -n one-data-web
    echo ""
    print_info "访问 Web UI："
    echo "  方法1: kubectl port-forward -n one-data-web svc/web-frontend 3000:80"
    echo "  方法2: make web-forward"
    echo "  然后打开浏览器访问: http://localhost:3000"
}

# 清理
cleanup() {
    print_info "清理旧的部署（如果存在）..."
    kubectl delete -f k8s/applications/web-frontend.yaml --ignore-not-found=true
}

# 主函数
main() {
    print_info "开始部署 Phase 2 Web 前端..."
    echo ""

    # 解析参数
    CLEANUP=false
    SKIP_BUILD=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --cleanup)
                CLEANUP=true
                shift
                ;;
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --help)
                echo "用法: $0 [选项]"
                echo ""
                echo "选项:"
                echo "  --cleanup      部署前先清理旧资源"
                echo "  --skip-build   跳过镜像构建（使用已有镜像）"
                echo "  --help         显示帮助信息"
                exit 0
                ;;
            *)
                print_error "未知参数: $1"
                echo "使用 --help 查看帮助信息"
                exit 1
                ;;
        esac
    done

    # 执行部署流程
    check_dependencies
    check_cluster

    if [ "$CLEANUP" = true ]; then
        cleanup
    fi

    if [ "$SKIP_BUILD" = false ]; then
        build_image
    fi

    load_image
    deploy_k8s
    show_status

    echo ""
    print_info "Phase 2 部署完成！"
}

# 运行主函数
main "$@"
