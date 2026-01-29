#!/bin/bash
# ONE-DATA-STUDIO 端口转发脚本
# 将 K8s 服务端口转发到本地

set -e

PID_FILE="/tmp/one-data-port-forward-pids.txt"

echo "==> ONE-DATA-STUDIO 端口转发"
echo ""

# 清理旧的端口转发进程
cleanup() {
    echo "==> 清理端口转发进程..."
    if [ -f "${PID_FILE}" ]; then
        while read -r pid; do
            if kill -0 "${pid}" 2>/dev/null; then
                kill "${pid}" 2>/dev/null || true
            fi
        done < "${PID_FILE}"
        rm -f "${PID_FILE}"
    fi
    pkill -f "kubectl port-forward.*one-data" 2>/dev/null || true
}

# 捕获退出信号
trap cleanup EXIT INT TERM

# 清理旧进程
cleanup

# 创建 PID 文件
touch "${PID_FILE}"

# 端口转发配置
# 格式: "本地端口:服务端口:命名空间:服务名"
declare -a FORWARDS=(
    "8000:8000:one-data-agent:agent-api"
    "8001:8001:one-data-data:data-api"
    "8002:8002:one-data-model:model-api"
    "8003:8000:one-data-openai:openai-proxy"
    "3000:80:one-data-web:web-frontend"
    "9001:9001:one-data-infra:minio"
)

echo "==> 启动端口转发..."
for forward in "${FORWARDS[@]}"; do
    IFS=':' read -r local_port svc_port namespace service <<< "${forward}"

    # 检查服务是否存在
    if kubectl get svc "${service}" -n "${namespace}" &>/dev/null; then
        echo "  ${service} (${namespace}) -> localhost:${local_port}"
        kubectl port-forward -n "${namespace}" "svc/${service}" "${local_port}:${svc_port}" &>/dev/null &
        echo $! >> "${PID_FILE}"
    else
        echo "  跳过 ${service} (服务不存在)"
    fi
done

echo ""
echo "==> 端口转发已启动"
echo ""
echo "访问地址:"
echo "  Bisheng API:  http://localhost:8000"
echo "  Alldata API:  http://localhost:8001"
echo "  Cube API:     http://localhost:8002"
echo "  OpenAI Proxy: http://localhost:8003"
echo "  Web Frontend: http://localhost:3000"
echo "  MinIO:        http://localhost:9001"
echo ""
echo "按 Ctrl+C 停止端口转发"
echo ""

# 保持脚本运行
wait
