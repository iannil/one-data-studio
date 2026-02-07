"""
Redis存储管理器

提供：
1. Redis连接管理
2. 缓存数据操作
3. 队列操作
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta

try:
    import redis
except ImportError:
    redis = None

from ..config import RedisConfig


logger = logging.getLogger(__name__)


class RedisManager:
    """
    Redis存储管理器

    提供：
    - 键值存储
    - 哈希表操作
    - 列表操作
    - 集合操作
    """

    def __init__(self, config: RedisConfig = None):
        """
        初始化Redis管理器

        Args:
            config: Redis配置
        """
        self.config = config or RedisConfig.from_env()
        self._client = None
        self._connected = False

    @property
    def is_available(self) -> bool:
        """检查redis是否可用"""
        return redis is not None

    def connect(self) -> bool:
        """
        建立Redis连接

        Returns:
            连接是否成功
        """
        if not self.is_available:
            logger.warning("redis library not available, using mock mode")
            self._connected = True
            return True

        if self._connected and self._client:
            return True

        try:
            self._client = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                password=self.config.password if self.config.password else None,
                db=self.config.db,
                decode_responses=self.config.decode_responses,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # 测试连接
            self._client.ping()
            self._connected = True
            logger.info(f"Connected to Redis at {self.config.host}:{self.config.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = True  # 设置为True以避免重复尝试
            return False

    def disconnect(self):
        """断开Redis连接"""
        if self._client:
            self._client.close()
        self._client = None
        self._connected = False
        logger.info("Disconnected from Redis")

    # ==================== 基本操作 ====================

    def set(self, key: str, value: Any, expiration: int = None) -> bool:
        """
        设置键值

        Args:
            key: 键
            value: 值（自动转换为JSON）
            expiration: 过期时间（秒）

        Returns:
            是否成功
        """
        if not self._connected:
            self.connect()

        try:
            if not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)

            if self._client:
                if expiration:
                    return self._client.setex(key, expiration, value)
                return self._client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Failed to set key {key}: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取键值

        Args:
            key: 键
            default: 默认值

        Returns:
            值（自动解析JSON）
        """
        if not self._connected:
            self.connect()

        try:
            if self._client:
                value = self._client.get(key)
                if value is None:
                    return default
                # 尝试解析JSON
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            return default
        except Exception as e:
            logger.error(f"Failed to get key {key}: {e}")
            return default

    def delete(self, *keys: str) -> int:
        """
        删除键

        Args:
            *keys: 键列表

        Returns:
            删除的数量
        """
        if not self._connected:
            self.connect()

        try:
            if self._client and keys:
                return self._client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Failed to delete keys: {e}")
            return 0

    def exists(self, *keys: str) -> int:
        """
        检查键是否存在

        Args:
            *keys: 键列表

        Returns:
            存在的键数量
        """
        if not self._connected:
            self.connect()

        try:
            if self._client and keys:
                return self._client.exists(*keys)
            return 0
        except Exception as e:
            logger.error(f"Failed to check keys existence: {e}")
            return 0

    def expire(self, key: str, seconds: int) -> bool:
        """
        设置过期时间

        Args:
            key: 键
            seconds: 过期秒数

        Returns:
            是否成功
        """
        if not self._connected:
            self.connect()

        try:
            if self._client:
                return self._client.expire(key, seconds)
            return False
        except Exception as e:
            logger.error(f"Failed to set expiration: {e}")
            return False

    # ==================== 哈希操作 ====================

    def hset(self, name: str, key: str, value: Any) -> bool:
        """
        设置哈希字段

        Args:
            name: 哈希表名
            key: 字段名
            value: 值

        Returns:
            是否成功
        """
        if not self._connected:
            self.connect()

        try:
            if not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)
            if self._client:
                return self._client.hset(name, key, value)
            return True
        except Exception as e:
            logger.error(f"Failed to hset {name}.{key}: {e}")
            return False

    def hget(self, name: str, key: str, default: Any = None) -> Any:
        """
        获取哈希字段

        Args:
            name: 哈希表名
            key: 字段名
            default: 默认值

        Returns:
            值
        """
        if not self._connected:
            self.connect()

        try:
            if self._client:
                value = self._client.hget(name, key)
                if value is None:
                    return default
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            return default
        except Exception as e:
            logger.error(f"Failed to hget {name}.{key}: {e}")
            return default

    def hgetall(self, name: str) -> Dict[str, Any]:
        """
        获取整个哈希表

        Args:
            name: 哈希表名

        Returns:
            哈希表字典
        """
        if not self._connected:
            self.connect()

        try:
            if self._client:
                data = self._client.hgetall(name)
                # 尝试解析JSON值
                result = {}
                for k, v in data.items():
                    try:
                        result[k] = json.loads(v)
                    except (json.JSONDecodeError, TypeError):
                        result[k] = v
                return result
            return {}
        except Exception as e:
            logger.error(f"Failed to hgetall {name}: {e}")
            return {}

    def hdel(self, name: str, *keys: str) -> int:
        """
        删除哈希字段

        Args:
            name: 哈希表名
            *keys: 字段名列表

        Returns:
            删除的数量
        """
        if not self._connected:
            self.connect()

        try:
            if self._client and keys:
                return self._client.hdel(name, *keys)
            return 0
        except Exception as e:
            logger.error(f"Failed to hdel: {e}")
            return 0

    # ==================== 列表操作 ====================

    def lpush(self, name: str, *values: Any) -> int:
        """
        列表左侧添加

        Args:
            name: 列表名
            *values: 值列表

        Returns:
            列表长度
        """
        if not self._connected:
            self.connect()

        try:
            if self._client:
                serialized_values = []
                for v in values:
                    if not isinstance(v, str):
                        v = json.dumps(v, ensure_ascii=False)
                    serialized_values.append(v)
                return self._client.lpush(name, *serialized_values)
            return 0
        except Exception as e:
            logger.error(f"Failed to lpush: {e}")
            return 0

    def rpush(self, name: str, *values: Any) -> int:
        """
        列表右侧添加

        Args:
            name: 列表名
            *values: 值列表

        Returns:
            列表长度
        """
        if not self._connected:
            self.connect()

        try:
            if self._client:
                serialized_values = []
                for v in values:
                    if not isinstance(v, str):
                        v = json.dumps(v, ensure_ascii=False)
                    serialized_values.append(v)
                return self._client.rpush(name, *serialized_values)
            return 0
        except Exception as e:
            logger.error(f"Failed to rpush: {e}")
            return 0

    def lrange(self, name: str, start: int = 0, end: int = -1) -> List[Any]:
        """
        获取列表范围

        Args:
            name: 列表名
            start: 起始位置
            end: 结束位置

        Returns:
            值列表
        """
        if not self._connected:
            self.connect()

        try:
            if self._client:
                values = self._client.lrange(name, start, end)
                result = []
                for v in values:
                    try:
                        result.append(json.loads(v))
                    except (json.JSONDecodeError, TypeError):
                        result.append(v)
                return result
            return []
        except Exception as e:
            logger.error(f"Failed to lrange: {e}")
            return []

    def lpop(self, name: str) -> Optional[Any]:
        """
        列表左侧弹出

        Args:
            name: 列表名

        Returns:
            弹出的值
        """
        if not self._connected:
            self.connect()

        try:
            if self._client:
                value = self._client.lpop(name)
                if value:
                    try:
                        return json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        return value
            return None
        except Exception as e:
            logger.error(f"Failed to lpop: {e}")
            return None

    # ==================== 集合操作 ====================

    def sadd(self, name: str, *values: Any) -> int:
        """
        集合添加成员

        Args:
            name: 集合名
            *values: 成员列表

        Returns:
            添加的成员数量
        """
        if not self._connected:
            self.connect()

        try:
            if self._client:
                serialized_values = []
                for v in values:
                    if not isinstance(v, str):
                        v = json.dumps(v, ensure_ascii=False)
                    serialized_values.append(v)
                return self._client.sadd(name, *serialized_values)
            return 0
        except Exception as e:
            logger.error(f"Failed to sadd: {e}")
            return 0

    def smembers(self, name: str) -> set:
        """
        获取集合所有成员

        Args:
            name: 集合名

        Returns:
            成员集合
        """
        if not self._connected:
            self.connect()

        try:
            if self._client:
                return self._client.smembers(name)
            return set()
        except Exception as e:
            logger.error(f"Failed to smembers: {e}")
            return set()

    def srem(self, name: str, *values: Any) -> int:
        """
        集合删除成员

        Args:
            name: 集合名
            *values: 成员列表

        Returns:
            删除的成员数量
        """
        if not self._connected:
            self.connect()

        try:
            if self._client and values:
                serialized_values = []
                for v in values:
                    if not isinstance(v, str):
                        v = json.dumps(v, ensure_ascii=False)
                    serialized_values.append(v)
                return self._client.srem(name, *serialized_values)
            return 0
        except Exception as e:
            logger.error(f"Failed to srem: {e}")
            return 0

    # ==================== 便捷方法 ====================

    def cache_get(self, key: str, default: Any = None) -> Any:
        """获取缓存值"""
        return self.get(f"cache:{key}", default)

    def cache_set(self, key: str, value: Any, expiration: int = 3600) -> bool:
        """设置缓存值（默认1小时过期）"""
        return self.set(f"cache:{key}", value, expiration)

    def cache_delete(self, *keys: str) -> int:
        """删除缓存值"""
        cache_keys = [f"cache:{k}" for k in keys]
        return self.delete(*cache_keys)

    def queue_push(self, name: str, value: Any) -> int:
        """推入队列"""
        return self.rpush(f"queue:{name}", value)

    def queue_pop(self, name: str) -> Optional[Any]:
        """从队列弹出"""
        return self.lpop(f"queue:{name}")

    def queue_size(self, name: str) -> int:
        """获取队列大小"""
        if not self._connected:
            self.connect()

        try:
            if self._client:
                return self._client.llen(f"queue:{name}")
            return 0
        except Exception as e:
            logger.error(f"Failed to get queue size: {e}")
            return 0

    def cleanup_test_keys(self, prefix: str = "test:") -> int:
        """
        清理测试数据

        Args:
            prefix: 键前缀

        Returns:
            删除的键数量
        """
        if not self._connected:
            self.connect()

        try:
            if self._client:
                # 查找所有匹配的键
                keys = []
                cursor = 0
                while True:
                    cursor, batch = self._client.scan(cursor, match=f"{prefix}*", count=100)
                    keys.extend(batch)
                    if cursor == 0:
                        break

                if keys:
                    return self._client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Failed to cleanup test keys: {e}")
            return 0

    def get_db_size(self) -> int:
        """
        获取当前数据库的键数量

        Returns:
            键数量
        """
        if not self._connected:
            self.connect()

        try:
            if self._client:
                return self._client.dbsize()
            return 0
        except Exception as e:
            logger.error(f"Failed to get db size: {e}")
            return 0


class MockRedisManager:
    """
    Redis管理器的Mock实现（用于测试）
    """

    def __init__(self, config: RedisConfig = None):
        self.config = config or RedisConfig()
        self._data: Dict[str, Any] = {}
        self._hashes: Dict[str, Dict[str, Any]] = {}
        self._lists: Dict[str, List[Any]] = {}
        self._sets: Dict[str, set] = {}
        self._connected = False

    def connect(self) -> bool:
        """模拟连接"""
        self._connected = True
        return True

    def disconnect(self):
        """模拟断开"""
        self._connected = False

    def set(self, key: str, value: Any, expiration: int = None) -> bool:
        """模拟设置键值"""
        self._data[key] = value
        return True

    def get(self, key: str, default: Any = None) -> Any:
        """模拟获取键值"""
        return self._data.get(key, default)

    def delete(self, *keys: str) -> int:
        """模拟删除键"""
        count = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                count += 1
        return count

    def exists(self, *keys: str) -> int:
        """模拟检查键存在"""
        return sum(1 for key in keys if key in self._data)

    def expire(self, key: str, seconds: int) -> bool:
        """模拟设置过期（实际不实现）"""
        return True

    def hset(self, name: str, key: str, value: Any) -> bool:
        """模拟哈希设置"""
        if name not in self._hashes:
            self._hashes[name] = {}
        self._hashes[name][key] = value
        return True

    def hget(self, name: str, key: str, default: Any = None) -> Any:
        """模拟哈希获取"""
        if name in self._hashes:
            return self._hashes[name].get(key, default)
        return default

    def hgetall(self, name: str) -> Dict[str, Any]:
        """模拟获取整个哈希"""
        return self._hashes.get(name, {})

    def hdel(self, name: str, *keys: str) -> int:
        """模拟哈希删除"""
        if name not in self._hashes:
            return 0
        count = 0
        for key in keys:
            if key in self._hashes[name]:
                del self._hashes[name][key]
                count += 1
        return count

    def lpush(self, name: str, *values: Any) -> int:
        """模拟列表左推"""
        if name not in self._lists:
            self._lists[name] = []
        for v in reversed(values):
            self._lists[name].insert(0, v)
        return len(self._lists[name])

    def rpush(self, name: str, *values: Any) -> int:
        """模拟列表右推"""
        if name not in self._lists:
            self._lists[name] = []
        self._lists[name].extend(values)
        return len(self._lists[name])

    def lrange(self, name: str, start: int = 0, end: int = -1) -> List[Any]:
        """模拟列表范围"""
        lst = self._lists.get(name, [])
        if end == -1:
            return lst[start:]
        return lst[start:end + 1]

    def lpop(self, name: str) -> Optional[Any]:
        """模拟列表左弹"""
        if name in self._lists and self._lists[name]:
            return self._lists[name].pop(0)
        return None

    def sadd(self, name: str, *values: Any) -> int:
        """模拟集合添加"""
        if name not in self._sets:
            self._sets[name] = set()
        before = len(self._sets[name])
        self._sets[name].update(values)
        return len(self._sets[name]) - before

    def smembers(self, name: str) -> set:
        """模拟集合成员"""
        return self._sets.get(name, set())

    def srem(self, name: str, *values: Any) -> int:
        """模拟集合删除"""
        if name not in self._sets:
            return 0
        count = 0
        for v in values:
            if v in self._sets[name]:
                self._sets[name].discard(v)
                count += 1
        return count

    def cache_get(self, key: str, default: Any = None) -> Any:
        """模拟缓存获取"""
        return self.get(f"cache:{key}", default)

    def cache_set(self, key: str, value: Any, expiration: int = 3600) -> bool:
        """模拟缓存设置"""
        return self.set(f"cache:{key}", value)

    def cache_delete(self, *keys: str) -> int:
        """模拟缓存删除"""
        cache_keys = [f"cache:{k}" for k in keys]
        return self.delete(*cache_keys)

    def queue_push(self, name: str, value: Any) -> int:
        """模拟队列推入"""
        return self.rpush(f"queue:{name}", value)

    def queue_pop(self, name: str) -> Optional[Any]:
        """模拟队列弹出"""
        return self.lpop(f"queue:{name}")

    def queue_size(self, name: str) -> int:
        """模拟队列大小"""
        return len(self._lists.get(f"queue:{name}", []))

    def cleanup_test_keys(self, prefix: str = "test:") -> int:
        """模拟清理测试键"""
        count = 0
        to_delete = [k for k in self._data.keys() if k.startswith(prefix)]
        for key in to_delete:
            del self._data[key]
            count += 1
        return count

    def get_db_size(self) -> int:
        """模拟获取数据库大小"""
        return len(self._data) + sum(len(h) for h in self._hashes.values())

    def get_all_data(self) -> Dict[str, Any]:
        """获取所有数据（用于测试验证）"""
        return {
            "data": self._data.copy(),
            "hashes": {k: v.copy() for k, v in self._hashes.items()},
            "lists": {k: v.copy() for k, v in self._lists.items()},
            "sets": {k: v.copy() for k, v in self._sets.items()},
        }


def get_redis_manager(config: RedisConfig = None, mock: bool = False) -> RedisManager:
    """
    获取Redis管理器实例

    Args:
        config: Redis配置
        mock: 是否使用Mock实现

    Returns:
        Redis管理器实例
    """
    if mock or redis is None:
        return MockRedisManager(config)
    return RedisManager(config)
