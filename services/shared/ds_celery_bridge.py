"""
DolphinScheduler 与 Celery 桥接服务
实现 DolphinScheduler 工作流与 Celery 异步任务的双向集成

功能：
1. 从 DolphinScheduler 触发 Celery 任务
2. 同步任务状态到 DolphinScheduler
3. 统一的任务调度接口
4. 任务依赖管理
"""

import logging
import os
import json
import time
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .celery_app import get_task_manager, celery_app

logger = logging.getLogger(__name__)


class DSTaskStatus(str, Enum):
    """DolphinScheduler 任务状态"""
    SUBMITTED_SUCCESS = "SUBMITTED_SUCCESS"
    RUNNING_EXECUTION = "RUNNING_EXECUTION"
    READY_PAUSE = "READY_PAUSE"
    PAUSE = "PAUSE"
    READY_STOP = "READY_STOP"
    STOP = "STOP"
    FAILURE = "FAILURE"
    SUCCESS = "SUCCESS"
    NEED_FAULT_TOLERANCE = "NEED_FAULT_TOLERANCE"
    KILL = "KILL"
    WAITTING_THREAD = "WAITTING_THREAD"
    WAITTING_DEPEND = "WAITTING_DEPEND"
    DELAY_EXECUTION = "DELAY_EXECUTION"
    FORCED_SUCCESS = "FORCED_SUCCESS"
    SERIAL_WAIT = "SERIAL_WAIT"
    DISPATCH = "DISPATCH"


class DSTaskType(str, Enum):
    """DolphinScheduler 任务类型"""
    SHELL = "SHELL"
    SQL = "SQL"
    PYTHON = "PYTHON"
    FLINK = "FLINK"
    SPARK = "SPARK"
    HTTP = "HTTP"
    DATA_X = "DATA_X"
    SUB_PROCESS = "SUB_PROCESS"
    PROCEDURE = "PROCEDURE"
    SQOOP = "SQOOP"
    CONDITION = "CONDITION"
    DEPENDENT = "DEPENDENT"
    SWITCH = "SWITCH"


@dataclass
class DSTaskDefinition:
    """DolphinScheduler 任务定义"""
    name: str
    task_type: DSTaskType
    description: str = ""
    code: str = ""  # 任务代码（SQL、Shell 脚本等）
    raw_script: str = ""  # 原始脚本
    params: Dict[str, Any] = field(default_factory=dict)
    risk_level: str = "MEDIUM"  # HIGH, MEDIUM, LOW
    delay_time: int = 0  # 延迟执行时间（秒）
    timeout: int = 3600  # 超时时间（秒）
    task_params: Dict[str, Any] = field(default_factory=dict)
    resource_list: List[str] = field(default_factory=list)
    local_params: List[Dict[str, Any]] = field(default_factory=list)
    condition_result: Dict[str, Any] = field(default_factory=dict)
    dependence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DSWorkflowDefinition:
    """DolphinScheduler 工作流定义"""
    name: str
    description: str = ""
    task_defs: List[DSTaskDefinition] = field(default_factory=list)
    global_params: List[Dict[str, Any]] = field(default_factory=list)
    timeout: int = 3600
    tenant_code: str = "default"
    execution_type: str = "PARALLEL"  # PARALLEL, SERIAL_WAIT, SERIAL_DISCARD, SERIAL_PRIORITY


class DolphinSchedulerClient:
    """DolphinScheduler API 客户端"""

    def __init__(
        self,
        base_url: str = None,
        username: str = None,
        password: str = None,
        token: str = None,
    ):
        """
        初始化 DolphinScheduler 客户端

        Args:
            base_url: DolphinScheduler API 基础 URL
            username: 用户名
            password: 密码
            token: 认证令牌（如果提供，则跳过登录）
        """
        self.base_url = (base_url or os.getenv(
            "DOLPHINSCHEDULER_URL", "http://localhost:12345")).rstrip('/')
        self.username = username or os.getenv("DOLPHINSCHEDULER_USERNAME", "admin")
        self.password = password or os.getenv("DOLPHINSCHEDULER_PASSWORD", "dolphinscheduler123")
        self._token = token
        self._session = self._create_session()

    def _create_session(self) -> requests.Session:
        """创建带重试机制的会话"""
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def login(self) -> bool:
        """登录并获取令牌"""
        try:
            response = self._session.post(
                f"{self.base_url}/dolphinscheduler/login",
                json={
                    "userName": self.username,
                    "userPassword": self.password,
                },
                headers=self._get_headers(),
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("code") == 0:
                self._token = data["data"]
                logger.info(f"DolphinScheduler 登录成功: {self.username}")
                return True
            else:
                logger.error(f"DolphinScheduler 登录失败: {data.get('msg')}")
                return False
        except Exception as e:
            logger.error(f"DolphinScheduler 登录异常: {e}")
            return False

    def get_token(self) -> Optional[str]:
        """获取认证令牌"""
        if not self._token:
            if not self.login():
                return None
        return self._token

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Dict[str, Any] = None,
        params: Dict[str, Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        发送 API 请求

        Args:
            method: HTTP 方法
            endpoint: API 端点
            data: 请求数据
            params: 查询参数

        Returns:
            响应数据
        """
        token = self.get_token()
        if not token:
            return None

        url = f"{self.base_url}/dolphinscheduler{endpoint}"
        headers = {
            **self._get_headers(),
            "token": token,
        }

        try:
            if method.upper() == "GET":
                response = self._session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=30,
                )
            elif method.upper() == "POST":
                response = self._session.post(
                    url,
                    json=data,
                    params=params,
                    headers=headers,
                    timeout=30,
                )
            elif method.upper() == "PUT":
                response = self._session.put(
                    url,
                    json=data,
                    params=params,
                    headers=headers,
                    timeout=30,
                )
            elif method.upper() == "DELETE":
                response = self._session.delete(
                    url,
                    params=params,
                    headers=headers,
                    timeout=30,
                )
            else:
                logger.error(f"不支持的 HTTP 方法: {method}")
                return None

            response.raise_for_status()
            result = response.json()

            if result.get("code") == 0:
                return result.get("data")
            else:
                logger.warning(f"API 请求失败: {result.get('msg')}")
                return None

        except requests.exceptions.Timeout:
            logger.error(f"API 请求超时: {endpoint}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"API 请求异常: {e}")
            return None

    # ==================== 项目管理 ====================

    def create_project(self, name: str, description: str = "") -> Optional[int]:
        """创建项目"""
        data = self._request("POST", "/projects/create", {
            " projectName": name,
            "description": description,
        })
        return data.get("id") if data else None

    def get_project_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取项目"""
        return self._request("GET", "/projects/query-by-name", {
            "projectName": name,
        })

    def ensure_project(self, name: str, description: str = "") -> int:
        """确保项目存在（不存在则创建）"""
        project = self.get_project_by_name(name)
        if project:
            return project.get("id")
        return self.create_project(name, description)

    # ==================== 工作流定义 ====================

    def create_workflow(
        self,
        project_code: int,
        workflow: DSWorkflowDefinition,
    ) -> Optional[int]:
        """创建工作流定义"""
        # 构建任务定义列表
        task_defs = []
        for task_def in workflow.task_defs:
            task_json = {
                "name": task_def.name,
                "description": task_def.description,
                "taskType": task_def.task_type.value,
                "taskParams": {
                    "resourceList": task_def.resource_list,
                    "localParams": task_def.local_params,
                    "rawScript": task_def.raw_script or task_def.code,
                    "dependence": task_def.dependence,
                    "conditionResult": task_def.condition_result,
                    "waitStartTimeout": {},
                    "switchResult": {},
                },
                "flag": "YES",
                "taskPriority": "MEDIUM",
                "workerGroup": "default",
                "failRetryTimes": 0,
                "failRetryInterval": 1,
                "timeoutFlag": "CLOSE",
                "timeoutNotifyStrategy": None,
                "delayTime": task_def.delay_time,
            }

            # 根据任务类型添加特定参数
            if task_def.task_type == DSTaskType.SQL:
                task_json["taskParams"]["type"] = "MYSQL"
                task_json["taskParams"]["datasource"] = 0

            task_defs.append(task_json)

        # 构建工作流定义
        data = self._request("POST", "/task-definition/batch-create", {
            "projectCode": project_code,
            "taskDefinitionJsonList": json.dumps(task_defs),
        })

        return data.get("code") if data else None

    def create_process_definition(
        self,
        project_code: int,
        name: str,
        description: str = "",
        task_relations: List[Dict] = None,
        global_params: List[Dict] = None,
        timeout: int = 0,
    ) -> Optional[int]:
        """创建流程定义"""
        data = self._request("POST", "/flow/process-definition", {
            "projectCode": project_code,
            "name": name,
            "description": description,
            "taskRelationJson": json.dumps(task_relations or []),
            "taskDefinitionJsonList": json.dumps(global_params or []),
            "globalParams": global_params or [],
            "timeout": timeout,
            "executionType": "PARALLEL",
        })

        return data.get("id") if data else None

    def schedule_workflow(
        self,
        project_code: int,
        process_definition_code: int,
        schedule_time: str = None,
        failure_strategy: str = "CONTINUE",
    ) -> Optional[int]:
        """调度工作流"""
        data = self._request("POST", "/executors/start-process-instance", {
            "processDefinitionCode": process_definition_code,
            "scheduleTime": schedule_time,
            "failureStrategy": failure_strategy,
            "warningType": "NONE",
        })

        return data.get("id") if data else None

    # ==================== 任务实例 ====================

    def get_task_instance_status(
        self,
        process_instance_id: int,
    ) -> List[Dict[str, Any]]:
        """获取任务实例状态"""
        return self._request("GET", "/log/task-detail-list", {
            "processInstanceId": process_instance_id,
        })

    def get_process_instance_status(
        self,
        process_instance_id: int,
    ) -> Optional[Dict[str, Any]]:
        """获取流程实例状态"""
        return self._request("GET", "/executors/detail", {
            "id": process_instance_id,
        })

    # ==================== 工作流执行 ====================

    def run_workflow(
        self,
        project_name: str,
        workflow_name: str,
        params: Dict[str, Any] = None,
    ) -> Optional[int]:
        """
        运行工作流

        Args:
            project_name: 项目名称
            workflow_name: 工作流名称
            params: 全局参数

        Returns:
            流程实例 ID
        """
        project_code = self.ensure_project(project_name)
        if not project_code:
            logger.error(f"项目创建/获取失败: {project_name}")
            return None

        # 获取流程定义
        definitions = self._request("GET", "/flow/process-definition", {
            "projectCode": project_code,
            "searchVal": workflow_name,
        })

        if not definitions or not definitions.get("totalList"):
            logger.error(f"工作流不存在: {workflow_name}")
            return None

        process_definition = definitions["totalList"][0]
        process_definition_code = process_definition.get("code")

        return self.schedule_workflow(
            project_code,
            process_definition_code,
        )


class DSCeleryBridge:
    """DolphinScheduler 与 Celery 桥接器

    实现：
    1. 从 DolphinScheduler 触发 Celery 任务
    2. 将 Celery 任务状态同步到 DolphinScheduler
    3. 支持任务依赖管理
    """

    def __init__(
        self,
        ds_client: DolphinSchedulerClient = None,
        ds_url: str = None,
        ds_username: str = None,
        ds_password: str = None,
    ):
        """
        初始化桥接器

        Args:
            ds_client: DolphinScheduler 客户端（可选）
            ds_url: DolphinScheduler URL
            ds_username: DolphinScheduler 用户名
            ds_password: DolphinScheduler 密码
        """
        if ds_client:
            self.ds = ds_client
        else:
            self.ds = DolphinSchedulerClient(
                base_url=ds_url,
                username=ds_username,
                password=ds_password,
            )

        self.celery = get_task_manager()

        # 任务映射：DS 任务实例 ID -> Celery 任务 ID
        self._ds_to_celery_map: Dict[int, str] = {}
        # Celery 任务 ID -> DS 任务实例 ID
        self._celery_to_ds_map: Dict[str, int] = {}

    # ==================== Celery 任务管理 ====================

    def trigger_celery_from_ds(
        self,
        task_name: str,
        task_params: Dict[str, Any] = None,
        celery_task_id: str = None,
    ) -> Optional[str]:
        """
        从 DolphinScheduler 触发 Celery 任务

        Args:
            task_name: Celery 任务名称
            task_params: 任务参数
            celery_task_id: 指定的 Celery 任务 ID（可选）

        Returns:
            Celery 任务 ID
        """
        try:
            args = task_params.get("args", [])
            kwargs = task_params.get("kwargs", {})

            # 使用 send_task 直接发送
            result = celery_app.send_task(
                task_name,
                args=args,
                kwargs=kwargs,
                task_id=celery_task_id,
            )

            logger.info(f"Celery 任务已触发: {task_name} - {result.id}")
            return result.id

        except Exception as e:
            logger.error(f"触发 Celery 任务失败: {e}")
            return None

    def submit_celery_task(
        self,
        task_name: str,
        *args,
        **kwargs,
    ) -> Optional[str]:
        """
        提交 Celery 任务

        Args:
            task_name: 任务名称
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            任务 ID
        """
        try:
            result = celery_app.send_task(task_name, args=args, kwargs=kwargs)
            logger.info(f"Celery 任务已提交: {task_name} - {result.id}")
            return result.id
        except Exception as e:
            logger.error(f"提交 Celery 任务失败: {e}")
            return None

    # ==================== 任务状态同步 ====================

    def sync_task_status_to_ds(
        self,
        ds_task_instance_id: int,
        celery_task_id: str,
    ) -> Optional[str]:
        """
        同步 Celery 任务状态到 DolphinScheduler

        Args:
            ds_task_instance_id: DS 任务实例 ID
            celery_task_id: Celery 任务 ID

        Returns:
            同步后的状态
        """
        try:
            # 获取 Celery 任务状态
            celery_status = self.celery.get_task_status(celery_task_id)
            status = celery_status.get("status")

            # 映射状态
            ds_status = self._map_celery_status_to_ds(status)

            logger.info(
                f"任务状态同步: Celery[{celery_task_id}] {status} -> "
                f"DS[{ds_task_instance_id}] {ds_status}"
            )

            return ds_status

        except Exception as e:
            logger.error(f"同步任务状态失败: {e}")
            return None

    def _map_celery_status_to_ds(self, celery_status: str) -> str:
        """映射 Celery 状态到 DolphinScheduler 状态"""
        mapping = {
            "PENDING": DSTaskStatus.DISPATCH.value,
            "STARTED": DSTaskStatus.RUNNING_EXECUTION.value,
            "SUCCESS": DSTaskStatus.SUCCESS.value,
            "FAILURE": DSTaskStatus.FAILURE.value,
            "RETRY": DSTaskStatus.RUNNING_EXECUTION.value,
            "REVOKED": DSTaskStatus.KILL.value,
        }
        return mapping.get(celery_status, DSTaskStatus.FAILURE.value)

    def _map_ds_status_to_celery(self, ds_status: str) -> str:
        """映射 DolphinScheduler 状态到 Celery 状态"""
        mapping = {
            DSTaskStatus.SUBMITTED_SUCCESS.value: "PENDING",
            DSTaskStatus.RUNNING_EXECUTION.value: "STARTED",
            DSTaskStatus.SUCCESS.value: "SUCCESS",
            DSTaskStatus.FAILURE.value: "FAILURE",
            DSTaskStatus.KILL.value: "REVOKED",
            DSTaskStatus.STOP.value: "REVOKED",
        }
        return mapping.get(ds_status, "PENDING")

    # ==================== 任务映射管理 ====================

    def add_task_mapping(
        self,
        ds_task_instance_id: int,
        celery_task_id: str,
    ):
        """添加任务映射"""
        self._ds_to_celery_map[ds_task_instance_id] = celery_task_id
        self._celery_to_ds_map[celery_task_id] = ds_task_instance_id

    def get_celery_task_id(self, ds_task_instance_id: int) -> Optional[str]:
        """获取 DS 任务对应的 Celery 任务 ID"""
        return self._ds_to_celery_map.get(ds_task_instance_id)

    def get_ds_task_instance_id(self, celery_task_id: str) -> Optional[int]:
        """获取 Celery 任务对应的 DS 任务实例 ID"""
        return self._celery_to_ds_map.get(celery_task_id)

    def remove_task_mapping(self, ds_task_instance_id: int = None, celery_task_id: str = None):
        """移除任务映射"""
        if ds_task_instance_id:
            celery_id = self._ds_to_celery_map.pop(ds_task_instance_id, None)
            if celery_id:
                self._celery_to_ds_map.pop(celery_id, None)
        if celery_task_id:
            ds_id = self._celery_to_ds_map.pop(celery_task_id, None)
            if ds_id:
                self._ds_to_celery_map.pop(ds_id, None)

    # ==================== 工作流创建 ====================

    def create_ds_workflow_from_tasks(
        self,
        project_name: str,
        workflow_name: str,
        tasks: List[Dict[str, Any]],
        description: str = "",
    ) -> Optional[int]:
        """
        从任务列表创建 DolphinScheduler 工作流

        Args:
            project_name: 项目名称
            workflow_name: 工作流名称
            tasks: 任务列表
                [{
                    "name": "任务名称",
                    "type": "PYTHON/SHELL/SQL",
                    "code": "任务代码",
                    "dependencies": ["前置任务名称"],
                    "params": {...}
                }]
            description: 工作流描述

        Returns:
            流程定义 ID
        """
        try:
            # 确保项目存在
            project_code = self.ds.ensure_project(project_name)
            if not project_code:
                logger.error(f"项目创建/获取失败: {project_name}")
                return None

            # 构建任务定义
            task_defs = []
            task_map = {}

            for idx, task in enumerate(tasks):
                task_def = DSTaskDefinition(
                    name=task["name"],
                    task_type=DSTaskType(task.get("type", "PYTHON")),
                    description=task.get("description", ""),
                    code=task.get("code", ""),
                    raw_script=task.get("code", ""),
                    params=task.get("params", {}),
                )
                task_defs.append(task_def)
                task_map[task["name"]] = task_def

            # 构建工作流定义
            workflow = DSWorkflowDefinition(
                name=workflow_name,
                description=description,
                task_defs=task_defs,
            )

            # 创建工作流
            return self.ds.create_workflow(project_code, workflow)

        except Exception as e:
            logger.error(f"创建 DS 工作流失败: {e}")
            return None

    # ==================== 批量操作 ====================

    def batch_trigger_celery_tasks(
        self,
        task_configs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        批量触发 Celery 任务

        Args:
            task_configs: 任务配置列表
                [{
                    "task_name": "services.shared.celery_tasks.index_document",
                    "args": [...],
                    "kwargs": {...},
                }]

        Returns:
            任务结果列表
        """
        results = []

        for config in task_configs:
            task_name = config.get("task_name")
            args = config.get("args", [])
            kwargs = config.get("kwargs", {})

            try:
                result = celery_app.send_task(task_name, args=args, kwargs=kwargs)
                results.append({
                    "task_name": task_name,
                    "success": True,
                    "task_id": result.id,
                })
            except Exception as e:
                results.append({
                    "task_name": task_name,
                    "success": False,
                    "error": str(e),
                })

        return results


# 创建全局桥接器实例
_bridge: Optional[DSCeleryBridge] = None


def get_ds_celery_bridge() -> DSCeleryBridge:
    """获取全局 DS-Celery 桥接器实例"""
    global _bridge
    if _bridge is None:
        _bridge = DSCeleryBridge()
    return _bridge


# 导出
__all__ = [
    'DSTaskStatus',
    'DSTaskType',
    'DSTaskDefinition',
    'DSWorkflowDefinition',
    'DolphinSchedulerClient',
    'DSCeleryBridge',
    'get_ds_celery_bridge',
]
