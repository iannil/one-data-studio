"""
共享配置模块
Sprint 6: 统一配置管理
Sprint 9: 安全加固 - JWT 密钥轮换

提供所有服务的统一配置接口，支持环境变量和配置文件
"""

import os
import logging
import hashlib
import secrets
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """数据库配置 - Sprint 14: 高可用支持"""
    # 主连接配置 (通过 ProxySQL 代理)
    host: str = field(default_factory=lambda: os.getenv('MYSQL_HOST', 'mysql.one-data-infra.svc.cluster.local'))
    port: int = field(default_factory=lambda: int(os.getenv('MYSQL_PORT', '3306')))
    user: str = field(default_factory=lambda: os.getenv('MYSQL_USER', 'one_data'))
    password: str = field(default_factory=lambda: os.getenv('MYSQL_PASSWORD', 'OneDataPassword123!'))
    database: str = field(default_factory=lambda: os.getenv('MYSQL_DATABASE', 'one_data_bisheng'))

    # 连接池配置
    pool_size: int = field(default_factory=lambda: int(os.getenv('DB_POOL_SIZE', '10')))
    max_overflow: int = field(default_factory=lambda: int(os.getenv('DB_MAX_OVERFLOW', '20')))
    pool_timeout: int = field(default_factory=lambda: int(os.getenv('DB_POOL_TIMEOUT', '30')))
    pool_recycle: int = field(default_factory=lambda: int(os.getenv('DB_POOL_RECYCLE', '3600')))

    # 高可用配置 - Sprint 14
    ha_enabled: bool = field(default_factory=lambda: os.getenv('MYSQL_HA_ENABLED', 'false').lower() == 'true')
    primary_host: str = field(default_factory=lambda: os.getenv('MYSQL_PRIMARY_HOST', 'mysql-primary.one-data-infra.svc.cluster.local'))
    replica_host: str = field(default_factory=lambda: os.getenv('MYSQL_REPLICA_HOST', 'mysql-replica.one-data-infra.svc.cluster.local'))

    # 连接重试配置
    connect_retry_count: int = field(default_factory=lambda: int(os.getenv('DB_CONNECT_RETRY_COUNT', '3')))
    connect_retry_delay: float = field(default_factory=lambda: float(os.getenv('DB_CONNECT_RETRY_DELAY', '1.0')))

    @property
    def url(self) -> str:
        """获取数据库连接 URL (通过 ProxySQL 代理，自动读写分离)"""
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}?charset=utf8mb4"

    @property
    def primary_url(self) -> str:
        """获取主库直连 URL (仅用于特殊场景)"""
        if self.ha_enabled:
            return f"mysql+pymysql://{self.user}:{self.password}@{self.primary_host}:{self.port}/{self.database}?charset=utf8mb4"
        return self.url

    @property
    def replica_url(self) -> str:
        """获取从库直连 URL (仅用于只读查询)"""
        if self.ha_enabled:
            return f"mysql+pymysql://{self.user}:{self.password}@{self.replica_host}:{self.port}/{self.database}?charset=utf8mb4"
        return self.url


@dataclass
class MinIOConfig:
    """MinIO 存储配置"""
    endpoint: str = field(default_factory=lambda: os.getenv('MINIO_ENDPOINT', 'minio.one-data-infra.svc.cluster.local:9000'))
    access_key: str = field(default_factory=lambda: os.getenv('MINIO_ACCESS_KEY', 'minioadmin'))
    secret_key: str = field(default_factory=lambda: os.getenv('MINIO_SECRET_KEY', 'minioadmin'))
    default_bucket: str = field(default_factory=lambda: os.getenv('MINIO_DEFAULT_BUCKET', 'alldata'))
    use_ssl: bool = field(default_factory=lambda: os.getenv('MINIO_USE_SSL', 'false').lower() == 'true')

    def __post_init__(self):
        """配置后处理"""
        # 警告使用默认密码
        if self.access_key == 'minioadmin' and self.secret_key == 'minioadmin':
            logger.warning("Using default MinIO credentials. Please set MINIO_ACCESS_KEY and MINIO_SECRET_KEY in production.")


@dataclass
class MilvusConfig:
    """Milvus 向量数据库配置"""
    host: str = field(default_factory=lambda: os.getenv('MILVUS_HOST', 'localhost'))
    port: str = field(default_factory=lambda: os.getenv('MILVUS_PORT', '19530'))
    embedding_dim: int = field(default_factory=lambda: int(os.getenv('EMBEDDING_DIM', '1536')))
    index_type: str = field(default_factory=lambda: os.getenv('MILVUS_INDEX_TYPE', 'IVF_FLAT'))
    metric_type: str = field(default_factory=lambda: os.getenv('MILVUS_METRIC_TYPE', 'L2'))
    nlist: int = field(default_factory=lambda: int(os.getenv('MILVUS_NLIST', '128')))

    @property
    def address(self) -> str:
        """获取 Milvus 地址"""
        return f"{self.host}:{self.port}"


@dataclass
class OpenAIConfig:
    """OpenAI API 配置"""
    # 支持多密钥配置（逗号分隔或列表）
    _api_keys: List[str] = field(default_factory=list)

    # 单密钥配置（向后兼容）
    api_key: Optional[str] = field(default_factory=lambda: os.getenv('OPENAI_API_KEY'))

    # 密钥轮换索引
    _current_key_index: int = 0

    # 密钥使用统计
    _key_usage_count: Dict[int, int] = field(default_factory=dict)

    base_url: str = field(default_factory=lambda: os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1'))
    model: str = field(default_factory=lambda: os.getenv('OPENAI_MODEL', 'gpt-4o-mini'))
    temperature: float = field(default_factory=lambda: float(os.getenv('OPENAI_TEMPERATURE', '0.7')))
    max_tokens: int = field(default_factory=lambda: int(os.getenv('OPENAI_MAX_TOKENS', '2000')))
    timeout: int = field(default_factory=lambda: int(os.getenv('OPENAI_TIMEOUT', '30')))

    # 密钥轮换策略
    rotation_strategy: str = field(default_factory=lambda: os.getenv('OPENAI_KEY_ROTATION_STRATEGY', 'round_robin'))
    # 轮换策略: 'round_robin' - 轮询, 'least_used' - 最少使用, 'random' - 随机

    def __post_init__(self):
        """初始化后处理"""
        # 尝试从环境变量加载多密钥
        env_keys = os.getenv('OPENAI_API_KEYS')
        if env_keys:
            self._api_keys = [k.strip() for k in env_keys.split(',') if k.strip()]
        elif self.api_key:
            self._api_keys = [self.api_key]

        # 验证密钥配置
        if not self._api_keys:
            logger.warning("No OpenAI API keys configured")

    @property
    def api_keys(self) -> List[str]:
        """获取所有可用密钥"""
        return self._api_keys.copy()

    @property
    def configured(self) -> bool:
        """检查是否已配置"""
        return len(self._api_keys) > 0

    @property
    def current_key_index(self) -> int:
        """获取当前密钥索引"""
        return self._current_key_index

    @property
    def current_key(self) -> Optional[str]:
        """获取当前使用的密钥"""
        if self._api_keys and 0 <= self._current_key_index < len(self._api_keys):
            return self._api_keys[self._current_key_index]
        return None

    def get_api_key(self) -> Optional[str]:
        """
        获取 API 密钥（根据轮换策略）

        Returns:
            当前可用的 API 密钥
        """
        if not self._api_keys:
            return None

        if len(self._api_keys) == 1:
            return self._api_keys[0]

        # 根据策略选择密钥
        if self.rotation_strategy == 'round_robin':
            key = self._api_keys[self._current_key_index]
            self._current_key_index = (self._current_key_index + 1) % len(self._api_keys)
        elif self.rotation_strategy == 'least_used':
            # 选择使用次数最少的密钥
            min_usage = min(self._key_usage_count.values()) if self._key_usage_count else 0
            candidates = [i for i, count in self._key_usage_count.items() if count == min_usage]
            import random
            idx = random.choice(candidates) if candidates else 0
            key = self._api_keys[idx]
            self._current_key_index = idx
        elif self.rotation_strategy == 'random':
            import random
            idx = random.randint(0, len(self._api_keys) - 1)
            key = self._api_keys[idx]
            self._current_key_index = idx
        else:
            # 默认使用第一个
            key = self._api_keys[0]

        # 更新使用统计
        self._key_usage_count[self._current_key_index] = self._key_usage_count.get(self._current_key_index, 0) + 1

        return key

    def get_next_key(self) -> Optional[str]:
        """
        切换到下一个密钥

        Returns:
            下一个可用的 API 密钥
        """
        if not self._api_keys:
            return None

        self._current_key_index = (self._current_key_index + 1) % len(self._api_keys)
        return self._api_keys[self._current_key_index]

    def set_key_index(self, index: int) -> bool:
        """
        设置当前密钥索引

        Args:
            index: 密钥索引

        Returns:
            是否成功设置
        """
        if 0 <= index < len(self._api_keys):
            self._current_key_index = index
            return True
        return False

    def add_key(self, key: str) -> bool:
        """
        添加新的 API 密钥

        Args:
            key: API 密钥

        Returns:
            是否成功添加
        """
        if key and key not in self._api_keys:
            self._api_keys.append(key)
            logger.info(f"Added new API key (total: {len(self._api_keys)})")
            return True
        return False

    def remove_key(self, key: str) -> bool:
        """
        移除 API 密钥

        Args:
            key: 要移除的 API 密钥

        Returns:
            是否成功移除
        """
        if key in self._api_keys:
            if len(self._api_keys) <= 1:
                logger.warning("Cannot remove the last API key")
                return False

            idx = self._api_keys.index(key)
            self._api_keys.remove(key)
            # 清理使用统计
            self._key_usage_count.pop(idx, None)
            # 调整当前索引
            if self._current_key_index >= len(self._api_keys):
                self._current_key_index = 0
            logger.info(f"Removed API key (remaining: {len(self._api_keys)})")
            return True
        return False

    def get_key_stats(self) -> Dict[str, int]:
        """
        获取密钥使用统计

        Returns:
            密钥使用次数统计
        """
        return {
            f"key_{i}": self._key_usage_count.get(i, 0)
            for i in range(len(self._api_keys))
        }

    def reset_usage_stats(self):
        """重置使用统计"""
        self._key_usage_count.clear()


@dataclass
class KeycloakConfig:
    """Keycloak 认证配置"""
    url: str = field(default_factory=lambda: os.getenv('KEYCLOAK_URL', 'http://keycloak.one-data-system.svc.cluster.local:80'))
    realm: str = field(default_factory=lambda: os.getenv('KEYCLOAK_REALM', 'one-data'))
    client_id: str = field(default_factory=lambda: os.getenv('KEYCLOAK_CLIENT_ID', 'one-data-studio'))
    client_secret: Optional[str] = field(default_factory=lambda: os.getenv('KEYCLOAK_CLIENT_SECRET'))

    @property
    def issuer(self) -> str:
        """获取 Issuer URL"""
        return f"{self.url}/realms/{self.realm}"


@dataclass
class JWTConfig:
    """JWT 认证配置 - Sprint 9: 密钥轮换支持

    支持多密钥管理，实现密钥的平滑轮换：
    1. 新密钥用于签发 token
    2. 旧密钥在过渡期内仍可验证
    3. 过渡期后旧密钥自动失效
    """
    # 当前有效密钥（用于签发）
    secret_key: str = field(default_factory=lambda: os.getenv('JWT_SECRET_KEY', 'dev-secret-key-change-in-production'))

    # 算法
    algorithm: str = field(default_factory=lambda: os.getenv('JWT_ALGORITHM', 'HS256'))

    # Access Token 过期时间（秒）
    access_token_expire: int = field(default_factory=lambda: int(os.getenv('JWT_ACCESS_TOKEN_EXPIRE', '3600')))

    # Refresh Token 过期时间（秒）
    refresh_token_expire: int = field(default_factory=lambda: int(os.getenv('JWT_REFRESH_TOKEN_EXPIRE', '604800')))

    # 密钥轮换相关
    _previous_keys: List[Tuple[str, float]] = field(default_factory=list)  # (密钥, 过期时间戳)
    _key_rotation_period: int = field(default_factory=lambda: int(os.getenv('JWT_KEY_ROTATION_PERIOD', '86400')))  # 默认 24 小时
    _key_grace_period: int = field(default_factory=lambda: int(os.getenv('JWT_KEY_GRACE_PERIOD', '7200')))  # 旧密钥仍有效的时间（默认 2 小时）

    # 密钥 ID（用于标识当前密钥）
    _key_id: str = field(default_factory=str)

    def __post_init__(self):
        """初始化后处理"""
        # 生成密钥 ID
        self._key_id = self._generate_key_id(self.secret_key)

        # 检查是否使用默认密钥
        if self.secret_key == 'dev-secret-key-change-in-production':
            logger.warning("Using default JWT secret key. Please set JWT_SECRET_KEY in production.")

        # 加载轮换密钥历史
        self._load_previous_keys()

    def _generate_key_id(self, key: str) -> str:
        """生成密钥 ID（密钥的短哈希）"""
        return hashlib.sha256(key.encode()).hexdigest()[:8]

    def _load_previous_keys(self):
        """从环境变量加载历史密钥"""
        # 格式: JWT_PREVIOUS_KEYS="key1:timestamp1,key2:timestamp2"
        prev_keys_env = os.getenv('JWT_PREVIOUS_KEYS', '')
        if prev_keys_env:
            for item in prev_keys_env.split(','):
                if ':' in item:
                    key, ts = item.rsplit(':', 1)
                    try:
                        self._previous_keys.append((key.strip(), float(ts)))
                    except ValueError:
                        logger.warning(f"Invalid previous key timestamp: {ts}")

    @property
    def key_id(self) -> str:
        """获取当前密钥 ID"""
        return self._key_id

    @property
    def all_valid_keys(self) -> List[str]:
        """获取所有当前有效的密钥（用于验证）"""
        current_time = time.time()
        valid_keys = [self.secret_key]

        # 添加未过期的历史密钥
        for key, expire_time in self._previous_keys:
            if expire_time > current_time:
                valid_keys.append(key)

        return valid_keys

    def rotate_key(self, new_key: Optional[str] = None) -> str:
        """轮换密钥

        Args:
            new_key: 新密钥（不提供则自动生成）

        Returns:
            新密钥
        """
        # 将当前密钥添加到历史（带过期时间）
        grace_expire = time.time() + self._key_grace_period
        self._previous_keys.append((self.secret_key, grace_expire))

        # 清理已过期的历史密钥
        current_time = time.time()
        self._previous_keys = [(k, t) for k, t in self._previous_keys if t > current_time]

        # 设置新密钥
        self.secret_key = new_key or secrets.token_urlsafe(32)
        self._key_id = self._generate_key_id(self.secret_key)

        logger.info(f"JWT key rotated. New key ID: {self._key_id}, "
                   f"Previous keys still valid: {len(self._previous_keys)}")

        return self.secret_key

    def verify_with_any_key(self, token: str) -> Tuple[Optional[dict], str]:
        """尝试使用所有有效密钥验证 token

        Args:
            token: JWT token

        Returns:
            (payload, used_key_id) 或 (None, '') 如果验证失败
        """
        try:
            import jwt
        except ImportError:
            logger.error("PyJWT not installed")
            return None, ''

        for key in self.all_valid_keys:
            try:
                payload = jwt.decode(token, key, algorithms=[self.algorithm])
                key_id = self._generate_key_id(key)
                return payload, key_id
            except jwt.InvalidTokenError:
                continue

        return None, ''

    def should_rotate(self) -> bool:
        """检查是否应该轮换密钥"""
        # 这里可以添加更复杂的逻辑，比如基于时间或使用次数
        # 简单实现：检查环境变量标志
        return os.getenv('JWT_FORCE_ROTATION', 'false').lower() == 'true'

    def get_token_claims(self, user_id: str, roles: List[str] = None,
                         extra_claims: Dict[str, Any] = None) -> Dict[str, Any]:
        """生成 token claims

        Args:
            user_id: 用户 ID
            roles: 用户角色列表
            extra_claims: 额外的 claims

        Returns:
            Token claims 字典
        """
        import time

        now = time.time()
        claims = {
            'sub': user_id,
            'iat': int(now),
            'exp': int(now + self.access_token_expire),
            'kid': self._key_id,  # 密钥 ID
        }

        if roles:
            claims['roles'] = roles

        if extra_claims:
            claims.update(extra_claims)

        return claims


@dataclass
class ServiceConfig:
    """服务间调用配置"""
    alldata_api_url: str = field(default_factory=lambda: os.getenv('ALDATA_API_URL', 'http://alldata-api:8080'))
    bisheng_api_url: str = field(default_factory=lambda: os.getenv('BISHENG_API_URL', 'http://bisheng-api:8081'))
    cube_api_url: str = field(default_factory=lambda: os.getenv('CUBE_API_URL', 'http://vllm-serving:8000'))
    openai_proxy_url: str = field(default_factory=lambda: os.getenv('OPENAI_PROXY_URL', 'http://openai-proxy:8000'))


@dataclass
class RedisConfig:
    """Redis 缓存配置 - Sprint 8 + Sprint 14: Sentinel 高可用"""
    host: str = field(default_factory=lambda: os.getenv('REDIS_HOST', 'localhost'))
    port: int = field(default_factory=lambda: int(os.getenv('REDIS_PORT', '6379')))
    db: int = field(default_factory=lambda: int(os.getenv('REDIS_DB', '0')))
    password: Optional[str] = field(default_factory=lambda: os.getenv('REDIS_PASSWORD'))
    max_connections: int = field(default_factory=lambda: int(os.getenv('REDIS_MAX_CONNECTIONS', '50')))
    socket_timeout: int = field(default_factory=lambda: int(os.getenv('REDIS_SOCKET_TIMEOUT', '5')))
    socket_connect_timeout: int = field(default_factory=lambda: int(os.getenv('REDIS_SOCKET_CONNECT_TIMEOUT', '5')))

    # 缓存 TTL 配置（秒）
    metadata_ttl: int = field(default_factory=lambda: int(os.getenv('CACHE_METADATA_TTL', '300')))
    model_list_ttl: int = field(default_factory=lambda: int(os.getenv('CACHE_MODEL_LIST_TTL', '600')))
    workflow_ttl: int = field(default_factory=lambda: int(os.getenv('CACHE_WORKFLOW_TTL', '180')))
    search_result_ttl: int = field(default_factory=lambda: int(os.getenv('CACHE_SEARCH_RESULT_TTL', '60')))

    # Sentinel 高可用配置 - Sprint 14
    sentinel_enabled: bool = field(default_factory=lambda: os.getenv('REDIS_SENTINEL_ENABLED', 'false').lower() == 'true')
    sentinel_master: str = field(default_factory=lambda: os.getenv('REDIS_SENTINEL_MASTER', 'mymaster'))
    sentinel_hosts: str = field(default_factory=lambda: os.getenv('REDIS_SENTINEL_HOSTS', 'redis-sentinel:26379'))
    sentinel_password: Optional[str] = field(default_factory=lambda: os.getenv('REDIS_SENTINEL_PASSWORD'))

    # 连接重试配置
    retry_on_timeout: bool = field(default_factory=lambda: os.getenv('REDIS_RETRY_ON_TIMEOUT', 'true').lower() == 'true')
    retry_count: int = field(default_factory=lambda: int(os.getenv('REDIS_RETRY_COUNT', '3')))

    @property
    def url(self) -> str:
        """获取 Redis URL"""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"

    @property
    def enabled(self) -> bool:
        """检查 Redis 是否启用"""
        return os.getenv('REDIS_ENABLED', 'true').lower() == 'true'

    @property
    def sentinel_addresses(self) -> List[Tuple[str, int]]:
        """解析 Sentinel 地址列表"""
        addresses = []
        for addr in self.sentinel_hosts.split(','):
            addr = addr.strip()
            if ':' in addr:
                host, port = addr.rsplit(':', 1)
                addresses.append((host, int(port)))
            else:
                addresses.append((addr, 26379))
        return addresses


@dataclass
class CeleryConfig:
    """Celery 异步任务队列配置 - Sprint 8"""
    broker_url: str = field(default_factory=lambda: os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1'))
    result_backend: str = field(default_factory=lambda: os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2'))
    task_track_started: bool = True
    task_time_limit: int = field(default_factory=lambda: int(os.getenv('CELERY_TASK_TIME_LIMIT', '3600')))
    task_soft_time_limit: int = field(default_factory=lambda: int(os.getenv('CELERY_TASK_SOFT_TIME_LIMIT', '3000')))
    worker_max_tasks_per_child: int = field(default_factory=lambda: int(os.getenv('CELERY_WORKER_MAX_TASKS', '100')))
    result_expires: int = field(default_factory=lambda: int(os.getenv('CELERY_RESULT_EXPIRES', '86400')))


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = field(default_factory=lambda: os.getenv('LOG_LEVEL', 'INFO'))
    format: str = field(default_factory=lambda: os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    file: Optional[str] = field(default_factory=lambda: os.getenv('LOG_FILE'))

    def setup(self):
        """设置日志配置"""
        logging.basicConfig(
            level=getattr(logging, self.level),
            format=self.format
        )
        if self.file:
            logger.info(f"Logging to file: {self.file}")


class Config:
    """统一配置管理器"""

    def __init__(self, env_file: Optional[str] = None):
        """
        初始化配置

        Args:
            env_file: .env 文件路径（可选）
        """
        if env_file:
            self._load_env_file(env_file)

        self.database = DatabaseConfig()
        self.minio = MinIOConfig()
        self.milvus = MilvusConfig()
        self.openai = OpenAIConfig()
        self.keycloak = KeycloakConfig()
        self.jwt = JWTConfig()  # Sprint 9: JWT 密钥轮换支持
        self.service = ServiceConfig()
        self.redis = RedisConfig()
        self.celery = CeleryConfig()
        self.logging = LoggingConfig()

        # 设置日志
        self.logging.setup()

        # 检查生产环境配置
        self._validate_production_config()

    def _load_env_file(self, env_file: str):
        """加载 .env 文件"""
        env_path = Path(env_file)
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
            logger.info(f"Loaded environment from: {env_file}")
        else:
            logger.warning(f"Environment file not found: {env_file}")

    def _validate_production_config(self):
        """验证生产环境配置"""
        if os.getenv('ENVIRONMENT') == 'production':
            warnings = []

            # 检查默认密码
            if self.minio.access_key == 'minioadmin':
                warnings.append("MinIO using default credentials")
            if self.database.password in ('OneDataPassword123!', 'password', '123456'):
                warnings.append("Database using default password")

            # 检查必需的 API keys
            if not self.openai.api_key:
                warnings.append("OpenAI API key not configured")

            if warnings:
                logger.warning("Production configuration warnings: " + "; ".join(warnings))

    def to_dict(self) -> Dict[str, Any]:
        """导出为字典（用于调试，隐藏敏感信息）"""
        return {
            'database': {
                'host': self.database.host,
                'port': self.database.port,
                'user': self.database.user,
                'database': self.database.database,
                'password': '***HIDDEN***' if self.database.password else None
            },
            'minio': {
                'endpoint': self.minio.endpoint,
                'access_key': self.minio.access_key,
                'secret_key': '***HIDDEN***' if self.minio.secret_key else None,
                'default_bucket': self.minio.default_bucket
            },
            'milvus': {
                'host': self.milvus.host,
                'port': self.milvus.port,
                'embedding_dim': self.milvus.embedding_dim
            },
            'openai': {
                'api_key': '***HIDDEN***' if self.openai.api_key else None,
                'base_url': self.openai.base_url,
                'model': self.openai.model,
                'configured': self.openai.configured
            },
            'keycloak': {
                'url': self.keycloak.url,
                'realm': self.keycloak.realm,
                'client_id': self.keycloak.client_id
            },
            'service': {
                'alldata_api_url': self.service.alldata_api_url,
                'bisheng_api_url': self.service.bisheng_api_url,
                'cube_api_url': self.service.cube_api_url
            }
        }

    def get_service_url(self, service_name: str) -> Optional[str]:
        """
        获取服务 URL

        Args:
            service_name: 服务名称 (alldata, bisheng, cube, openai_proxy)

        Returns:
            服务 URL
        """
        return getattr(self.service, f'{service_name}_api_url', None)


# 全局配置实例
_config: Optional[Config] = None


def get_config(env_file: Optional[str] = None) -> Config:
    """
    获取全局配置实例（单例模式）

    Args:
        env_file: .env 文件路径（仅在首次调用时生效）

    Returns:
        Config 实例
    """
    global _config
    if _config is None:
        _config = Config(env_file)
    return _config


def reload_config(env_file: Optional[str] = None) -> Config:
    """
    重新加载配置

    Args:
        env_file: .env 文件路径

    Returns:
        新的 Config 实例
    """
    global _config
    _config = Config(env_file)
    return _config
