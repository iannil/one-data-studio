#!/bin/bash
# port-forward.sh - 启动所有服务的端口转发

set -e

echo "=== ONE-DATA-STUDIO 端口转发 ==="

# 清理可能存在的旧进程
pkill -f "port-forward.*one-data" 2>/dev/null || true
sleep 2

# 启动端口转发
echo "启动端口转发..."

# Alldata API
kubectl port-forward -n one-data-alldata svc/alldata-api 8080:8080 &
PF_PID1=$!
echo "  Alldata API:  http://localhost:8080 (PID: $PF_PID1)"

# Cube vLLM
kubectl port-forward -n one-data-cube svc/vllm-serving 8000:8000 &
PF_PID2=$!
echo "  Cube API:     http://localhost:8000 (PID: $PF_PID2)"

# Bisheng API
kubectl port-forward -n one-data-bisheng svc/bisheng-api 8081:8080 &
PF_PID3=$!
echo "  Bisheng API:  http://localhost:8081 (PID: $PF_PID3)"

# MinIO Console
kubectl port-forward -n one-data-infra svc/minio 9001:9001 &
PF_PID4=$!
echo "  MinIO Console: http://localhost:9001 (admin/admin123456) (PID: $PF_PID4)"

# Grafana
if kubectl get svc -n one-data-system grafana &> /dev/null; then
    kubectl port-forward -n one-data-system svc/grafana 3000:3000 &
    PF_PID5=$!
    echo "  Grafana:      http://localhost:3000 (admin/admin123) (PID: $PF_PID5)"
fi

# 保存 PID 以便后续清理
echo $PF_PID1 $PF_PID2 $PF_PID3 $PF_PID4 > /tmp/one-data-port-forward-pids.txt

echo ""
echo "端口转发已启动"
echo "按 Ctrl+C 停止所有转发"

# 等待中断信号
trap "kill $(cat /tmp/one-data-port-forward-pids.txt) 2>/dev/null; rm /tmp/one-data-port-forward-pids.txt; echo '端口转发已停止'; exit 0" SIGINT SIGTERM

# 保持脚本运行
wait
