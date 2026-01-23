#!/bin/bash
# install-kind.sh - 安装 Kind 本地 K8s 集群

set -e

CLUSTER_NAME="one-data"
KIND_VERSION="v0.20.0"
K8S_VERSION="v1.27.3"

echo "=== ONE-DATA-STUDIO Kind 集群安装 ==="

# 检查 Kind 是否已安装
if command -v kind &> /dev/null; then
    echo "Kind 已安装: $(kind version)"
else
    echo "安装 Kind..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install kind
    else
        curl -Lo ./kind "https://kind.sigs.k8s.io/dl/${KIND_VERSION}/kind-linux-amd64"
        chmod +x ./kind
        sudo mv ./kind /usr/local/bin/kind
    fi
fi

# 检查集群是否已存在
if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
    echo "集群 ${CLUSTER_NAME} 已存在"
    read -p "是否删除并重新创建? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "删除现有集群..."
        kind delete cluster --name ${CLUSTER_NAME}
    else
        echo "使用现有集群"
        exit 0
    fi
fi

# 创建集群
echo "创建 Kind 集群..."
kind create cluster --name ${CLUSTER_NAME} --config k8s/kind-config.yaml

# 等待节点就绪
echo "等待节点就绪..."
kubectl wait --for=condition=ready nodes --all --timeout=300s

# 安装 ingress-nginx (如果需要)
if ! kubectl get namespace ingress-nginx &> /dev/null; then
    echo "安装 Ingress NGINX..."
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/kind/deploy.yaml
fi

# 安装 Local Path Provisioner (存储)
if ! kubectl get storageclass local-path &> /dev/null; then
    echo "安装 Local Path Provisioner..."
    kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.24/deploy/local-path-storage.yaml
fi

# 设置默认 StorageClass
kubectl patch storageclass local-path -p '{"metadata":{"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}' 2>/dev/null || true

echo ""
echo "=== 集群安装完成 ==="
echo "集群名称: ${CLUSTER_NAME}"
echo ""
echo "验证集群:"
echo "  kubectl get nodes"
echo ""
echo "下一步:"
echo "  make install"
