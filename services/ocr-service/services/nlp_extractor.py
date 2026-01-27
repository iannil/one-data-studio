"""
高级 NLP 信息提取服务
Phase 2 P2: 基于 PaddleNLP UIE 的命名实体识别和关系抽取

功能：
- 命名实体识别（NER）: 人名、组织、地点、日期、金额等
- 关系抽取（RE）: 实体间的语义关系
- 文本分类: 文档类型自动识别
- 关键信息提取: 结构化信息抽取（发票号、合同金额等）
- 与现有 ai_extractor.py 互补（本地模型，无需 API 调用）
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# PaddleNLP 延迟导入标志
_paddle_available = None
_taskflow = None


def _check_paddle():
    """检查 PaddleNLP 是否可用"""
    global _paddle_available
    if _paddle_available is not None:
        return _paddle_available
    try:
        import paddlenlp  # noqa: F401
        _paddle_available = True
        logger.info(f"PaddleNLP 版本: {paddlenlp.__version__}")
    except ImportError:
        _paddle_available = False
        logger.warning("PaddleNLP 未安装，NLP 提取功能不可用。安装: pip install paddlenlp")
    return _paddle_available


def _get_taskflow(task: str, model: str = None, **kwargs):
    """获取 PaddleNLP Taskflow 实例（带缓存）"""
    global _taskflow
    if _taskflow is None:
        _taskflow = {}

    cache_key = f"{task}:{model or 'default'}"
    if cache_key not in _taskflow:
        if not _check_paddle():
            return None
        from paddlenlp import Taskflow
        if model:
            _taskflow[cache_key] = Taskflow(task, model=model, **kwargs)
        else:
            _taskflow[cache_key] = Taskflow(task, **kwargs)
    return _taskflow[cache_key]


class EntityType(str, Enum):
    """实体类型枚举"""
    PERSON = "人物"
    ORGANIZATION = "组织机构"
    LOCATION = "地点"
    DATE = "日期"
    TIME = "时间"
    MONEY = "金额"
    PERCENT = "百分比"
    PHONE = "电话"
    EMAIL = "邮箱"
    ID_NUMBER = "证件号"
    PRODUCT = "产品"
    EVENT = "事件"
    QUANTITY = "数量"
    ADDRESS = "地址"


class RelationType(str, Enum):
    """关系类型枚举"""
    BELONG_TO = "属于"
    LOCATED_IN = "位于"
    PRODUCED_BY = "生产"
    SIGNED_BY = "签署"
    ISSUED_BY = "签发"
    PAID_TO = "支付给"
    AMOUNT_OF = "金额为"
    DATED = "日期为"
    EMPLOYED_BY = "任职于"


@dataclass
class Entity:
    """识别到的实体"""
    text: str
    entity_type: str
    start: int = -1
    end: int = -1
    confidence: float = 0.0
    source: str = "paddlenlp"  # paddlenlp, regex, rule

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "entity_type": self.entity_type,
            "start": self.start,
            "end": self.end,
            "confidence": round(self.confidence, 4),
            "source": self.source,
        }


@dataclass
class Relation:
    """识别到的关系"""
    subject: Entity
    predicate: str
    object: Entity
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject": self.subject.to_dict(),
            "predicate": self.predicate,
            "object": self.object.to_dict(),
            "confidence": round(self.confidence, 4),
        }


@dataclass
class NLPExtractionResult:
    """NLP 提取结果"""
    entities: List[Entity] = field(default_factory=list)
    relations: List[Relation] = field(default_factory=list)
    text_classification: Optional[Dict[str, Any]] = None
    key_info: Dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "relations": [r.to_dict() for r in self.relations],
            "text_classification": self.text_classification,
            "key_info": self.key_info,
            "entity_count": len(self.entities),
            "relation_count": len(self.relations),
            "duration_ms": self.duration_ms,
        }


# 预定义的信息提取 Schema（用于 UIE 模型）
EXTRACTION_SCHEMAS = {
    "invoice": {
        "entities": ["发票号码", "开票日期", "购买方", "销售方", "金额", "税额", "价税合计",
                     "发票类型", "购方税号", "销方税号", "地址电话", "开户行及账号"],
        "relations": [("购买方", "购买"), ("销售方", "销售"), ("发票号码", "对应发票")],
    },
    "contract": {
        "entities": ["甲方", "乙方", "合同编号", "签订日期", "合同金额", "合同期限",
                     "项目名称", "付款方式", "违约金", "签署地点"],
        "relations": [("甲方", "签署"), ("乙方", "签署"), ("合同金额", "金额为")],
    },
    "report": {
        "entities": ["报告名称", "报告日期", "编制单位", "审核人", "审批人",
                     "报告周期", "统计指标", "数据来源"],
        "relations": [("编制单位", "编制"), ("审核人", "审核")],
    },
    "general": {
        "entities": ["人物", "组织机构", "地点", "日期", "时间",
                     "金额", "百分比", "电话", "邮箱"],
        "relations": [],
    },
}

# 正则增强规则（补充 NLP 模型不足）
REGEX_PATTERNS = {
    "电话": [
        r"(?:(?:\+86)?1[3-9]\d{9})",                          # 手机号
        r"(?:0\d{2,3}-?\d{7,8})",                              # 固话
    ],
    "邮箱": [
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}",
    ],
    "证件号": [
        r"\d{17}[\dXx]",                                       # 身份证
        r"[A-Z]\d{8}",                                         # 护照
        r"\d{15}",                                              # 旧身份证
    ],
    "金额": [
        r"(?:(?:人民币|¥|￥|RMB)\s*)[\d,]+(?:\.\d{1,2})?(?:\s*(?:元|万元|亿元))?",
        r"[\d,]+(?:\.\d{1,2})?\s*(?:元|万元|亿元)",
    ],
    "日期": [
        r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日号]?",
        r"\d{4}年\d{1,2}月",
    ],
    "百分比": [
        r"\d+(?:\.\d+)?%",
        r"\d+(?:\.\d+)?‰",
    ],
    "发票号码": [
        r"\d{8}",                                              # 8位发票号
        r"\d{20}",                                             # 20位发票代码+号码
    ],
}


class NLPExtractorService:
    """
    高级 NLP 信息提取服务

    基于 PaddleNLP UIE (Universal Information Extraction) 模型，
    提供中文命名实体识别、关系抽取和结构化信息提取。
    UIE 模型支持零样本和少样本学习，可以通过 Schema 定义灵活地提取各类信息。
    """

    def __init__(self, uie_model: str = "uie-base"):
        """
        初始化 NLP 提取服务

        Args:
            uie_model: UIE 模型名称
                - uie-base: 基础模型（推荐）
                - uie-medium: 中型模型
                - uie-mini: 轻量模型（速度快）
                - uie-micro: 极轻模型
                - uie-nano: 超轻量
        """
        self.uie_model = uie_model
        self._uie_engine = None
        self._ner_engine = None

    @property
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return _check_paddle()

    def _get_uie(self, schema: List[str]):
        """获取 UIE 引擎（动态 Schema）"""
        if not self.is_available:
            return None

        from paddlenlp import Taskflow
        # UIE 每次 Schema 变化需要重新设置
        if self._uie_engine is None:
            self._uie_engine = Taskflow(
                "information_extraction",
                schema=schema,
                model=self.uie_model,
            )
        else:
            self._uie_engine.set_schema(schema)
        return self._uie_engine

    def extract_entities(
        self,
        text: str,
        entity_types: List[str] = None,
        use_regex: bool = True,
        confidence_threshold: float = 0.5,
    ) -> List[Entity]:
        """
        命名实体识别（NER）

        使用 UIE 模型进行实体抽取，支持自定义实体类型。

        Args:
            text: 输入文本
            entity_types: 实体类型列表（None 表示通用类型）
            use_regex: 是否使用正则增强
            confidence_threshold: 置信度阈值

        Returns:
            识别到的实体列表
        """
        if not text or not text.strip():
            return []

        entities = []

        # 1. 使用 UIE 模型提取
        if entity_types is None:
            entity_types = EXTRACTION_SCHEMAS["general"]["entities"]

        uie = self._get_uie(entity_types)
        if uie is not None:
            try:
                results = uie(text)
                for result in results:
                    for etype, etype_results in result.items():
                        for item in etype_results:
                            if item.get("probability", 0) >= confidence_threshold:
                                ent = Entity(
                                    text=item["text"],
                                    entity_type=etype,
                                    start=item.get("start", -1),
                                    end=item.get("end", -1),
                                    confidence=item.get("probability", 0),
                                    source="paddlenlp_uie",
                                )
                                entities.append(ent)
            except Exception as e:
                logger.warning(f"UIE 实体提取失败: {e}")

        # 2. 正则增强
        if use_regex:
            regex_entities = self._regex_extract(text, confidence_threshold)
            # 去重：避免正则结果与 UIE 结果重复
            existing_spans = set((e.text, e.entity_type) for e in entities)
            for re_ent in regex_entities:
                if (re_ent.text, re_ent.entity_type) not in existing_spans:
                    entities.append(re_ent)

        return entities

    def extract_relations(
        self,
        text: str,
        relation_schema: List[Tuple[str, str]] = None,
        confidence_threshold: float = 0.5,
    ) -> List[Relation]:
        """
        关系抽取（RE）

        使用 UIE 模型进行关系抽取。关系 Schema 格式为 [(主体类型, 关系类型)]，
        模型会自动识别对应的客体。

        Args:
            text: 输入文本
            relation_schema: 关系定义列表 [(主体类型, 关系)]
            confidence_threshold: 置信度阈值

        Returns:
            识别到的关系列表
        """
        if not text or not text.strip():
            return []

        if relation_schema is None:
            relation_schema = [
                ("人物", "任职于"),
                ("组织机构", "位于"),
                ("产品", "生产"),
            ]

        relations = []

        # 构建 UIE Schema（嵌套 Schema 用于关系抽取）
        schema = {}
        for subject_type, predicate in relation_schema:
            if subject_type not in schema:
                schema[subject_type] = []
            schema[subject_type].append(predicate)

        # 转换为 UIE 支持的格式
        uie_schema = []
        for subject_type, predicates in schema.items():
            uie_schema.append({subject_type: predicates})

        uie = self._get_uie(uie_schema)
        if uie is None:
            return []

        try:
            results = uie(text)
            for result in results:
                for subject_type, subjects in result.items():
                    for subject_item in subjects:
                        subject_text = subject_item["text"]
                        subject_prob = subject_item.get("probability", 0)

                        if subject_prob < confidence_threshold:
                            continue

                        subject_entity = Entity(
                            text=subject_text,
                            entity_type=subject_type,
                            start=subject_item.get("start", -1),
                            end=subject_item.get("end", -1),
                            confidence=subject_prob,
                            source="paddlenlp_uie",
                        )

                        # 处理关系
                        relations_data = subject_item.get("relations", {})
                        for predicate, objects in relations_data.items():
                            for obj_item in objects:
                                if obj_item.get("probability", 0) < confidence_threshold:
                                    continue

                                object_entity = Entity(
                                    text=obj_item["text"],
                                    entity_type=predicate,
                                    start=obj_item.get("start", -1),
                                    end=obj_item.get("end", -1),
                                    confidence=obj_item.get("probability", 0),
                                    source="paddlenlp_uie",
                                )

                                rel = Relation(
                                    subject=subject_entity,
                                    predicate=predicate,
                                    object=object_entity,
                                    confidence=min(subject_prob, obj_item.get("probability", 0)),
                                )
                                relations.append(rel)
        except Exception as e:
            logger.warning(f"UIE 关系抽取失败: {e}")

        return relations

    def extract_structured_info(
        self,
        text: str,
        document_type: str = "general",
        custom_schema: Dict[str, Any] = None,
        confidence_threshold: float = 0.5,
    ) -> NLPExtractionResult:
        """
        结构化信息提取（综合 NER + RE + 正则）

        根据文档类型自动选择提取 Schema，或使用自定义 Schema。

        Args:
            text: 输入文本
            document_type: 文档类型 (invoice, contract, report, general)
            custom_schema: 自定义 Schema（覆盖预定义 Schema）
            confidence_threshold: 置信度阈值

        Returns:
            NLPExtractionResult 结构化提取结果
        """
        start_time = time.time()

        # 获取 Schema
        if custom_schema:
            entity_types = custom_schema.get("entities", [])
            relation_defs = custom_schema.get("relations", [])
        else:
            schema = EXTRACTION_SCHEMAS.get(document_type, EXTRACTION_SCHEMAS["general"])
            entity_types = schema["entities"]
            relation_defs = schema.get("relations", [])

        # 1. 实体识别
        entities = self.extract_entities(
            text,
            entity_types=entity_types,
            use_regex=True,
            confidence_threshold=confidence_threshold,
        )

        # 2. 关系抽取
        relations = []
        if relation_defs:
            relations = self.extract_relations(
                text,
                relation_schema=relation_defs,
                confidence_threshold=confidence_threshold,
            )

        # 3. 构建关键信息字典
        key_info = self._build_key_info(entities, document_type)

        # 4. 文本分类（如果是 general 类型，尝试自动分类）
        text_classification = None
        if document_type == "general":
            text_classification = self.classify_document(text)

        duration_ms = int((time.time() - start_time) * 1000)

        return NLPExtractionResult(
            entities=entities,
            relations=relations,
            text_classification=text_classification,
            key_info=key_info,
            duration_ms=duration_ms,
        )

    def classify_document(
        self,
        text: str,
        labels: List[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        文档类型分类

        使用 UIE 的零样本分类能力判断文档类型。

        Args:
            text: 输入文本
            labels: 候选标签列表

        Returns:
            分类结果字典
        """
        if labels is None:
            labels = ["发票", "合同", "报告", "通知", "简历", "新闻", "学术论文", "其他"]

        # 使用文本分类 Taskflow
        classifier = _get_taskflow("zero_shot_text_classification")
        if classifier is None:
            # 降级：基于关键词的简单分类
            return self._keyword_classify(text, labels)

        try:
            classifier.set_schema(labels)
            results = classifier(text[:512])  # 截断过长文本
            if results:
                result = results[0]
                # 取最高置信度的标签
                best_label = None
                best_prob = 0
                predictions = result.get("predictions", [])
                for pred in predictions:
                    if pred.get("score", 0) > best_prob:
                        best_prob = pred["score"]
                        best_label = pred["label"]

                return {
                    "label": best_label,
                    "confidence": round(best_prob, 4),
                    "all_predictions": [
                        {"label": p["label"], "score": round(p["score"], 4)}
                        for p in sorted(predictions, key=lambda x: x.get("score", 0), reverse=True)
                    ],
                }
        except Exception as e:
            logger.warning(f"文本分类失败: {e}")

        return self._keyword_classify(text, labels)

    def extract_for_sensitivity_scan(
        self,
        text: str,
        column_name: str = "",
    ) -> List[Dict[str, Any]]:
        """
        敏感数据识别增强（与敏感扫描系统集成）

        识别文本中的敏感信息实体，辅助敏感数据扫描。

        Args:
            text: 输入文本
            column_name: 列名（辅助上下文）

        Returns:
            敏感信息列表
        """
        sensitive_types = [
            "人物", "电话", "邮箱", "地址", "证件号", "银行卡号",
            "金额", "组织机构",
        ]

        entities = self.extract_entities(
            text,
            entity_types=sensitive_types,
            use_regex=True,
            confidence_threshold=0.4,
        )

        # 映射到敏感数据分类
        type_mapping = {
            "人物": "pii",
            "电话": "pii",
            "邮箱": "pii",
            "地址": "pii",
            "证件号": "pii",
            "银行卡号": "financial",
            "金额": "financial",
            "组织机构": "internal",
        }

        results = []
        for entity in entities:
            sensitivity_type = type_mapping.get(entity.entity_type, "unknown")
            results.append({
                "text": entity.text,
                "entity_type": entity.entity_type,
                "sensitivity_type": sensitivity_type,
                "confidence": entity.confidence,
                "source": entity.source,
                "column_name": column_name,
            })

        return results

    # ===== 内部方法 =====

    def _regex_extract(
        self,
        text: str,
        confidence_threshold: float = 0.5,
    ) -> List[Entity]:
        """使用正则表达式补充提取"""
        entities = []
        for etype, patterns in REGEX_PATTERNS.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text):
                    ent = Entity(
                        text=match.group(),
                        entity_type=etype,
                        start=match.start(),
                        end=match.end(),
                        confidence=0.85,  # 正则匹配的固定置信度
                        source="regex",
                    )
                    entities.append(ent)
        return entities

    def _build_key_info(
        self,
        entities: List[Entity],
        document_type: str,
    ) -> Dict[str, Any]:
        """从实体列表构建关键信息字典"""
        key_info: Dict[str, Any] = {}

        # 按类型分组
        by_type: Dict[str, List[Entity]] = {}
        for ent in entities:
            if ent.entity_type not in by_type:
                by_type[ent.entity_type] = []
            by_type[ent.entity_type].append(ent)

        # 提取关键信息（每个类型取最高置信度的实体）
        for etype, type_entities in by_type.items():
            sorted_ents = sorted(type_entities, key=lambda e: e.confidence, reverse=True)
            if len(sorted_ents) == 1:
                key_info[etype] = sorted_ents[0].text
            else:
                key_info[etype] = [e.text for e in sorted_ents]

        return key_info

    def _keyword_classify(
        self,
        text: str,
        labels: List[str],
    ) -> Dict[str, Any]:
        """基于关键词的简单文本分类（降级方案）"""
        keyword_map = {
            "发票": ["发票", "开票", "税额", "价税合计", "购买方", "销售方", "增值税"],
            "合同": ["合同", "甲方", "乙方", "协议", "违约", "签字盖章", "生效"],
            "报告": ["报告", "分析", "总结", "汇报", "评估", "审计"],
            "通知": ["通知", "通告", "公告", "各部门", "特此通知"],
            "简历": ["简历", "工作经验", "教育背景", "技能", "自我评价"],
            "新闻": ["记者", "报道", "据悉", "消息", "发布会"],
            "学术论文": ["摘要", "关键词", "参考文献", "论文", "实验"],
        }

        scores = {}
        text_lower = text[:2000]  # 只检查前2000字符

        for label in labels:
            keywords = keyword_map.get(label, [])
            count = sum(1 for kw in keywords if kw in text_lower)
            scores[label] = count / max(len(keywords), 1)

        if not scores or max(scores.values()) == 0:
            return {
                "label": "其他",
                "confidence": 0.3,
                "all_predictions": [{"label": "其他", "score": 0.3}],
            }

        best_label = max(scores, key=scores.get)
        best_score = min(scores[best_label], 1.0)

        return {
            "label": best_label,
            "confidence": round(best_score, 4),
            "all_predictions": sorted(
                [{"label": l, "score": round(s, 4)} for l, s in scores.items()],
                key=lambda x: x["score"],
                reverse=True,
            ),
        }


# 全局实例
_nlp_extractor: Optional[NLPExtractorService] = None


def get_nlp_extractor(model: str = "uie-base") -> NLPExtractorService:
    """获取 NLP 提取服务单例"""
    global _nlp_extractor
    if _nlp_extractor is None:
        _nlp_extractor = NLPExtractorService(uie_model=model)
    return _nlp_extractor
