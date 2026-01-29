"""
统一 AI 服务模块

提供与 vLLM 服务交互的统一接口，支持：
- 元数据 AI 标注（列描述、业务术语）
- 敏感数据深度分析
- ETL 清洗规则推荐
- Text-to-SQL 生成
"""

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class AIServiceConfig:
    """AI 服务配置"""

    # vLLM Chat 服务
    vllm_chat_url: str = "http://vllm-chat:8000"
    vllm_chat_model: str = "Qwen/Qwen2.5-1.5B-Instruct"

    # 可选：通过 openai-proxy 调用（支持降级到OpenAI）
    use_proxy: bool = False
    proxy_url: str = "http://openai-proxy:8000"

    # 功能开关
    enabled: bool = True

    # 请求配置
    timeout: int = 60
    max_tokens: int = 2048
    temperature: float = 0.3

    # 重试配置
    max_retries: int = 2
    retry_delay: float = 1.0

    # 健康检查缓存
    health_cache_ttl: int = 30  # 秒

    @classmethod
    def from_env(cls) -> "AIServiceConfig":
        """从环境变量加载配置"""
        return cls(
            vllm_chat_url=os.getenv("VLLM_CHAT_URL", "http://vllm-chat:8000"),
            vllm_chat_model=os.getenv("VLLM_CHAT_MODEL", "Qwen/Qwen2.5-1.5B-Instruct"),
            use_proxy=os.getenv("AI_USE_PROXY", "false").lower() == "true",
            proxy_url=os.getenv("OPENAI_PROXY_URL", "http://openai-proxy:8000"),
            enabled=os.getenv("AI_FEATURES_ENABLED", "true").lower() == "true",
            timeout=int(os.getenv("AI_SERVICE_TIMEOUT", "60")),
            max_tokens=int(os.getenv("AI_MAX_TOKENS", "2048")),
            temperature=float(os.getenv("AI_TEMPERATURE", "0.3")),
            max_retries=int(os.getenv("AI_MAX_RETRIES", "2")),
            retry_delay=float(os.getenv("AI_RETRY_DELAY", "1.0")),
            health_cache_ttl=int(os.getenv("AI_HEALTH_CACHE_TTL", "30")),
        )


class AIService:
    """
    统一 AI 服务

    提供与 vLLM 服务交互的统一接口，所有 AI 功能通过此服务调用。
    """

    def __init__(self, config: Optional[AIServiceConfig] = None):
        """
        初始化 AI 服务

        Args:
            config: AI 服务配置，如果为 None 则从环境变量加载
        """
        self.config = config or AIServiceConfig.from_env()
        self._session = requests.Session()
        self._health_cache = {"status": None, "timestamp": 0}

    def _chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        调用 vLLM Chat Completion API（支持重试）

        Args:
            messages: 对话消息列表
            max_tokens: 最大生成 token 数
            temperature: 温度参数

        Returns:
            生成的文本内容

        Raises:
            Exception: API 调用失败时抛出
        """
        if not self.config.enabled:
            logger.warning("AI 服务已禁用")
            return ""

        # 确定使用哪个端点
        if self.config.use_proxy:
            url = f"{self.config.proxy_url}/v1/chat/completions"
            model = self.config.vllm_chat_model
        else:
            url = f"{self.config.vllm_chat_url}/v1/chat/completions"
            model = self.config.vllm_chat_model

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature or self.config.temperature,
        }

        last_error = None
        for attempt in range(self.config.max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"AI 服务重试第 {attempt} 次...")
                    time.sleep(self.config.retry_delay * attempt)

                response = self._session.post(
                    url,
                    json=payload,
                    timeout=self.config.timeout,
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]

            except requests.exceptions.Timeout:
                last_error = f"AI 服务请求超时: {url}"
                logger.error(last_error)
            except requests.exceptions.RequestException as e:
                last_error = f"AI 服务请求失败: {e}"
                logger.error(last_error)
            except (KeyError, IndexError) as e:
                last_error = f"AI 服务响应解析失败: {e}"
                logger.error(last_error)
                # 响应解析失败不重试
                raise

        # 所有重试都失败
        raise Exception(last_error)

    def health_check(self, use_cache: bool = True) -> bool:
        """
        检查 AI 服务健康状态（支持缓存）

        Args:
            use_cache: 是否使用缓存结果

        Returns:
            服务是否健康
        """
        current_time = time.time()

        # 使用缓存
        if use_cache and self._health_cache["status"] is not None:
            cache_age = current_time - self._health_cache["timestamp"]
            if cache_age < self.config.health_cache_ttl:
                return self._health_cache["status"]

        # 执行健康检查
        try:
            if self.config.use_proxy:
                # 检查代理服务的健康状态
                url = f"{self.config.proxy_url}/health"
            else:
                url = f"{self.config.vllm_chat_url}/health"

            response = self._session.get(url, timeout=5)
            is_healthy = response.status_code == 200

            # 更新缓存
            self._health_cache["status"] = is_healthy
            self._health_cache["timestamp"] = current_time

            return is_healthy

        except Exception as e:
            logger.debug(f"健康检查失败: {e}")
            # 更新缓存为不健康
            self._health_cache["status"] = False
            self._health_cache["timestamp"] = current_time
            return False

    # ========== 元数据 AI 标注功能 ==========

    def annotate_column(
        self,
        column_name: str,
        data_type: str,
        sample_values: List[str],
        table_name: Optional[str] = None,
        existing_comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        AI 标注数据库列

        Args:
            column_name: 列名
            data_type: 数据类型
            sample_values: 样本值列表
            table_name: 表名（可选，提供更多上下文）
            existing_comment: 已有注释（可选）

        Returns:
            {
                "description": "业务描述",
                "business_term": "业务术语",
                "suggested_tags": ["标签1", "标签2"],
                "data_quality_hint": "数据质量提示"
            }
        """
        # 限制样本数量
        samples = sample_values[:5] if sample_values else []
        samples_str = ", ".join([f'"{s}"' for s in samples]) if samples else "无"

        context = f"表名: {table_name}\n" if table_name else ""
        if existing_comment:
            context += f"已有注释: {existing_comment}\n"

        prompt = f"""你是一个数据库元数据专家。请分析以下数据库列并提供业务描述。

{context}列名: {column_name}
数据类型: {data_type}
样本值: {samples_str}

请以 JSON 格式返回以下信息（只返回 JSON，不要其他内容）：
{{
    "description": "简洁的中文业务描述（1-2句话）",
    "business_term": "标准业务术语（如：用户ID、创建时间等）",
    "suggested_tags": ["相关标签1", "相关标签2"],
    "data_quality_hint": "数据质量提示（如有问题则说明，无问题则为空字符串）"
}}"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self._chat_completion(messages, max_tokens=512, temperature=0.2)

            # 尝试解析 JSON
            # 处理可能的 markdown 代码块
            content = response.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])

            result = json.loads(content)
            return {
                "description": result.get("description", ""),
                "business_term": result.get("business_term", ""),
                "suggested_tags": result.get("suggested_tags", []),
                "data_quality_hint": result.get("data_quality_hint", ""),
            }

        except json.JSONDecodeError as e:
            logger.warning(f"AI 响应解析失败，使用规则匹配: {e}")
            return self._fallback_annotate_column(column_name, data_type)
        except Exception as e:
            logger.warning(f"AI 标注失败，使用规则匹配: {e}")
            return self._fallback_annotate_column(column_name, data_type)

    def annotate_table(
        self,
        table_name: str,
        columns: List[Dict[str, str]],
        sample_data: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        AI 标注数据库表

        Args:
            table_name: 表名
            columns: 列信息列表 [{"name": "...", "type": "..."}]
            sample_data: 样本数据（可选）

        Returns:
            {
                "description": "表描述",
                "business_domain": "业务域",
                "suggested_tags": ["标签1", "标签2"]
            }
        """
        cols_str = "\n".join([f"  - {c['name']} ({c['type']})" for c in columns[:20]])

        prompt = f"""你是一个数据库元数据专家。请分析以下数据库表并提供业务描述。

表名: {table_name}
列列表:
{cols_str}

请以 JSON 格式返回以下信息（只返回 JSON，不要其他内容）：
{{
    "description": "简洁的中文业务描述（1-2句话）",
    "business_domain": "所属业务域（如：用户管理、订单管理、财务等）",
    "suggested_tags": ["相关标签1", "相关标签2"]
}}"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self._chat_completion(messages, max_tokens=512, temperature=0.2)

            content = response.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])

            result = json.loads(content)
            return {
                "description": result.get("description", ""),
                "business_domain": result.get("business_domain", ""),
                "suggested_tags": result.get("suggested_tags", []),
            }

        except Exception as e:
            logger.warning(f"AI 表标注失败: {e}")
            return {
                "description": "",
                "business_domain": "",
                "suggested_tags": [],
            }

    def batch_annotate_columns(
        self,
        table_name: str,
        columns: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        批量标注多个列（优化 API 调用）

        Args:
            table_name: 表名
            columns: 列信息列表，每个包含 name, type, samples

        Returns:
            标注结果列表
        """
        if not columns:
            return []

        # 构建批量请求
        cols_info = []
        for col in columns[:30]:  # 限制单次批量数量
            samples = col.get("samples", [])[:3]
            samples_str = ", ".join([f'"{s}"' for s in samples]) if samples else "无"
            cols_info.append(f"- {col['name']} ({col['type']}): 样本={samples_str}")

        cols_str = "\n".join(cols_info)

        prompt = f"""你是一个数据库元数据专家。请分析以下数据库表的所有列并提供业务描述。

表名: {table_name}
列列表:
{cols_str}

请以 JSON 数组格式返回每列的信息（只返回 JSON 数组，不要其他内容）：
[
    {{
        "column_name": "列名",
        "description": "简洁的中文业务描述",
        "business_term": "标准业务术语"
    }},
    ...
]"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self._chat_completion(messages, max_tokens=2048, temperature=0.2)

            content = response.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])

            results = json.loads(content)

            # 建立列名到结果的映射
            result_map = {r["column_name"]: r for r in results if "column_name" in r}

            # 按原始顺序返回结果
            final_results = []
            for col in columns:
                col_name = col["name"]
                if col_name in result_map:
                    final_results.append(result_map[col_name])
                else:
                    # 使用规则匹配作为后备
                    fallback = self._fallback_annotate_column(col_name, col.get("type", ""))
                    fallback["column_name"] = col_name
                    final_results.append(fallback)

            return final_results

        except Exception as e:
            logger.warning(f"批量 AI 标注失败，使用规则匹配: {e}")
            return [
                {
                    "column_name": col["name"],
                    **self._fallback_annotate_column(col["name"], col.get("type", ""))
                }
                for col in columns
            ]

    def _fallback_annotate_column(
        self,
        column_name: str,
        data_type: str,
    ) -> Dict[str, Any]:
        """基于规则的后备标注方法"""
        name_descriptions = {
            "id": "主键ID",
            "name": "名称",
            "title": "标题",
            "description": "描述",
            "status": "状态",
            "type": "类型",
            "created_at": "创建时间",
            "updated_at": "更新时间",
            "deleted_at": "删除时间",
            "created_by": "创建者",
            "updated_by": "更新者",
            "is_active": "是否启用",
            "is_deleted": "是否删除",
            "email": "邮箱地址",
            "phone": "电话号码",
            "mobile": "手机号码",
            "address": "地址",
            "amount": "金额",
            "price": "价格",
            "quantity": "数量",
        }

        col_lower = column_name.lower()
        description = ""

        # 精确匹配
        if col_lower in name_descriptions:
            description = name_descriptions[col_lower]
        elif col_lower.endswith("_id"):
            ref = col_lower[:-3].replace("_", " ")
            description = f"{ref} 关联ID"
        elif col_lower.endswith("_time") or col_lower.endswith("_date"):
            description = "时间字段"
        elif col_lower.startswith("is_"):
            description = "布尔标识字段"

        return {
            "description": description,
            "business_term": "",
            "suggested_tags": [],
            "data_quality_hint": "",
        }

    # ========== 敏感数据分析功能 ==========

    def analyze_sensitivity(
        self,
        column_name: str,
        data_type: str,
        sample_values: List[str],
    ) -> Dict[str, Any]:
        """
        AI 分析列数据的敏感性

        Args:
            column_name: 列名
            data_type: 数据类型
            sample_values: 样本值列表

        Returns:
            {
                "is_sensitive": True/False,
                "sensitivity_type": "pii/financial/health/credential/none",
                "sensitivity_level": "public/internal/confidential/restricted",
                "confidence": 0.0-1.0,
                "reason": "判断理由",
                "suggested_masking": "建议的脱敏方式"
            }
        """
        samples = sample_values[:10] if sample_values else []
        samples_str = "\n".join([f"  - {s}" for s in samples]) if samples else "无样本数据"

        prompt = f"""你是一个数据安全专家。请分析以下数据库列是否包含敏感信息。

列名: {column_name}
数据类型: {data_type}
样本数据:
{samples_str}

敏感数据类型说明：
- pii: 个人身份信息（姓名、身份证、手机号、邮箱、地址等）
- financial: 金融信息（银行卡号、账户余额、交易记录等）
- health: 健康医疗信息
- credential: 凭证信息（密码、密钥、令牌等）
- none: 非敏感数据

敏感级别说明：
- public: 可公开
- internal: 内部使用
- confidential: 机密
- restricted: 严格限制

请以 JSON 格式返回分析结果（只返回 JSON，不要其他内容）：
{{
    "is_sensitive": true或false,
    "sensitivity_type": "pii/financial/health/credential/none",
    "sensitivity_level": "public/internal/confidential/restricted",
    "confidence": 0.0到1.0之间的数字,
    "reason": "判断理由（简洁说明）",
    "suggested_masking": "建议的脱敏方式（如：部分掩码、哈希等）"
}}"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self._chat_completion(messages, max_tokens=512, temperature=0.1)

            content = response.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])

            result = json.loads(content)
            return {
                "is_sensitive": result.get("is_sensitive", False),
                "sensitivity_type": result.get("sensitivity_type", "none"),
                "sensitivity_level": result.get("sensitivity_level", "public"),
                "confidence": float(result.get("confidence", 0.5)),
                "reason": result.get("reason", ""),
                "suggested_masking": result.get("suggested_masking", ""),
            }

        except Exception as e:
            logger.warning(f"AI 敏感性分析失败: {e}")
            return {
                "is_sensitive": False,
                "sensitivity_type": "none",
                "sensitivity_level": "public",
                "confidence": 0.0,
                "reason": f"AI 分析失败: {str(e)}",
                "suggested_masking": "",
            }

    # ========== ETL 清洗规则推荐 ==========

    def recommend_cleaning_rules(
        self,
        table_name: str,
        columns: List[Dict[str, Any]],
        data_quality_stats: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        AI 推荐数据清洗规则

        Args:
            table_name: 表名
            columns: 列信息列表
            data_quality_stats: 数据质量统计（空值率、唯一性等）

        Returns:
            清洗规则推荐列表
        """
        cols_info = []
        for col in columns[:20]:
            stats = data_quality_stats.get(col["name"], {})
            null_rate = stats.get("null_rate", 0)
            uniqueness = stats.get("uniqueness", 0)
            cols_info.append(
                f"- {col['name']} ({col['type']}): "
                f"空值率={null_rate:.1%}, 唯一性={uniqueness:.1%}"
            )

        cols_str = "\n".join(cols_info)

        prompt = f"""你是一个数据工程专家。请根据以下表结构和数据质量统计，推荐数据清洗规则。

表名: {table_name}
列信息:
{cols_str}

请以 JSON 数组格式返回清洗规则推荐（只返回 JSON 数组，不要其他内容）：
[
    {{
        "column": "列名",
        "rule_type": "null_handling/dedup/format/outlier/type_cast",
        "description": "规则描述",
        "config": {{"strategy": "...", "参数": "..."}},
        "priority": 1-10的优先级
    }}
]

规则类型说明：
- null_handling: 空值处理（填充、删除）
- dedup: 去重
- format: 格式标准化
- outlier: 异常值处理
- type_cast: 类型转换"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self._chat_completion(messages, max_tokens=1024, temperature=0.3)

            content = response.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])

            return json.loads(content)

        except Exception as e:
            logger.warning(f"AI 清洗规则推荐失败: {e}")
            return []


# ========== 全局实例管理 ==========

_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """获取 AI 服务单例"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
