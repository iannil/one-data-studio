#!/bin/bash
# clean.sh - 清理所有资源

set -e

echo "=== ONE-DATA-STUDIO 清理脚本 ==="

# 停止端口转发
echo "停止端口转发..."
pkill -f "port-forward.*one-data" 2>/dev/null || true
rm -f /tmp/one-data-port-forward-pids.txt 2>/dev/null || true

# 删除 K8s 资源
if kubectl get namespace one-data-system &> /dev/null; then
    echo "删除应用服务..."
    kubectl delete -f k8s/applications/ --ignore-not-found=true

    echo "删除基础设施..."
    kubectl delete -f k8s/infrastructure/ --ignore-not-found=true

    echo "删除基础资源..."
    kubectl delete -f k8s/base/ --ignore-not-found=true
else
    echo "K8s 资源未部署，跳过删除"
fi

# 询问是否删除 Kind 集群
if kind get clusters | grep -q "^one-data$"; then
    echo ""
    read -p "是否删除 Kind 集群? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "删除 Kind 集群..."
        kind delete cluster --name one-data
    fi
fi

# 清理 Docker 资源（可选）
echo ""
read -p "是否清理 Docker 资源? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "清理 Docker 资源..."
    docker-compose down -v 2>/dev/null || true
    docker system prune -f
fi

echo ""
echo "=== 清理完成 ==="
