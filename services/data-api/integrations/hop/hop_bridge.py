"""
Apache Hop Server 客户端

提供与 Apache Hop Server 通信的功能，
支持提交、监控和管理 Pipeline 和 Workflow 任务。

Hop Server REST API 基于 JSON，提供现代化的接口。
"""
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List

import requests
from requests.auth import HTTPBasicAuth

from .config import HopConfig


logger = logging.getLogger(__name__)


class PipelineStatus(Enum):
    """Pipeline 执行状态"""
    RUNNING = "Running"
    FINISHED = "Finished"
    STOPPED = "Stopped"
    ERROR = "Error"
    WAITING = "Waiting"
    UNKNOWN = "Unknown"


class WorkflowStatus(Enum):
    """Workflow 执行状态"""
    RUNNING = "Running"
    FINISHED = "Finished"
    STOPPED = "Stopped"
    ERROR = "Error"
    WAITING = "Waiting"
    UNKNOWN = "Unknown"


@dataclass
class PipelineResult:
    """Pipeline 执行结果"""
    name: str
    status: PipelineStatus
    status_description: str
    rows_read: int = 0
    rows_written: int = 0
    rows_rejected: int = 0
    errors: int = 0
    transform_statuses: List[Dict[str, Any]] = field(default_factory=list)
    log_text: str = ""
    execution_time_ms: int = 0

    @property
    def is_running(self) -> bool:
        return self.status == PipelineStatus.RUNNING

    @property
    def is_finished(self) -> bool:
        return self.status in (
            PipelineStatus.FINISHED,
            PipelineStatus.STOPPED,
            PipelineStatus.ERROR,
        )

    @property
    def is_success(self) -> bool:
        return self.status == PipelineStatus.FINISHED and self.errors == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "status_description": self.status_description,
            "rows_read": self.rows_read,
            "rows_written": self.rows_written,
            "rows_rejected": self.rows_rejected,
            "errors": self.errors,
            "transform_statuses": self.transform_statuses,
            "log_text": self.log_text,
            "execution_time_ms": self.execution_time_ms,
            "is_running": self.is_running,
            "is_finished": self.is_finished,
            "is_success": self.is_success,
        }


@dataclass
class WorkflowResult:
    """Workflow 执行结果"""
    name: str
    status: WorkflowStatus
    status_description: str
    errors: int = 0
    action_statuses: List[Dict[str, Any]] = field(default_factory=list)
    log_text: str = ""
    execution_time_ms: int = 0

    @property
    def is_running(self) -> bool:
        return self.status == WorkflowStatus.RUNNING

    @property
    def is_finished(self) -> bool:
        return self.status in (
            WorkflowStatus.FINISHED,
            WorkflowStatus.STOPPED,
            WorkflowStatus.ERROR,
        )

    @property
    def is_success(self) -> bool:
        return self.status == WorkflowStatus.FINISHED and self.errors == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "status_description": self.status_description,
            "errors": self.errors,
            "action_statuses": self.action_statuses,
            "log_text": self.log_text,
            "execution_time_ms": self.execution_time_ms,
            "is_running": self.is_running,
            "is_finished": self.is_finished,
            "is_success": self.is_success,
        }


class HopBridge:
    """
    Apache Hop Server 客户端

    提供以下功能:
    - 注册和执行 Pipeline（相当于 Kettle Transformation）
    - 注册和执行 Workflow（相当于 Kettle Job）
    - 查询执行状态
    - 获取执行日志
    - 停止正在运行的任务
    """

    def __init__(self, config: Optional[HopConfig] = None):
        """
        初始化 Hop 客户端

        Args:
            config: Hop 配置，如果为 None 则从环境变量加载
        """
        self.config = config or HopConfig.from_env()
        self.auth = HTTPBasicAuth(
            self.config.username,
            self.config.password
        )
        self._session = requests.Session()
        self._session.auth = self.auth

    def _get_url(self, endpoint: str) -> str:
        """构造完整 URL"""
        base = self.config.base_url
        # Hop Server REST API 路径
        return f"{base}/api/v1/{endpoint.lstrip('/')}"

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        files: Optional[Dict] = None,
        timeout: Optional[int] = None,
    ) -> requests.Response:
        """
        发送 HTTP 请求到 Hop Server

        Args:
            method: HTTP 方法
            endpoint: API 端点
            params: URL 参数
            json_data: JSON 请求体数据
            files: 文件上传数据
            timeout: 超时时间

        Returns:
            响应对象

        Raises:
            requests.RequestException: 请求失败时抛出
        """
        url = self._get_url(endpoint)
        timeout = timeout or self.config.timeout

        logger.debug(f"Hop request: {method} {url} params={params}")

        headers = {}
        if json_data and not files:
            headers["Content-Type"] = "application/json"

        response = self._session.request(
            method=method,
            url=url,
            params=params,
            json=json_data,
            files=files,
            timeout=timeout,
            headers=headers if headers else None,
        )

        response.raise_for_status()
        return response

    def health_check(self) -> bool:
        """
        检查 Hop Server 健康状态

        Returns:
            服务器是否可用
        """
        try:
            response = self._request("GET", "server/status")
            return response.status_code == 200
        except requests.RequestException as e:
            logger.error(f"Hop health check failed: {e}")
            return False

    def get_server_status(self) -> Dict[str, Any]:
        """
        获取 Hop Server 状态详情

        Returns:
            服务器状态信息
        """
        try:
            response = self._request("GET", "server/status")
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get Hop server status: {e}")
            return {"error": str(e), "available": False}

    # ==================== Pipeline (相当于 Kettle Transformation) ====================

    def register_pipeline(
        self,
        pipeline_xml: str,
        pipeline_name: str,
    ) -> bool:
        """
        注册 Pipeline 到 Hop Server

        Args:
            pipeline_xml: Hop Pipeline XML 内容 (.hpl)
            pipeline_name: Pipeline 名称

        Returns:
            是否注册成功
        """
        try:
            # 使用 multipart/form-data 上传 Pipeline
            files = {
                "file": (f"{pipeline_name}.hpl", pipeline_xml, "application/xml")
            }
            response = self._request(
                "POST",
                "pipelines/register",
                files=files,
            )

            result = response.json()
            if result.get("status") == "OK" or result.get("result") == "OK":
                logger.info(f"Pipeline '{pipeline_name}' registered successfully")
                return True
            else:
                error_msg = result.get("message", "Unknown error")
                logger.error(f"Failed to register pipeline: {error_msg}")
                return False

        except Exception as e:
            logger.error(f"Failed to register pipeline '{pipeline_name}': {e}")
            raise

    def execute_pipeline(
        self,
        pipeline_name: str,
        log_level: str = "Basic",
    ) -> bool:
        """
        执行已注册的 Pipeline

        Args:
            pipeline_name: Pipeline 名称
            log_level: 日志级别 (Nothing, Error, Minimal, Basic, Detailed, Debug, Rowlevel)

        Returns:
            是否启动成功
        """
        try:
            response = self._request(
                "POST",
                f"pipelines/{pipeline_name}/start",
                json_data={"logLevel": log_level},
            )

            result = response.json()
            if result.get("status") == "OK" or result.get("result") == "OK":
                logger.info(f"Pipeline '{pipeline_name}' started successfully")
                return True
            else:
                error_msg = result.get("message", "Unknown error")
                logger.error(f"Failed to execute pipeline: {error_msg}")
                return False

        except Exception as e:
            logger.error(f"Failed to execute pipeline '{pipeline_name}': {e}")
            raise

    def submit_pipeline(
        self,
        pipeline_xml: str,
        pipeline_name: str,
        log_level: str = "Basic",
    ) -> str:
        """
        注册并执行 Pipeline (组合操作)

        Args:
            pipeline_xml: Hop Pipeline XML 内容
            pipeline_name: Pipeline 名称
            log_level: 日志级别

        Returns:
            Pipeline 名称 (作为 job_id 使用)

        Raises:
            Exception: 注册或执行失败时抛出
        """
        # 1. 注册 Pipeline
        if not self.register_pipeline(pipeline_xml, pipeline_name):
            raise Exception(f"Failed to register pipeline '{pipeline_name}'")

        # 2. 执行 Pipeline
        if not self.execute_pipeline(pipeline_name, log_level):
            raise Exception(f"Failed to execute pipeline '{pipeline_name}'")

        return pipeline_name

    def get_pipeline_status(
        self,
        pipeline_name: str,
    ) -> PipelineResult:
        """
        获取 Pipeline 执行状态

        Args:
            pipeline_name: Pipeline 名称

        Returns:
            Pipeline 执行结果
        """
        try:
            response = self._request(
                "GET",
                f"pipelines/{pipeline_name}/status",
            )

            return self._parse_pipeline_status(response.json(), pipeline_name)

        except Exception as e:
            logger.error(f"Failed to get pipeline status '{pipeline_name}': {e}")
            raise

    def _parse_pipeline_status(self, data: Dict[str, Any], pipeline_name: str) -> PipelineResult:
        """解析 Pipeline 状态 JSON"""
        status_str = data.get("status_desc", data.get("status", "Unknown"))

        # 映射状态
        status_map = {
            "Running": PipelineStatus.RUNNING,
            "Finished": PipelineStatus.FINISHED,
            "Stopped": PipelineStatus.STOPPED,
            "Error": PipelineStatus.ERROR,
            "Stopped with errors": PipelineStatus.ERROR,
            "Waiting": PipelineStatus.WAITING,
        }
        status = status_map.get(status_str, PipelineStatus.UNKNOWN)

        # 获取统计信息
        rows_read = 0
        rows_written = 0
        rows_rejected = 0
        errors = data.get("errors", 0)
        transform_statuses = []

        # 解析 transform 状态
        transforms = data.get("transforms", data.get("step_statuses", []))
        for transform in transforms:
            transform_info = {
                "name": transform.get("name", transform.get("transform_name", "")),
                "read": transform.get("lines_read", transform.get("read", 0)),
                "written": transform.get("lines_written", transform.get("written", 0)),
                "rejected": transform.get("lines_rejected", transform.get("rejected", 0)),
                "errors": transform.get("errors", 0),
            }
            transform_statuses.append(transform_info)

            rows_read += transform_info["read"]
            rows_written += transform_info["written"]
            rows_rejected += transform_info["rejected"]

        # 获取日志
        log_text = data.get("logging_string", data.get("log_text", ""))

        return PipelineResult(
            name=pipeline_name,
            status=status,
            status_description=status_str,
            rows_read=rows_read,
            rows_written=rows_written,
            rows_rejected=rows_rejected,
            errors=errors,
            transform_statuses=transform_statuses,
            log_text=log_text,
            execution_time_ms=data.get("execution_time_ms", 0),
        )

    def stop_pipeline(self, pipeline_name: str) -> bool:
        """
        停止正在运行的 Pipeline

        Args:
            pipeline_name: Pipeline 名称

        Returns:
            是否停止成功
        """
        try:
            response = self._request(
                "POST",
                f"pipelines/{pipeline_name}/stop",
            )

            result = response.json()
            if result.get("status") == "OK" or result.get("result") == "OK":
                logger.info(f"Pipeline '{pipeline_name}' stopped")
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"Failed to stop pipeline '{pipeline_name}': {e}")
            raise

    def remove_pipeline(self, pipeline_name: str) -> bool:
        """
        从 Hop Server 移除 Pipeline

        Args:
            pipeline_name: Pipeline 名称

        Returns:
            是否移除成功
        """
        try:
            response = self._request(
                "DELETE",
                f"pipelines/{pipeline_name}",
            )

            result = response.json()
            if result.get("status") == "OK" or result.get("result") == "OK":
                logger.info(f"Pipeline '{pipeline_name}' removed")
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"Failed to remove pipeline '{pipeline_name}': {e}")
            raise

    def list_pipelines(self) -> List[Dict[str, Any]]:
        """
        列出所有已注册的 Pipeline

        Returns:
            Pipeline 列表
        """
        try:
            response = self._request("GET", "pipelines")
            data = response.json()

            pipelines = []
            for item in data.get("pipelines", data.get("items", [])):
                pipelines.append({
                    "name": item.get("name", ""),
                    "status": item.get("status", ""),
                    "id": item.get("id", ""),
                })

            return pipelines

        except Exception as e:
            logger.error(f"Failed to list pipelines: {e}")
            raise

    # ==================== Workflow (相当于 Kettle Job) ====================

    def register_workflow(
        self,
        workflow_xml: str,
        workflow_name: str,
    ) -> bool:
        """
        注册 Workflow 到 Hop Server

        Args:
            workflow_xml: Hop Workflow XML 内容 (.hwf)
            workflow_name: Workflow 名称

        Returns:
            是否注册成功
        """
        try:
            files = {
                "file": (f"{workflow_name}.hwf", workflow_xml, "application/xml")
            }
            response = self._request(
                "POST",
                "workflows/register",
                files=files,
            )

            result = response.json()
            if result.get("status") == "OK" or result.get("result") == "OK":
                logger.info(f"Workflow '{workflow_name}' registered successfully")
                return True
            else:
                error_msg = result.get("message", "Unknown error")
                logger.error(f"Failed to register workflow: {error_msg}")
                return False

        except Exception as e:
            logger.error(f"Failed to register workflow '{workflow_name}': {e}")
            raise

    def execute_workflow(
        self,
        workflow_name: str,
        log_level: str = "Basic",
    ) -> bool:
        """
        执行已注册的 Workflow

        Args:
            workflow_name: Workflow 名称
            log_level: 日志级别

        Returns:
            是否启动成功
        """
        try:
            response = self._request(
                "POST",
                f"workflows/{workflow_name}/start",
                json_data={"logLevel": log_level},
            )

            result = response.json()
            if result.get("status") == "OK" or result.get("result") == "OK":
                logger.info(f"Workflow '{workflow_name}' started successfully")
                return True
            else:
                error_msg = result.get("message", "Unknown error")
                logger.error(f"Failed to execute workflow: {error_msg}")
                return False

        except Exception as e:
            logger.error(f"Failed to execute workflow '{workflow_name}': {e}")
            raise

    def get_workflow_status(
        self,
        workflow_name: str,
    ) -> WorkflowResult:
        """
        获取 Workflow 执行状态

        Args:
            workflow_name: Workflow 名称

        Returns:
            Workflow 执行结果
        """
        try:
            response = self._request(
                "GET",
                f"workflows/{workflow_name}/status",
            )

            return self._parse_workflow_status(response.json(), workflow_name)

        except Exception as e:
            logger.error(f"Failed to get workflow status '{workflow_name}': {e}")
            raise

    def _parse_workflow_status(self, data: Dict[str, Any], workflow_name: str) -> WorkflowResult:
        """解析 Workflow 状态 JSON"""
        status_str = data.get("status_desc", data.get("status", "Unknown"))

        # 映射状态
        status_map = {
            "Running": WorkflowStatus.RUNNING,
            "Finished": WorkflowStatus.FINISHED,
            "Stopped": WorkflowStatus.STOPPED,
            "Error": WorkflowStatus.ERROR,
            "Stopped with errors": WorkflowStatus.ERROR,
            "Waiting": WorkflowStatus.WAITING,
        }
        status = status_map.get(status_str, WorkflowStatus.UNKNOWN)

        # 解析 action 状态
        action_statuses = []
        actions = data.get("actions", data.get("action_statuses", []))
        for action in actions:
            action_info = {
                "name": action.get("name", action.get("action_name", "")),
                "result": action.get("result", ""),
                "errors": action.get("errors", 0),
            }
            action_statuses.append(action_info)

        # 获取日志
        log_text = data.get("logging_string", data.get("log_text", ""))

        return WorkflowResult(
            name=workflow_name,
            status=status,
            status_description=status_str,
            errors=data.get("errors", 0),
            action_statuses=action_statuses,
            log_text=log_text,
            execution_time_ms=data.get("execution_time_ms", 0),
        )

    def stop_workflow(self, workflow_name: str) -> bool:
        """
        停止正在运行的 Workflow

        Args:
            workflow_name: Workflow 名称

        Returns:
            是否停止成功
        """
        try:
            response = self._request(
                "POST",
                f"workflows/{workflow_name}/stop",
            )

            result = response.json()
            if result.get("status") == "OK" or result.get("result") == "OK":
                logger.info(f"Workflow '{workflow_name}' stopped")
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"Failed to stop workflow '{workflow_name}': {e}")
            raise

    def list_workflows(self) -> List[Dict[str, Any]]:
        """
        列出所有已注册的 Workflow

        Returns:
            Workflow 列表
        """
        try:
            response = self._request("GET", "workflows")
            data = response.json()

            workflows = []
            for item in data.get("workflows", data.get("items", [])):
                workflows.append({
                    "name": item.get("name", ""),
                    "status": item.get("status", ""),
                    "id": item.get("id", ""),
                })

            return workflows

        except Exception as e:
            logger.error(f"Failed to list workflows: {e}")
            raise

    def get_pipeline_log(self, pipeline_name: str) -> str:
        """
        获取 Pipeline 执行日志

        Args:
            pipeline_name: Pipeline 名称

        Returns:
            日志文本
        """
        status = self.get_pipeline_status(pipeline_name)
        return status.log_text

    def get_workflow_log(self, workflow_name: str) -> str:
        """
        获取 Workflow 执行日志

        Args:
            workflow_name: Workflow 名称

        Returns:
            日志文本
        """
        status = self.get_workflow_status(workflow_name)
        return status.log_text
