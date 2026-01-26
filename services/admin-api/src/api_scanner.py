"""
API扫描器 - 自动发现和注册API端点
Phase 2.2: API可视化管理
"""

import logging
import re
from typing import Dict, List, Any, Optional
from flask import Blueprint
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from database import db_manager
from models.api_call_log import ApiEndpoint, ApiCallLog

logger = logging.getLogger(__name__)


class ApiScanner:
    """API扫描器 - 自动发现API端点"""

    def __init__(self):
        self.endpoints_cache: Dict[str, List[Dict[str, Any]]] = {}

    def scan_app(self, app) -> Dict[str, Any]:
        """
        扫描Flask应用的所有路由

        Args:
            app: Flask应用实例

        Returns:
            扫描结果
        """
        endpoints = {
            "total": 0,
            "by_method": {},
            "by_blueprint": {},
            "endpoints": [],
        }

        for rule in app.url_map.iter_rules():
            # 跳过静态文件和内部路由
            if self._should_skip_rule(rule):
                continue

            endpoint_info = self._parse_rule(rule)
            if endpoint_info:
                endpoints["endpoints"].append(endpoint_info)
                endpoints["total"] += 1

                # 按方法统计
                for method in endpoint_info["methods"]:
                    if method not in endpoints["by_method"]:
                        endpoints["by_method"][method] = 0
                    endpoints["by_method"][method] += 1

                # 按蓝图统计
                blueprint = endpoint_info["blueprint"]
                if blueprint not in endpoints["by_blueprint"]:
                    endpoints["by_blueprint"][blueprint] = 0
                endpoints["by_blueprint"][blueprint] += 1

        return endpoints

    def _should_skip_rule(self, rule) -> bool:
        """判断是否跳过该路由"""
        # 跳过静态文件
        if rule.rule.startswith('/static'):
            return True

        # 跳过Flask内部路由
        if rule.endpoint.startswith('static'):
            return True
        if rule.endpoint == 'root':
            return True

        return False

    def _parse_rule(self, rule) -> Optional[Dict[str, Any]]:
        """解析路由规则"""
        try:
            methods = [m for m in rule.methods if m not in ['HEAD', 'OPTIONS']]

            if not methods:
                return None

            # 提取蓝图名称
            blueprint = 'default'
            if '.' in rule.endpoint:
                blueprint = rule.endpoint.split('.')[0]

            # 提取路径参数
            path_params = re.findall(r'<(\w+):?([^>]+)?>', rule.rule)
            parameters = []
            for param in path_params:
                parameters.append({
                    "name": param[0],
                    "type": param[1] if param[1] else "string",
                })

            # 生成描述（基于端点名称）
            description = self._generate_description(rule.endpoint)

            return {
                "path": rule.rule,
                "methods": methods,
                "endpoint": rule.endpoint,
                "blueprint": blueprint,
                "parameters": parameters,
                "description": description,
            }

        except Exception as e:
            logger.warning(f"Error parsing rule {rule}: {e}")
            return None

    def _generate_description(self, endpoint: str) -> str:
        """基于端点名称生成描述"""
        # 移除常见的类名前缀
        name = endpoint.split('.')[-1]

        # 替换下划线为空格
        name = re.sub(r'_+', ' ', name)

        # 首字母大写
        return name.capitalize()

    def register_endpoints(self, endpoints: List[Dict[str, Any]], service: str) -> int:
        """
        注册API端点到数据库

        Args:
            endpoints: 端点列表
            service: 服务名称

        Returns:
            注册数量
        """
        count = 0
        with db_manager.get_session() as session:
            for ep in endpoints:
                # 检查是否已存在
                existing = session.query(ApiEndpoint).filter(
                    ApiEndpoint.path == ep["path"],
                    ApiEndpoint.method == ep["methods"][0]  # 使用第一个方法
                ).first()

                if not existing:
                    api_ep = ApiEndpoint(
                        path=ep["path"],
                        method=ep["methods"][0],
                        service=service,
                        blueprint=ep.get("blueprint", "default"),
                        endpoint_name=ep["endpoint"],
                        description=ep.get("description", ""),
                        parameters=ep.get("parameters", []),
                        request_schema=self._infer_schema(ep),
                        response_schema=self._infer_response_schema(ep),
                    )
                    session.add(api_ep)
                    count += 1
                else:
                    # 更新最后调用时间
                    existing.last_called = None  # 由监控模块更新

            session.commit()

        logger.info(f"Registered {count} new endpoints for service {service}")
        return count

    def _infer_schema(self, endpoint_info: Dict[str, Any]) -> Dict[str, Any]:
        """推断请求模式"""
        # 基于路径参数推断
        parameters = endpoint_info.get("parameters", [])
        schema = {
            "type": "object",
            "properties": {},
            "required": [],
        }

        for param in parameters:
            param_type = "string"
            if param["type"] in ["int", "integer", "long"]:
                param_type = "integer"
            elif param["type"] in ["float", "double"]:
                param_type = "number"
            elif param["type"] == "bool":
                param_type = "boolean"

            schema["properties"][param["name"]] = {
                "type": param_type,
                "in": "path",
            }
            schema["required"].append(param["name"])

        return schema

    def _infer_response_schema(self, endpoint_info: Dict[str, Any]) -> Dict[str, Any]:
        """推断响应模式"""
        # 基于端点名称推断
        endpoint = endpoint_info["endpoint"].lower()

        if "list" in endpoint or "get" in endpoint:
            return {
                "type": "object",
                "properties": {
                    "code": {"type": "integer"},
                    "message": {"type": "string"},
                    "data": {"type": "array"},
                },
            }

        return {
            "type": "object",
            "properties": {
                "code": {"type": "integer"},
                "message": {"type": "string"},
            },
        }


class ApiMonitor:
    """API监控器 - 记录和分析API调用"""

    def log_call(
        self,
        path: str,
        method: str,
        user_id: str,
        username: Optional[str],
        status_code: int,
        duration_ms: int,
        request_body: Optional[str] = None,
        response_body: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        """
        记录API调用

        Args:
            path: 请求路径
            method: 请求方法
            user_id: 用户ID
            username: 用户名
            status_code: 响应状态码
            duration_ms: 耗时（毫秒）
            request_body: 请求体
            response_body: 响应体
            error_message: 错误信息
        """
        try:
            log = ApiCallLog(
                path=path,
                method=method,
                user_id=user_id,
                username=username,
                status_code=status_code,
                duration_ms=duration_ms,
                request_body=self._sanitize_body(request_body, "request"),
                response_body=self._sanitize_body(response_body, "response"),
                error_message=error_message,
            )

            with db_manager.get_session() as session:
                session.add(log)
                session.commit()

        except Exception as e:
            logger.error(f"Error logging API call: {e}")

    def _sanitize_body(self, body: Optional[str], body_type: str) -> Optional[str]:
        """清理请求/响应体（隐藏敏感信息）"""
        if not body:
            return None

        # 截断过长的body
        if len(body) > 10000:
            body = body[:10000] + "...(truncated)"

        # 隐藏敏感字段
        import re
        body = re.sub(r'("password"\s*:\s*")([^"]+)(")', r'\1***\3', body, flags=re.IGNORECASE)
        body = re.sub(r'("token"\s*:\s*")([^"]+)(")', r'\1***\3', body, flags=re.IGNORECASE)
        body = re.sub(r'("api_key"\s*:\s*")([^"]+)(")', r'\1***\3', body, flags=re.IGNORECASE)

        return body

    def get_statistics(
        self,
        service: Optional[str] = None,
        days: int = 7,
    ) -> Dict[str, Any]:
        """
        获取API调用统计

        Args:
            service: 服务名称过滤
            days: 统计天数

        Returns:
            统计数据
        """
        from datetime import datetime, timedelta

        start_time = datetime.utcnow() - timedelta(days=days)

        with db_manager.get_session() as session:
            query = session.query(ApiCallLog).filter(
                ApiCallLog.created_at >= start_time
            )

            if service:
                # 简单的路径前缀过滤
                query = query.filter(ApiCallLog.path.like(f'/%{service}%'))

            total_calls = query.count()

            # 按状态码统计
            status_distribution = dict(
                session.query(
                    ApiCallLog.status_code,
                    func.count(ApiCallLog.id)
                ).filter(
                    ApiCallLog.created_at >= start_time
                ).group_by(ApiCallLog.status_code).all()
            )

            # 按方法统计
            method_distribution = dict(
                session.query(
                    ApiCallLog.method,
                    func.count(ApiCallLog.id)
                ).filter(
                    ApiCallLog.created_at >= start_time
                ).group_by(ApiCallLog.method).all()
            )

            # 最慢的API
            slowest_apis = session.query(
                ApiCallLog.path,
                ApiCallLog.method,
                func.avg(ApiCallLog.duration_ms).label('avg_duration')
            ).filter(
                ApiCallLog.created_at >= start_time
            ).group_by(
                ApiCallLog.path,
                ApiCallLog.method
            ).order_by(
                func.avg(ApiCallLog.duration_ms).desc()
            ).limit(10).all()

            # 错误率
            error_calls = query.filter(ApiCallLog.status_code >= 400).count()

            return {
                "total_calls": total_calls,
                "error_rate": error_calls / total_calls if total_calls > 0 else 0,
                "avg_duration": session.query(func.avg(ApiCallLog.duration_ms)).filter(
                    ApiCallLog.created_at >= start_time
                ).scalar() or 0,
                "status_distribution": status_distribution,
                "method_distribution": method_distribution,
                "slowest_apis": [
                    {"path": r[0], "method": r[1], "avg_duration": float(r[2])}
                    for r in slowest_apis
                ],
                "period_days": days,
            }

    def get_slow_queries(
        self,
        threshold_ms: int = 1000,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """获取慢查询列表"""
        from datetime import datetime, timedelta

        start_time = datetime.utcnow() - timedelta(days=1)

        with db_manager.get_session() as session:
            logs = session.query(ApiCallLog).filter(
                ApiCallLog.created_at >= start_time,
                ApiCallLog.duration_ms >= threshold_ms
            ).order_by(
                ApiCallLog.duration_ms.desc()
            ).limit(limit).all()

            return [log.to_dict() for l in logs]


# 全局实例
_api_scanner: Optional[ApiScanner] = None
_api_monitor: Optional[ApiMonitor] = None


def get_api_scanner() -> ApiScanner:
    """获取API扫描器单例"""
    global _api_scanner
    if _api_scanner is None:
        _api_scanner = ApiScanner()
    return _api_scanner


def get_api_monitor() -> ApiMonitor:
    """获取API监控器单例"""
    global _api_monitor
    if _api_monitor is None:
        _api_monitor = ApiMonitor()
    return _api_monitor
