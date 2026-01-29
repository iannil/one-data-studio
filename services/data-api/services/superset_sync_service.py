"""
Superset 数据源同步服务
自动同步 One Data Studio 的数据集到 Superset

功能：
1. 数据库同步
2. 数据集同步
3. 图表同步
4. 仪表板同步
5. 权限管理
"""

import logging
import os
import json
import time
import hashlib
import requests
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class SupersetChartType(str, Enum):
    """Superset 图表类型映射"""
    # ECharts 图表类型
    ECHARTS_LINE = "echarts_timeseries_line"
    ECHARTS_BAR = "echarts_timeseries_bar"
    ECHARTS_AREA = "echarts_area"
    ECHARTS_SCATTER = "echarts_scatter"
    ECHARTS_PIE = "echarts_pie"
    ECHARTS_FUNNEL = "echarts_funnel"
    ECHARTS_GAUGE = "echarts_gauge"
    ECHARTS_TREE_MAP = "echarts_tree_map"
    # 原生图表类型
    TABLE = "table"
    BIG_NUMBER = "big_number"
    BIG_NUMBER_TOTAL = "big_number_with_percentage"
    DIST_BAR = "dist_bar"
    PIE = "pie"
    LINE = "line"
    BAR = "bar"
    AREA = "area"
    TREEMAP = "treemap"
    HEATMAP = "heatmap"
    HISTOGRAM = "histogram"
    BOX_PLOT = "box_plot"


class SupersetClient:
    """Superset API 客户端"""

    def __init__(
        self,
        base_url: str = None,
        username: str = None,
        password: str = None,
    ):
        """
        初始化 Superset 客户端

        Args:
            base_url: Superset API 基础 URL
            username: 用户名
            password: 密码
        """
        self.base_url = (base_url or os.getenv(
            "SUPERSET_URL", "http://localhost:8088")).rstrip('/')
        self.username = username or os.getenv("SUPERSET_USERNAME", "admin")
        self.password = password or os.getenv("SUPERSET_PASSWORD", "admin")
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._session = self._create_session()
        self._csrf_token: Optional[str] = None

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
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    def login(self) -> bool:
        """
        登录并获取访问令牌

        Superset 使用 OAuth2 /login 端点
        """
        try:
            # 获取 CSRF token
            response = self._session.get(
                f"{self.base_url}/api/v1/security/csrf_token/",
                timeout=10,
            )
            if response.status_code == 200:
                csrf_data = response.json()
                self._csrf_token = csrf_data.get("result")

            # 登录
            login_data = {
                "username": self.username,
                "password": self.password,
                "provider": "db",
                "refresh": True,
            }

            if self._csrf_token:
                login_data["csrf_token"] = self._csrf_token

            response = self._session.post(
                f"{self.base_url}/api/v1/security/login",
                json=login_data,
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                self._access_token = data.get("access_token")
                self._refresh_token = data.get("refresh_token")
                logger.info(f"Superset 登录成功: {self.username}")
                return True
            else:
                logger.error(f"Superset 登录失败: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Superset 登录异常: {e}")
            return False

    def refresh_token(self) -> bool:
        """刷新访问令牌"""
        if not self._refresh_token:
            return self.login()

        try:
            response = self._session.post(
                f"{self.base_url}/api/v1/security/refresh",
                headers={"Authorization": f"Bearer {self._refresh_token}"},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                self._access_token = data.get("access_token")
                return True
            else:
                return self.login()

        except Exception as e:
            logger.error(f"令牌刷新失败: {e}")
            return self.login()

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Dict[str, Any] = None,
        params: Dict[str, Any] = None,
        retry_login: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        发送 API 请求

        Args:
            method: HTTP 方法
            endpoint: API 端点
            data: 请求数据
            params: 查询参数
            retry_login: 失败时是否重试登录

        Returns:
            响应数据
        """
        if not self._access_token and not self.login():
            return None

        url = f"{self.base_url}/api/v1{endpoint}"
        headers = self._get_headers()

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
            elif method.upper() == "PATCH":
                response = self._session.patch(
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

            # 检查令牌是否过期
            if response.status_code == 401 and retry_login:
                if self.login():
                    return self._request(method, endpoint, data, params, retry_login=False)

            response.raise_for_status()
            result = response.json()

            return result

        except requests.exceptions.Timeout:
            logger.error(f"API 请求超时: {endpoint}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"API 请求异常: {e}")
            return None

    # ==================== 数据库管理 ====================

    def list_databases(self) -> List[Dict[str, Any]]:
        """列出所有数据库"""
        result = self._request("GET", "/database/")
        if result:
            return result.get("result", [])
        return []

    def create_database(
        self,
        name: str,
        sqlalchemy_uri: str,
        driver: str = "mysql+pymysql",
        extras: Dict[str, Any] = None,
    ) -> Optional[int]:
        """
        创建数据库

        Args:
            name: 数据库名称
            sqlalchemy_uri: SQLAlchemy URI
            driver: 数据库驱动
            extras: 额外配置

        Returns:
            数据库 ID
        """
        data = {
            "database_name": name,
            "sqlalchemy_uri": sqlalchemy_uri,
            "driver": driver,
            "extras": json.dumps(extras or {}),
            "masked_encrypted_extra": {},
            "cache_timeout": None,
            "expose_in_sqllab": True,
            "allow_run_async": True,
            "allow_ctas": True,
            "allow_dml": True,
            "force_ctas_schema": None,
        }

        result = self._request("POST", "/database/", data)
        if result:
            return result.get("id")
        return None

    def get_database_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取数据库"""
        databases = self.list_databases()
        for db in databases:
            if db.get("database_name") == name:
                return db
        return None

    def ensure_database(
        self,
        name: str,
        host: str,
        port: int,
        username: str,
        password: str,
        database: str,
    ) -> Optional[int]:
        """确保数据库存在（不存在则创建）"""
        existing = self.get_database_by_name(name)
        if existing:
            return existing.get("id")

        sqlalchemy_uri = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"

        return self.create_database(
            name=name,
            sqlalchemy_uri=sqlalchemy_uri,
            extras={
                "metadata_params": {},
                "engine_params": {},
                "connect_args": {
                    "charset": "utf8mb4",
                },
            },
        )

    # ==================== 数据集管理 ====================

    def list_datasets(self, database_id: int = None) -> List[Dict[str, Any]]:
        """列出数据集"""
        params = {}
        if database_id:
            params["database_id"] = database_id

        result = self._request("GET", "/dataset/", params=params)
        if result:
            return result.get("result", [])
        return []

    def create_dataset(
        self,
        database_id: int,
        schema: str,
        table_name: str,
        name: str = None,
    ) -> Optional[int]:
        """
        创建数据集

        Args:
            database_id: 数据库 ID
            schema: 数据库模式
            table_name: 表名
            name: 数据集名称（可选）

        Returns:
            数据集 ID
        """
        if not name:
            name = f"{schema}.{table_name}"

        # 需要先获取表的信息
        tables_result = self._request(
            "GET",
            f"/database/{database_id}/tables/",
            params={"schema": schema},
        )

        table_id = None
        if tables_result:
            for table in tables_result.get("result", []):
                if table.get("name") == table_name:
                    table_id = table.get("id")
                    break

        if not table_id:
            logger.error(f"表不存在: {schema}.{table_name}")
            return None

        # 创建数据集
        data = {
            "database": database_id,
            "schema": schema,
            "table_name": table_name,
            "name": name,
        }

        result = self._request("POST", "/dataset/", data)
        if result:
            return result.get("id")
        return None

    def get_dataset_by_name(
        self,
        database_id: int,
        schema: str,
        table_name: str,
    ) -> Optional[Dict[str, Any]]:
        """根据名称获取数据集"""
        datasets = self.list_datasets(database_id)
        for ds in datasets:
            if (ds.get("schema") == schema and
                ds.get("table_name") == table_name):
                return ds
        return None

    # ==================== 图表管理 ====================

    def list_charts(self, dataset_id: int = None) -> List[Dict[str, Any]]:
        """列出图表"""
        params = {}
        if dataset_id:
            params["datasource_id"] = dataset_id

        result = self._request("GET", "/chart/data", params=params)
        if result:
            return result.get("result", [])
        return []

    def create_chart(
        self,
        dataset_id: int,
        name: str,
        viz_type: str,
        params: Dict[str, Any],
        description: str = "",
    ) -> Optional[int]:
        """
        创建图表

        Args:
            dataset_id: 数据集 ID
            name: 图表名称
            viz_type: 可视化类型
            params: 图表参数
            description: 描述

        Returns:
            图表 ID
        """
        # 构建 queries 参数
        queries = [{
            "viz_type": viz_type,
            "time_range": "No filter",
            "groupby": params.get("dimensions", []),
            "metrics": params.get("metrics", []),
            "orderby": [],
            "row_limit": params.get("row_limit", 10000),
            "extras": {
                "having": "",
                "where": "",
            },
        }]

        data = {
            "datasource_id": dataset_id,
            "datasource_type": "table",
            "slice_name": name,
            "viz_type": viz_type,
            "params": json.dumps({
                "queries": queries,
                "description": description,
            }),
        }

        result = self._request("POST", "/chart/data", data)
        if result:
            return result.get("id")
        return None

    # ==================== 仪表板管理 ====================

    def list_dashboards(self) -> List[Dict[str, Any]]:
        """列出仪表板"""
        result = self._request("GET", "/dashboard/")
        if result:
            return result.get("result", [])
        return []

    def create_dashboard(
        self,
        name: str,
        description: str = "",
        json_metadata: str = None,
    ) -> Optional[int]:
        """
        创建仪表板

        Args:
            name: 仪表板名称
            description: 描述
            json_metadata: JSON 元数据

        Returns:
            仪表板 ID
        """
        data = {
            "dashboard_title": name,
            "description": description,
            "json_metadata": json_metadata or "{}",
            "owners": [self._get_current_user_id()],
        }

        result = self._request("POST", "/dashboard/", data)
        if result:
            return result.get("id")
        return None

    def _get_current_user_id(self) -> int:
        """获取当前用户 ID"""
        result = self._request("GET", "/me/")
        if result:
            return result.get("id", 1)
        return 1

    def add_chart_to_dashboard(
        self,
        dashboard_id: int,
        chart_id: int,
        position: Dict[str, Any] = None,
    ) -> bool:
        """
        添加图表到仪表板

        Args:
            dashboard_id: 仪表板 ID
            chart_id: 图表 ID
            position: 位置信息

        Returns:
            是否成功
        """
        # 获取仪表板现有配置
        result = self._request("GET", f"/dashboard/{dashboard_id}")
        if not result:
            return False

        dashboard = result.get("result", {})
        position_json = dashboard.get("position_json", "{}")

        try:
            positions = json.loads(position_json)
        except:
            positions = {}

        # 添加新图表位置
        positions[str(chart_id)] = position or {
            "type": "CHART",
            "size": "M",
            "col": 0,
            "row": 0,
        }

        # 更新仪表板
        update_data = {
            "position_json": json.dumps(positions),
        }

        result = self._request("PUT", f"/dashboard/{dashboard_id}", update_data)
        return result is not None


class SupersetSyncService:
    """Superset 同步服务

    将 One Data Studio 的元数据同步到 Superset
    """

    def __init__(
        self,
        superset_url: str = None,
        username: str = None,
        password: str = None,
    ):
        """
        初始化同步服务

        Args:
            superset_url: Superset URL
            username: 用户名
            password: 密码
        """
        self.client = SupersetClient(
            base_url=superset_url,
            username=username,
            password=password,
        )
        self._sync_cache: Dict[str, Any] = {}

    def sync_database(
        self,
        name: str,
        host: str,
        port: int,
        username: str,
        password: str,
        database: str,
    ) -> Optional[int]:
        """
        同步数据库到 Superset

        Args:
            name: 数据库名称
            host: 主机
            port: 端口
            username: 用户名
            password: 密码
            database: 数据库名

        Returns:
            数据库 ID
        """
        try:
            db_id = self.client.ensure_database(
                name=name,
                host=host,
                port=port,
                username=username,
                password=password,
                database=database,
            )

            if db_id:
                logger.info(f"数据库同步成功: {name} (ID: {db_id})")
                self._sync_cache[f"db:{name}"] = db_id
                return db_id
            else:
                logger.error(f"数据库同步失败: {name}")
                return None

        except Exception as e:
            logger.error(f"同步数据库异常: {e}")
            return None

    def sync_dataset(
        self,
        db_id: int,
        schema: str,
        table_name: str,
        dataset_name: str = None,
    ) -> Optional[int]:
        """
        同步数据集到 Superset

        Args:
            db_id: 数据库 ID
            schema: 模式名
            table_name: 表名
            dataset_name: 数据集名称

        Returns:
            数据集 ID
        """
        try:
            # 检查是否已存在
            existing = self.client.get_dataset_by_name(db_id, schema, table_name)
            if existing:
                logger.info(f"数据集已存在: {schema}.{table_name} (ID: {existing['id']})")
                return existing.get("id")

            # 创建数据集
            dataset_id = self.client.create_dataset(
                database_id=db_id,
                schema=schema,
                table_name=table_name,
                name=dataset_name,
            )

            if dataset_id:
                logger.info(f"数据集同步成功: {schema}.{table_name} (ID: {dataset_id})")
                self._sync_cache[f"dataset:{schema}.{table_name}"] = dataset_id
                return dataset_id
            else:
                logger.error(f"数据集同步失败: {schema}.{table_name}")
                return None

        except Exception as e:
            logger.error(f"同步数据集异常: {e}")
            return None

    def create_chart_from_bi_chart(
        self,
        bi_chart: Any,
        dataset_id: int,
    ) -> Optional[int]:
        """
        从 BIChart 创建 Superset 图表

        Args:
            bi_chart: BIChart 对象
            dataset_id: 数据集 ID

        Returns:
            图表 ID
        """
        try:
            # 映射图表类型
            viz_type = self._map_chart_type(bi_chart.chart_type)

            # 构建图表参数
            params = {
                "dimensions": bi_chart.dimensions or [],
                "metrics": bi_chart.metrics or [],
                "row_limit": 10000,
            }

            # 应用过滤器
            if bi_chart.filters:
                params["extras"] = {
                    "where": self._build_filter_clause(bi_chart.filters),
                }

            # 创建图表
            chart_id = self.client.create_chart(
                dataset_id=dataset_id,
                name=bi_chart.name,
                viz_type=viz_type,
                params=params,
                description=bi_chart.description or "",
            )

            if chart_id:
                logger.info(f"图表创建成功: {bi_chart.name} (ID: {chart_id})")
                return chart_id
            else:
                logger.error(f"图表创建失败: {bi_chart.name}")
                return None

        except Exception as e:
            logger.error(f"创建图表异常: {e}")
            return None

    def create_dashboard_from_bi_dashboard(
        self,
        bi_dashboard: Any,
        chart_map: Dict[str, int],
    ) -> Optional[int]:
        """
        从 BIDashboard 创建 Superset 仪表板

        Args:
            bi_dashboard: BIDashboard 对象
            chart_map: 图表名称到 Superset 图表 ID 的映射

        Returns:
            仪表板 ID
        """
        try:
            # 创建仪表板
            dashboard_id = self.client.create_dashboard(
                name=bi_dashboard.name,
                description=bi_dashboard.description or "",
            )

            if not dashboard_id:
                logger.error(f"仪表板创建失败: {bi_dashboard.name}")
                return None

            # 添加图表到仪表板
            position_data = json.loads(bi_dashboard.layout) if bi_dashboard.layout else {}
            row = 0
            col = 0

            for chart_ref in position_data.get("charts", []):
                chart_name = chart_ref.get("chart_id")
                superset_chart_id = chart_map.get(chart_name)

                if superset_chart_id:
                    self.client.add_chart_to_dashboard(
                        dashboard_id=dashboard_id,
                        chart_id=superset_chart_id,
                        position={
                            "type": "CHART",
                            "size": chart_ref.get("size", "M"),
                            "col": col % 12,
                            "row": row,
                        },
                    )
                    col += 1
                    if col % 12 == 0:
                        row += 1

            logger.info(f"仪表板创建成功: {bi_dashboard.name} (ID: {dashboard_id})")
            return dashboard_id

        except Exception as e:
            logger.error(f"创建仪表板异常: {e}")
            return None

    def _map_chart_type(self, chart_type: str) -> str:
        """映射图表类型"""
        mapping = {
            "line": SupersetChartType.ECHARTS_LINE.value,
            "bar": SupersetChartType.ECHARTS_BAR.value,
            "area": SupersetChartType.ECHARTS_AREA.value,
            "pie": SupersetChartType.ECHARTS_PIE.value,
            "scatter": SupersetChartType.ECHARTS_SCATTER.value,
            "table": SupersetChartType.TABLE.value,
            "big_number": SupersetChartType.BIG_NUMBER.value,
            "dist_bar": SupersetChartType.DIST_BAR.value,
            "treemap": SupersetChartType.TREEMAP.value,
            "heatmap": SupersetChartType.HEATMAP.value,
        }
        return mapping.get(chart_type, SupersetChartType.TABLE.value)

    def _build_filter_clause(self, filters: Dict[str, Any]) -> str:
        """构建过滤条件"""
        conditions = []
        for key, value in filters.items():
            if isinstance(value, str):
                conditions.append(f"`{key}` = '{value}'")
            elif isinstance(value, list):
                values = "', '".join(str(v) for v in value)
                conditions.append(f"`{key}` IN ('{values}')")
            else:
                conditions.append(f"`{key}` = {value}")
        return " AND ".join(conditions)


# 全局服务实例
_superset_sync_service: Optional[SupersetSyncService] = None


def get_superset_sync_service() -> SupersetSyncService:
    """获取 Superset 同步服务实例"""
    global _superset_sync_service
    if _superset_sync_service is None:
        _superset_sync_service = SupersetSyncService()
    return _superset_sync_service


# 导出
__all__ = [
    'SupersetChartType',
    'SupersetClient',
    'SupersetSyncService',
    'get_superset_sync_service',
]
