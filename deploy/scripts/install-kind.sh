#!/bin/bash
# ONE-DATA-STUDIO Kind Cluster 安装脚本
# 创建本地 Kubernetes 开发集群

set -e

CLUSTER_NAME="${CLUSTER_NAME:-one-data}"
KIND_CONFIG="deploy/kubernetes/kind-config.yaml"

echo "==> ONE-DATA-STUDIO Kind 集群安装脚本"
echo ""

# 检查 Kind 是否安装
if ! command -v kind &> /dev/null; then
    echo "错误: Kind 未安装"
    echo "请先安装 Kind: https://kind.sigs.k8s.io/docs/user/quick-start/#installation"
    echo ""
    echo "macOS:   brew install kind"
    echo "Linux:   curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64 && chmod +x ./kind && sudo mv ./kind /usr/local/bin/kind"
    exit 1
fi

# 检查 kubectl 是否安装
if ! command -v kubectl &> /dev/null; then
    echo "错误: kubectl 未安装"
    echo "请先安装 kubectl: https://kubernetes.io/docs/tasks/tools/"
    exit 1
fi

# 检查 Docker 是否运行
if ! docker info &> /dev/null; then
    echo "错误: Docker 未运行"
    echo "请先启动 Docker"
    exit 1
fi

# 检查集群是否已存在
if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
    echo "==> 集群 '${CLUSTER_NAME}' 已存在"
    read -p "是否删除并重新创建? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "==> 删除现有集群..."
        kind delete cluster --name "${CLUSTER_NAME}"
    else
        echo "==> 使用现有集群"
        kubectl cluster-info --context "kind-${CLUSTER_NAME}"
        exit 0
    fi
fi

# 创建集群
echo "==> 创建 Kind 集群: ${CLUSTER_NAME}"
if [ -f "${KIND_CONFIG}" ]; then
    echo "==> 使用配置文件: ${KIND_CONFIG}"
    kind create cluster --name "${CLUSTER_NAME}" --config "${KIND_CONFIG}"
else
    echo "==> 使用默认配置"
    kind create cluster --name "${CLUSTER_NAME}"
fi

# 验证集群
echo ""
echo "==> 验证集群..."
kubectl cluster-info --context "kind-${CLUSTER_NAME}"

# 创建命名空间
echo ""
echo "==> 创建命名空间..."
kubectl apply -f deploy/kubernetes/base/namespaces.yaml || true

echo ""
echo "==> Kind 集群创建成功!"
echo ""
echo "集群信息:"
echo "  名称:    ${CLUSTER_NAME}"
echo "  上下文:  kind-${CLUSTER_NAME}"
echo ""
echo "下一步:"
echo "  make install-infra  # 安装基础设施"
echo "  make install-apps   # 安装应用服务"
echo "  make status         # 查看状态"
