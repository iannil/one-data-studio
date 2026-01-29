"""
阿里云函数计算 (Function Compute) 适配器

提供模型推理服务部署到阿里云函数计算的能力，支持：
- 函数服务管理（创建、更新、删除）
- HTTP 触发器配置
- 模型推理一键部署
- 同步/异步调用
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)

# 模块级别的单例实例
_adapter_instance: Optional["AliyunFCAdapter"] = None


@dataclass
class AliyunFCConfig:
    """阿里云函数计算配置"""

    region: str  # 地域，如 "cn-shanghai"
    access_key_id: str  # AccessKey ID
    access_key_secret: str  # AccessKey Secret
    account_id: str  # 阿里云账号 ID
    service_name: str  # 函数计算服务名称
    timeout: int = 60  # 函数执行超时时间（秒）
    memory_size: int = 3072  # 内存大小（MB）
    concurrency: int = 10  # 单实例并发度

    @property
    def endpoint(self) -> str:
        """获取函数计算 API 端点"""
        return f"https://{self.account_id}.{self.region}.fc.aliyuncs.com"

    @classmethod
    def from_env(cls) -> "AliyunFCConfig":
        """从环境变量创建配置"""
        return cls(
            region=os.getenv("ALIYUN_FC_REGION", "cn-shanghai"),
            access_key_id=os.getenv("ALIYUN_ACCESS_KEY_ID", ""),
            access_key_secret=os.getenv("ALIYUN_ACCESS_KEY_SECRET", ""),
            account_id=os.getenv("ALIYUN_ACCOUNT_ID", ""),
            service_name=os.getenv("ALIYUN_FC_SERVICE_NAME", "model-inference"),
            timeout=int(os.getenv("ALIYUN_FC_TIMEOUT", "60")),
            memory_size=int(os.getenv("ALIYUN_FC_MEMORY_SIZE", "3072")),
            concurrency=int(os.getenv("ALIYUN_FC_CONCURRENCY", "10")),
        )


class AliyunFCError(Exception):
    """阿里云函数计算错误"""

    def __init__(self, message: str, status_code: int = None, response: Dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response or {}


class AliyunFCAdapter:
    """
    阿里云函数计算适配器

    提供模型推理服务部署到函数计算的完整功能，包括：
    - 服务和函数的 CRUD 操作
    - HTTP 触发器管理
    - 模型推理一键部署

    使用示例:
        config = AliyunFCConfig(
            region="cn-shanghai",
            access_key_id="your-key-id",
            access_key_secret="your-key-secret",
            account_id="your-account-id",
            service_name="model-inference"
        )
        adapter = AliyunFCAdapter(config)

        # 部署模型推理服务
        result = adapter.deploy_model_inference(
            model_name="bert-classifier",
            model_path="/models/bert",
            inference_handler="handler.inference"
        )
    """

    # FC API 版本
    API_VERSION = "2016-08-15"

    def __init__(self, config: AliyunFCConfig):
        """
        初始化适配器

        Args:
            config: 阿里云函数计算配置
        """
        self.config = config
        self._session = requests.Session()

        # 验证配置
        if not config.access_key_id or not config.access_key_secret:
            logger.warning("阿里云 AccessKey 未配置，API 调用可能失败")

        logger.info(f"阿里云函数计算适配器初始化完成，服务名: {config.service_name}")

    def _sign_request(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        body: bytes = b""
    ) -> str:
        """
        生成阿里云 API 签名

        使用 HMAC-SHA256 算法对请求进行签名，符合阿里云 API 签名规范。

        Args:
            method: HTTP 方法（GET, POST, PUT, DELETE）
            path: 请求路径
            headers: 请求头
            body: 请求体（用于计算 Content-MD5）

        Returns:
            签名字符串
        """
        # 计算 Content-MD5
        content_md5 = ""
        if body:
            md5_hash = hashlib.md5(body).digest()
            content_md5 = base64.b64encode(md5_hash).decode("utf-8")

        # 构建规范化请求
        content_type = headers.get("Content-Type", "")
        date = headers.get("Date", "")

        # 构建 CanonicalizedFCHeaders
        fc_headers = {}
        for key, value in headers.items():
            lower_key = key.lower()
            if lower_key.startswith("x-fc-"):
                fc_headers[lower_key] = value

        canonicalized_fc_headers = ""
        if fc_headers:
            sorted_headers = sorted(fc_headers.items())
            canonicalized_fc_headers = "\n".join(
                f"{k}:{v}" for k, v in sorted_headers
            )

        # 构建 CanonicalizedResource
        canonicalized_resource = path

        # 构建待签名字符串
        string_to_sign_parts = [
            method.upper(),
            content_md5,
            content_type,
            date,
        ]

        if canonicalized_fc_headers:
            string_to_sign_parts.append(canonicalized_fc_headers)

        string_to_sign_parts.append(canonicalized_resource)
        string_to_sign = "\n".join(string_to_sign_parts)

        # 使用 HMAC-SHA256 计算签名
        signature = hmac.new(
            self.config.access_key_secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256
        ).digest()

        return base64.b64encode(signature).decode("utf-8")

    def _make_request(
        self,
        method: str,
        path: str,
        body: Dict = None,
        raw_body: bytes = None
    ) -> Dict:
        """
        发送认证后的 HTTP 请求到函数计算 API

        Args:
            method: HTTP 方法
            path: API 路径（不包含域名）
            body: 请求体（字典，会被序列化为 JSON）
            raw_body: 原始请求体（字节，用于二进制数据）

        Returns:
            API 响应（字典）

        Raises:
            AliyunFCError: API 调用失败时抛出
        """
        url = f"{self.config.endpoint}{path}"

        # 准备请求体
        if raw_body is not None:
            body_bytes = raw_body
            content_type = "application/octet-stream"
        elif body is not None:
            body_bytes = json.dumps(body).encode("utf-8")
            content_type = "application/json"
        else:
            body_bytes = b""
            content_type = "application/json"

        # 构建请求头
        date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
        headers = {
            "Content-Type": content_type,
            "Date": date,
            "x-fc-account-id": self.config.account_id,
        }

        # 计算签名
        signature = self._sign_request(method, path, headers, body_bytes)
        headers["Authorization"] = f"FC {self.config.access_key_id}:{signature}"

        # 发送请求
        try:
            response = self._session.request(
                method=method,
                url=url,
                headers=headers,
                data=body_bytes if body_bytes else None,
                timeout=30
            )

            # 解析响应
            if response.status_code >= 400:
                error_data = {}
                try:
                    error_data = response.json()
                except Exception:
                    error_data = {"message": response.text}

                error_msg = error_data.get("ErrorMessage", error_data.get("message", "未知错误"))
                logger.error(f"函数计算 API 调用失败: {response.status_code} - {error_msg}")
                raise AliyunFCError(
                    message=error_msg,
                    status_code=response.status_code,
                    response=error_data
                )

            # 返回响应数据
            if response.content:
                try:
                    return response.json()
                except Exception:
                    return {"data": response.text}
            return {}

        except requests.RequestException as e:
            logger.error(f"函数计算 API 请求异常: {e}")
            raise AliyunFCError(f"请求失败: {e}")

    def create_service(self, description: str = "") -> Dict:
        """
        创建函数计算服务

        如果服务已存在，则返回现有服务信息。

        Args:
            description: 服务描述

        Returns:
            服务信息字典，包含 serviceName, serviceId 等
        """
        logger.info(f"创建函数计算服务: {self.config.service_name}")

        # 先检查服务是否存在
        try:
            existing = self._make_request(
                "GET",
                f"/{self.API_VERSION}/services/{self.config.service_name}"
            )
            logger.info(f"服务已存在: {self.config.service_name}")
            return existing
        except AliyunFCError as e:
            if e.status_code != 404:
                raise

        # 创建新服务
        body = {
            "serviceName": self.config.service_name,
            "description": description or f"模型推理服务 - {self.config.service_name}",
        }

        result = self._make_request(
            "POST",
            f"/{self.API_VERSION}/services",
            body=body
        )

        logger.info(f"服务创建成功: {result.get('serviceName')}")
        return result

    def create_function(
        self,
        function_name: str,
        handler: str,
        runtime: str = "python3.10",
        code_dir: str = None,
        code_oss_bucket: str = None,
        code_oss_key: str = None,
        environment_variables: Dict = None
    ) -> Dict:
        """
        创建函数

        支持从本地目录或 OSS 部署代码。

        Args:
            function_name: 函数名称
            handler: 函数入口（如 "handler.inference"）
            runtime: 运行时环境（python3.10, python3.9 等）
            code_dir: 本地代码目录路径
            code_oss_bucket: OSS Bucket 名称（与 code_dir 二选一）
            code_oss_key: OSS 对象 Key
            environment_variables: 环境变量

        Returns:
            函数信息字典
        """
        logger.info(f"创建函数: {function_name}")

        body = {
            "functionName": function_name,
            "handler": handler,
            "runtime": runtime,
            "timeout": self.config.timeout,
            "memorySize": self.config.memory_size,
            "instanceConcurrency": self.config.concurrency,
        }

        # 设置环境变量
        if environment_variables:
            body["environmentVariables"] = environment_variables

        # 处理代码来源
        if code_dir:
            # 从本地目录打包上传
            code_zip = self._pack_code_dir(code_dir)
            body["code"] = {
                "zipFile": base64.b64encode(code_zip).decode("utf-8")
            }
        elif code_oss_bucket and code_oss_key:
            # 从 OSS 获取代码
            body["code"] = {
                "ossBucketName": code_oss_bucket,
                "ossObjectName": code_oss_key
            }
        else:
            raise AliyunFCError("必须指定 code_dir 或 (code_oss_bucket, code_oss_key)")

        result = self._make_request(
            "POST",
            f"/{self.API_VERSION}/services/{self.config.service_name}/functions",
            body=body
        )

        logger.info(f"函数创建成功: {result.get('functionName')}")
        return result

    def _pack_code_dir(self, code_dir: str) -> bytes:
        """
        将代码目录打包为 ZIP 文件

        Args:
            code_dir: 代码目录路径

        Returns:
            ZIP 文件的字节内容
        """
        if not os.path.isdir(code_dir):
            raise AliyunFCError(f"代码目录不存在: {code_dir}")

        # 创建临时 ZIP 文件
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(code_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, code_dir)
                        zf.write(file_path, arc_name)

            with open(tmp_path, "rb") as f:
                return f.read()
        finally:
            os.unlink(tmp_path)

    def update_function(self, function_name: str, **updates) -> Dict:
        """
        更新函数配置

        Args:
            function_name: 函数名称
            **updates: 要更新的配置项，支持:
                - handler: 函数入口
                - runtime: 运行时
                - timeout: 超时时间
                - memorySize: 内存大小
                - instanceConcurrency: 并发度
                - environmentVariables: 环境变量
                - code_dir: 新代码目录

        Returns:
            更新后的函数信息
        """
        logger.info(f"更新函数: {function_name}")

        body = {}

        # 处理标准配置项
        allowed_fields = [
            "handler", "runtime", "timeout", "memorySize",
            "instanceConcurrency", "environmentVariables", "description"
        ]
        for field in allowed_fields:
            if field in updates:
                body[field] = updates[field]

        # 处理代码更新
        if "code_dir" in updates:
            code_zip = self._pack_code_dir(updates["code_dir"])
            body["code"] = {
                "zipFile": base64.b64encode(code_zip).decode("utf-8")
            }

        if not body:
            logger.warning("没有需要更新的配置项")
            return self._make_request(
                "GET",
                f"/{self.API_VERSION}/services/{self.config.service_name}/functions/{function_name}"
            )

        result = self._make_request(
            "PUT",
            f"/{self.API_VERSION}/services/{self.config.service_name}/functions/{function_name}",
            body=body
        )

        logger.info(f"函数更新成功: {function_name}")
        return result

    def delete_function(self, function_name: str) -> bool:
        """
        删除函数

        Args:
            function_name: 函数名称

        Returns:
            是否删除成功
        """
        logger.info(f"删除函数: {function_name}")

        try:
            self._make_request(
                "DELETE",
                f"/{self.API_VERSION}/services/{self.config.service_name}/functions/{function_name}"
            )
            logger.info(f"函数删除成功: {function_name}")
            return True
        except AliyunFCError as e:
            if e.status_code == 404:
                logger.warning(f"函数不存在: {function_name}")
                return True
            raise

    def invoke_function(
        self,
        function_name: str,
        payload: Dict,
        async_mode: bool = False
    ) -> Dict:
        """
        调用函数

        Args:
            function_name: 函数名称
            payload: 调用参数
            async_mode: 是否异步调用

        Returns:
            函数执行结果
        """
        logger.info(f"调用函数: {function_name}, 异步模式: {async_mode}")

        path = f"/{self.API_VERSION}/services/{self.config.service_name}/functions/{function_name}/invocations"

        # 构建请求
        url = f"{self.config.endpoint}{path}"
        body_bytes = json.dumps(payload).encode("utf-8")

        date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
        headers = {
            "Content-Type": "application/json",
            "Date": date,
            "x-fc-account-id": self.config.account_id,
        }

        # 设置调用类型
        if async_mode:
            headers["x-fc-invocation-type"] = "Async"
        else:
            headers["x-fc-invocation-type"] = "Sync"

        # 计算签名
        signature = self._sign_request("POST", path, headers, body_bytes)
        headers["Authorization"] = f"FC {self.config.access_key_id}:{signature}"

        try:
            response = self._session.post(
                url,
                headers=headers,
                data=body_bytes,
                timeout=self.config.timeout + 10  # 额外 10 秒网络缓冲
            )

            if response.status_code >= 400:
                raise AliyunFCError(
                    message=f"函数调用失败: {response.text}",
                    status_code=response.status_code
                )

            # 解析响应
            if async_mode:
                return {
                    "requestId": response.headers.get("x-fc-request-id"),
                    "status": "async_invoked"
                }

            try:
                return response.json()
            except Exception:
                return {"result": response.text}

        except requests.RequestException as e:
            logger.error(f"函数调用异常: {e}")
            raise AliyunFCError(f"函数调用失败: {e}")

    def create_http_trigger(
        self,
        function_name: str,
        trigger_name: str = "http-trigger",
        methods: List[str] = None
    ) -> Dict:
        """
        创建 HTTP 触发器

        为函数配置 HTTP 触发器，使其可通过 REST API 访问。

        Args:
            function_name: 函数名称
            trigger_name: 触发器名称
            methods: 允许的 HTTP 方法列表，默认 ["GET", "POST"]

        Returns:
            触发器信息
        """
        logger.info(f"创建 HTTP 触发器: {function_name}/{trigger_name}")

        if methods is None:
            methods = ["GET", "POST"]

        body = {
            "triggerName": trigger_name,
            "triggerType": "http",
            "triggerConfig": {
                "authType": "anonymous",  # 匿名访问，生产环境建议使用 "function"
                "methods": methods
            }
        }

        result = self._make_request(
            "POST",
            f"/{self.API_VERSION}/services/{self.config.service_name}/functions/{function_name}/triggers",
            body=body
        )

        logger.info(f"HTTP 触发器创建成功: {trigger_name}")
        return result

    def get_function_url(self, function_name: str) -> str:
        """
        获取函数的公网调用 URL

        Args:
            function_name: 函数名称

        Returns:
            函数调用 URL
        """
        # HTTP 触发器的标准 URL 格式
        url = (
            f"https://{self.config.account_id}.{self.config.region}.fc.aliyuncs.com"
            f"/{self.API_VERSION}/proxy/{self.config.service_name}/{function_name}/"
        )
        return url

    def deploy_model_inference(
        self,
        model_name: str,
        model_path: str,
        inference_handler: str = "handler.inference"
    ) -> Dict:
        """
        一键部署模型推理服务

        完整的部署流程：
        1. 创建服务（如不存在）
        2. 创建函数
        3. 创建 HTTP 触发器
        4. 返回调用 URL

        Args:
            model_name: 模型名称（将作为函数名）
            model_path: 模型代码目录路径
            inference_handler: 推理函数入口

        Returns:
            部署结果，包含函数信息和调用 URL
        """
        logger.info(f"开始部署模型推理服务: {model_name}")

        # 标准化函数名（只允许字母、数字、下划线和连字符）
        function_name = model_name.replace(".", "-").replace("/", "-")

        try:
            # 1. 创建服务
            service = self.create_service(
                description=f"模型推理服务 - 由 ONE-DATA-STUDIO 自动创建"
            )

            # 2. 检查函数是否存在，存在则更新
            try:
                existing_function = self._make_request(
                    "GET",
                    f"/{self.API_VERSION}/services/{self.config.service_name}/functions/{function_name}"
                )
                logger.info(f"函数已存在，执行更新: {function_name}")
                function = self.update_function(
                    function_name,
                    code_dir=model_path,
                    handler=inference_handler
                )
            except AliyunFCError as e:
                if e.status_code == 404:
                    # 创建新函数
                    function = self.create_function(
                        function_name=function_name,
                        handler=inference_handler,
                        runtime="python3.10",
                        code_dir=model_path,
                        environment_variables={
                            "MODEL_NAME": model_name,
                            "PYTHONUNBUFFERED": "1"
                        }
                    )
                else:
                    raise

            # 3. 创建 HTTP 触发器（如不存在）
            trigger_name = "http-trigger"
            try:
                trigger = self.create_http_trigger(
                    function_name=function_name,
                    trigger_name=trigger_name,
                    methods=["GET", "POST", "PUT", "DELETE"]
                )
            except AliyunFCError as e:
                if "TriggerAlreadyExists" in str(e.response):
                    logger.info(f"HTTP 触发器已存在: {trigger_name}")
                    trigger = {"triggerName": trigger_name}
                else:
                    raise

            # 4. 获取调用 URL
            invoke_url = self.get_function_url(function_name)

            result = {
                "success": True,
                "model_name": model_name,
                "function_name": function_name,
                "service_name": self.config.service_name,
                "invoke_url": invoke_url,
                "function": function,
                "trigger": trigger
            }

            logger.info(f"模型推理服务部署成功: {invoke_url}")
            return result

        except Exception as e:
            logger.error(f"模型推理服务部署失败: {e}")
            return {
                "success": False,
                "model_name": model_name,
                "error": str(e)
            }

    def health_check(self) -> Dict:
        """
        健康检查

        验证函数计算服务是否可访问。

        Returns:
            健康状态信息
        """
        logger.info("执行函数计算服务健康检查")

        try:
            # 尝试获取服务信息
            result = self._make_request(
                "GET",
                f"/{self.API_VERSION}/services/{self.config.service_name}"
            )

            return {
                "healthy": True,
                "service_name": self.config.service_name,
                "region": self.config.region,
                "service_id": result.get("serviceId"),
                "created_time": result.get("createdTime"),
                "last_modified_time": result.get("lastModifiedTime")
            }
        except AliyunFCError as e:
            if e.status_code == 404:
                # 服务不存在但 API 可访问
                return {
                    "healthy": True,
                    "service_name": self.config.service_name,
                    "region": self.config.region,
                    "service_exists": False,
                    "message": "服务不存在，需要创建"
                }
            return {
                "healthy": False,
                "service_name": self.config.service_name,
                "region": self.config.region,
                "error": str(e),
                "status_code": e.status_code
            }
        except Exception as e:
            return {
                "healthy": False,
                "service_name": self.config.service_name,
                "region": self.config.region,
                "error": str(e)
            }

    def list_functions(self, limit: int = 100, next_token: str = None) -> Dict:
        """
        列出服务下的所有函数

        Args:
            limit: 返回数量限制
            next_token: 分页标记

        Returns:
            函数列表
        """
        path = f"/{self.API_VERSION}/services/{self.config.service_name}/functions"
        params = [f"limit={limit}"]
        if next_token:
            params.append(f"nextToken={quote(next_token)}")

        if params:
            path += "?" + "&".join(params)

        return self._make_request("GET", path)

    def get_function(self, function_name: str) -> Dict:
        """
        获取函数详情

        Args:
            function_name: 函数名称

        Returns:
            函数信息
        """
        return self._make_request(
            "GET",
            f"/{self.API_VERSION}/services/{self.config.service_name}/functions/{function_name}"
        )


def get_aliyun_fc_adapter(config: AliyunFCConfig = None) -> AliyunFCAdapter:
    """
    获取阿里云函数计算适配器单例

    Args:
        config: 配置对象，首次调用时必须提供，后续调用可省略

    Returns:
        AliyunFCAdapter 实例

    Raises:
        ValueError: 首次调用未提供配置时抛出
    """
    global _adapter_instance

    if _adapter_instance is None:
        if config is None:
            # 尝试从环境变量创建配置
            config = AliyunFCConfig.from_env()
            if not config.access_key_id:
                raise ValueError("首次调用必须提供配置或设置环境变量")

        _adapter_instance = AliyunFCAdapter(config)
        logger.info("阿里云函数计算适配器单例已创建")
    elif config is not None:
        # 如果提供了新配置，更新实例
        _adapter_instance = AliyunFCAdapter(config)
        logger.info("阿里云函数计算适配器单例已更新")

    return _adapter_instance
