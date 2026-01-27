"""
AI信息抽取器
使用LLM从文档中提取结构化信息
支持双引擎: LLM (远程API) + PaddleNLP UIE (本地模型)
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# NLP提取器延迟导入
_nlp_extractor = None


def _get_nlp_extractor():
    """获取NLP提取器实例（延迟导入，避免启动时加载模型）"""
    global _nlp_extractor
    if _nlp_extractor is None:
        try:
            from services.nlp_extractor import get_nlp_extractor
            _nlp_extractor = get_nlp_extractor()
        except ImportError:
            logger.info("NLP extractor not available (paddlenlp not installed)")
            _nlp_extractor = False  # 标记为不可用，避免重复导入
    return _nlp_extractor if _nlp_extractor is not False else None


class AIExtractor:
    """AI信息抽取器"""

    def __init__(self, api_key: str = None, base_url: str = None):
        """
        初始化AI抽取器
        api_key: OpenAI API密钥
        base_url: API基础URL
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("AI_MODEL", "gpt-4o-mini")

        self._client = None
        self._init_client()

    def _init_client(self):
        """初始化OpenAI客户端"""
        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info("AI extractor initialized with model: %s", self.model)
        except ImportError:
            logger.warning("OpenAI library not installed")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")

    def is_available(self) -> bool:
        """检查AI抽取器是否可用"""
        return self._client is not None

    def extract_with_template(
        self,
        text: str,
        template: Dict,
        image_base64: str = None
    ) -> Dict:
        """
        使用模板提取信息

        template示例:
        {
            "type": "invoice",
            "fields": [
                {"name": "发票号码", "key": "invoice_number", "required": True},
                {"name": "开票日期", "key": "date", "required": True},
                {"name": "金额", "key": "amount", "required": True}
            ]
        }
        """
        if not self.is_available():
            logger.warning("AI extractor not available, returning empty result")
            return {"extracted": {}, "confidence": 0.0, "missing_fields": []}

        template_type = template.get("type", "general")
        fields = template.get("fields", [])

        # 构建提示词
        prompt = self._build_extraction_prompt(template_type, fields, text)

        try:
            # 构建消息
            messages = [{"role": "user", "content": prompt}]

            # 如果有图片，添加图片内容
            if image_base64:
                messages[0]["content"] = [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                    }
                ]

            # 调用API
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            # 解析结果
            result_text = response.choices[0].message.content
            extracted = json.loads(result_text)

            # 验证必填字段
            missing_fields = [
                f["name"] for f in fields
                if f.get("required", False) and f["key"] not in extracted.get("data", {})
            ]

            return {
                "extracted": extracted.get("data", {}),
                "confidence": extracted.get("confidence", 0.8),
                "missing_fields": missing_fields,
                "raw_response": extracted
            }

        except Exception as e:
            logger.error(f"AI extraction error: {e}")
            return {"extracted": {}, "confidence": 0.0, "error": str(e)}

    def _build_extraction_prompt(self, template_type: str, fields: List[Dict], text: str) -> str:
        """构建提取提示词"""

        # 字段描述
        field_descriptions = "\n".join([
            f"- {f['name']} ({f['key']}): {'必填' if f.get('required') else '选填'}"
            for f in fields
        ])

        # 模板特定的提示
        type_specific = self._get_type_specific_prompt(template_type)

        prompt = f"""你是一个专业的文档信息抽取助手。请从以下文档内容中提取指定的字段信息。

文档类型: {template_type}

需要提取的字段:
{field_descriptions}

{type_specific}

请按照以下JSON格式返回结果:
{{
  "data": {{
    "字段key1": "值1",
    "字段key2": "值2"
  }},
  "confidence": 0.95,
  "reasoning": "提取理由说明"
}}

文档内容:
{text}

请仔细阅读文档内容，准确提取每个字段的值。如果某个字段在文档中找不到，请使用null值。对于日期、金额等特殊字段，请尽量转换为标准格式。"""

        return prompt

    def _get_type_specific_prompt(self, template_type: str) -> str:
        """获取特定类型的提示"""
        prompts = {
            "invoice": """发票抽取注意事项:
- 发票号码: 通常是8-20位数字
- 开票日期: 请转换为YYYY-MM-DD格式
- 金额: 请提取不含税金额和税额，返回数字格式
- 税率: 返回百分比格式，如13%""",
            "contract": """合同抽取注意事项:
- 合同编号: 通常在合同开头
- 甲方乙方: 提取公司名称
- 合同金额: 返回数字格式
- 签订日期: 转换为YYYY-MM-DD格式
- 有效期: 提取起止日期""",
            "report": """报告抽取注意事项:
- 报告标题: 通常在文档开头
- 报告日期: 转换为YYYY-MM-DD格式
- 核心指标: 提取关键数值指标
- 报告期: 提取报告的时间范围"""
        }

        return prompts.get(template_type, "")

    def extract_invoice(self, text: str, image_base64: str = None) -> Dict:
        """提取发票信息"""
        template = {
            "type": "invoice",
            "fields": [
                {"name": "发票类型", "key": "invoice_type", "required": False},
                {"name": "发票号码", "key": "invoice_number", "required": True},
                {"name": "开票日期", "key": "invoice_date", "required": True},
                {"name": "购买方名称", "key": "buyer_name", "required": False},
                {"name": "购买方税号", "key": "buyer_tax_id", "required": False},
                {"name": "销售方名称", "key": "seller_name", "required": False},
                {"name": "销售方税号", "key": "seller_tax_id", "required": False},
                {"name": "价税合计", "key": "total_amount", "required": True},
                {"name": "金额", "key": "amount", "required": False},
                {"name": "税额", "key": "tax_amount", "required": False},
                {"name": "税率", "key": "tax_rate", "required": False},
            ]
        }

        return self.extract_with_template(text, template, image_base64)

    def extract_contract(self, text: str, image_base64: str = None) -> Dict:
        """提取合同信息"""
        template = {
            "type": "contract",
            "fields": [
                {"name": "合同编号", "key": "contract_number", "required": False},
                {"name": "合同名称", "key": "contract_name", "required": True},
                {"name": "甲方", "key": "party_a", "required": True},
                {"name": "乙方", "key": "party_b", "required": True},
                {"name": "合同金额", "key": "contract_amount", "required": False},
                {"name": "签订日期", "key": "signing_date", "required": False},
                {"name": "生效日期", "key": "effective_date", "required": False},
                {"name": "截止日期", "key": "expiry_date", "required": False},
                {"name": "合同期限", "key": "contract_period", "required": False},
            ]
        }

        return self.extract_with_template(text, template, image_base64)

    def extract_report(self, text: str, image_base64: str = None) -> Dict:
        """提取报告信息"""
        template = {
            "type": "report",
            "fields": [
                {"name": "报告标题", "key": "report_title", "required": True},
                {"name": "报告日期", "key": "report_date", "required": False},
                {"name": "报告期", "key": "report_period", "required": False},
                {"name": "核心指标", "key": "key_metrics", "required": False},
                {"name": "同比", "key": "yoy_growth", "required": False},
                {"name": "环比", "key": "mom_growth", "required": False},
            ]
        }

        return self.extract_with_template(text, template, image_base64)

    def extract_general(self, text: str, fields: List[Dict]) -> Dict:
        """通用信息抽取"""
        template = {
            "type": "general",
            "fields": fields
        }

        return self.extract_with_template(text, template)

    def extract_table_structure(self, table_data: List[List[str]], context: str = "") -> Dict:
        """
        分析表格结构，生成表头和列说明

        table_data: 二维数组形式的表格数据
        """
        if not table_data or not self.is_available():
            return {"headers": [], "column_descriptions": {}, "table_summary": ""}

        headers = table_data[0] if table_data else []
        rows = table_data[1:] if len(table_data) > 1 else []

        # 构建提示词
        sample_rows = "\n".join([
            " | ".join([str(cell) for cell in row])
            for row in rows[:5]  # 只取前5行作为示例
        ])

        prompt = f"""请分析以下表格的结构和内容。

表头: {headers}

示例数据:
{sample_rows}

请提供:
1. 每列的描述
2. 表格内容的简要总结

请以JSON格式返回:
{{
  "column_descriptions": {{
    "列名1": "列的描述",
    "列名2": "列的描述"
  }},
  "table_summary": "表格内容的总结",
  "data_types": {{
    "列名1": "数据类型(string/number/date等)",
    "列名2": "数据类型"
  }}
}}"""

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            return {
                "headers": headers,
                "column_descriptions": result.get("column_descriptions", {}),
                "table_summary": result.get("table_summary", ""),
                "data_types": result.get("data_types", {})
            }

        except Exception as e:
            logger.error(f"Table structure analysis error: {e}")
            return {
                "headers": headers,
                "column_descriptions": {},
                "table_summary": "",
                "error": str(e)
            }

    def suggest_extraction_template(self, text: str, sample_documents: List[str] = None) -> Dict:
        """
        基于样本文档，建议提取模板

        text: 样本文本内容
        sample_documents: 更多样本文档列表
        """
        if not self.is_available():
            return {"suggested_fields": [], "template_type": "general"}

        prompt = f"""请分析以下文档内容，建议一个信息提取模板。

文档内容:
{text[:4000]}

请建议:
1. 文档类型(发票/合同/报告/其他)
2. 应该提取哪些字段
3. 每个字段的说明

请以JSON格式返回:
{{
  "template_type": "文档类型",
  "suggested_fields": [
    {{
      "name": "字段中文名",
      "key": "字段key(英文)",
      "required": true/false,
      "description": "字段说明"
    }}
  ],
  "reasoning": "推荐理由"
}}"""

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            return result

        except Exception as e:
            logger.error(f"Template suggestion error: {e}")
            return {"suggested_fields": [], "error": str(e)}

    def extract_with_nlp(
        self,
        text: str,
        document_type: str = "general",
        use_llm: bool = True,
        use_nlp: bool = True,
    ) -> Dict[str, Any]:
        """
        双引擎信息抽取（LLM + 本地NLP）

        结合LLM远程API和PaddleNLP本地UIE模型进行互补提取：
        - LLM: 擅长理解复杂语义和上下文，准确率高但需要API调用
        - NLP: 本地推理无需网络，擅长结构化实体和关系抽取

        Args:
            text: 输入文本
            document_type: 文档类型 (invoice, contract, report, general)
            use_llm: 是否使用LLM引擎
            use_nlp: 是否使用本地NLP引擎

        Returns:
            合并的提取结果
        """
        result = {
            "llm_result": None,
            "nlp_result": None,
            "merged": {},
            "sources": [],
        }

        # 1. LLM提取
        if use_llm and self.is_available():
            try:
                type_method = {
                    "invoice": self.extract_invoice,
                    "contract": self.extract_contract,
                    "report": self.extract_report,
                }
                extractor = type_method.get(document_type)
                if extractor:
                    llm_result = extractor(text)
                else:
                    llm_result = self.extract_general(text, [])
                result["llm_result"] = llm_result
                result["sources"].append("llm")
                # 合并LLM结果
                if llm_result.get("extracted"):
                    result["merged"].update(llm_result["extracted"])
            except Exception as e:
                logger.warning(f"LLM extraction failed: {e}")

        # 2. NLP本地提取
        if use_nlp:
            nlp = _get_nlp_extractor()
            if nlp and nlp.is_available:
                try:
                    nlp_result = nlp.extract_structured_info(
                        text,
                        document_type=document_type,
                    )
                    result["nlp_result"] = nlp_result.to_dict()
                    result["sources"].append("nlp")

                    # 合并NLP实体到结果（不覆盖LLM已提取的字段）
                    for entity_type, value in nlp_result.key_info.items():
                        if entity_type not in result["merged"]:
                            result["merged"][entity_type] = value

                    # 添加文本分类
                    if nlp_result.text_classification:
                        result["merged"]["_document_type"] = nlp_result.text_classification.get("label")
                        result["merged"]["_classification_confidence"] = nlp_result.text_classification.get("confidence")

                except Exception as e:
                    logger.warning(f"NLP extraction failed: {e}")

        return result
