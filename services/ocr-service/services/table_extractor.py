"""
表格提取器
从文档中提取表格数据
"""

import logging
from typing import Dict, List, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class TableExtractor:
    """表格提取器"""

    def __init__(self):
        self._init_dependencies()

    def _init_dependencies(self):
        """初始化依赖"""
        self._has_camelot = False
        self._has_tabula = False
        self._has_pdfplumber = False

        try:
            import camelot
            self._camelot = camelot
            self._has_camelot = True
            logger.info("Camelot table extractor initialized")
        except ImportError:
            logger.warning("Camelot not available")

        try:
            import pdfplumber
            self._pdfplumber = pdfplumber
            self._has_pdfplumber = True
        except ImportError:
            pass

    def extract_from_pdf(self, pdf_path: str, pages: str = "all") -> List[Dict]:
        """
        从PDF提取表格
        pages: "all", "1-3", "1,3,5" 等
        """
        tables = []

        if self._has_camelot:
            tables = self._extract_with_camelot(pdf_path, pages)
        elif self._has_pdfplumber:
            tables = self._extract_with_pdfplumber(pdf_path, pages)

        return tables

    def _extract_with_camelot(self, pdf_path: str, pages: str) -> List[Dict]:
        """使用Camelot提取表格"""
        tables = []

        try:
            # 提取表格
            table_list = self._camelot.read_pdf(
                pdf_path,
                pages=pages,
                flavor="lattice",  # lattice或stream
                suppress_stdout=True
            )

            for i, table in enumerate(table_list):
                tables.append({
                    "index": i,
                    "page": table.page,
                    "headers": table.df.iloc[0].tolist() if not table.df.empty else [],
                    "rows": table.df.iloc[1:].values.tolist() if len(table.df) > 1 else [],
                    "row_count": len(table.df),
                    "col_count": len(table.df.columns) if not table.df.empty else 0,
                    "accuracy": table.accuracy,
                    "whitespace": table.whitespace,
                    "order": table.order
                })

        except Exception as e:
            logger.error(f"Camelot extraction error: {e}")

        return tables

    def _extract_with_pdfplumber(self, pdf_path: str, pages: str) -> List[Dict]:
        """使用pdfplumber提取表格"""
        tables = []

        try:
            with self._pdfplumber.open(pdf_path) as pdf:
                target_pages = self._parse_pages_param(pages, len(pdf.pages))

                for page_num in target_pages:
                    page = pdf.pages[page_num - 1]
                    page_tables = page.extract_tables()

                    for i, table in enumerate(page_tables):
                        if table:
                            tables.append({
                                "index": len(tables),
                                "page": page_num,
                                "headers": table[0] if table else [],
                                "rows": table[1:] if len(table) > 1 else [],
                                "row_count": len(table),
                                "col_count": len(table[0]) if table else 0,
                            })

        except Exception as e:
            logger.error(f"pdfplumber extraction error: {e}")

        return tables

    def extract_from_image(self, image: np.ndarray) -> List[Dict]:
        """从图片提取表格"""
        tables = []

        # 图片表格提取需要OCR引擎支持
        # 这里返回空，实际使用时由OCR引擎的table recognition处理

        return tables

    def extract_from_html(self, html: str) -> List[Dict]:
        """从HTML表格提取数据"""
        tables = []

        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, 'html.parser')
            table_elements = soup.find_all('table')

            for i, table_elem in enumerate(table_elements):
                headers = []
                rows = []

                # 提取表头
                thead = table_elem.find('thead')
                if thead:
                    for th in thead.find_all('th'):
                        headers.append(th.get_text(strip=True))

                # 如果没有thead，尝试第一行tr
                if not headers:
                    first_row = table_elem.find('tr')
                    if first_row:
                        for th in first_row.find_all(['th', 'td']):
                            headers.append(th.get_text(strip=True))

                # 提取数据行
                tbody = table_elem.find('tbody') or table_elem
                for tr in tbody.find_all('tr')[1 if headers else 0:]:
                    row = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                    if row:
                        rows.append(row)

                tables.append({
                    "index": i,
                    "headers": headers,
                    "rows": rows,
                    "row_count": len(rows),
                    "col_count": len(headers)
                })

        except ImportError:
            logger.warning("BeautifulSoup not available for HTML table extraction")
        except Exception as e:
            logger.error(f"HTML table extraction error: {e}")

        return tables

    def _parse_pages_param(self, pages: str, total_pages: int) -> List[int]:
        """解析页码参数"""
        if pages == "all":
            return list(range(1, total_pages + 1))

        result = []
        for part in pages.split(','):
            part = part.strip()
            if '-' in part:
                start, end = part.split('-')
                result.extend(range(int(start), int(end) + 1))
            else:
                result.append(int(part))

        return [p for p in result if 1 <= p <= total_pages]

    def normalize_table(self, table: Dict) -> Dict:
        """规范化表格数据"""
        return {
            "index": table.get("index", 0),
            "page": table.get("page", 1),
            "headers": table.get("headers", []),
            "rows": table.get("rows", []),
            "row_count": table.get("row_count", 0),
            "col_count": table.get("col_count", 0),
            "confidence": table.get("accuracy", table.get("confidence", 0.0))
        }

    def merge_cells_info(self, table: Dict) -> List[Dict]:
        """处理合并单元格信息"""
        # 这里可以实现合并单元格的检测逻辑
        # 简化版本返回空列表
        return []

    def validate_table(self, table: Dict) -> Tuple[bool, List[str]]:
        """验证表格数据的完整性"""
        issues = []

        if not table.get("headers"):
            issues.append("表格缺少表头")

        if table.get("row_count", 0) == 0:
            issues.append("表格没有数据行")

        # 检查列数一致性
        col_count = table.get("col_count", 0)
        if col_count > 0:
            for i, row in enumerate(table.get("rows", [])):
                if len(row) != col_count:
                    issues.append(f"第{i+1}行列数不一致: 期望{col_count}, 实际{len(row)}")

        return len(issues) == 0, issues
