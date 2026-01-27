#!/bin/bash
#
# OCR服务Kubernetes部署脚本
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 配置
K8S_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/k8s"
NAMESPACE="ocr-service"
CONTEXT="${KUBECONTEXT:-}"

# 检查kubectl
check_kubectl() {
    print_header "检查kubectl"

    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl未安装"
        exit 1
    fi

    # 检查集群连接
    if [ -n "$CONTEXT" ]; then
        kubectl use-context "$CONTEXT"
    fi

    if ! kubectl cluster-info &> /dev/null; then
        log_error "无法连接到Kubernetes集群"
        exit 1
    fi

    log_success "kubectl已就绪"
}

# 创建命名空间
create_namespace() {
    print_header "创建命名空间"

    kubectl apply -f "$K8S_DIR/namespace.yaml"
    log_success "命名空间已创建"
}

# 创建配置
create_config() {
    print_header "创建配置"

    kubectl apply -f "$K8S_DIR/configmap.yaml"
    kubectl apply -f "$K8S_DIR/secret.yaml"

    log_success "配置已创建"
}

# 部署应用
deploy_app() {
    print_header "部署应用"

    kubectl apply -f "$K8S_DIR/rbac.yaml"
    kubectl apply -f "$K8S_DIR/deployment.yaml"
    kubectl apply -f "$K8S_DIR/service.yaml"
    kubectl apply -f "$K8S_DIR/networkpolicy.yaml"
    kubectl apply -f "$K8S_DIR/pdb.yaml"

    log_success "应用已部署"
}

# 部署Ingress
deploy_ingress() {
    print_header "部署Ingress"

    kubectl apply -f "$K8S_DIR/ingress.yaml"

    log_success "Ingress已部署"
}

# 等待Pod就绪
wait_for_pods() {
    print_header "等待Pod就绪"

    log_info "等待部署完成..."
    kubectl wait --for=condition=available --timeout=300s \
        deployment/ocr-service -n "$NAMESPACE"

    log_success "所有Pod已就绪"
}

# 显示状态
show_status() {
    print_header "部署状态"

    echo ""
    kubectl get pods -n "$NAMESPACE"
    echo ""
    kubectl get services -n "$NAMESPACE"
    echo ""
    kubectl get ingress -n "$NAMESPACE" 2>/dev/null || true
}

# 显示访问信息
show_access_info() {
    print_header "访问信息"

    # 获取服务地址
    if kubectl get svc -n "$NAMESPACE" ocr-service &> /dev/null; then
        echo "服务已部署在命名空间: $NAMESPACE"
        echo ""
        echo "端口转发命令:"
        echo "  kubectl port-forward svc/ocr-service 8007:8007 -n $NAMESPACE"
        echo ""
        echo "然后访问: http://localhost:8007"
    fi

    # 检查Ingress
    if kubectl get ingress -n "$NAMESPACE" ocr-service-ingress &> /dev/null; then
        echo ""
        INGRESS_HOST=$(kubectl get ingress ocr-service-ingress -n "$NAMESPACE" -o jsonpath='{.spec.rules[0].host}' 2>/dev/null)
        if [ -n "$INGRESS_HOST" ]; then
            echo "Ingress地址: http://$INGRESS_HOST"
        fi
    fi
}

# 健康检查
health_check() {
    print_header "健康检查"

    # 端口转发进行健康检查
    log_info "启动端口转发..."
    kubectl port-forward svc/ocr-service 8007:8007 -n "$NAMESPACE" &
    PF_PID=$!

    sleep 5

    if curl -s http://localhost:8007/health | grep -q "healthy"; then
        log_success "健康检查通过"
    else
        log_warning "健康检查失败，请手动验证"
    fi

    kill $PF_PID 2>/dev/null || true
}

# 清理部署
cleanup() {
    print_header "清理部署"

    read -p "确定要删除所有资源吗? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        log_info "取消清理"
        return
    fi

    kubectl delete -f "$K8S_DIR/" || true
    log_success "资源已删除"
}

# 查看日志
view_logs() {
    print_header "查看日志"

    kubectl logs -f deployment/ocr-service -n "$NAMESPACE"
}

# 执行命令
exec_shell() {
    kubectl exec -it deployment/ocr-service -n "$NAMESPACE" -- bash
}

# 打印标题
print_header() {
    echo ""
    echo "================================"
    echo "  $1"
    echo "================================"
    echo ""
}

# 显示帮助
show_help() {
    cat << EOF
OCR服务Kubernetes部署脚本

用法: $0 [命令]

命令:
  deploy     完整部署
  status     查看状态
  logs       查看日志
  shell      进入容器Shell
  health     健康检查
  cleanup    清理部署
  help       显示帮助

示例:
  $0 deploy       # 部署到K8s
  $0 status       # 查看状态
  $0 logs         # 查看日志

环境变量:
  KUBECONTEXT  Kubernetes上下文
  NAMESPACE    命名空间 (默认: ocr-service)

EOF
}

# 主函数
main() {
    local command="${1:-help}"

    case "$command" in
        deploy)
            check_kubectl
            create_namespace
            create_config
            deploy_app
            deploy_ingress
            wait_for_pods
            show_status
            show_access_info
            health_check
            log_success "部署完成！"
            ;;
        status)
            show_status
            ;;
        logs)
            view_logs
            ;;
        shell)
            exec_shell
            ;;
        health)
            health_check
            ;;
        cleanup)
            cleanup
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
