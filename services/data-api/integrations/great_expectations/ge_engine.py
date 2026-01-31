"""
Great Expectations 校验引擎

封装 GE 的核心校验流程，提供与平台质量规则兼容的接口。
在 GE 不可用时自动降级。
"""

import logging
import os
from typing import Any, Dict, Optional

from .config import GEConfig
from .expectation_mapper import build_expectation_kwargs, is_ge_supported

logger = logging.getLogger(__name__)

# 延迟导入 Great Expectations（可选依赖）
GE_AVAILABLE = False
try:
    import great_expectations as gx
    from great_expectations.data_context import FileDataContext
    GE_AVAILABLE = True
except ImportError:
    gx = None
    FileDataContext = None
    logger.info("Great Expectations not installed, GE engine will be disabled")


class GEValidationEngine:
    """Great Expectations 校验引擎"""

    def __init__(self, config: Optional[GEConfig] = None):
        self.config = config or GEConfig.from_env()
        self._context: Optional[Any] = None
        self._initialized = False

    @property
    def available(self) -> bool:
        """GE 是否可用"""
        return GE_AVAILABLE and self.config.enabled

    def _ensure_context(self) -> Optional[Any]:
        """延迟初始化 GE FileDataContext"""
        if not self.available:
            return None

        if self._context is not None:
            return self._context

        try:
            context_root = self.config.context_root_dir
            os.makedirs(context_root, exist_ok=True)

            self._context = gx.get_context(context_root_dir=context_root)
            self._initialized = True
            logger.info(f"GE FileDataContext initialized at {context_root}")
            return self._context
        except Exception as e:
            logger.error(f"Failed to initialize GE context: {e}")
            return None

    def validate_rule(
        self,
        rule_type: str,
        target_table: str,
        target_column: str,
        config: Dict[str, Any],
        rule_expression: str = "",
        db_connection=None,
    ) -> Optional[Dict[str, Any]]:
        """
        使用 GE 执行单条质量规则

        Args:
            rule_type: 规则类型（对应 QualityRuleType.value）
            target_table: 目标表名
            target_column: 目标列名
            config: 规则额外配置
            rule_expression: 规则表达式
            db_connection: SQLAlchemy 连接（可选）

        Returns:
            校验结果字典，或 None 表示 GE 不可用/不支持
        """
        if not self.available:
            return None

        if not is_ge_supported(rule_type):
            return None

        context = self._ensure_context()
        if context is None:
            return None

        try:
            expectation_name, kwargs = build_expectation_kwargs(
                rule_type=rule_type,
                target_column=target_column,
                config=config,
                rule_expression=rule_expression,
            )

            # 构建数据源连接
            db_url = self.config.db_url
            datasource_name = f"runtime_{target_table}"

            datasource = context.sources.add_or_update_sql(
                name=datasource_name,
                connection_string=db_url,
            )

            # 获取数据资产
            data_asset = datasource.add_table_asset(
                name=target_table,
                table_name=target_table,
            )

            batch_request = data_asset.build_batch_request()

            # 创建 Expectation Suite
            suite_name = f"runtime_{target_table}_{rule_type}"
            suite = context.add_or_update_expectation_suite(expectation_suite_name=suite_name)

            # 获取 Validator
            validator = context.get_validator(
                batch_request=batch_request,
                expectation_suite_name=suite_name,
            )

            # 执行 Expectation
            result = getattr(validator, expectation_name)(**kwargs)

            return self._parse_validation_result(result, expectation_name)

        except Exception as e:
            logger.error(f"GE validation failed for {rule_type} on {target_table}.{target_column}: {e}")
            return None

    def _parse_validation_result(
        self,
        result: Any,
        expectation_name: str,
    ) -> Dict[str, Any]:
        """将 GE 校验结果转换为平台兼容格式"""
        try:
            result_dict = result.to_json_dict() if hasattr(result, "to_json_dict") else {}
            ge_result = result_dict.get("result", {})

            total_rows = ge_result.get("element_count", 0)
            unexpected_count = ge_result.get("unexpected_count", 0)
            passed_rows = total_rows - unexpected_count

            score = (passed_rows / total_rows * 100) if total_rows > 0 else 100.0

            return {
                "engine": "great_expectations",
                "expectation": expectation_name,
                "success": result_dict.get("success", False),
                "score": round(score, 2),
                "total_rows": total_rows,
                "passed_rows": passed_rows,
                "failed_rows": unexpected_count,
                "unexpected_percent": ge_result.get("unexpected_percent", 0),
                "partial_unexpected_list": ge_result.get("partial_unexpected_list", [])[:20],
            }
        except Exception as e:
            logger.error(f"Failed to parse GE result: {e}")
            return {
                "engine": "great_expectations",
                "expectation": expectation_name,
                "success": False,
                "score": 0.0,
                "error": str(e),
            }

    def generate_data_docs(self) -> Optional[str]:
        """
        生成 GE Data Docs（HTML 报告）

        Returns:
            Data Docs 路径，或 None
        """
        context = self._ensure_context()
        if context is None:
            return None

        try:
            context.build_data_docs()
            docs_dir = os.path.join(self.config.context_root_dir, "uncommitted", "data_docs", "local_site")
            index_path = os.path.join(docs_dir, "index.html")
            if os.path.exists(index_path):
                logger.info(f"GE Data Docs generated at {index_path}")
                return index_path
            return docs_dir
        except Exception as e:
            logger.error(f"Failed to generate GE Data Docs: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """获取 GE 引擎状态"""
        return {
            "ge_installed": GE_AVAILABLE,
            "ge_version": gx.__version__ if GE_AVAILABLE else None,
            "enabled": self.config.enabled,
            "context_initialized": self._initialized,
            "context_root_dir": self.config.context_root_dir,
            "datasource_name": self.config.datasource_name,
        }
