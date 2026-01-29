"""
Kettle Carte 服务器客户端

提供与 Pentaho Data Integration (PDI) Carte 服务器通信的功能，
支持提交、监控和管理 ETL 转换任务。

Carte API 参考: https://wiki.pentaho.com/display/EAI/Carte+Web+Services
"""
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List
from io import StringIO

import requests
from requests.auth import HTTPBasicAuth

from .config import KettleConfig


logger = logging.getLogger(__name__)


class TransformationStatus(Enum):
    """转换执行状态"""
    RUNNING = "Running"
    FINISHED = "Finished"
    STOPPED = "Stopped"
    STOPPED_WITH_ERRORS = "Stopped with errors"
    WAITING = "Waiting"
    UNKNOWN = "Unknown"


@dataclass
class TransformationResult:
    """转换执行结果"""
    name: str
    status: TransformationStatus
    status_description: str
    rows_read: int = 0
    rows_written: int = 0
    rows_rejected: int = 0
    errors: int = 0
    step_statuses: List[Dict[str, Any]] = None
    log_text: str = ""
    execution_time_ms: int = 0

    def __post_init__(self):
        if self.step_statuses is None:
            self.step_statuses = []

    @property
    def is_running(self) -> bool:
        return self.status == TransformationStatus.RUNNING

    @property
    def is_finished(self) -> bool:
        return self.status in (
            TransformationStatus.FINISHED,
            TransformationStatus.STOPPED,
            TransformationStatus.STOPPED_WITH_ERRORS,
        )

    @property
    def is_success(self) -> bool:
        return self.status == TransformationStatus.FINISHED and self.errors == 0


class KettleBridge:
    """
    Kettle Carte 服务器客户端

    提供以下功能:
    - 注册和执行转换 (Transformation)
    - 查询转换执行状态
    - 获取执行日志
    - 停止正在运行的转换
    """

    def __init__(self, config: Optional[KettleConfig] = None):
        """
        初始化 Kettle 客户端

        Args:
            config: Kettle 配置，如果为 None 则从环境变量加载
        """
        self.config = config or KettleConfig.from_env()
        self.auth = HTTPBasicAuth(
            self.config.carte_user,
            self.config.carte_password
        )
        self._session = requests.Session()
        self._session.auth = self.auth

    def _get_url(self, endpoint: str) -> str:
        """构造完整 URL"""
        base = self.config.carte_url.rstrip("/")
        return f"{base}/kettle/{endpoint}"

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> requests.Response:
        """
        发送 HTTP 请求到 Carte 服务器

        Args:
            method: HTTP 方法
            endpoint: API 端点
            params: URL 参数
            data: 请求体数据
            timeout: 超时时间

        Returns:
            响应对象

        Raises:
            requests.RequestException: 请求失败时抛出
        """
        url = self._get_url(endpoint)
        timeout = timeout or self.config.timeout

        logger.debug(f"Kettle request: {method} {url} params={params}")

        response = self._session.request(
            method=method,
            url=url,
            params=params,
            data=data,
            timeout=timeout,
            headers={"Content-Type": "text/xml"} if data else None,
        )

        response.raise_for_status()
        return response

    def health_check(self) -> bool:
        """
        检查 Carte 服务器健康状态

        Returns:
            服务器是否可用
        """
        try:
            response = self._request("GET", "status/", params={"xml": "Y"})
            return response.status_code == 200
        except requests.RequestException as e:
            logger.error(f"Kettle health check failed: {e}")
            return False

    def register_transformation(
        self,
        trans_xml: str,
        trans_name: str,
    ) -> bool:
        """
        注册转换到 Carte 服务器

        Args:
            trans_xml: Kettle 转换 XML 内容
            trans_name: 转换名称

        Returns:
            是否注册成功
        """
        try:
            response = self._request(
                "POST",
                "registerTrans/",
                data=trans_xml,
            )

            # 解析响应
            root = ET.fromstring(response.text)
            result = root.find("result")

            if result is not None and result.text == "OK":
                logger.info(f"Transformation '{trans_name}' registered successfully")
                return True
            else:
                message = root.find("message")
                error_msg = message.text if message is not None else "Unknown error"
                logger.error(f"Failed to register transformation: {error_msg}")
                return False

        except Exception as e:
            logger.error(f"Failed to register transformation '{trans_name}': {e}")
            raise

    def execute_transformation(
        self,
        trans_name: str,
        level: str = "Basic",
    ) -> bool:
        """
        执行已注册的转换

        Args:
            trans_name: 转换名称
            level: 日志级别 (Nothing, Error, Minimal, Basic, Detailed, Debug, Rowlevel)

        Returns:
            是否启动成功
        """
        try:
            response = self._request(
                "GET",
                "executeTrans/",
                params={"name": trans_name, "level": level},
            )

            # 解析响应
            root = ET.fromstring(response.text)
            result = root.find("result")

            if result is not None and result.text == "OK":
                logger.info(f"Transformation '{trans_name}' started successfully")
                return True
            else:
                message = root.find("message")
                error_msg = message.text if message is not None else "Unknown error"
                logger.error(f"Failed to execute transformation: {error_msg}")
                return False

        except Exception as e:
            logger.error(f"Failed to execute transformation '{trans_name}': {e}")
            raise

    def submit_transformation(
        self,
        trans_xml: str,
        trans_name: str,
        level: str = "Basic",
    ) -> str:
        """
        注册并执行转换 (组合操作)

        Args:
            trans_xml: Kettle 转换 XML 内容
            trans_name: 转换名称
            level: 日志级别

        Returns:
            转换名称 (作为 job_id 使用)

        Raises:
            Exception: 注册或执行失败时抛出
        """
        # 1. 注册转换
        if not self.register_transformation(trans_xml, trans_name):
            raise Exception(f"Failed to register transformation '{trans_name}'")

        # 2. 执行转换
        if not self.execute_transformation(trans_name, level):
            raise Exception(f"Failed to execute transformation '{trans_name}'")

        return trans_name

    def get_transformation_status(
        self,
        trans_name: str,
    ) -> TransformationResult:
        """
        获取转换执行状态

        Args:
            trans_name: 转换名称

        Returns:
            转换执行结果
        """
        try:
            response = self._request(
                "GET",
                "transStatus/",
                params={"name": trans_name, "xml": "Y"},
            )

            return self._parse_trans_status(response.text, trans_name)

        except Exception as e:
            logger.error(f"Failed to get transformation status '{trans_name}': {e}")
            raise

    def _parse_trans_status(self, xml_text: str, trans_name: str) -> TransformationResult:
        """解析转换状态 XML"""
        root = ET.fromstring(xml_text)

        # 获取状态描述
        status_desc_elem = root.find("status_desc")
        status_desc = status_desc_elem.text if status_desc_elem is not None else "Unknown"

        # 映射状态
        status_map = {
            "Running": TransformationStatus.RUNNING,
            "Finished": TransformationStatus.FINISHED,
            "Stopped": TransformationStatus.STOPPED,
            "Stopped with errors": TransformationStatus.STOPPED_WITH_ERRORS,
            "Waiting": TransformationStatus.WAITING,
        }
        status = status_map.get(status_desc, TransformationStatus.UNKNOWN)

        # 获取统计信息
        rows_read = 0
        rows_written = 0
        rows_rejected = 0
        errors = 0
        step_statuses = []

        for step_status in root.findall(".//stepstatus"):
            step_name = step_status.find("stepname")
            step_read = step_status.find("linesRead")
            step_written = step_status.find("linesWritten")
            step_rejected = step_status.find("linesRejected")
            step_errors = step_status.find("errors")

            step_info = {
                "name": step_name.text if step_name is not None else "",
                "read": int(step_read.text) if step_read is not None else 0,
                "written": int(step_written.text) if step_written is not None else 0,
                "rejected": int(step_rejected.text) if step_rejected is not None else 0,
                "errors": int(step_errors.text) if step_errors is not None else 0,
            }
            step_statuses.append(step_info)

            rows_read += step_info["read"]
            rows_written += step_info["written"]
            rows_rejected += step_info["rejected"]
            errors += step_info["errors"]

        # 获取日志
        log_elem = root.find("logging_string")
        log_text = log_elem.text if log_elem is not None else ""

        return TransformationResult(
            name=trans_name,
            status=status,
            status_description=status_desc,
            rows_read=rows_read,
            rows_written=rows_written,
            rows_rejected=rows_rejected,
            errors=errors,
            step_statuses=step_statuses,
            log_text=log_text,
        )

    def stop_transformation(self, trans_name: str) -> bool:
        """
        停止正在运行的转换

        Args:
            trans_name: 转换名称

        Returns:
            是否停止成功
        """
        try:
            response = self._request(
                "GET",
                "stopTrans/",
                params={"name": trans_name},
            )

            root = ET.fromstring(response.text)
            result = root.find("result")

            if result is not None and result.text == "OK":
                logger.info(f"Transformation '{trans_name}' stopped")
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"Failed to stop transformation '{trans_name}': {e}")
            raise

    def remove_transformation(self, trans_name: str) -> bool:
        """
        从 Carte 服务器移除转换

        Args:
            trans_name: 转换名称

        Returns:
            是否移除成功
        """
        try:
            response = self._request(
                "GET",
                "removeTrans/",
                params={"name": trans_name},
            )

            root = ET.fromstring(response.text)
            result = root.find("result")

            if result is not None and result.text == "OK":
                logger.info(f"Transformation '{trans_name}' removed")
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"Failed to remove transformation '{trans_name}': {e}")
            raise

    def get_transformation_log(self, trans_name: str) -> str:
        """
        获取转换执行日志

        Args:
            trans_name: 转换名称

        Returns:
            日志文本
        """
        status = self.get_transformation_status(trans_name)
        return status.log_text

    def list_transformations(self) -> List[Dict[str, Any]]:
        """
        列出所有已注册的转换

        Returns:
            转换列表
        """
        try:
            response = self._request("GET", "status/", params={"xml": "Y"})
            root = ET.fromstring(response.text)

            transformations = []
            for trans_status in root.findall(".//transstatus"):
                name = trans_status.find("transname")
                status = trans_status.find("status_desc")
                transformations.append({
                    "name": name.text if name is not None else "",
                    "status": status.text if status is not None else "",
                })

            return transformations

        except Exception as e:
            logger.error(f"Failed to list transformations: {e}")
            raise
