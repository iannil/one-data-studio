"""
OpenMetadata API 客户端

提供对 OpenMetadata REST API 的封装访问
参考: https://docs.open-metadata.org/latest/main-concepts/metadata-standard/apis
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import OpenMetadataConfig, get_config

logger = logging.getLogger(__name__)


class OpenMetadataClient:
    """OpenMetadata REST API 客户端"""

    def __init__(self, config: Optional[OpenMetadataConfig] = None):
        """
        初始化客户端

        Args:
            config: 配置对象，如果为 None 则从环境变量加载
        """
        self.config = config or get_config()
        self._session: Optional[requests.Session] = None

    @property
    def session(self) -> requests.Session:
        """获取带重试机制的 HTTP 会话"""
        if self._session is None:
            self._session = requests.Session()

            # 配置重试策略
            retry_strategy = Retry(
                total=3,
                backoff_factor=0.5,
                status_forcelist=[500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)

            # 设置默认头
            self._session.headers.update({
                "Content-Type": "application/json",
                "Accept": "application/json",
            })

            # 如果有 JWT token，添加认证头
            if self.config.jwt_token:
                self._session.headers["Authorization"] = f"Bearer {self.config.jwt_token}"

        return self._session

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        发送 HTTP 请求

        Args:
            method: HTTP 方法
            endpoint: API 端点（不含基础 URL）
            data: 请求体数据
            params: URL 查询参数

        Returns:
            响应 JSON 数据

        Raises:
            requests.HTTPError: 请求失败时
        """
        url = f"{self.config.base_url}/{endpoint.lstrip('/')}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            return response.json() if response.text else {}
        except requests.exceptions.RequestException as e:
            logger.error("OpenMetadata API request failed: %s %s - %s", method, url, e)
            raise

    # ========================================
    # 健康检查
    # ========================================

    def health_check(self) -> bool:
        """
        检查 OpenMetadata 服务健康状态

        Returns:
            True 如果服务健康，否则 False
        """
        if not self.config.enabled:
            return False

        try:
            response = self.session.get(
                self.config.health_url,
                timeout=5
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    # ========================================
    # 数据库服务 API
    # ========================================

    def list_database_services(self, limit: int = 100) -> List[Dict]:
        """
        列出所有数据库服务

        Args:
            limit: 返回数量限制

        Returns:
            数据库服务列表
        """
        result = self._request("GET", "services/databaseServices", params={"limit": limit})
        return result.get("data", [])

    def create_database_service(
        self,
        name: str,
        service_type: str = "Mysql",
        description: Optional[str] = None,
        connection_config: Optional[Dict] = None,
    ) -> Dict:
        """
        创建数据库服务

        Args:
            name: 服务名称
            service_type: 服务类型 (Mysql, Postgres, etc.)
            description: 描述
            connection_config: 连接配置

        Returns:
            创建的服务对象
        """
        data = {
            "name": name,
            "serviceType": service_type,
        }
        if description:
            data["description"] = description
        if connection_config:
            data["connection"] = {"config": connection_config}

        return self._request("POST", "services/databaseServices", data=data)

    def get_database_service(self, service_name: str) -> Optional[Dict]:
        """获取数据库服务详情"""
        try:
            return self._request("GET", f"services/databaseServices/name/{service_name}")
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    # ========================================
    # 数据库 API
    # ========================================

    def list_databases(self, service: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """
        列出数据库

        Args:
            service: 过滤特定服务的数据库
            limit: 返回数量限制

        Returns:
            数据库列表
        """
        params = {"limit": limit}
        if service:
            params["service"] = service

        result = self._request("GET", "databases", params=params)
        return result.get("data", [])

    def create_database(
        self,
        name: str,
        service_fqn: str,
        description: Optional[str] = None,
    ) -> Dict:
        """
        创建数据库

        Args:
            name: 数据库名称
            service_fqn: 所属服务的完全限定名
            description: 描述

        Returns:
            创建的数据库对象
        """
        data = {
            "name": name,
            "service": service_fqn,
        }
        if description:
            data["description"] = description

        return self._request("POST", "databases", data=data)

    def get_database(self, database_fqn: str) -> Optional[Dict]:
        """获取数据库详情"""
        try:
            return self._request("GET", f"databases/name/{database_fqn}")
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    # ========================================
    # 表 API
    # ========================================

    def list_tables(
        self,
        database: Optional[str] = None,
        limit: int = 100,
        include_columns: bool = False,
    ) -> List[Dict]:
        """
        列出表

        Args:
            database: 过滤特定数据库的表
            limit: 返回数量限制
            include_columns: 是否包含列信息

        Returns:
            表列表
        """
        params = {"limit": limit}
        if database:
            params["database"] = database
        if include_columns:
            params["fields"] = "columns"

        result = self._request("GET", "tables", params=params)
        return result.get("data", [])

    def create_table(
        self,
        name: str,
        database_fqn: str,
        columns: List[Dict],
        description: Optional[str] = None,
        table_type: str = "Regular",
        custom_properties: Optional[Dict] = None,
    ) -> Dict:
        """
        创建表

        Args:
            name: 表名
            database_fqn: 所属数据库的完全限定名
            columns: 列定义列表
            description: 描述
            table_type: 表类型
            custom_properties: 自定义属性

        Returns:
            创建的表对象
        """
        data = {
            "name": name,
            "databaseSchema": database_fqn,
            "columns": columns,
            "tableType": table_type,
        }
        if description:
            data["description"] = description
        if custom_properties:
            data["customProperties"] = custom_properties

        return self._request("POST", "tables", data=data)

    def get_table(self, table_fqn: str, include_columns: bool = True) -> Optional[Dict]:
        """获取表详情"""
        try:
            params = {}
            if include_columns:
                params["fields"] = "columns,tableConstraints"
            return self._request("GET", f"tables/name/{table_fqn}", params=params)
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def update_table(self, table_fqn: str, updates: Dict) -> Dict:
        """更新表"""
        return self._request("PATCH", f"tables/name/{table_fqn}", data=updates)

    # ========================================
    # 血缘 API
    # ========================================

    def add_lineage(
        self,
        from_entity_type: str,
        from_entity_fqn: str,
        to_entity_type: str,
        to_entity_fqn: str,
        description: Optional[str] = None,
    ) -> Dict:
        """
        添加血缘关系

        Args:
            from_entity_type: 源实体类型 (table, pipeline, etc.)
            from_entity_fqn: 源实体完全限定名
            to_entity_type: 目标实体类型
            to_entity_fqn: 目标实体完全限定名
            description: 描述

        Returns:
            血缘关系对象
        """
        data = {
            "edge": {
                "fromEntity": {
                    "type": from_entity_type,
                    "fqn": from_entity_fqn,
                },
                "toEntity": {
                    "type": to_entity_type,
                    "fqn": to_entity_fqn,
                },
            }
        }
        if description:
            data["edge"]["description"] = description

        return self._request("PUT", "lineage", data=data)

    def get_lineage(
        self,
        entity_type: str,
        entity_fqn: str,
        upstream_depth: int = 3,
        downstream_depth: int = 3,
    ) -> Dict:
        """
        获取实体的血缘关系

        Args:
            entity_type: 实体类型
            entity_fqn: 实体完全限定名
            upstream_depth: 上游深度
            downstream_depth: 下游深度

        Returns:
            血缘关系图
        """
        params = {
            "upstreamDepth": upstream_depth,
            "downstreamDepth": downstream_depth,
        }
        return self._request(
            "GET",
            f"lineage/{entity_type}/name/{entity_fqn}",
            params=params
        )

    # ========================================
    # 搜索 API
    # ========================================

    def search(
        self,
        query: str,
        index: str = "table_search_index",
        limit: int = 10,
        offset: int = 0,
    ) -> Dict:
        """
        搜索实体

        Args:
            query: 搜索查询
            index: 搜索索引
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            搜索结果
        """
        params = {
            "q": query,
            "index": index,
            "from": offset,
            "size": limit,
        }
        return self._request("GET", "search/query", params=params)

    # ========================================
    # 数据质量 API
    # ========================================

    def create_test_case(
        self,
        table_fqn: str,
        test_type: str,
        test_name: str,
        parameters: Optional[Dict] = None,
    ) -> Dict:
        """
        创建数据质量测试用例

        Args:
            table_fqn: 表的完全限定名
            test_type: 测试类型
            test_name: 测试名称
            parameters: 测试参数

        Returns:
            测试用例对象
        """
        data = {
            "name": test_name,
            "entityLink": f"<#E::table::{table_fqn}>",
            "testDefinition": test_type,
            "parameterValues": parameters or [],
        }
        return self._request("POST", "dataQuality/testCases", data=data)

    def list_test_cases(self, table_fqn: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """列出数据质量测试用例"""
        params = {"limit": limit}
        if table_fqn:
            params["entityLink"] = f"<#E::table::{table_fqn}>"

        result = self._request("GET", "dataQuality/testCases", params=params)
        return result.get("data", [])


# 全局客户端实例
_client: Optional[OpenMetadataClient] = None


def get_client() -> OpenMetadataClient:
    """获取全局客户端实例（单例）"""
    global _client
    if _client is None:
        _client = OpenMetadataClient()
    return _client
