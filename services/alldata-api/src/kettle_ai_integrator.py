"""
AI 规则到 Kettle 组件自动配置服务
Phase 2 P1: 将 AI 清洗/填充规则转换为 Kettle 转换步骤

功能：
- 将 CleaningRecommendation 转换为 Kettle 步骤 XML
- 将 ImputationRule 转换为 Kettle 步骤 XML
- 将脱敏规则注入到 Kettle 转换中
- 动态修改现有 Kettle 转换文件
"""

import logging
import xml.etree.ElementTree as ET
from copy import deepcopy
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class KettleStepPosition:
    """Kettle 步骤位置"""
    x: int = 0
    y: int = 0

    def next_position(self, offset_x: int = 200, offset_y: int = 0) -> "KettleStepPosition":
        return KettleStepPosition(self.x + offset_x, self.y + offset_y)


class KettleAIIntegrator:
    """AI 规则到 Kettle 组件转换器"""

    # 步骤类型常量
    STEP_IF_NULL = "IfFieldValueIsNull"
    STEP_VALUE_MAPPER = "ValueMapper"
    STEP_FILTER_ROWS = "FilterRows"
    STEP_REGEX_EVAL = "RegexEvaluation"
    STEP_STRING_OPS = "StringOperations"
    STEP_CALCULATOR = "Calculator"
    STEP_UNIQUE = "Unique"
    STEP_SORT = "SortRows"
    STEP_JS_VALUE = "ScriptValueMod"  # Modified JavaScript Value
    STEP_STREAM_LOOKUP = "StreamLookup"  # 流查找（内存关联）
    STEP_DB_LOOKUP = "DBLookup"          # 数据库查找

    def __init__(self):
        self.step_counter = 0

    def _get_step_name(self, prefix: str) -> str:
        """生成唯一步骤名"""
        self.step_counter += 1
        return f"{prefix}_{self.step_counter}"

    # =========================================
    # 清洗规则转换
    # =========================================

    def cleaning_rule_to_kettle_step(
        self,
        rule: Dict[str, Any],
        position: KettleStepPosition = None,
    ) -> Tuple[ET.Element, KettleStepPosition]:
        """
        将清洗规则转换为 Kettle 步骤

        Args:
            rule: CleaningRecommendation 字典
            position: 步骤位置

        Returns:
            (步骤 XML 元素, 下一个位置)
        """
        if position is None:
            position = KettleStepPosition(300, 200)

        cleaning_type = rule.get("cleaning_type", "")
        kettle_step_type = rule.get("kettle_step_type", "")
        kettle_config = rule.get("kettle_config", {})
        column_name = rule.get("column_name", "")

        step_element = None

        if kettle_step_type == self.STEP_IF_NULL:
            step_element = self._create_if_null_step(
                name=kettle_config.get("step_name", f"空值处理_{column_name}"),
                field_name=column_name,
                replace_value=kettle_config.get("replace_value", ""),
                position=position,
            )

        elif kettle_step_type == self.STEP_VALUE_MAPPER:
            step_element = self._create_value_mapper_step(
                name=kettle_config.get("step_name", f"值映射_{column_name}"),
                field_name=column_name,
                mappings=kettle_config.get("mappings", []),
                position=position,
            )

        elif kettle_step_type == self.STEP_FILTER_ROWS:
            step_element = self._create_filter_rows_step(
                name=kettle_config.get("step_name", f"过滤_{column_name}"),
                condition=kettle_config.get("condition", ""),
                send_true_to=kettle_config.get("send_true_to", ""),
                send_false_to=kettle_config.get("send_false_to", ""),
                position=position,
            )

        elif kettle_step_type == self.STEP_REGEX_EVAL:
            step_element = self._create_regex_eval_step(
                name=kettle_config.get("step_name", f"正则_{column_name}"),
                field_name=column_name,
                pattern=kettle_config.get("pattern", ""),
                result_field=kettle_config.get("result_field", f"{column_name}_matched"),
                position=position,
            )

        elif kettle_step_type == self.STEP_STRING_OPS:
            step_element = self._create_string_operations_step(
                name=kettle_config.get("step_name", f"字符串处理_{column_name}"),
                field_name=column_name,
                operations=kettle_config.get("operations", []),
                position=position,
            )

        elif kettle_step_type == self.STEP_UNIQUE:
            step_element = self._create_unique_step(
                name=kettle_config.get("step_name", f"去重_{column_name}"),
                key_fields=kettle_config.get("key_fields", [column_name]),
                position=position,
            )

        elif kettle_step_type == self.STEP_CALCULATOR:
            step_element = self._create_calculator_step(
                name=kettle_config.get("step_name", f"计算_{column_name}"),
                calculations=kettle_config.get("calculations", []),
                position=position,
            )

        else:
            # 默认使用脚本步骤
            step_element = self._create_js_value_step(
                name=kettle_config.get("step_name", f"处理_{column_name}"),
                script=kettle_config.get("script", f"// 处理 {column_name}"),
                position=position,
            )

        return step_element, position.next_position()

    # =========================================
    # 填充规则转换
    # =========================================

    def imputation_rule_to_kettle_step(
        self,
        rule: Dict[str, Any],
        position: KettleStepPosition = None,
    ) -> Tuple[ET.Element, KettleStepPosition]:
        """
        将填充规则转换为 Kettle 步骤

        Args:
            rule: ImputationRule 字典
            position: 步骤位置

        Returns:
            (步骤 XML 元素, 下一个位置)
        """
        if position is None:
            position = KettleStepPosition(300, 200)

        strategy = rule.get("strategy", "")
        kettle_step_type = rule.get("kettle_step_type", "IfFieldValueIsNull")
        kettle_config = rule.get("kettle_config", {})
        column_name = rule.get("column_name", "")

        step_element = None

        if kettle_step_type == self.STEP_IF_NULL:
            step_element = self._create_if_null_step(
                name=kettle_config.get("step_name", f"填充_{column_name}"),
                field_name=kettle_config.get("field_name", column_name),
                replace_value=kettle_config.get("replace_value", ""),
                position=position,
            )

        elif kettle_step_type == self.STEP_FILTER_ROWS:
            # 用于删除含缺失值的行
            step_element = self._create_filter_rows_step(
                name=kettle_config.get("step_name", f"过滤空值_{column_name}"),
                condition=kettle_config.get("condition", f"NOT ISNULL([{column_name}])"),
                send_true_to=kettle_config.get("send_true_to", ""),
                send_false_to=kettle_config.get("send_false_to", ""),
                position=position,
            )

        elif kettle_step_type == self.STEP_CALCULATOR:
            # 用于标记缺失或简单计算
            step_element = self._create_calculator_step(
                name=kettle_config.get("step_name", f"计算_{column_name}"),
                calculations=[{
                    "field_name": kettle_config.get("result_field", f"{column_name}_is_missing"),
                    "calc_type": "NVL",
                    "field_a": column_name,
                    "field_b": "",
                    "field_c": "",
                }],
                position=position,
            )

        elif kettle_step_type == "AnalyticQuery":
            # 用于前向/后向填充
            step_element = self._create_analytic_query_step(
                name=kettle_config.get("step_name", f"窗口填充_{column_name}"),
                subject_field=column_name,
                result_field=kettle_config.get("result_field", f"{column_name}_filled"),
                function_type=kettle_config.get("function_type", "LAG"),
                offset=kettle_config.get("offset", 1),
                position=position,
            )

        elif kettle_step_type == self.STEP_STREAM_LOOKUP:
            # 用于关联字段推断（基于流查找）
            step_element = self._create_stream_lookup_step(
                name=kettle_config.get("step_name", f"关联填充_{column_name}"),
                lookup_step=kettle_config.get("lookup_step", "查找数据源"),
                key_fields=kettle_config.get("lookup_fields", []),
                value_fields=[{
                    "lookup_field": kettle_config.get("result_field", column_name),
                    "rename": column_name,
                    "default_value": kettle_config.get("default_value", ""),
                    "value_type": "String",
                }],
                position=position,
            )

        elif kettle_step_type == self.STEP_DB_LOOKUP:
            # 用于数据库关联查找填充
            step_element = self._create_db_lookup_step(
                name=kettle_config.get("step_name", f"数据库查找_{column_name}"),
                connection=kettle_config.get("connection", "default"),
                schema=kettle_config.get("schema", ""),
                table=kettle_config.get("lookup_table", ""),
                key_fields=kettle_config.get("lookup_fields", []),
                value_fields=[{
                    "field": kettle_config.get("result_field", column_name),
                    "rename": column_name,
                    "default_value": kettle_config.get("default_value", ""),
                    "value_type": "String",
                }],
                position=position,
            )

        else:
            # 默认使用 If Null 步骤
            step_element = self._create_if_null_step(
                name=f"填充_{column_name}",
                field_name=column_name,
                replace_value=str(rule.get("fill_value", "")),
                position=position,
            )

        return step_element, position.next_position()

    # =========================================
    # 脱敏规则转换
    # =========================================

    def masking_rule_to_kettle_step(
        self,
        column_name: str,
        masking_config: Dict[str, Any],
        position: KettleStepPosition = None,
    ) -> Tuple[ET.Element, KettleStepPosition]:
        """
        将脱敏规则转换为 Kettle 步骤

        Args:
            column_name: 列名
            masking_config: 脱敏配置
            position: 步骤位置

        Returns:
            (步骤 XML 元素, 下一个位置)
        """
        if position is None:
            position = KettleStepPosition(300, 200)

        strategy = masking_config.get("strategy", "partial_mask")
        params = masking_config.get("params", {})

        # 生成脱敏 JavaScript 代码
        script = self._generate_masking_script(column_name, strategy, params)

        step_element = self._create_js_value_step(
            name=f"脱敏_{column_name}",
            script=script,
            fields=[{
                "name": column_name,
                "type": "String",
                "replace": True,
            }],
            position=position,
        )

        return step_element, position.next_position()

    def _generate_masking_script(
        self,
        column_name: str,
        strategy: str,
        params: Dict[str, Any],
    ) -> str:
        """生成脱敏 JavaScript 代码"""
        scripts = {
            "partial_mask": f"""
// 部分遮盖
var value = {column_name};
if (value != null && value.length > 0) {{
    var start = {params.get('start', 0)};
    var end = {params.get('end', -4)};
    var mask_char = '{params.get('mask_char', '*')}';

    if (end < 0) end = value.length + end;
    if (end < start) end = start;

    var prefix = value.substring(0, start);
    var suffix = value.substring(end);
    var mask = '';
    for (var i = start; i < end; i++) mask += mask_char;

    {column_name} = prefix + mask + suffix;
}}
""",
            "hash": f"""
// 哈希处理
var value = {column_name};
if (value != null) {{
    // 简化的哈希（实际应用中应使用 MessageDigest）
    var hash = 0;
    for (var i = 0; i < value.length; i++) {{
        hash = ((hash << 5) - hash) + value.charCodeAt(i);
        hash = hash & hash;
    }}
    {column_name} = Math.abs(hash).toString(16);
}}
""",
            "replace": f"""
// 替换为固定值
{column_name} = '{params.get('replacement', '***')}';
""",
            "truncate": f"""
// 截断
var value = {column_name};
if (value != null) {{
    {column_name} = value.substring(0, {params.get('length', 4)});
}}
""",
            "null_out": f"""
// 置空
{column_name} = null;
""",
            "email_mask": f"""
// 邮箱脱敏
var value = {column_name};
if (value != null && value.indexOf('@') > 0) {{
    var parts = value.split('@');
    var local = parts[0];
    var domain = parts[1];
    if (local.length > 2) {{
        local = local.substring(0, 2) + '***';
    }}
    {column_name} = local + '@' + domain;
}}
""",
            "phone_mask": f"""
// 手机号脱敏
var value = {column_name};
if (value != null && value.length >= 7) {{
    {column_name} = value.substring(0, 3) + '****' + value.substring(value.length - 4);
}}
""",
            "id_card_mask": f"""
// 身份证脱敏
var value = {column_name};
if (value != null && value.length >= 15) {{
    {column_name} = value.substring(0, 6) + '********' + value.substring(value.length - 4);
}}
""",
            "bank_card_mask": f"""
// 银行卡脱敏
var value = {column_name};
if (value != null && value.length >= 12) {{
    {column_name} = value.substring(0, 4) + ' **** **** ' + value.substring(value.length - 4);
}}
""",
        }

        return scripts.get(strategy, f"// 未知策略: {strategy}\n// {column_name} 保持原值")

    # =========================================
    # Kettle 步骤创建方法
    # =========================================

    def _create_if_null_step(
        self,
        name: str,
        field_name: str,
        replace_value: str,
        position: KettleStepPosition,
    ) -> ET.Element:
        """创建 IfFieldValueIsNull 步骤"""
        step = ET.Element("step")
        ET.SubElement(step, "name").text = name
        ET.SubElement(step, "type").text = "IfFieldValueIsNull"
        ET.SubElement(step, "description")
        ET.SubElement(step, "distribute").text = "Y"
        ET.SubElement(step, "custom_distribution")
        ET.SubElement(step, "copies").text = "1"

        # 字段配置
        fields = ET.SubElement(step, "fields")
        field = ET.SubElement(fields, "field")
        ET.SubElement(field, "name").text = field_name
        ET.SubElement(field, "value").text = replace_value
        ET.SubElement(field, "mask")
        ET.SubElement(field, "set_empty_string").text = "N"

        ET.SubElement(step, "selectFields").text = "N"
        ET.SubElement(step, "selectValuesType")
        ET.SubElement(step, "replaceAllByValue")
        ET.SubElement(step, "replaceAllMask")
        ET.SubElement(step, "setEmptyStringAll").text = "N"

        # 位置
        gui = ET.SubElement(step, "GUI")
        ET.SubElement(gui, "xloc").text = str(position.x)
        ET.SubElement(gui, "yloc").text = str(position.y)
        ET.SubElement(gui, "draw").text = "Y"

        return step

    def _create_value_mapper_step(
        self,
        name: str,
        field_name: str,
        mappings: List[Dict[str, str]],
        position: KettleStepPosition,
    ) -> ET.Element:
        """创建 ValueMapper 步骤"""
        step = ET.Element("step")
        ET.SubElement(step, "name").text = name
        ET.SubElement(step, "type").text = "ValueMapper"
        ET.SubElement(step, "description")
        ET.SubElement(step, "distribute").text = "Y"
        ET.SubElement(step, "custom_distribution")
        ET.SubElement(step, "copies").text = "1"

        ET.SubElement(step, "field_to_use").text = field_name
        ET.SubElement(step, "target_field")
        ET.SubElement(step, "non_match_default")

        fields = ET.SubElement(step, "fields")
        for mapping in mappings:
            field = ET.SubElement(fields, "field")
            ET.SubElement(field, "source_value").text = mapping.get("source", "")
            ET.SubElement(field, "target_value").text = mapping.get("target", "")

        gui = ET.SubElement(step, "GUI")
        ET.SubElement(gui, "xloc").text = str(position.x)
        ET.SubElement(gui, "yloc").text = str(position.y)
        ET.SubElement(gui, "draw").text = "Y"

        return step

    def _create_filter_rows_step(
        self,
        name: str,
        condition: str,
        send_true_to: str,
        send_false_to: str,
        position: KettleStepPosition,
    ) -> ET.Element:
        """创建 FilterRows 步骤"""
        step = ET.Element("step")
        ET.SubElement(step, "name").text = name
        ET.SubElement(step, "type").text = "FilterRows"
        ET.SubElement(step, "description")
        ET.SubElement(step, "distribute").text = "Y"
        ET.SubElement(step, "custom_distribution")
        ET.SubElement(step, "copies").text = "1"

        ET.SubElement(step, "send_true_to").text = send_true_to
        ET.SubElement(step, "send_false_to").text = send_false_to

        # 条件
        cond = ET.SubElement(step, "compare")
        # 解析简单条件
        if "IS NOT NULL" in condition.upper():
            field_match = condition.replace("[", "").replace("]", "").split()[0]
            ET.SubElement(cond, "name").text = field_match
            ET.SubElement(cond, "function").text = "IS NOT NULL"
        elif "!=" in condition:
            parts = condition.split("!=")
            ET.SubElement(cond, "name").text = parts[0].strip().replace("[", "").replace("]", "")
            ET.SubElement(cond, "function").text = "<>"
            ET.SubElement(cond, "value").text = parts[1].strip().strip("'\"")
        else:
            # 复杂条件使用脚本
            ET.SubElement(cond, "name").text = "TRUE"
            ET.SubElement(cond, "function").text = "="
            ET.SubElement(cond, "value").text = "TRUE"

        gui = ET.SubElement(step, "GUI")
        ET.SubElement(gui, "xloc").text = str(position.x)
        ET.SubElement(gui, "yloc").text = str(position.y)
        ET.SubElement(gui, "draw").text = "Y"

        return step

    def _create_regex_eval_step(
        self,
        name: str,
        field_name: str,
        pattern: str,
        result_field: str,
        position: KettleStepPosition,
    ) -> ET.Element:
        """创建 RegexEvaluation 步骤"""
        step = ET.Element("step")
        ET.SubElement(step, "name").text = name
        ET.SubElement(step, "type").text = "RegexEvaluation"
        ET.SubElement(step, "description")
        ET.SubElement(step, "distribute").text = "Y"
        ET.SubElement(step, "custom_distribution")
        ET.SubElement(step, "copies").text = "1"

        ET.SubElement(step, "script").text = pattern
        ET.SubElement(step, "matcher").text = field_name
        ET.SubElement(step, "resultfieldname").text = result_field
        ET.SubElement(step, "usealikeregex").text = "N"
        ET.SubElement(step, "usealikegroup").text = "N"
        ET.SubElement(step, "allowcapturegroups").text = "N"
        ET.SubElement(step, "replacefields").text = "N"
        ET.SubElement(step, "canoneq").text = "N"
        ET.SubElement(step, "caseinsensitive").text = "N"
        ET.SubElement(step, "comment").text = "N"
        ET.SubElement(step, "dotall").text = "N"
        ET.SubElement(step, "multiline").text = "N"
        ET.SubElement(step, "unicode").text = "N"
        ET.SubElement(step, "unix").text = "N"

        gui = ET.SubElement(step, "GUI")
        ET.SubElement(gui, "xloc").text = str(position.x)
        ET.SubElement(gui, "yloc").text = str(position.y)
        ET.SubElement(gui, "draw").text = "Y"

        return step

    def _create_string_operations_step(
        self,
        name: str,
        field_name: str,
        operations: List[str],
        position: KettleStepPosition,
    ) -> ET.Element:
        """创建 StringOperations 步骤"""
        step = ET.Element("step")
        ET.SubElement(step, "name").text = name
        ET.SubElement(step, "type").text = "StringOperations"
        ET.SubElement(step, "description")
        ET.SubElement(step, "distribute").text = "Y"
        ET.SubElement(step, "custom_distribution")
        ET.SubElement(step, "copies").text = "1"

        fields = ET.SubElement(step, "fields")
        field = ET.SubElement(fields, "field")
        ET.SubElement(field, "in_stream_name").text = field_name
        ET.SubElement(field, "out_stream_name")

        # 操作映射
        op_map = {
            "trim": ("both", "none"),
            "trim_left": ("left", "none"),
            "trim_right": ("right", "none"),
            "upper": ("none", "upper"),
            "lower": ("none", "lower"),
            "capitalize": ("none", "cap_first"),
        }

        trim_type = "none"
        case_type = "none"
        for op in operations:
            if op in op_map:
                t, c = op_map[op]
                if t != "none":
                    trim_type = t
                if c != "none":
                    case_type = c

        ET.SubElement(field, "trim_type").text = trim_type
        ET.SubElement(field, "lower_upper").text = case_type
        ET.SubElement(field, "padding_type").text = "none"
        ET.SubElement(field, "pad_char")
        ET.SubElement(field, "pad_len")
        ET.SubElement(field, "init_cap").text = "N"
        ET.SubElement(field, "mask_xml").text = "none"
        ET.SubElement(field, "digits").text = "none"
        ET.SubElement(field, "remove_special_characters").text = "none"

        gui = ET.SubElement(step, "GUI")
        ET.SubElement(gui, "xloc").text = str(position.x)
        ET.SubElement(gui, "yloc").text = str(position.y)
        ET.SubElement(gui, "draw").text = "Y"

        return step

    def _create_unique_step(
        self,
        name: str,
        key_fields: List[str],
        position: KettleStepPosition,
    ) -> ET.Element:
        """创建 Unique 步骤（需要先排序）"""
        step = ET.Element("step")
        ET.SubElement(step, "name").text = name
        ET.SubElement(step, "type").text = "Unique"
        ET.SubElement(step, "description")
        ET.SubElement(step, "distribute").text = "Y"
        ET.SubElement(step, "custom_distribution")
        ET.SubElement(step, "copies").text = "1"

        ET.SubElement(step, "count_rows").text = "N"
        ET.SubElement(step, "count_field")
        ET.SubElement(step, "reject_duplicate_row").text = "N"
        ET.SubElement(step, "error_description")

        fields = ET.SubElement(step, "fields")
        for field_name in key_fields:
            field = ET.SubElement(fields, "field")
            ET.SubElement(field, "name").text = field_name
            ET.SubElement(field, "case_insensitive").text = "N"

        gui = ET.SubElement(step, "GUI")
        ET.SubElement(gui, "xloc").text = str(position.x)
        ET.SubElement(gui, "yloc").text = str(position.y)
        ET.SubElement(gui, "draw").text = "Y"

        return step

    def _create_calculator_step(
        self,
        name: str,
        calculations: List[Dict[str, Any]],
        position: KettleStepPosition,
    ) -> ET.Element:
        """创建 Calculator 步骤"""
        step = ET.Element("step")
        ET.SubElement(step, "name").text = name
        ET.SubElement(step, "type").text = "Calculator"
        ET.SubElement(step, "description")
        ET.SubElement(step, "distribute").text = "Y"
        ET.SubElement(step, "custom_distribution")
        ET.SubElement(step, "copies").text = "1"
        ET.SubElement(step, "failIfNoFile").text = "Y"

        calcs = ET.SubElement(step, "calculation")
        for calc in calculations:
            calc_elem = ET.SubElement(calcs, "calculation")
            ET.SubElement(calc_elem, "field_name").text = calc.get("field_name", "")
            ET.SubElement(calc_elem, "calc_type").text = calc.get("calc_type", "CONSTANT")
            ET.SubElement(calc_elem, "field_a").text = calc.get("field_a", "")
            ET.SubElement(calc_elem, "field_b").text = calc.get("field_b", "")
            ET.SubElement(calc_elem, "field_c").text = calc.get("field_c", "")
            ET.SubElement(calc_elem, "value_type").text = calc.get("value_type", "String")
            ET.SubElement(calc_elem, "value_length").text = str(calc.get("value_length", -1))
            ET.SubElement(calc_elem, "value_precision").text = str(calc.get("value_precision", -1))
            ET.SubElement(calc_elem, "remove").text = "N"
            ET.SubElement(calc_elem, "conversion_mask")
            ET.SubElement(calc_elem, "decimal_symbol")
            ET.SubElement(calc_elem, "grouping_symbol")
            ET.SubElement(calc_elem, "currency_symbol")

        gui = ET.SubElement(step, "GUI")
        ET.SubElement(gui, "xloc").text = str(position.x)
        ET.SubElement(gui, "yloc").text = str(position.y)
        ET.SubElement(gui, "draw").text = "Y"

        return step

    def _create_analytic_query_step(
        self,
        name: str,
        subject_field: str,
        result_field: str,
        function_type: str,
        offset: int,
        position: KettleStepPosition,
    ) -> ET.Element:
        """创建 AnalyticQuery 步骤（用于前向/后向填充）"""
        step = ET.Element("step")
        ET.SubElement(step, "name").text = name
        ET.SubElement(step, "type").text = "AnalyticQuery"
        ET.SubElement(step, "description")
        ET.SubElement(step, "distribute").text = "Y"
        ET.SubElement(step, "custom_distribution")
        ET.SubElement(step, "copies").text = "1"

        # 分组（空表示整个数据集）
        ET.SubElement(step, "group")

        # 字段配置
        fields = ET.SubElement(step, "fields")
        field = ET.SubElement(fields, "field")
        ET.SubElement(field, "aggregate_name").text = result_field
        ET.SubElement(field, "subject").text = subject_field
        ET.SubElement(field, "type").text = function_type  # LAG or LEAD
        ET.SubElement(field, "valuefield").text = str(offset)

        gui = ET.SubElement(step, "GUI")
        ET.SubElement(gui, "xloc").text = str(position.x)
        ET.SubElement(gui, "yloc").text = str(position.y)
        ET.SubElement(gui, "draw").text = "Y"

        return step

    def _create_stream_lookup_step(
        self,
        name: str,
        lookup_step: str,
        key_fields: List[str],
        value_fields: List[Dict[str, str]],
        position: KettleStepPosition = None,
    ) -> ET.Element:
        """
        创建 StreamLookup 步骤（流查找，用于关联字段推断填充）

        StreamLookup 从另一个流中根据关联键查找匹配行，
        类似于 SQL 的 LEFT JOIN，用于跨数据流的缺失值填充。

        Args:
            name: 步骤名称
            lookup_step: 查找源步骤名称
            key_fields: 关联键字段列表
            value_fields: 查找值字段列表，每项包含:
                - lookup_field: 查找表中的字段名
                - rename: 结果字段名
                - default_value: 默认值
                - value_type: 值类型
            position: 步骤位置
        """
        if position is None:
            position = KettleStepPosition(300, 200)

        step = ET.Element("step")
        ET.SubElement(step, "name").text = name
        ET.SubElement(step, "type").text = "StreamLookup"
        ET.SubElement(step, "description").text = "基于关联字段的流查找填充"
        ET.SubElement(step, "distribute").text = "Y"
        ET.SubElement(step, "custom_distribution")
        ET.SubElement(step, "copies").text = "1"

        # 查找来源步骤
        lookup = ET.SubElement(step, "from").text = lookup_step

        ET.SubElement(step, "input_sorted").text = "N"
        ET.SubElement(step, "preserve_memory").text = "Y"

        # 关联键
        keys = ET.SubElement(step, "lookup")
        for key_field in key_fields:
            key = ET.SubElement(keys, "key")
            ET.SubElement(key, "name").text = key_field
            ET.SubElement(key, "field").text = key_field

        # 查找值字段
        values = ET.SubElement(step, "value")
        for vf in value_fields:
            val = ET.SubElement(values, "value")
            ET.SubElement(val, "name").text = vf.get("lookup_field", "")
            ET.SubElement(val, "rename").text = vf.get("rename", vf.get("lookup_field", ""))
            ET.SubElement(val, "default").text = vf.get("default_value", "")
            ET.SubElement(val, "type").text = vf.get("value_type", "String")

        gui = ET.SubElement(step, "GUI")
        ET.SubElement(gui, "xloc").text = str(position.x)
        ET.SubElement(gui, "yloc").text = str(position.y)
        ET.SubElement(gui, "draw").text = "Y"

        return step

    def _create_db_lookup_step(
        self,
        name: str,
        connection: str,
        schema: str,
        table: str,
        key_fields: List[str],
        value_fields: List[Dict[str, str]],
        cache: bool = True,
        cache_size: int = 5000,
        position: KettleStepPosition = None,
    ) -> ET.Element:
        """
        创建 DBLookup 步骤（数据库查找，用于跨表关联填充）

        DBLookup 从数据库表中根据关联键查找匹配行，
        类似于 SQL 的子查询或 Kettle Database Lookup 步骤。

        Args:
            name: 步骤名称
            connection: 数据库连接名称
            schema: 数据库 schema
            table: 查找表名
            key_fields: 关联键字段列表
            value_fields: 返回值字段列表，每项包含:
                - field: 查找表中的字段名
                - rename: 结果字段名
                - default_value: 默认值
                - value_type: 值类型
            cache: 是否启用缓存
            cache_size: 缓存大小
            position: 步骤位置
        """
        if position is None:
            position = KettleStepPosition(300, 200)

        step = ET.Element("step")
        ET.SubElement(step, "name").text = name
        ET.SubElement(step, "type").text = "DBLookup"
        ET.SubElement(step, "description").text = "数据库查找填充缺失值"
        ET.SubElement(step, "distribute").text = "Y"
        ET.SubElement(step, "custom_distribution")
        ET.SubElement(step, "copies").text = "1"

        # 数据库连接
        ET.SubElement(step, "connection").text = connection
        ET.SubElement(step, "schema").text = schema
        ET.SubElement(step, "table").text = table
        ET.SubElement(step, "cache").text = "Y" if cache else "N"
        ET.SubElement(step, "cache_size").text = str(cache_size)
        ET.SubElement(step, "orderby")
        ET.SubElement(step, "fail_on_multiple").text = "N"
        ET.SubElement(step, "eat_row_on_failure").text = "N"

        # 关联键
        lookup = ET.SubElement(step, "lookup")
        for key_field in key_fields:
            key = ET.SubElement(lookup, "key")
            ET.SubElement(key, "name").text = key_field
            ET.SubElement(key, "field").text = key_field
            ET.SubElement(key, "condition").text = "="

        # 返回值字段
        for vf in value_fields:
            val = ET.SubElement(lookup, "value")
            ET.SubElement(val, "name").text = vf.get("field", "")
            ET.SubElement(val, "rename").text = vf.get("rename", vf.get("field", ""))
            ET.SubElement(val, "default").text = vf.get("default_value", "")
            ET.SubElement(val, "type").text = vf.get("value_type", "String")

        gui = ET.SubElement(step, "GUI")
        ET.SubElement(gui, "xloc").text = str(position.x)
        ET.SubElement(gui, "yloc").text = str(position.y)
        ET.SubElement(gui, "draw").text = "Y"

        return step

    def _create_js_value_step(
        self,
        name: str,
        script: str,
        fields: List[Dict[str, Any]] = None,
        position: KettleStepPosition = None,
    ) -> ET.Element:
        """创建 Modified JavaScript Value 步骤"""
        if position is None:
            position = KettleStepPosition(300, 200)

        step = ET.Element("step")
        ET.SubElement(step, "name").text = name
        ET.SubElement(step, "type").text = "ScriptValueMod"
        ET.SubElement(step, "description")
        ET.SubElement(step, "distribute").text = "Y"
        ET.SubElement(step, "custom_distribution")
        ET.SubElement(step, "copies").text = "1"

        ET.SubElement(step, "compatible").text = "N"
        ET.SubElement(step, "optimizationLevel").text = "9"

        # 脚本
        jsScripts = ET.SubElement(step, "jsScripts")
        jsScript = ET.SubElement(jsScripts, "jsScript")
        ET.SubElement(jsScript, "jsScript_type").text = "0"
        ET.SubElement(jsScript, "jsScript_name").text = "Script 1"
        ET.SubElement(jsScript, "jsScript_script").text = script

        # 输出字段
        fields_elem = ET.SubElement(step, "fields")
        if fields:
            for f in fields:
                field = ET.SubElement(fields_elem, "field")
                ET.SubElement(field, "name").text = f.get("name", "")
                ET.SubElement(field, "rename").text = f.get("rename", f.get("name", ""))
                ET.SubElement(field, "type").text = f.get("type", "String")
                ET.SubElement(field, "length").text = str(f.get("length", -1))
                ET.SubElement(field, "precision").text = str(f.get("precision", -1))
                ET.SubElement(field, "replace").text = "Y" if f.get("replace", False) else "N"

        gui = ET.SubElement(step, "GUI")
        ET.SubElement(gui, "xloc").text = str(position.x)
        ET.SubElement(gui, "yloc").text = str(position.y)
        ET.SubElement(gui, "draw").text = "Y"

        return step

    # =========================================
    # 转换注入方法
    # =========================================

    def inject_ai_steps_to_transformation(
        self,
        trans_xml: str,
        ai_steps: List[ET.Element],
        insert_after_step: str = None,
    ) -> str:
        """
        将 AI 步骤注入到 Kettle 转换中

        Args:
            trans_xml: 原始转换 XML
            ai_steps: 要注入的步骤列表
            insert_after_step: 插入位置（步骤名），None 表示在输入步骤后

        Returns:
            修改后的 XML 字符串
        """
        root = ET.fromstring(trans_xml)

        # 找到所有步骤
        steps = root.findall(".//step")
        step_names = [s.find("name").text for s in steps if s.find("name") is not None]

        # 确定插入位置
        if insert_after_step is None:
            # 找输入步骤（TableInput, CSVInput 等）
            input_types = ["TableInput", "CsvInput", "TextFileInput", "ExcelInput"]
            for step in steps:
                step_type = step.find("type")
                if step_type is not None and step_type.text in input_types:
                    insert_after_step = step.find("name").text
                    break

        # 插入步骤
        for ai_step in ai_steps:
            root.append(ai_step)

        # 更新 hops（连接）
        if insert_after_step and ai_steps:
            # 找到原来从 insert_after_step 出发的 hop
            order = root.find("order")
            if order is None:
                order = ET.SubElement(root, "order")

            # 获取 AI 步骤名称
            ai_step_names = [s.find("name").text for s in ai_steps if s.find("name") is not None]

            # 找到原有的 hop
            original_next = None
            for hop in order.findall("hop"):
                from_elem = hop.find("from")
                if from_elem is not None and from_elem.text == insert_after_step:
                    original_next = hop.find("to").text
                    # 更新这个 hop 指向第一个 AI 步骤
                    hop.find("to").text = ai_step_names[0]
                    break

            # 创建 AI 步骤之间的 hops
            for i in range(len(ai_step_names) - 1):
                hop = ET.SubElement(order, "hop")
                ET.SubElement(hop, "from").text = ai_step_names[i]
                ET.SubElement(hop, "to").text = ai_step_names[i + 1]
                ET.SubElement(hop, "enabled").text = "Y"

            # 最后一个 AI 步骤连接到原来的下一个步骤
            if original_next and ai_step_names:
                hop = ET.SubElement(order, "hop")
                ET.SubElement(hop, "from").text = ai_step_names[-1]
                ET.SubElement(hop, "to").text = original_next
                ET.SubElement(hop, "enabled").text = "Y"

        return ET.tostring(root, encoding="unicode")

    def inject_masking_rules(
        self,
        trans_xml: str,
        masking_configs: Dict[str, Dict[str, Any]],
    ) -> str:
        """
        将脱敏规则注入到 Kettle 转换中

        Args:
            trans_xml: 原始转换 XML
            masking_configs: 列名到脱敏配置的映射

        Returns:
            修改后的 XML 字符串
        """
        masking_steps = []
        position = KettleStepPosition(500, 200)

        for column_name, config in masking_configs.items():
            step, position = self.masking_rule_to_kettle_step(
                column_name, config, position
            )
            masking_steps.append(step)
            position = position.next_position(0, 100)  # 垂直排列

        # 找输出步骤前的位置插入
        root = ET.fromstring(trans_xml)
        output_types = ["TableOutput", "TextFileOutput", "ExcelOutput", "InsertUpdate"]

        insert_before = None
        for step in root.findall(".//step"):
            step_type = step.find("type")
            if step_type is not None and step_type.text in output_types:
                insert_before = step.find("name").text
                break

        # 找到连接到输出的步骤
        if insert_before:
            order = root.find("order")
            if order:
                for hop in order.findall("hop"):
                    to_elem = hop.find("to")
                    if to_elem is not None and to_elem.text == insert_before:
                        insert_after = hop.find("from").text
                        return self.inject_ai_steps_to_transformation(
                            trans_xml, masking_steps, insert_after
                        )

        # 默认行为
        return self.inject_ai_steps_to_transformation(trans_xml, masking_steps)


# 创建全局实例
_kettle_ai_integrator: Optional[KettleAIIntegrator] = None


def get_kettle_ai_integrator() -> KettleAIIntegrator:
    """获取 Kettle AI 集成器单例"""
    global _kettle_ai_integrator
    if _kettle_ai_integrator is None:
        _kettle_ai_integrator = KettleAIIntegrator()
    return _kettle_ai_integrator
