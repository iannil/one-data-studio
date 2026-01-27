#!/usr/bin/env python3
"""
测试文档生成器
生成用于测试OCR服务的模拟文档
"""

import os
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("Warning: reportlab not installed. Install with: pip install reportlab")


@dataclass
class CompanyInfo:
    """公司信息"""
    name: str
    address: str
    tax_id: str
    phone: str
    bank: str
    bank_account: str


class DocumentGenerator:
    """测试文档生成器"""

    def __init__(self, output_dir: str = "./tests/documents"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 字体配置
        self.fonts_registered = False
        if REPORTLAB_AVAILABLE:
            self._register_fonts()

    def _register_fonts(self):
        """注册中文字体"""
        if self.fonts_registered:
            return

        # 尝试注册系统中文字体
        font_paths = [
            "/System/Library/Fonts/PingFang.ttc",  # macOS
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
            "C:/Windows/Fonts/simhei.ttf",  # Windows
        ]

        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont("Chinese", font_path))
                    self.fonts_registered = True
                    break
                except:
                    continue

    def generate_invoice(
        self,
        output_name: str = "sample_invoice.pdf",
        seller: Optional[CompanyInfo] = None,
        amount: Optional[float] = None
    ) -> str:
        """生成发票测试文档"""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab is required for PDF generation")

        output_path = self.output_dir / output_name

        # 创建PDF
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        styles = getSampleStyleSheet()
        if self.fonts_registered:
            styles.add(ParagraphStyle(
                name='Chinese',
                fontName='Chinese',
                fontSize=12,
                leading=16
            ))

        # 内容
        story = []

        # 标题
        if self.fonts_registered:
            title = Paragraph("增值税普通发票", ParagraphStyle(
                'ChineseTitle',
                fontName='Chinese',
                fontSize=24,
                alignment=TA_CENTER,
                spaceAfter=1*cm
            ))
        else:
            title = Paragraph("VAT INVOICE", ParagraphStyle(
                'Title',
                fontSize=24,
                alignment=TA_CENTER,
                spaceAfter=1*cm
            ))
        story.append(title)

        # 发票信息
        invoice_no = f"{random.randint(10000000, 99999999)}"
        invoice_date = (datetime.now() - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d")

        if amount is None:
            amount = round(random.uniform(100, 100000), 2)

        info_data = [
            ["发票号码:", invoice_no],
            ["开票日期:", invoice_date],
        ]

        info_table = Table(info_data, colWidths=[5*cm, 5*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Chinese' if self.fonts_registered else 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(info_table)
        story.append(Spacer(1*cm, 1*cm))

        # 购买方/销售方信息
        seller = seller or CompanyInfo(
            name="示例供应商有限公司",
            address="北京市朝阳区示例路123号",
            tax_id="91110000123456789X",
            phone="010-12345678",
            bank="中国银行北京分行",
            bank_account="123456789012345678"
        )

        buyer = CompanyInfo(
            name="示例采购有限公司",
            address="上海市浦东新区测试路456号",
            tax_id="91310000987654321Y",
            phone="021-87654321",
            bank="工商银行上海分行",
            bank_account="987654321098765432"
        )

        party_data = [
            ["购买方信息", ""],
            ["名称:", buyer.name],
            ["纳税人识别号:", buyer.tax_id],
            ["地址、电话:", f"{buyer.address} {buyer.phone}"],
            ["", ""],
            ["销售方信息", ""],
            ["名称:", seller.name],
            ["纳税人识别号:", seller.tax_id],
            ["地址、电话:", f"{seller.address} {seller.phone}"],
        ]

        party_table = Table(party_data, colWidths=[4*cm, 8*cm])
        party_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Chinese' if self.fonts_registered else 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(party_table)
        story.append(Spacer(1*cm, 1*cm))

        # 货物明细
        items = [
            ["货物或应税劳务、服务名称", "规格型号", "单位", "数量", "单价", "金额", "税率", "税额"]
        ]

        item_count = random.randint(1, 5)
        total_amount = 0
        total_tax = 0

        for i in range(item_count):
            item_name = f"商品{i+1}"
            quantity = random.randint(1, 100)
            unit_price = round(random.uniform(10, 1000), 2)
            item_amount = round(quantity * unit_price, 2)
            tax_rate = 0.13
            item_tax = round(item_amount * tax_rate, 2)

            total_amount += item_amount
            total_tax += item_tax

            items.append([
                item_name, "-", "件", str(quantity),
                f"{unit_price:.2f}", f"{item_amount:.2f}",
                "13%", f"{item_tax:.2f}"
            ])

        # 合计行
        items.append(["", "", "", "", "", f"{total_amount:.2f}", "", f"{total_tax:.2f}"])

        # 价税合计
        total = round(total_amount + total_tax, 2)
        items.append(["价税合计（大写）", self._amount_to_chinese(total), "", "", "", "", "", ""])
        items.append(["价税合计（小写）", f"¥{total:.2f}", "", "", "", "", "", ""])

        items_table = Table(items, colWidths=[4*cm, 1.5*cm, 1*cm, 1*cm, 1.5*cm, 1.5*cm, 1*cm, 1.5*cm])
        items_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Chinese' if self.fonts_registered else 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(items_table)

        # 收款人信息
        story.append(Spacer(1.5*cm, 1.5*cm))
        footer_data = [
            ["收款人: " + "张三", "复核: " + "李四", "开票人: " + "王五", "销售方:(盖章)"]
        ]
        footer_table = Table(footer_data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
        footer_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Chinese' if self.fonts_registered else 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        story.append(footer_table)

        # 生成PDF
        doc.build(story)
        return str(output_path)

    def generate_contract(
        self,
        output_name: str = "sample_contract.pdf",
        amount: Optional[float] = None
    ) -> str:
        """生成合同测试文档"""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab is required for PDF generation")

        output_path = self.output_dir / output_name

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        styles = getSampleStyleSheet()

        story = []

        # 标题
        title = Paragraph("技术服务合同", ParagraphStyle(
            'Title',
            fontSize=20,
            alignment=TA_CENTER,
            spaceAfter=1*cm
        ))
        story.append(title)

        # 合同编号和日期
        contract_no = f"HT-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        contract_date = datetime.now().strftime("%Y年%m月%d日")

        info_style = ParagraphStyle(
            'Info',
            fontSize=10,
            alignment=TA_RIGHT
        )

        story.append(Paragraph(f"合同编号: {contract_no}", info_style))
        story.append(Paragraph(f"签订日期: {contract_date}", info_style))
        story.append(Spacer(1*cm, 1*cm))

        # 甲乙方信息
        party_a = "甲方: 北京科技有限公司"
        party_b = "乙方: 上海技术服务公司"

        story.append(Paragraph(party_a, styles['Normal']))
        story.append(Paragraph(party_b, styles['Normal']))
        story.append(Spacer(1*cm, 1*cm))

        # 合同内容
        content = """
        <b>第一条 服务内容</b>
        乙方同意向甲方提供技术服务，具体内容包括系统开发、技术咨询、运维支持等。

        <b>第二条 服务期限</b>
        本合同有效期为一年，自签订之日起计算。

        <b>第三条 服务费用</b>
        """

        story.append(Paragraph(content, styles['Normal']))

        if amount is None:
            amount = round(random.uniform(50000, 500000), 2)

        amount_cn = self._amount_to_chinese(amount)

        fee_table = Table([
            ["服务费用总金额:", f"¥{amount:.2f} 元 ({amount_cn})"],
            ["付款方式:", "分期付款"],
            ["付款计划:", ""],
            ["首期付款:", "签订合同后7个工作日内支付50%"],
            ["二期付款:", "服务完成验收后支付50%"],
        ], colWidths=[5*cm, 10*cm])

        fee_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Chinese' if self.fonts_registered else 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(fee_table)

        story.append(Spacer(1*cm, 1*cm))

        # 签字区域
        story.append(Spacer(2*cm, 2*cm))

        sign_table = Table([
            ["甲方（盖章）: ", "乙方（盖章）: "],
            ["法定代表人: ", "法定代表人: "],
            ["签字日期: ", "签字日期: "],
        ], colWidths=[8*cm, 8*cm])

        sign_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Chinese' if self.fonts_registered else 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(sign_table)

        doc.build(story)
        return str(output_path)

    def _amount_to_chinese(self, amount: float) -> str:
        """金额转中文大写"""
        chinese_nums = ['零', '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖']
        chinese_units = ['', '拾', '佰', '仟', '万', '拾', '佰', '仟', '亿']

        # 简化版本，实际使用需要更完整的实现
        integer_part = int(amount)
        decimal_part = int(round((amount - integer_part) * 100))

        result = "人民币"

        if integer_part == 0:
            result += "零"
        else:
            # 简化的整数转换
            result += f"{integer_part}元"

        if decimal_part > 0:
            result += f"{decimal_part}角"

        return result + "整"

    def generate_all_samples(self):
        """生成所有示例文档"""
        print("生成测试文档...")

        try:
            invoice_path = self.generate_invoice()
            print(f"  ✅ {invoice_path}")

            contract_path = self.generate_contract()
            print(f"  ✅ {contract_path}")

            # 生成多个变体
            for i in range(3):
                self.generate_invoice(f"sample_invoice_{i+1}.pdf", amount=random.uniform(1000, 50000))

            for i in range(2):
                self.generate_contract(f"sample_contract_{i+1}.pdf", amount=random.uniform(50000, 200000))

            print(f"\n✅ 所有测试文档已生成到: {self.output_dir}")

        except ImportError as e:
            print(f"❌ 生成失败: {e}")
            print("请安装 reportlab: pip install reportlab")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="OCR测试文档生成器")
    parser.add_argument("--output", "-o", default="./tests/documents", help="输出目录")
    parser.add_argument("--type", "-t", choices=["invoice", "contract", "all"], default="all",
                       help="文档类型")

    args = parser.parse_args()

    generator = DocumentGenerator(args.output)

    if args.type == "invoice":
        generator.generate_invoice()
    elif args.type == "contract":
        generator.generate_contract()
    else:
        generator.generate_all_samples()


if __name__ == "__main__":
    main()
