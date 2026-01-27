"""
文档布局分析服务
- 页面结构分析（段落、表格、图片区域）
- 签名区域识别
- 印章区域检测
- 页眉页脚识别
"""

import logging
import re
from typing import Dict, List, Tuple, Optional, Any
import numpy as np

logger = logging.getLogger(__name__)


class LayoutAnalyzer:
    """文档布局分析器"""

    def __init__(self):
        """初始化布局分析器"""
        self._init_paddle_structure()
        self._init_opencv()

    def _init_paddle_structure(self):
        """初始化PaddleOCR版面分析模型"""
        self._has_paddle_structure = False
        try:
            from paddleocr import PPStructure
            self.structure_engine = PPStructure(show_log=False, use_gpu=False)
            self._has_paddle_structure = True
            logger.info("PaddleOCR Structure engine initialized")
        except ImportError:
            logger.warning("PaddleOCR PPStructure not available")
        except Exception as e:
            logger.warning(f"Failed to initialize PPStructure: {e}")

    def _init_opencv(self):
        """初始化OpenCV"""
        self._has_cv2 = False
        try:
            import cv2
            self.cv2 = cv2
            self._has_cv2 = True
        except ImportError:
            logger.warning("OpenCV not available")

    def analyze_page(self, image_path: str, ocr_text: str = "") -> Dict:
        """
        分析单页文档的布局结构

        Args:
            image_path: 图片路径
            ocr_text: OCR识别的文本（可选，用于辅助分析）

        Returns:
            布局分析结果字典
        """
        result = {
            "paragraphs": [],
            "tables": [],
            "images": [],
            "signatures": [],
            "seals": [],
            "header": None,
            "footer": None,
            "page_type": None,
            "regions": []
        }

        # 使用PaddleOCR版面分析
        if self._has_paddle_structure:
            result = self._analyze_with_paddle(image_path, result)

        # 使用文本分析辅助识别签名/印章区域
        if ocr_text:
            text_based_result = self._analyze_by_text(ocr_text, result)
            result.update(text_based_result)

        return result

    def _analyze_with_paddle(self, image_path: str, result: Dict) -> Dict:
        """使用PaddleOCR版面分析"""
        try:
            paddle_result = self.structure_engine(image_path)

            for item in paddle_result:
                item_type = item.get('type', '')
                bbox = item.get('bbox', [])
                res = item.get('res', {})
                text = item.get('text', '')

                if item_type == 'text':
                    result["paragraphs"].append(self._parse_text_block(item))
                elif item_type == 'table':
                    result["tables"].append(self._parse_table_block(item))
                elif item_type == 'figure':
                    if self._is_signature(item, text):
                        result["signatures"].append(self._parse_signature(item))
                    elif self._is_seal(item):
                        result["seals"].append(self._parse_seal(item))
                    else:
                        result["images"].append(self._parse_image(item))

                # 添加区域信息
                if bbox:
                    result["regions"].append({
                        "type": item_type,
                        "bbox": bbox,
                        "confidence": res.get('score', 0.0)
                    })

        except Exception as e:
            logger.error(f"PaddleOCR analysis error: {e}")

        return result

    def _parse_text_block(self, item: Dict) -> Dict:
        """解析文本块"""
        bbox = item.get('bbox', [])
        res = item.get('res', {})
        text = item.get('text', '')

        return {
            "type": "paragraph",
            "bbox": bbox,
            "text": text,
            "confidence": res.get('score', 0.0),
            "position": self._get_position_info(bbox)
        }

    def _parse_table_block(self, item: Dict) -> Dict:
        """解析表格块"""
        bbox = item.get('bbox', [])
        res = item.get('res', {})

        # 提取表格内容
        html = res.get('html', '')
        rows = self._parse_html_table(html) if html else []

        return {
            "type": "table",
            "bbox": bbox,
            "rows": rows,
            "row_count": len(rows),
            "confidence": res.get('score', 0.0),
            "position": self._get_position_info(bbox)
        }

    def _parse_image(self, item: Dict) -> Dict:
        """解析图片区域"""
        bbox = item.get('bbox', [])

        return {
            "type": "image",
            "bbox": bbox,
            "position": self._get_position_info(bbox)
        }

    def _parse_signature(self, item: Dict) -> Dict:
        """解析签名区域"""
        bbox = item.get('bbox', [])
        text = item.get('text', '')

        return {
            "type": "signature",
            "bbox": bbox,
            "text_hint": text,
            "position": self._get_position_info(bbox),
            "label": self._identify_signature_label(text)
        }

    def _parse_seal(self, item: Dict) -> Dict:
        """解析印章区域"""
        bbox = item.get('bbox', [])

        return {
            "type": "seal",
            "bbox": bbox,
            "position": self._get_position_info(bbox),
            "shape": self._detect_seal_shape(item),
            "color": self._detect_seal_color(item)
        }

    def _is_signature(self, item: Dict, text: str) -> bool:
        """
        判断是否为签名区域

        基于以下特征：
        1. 位置通常在页面底部
        2. 形状通常是横向的矩形
        3. 附近包含签名相关关键词
        """
        bbox = item.get('bbox', [])
        if not bbox:
            return False

        # 计算宽高比
        width = bbox[2][0] - bbox[0][0] if len(bbox) > 2 else 0
        height = bbox[2][1] - bbox[0][1] if len(bbox) > 2 else 0

        if height == 0:
            return False

        aspect_ratio = width / height

        # 签名通常是横向矩形
        if not (1.5 < aspect_ratio < 8):
            return False

        # 检查是否在页面底部区域
        position = self._get_position_info(bbox)
        if position.get("vertical") == "bottom":
            return True

        # 检查文本关键词
        signature_keywords = ["签字", "签名", "签署", "代表", "日期", "年", "月", "日"]
        for keyword in signature_keywords:
            if keyword in text:
                return True

        return False

    def _is_seal(self, item: Dict) -> bool:
        """
        判断是否为印章区域

        印章特征：
        1. 通常是圆形或椭圆形
        2. 颜色通常是红色
        3. 可能包含文字（环形排列）
        """
        bbox = item.get('bbox', [])
        if not bbox:
            return False

        # 检查形状
        shape = self._detect_seal_shape(item)
        if shape in ["circle", "ellipse"]:
            # 进一步检查颜色
            color = self._detect_seal_color(item)
            if color == "red":
                return True

        return False

    def _detect_seal_shape(self, item: Dict) -> str:
        """检测印章形状"""
        bbox = item.get('bbox', [])
        if not bbox or len(bbox) < 4:
            return "unknown"

        width = bbox[2][0] - bbox[0][0]
        height = bbox[2][1] - bbox[0][1]

        if height == 0:
            return "unknown"

        ratio = width / height

        # 圆形的宽高比接近1
        if 0.8 <= ratio <= 1.2:
            return "circle"
        # 椭圆的宽高比在0.5-2之间
        elif 0.5 <= ratio <= 2:
            return "ellipse"
        else:
            return "rectangle"

    def _detect_seal_color(self, item: Dict) -> str:
        """检测印章颜色"""
        # 简化版本：默认返回红色
        # 实际实现需要读取图片像素进行分析
        try:
            if self._has_cv2 and 'img_path' in item:
                img = self.cv2.imread(item['img_path'])
                if img is not None:
                    # 分析中心区域的颜色
                    # 这里简化处理
                    pass
        except Exception:
            pass

        return "red"

    def _identify_signature_label(self, text: str) -> str:
        """识别签名标签类型"""
        signature_mapping = {
            "甲方": "party_a_signature",
            "乙方": "party_b_signature",
            "委托方": "principal_signature",
            "受托方": "agent_signature",
            "法定代表人": "legal_rep_signature",
            "授权代表": "authorized_rep_signature",
            "收款人": "payee_signature",
            "付款人": "payer_signature",
            "经办人": "handler_signature",
            "审核人": "auditor_signature"
        }

        for keyword, label in signature_mapping.items():
            if keyword in text:
                return label

        return "signature"

    def _get_position_info(self, bbox: List) -> Dict:
        """获取边界框的位置信息"""
        if not bbox or len(bbox) < 4:
            return {"vertical": "unknown", "horizontal": "unknown"}

        # 假设页面高度为1000（标准化）
        y_center = (bbox[0][1] + bbox[2][1]) / 2 if len(bbox) > 2 else 0
        x_center = (bbox[0][0] + bbox[2][0]) / 2 if len(bbox) > 2 else 0

        # 垂直位置
        if y_center < 250:
            vertical = "top"
        elif y_center < 500:
            vertical = "middle_top"
        elif y_center < 750:
            vertical = "middle_bottom"
        else:
            vertical = "bottom"

        # 水平位置
        if x_center < 250:
            horizontal = "left"
        elif x_center < 500:
            horizontal = "center"
        else:
            horizontal = "right"

        return {
            "vertical": vertical,
            "horizontal": horizontal
        }

    def _parse_html_table(self, html: str) -> List[List[str]]:
        """从HTML表格解析行数据"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            rows = []

            for tr in soup.find_all('tr'):
                row = []
                for td in tr.find_all(['td', 'th']):
                    row.append(td.get_text(strip=True))
                if row:
                    rows.append(row)

            return rows
        except ImportError:
            logger.warning("BeautifulSoup not available for table parsing")
            return []
        except Exception as e:
            logger.error(f"HTML table parsing error: {e}")
            return []

    def _analyze_by_text(self, text: str, result: Dict) -> Dict:
        """基于文本分析布局"""
        lines = text.split('\n')

        # 检测页眉
        header = self._detect_header(lines)
        if header:
            result["header"] = header

        # 检测页脚
        footer = self._detect_footer(lines)
        if footer:
            result["footer"] = footer

        # 检测签名区域（基于关键词）
        signature_areas = self._detect_signature_areas_by_text(text, lines)
        if signature_areas:
            result["signatures"].extend(signature_areas)

        # 检测印章关键词
        seal_areas = self._detect_seal_areas_by_text(text)
        if seal_areas:
            result["seals"].extend(seal_areas)

        # 检测页面类型
        page_type = self._detect_page_type(text)
        result["page_type"] = page_type

        return result

    def _detect_header(self, lines: List[str]) -> Optional[str]:
        """检测页眉"""
        if not lines:
            return None

        # 页眉通常在第一行或前几行
        first_lines = lines[:3]

        # 检测标题模式
        for line in first_lines:
            if line and len(line) < 50:
                # 可能是标题
                if any(kw in line for kw in ["合同", "协议", "订单", "报价单", "收据", "发票"]):
                    return line

        return first_lines[0] if first_lines else None

    def _detect_footer(self, lines: List[str]) -> Optional[str]:
        """检测页脚"""
        if not lines:
            return None

        # 页脚通常在最后几行
        last_lines = lines[-3:]

        # 检测页码
        for line in last_lines:
            if re.search(r'第\s*\d+\s*页', line) or re.search(r'\d+\s*/\s*\d+', line):
                return line

        return None

    def detect_signature_areas(self, text: str, bbox: List = None) -> List[Dict]:
        """
        基于关键词检测签名区域

        Args:
            text: OCR文本
            bbox: 边界框（可选）

        Returns:
            签名区域列表
        """
        lines = text.split('\n')
        return self._detect_signature_areas_by_text(text, lines)

    def _detect_signature_areas_by_text(self, text: str, lines: List[str]) -> List[Dict]:
        """基于文本检测签名区域"""
        signature_keywords = [
            ("甲方签字", "party_a_signature"),
            ("甲方盖章", "party_a_seal"),
            ("乙方签字", "party_b_signature"),
            ("乙方盖章", "party_b_seal"),
            ("委托方签字", "principal_signature"),
            ("受托方签字", "agent_signature"),
            ("法定代表人签字", "legal_rep_signature"),
            ("授权代表签字", "authorized_rep_signature"),
            ("收款人签字", "payee_signature"),
            ("付款人签字", "payer_signature"),
            ("经办人", "handler_signature"),
            ("审核人", "auditor_signature")
        ]

        areas = []
        for i, line in enumerate(lines):
            for keyword, label in signature_keywords:
                if keyword in line:
                    areas.append({
                        "type": "signature",
                        "label": label,
                        "keyword": keyword,
                        "line": line,
                        "line_number": i,
                        "bbox": None
                    })

        return areas

    def _detect_seal_areas_by_text(self, text: str) -> List[Dict]:
        """基于文本检测印章区域"""
        seal_keywords = [
            ("公章", "official_seal"),
            ("合同章", "contract_seal"),
            ("财务专用章", "finance_seal"),
            ("法人章", "legal_rep_seal"),
            ("发票专用章", "invoice_seal"),
            ("收款单位盖章", "company_seal")
        ]

        areas = []
        for keyword, label in seal_keywords:
            if keyword in text:
                areas.append({
                    "type": "seal",
                    "label": label,
                    "keyword": keyword
                })

        return areas

    def _detect_page_type(self, text: str) -> str:
        """检测页面类型"""
        # 封面特征
        if any(kw in text for kw in ["合同", "协议", "编号"]):
            if len(text) < 500:  # 封面文字通常较少
                return "cover"

        # 签署页特征
        signature_keywords = ["签字", "盖章", "签署", "日期", "双方确认"]
        signature_count = sum(1 for kw in signature_keywords if kw in text)
        if signature_count >= 2:
            return "signature"

        # 附件特征
        if "附件" in text or "Appendix" in text or "附录" in text:
            return "attachment"

        return "content"

    def analyze_multi_page(self, pages: List[Dict]) -> Dict:
        """
        分析多页文档的布局

        Args:
            pages: 页面列表，每页包含image_path和ocr_text

        Returns:
            多页文档布局分析结果
        """
        total_pages = len(pages)

        result = {
            "total_pages": total_pages,
            "page_types": {
                "cover": [],
                "content": [],
                "signature": [],
                "attachment": []
            },
            "signature_pages": [],
            "seal_pages": [],
            "merged_signatures": [],
            "merged_seals": []
        }

        for i, page in enumerate(pages):
            page_num = i + 1
            image_path = page.get("image_path", "")
            ocr_text = page.get("ocr_text", "")

            page_result = self.analyze_page(image_path, ocr_text)
            page_type = page_result.get("page_type", "content")

            result["page_types"][page_type].append(page_num)

            # 收集签名和印章信息
            if page_result.get("signatures"):
                for sig in page_result["signatures"]:
                    sig["page"] = page_num
                    result["merged_signatures"].append(sig)
                    result["signature_pages"].append(page_num)

            if page_result.get("seals"):
                for seal in page_result["seals"]:
                    seal["page"] = page_num
                    result["merged_seals"].append(seal)
                    result["seal_pages"].append(page_num)

        # 去重签名页和印章页
        result["signature_pages"] = list(set(result["signature_pages"]))
        result["seal_pages"] = list(set(result["seal_pages"]))

        return result

    def extract_key_regions(self, layout_result: Dict) -> Dict:
        """
        提取关键区域信息

        Args:
            layout_result: 布局分析结果

        Returns:
            关键区域信息
        """
        return {
            "has_signatures": len(layout_result.get("signatures", [])) > 0,
            "signature_count": len(layout_result.get("signatures", [])),
            "signature_labels": [s.get("label") for s in layout_result.get("signatures", [])],
            "has_seals": len(layout_result.get("seals", [])) > 0,
            "seal_count": len(layout_result.get("seals", [])),
            "seal_labels": [s.get("label") for s in layout_result.get("seals", [])],
            "page_type": layout_result.get("page_type"),
            "has_header": layout_result.get("header") is not None,
            "has_footer": layout_result.get("footer") is not None
        }


# 便捷函数
def analyze_document_layout(image_path: str, ocr_text: str = "") -> Dict:
    """
    分析文档布局

    Args:
        image_path: 图片路径
        ocr_text: OCR识别的文本

    Returns:
        布局分析结果
    """
    analyzer = LayoutAnalyzer()
    return analyzer.analyze_page(image_path, ocr_text)
