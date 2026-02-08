#!/usr/bin/env python3
"""
ONE-DATA-STUDIO 健康检查脚本
检查所有 Docker 容器的健康状态和 HTTP 端点可用性
"""

import json
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
import subprocess
import urllib.request
import urllib.error


@dataclass
class ServiceStatus:
    """服务状态数据类"""
    name: str
    container: str
    status: str  # running, stopped, not_found
    health: str  # healthy, unhealthy, starting, no_healthcheck
    http_status: Optional[int] = None
    http_url: Optional[str] = None
    response_time: Optional[float] = None


class HealthChecker:
    """健康检查器"""

    # 服务定义
    SERVICES = {
        # 基础设施
        "mysql": "one-data-mysql",
        "redis": "one-data-redis",
        "minio": "one-data-minio",
        "etcd": "one-data-etcd",
        "elasticsearch": "one-data-elasticsearch",
        "milvus": "one-data-milvus",
        # 元数据
        "openmetadata": "one-data-openmetadata",
        # ETL
        "kettle": "one-data-kettle",
        "hop-server": "one-data-hop-server",
        # 认证
        "keycloak": "one-data-keycloak",
        # AI
        "vllm-chat": "one-data-vllm-chat",
        "vllm-embed": "one-data-vllm-embed",
        "ollama": "one-data-ollama",
        # 标注
        "label-studio": "one-data-label-studio",
        "label-studio-pg": "one-data-label-studio-pg",
        # 应用服务
        "agent-api": "one-data-agent-api",
        "data-api": "one-data-data-api",
        "model-api": "one-data-model-api",
        "openai-proxy": "one-data-openai-proxy",
        "admin-api": "one-data-admin-api",
        "ocr-service": "one-data-ocr-service",
        "behavior-service": "one-data-behavior-service",
        # 前端
        "web-frontend": "one-data-web",
        # 工作流
        "zookeeper": "one-data-zookeeper",
        "dolphinscheduler-pg": "one-data-dolphinscheduler-postgresql",
        "dolphinscheduler": "one-data-dolphinscheduler",
        # BI
        "superset-cache": "one-data-superset-cache",
        "superset": "one-data-superset",
        # 数据集成
        "seatunnel-zk": "one-data-seatunnel-zk",
        "seatunnel": "one-data-seatunnel",
    }

    # HTTP 健康检查端点
    HTTP_ENDPOINTS = {
        "openmetadata": ("http://localhost:8585/api/v1/system/version", None),
        "kettle": ("http://localhost:8080/spoon/spoon", None),
        "hop-server": ("http://localhost:8182/hop/status", None),
        "vllm-chat": ("http://localhost:8010/health", None),
        "vllm-embed": ("http://localhost:8011/health", None),
        "ollama": ("http://localhost:11434/api/tags", None),
        "label-studio": ("http://localhost:8009/health", None),
        "agent-api": ("http://localhost:8000/api/v1/health", None),
        "data-api": ("http://localhost:8001/api/v1/health", None),
        "model-api": ("http://localhost:8002/health", None),
        "openai-proxy": ("http://localhost:8003/health", None),
        "admin-api": ("http://localhost:8004/health", None),
        "ocr-service": ("http://localhost:8007/health", None),
        "behavior-service": ("http://localhost:8008/health", None),
        "web-frontend": ("http://localhost:3000", None),
        "dolphinscheduler": ("http://localhost:12345/dolphinscheduler/auth/login", None),
        "superset": ("http://localhost:8088/health", None),
        "seatunnel": ("http://localhost:5801", None),
    }

    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self.results: Dict[str, ServiceStatus] = {}

    def _run_command(self, cmd: List[str]) -> str:
        """运行命令并返回输出"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return ""

    def check_docker(self) -> None:
        """检查 Docker 容器状态"""
        # 获取所有容器状态
        for name, container in self.SERVICES.items():
            status = ServiceStatus(name=name, container=container, status="not_found", health="no_healthcheck")

            # 检查容器是否存在
            containers = self._run_command(["docker", "ps", "-a", "--format", "{{.Names}}"])
            if container not in containers:
                self.results[name] = status
                continue

            # 检查容器状态
            inspect = self._run_command([
                "docker", "inspect", "-f",
                "{{.State.Status}}",
                container
            ])
            status.status = inspect if inspect else "unknown"

            # 检查健康状态
            health = self._run_command([
                "docker", "inspect", "-f",
                "{{.State.Health.Status}}",
                container
            ])
            if health:
                status.health = health
            elif status.status == "running":
                status.health = "no_healthcheck"

            self.results[name] = status

    def check_http(self) -> None:
        """检查 HTTP 端点"""
        for name, (url, _) in self.HTTP_ENDPOINTS.items():
            if name not in self.results:
                self.results[name] = ServiceStatus(
                    name=name,
                    container="",
                    status="running",
                    health="no_healthcheck"
                )

            try:
                start = time.time()
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    self.results[name].http_status = response.status
                    self.results[name].http_url = url
                    self.results[name].response_time = round((time.time() - start) * 1000, 2)
            except urllib.error.HTTPError as e:
                self.results[name].http_status = e.code
                self.results[name].http_url = url
            except (urllib.error.URLError, Exception):
                self.results[name].http_url = url

    def print_results(self) -> None:
        """打印结果"""
        # ANSI 颜色
        GREEN = "\033[92m"
        YELLOW = "\033[93m"
        RED = "\033[91m"
        BLUE = "\033[94m"
        NC = "\033[0m"

        print(f"\n{BLUE}{'=' * 50}{NC}")
        print(f"{BLUE}ONE-DATA-STUDIO 健康检查{NC}")
        print(f"{BLUE}{'=' * 50}{NC}\n")

        healthy = unhealthy = starting = not_running = 0

        for name, status in self.results.items():
            # 容器状态图标
            if status.status == "running":
                if status.health == "healthy":
                    icon = f"{GREEN}✓{NC}"
                    healthy += 1
                elif status.health == "unhealthy":
                    icon = f"{RED}✗{NC}"
                    unhealthy += 1
                elif status.health == "starting":
                    icon = f"{YELLOW}○{NC}"
                    starting += 1
                else:
                    icon = f"{GREEN}✓{NC}"
                    healthy += 1
            else:
                icon = f"{RED}✗{NC}"
                not_running += 1

            # 打印状态
            container_info = f"({status.container})" if status.container else ""
            health_info = f"[{status.health}]" if status.health != "no_healthcheck" else ""

            line = f"{icon} {name:20} {container_info:30} {health_info:15}"

            # 添加 HTTP 状态
            if status.http_url:
                http_info = f"HTTP {status.http_status}" if status.http_status else "HTTP ---"
                if status.response_time:
                    http_info += f" ({status.response_time}ms)"
                line += f" {http_info}"

            print(line)

        # 汇总
        print(f"\n{BLUE}{'-' * 50}{NC}")
        print(f"总计: {len(self.results)} 个服务")
        print(f"{GREEN}健康: {healthy}{NC}")
        print(f"{YELLOW}启动中: {starting}{NC}")
        print(f"{RED}不健康/停止: {unhealthy + not_running}{NC}")
        print(f"{BLUE}{'-' * 50}{NC}\n")

        # 返回码
        if unhealthy + not_running > 0:
            print(f"{RED}部分服务不健康，请检查日志{NC}")
            print("使用以下命令查看日志:")
            print("  docker logs <container_name>")
            sys.exit(1)
        elif starting > 0:
            print(f"{YELLOW}部分服务正在启动中...{NC}")
            print("稍后重新运行此脚本检查")
            sys.exit(0)
        else:
            print(f"{GREEN}所有服务运行正常！{NC}")
            sys.exit(0)

    def run(self) -> None:
        """运行健康检查"""
        self.check_docker()
        self.check_http()
        self.print_results()


def main():
    """主函数"""
    checker = HealthChecker()
    checker.run()


if __name__ == "__main__":
    main()
