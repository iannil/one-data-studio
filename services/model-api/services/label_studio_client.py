"""
Label Studio REST API 客户端

提供对 Label Studio 的封装访问，用于数据标注功能的代理。
参考: https://labelstud.io/api
"""

import os
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


@dataclass
class LabelStudioConfig:
    """Label Studio 连接配置"""
    url: str
    api_token: str
    timeout: int = 30
    enabled: bool = True

    @classmethod
    def from_env(cls) -> "LabelStudioConfig":
        """从环境变量加载配置"""
        url = os.getenv("LABEL_STUDIO_URL", "")
        api_token = os.getenv("LABEL_STUDIO_API_TOKEN", "")
        timeout = int(os.getenv("LABEL_STUDIO_TIMEOUT", "30"))
        enabled = bool(url and api_token)

        return cls(
            url=url.rstrip("/"),
            api_token=api_token,
            timeout=timeout,
            enabled=enabled,
        )


class LabelStudioClient:
    """Label Studio REST API 客户端"""

    def __init__(self, config: Optional[LabelStudioConfig] = None):
        self.config = config or LabelStudioConfig.from_env()
        self._session: Optional[requests.Session] = None

    @property
    def session(self) -> requests.Session:
        """获取带重试机制的 HTTP 会话"""
        if self._session is None:
            self._session = requests.Session()

            retry_strategy = Retry(
                total=3,
                backoff_factor=0.5,
                status_forcelist=[500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)

            self._session.headers.update({
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Token {self.config.api_token}",
            })

        return self._session

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Any] = None,
        params: Optional[Dict] = None,
    ) -> Any:
        """发送 HTTP 请求到 Label Studio"""
        url = f"{self.config.url}{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=self.config.timeout,
            )
            response.raise_for_status()

            if response.content:
                return response.json()
            return {}

        except requests.exceptions.HTTPError as e:
            logger.error(f"Label Studio API error: {e} - {e.response.text if e.response else ''}")
            raise
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Label Studio connection error: {e}")
            raise
        except Exception as e:
            logger.error(f"Label Studio request failed: {e}")
            raise

    def health_check(self) -> bool:
        """检查 Label Studio 健康状态"""
        try:
            response = self.session.get(
                f"{self.config.url}/health",
                timeout=5,
            )
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Label Studio health check failed: {e}")
            return False

    def create_project(
        self,
        title: str,
        description: str = "",
        label_config: str = "",
    ) -> Dict[str, Any]:
        """
        创建 Label Studio 项目

        Args:
            title: 项目标题
            description: 项目描述
            label_config: Label Studio XML 配置

        Returns:
            创建的项目信息（包含 int id）
        """
        payload = {
            "title": title,
            "description": description,
        }
        if label_config:
            payload["label_config"] = label_config

        return self._request("POST", "/api/projects/", data=payload)

    def list_projects(self) -> List[Dict[str, Any]]:
        """列出所有项目"""
        result = self._request("GET", "/api/projects/")
        # Label Studio 返回分页结果
        if isinstance(result, dict) and "results" in result:
            return result["results"]
        if isinstance(result, list):
            return result
        return []

    def get_project(self, project_id: int) -> Dict[str, Any]:
        """获取项目详情"""
        return self._request("GET", f"/api/projects/{project_id}/")

    def delete_project(self, project_id: int) -> None:
        """删除项目"""
        self._request("DELETE", f"/api/projects/{project_id}/")

    def create_tasks(
        self,
        project_id: int,
        tasks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        批量导入任务到项目

        Args:
            project_id: Label Studio 项目 ID
            tasks: 任务数据列表

        Returns:
            创建的任务列表
        """
        result = self._request(
            "POST",
            f"/api/projects/{project_id}/import",
            data=tasks,
        )
        if isinstance(result, list):
            return result
        return result.get("tasks", []) if isinstance(result, dict) else []

    def create_annotation(
        self,
        task_id: int,
        result: List[Dict[str, Any]],
        lead_time: float = 0.0,
        was_cancelled: bool = False,
    ) -> Dict[str, Any]:
        """
        创建标注结果

        Args:
            task_id: Label Studio 任务 ID
            result: 标注结果数据
            lead_time: 标注耗时
            was_cancelled: 是否取消
        """
        payload = {
            "result": result,
            "lead_time": lead_time,
            "was_cancelled": was_cancelled,
        }
        return self._request("POST", f"/api/tasks/{task_id}/annotations/", data=payload)

    def export_annotations(
        self,
        project_id: int,
        export_type: str = "JSON",
    ) -> Any:
        """
        导出标注结果

        Args:
            project_id: 项目 ID
            export_type: 导出格式 (JSON, CSV, COCO, YOLO 等)
        """
        return self._request(
            "GET",
            f"/api/projects/{project_id}/export",
            params={"exportType": export_type},
        )

    def get_tasks(
        self,
        project_id: int,
        page: int = 1,
        page_size: int = 100,
    ) -> Dict[str, Any]:
        """
        获取项目任务列表

        Args:
            project_id: 项目 ID
            page: 页码
            page_size: 每页数量
        """
        return self._request(
            "GET",
            f"/api/tasks/",
            params={
                "project": project_id,
                "page": page,
                "page_size": page_size,
            },
        )
