#!/bin/bash
# ONE-DATA-STUDIO 资源清理脚本
# 删除所有 K8s 资源

set -e

echo "==> ONE-DATA-STUDIO 资源清理"
echo ""

# 确认提示
read -p "确定要删除所有 ONE-DATA-STUDIO K8s 资源吗? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "==> 取消清理"
    exit 0
fi

echo ""
echo "==> 删除应用服务..."
kubectl delete -f deploy/kubernetes/applications/ --ignore-not-found=true --recursive 2>/dev/null || true

echo "==> 删除 Jobs..."
kubectl delete -f deploy/kubernetes/jobs/ --ignore-not-found=true 2>/dev/null || true

echo "==> 删除基础设施..."
kubectl delete -f deploy/kubernetes/infrastructure/ --ignore-not-found=true --recursive 2>/dev/null || true

echo "==> 删除 PVC (持久化数据)..."
for ns in one-data-data one-data-agent one-data-model one-data-infra one-data-web one-data-monitoring; do
    if kubectl get namespace "${ns}" &>/dev/null; then
        kubectl delete pvc --all -n "${ns}" --ignore-not-found=true 2>/dev/null || true
    fi
done

echo "==> 删除基础资源..."
kubectl delete -f deploy/kubernetes/base/ --ignore-not-found=true 2>/dev/null || true

# 删除命名空间
echo "==> 删除命名空间..."
for ns in one-data-data one-data-agent one-data-model one-data-infra one-data-web one-data-monitoring one-data-system; do
    kubectl delete namespace "${ns}" --ignore-not-found=true 2>/dev/null || true
done

# 停止端口转发
echo "==> 停止端口转发..."
pkill -f "kubectl port-forward.*one-data" 2>/dev/null || true
rm -f /tmp/one-data-port-forward-pids.txt 2>/dev/null || true

echo ""
echo "==> 清理完成"
echo ""
echo "注意: Kind 集群未删除，如需删除请运行:"
echo "  kind delete cluster --name one-data"
