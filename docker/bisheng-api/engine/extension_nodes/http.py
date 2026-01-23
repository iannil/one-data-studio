"""
HTTP 请求节点
Phase 6: Sprint 6.1

支持对外部 REST API 的调用，实现工作流与第三方服务的集成。
"""

import json
import re
from typing import Any, Dict, List, Optional


class HTTPNodeImpl:
    """HTTP 请求节点实现

    向外部 REST API 发起请求，支持各种 HTTP 方法和配置。

    配置参数：
    - url: 请求 URL，支持变量插值 (如: https://api.example.com/{{input.id}})
    - method: HTTP 方法 (GET, POST, PUT, DELETE, PATCH)
    - headers: 请求头字典
    - body: 请求体 (JSON 格式，用于 POST/PUT/PATCH)
    - query_params: URL 查询参数
    - timeout: 超时时间（毫秒，默认 30000）
    - retry: 重试次数（默认 0）
    - retry_delay: 重试延迟（毫秒，默认 1000）
    - auth: 认证配置 ({"type": "bearer", "token": "..."} 或 {"type": "basic", "username": "...", "password": "..."})
    - response_format: 响应处理格式 (json, text, auto)
    - success_codes: 视为成功的状态码列表 (默认: [200, 201, 202, 204])
    - output_path: 从响应中提取值的 JSONPath (如: $.data.items[0])

    例如：
    ```json
    {
      "type": "http",
      "config": {
        "url": "https://api.example.com/users/{{inputs.user_id}}",
        "method": "GET",
        "headers": {
          "Authorization": "Bearer {{secrets.api_key}}",
          "Content-Type": "application/json"
        },
        "timeout": 30000,
        "retry": 3
      }
    }
    ```

    POST 请求示例：
    ```json
    {
      "type": "http",
      "config": {
        "url": "https://api.example.com/search",
        "method": "POST",
        "headers": {
          "Content-Type": "application/json"
        },
        "body": {
          "query": "{{inputs.query}}",
          "limit": 10
        },
        "response_format": "json"
      }
    }
    ```
    """

    def __init__(self, node_id: str, config: Dict[str, Any] = None):
        self.node_id = node_id
        self.node_type = "http"
        self.config = config or {}
        self.url_template = config.get("url", "")
        self.method = config.get("method", "GET").upper()
        self.headers_template = config.get("headers", {})
        self.body_template = config.get("body", {})
        self.query_params_template = config.get("query_params", {})
        self.timeout = config.get("timeout", 30000) / 1000  # 转换为秒
        self.retry = config.get("retry", 0)
        self.retry_delay = config.get("retry_delay", 1000) / 1000  # 转换为秒
        self.auth = config.get("auth", {})
        self.response_format = config.get("response_format", "auto")
        self.success_codes = config.get("success_codes", [200, 201, 202, 204])
        self.output_path = config.get("output_path", "")
        self.follow_redirects = config.get("follow_redirects", True)
        self.verify_ssl = config.get("verify_ssl", True)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行 HTTP 请求"""
        import asyncio
        import httpx

        # 渲染模板
        url = self._render_template(self.url_template, context)
        headers = self._render_dict(self.headers_template, context)
        body = self._render_dict(self.body_template, context)
        query_params = self._render_dict(self.query_params_template, context)

        # 处理认证
        auth = self._prepare_auth(context)

        # 准备请求参数
        request_params = {
            "method": self.method,
            "url": url,
            "headers": headers,
            "timeout": self.timeout,
            "follow_redirects": self.follow_redirects,
            "verify": self.verify_ssl,
        }

        # 添加查询参数
        if query_params:
            request_params["params"] = query_params

        # 添加请求体
        if self.method in ["POST", "PUT", "PATCH"] and body:
            content_type = headers.get("Content-Type", headers.get("content-type", ""))
            if "application/json" in content_type:
                request_params["json"] = body
            elif "application/x-www-form-urlencoded" in content_type:
                request_params["data"] = body
            else:
                request_params["content"] = json.dumps(body) if isinstance(body, dict) else body

        # 添加认证
        if auth:
            if auth["type"] == "bearer":
                request_params["headers"]["Authorization"] = f"Bearer {auth['token']}"
            elif auth["type"] == "basic":
                import base64
                credentials = base64.b64encode(
                    f"{auth['username']}:{auth['password']}".encode()
                ).decode()
                request_params["headers"]["Authorization"] = f"Basic {credentials}"
            elif auth["type"] == "api_key":
                key_header = auth.get("header", "X-API-Key")
                request_params["headers"][key_header] = auth["key"]

        # 执行请求（带重试）
        response_data = await self._execute_with_retry(request_params, self.retry)

        # 提取输出路径
        output = self._extract_output(response_data, self.output_path)

        return {
            self.node_id: {
                "output": output,
                "status_code": response_data.get("status_code"),
                "headers": response_data.get("headers", {}),
                "success": response_data.get("status_code", 0) in self.success_codes,
                "url": url,
                "method": self.method
            }
        }

    async def _execute_with_retry(
        self, request_params: Dict[str, Any], max_retries: int
    ) -> Dict[str, Any]:
        """执行请求并支持重试"""
        import httpx

        last_error = None
        attempt = 0

        while attempt <= max_retries:
            attempt += 1

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.request(**request_params)

                    # 解析响应
                    response_data = {
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                    }

                    # 根据格式解析响应体
                    content_type = response.headers.get("content-type", "")

                    if self.response_format == "json" or (
                        self.response_format == "auto" and "application/json" in content_type
                    ):
                        try:
                            response_data["data"] = response.json()
                        except json.JSONDecodeError:
                            response_data["data"] = response.text
                            response_data["raw"] = response.text
                    else:
                        response_data["data"] = response.text
                        response_data["raw"] = response.text

                    # 如果是成功状态码或客户端错误（4xx），不重试
                    if response.status_code < 500 or attempt > max_retries:
                        return response_data

                    last_error = f"HTTP {response.status_code}: {response.text}"

            except httpx.TimeoutException as e:
                last_error = f"Timeout: {str(e)}"
            except httpx.ConnectError as e:
                last_error = f"Connection error: {str(e)}"
            except Exception as e:
                last_error = f"Request error: {str(e)}"

            # 如果还有重试机会，等待后重试
            if attempt <= max_retries:
                await asyncio.sleep(self.retry_delay)

        # 所有重试都失败
        return {
            "status_code": 503,
            "headers": {},
            "data": None,
            "error": last_error,
            "raw": last_error
        }

    def _render_template(self, template: str, context: Dict[str, Any]) -> str:
        """渲染模板字符串，支持变量插值"""
        if not template:
            return template

        def replace_var(match):
            var_path = match.group(1).strip()
            value = self._get_value(var_path, context)
            return str(value) if value is not None else ""

        pattern = r'\{\{\s*([^\}]+)\s*\}\}'
        return re.sub(pattern, replace_var, template)

    def _render_dict(self, data: Any, context: Dict[str, Any]) -> Any:
        """递归渲染字典或列表中的模板"""
        if isinstance(data, str):
            return self._render_template(data, context)
        elif isinstance(data, dict):
            return {k: self._render_dict(v, context) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._render_dict(item, context) for item in data]
        return data

    def _get_value(self, path: str, context: Dict[str, Any]) -> Any:
        """从上下文中获取值"""
        parts = path.split('.')

        # 处理 inputs 前缀
        if parts[0] == "inputs":
            initial_input = context.get("_initial_input", {})
            if len(parts) == 1:
                return initial_input
            return self._get_nested_value(initial_input, parts[1:])

        # 处理 secrets 前缀（从环境变量获取）
        if parts[0] == "secrets":
            import os
            if len(parts) == 2:
                return os.getenv(parts[1].upper(), os.getenv(parts[1], ""))
            return None

        # 处理 env 前缀
        if parts[0] == "env":
            import os
            if len(parts) == 2:
                return os.getenv(parts[1], "")
            return None

        # 处理从节点获取
        if parts[0] in context:
            node_output = context[parts[0]]
            if len(parts) == 1:
                return node_output.get("output", node_output)
            return self._get_nested_value(node_output, parts[1:])

        # 直接从上下文获取
        return self._get_nested_value(context, parts)

    def _get_nested_value(self, data: Any, path: List[str]) -> Any:
        """从嵌套结构中获取值"""
        current = data
        for key in path:
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list) and key.isdigit():
                idx = int(key)
                current = current[idx] if 0 <= idx < len(current) else None
            else:
                return None
            if current is None:
                return None
        return current

    def _prepare_auth(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """准备认证配置"""
        if not self.auth:
            return None

        auth_type = self.auth.get("type", "")

        if auth_type == "bearer":
            token = self._render_template(self.auth.get("token", ""), context)
            return {"type": "bearer", "token": token}
        elif auth_type == "basic":
            username = self._render_template(self.auth.get("username", ""), context)
            password = self._render_template(self.auth.get("password", ""), context)
            return {"type": "basic", "username": username, "password": password}
        elif auth_type == "api_key":
            key = self._render_template(self.auth.get("key", ""), context)
            return {"type": "api_key", "key": key, "header": self.auth.get("header", "X-API-Key")}

        return None

    def _extract_output(self, response_data: Dict[str, Any], path: str) -> Any:
        """从响应中提取指定的值"""
        data = response_data.get("data")

        if not path:
            return data

        # 简单的 JSONPath 实现
        # 移除 $. 前缀
        if path.startswith("$."):
            path = path[2:]

        if not path:
            return data

        # 分割路径
        parts = self._parse_path(path)

        return self._get_nested_value(data, parts)

    def _parse_path(self, path: str) -> List[str]:
        """解析 JSONPath 路径"""
        parts = []
        current = ""

        i = 0
        while i < len(path):
            char = path[i]

            if char == '.':
                if current:
                    parts.append(current)
                    current = ""
                i += 1
            elif char == '[':
                if current:
                    parts.append(current)
                    current = ""
                # 找到匹配的 ]
                j = i + 1
                while j < len(path) and path[j] != ']':
                    j += 1
                if j < len(path):
                    # 提取索引
                    index = path[i+1:j].strip('\'"')
                    parts.append(index)
                    i = j + 1
                else:
                    current += char
                    i += 1
            else:
                current += char
                i += 1

        if current:
            parts.append(current)

        return parts

    def validate(self) -> bool:
        """验证节点配置"""
        if not self.url_template:
            return False
        if self.method not in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]:
            return False
        return True
