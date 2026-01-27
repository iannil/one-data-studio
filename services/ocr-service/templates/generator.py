#!/usr/bin/env python3
"""
文档模板生成器
用于快速创建新的文档类型模板
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class FieldConfig:
    """字段配置"""
    name: str
    key: str
    required: bool = False
    validation: Optional[Dict] = None


@dataclass
class TableConfig:
    """表格配置"""
    name: str
    key: str
    required: bool = True
    header_keywords: List[str] = None
    fields: List[Dict] = None

    def __post_init__(self):
        if self.header_keywords is None:
            self.header_keywords = []
        if self.fields is None:
            self.fields = []


@dataclass
class ValidationRule:
    """校验规则"""
    rule: str
    description: str
    fields: List[str]
    validation: str


class TemplateGenerator:
    """模板生成器"""

    def __init__(self):
        self.template_types = [
            "invoice", "contract", "purchase_order", "delivery_note",
            "quotation", "receipt", "report", "table", "general"
        ]

    def generate_template(
        self,
        name: str,
        template_type: str,
        category: str,
        description: str = "",
        fields: List[FieldConfig] = None,
        tables: List[TableConfig] = None,
        validation_rules: List[ValidationRule] = None,
        supported_formats: List[str] = None,
        has_signature_detection: bool = False,
        has_seal_detection: bool = False
    ) -> Dict:
        """
        生成文档模板

        Args:
            name: 模板名称
            template_type: 模板类型
            category: 分类
            description: 描述
            fields: 字段列表
            tables: 表格列表
            validation_rules: 校验规则
            supported_formats: 支持的文件格式
            has_signature_detection: 是否启用签名检测
            has_seal_detection: 是否启用印章检测

        Returns:
            模板配置字典
        """
        if fields is None:
            fields = []
        if tables is None:
            tables = []
        if validation_rules is None:
            validation_rules = []
        if supported_formats is None:
            supported_formats = ["pdf", "image"]

        template = {
            "name": name,
            "description": description,
            "type": template_type,
            "category": category,
            "supported_formats": supported_formats,
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "fields": [
                {
                    "name": f.name,
                    "key": f.key,
                    "required": f.required,
                    "validation": f.validation or {}
                }
                for f in fields
            ],
            "tables": [
                {
                    "name": t.name,
                    "key": t.key,
                    "required": t.required,
                    "header_keywords": t.header_keywords,
                    "fields": t.fields or []
                }
                for t in tables
            ],
            "cross_field_validation": [
                {
                    "rule": r.rule,
                    "description": r.description,
                    "fields": r.fields,
                    "validation": r.validation
                }
                for r in validation_rules
            ]
        }

        # 添加布局检测配置
        if has_signature_detection or has_seal_detection:
            template["layout_detection"] = {}

            if has_signature_detection:
                template["layout_detection"]["signature_regions"] = [
                    {"keywords": ["签字", "签署", "签名"], "label": "signature"}
                ]

            if has_seal_detection:
                template["layout_detection"]["seal_regions"] = [
                    {"keywords": ["盖章", "印章", "公章"], "label": "seal"}
                ]

        return template

    def save_template(self, template: Dict, output_path: str):
        """保存模板到文件"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, ensure_ascii=False, indent=2)
        print(f"✅ 模板已保存到: {output_path}")

    def load_template(self, template_path: str) -> Dict:
        """从文件加载模板"""
        with open(template_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def validate_template(self, template: Dict) -> List[str]:
        """验证模板配置"""
        errors = []

        required_fields = ["name", "type", "category"]
        for field in required_fields:
            if field not in template:
                errors.append(f"缺少必填字段: {field}")

        if template.get("type") not in self.template_types:
            errors.append(f"无效的模板类型: {template.get('type')}")

        return errors

    def create_from_interactive(self) -> Dict:
        """交互式创建模板"""
        print("=" * 50)
        print("OCR文档模板生成器 - 交互模式")
        print("=" * 50)

        name = input("模板名称: ")
        description = input("模板描述 (可选): ")

        print("\n选择模板类型:")
        for i, t in enumerate(self.template_types, 1):
            print(f"  {i}. {t}")

        type_choice = input("选择类型编号 (默认: general): ") or "9"
        template_type = self.template_types[int(type_choice) - 1]

        category = input("分类 (如: financial, legal, business): ") or "general"

        print("\n--- 添加字段 ---")
        fields = []
        while True:
            field_name = input("字段名称 (留空结束): ")
            if not field_name:
                break

            field_key = input("字段键名 (如: total_amount): ")
            required = input("是否必填? (y/n): ").lower() == 'y'

            fields.append(FieldConfig(
                name=field_name,
                key=field_key,
                required=required
            ))

        print("\n--- 添加表格 ---")
        tables = []
        while True:
            table_name = input("表格名称 (留空结束): ")
            if not table_name:
                break

            table_key = input("表格键名 (如: items): ")
            tables.append(TableConfig(
                name=table_name,
                key=table_key,
                required=True
            ))

        return self.generate_template(
            name=name,
            description=description,
            template_type=template_type,
            category=category,
            fields=fields,
            tables=tables
        )


# 预设模板配置
PRESET_TEMPLATES = {
    "salary_certificate": {
        "name": "工资收入证明模板",
        "description": "用于提取工资收入证明的关键信息",
        "type": "general",
        "category": "financial",
        "fields": [
            {"name": "姓名", "key": "name", "required": True},
            {"name": "身份证号", "key": "id_number", "required": True},
            {"name": "单位名称", "key": "company_name", "required": True},
            {"name": "职位", "key": "position", "required": False},
            {"name": "入职时间", "key": "hire_date", "required": False},
            {"name": "月收入", "key": "monthly_income", "required": True},
            {"name": "年收入", "key": "annual_income", "required": False},
            {"name": "证明日期", "key": "certificate_date", "required": True},
        ]
    },
    "bank_statement": {
        "name": "银行流水模板",
        "description": "用于提取银行流水的关键信息",
        "type": "table",
        "category": "financial",
        "fields": [
            {"name": "账户名称", "key": "account_name", "required": True},
            {"name": "账号", "key": "account_number", "required": True},
            {"name": "开户行", "key": "bank_name", "required": True},
            {"name": "统计周期", "key": "period", "required": False},
            {"name": "期初余额", "key": "opening_balance", "required": False},
            {"name": "期末余额", "key": "closing_balance", "required": False},
        ],
        "tables": [
            {
                "name": "交易明细",
                "key": "transactions",
                "required": True,
                "header_keywords": ["日期", "摘要", "收入", "支出", "余额"],
                "fields": [
                    {"name": "交易日期", "key": "date"},
                    {"name": "交易摘要", "key": "description"},
                    {"name": "收入金额", "key": "income"},
                    {"name": "支出金额", "key": "expense"},
                    {"name": "余额", "key": "balance"},
                ]
            }
        ]
    },
    "id_card": {
        "name": "身份证模板",
        "description": "用于提取身份证信息",
        "type": "general",
        "category": "identity",
        "fields": [
            {"name": "姓名", "key": "name", "required": True},
            {"name": "性别", "key": "gender", "required": False},
            {"name": "民族", "key": "ethnicity", "required": False},
            {"name": "出生日期", "key": "birth_date", "required": False},
            {"name": "住址", "key": "address", "required": False},
            {"name": "身份证号", "key": "id_number", "required": True},
        ]
    },
    "business_license": {
        "name": "营业执照模板",
        "description": "用于提取营业执照信息",
        "type": "general",
        "category": "business",
        "fields": [
            {"name": "统一社会信用代码", "key": "credit_code", "required": True},
            {"name": "名称", "key": "company_name", "required": True},
            {"name": "类型", "key": "company_type", "required": False},
            {"name": "法定代表人", "key": "legal_rep", "required": True},
            {"name": "注册资本", "key": "registered_capital", "required": False},
            {"name": "成立日期", "key": "establish_date", "required": False},
            {"name": "营业期限", "key": "business_term", "required": False},
            {"name": "经营范围", "key": "business_scope", "required": False},
        ],
        "layout_detection": {
            "seal_regions": [
                {"keywords": ["公章", "电子公章"], "label": "official_seal"}
            ]
        }
    }
}


def create_preset_templates():
    """创建预设模板"""
    gen = TemplateGenerator()
    output_dir = Path(__file__).parent.parent / "templates"

    for key, config in PRESET_TEMPLATES.items():
        template = gen.generate_template(
            name=config["name"],
            description=config["description"],
            template_type=config["type"],
            category=config["category"],
            fields=[FieldConfig(**f) for f in config.get("fields", [])],
            tables=[TableConfig(**t) for t in config.get("tables", [])],
            has_signature_detection="signature_regions" in config.get("layout_detection", {}),
            has_seal_detection="seal_regions" in config.get("layout_detection", {})
        )

        output_path = output_dir / f"{key}.json"
        gen.save_template(template, str(output_path))


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="OCR文档模板生成器")
    parser.add_argument("command", nargs="?", choices=["interactive", "preset", "validate"],
                       help="命令类型", default="interactive")
    parser.add_argument("--input", "-i", help="输入模板文件路径")
    parser.add_argument("--output", "-o", help="输出模板文件路径")

    args = parser.parse_args()

    gen = TemplateGenerator()

    if args.command == "interactive":
        template = gen.create_from_interactive()
        output_path = args.output or f"{template['type']}_custom.json"
        gen.save_template(template, output_path)

    elif args.command == "preset":
        print("创建预设模板...")
        create_preset_templates()
        print("✅ 预设模板创建完成")

    elif args.command == "validate":
        if not args.input:
            print("❌ 请指定输入模板文件")
            sys.exit(1)

        template = gen.load_template(args.input)
        errors = gen.validate_template(template)

        if errors:
            print("❌ 模板验证失败:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
        else:
            print("✅ 模板验证通过")


if __name__ == "__main__":
    main()
