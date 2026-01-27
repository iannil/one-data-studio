"""
多页文档处理服务
- 页面分类（正文、附件、签署页）
- 页面合并策略
- 跨页表格处理
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class MultiPageProcessor:
    """多页文档处理器"""

    def __init__(self):
        """初始化处理器"""
        pass

    def process(
        self,
        pages: List[Dict],
        template: Optional[Dict] = None
    ) -> Dict:
        """
        处理多页文档

        Args:
            pages: 页面列表，每页包含text、tables、layout等信息
            template: 文档模板（可选）

        Returns:
            处理结果
        """
        total_pages = len(pages)

        result = {
            "total_pages": total_pages,
            "pages": [],
            "classified_pages": {
                "cover": [],
                "content": [],
                "attachment": [],
                "signature": []
            },
            "merged_content": None,
            "cross_page_tables": [],
            "summary": {}
        }

        for page_num, page_data in enumerate(pages):
            page_result = self._process_page(page_data, page_num, total_pages, template)
            result["pages"].append(page_result)

            # 页面分类
            page_type = self._classify_page(page_result, page_num, total_pages)
            result["classified_pages"][page_type].append(page_num)

        # 合并内容
        result["merged_content"] = self._merge_pages(result["pages"], template)

        # 处理跨页表格
        result["cross_page_tables"] = self._handle_cross_page_tables(result["pages"])

        # 生成摘要
        result["summary"] = self._generate_summary(result)

        return result

    def _process_page(
        self,
        page_data: Dict,
        page_num: int,
        total_pages: int,
        template: Optional[Dict] = None
    ) -> Dict:
        """处理单个页面"""
        result = {
            "page_number": page_num + 1,
            "text": page_data.get("text", ""),
            "tables": page_data.get("tables", []),
            "layout": page_data.get("layout", {}),
            "fields": {},
            "page_type": None
        }

        # 如果有模板，尝试提取字段
        if template:
            result["fields"] = self._extract_fields_from_page(
                result["text"],
                template
            )

        return result

    def _classify_page(
        self,
        page_data: Dict,
        page_num: int,
        total_pages: int
    ) -> str:
        """
        分类页面类型

        Args:
            page_data: 页面数据
            page_num: 页码（从0开始）
            total_pages: 总页数

        Returns:
            页面类型
        """
        text = page_data.get("text", "")
        layout = page_data.get("layout", {})
        page_number = page_data.get("page_number", page_num + 1)

        # 第一页通常是封面
        if page_num == 0:
            if self._is_cover_page(text, layout):
                return "cover"

        # 最后一页通常是签署页
        if page_num == total_pages - 1:
            if self._is_signature_page(text, layout):
                return "signature"

        # 检查是否是附件页
        if self._is_attachment_page(text):
            return "attachment"

        # 检查是否是中间的签署页
        if self._is_signature_page(text, layout):
            return "signature"

        return "content"

    def _is_cover_page(self, text: str, layout: Dict) -> bool:
        """判断是否为封面页"""
        # 封面特征：文字较少，包含标题关键词
        cover_keywords = [
            "合同", "协议", "订单", "报价单", "收据", "发票",
            "采购合同", "销售合同", "服务协议", "合作协议"
        ]

        has_keyword = any(kw in text for kw in cover_keywords)
        is_short = len(text) < 800  # 封面文字通常较少

        return has_keyword and is_short

    def _is_signature_page(self, text: str, layout: Dict) -> bool:
        """判断是否为签署页"""
        signature_keywords = [
            "签字", "盖章", "签署", "甲方签字", "乙方签字",
            "委托方签字", "受托方签字", "法定代表人签字",
            "授权代表签字", "日期", "年", "月", "日"
        ]

        # 统计关键词出现次数
        keyword_count = sum(1 for kw in signature_keywords if kw in text)

        # 至少出现2个关键词才认为是签署页
        if keyword_count >= 2:
            return True

        # 检查布局信息中的签名区域
        key_regions = layout.get("key_regions", {})
        if key_regions.get("has_signatures"):
            return True

        return False

    def _is_attachment_page(self, text: str) -> bool:
        """判断是否为附件页"""
        attachment_keywords = ["附件", "附录", "补充", "Appendix", "Annex"]

        for keyword in attachment_keywords:
            if keyword in text:
                return True

        return False

    def _merge_pages(
        self,
        pages: List[Dict],
        template: Optional[Dict] = None
    ) -> Dict:
        """
        合并多页内容

        Args:
            pages: 页面列表
            template: 模板配置

        Returns:
            合并后的内容
        """
        merged = {
            "fields": {},
            "tables": [],
            "full_text": "",
            "page_ranges": {
                "content": [],
                "signature": [],
                "attachment": []
            }
        }

        # 收集内容页范围
        for page in pages:
            page_type = page.get("page_type", "content")
            page_num = page.get("page_number", 0)
            if page_type == "content":
                merged["page_ranges"]["content"].append(page_num)
            elif page_type == "signature":
                merged["page_ranges"]["signature"].append(page_num)
            elif page_type == "attachment":
                merged["page_ranges"]["attachment"].append(page_num)

        # 合并字段（优先取非空值，后面的覆盖前面的）
        for page in pages:
            page_type = page.get("page_type", "content")
            # 附件页的字段不合并到主内容
            if page_type == "attachment":
                continue

            for key, value in page.get("fields", {}).items():
                if value and (key not in merged["fields"] or not merged["fields"][key]):
                    merged["fields"][key] = value

        # 合并表格
        content_tables = []
        for page in pages:
            page_type = page.get("page_type", "content")
            if page_type == "attachment":
                # 附件的表格单独处理
                continue

            for table in page.get("tables", []):
                content_tables.append({
                    **table,
                    "page": page.get("page_number", 0)
                })

        # 尝试合并跨页表格
        merged["tables"] = self._merge_similar_tables(content_tables)

        # 合并全文
        full_texts = []
        for page in pages:
            text = page.get("text", "")
            if text:
                full_texts.append(f"--- 第{page.get('page_number', 0)}页 ---\n{text}")

        merged["full_text"] = "\n\n".join(full_texts)

        return merged

    def _merge_similar_tables(self, tables: List[Dict]) -> List[Dict]:
        """
        合并相似的表格（可能是跨页表格）

        Args:
            tables: 表格列表

        Returns:
            合并后的表格列表
        """
        if not tables:
            return []

        merged = []
        i = 0

        while i < len(tables):
            current_table = tables[i]

            # 检查是否与下一个表格相似
            if i + 1 < len(tables):
                next_table = tables[i + 1]

                if self._are_tables_similar(current_table, next_table):
                    # 合并表格
                    merged_table = self._merge_two_tables(current_table, next_table)
                    merged.append(merged_table)
                    i += 2  # 跳过下一个表格
                    continue

            merged.append(current_table)
            i += 1

        return merged

    def _are_tables_similar(self, table1: Dict, table2: Dict) -> bool:
        """判断两个表格是否相似（可能是同一表格的跨页）"""
        # 检查表头是否相同
        headers1 = table1.get("headers", [])
        headers2 = table2.get("headers", [])

        if not headers1 or not headers2:
            return False

        # 表头数量应该相同
        if len(headers1) != len(headers2):
            return False

        # 表头内容应该相同
        # 容错：允许OCR识别误差
        match_count = 0
        for h1, h2 in zip(headers1, headers2):
            if self._are_strings_similar(h1, h2):
                match_count += 1

        similarity = match_count / len(headers1)
        return similarity >= 0.8

    def _are_strings_similar(self, s1: str, s2: str) -> bool:
        """判断两个字符串是否相似"""
        if not s1 or not s2:
            return False

        # 完全相同
        if s1 == s2:
            return True

        # 去除空格后相同
        if s1.replace(" ", "") == s2.replace(" ", ""):
            return True

        # 简单的编辑距离判断
        if abs(len(s1) - len(s2)) <= 2:
            return True

        return False

    def _merge_two_tables(self, table1: Dict, table2: Dict) -> Dict:
        """合并两个表格"""
        merged = {
            "headers": table1.get("headers", []),
            "rows": [],
            "row_count": 0,
            "col_count": table1.get("col_count", 0),
            "merged": True,
            "source_pages": [
                table1.get("page", 0),
                table2.get("page", 0)
            ]
        }

        # 合并行（第二个表格的表头可能需要跳过）
        rows1 = table1.get("rows", [])
        rows2 = table2.get("rows", [])

        merged["rows"] = rows1 + rows2
        merged["row_count"] = len(merged["rows"])

        return merged

    def _handle_cross_page_tables(self, pages: List[Dict]) -> List[Dict]:
        """
        处理跨页表格

        Args:
            pages: 页面列表

        Returns:
            跨页表格信息
        """
        cross_page_tables = []

        for i, page in enumerate(pages):
            tables = page.get("tables", [])

            for j, table in enumerate(tables):
                # 检查表格是否被截断（最后一行不完整）
                if self._is_table_truncated(table):
                    # 查找下一页是否有相似的表格
                    if i + 1 < len(pages):
                        next_page = pages[i + 1]
                        next_tables = next_page.get("tables", [])

                        for k, next_table in enumerate(next_tables):
                            if self._are_tables_similar(table, next_table):
                                cross_page_tables.append({
                                    "type": "cross_page",
                                    "first_page": page.get("page_number"),
                                    "second_page": next_page.get("page_number"),
                                    "table_index": j,
                                    "next_table_index": k,
                                    "status": "detected"
                                })

        return cross_page_tables

    def _is_table_truncated(self, table: Dict) -> bool:
        """判断表格是否被截断"""
        # 简化判断：检查最后一行是否包含明显的不完整特征
        rows = table.get("rows", [])

        if not rows:
            return False

        last_row = rows[-1]

        # 检查是否有空单元格
        empty_count = sum(1 for cell in last_row if not cell or cell.strip() == "")

        # 如果最后一行有超过50%的空单元格，可能是被截断
        return empty_count > len(last_row) * 0.5

    def _extract_fields_from_page(
        self,
        text: str,
        template: Dict
    ) -> Dict:
        """从单页文本中提取字段"""
        fields = {}
        field_definitions = template.get("fields", [])

        for field_def in field_definitions:
            key = field_def.get("key")
            keywords = field_def.get("keywords", [])

            if not key:
                continue

            # 使用关键词查找字段值
            value = self._find_value_by_keywords(text, keywords)
            if value:
                fields[key] = value

        return fields

    def _find_value_by_keywords(self, text: str, keywords: List[str]) -> Optional[str]:
        """根据关键词查找值"""
        import re

        for keyword in keywords:
            # 尝试匹配"关键词：值"的模式
            pattern = rf"{keyword}[:：\s]*([^\n\r]+?)(?=\n|$|，|；)"
            match = re.search(pattern, text)

            if match:
                value = match.group(1).strip()
                # 过滤掉明显不是值的文本
                if value and len(value) < 100:
                    return value

        return None

    def _generate_summary(self, result: Dict) -> Dict:
        """生成文档摘要"""
        classified = result.get("classified_pages", {})

        return {
            "total_pages": result.get("total_pages", 0),
            "cover_pages": len(classified.get("cover", [])),
            "content_pages": len(classified.get("content", [])),
            "signature_pages": len(classified.get("signature", [])),
            "attachment_pages": len(classified.get("attachment", [])),
            "cross_page_table_count": len(result.get("cross_page_tables", [])),
            "total_tables": sum(len(p.get("tables", [])) for p in result.get("pages", [])),
            "fields_extracted": len(result.get("merged_content", {}).get("fields", {}))
        }

    def extract_key_info(self, result: Dict) -> Dict:
        """
        从处理结果中提取关键信息

        Args:
            result: process方法返回的结果

        Returns:
            关键信息摘要
        """
        merged = result.get("merged_content", {})
        classified = result.get("classified_pages", {})
        summary = result.get("summary", {})

        return {
            "document_structure": {
                "has_cover": len(classified.get("cover", [])) > 0,
                "cover_page": classified.get("cover", [None])[0],
                "has_signature": len(classified.get("signature", [])) > 0,
                "signature_pages": classified.get("signature", []),
                "has_attachment": len(classified.get("attachment", [])) > 0,
                "attachment_pages": classified.get("attachment", []),
                "content_page_range": self._get_page_range(classified.get("content", []))
            },
            "fields": merged.get("fields", {}),
            "tables_count": len(merged.get("tables", [])),
            "cross_page_tables": result.get("cross_page_tables", []),
            "completeness": {
                "total_fields": len(merged.get("fields", {})),
                "total_tables": summary.get("total_tables", 0),
                "pages_processed": summary.get("total_pages", 0)
            }
        }

    def _get_page_range(self, pages: List[int]) -> Dict:
        """获取页码范围"""
        if not pages:
            return {"start": None, "end": None, "count": 0}

        return {
            "start": min(pages),
            "end": max(pages),
            "count": len(pages)
        }


# 便捷函数
def process_multi_page_document(pages: List[Dict], template: Optional[Dict] = None) -> Dict:
    """
    处理多页文档的便捷函数

    Args:
        pages: 页面列表
        template: 模板配置

    Returns:
        处理结果
    """
    processor = MultiPageProcessor()
    return processor.process(pages, template)
