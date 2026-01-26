"""
数据服务接口管理服务
支持 API 服务创建、认证管理、调用追踪、统计分析
"""

import logging
import secrets
import hashlib
import hmac
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

logger = logging.getLogger(__name__)


class APIKey:
    """API 密钥"""

    def __init__(
        self,
        key_id: str,
        key_secret: str,
        name: str,
        user_id: str,
        scopes: List[str] = None,
        expires_at: datetime = None,
    ):
        self.key_id = key_id
        self.key_secret = key_secret  # 只在创建时返回，之后不可见
        self.name = name
        self.user_id = user_id
        self.scopes = scopes or ["read"]
        self.created_at = datetime.now()
        self.expires_at = expires_at
        self.last_used = None
        self.is_active = True

    def to_dict(self, include_secret: bool = False) -> Dict:
        result = {
            "key_id": self.key_id,
            "name": self.name,
            "user_id": self.user_id,
            "scopes": self.scopes,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "is_active": self.is_active,
        }
        if include_secret:
            result["key_secret"] = self.key_secret
        return result

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


class DataService:
    """数据服务定义"""

    def __init__(
        self,
        service_id: str,
        name: str,
        description: str,
        service_type: str,  # rest, graphql
        source_type: str,  # table, query, dataset
        source_config: Dict,
        endpoint: str,
        method: str = "GET",
        created_by: str = "",
    ):
        self.service_id = service_id
        self.name = name
        self.description = description
        self.service_type = service_type
        self.source_type = source_type
        self.source_config = source_config
        self.endpoint = endpoint
        self.method = method
        self.created_by = created_by
        self.created_at = datetime.now()
        self.updated_at = None
        self.status = "draft"  # draft, published, archived
        self.version = 1
        self.tags: List[str] = []
        self.rate_limit = None  # {requests_per_minute: 60}

    def to_dict(self) -> Dict:
        return {
            "service_id": self.service_id,
            "name": self.name,
            "description": self.description,
            "service_type": self.service_type,
            "source_type": self.source_type,
            "source_config": self._sanitize_source_config(),
            "endpoint": self.endpoint,
            "method": self.method,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "status": self.status,
            "version": self.version,
            "tags": self.tags,
            "rate_limit": self.rate_limit,
        }

    def _sanitize_source_config(self) -> Dict:
        """脱敏敏感配置"""
        config = self.source_config.copy()
        if "password" in config:
            config["password"] = "******"
        if "api_key" in config:
            config["api_key"] = config["api_key"][:4] + "****" if len(config["api_key"]) > 4 else "****"
        return config


class APICallRecord:
    """API 调用记录"""

    def __init__(
        self,
        call_id: str,
        service_id: str,
        api_key_id: str,
        method: str,
        path: str,
        status_code: int,
        latency_ms: int,
        request_size: int = 0,
        response_size: int = 0,
        error_message: str = "",
    ):
        self.call_id = call_id
        self.service_id = service_id
        self.api_key_id = api_key_id
        self.method = method
        self.path = path
        self.status_code = status_code
        self.latency_ms = latency_ms
        self.request_size = request_size
        self.response_size = response_size
        self.error_message = error_message
        self.timestamp = datetime.now()
        self.ip_address = ""
        self.user_agent = ""

    def to_dict(self) -> Dict:
        return {
            "call_id": self.call_id,
            "service_id": self.service_id,
            "api_key_id": self.api_key_id,
            "method": self.method,
            "path": self.path,
            "status_code": self.status_code,
            "latency_ms": self.latency_ms,
            "request_size": self.request_size,
            "response_size": self.response_size,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat(),
            "ip_address": self.ip_address,
        }

    def is_success(self) -> bool:
        return 200 <= self.status_code < 400


class DataServiceManager:
    """数据服务管理器"""

    def __init__(self):
        # 存储配置（生产环境应使用数据库）
        self._services: Dict[str, DataService] = {}
        self._api_keys: Dict[str, APIKey] = {}
        self._call_records: List[APICallRecord] = []

    # ==================== 数据服务管理 ====================

    def create_service(
        self,
        name: str,
        description: str,
        service_type: str,
        source_type: str,
        source_config: Dict,
        endpoint: str,
        method: str = "GET",
        created_by: str = "",
        tags: List[str] = None,
        rate_limit: Dict = None,
    ) -> Dict:
        """创建数据服务"""
        service_id = f"ds_{secrets.token_hex(8)}"

        service = DataService(
            service_id=service_id,
            name=name,
            description=description,
            service_type=service_type,
            source_type=source_type,
            source_config=source_config,
            endpoint=endpoint,
            method=method,
            created_by=created_by,
        )
        service.tags = tags or []
        service.rate_limit = rate_limit

        self._services[service_id] = service

        return service.to_dict()

    def update_service(
        self,
        service_id: str,
        updates: Dict,
    ) -> Optional[Dict]:
        """更新数据服务"""
        service = self._services.get(service_id)
        if not service:
            return None

        if "name" in updates:
            service.name = updates["name"]
        if "description" in updates:
            service.description = updates["description"]
        if "source_config" in updates:
            service.source_config.update(updates["source_config"])
        if "endpoint" in updates:
            service.endpoint = updates["endpoint"]
        if "method" in updates:
            service.method = updates["method"]
        if "status" in updates:
            service.status = updates["status"]
        if "tags" in updates:
            service.tags = updates["tags"]
        if "rate_limit" in updates:
            service.rate_limit = updates["rate_limit"]

        service.updated_at = datetime.now()

        return service.to_dict()

    def delete_service(self, service_id: str) -> bool:
        """删除数据服务"""
        if service_id in self._services:
            del self._services[service_id]
            return True
        return False

    def get_service(self, service_id: str) -> Optional[Dict]:
        """获取数据服务"""
        service = self._services.get(service_id)
        return service.to_dict() if service else None

    def list_services(
        self,
        status: Optional[str] = None,
        service_type: Optional[str] = None,
        source_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_by: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict:
        """列出数据服务"""
        services = list(self._services.values())

        # 过滤
        if status:
            services = [s for s in services if s.status == status]
        if service_type:
            services = [s for s in services if s.service_type == service_type]
        if source_type:
            services = [s for s in services if s.source_type == source_type]
        if tags:
            services = [s for s in services if any(t in s.tags for t in tags)]
        if created_by:
            services = [s for s in services if s.created_by == created_by]

        # 排序
        services.sort(key=lambda s: s.created_at, reverse=True)

        # 分页
        total = len(services)
        services = services[offset:offset + limit]

        return {
            "services": [s.to_dict() for s in services],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def publish_service(self, service_id: str) -> Optional[Dict]:
        """发布数据服务"""
        service = self._services.get(service_id)
        if not service:
            return None

        service.status = "published"
        service.updated_at = datetime.now()

        return service.to_dict()

    def archive_service(self, service_id: str) -> Optional[Dict]:
        """归档数据服务"""
        service = self._services.get(service_id)
        if not service:
            return None

        service.status = "archived"
        service.updated_at = datetime.now()

        return service.to_dict()

    # ==================== API Key 管理 ====================

    def create_api_key(
        self,
        name: str,
        user_id: str,
        scopes: List[str] = None,
        expires_days: int = None,
    ) -> Dict:
        """创建 API Key"""
        key_id = f"ak_{secrets.token_hex(16)}"
        key_secret = secrets.token_urlsafe(32)

        expires_at = None
        if expires_days:
            expires_at = datetime.now() + timedelta(days=expires_days)

        api_key = APIKey(
            key_id=key_id,
            key_secret=key_secret,
            name=name,
            user_id=user_id,
            scopes=scopes or ["read"],
            expires_at=expires_at,
        )

        self._api_keys[key_id] = api_key

        # 返回完整信息（包括 secret，仅此一次）
        return api_key.to_dict(include_secret=True)

    def list_api_keys(
        self,
        user_id: Optional[str] = None,
        include_expired: bool = False,
        include_inactive: bool = False,
    ) -> Dict:
        """列出 API Keys"""
        keys = list(self._api_keys.values())

        if user_id:
            keys = [k for k in keys if k.user_id == user_id]
        if not include_expired:
            keys = [k for k in keys if not k.is_expired()]
        if not include_inactive:
            keys = [k for k in keys if k.is_active]

        keys.sort(key=lambda k: k.created_at, reverse=True)

        return {
            "keys": [k.to_dict() for k in keys],
            "total": len(keys),
        }

    def get_api_key(self, key_id: str) -> Optional[Dict]:
        """获取 API Key（不含 secret）"""
        key = self._api_keys.get(key_id)
        return key.to_dict() if key else None

    def deactivate_api_key(self, key_id: str) -> bool:
        """停用 API Key"""
        key = self._api_keys.get(key_id)
        if key:
            key.is_active = False
            return True
        return False

    def delete_api_key(self, key_id: str) -> bool:
        """删除 API Key"""
        if key_id in self._api_keys:
            del self._api_keys[key_id]
            return True
        return False

    def verify_api_key(self, key_id: str, key_secret: str) -> Optional[Dict]:
        """验证 API Key"""
        key = self._api_keys.get(key_id)
        if not key:
            return None

        if not key.is_active or key.is_expired():
            return None

        if key.key_secret != key_secret:
            return None

        # 更新最后使用时间
        key.last_used = datetime.now()

        return {
            "key_id": key.key_id,
            "user_id": key.user_id,
            "scopes": key.scopes,
        }

    # ==================== API 调用记录 ====================

    def record_api_call(
        self,
        service_id: str,
        api_key_id: str,
        method: str,
        path: str,
        status_code: int,
        latency_ms: int,
        request_size: int = 0,
        response_size: int = 0,
        error_message: str = "",
        ip_address: str = "",
        user_agent: str = "",
    ) -> str:
        """记录 API 调用"""
        call_id = f"call_{secrets.token_hex(12)}"
        record = APICallRecord(
            call_id=call_id,
            service_id=service_id,
            api_key_id=api_key_id,
            method=method,
            path=path,
            status_code=status_code,
            latency_ms=latency_ms,
            request_size=request_size,
            response_size=response_size,
            error_message=error_message,
        )
        record.ip_address = ip_address
        record.user_agent = user_agent

        self._call_records.append(record)

        # 限制记录数量（生产环境应持久化到数据库）
        if len(self._call_records) > 10000:
            self._call_records = self._call_records[-5000:]

        return call_id

    def get_call_records(
        self,
        service_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        status_code: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict:
        """获取 API 调用记录"""
        records = self._call_records

        if service_id:
            records = [r for r in records if r.service_id == service_id]
        if api_key_id:
            records = [r for r in records if r.api_key_id == api_key_id]
        if status_code is not None:
            records = [r for r in records if r.status_code == status_code]
        if start_time:
            records = [r for r in records if r.timestamp >= start_time]
        if end_time:
            records = [r for r in records if r.timestamp <= end_time]

        records.sort(key=lambda r: r.timestamp, reverse=True)

        total = len(records)
        records = records[offset:offset + limit]

        return {
            "records": [r.to_dict() for r in records],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    # ==================== 统计分析 ====================

    def get_service_statistics(
        self,
        service_id: str,
        time_window_hours: int = 24,
    ) -> Dict:
        """获取服务调用统计"""
        since = datetime.now() - timedelta(hours=time_window_hours)

        service_records = [
            r for r in self._call_records
            if r.service_id == service_id and r.timestamp >= since
        ]

        if not service_records:
            return {
                "service_id": service_id,
                "time_window_hours": time_window_hours,
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "success_rate": 0,
                "avg_latency_ms": 0,
                "p50_latency_ms": 0,
                "p95_latency_ms": 0,
                "p99_latency_ms": 0,
                "qps": 0,
                "total_bytes": 0,
            }

        total_calls = len(service_records)
        successful_calls = sum(1 for r in service_records if r.is_success())
        failed_calls = total_calls - successful_calls

        latencies = sorted([r.latency_ms for r in service_records])
        avg_latency = sum(latencies) / len(latencies)

        p50_latency = latencies[int(len(latencies) * 0.5)]
        p95_latency = latencies[int(len(latencies) * 0.95)]
        p99_latency = latencies[int(len(latencies) * 0.99)]

        total_bytes = sum(r.request_size + r.response_size for r in service_records)

        # 计算 QPS (每秒请求数)
        qps = total_calls / (time_window_hours * 3600) if time_window_hours > 0 else 0

        return {
            "service_id": service_id,
            "time_window_hours": time_window_hours,
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "success_rate": successful_calls / total_calls if total_calls > 0 else 0,
            "avg_latency_ms": round(avg_latency, 2),
            "p50_latency_ms": p50_latency,
            "p95_latency_ms": p95_latency,
            "p99_latency_ms": p99_latency,
            "qps": round(qps, 2),
            "total_bytes": total_bytes,
        }

    def get_overall_statistics(
        self,
        time_window_hours: int = 24,
    ) -> Dict:
        """获取整体统计"""
        since = datetime.now() - timedelta(hours=time_window_hours)

        recent_records = [
            r for r in self._call_records
            if r.timestamp >= since
        ]

        total_calls = len(recent_records)
        successful_calls = sum(1 for r in recent_records if r.is_success())

        # 按服务统计
        service_stats = {}
        for record in recent_records:
            if record.service_id not in service_stats:
                service_stats[record.service_id] = {"calls": 0, "errors": 0}
            service_stats[record.service_id]["calls"] += 1
            if not record.is_success():
                service_stats[record.service_id]["errors"] += 1

        # 按状态码统计
        status_codes = {}
        for record in recent_records:
            code = record.status_code
            status_codes[code] = status_codes.get(code, 0) + 1

        # 按 API Key 统计
        key_stats = {}
        for record in recent_records:
            key = record.api_key_id
            if key not in key_stats:
                key_stats[key] = 0
            key_stats[key] += 1

        return {
            "time_window_hours": time_window_hours,
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": total_calls - successful_calls,
            "success_rate": successful_calls / total_calls if total_calls > 0 else 0,
            "active_services": len(service_stats),
            "active_keys": len(key_stats),
            "top_services": sorted(
                [{"service_id": k, **v} for k, v in service_stats.items()],
                key=lambda x: x["calls"],
                reverse=True,
            )[:10],
            "status_codes": status_codes,
        }

    # ==================== 接口测试 ====================

    def test_service(
        self,
        service_id: str,
        params: Dict = None,
    ) -> Dict:
        """测试数据服务"""
        service = self._services.get(service_id)
        if not service:
            return {
                "success": False,
                "message": "服务不存在",
            }

        # 模拟测试执行
        # 生产环境应该实际调用数据源

        return {
            "success": True,
            "message": "测试成功",
            "test_result": {
                "service_id": service_id,
                "service_type": service.service_type,
                "source_type": service.source_type,
                "rows_returned": 10,
                "execution_time_ms": 125,
                "sample_data": [
                    {"id": 1, "name": "示例数据 1"},
                    {"id": 2, "name": "示例数据 2"},
                ],
            },
        }

    # ==================== 签名验证 ====================

    def generate_signature(
        self,
        api_key_id: str,
        method: str,
        path: str,
        body: str = "",
        timestamp: str = None,
    ) -> str:
        """生成请求签名"""
        key = self._api_keys.get(api_key_id)
        if not key:
            return ""

        if timestamp is None:
            timestamp = str(int(datetime.now().timestamp()))

        # 构造签名字符串
        sign_str = f"{method}\n{path}\n{timestamp}\n{body}"

        # 使用 HMAC-SHA256 签名
        signature = hmac.new(
            key.key_secret.encode(),
            sign_str.encode(),
            hashlib.sha256,
        ).hexdigest()

        return signature

    def verify_signature(
        self,
        api_key_id: str,
        method: str,
        path: str,
        signature: str,
        body: str = "",
        timestamp: str = None,
    ) -> bool:
        """验证请求签名"""
        expected_signature = self.generate_signature(
            api_key_id, method, path, body, timestamp
        )
        return hmac.compare_digest(expected_signature or "", signature)

    # ==================== 清理 ====================

    def cleanup_old_records(self, days_to_keep: int = 30) -> int:
        """清理旧的调用记录"""
        cutoff = datetime.now() - timedelta(days=days_to_keep)
        old_count = len(self._call_records)
        self._call_records = [
            r for r in self._call_records
            if r.timestamp > cutoff
        ]
        removed = old_count - len(self._call_records)
        if removed > 0:
            logger.info(f"清理了 {removed} 条旧调用记录")
        return removed


# 创建全局服务实例
_data_service_manager = None


def get_data_service_manager() -> DataServiceManager:
    """获取数据服务管理器实例"""
    global _data_service_manager
    if _data_service_manager is None:
        _data_service_manager = DataServiceManager()
    return _data_service_manager
