"""
E2E 测试 API 客户端

提供统一的 API 调用接口，封装所有数据治理平台的核心 API
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class E2EAPIClient:
    """E2E 测试 API 客户端"""

    def __init__(self, base_url: str = None, timeout: int = 30):
        """
        初始化 API 客户端

        Args:
            base_url: API 基础 URL，默认从环境变量读取
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url or os.getenv(
            "API_BASE_URL",
            "http://localhost:8001/api/v1"
        )
        self.timeout = timeout

        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session = requests.Session()
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # 默认请求头
        self.default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Dict[str, Any] = None,
        params: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        发送 HTTP 请求

        Args:
            method: HTTP 方法 (GET, POST, PUT, DELETE)
            endpoint: API 端点
            data: 请求体数据
            params: 查询参数
            headers: 请求头

        Returns:
            (success, response_data)
        """
        url = f"{self.base_url}{endpoint}"
        req_headers = {**self.default_headers, **(headers or {})}

        try:
            if method.upper() == "GET":
                response = self.session.get(
                    url,
                    params=params,
                    headers=req_headers,
                    timeout=self.timeout,
                )
            elif method.upper() == "POST":
                response = self.session.post(
                    url,
                    json=data,
                    params=params,
                    headers=req_headers,
                    timeout=self.timeout,
                )
            elif method.upper() == "PUT":
                response = self.session.put(
                    url,
                    json=data,
                    params=params,
                    headers=req_headers,
                    timeout=self.timeout,
                )
            elif method.upper() == "DELETE":
                response = self.session.delete(
                    url,
                    params=params,
                    headers=req_headers,
                    timeout=self.timeout,
                )
            else:
                return False, {"error": f"Unsupported method: {method}"}

            response.raise_for_status()
            return True, response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {method} {url} - {e}")
            return False, {"error": str(e)}

    # ========================================================================
    # 模块 1: 数据源管理
    # ========================================================================

    def create_datasource(
        self,
        name: str,
        db_type: str,
        host: str,
        port: int,
        username: str,
        password: str,
        database: str = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        创建数据源

        Args:
            name: 数据源名称
            db_type: 数据库类型 (mysql, postgresql, etc.)
            host: 主机地址
            port: 端口
            username: 用户名
            password: 密码
            database: 数据库名称

        Returns:
            (success, response_data)
        """
        data = {
            "name": name,
            "type": db_type,
            "host": host,
            "port": port,
            "username": username,
            "password": password,
        }
        if database:
            data["database"] = database

        return self._request("POST", "/datasources", data=data)

    def test_connection(self, datasource_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        测试数据源连接

        Args:
            datasource_id: 数据源 ID

        Returns:
            (success, response_data)
        """
        return self._request("POST", f"/datasources/{datasource_id}/test")

    def get_datasources(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        获取数据源列表

        Returns:
            (success, datasources_list)
        """
        success, data = self._request("GET", "/datasources")
        if success and "data" in data:
            return True, data["data"]
        return success, []

    def get_datasource(self, datasource_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        获取单个数据源

        Args:
            datasource_id: 数据源 ID

        Returns:
            (success, datasource_data)
        """
        return self._request("GET", f"/datasources/{datasource_id}")

    def update_datasource(
        self, datasource_id: str, **kwargs
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        更新数据源

        Args:
            datasource_id: 数据源 ID
            **kwargs: 要更新的字段

        Returns:
            (success, response_data)
        """
        return self._request("PUT", f"/datasources/{datasource_id}", data=kwargs)

    def delete_datasource(self, datasource_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        删除数据源

        Args:
            datasource_id: 数据源 ID

        Returns:
            (success, response_data)
        """
        return self._request("DELETE", f"/datasources/{datasource_id}")

    # ========================================================================
    # 模块 2: 元数据管理
    # ========================================================================

    def scan_metadata(
        self,
        datasource_id: str,
        database: str = None,
        tables: List[str] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        扫描元数据

        Args:
            datasource_id: 数据源 ID
            database: 数据库名称（可选）
            tables: 表名列表（可选）

        Returns:
            (success, response_data)
        """
        data = {}
        if database:
            data["database"] = database
        if tables:
            data["tables"] = tables

        return self._request("POST", f"/datasources/{datasource_id}/scan", data=data)

    def get_databases(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        获取数据库列表

        Returns:
            (success, databases_list)
        """
        success, data = self._request("GET", "/metadata/databases")
        if success and "data" in data:
            return True, data["data"].get("databases", [])
        return success, []

    def get_tables(self, database: str) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        获取表列表

        Args:
            database: 数据库名称

        Returns:
            (success, tables_list)
        """
        success, data = self._request("GET", f"/metadata/databases/{database}/tables")
        if success and "data" in data:
            return True, data["data"].get("tables", [])
        return success, []

    def get_table_metadata(
        self, database: str, table: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        获取表元数据

        Args:
            database: 数据库名称
            table: 表名

        Returns:
            (success, table_metadata)
        """
        success, data = self._request(
            "GET", f"/metadata/databases/{database}/tables/{table}"
        )
        if success and "data" in data:
            return True, data["data"]
        return success, {}

    def search_metadata(self, keyword: str) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        搜索元数据

        Args:
            keyword: 搜索关键词

        Returns:
            (success, search_results)
        """
        success, data = self._request("GET", "/metadata/search", params={"q": keyword})
        if success and "data" in data:
            return True, data["data"]
        return success, []

    # ========================================================================
    # 模块 3: 数据版本管理
    # ========================================================================

    def create_snapshot(
        self,
        database: str,
        tables: List[str] = None,
        version: str = None,
        description: str = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        创建版本快照

        Args:
            database: 数据库名称
            tables: 表名列表
            version: 版本号
            description: 描述

        Returns:
            (success, response_data)
        """
        data = {
            "database": database,
        }
        if tables:
            data["tables"] = tables
        if version:
            data["version"] = version
        if description:
            data["description"] = description

        return self._request("POST", "/metadata/versions/snapshot", data=data)

    def list_snapshots(
        self, database: str, limit: int = 10
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        获取版本快照列表

        Args:
            database: 数据库名称
            limit: 返回数量限制

        Returns:
            (success, snapshots_list)
        """
        success, data = self._request(
            "GET", f"/metadata/versions", params={"database": database, "limit": limit}
        )
        if success and "data" in data:
            return True, data["data"]
        return success, []

    def get_snapshot(self, snapshot_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        获取快照详情

        Args:
            snapshot_id: 快照 ID

        Returns:
            (success, snapshot_data)
        """
        success, data = self._request("GET", f"/metadata/versions/{snapshot_id}")
        if success and "data" in data:
            return True, data["data"]
        return success, {}

    def compare_snapshots(
        self, from_snapshot_id: str, to_snapshot_id: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        比较两个快照

        Args:
            from_snapshot_id: 源快照 ID
            to_snapshot_id: 目标快照 ID

        Returns:
            (success, comparison_result)
        """
        success, data = self._request(
            "POST",
            f"/metadata/versions/compare",
            data={"from": from_snapshot_id, "to": to_snapshot_id},
        )
        if success and "data" in data:
            return True, data["data"]
        return success, {}

    def rollback_snapshot(
        self, snapshot_id: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        回滚到指定快照

        Args:
            snapshot_id: 快照 ID

        Returns:
            (success, response_data)
        """
        return self._request("POST", f"/metadata/versions/{snapshot_id}/rollback")

    # ========================================================================
    # 模块 4: 特征管理
    # ========================================================================

    def create_feature_group(
        self,
        name: str,
        description: str = None,
        entity_type: str = None,
        tags: List[str] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        创建特征组

        Args:
            name: 特征组名称
            description: 描述
            entity_type: 实体类型
            tags: 标签列表

        Returns:
            (success, response_data)
        """
        data = {"name": name}
        if description:
            data["description"] = description
        if entity_type:
            data["entity_type"] = entity_type
        if tags:
            data["tags"] = tags

        return self._request("POST", "/feature-groups", data=data)

    def get_feature_groups(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        获取特征组列表

        Returns:
            (success, feature_groups_list)
        """
        success, data = self._request("GET", "/feature-groups")
        if success and "data" in data:
            return True, data["data"]
        return success, []

    def get_feature_group(self, group_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        获取特征组详情

        Args:
            group_id: 特征组 ID

        Returns:
            (success, feature_group_data)
        """
        success, data = self._request("GET", f"/feature-groups/{group_id}")
        if success and "data" in data:
            return True, data["data"]
        return success, {}

    def create_feature(
        self,
        group_id: str,
        name: str,
        feature_type: str,
        description: str = None,
        data_source: str = None,
        sql_expression: str = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        创建特征

        Args:
            group_id: 特征组 ID
            name: 特征名称
            feature_type: 特征类型
            description: 描述
            data_source: 数据源
            sql_expression: SQL 表达式

        Returns:
            (success, response_data)
        """
        data = {
            "name": name,
            "type": feature_type,
        }
        if description:
            data["description"] = description
        if data_source:
            data["data_source"] = data_source
        if sql_expression:
            data["sql_expression"] = sql_expression

        return self._request("POST", f"/feature-groups/{group_id}/features", data=data)

    def get_features(self, group_id: str) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        获取特征列表

        Args:
            group_id: 特征组 ID

        Returns:
            (success, features_list)
        """
        success, data = self._request("GET", f"/feature-groups/{group_id}/features")
        if success and "data" in data:
            return True, data["data"]
        return success, []

    # ========================================================================
    # 模块 5: 数据标准
    # ========================================================================

    def create_data_standard(
        self,
        name: str,
        standard_type: str,
        description: str = None,
        rules: List[Dict[str, Any]] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        创建数据标准

        Args:
            name: 标准名称
            standard_type: 标准类型
            description: 描述
            rules: 规则列表

        Returns:
            (success, response_data)
        """
        data = {
            "name": name,
            "type": standard_type,
        }
        if description:
            data["description"] = description
        if rules:
            data["rules"] = rules

        return self._request("POST", "/standards", data=data)

    def get_data_standards(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        获取数据标准列表

        Returns:
            (success, standards_list)
        """
        success, data = self._request("GET", "/standards")
        if success and "data" in data:
            return True, data["data"]
        return success, []

    def create_standard_element(
        self,
        name: str,
        element_type: str,
        value_constraint: Dict[str, Any] = None,
        description: str = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        创建标准元素

        Args:
            name: 元素名称
            element_type: 元素类型
            value_constraint: 值约束
            description: 描述

        Returns:
            (success, response_data)
        """
        data = {
            "name": name,
            "type": element_type,
        }
        if value_constraint:
            data["value_constraint"] = value_constraint
        if description:
            data["description"] = description

        return self._request("POST", "/standards/elements", data=data)

    def apply_standard(
        self, standard_id: str, target_database: str, target_table: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        应用数据标准

        Args:
            standard_id: 标准 ID
            target_database: 目标数据库
            target_table: 目标表

        Returns:
            (success, response_data)
        """
        return self._request(
            "POST",
            f"/standards/{standard_id}/apply",
            data={"database": target_database, "table": target_table},
        )

    def validate_standard(
        self, standard_id: str, database: str, table: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        验证数据标准

        Args:
            standard_id: 标准 ID
            database: 数据库名称
            table: 表名

        Returns:
            (success, validation_result)
        """
        success, data = self._request(
            "POST",
            f"/standards/{standard_id}/validate",
            data={"database": database, "table": table},
        )
        if success and "data" in data:
            return True, data["data"]
        return success, {}

    # ========================================================================
    # 模块 6: 数据资产
    # ========================================================================

    def register_asset(
        self,
        name: str,
        asset_type: str,
        datasource_id: str,
        database: str,
        table: str,
        description: str = None,
        business_terms: List[str] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        注册数据资产

        Args:
            name: 资产名称
            asset_type: 资产类型
            datasource_id: 数据源 ID
            database: 数据库名称
            table: 表名
            description: 描述
            business_terms: 业务术语

        Returns:
            (success, response_data)
        """
        data = {
            "name": name,
            "type": asset_type,
            "datasource_id": datasource_id,
            "database": database,
            "table": table,
        }
        if description:
            data["description"] = description
        if business_terms:
            data["business_terms"] = business_terms

        return self._request("POST", "/assets", data=data)

    def get_assets(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        获取资产列表

        Returns:
            (success, assets_list)
        """
        success, data = self._request("GET", "/assets")
        if success and "data" in data:
            return True, data["data"]
        return success, []

    def get_asset(self, asset_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        获取资产详情

        Args:
            asset_id: 资产 ID

        Returns:
            (success, asset_data)
        """
        success, data = self._request("GET", f"/assets/{asset_id}")
        if success and "data" in data:
            return True, data["data"]
        return success, {}

    def evaluate_asset_value(self, asset_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        评估资产价值

        Args:
            asset_id: 资产 ID

        Returns:
            (success, evaluation_result)
        """
        success, data = self._request("POST", f"/assets/{asset_id}/evaluate")
        if success and "data" in data:
            return True, data["data"]
        return success, {}

    def get_asset_lineage(self, asset_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        获取资产血缘

        Args:
            asset_id: 资产 ID

        Returns:
            (success, lineage_data)
        """
        success, data = self._request("GET", f"/assets/{asset_id}/lineage")
        if success and "data" in data:
            return True, data["data"]
        return success, {}

    def get_asset_collections(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        获取资产集合列表

        Returns:
            (success, collections_list)
        """
        success, data = self._request("GET", "/assets/collections")
        if success and "data" in data:
            return True, data["data"]
        return success, []

    # ========================================================================
    # 健康检查
    # ========================================================================

    def health_check(self) -> Tuple[bool, Dict[str, Any]]:
        """
        健康检查

        Returns:
            (success, health_data)
        """
        try:
            response = self.session.get(
                f"{self.base_url.replace('/api/v1', '')}/health",
                timeout=self.timeout,
            )
            response.raise_for_status()
            return True, response.json()
        except requests.exceptions.RequestException as e:
            return False, {"error": str(e)}
