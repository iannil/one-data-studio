"""
预置数据初始化脚本
用于初始化内容分类、预置预测模板等数据
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, '/app')

from models import SessionLocal
from models.content import ContentCategory, ContentTag
from models.api_call_log import ApiEndpoint, generate_api_endpoint_id


def init_content_categories():
    """初始化内容分类"""
    db = SessionLocal()
    try:
        # 检查是否已初始化
        existing = db.query(ContentCategory).count()
        if existing > 0:
            print(f"内容分类已存在，跳过初始化")
            return

        categories = [
            {
                "name": "产品更新",
                "slug": "product-updates",
                "description": "产品功能更新、版本发布等相关内容",
                "icon": "ProductOutlined",
                "level": 0,
                "sort_order": 1,
            },
            {
                "name": "使用教程",
                "slug": "tutorials",
                "description": "产品使用教程、操作指南等",
                "icon": "BookOutlined",
                "level": 0,
                "sort_order": 2,
            },
            {
                "name": "常见问题",
                "slug": "faq",
                "description": "用户常见问题解答",
                "icon": "QuestionCircleOutlined",
                "level": 0,
                "sort_order": 3,
            },
            {
                "name": "技术文档",
                "slug": "technical-docs",
                "description": "技术文档、API参考等",
                "icon": "CodeOutlined",
                "level": 0,
                "sort_order": 4,
            },
            {
                "name": "公告通知",
                "slug": "announcements",
                "description": "系统公告、通知等",
                "icon": "NotificationOutlined",
                "level": 0,
                "sort_order": 5,
            },
        ]

        for cat_data in categories:
            from models.content import generate_category_id
            category = ContentCategory(
                category_id=generate_category_id(),
                **cat_data,
            )
            db.add(category)

        db.commit()
        print(f"已初始化 {len(categories)} 个内容分类")

    except Exception as e:
        print(f"初始化内容分类失败: {e}")
        db.rollback()
    finally:
        db.close()


def init_content_tags():
    """初始化内容标签"""
    db = SessionLocal()
    try:
        # 检查是否已初始化
        existing = db.query(ContentTag).count()
        if existing > 0:
            print(f"内容标签已存在，跳过初始化")
            return

        tags = [
            {"name": "新手指南", "slug": "beginner-guide", "color": "#52c41a"},
            {"name": "进阶教程", "slug": "advanced-tutorial", "color": "#1890ff"},
            {"name": "性能优化", "slug": "performance", "color": "#fa8c16"},
            {"name": "安全", "slug": "security", "color": "#f5222d"},
            {"name": "部署", "slug": "deployment", "color": "#722ed1"},
            {"name": "故障排查", "slug": "troubleshooting", "color": "#eb2f96"},
            {"name": "最佳实践", "slug": "best-practices", "color": "#13c2c2"},
            {"name": "视频教程", "slug": "video", "color": "#faad14"},
        ]

        for tag_data in tags:
            from models.content import generate_tag_id
            tag = ContentTag(
                tag_id=generate_tag_id(),
                **tag_data,
            )
            db.add(tag)

        db.commit()
        print(f"已初始化 {len(tags)} 个内容标签")

    except Exception as e:
        print(f"初始化内容标签失败: {e}")
        db.rollback()
    finally:
        db.close()


def init_api_endpoints():
    """初始化API端点（扫描当前应用）"""
    try:
        # 导入当前应用
        from app import app
        from sqlalchemy import or_

        db = SessionLocal()
        try:
            # 扫描所有路由
            endpoints = []
            for rule in app.url_map.iter_rules():
                # 跳过静态文件和内部路由
                if rule.rule.startswith('/static') or rule.endpoint.startswith('static'):
                    continue
                if rule.endpoint == 'root':
                    continue

                methods = [m for m in rule.methods if m not in ['HEAD', 'OPTIONS']]
                if not methods:
                    continue

                for method in methods:
                    endpoints.append({
                        "path": rule.rule,
                        "method": method,
                        "service": "admin-api",
                        "endpoint_name": rule.endpoint,
                        "description": f"{method} {rule.rule}",
                        "requires_auth": True,
                    })

            # 注册端点
            registered = 0
            for ep in endpoints:
                existing = db.query(ApiEndpoint).filter(
                    ApiEndpoint.path == ep["path"],
                    ApiEndpoint.method == ep["method"]
                ).first()

                if not existing:
                    api_ep = ApiEndpoint(
                        endpoint_id=generate_api_endpoint_id(),
                        **ep,
                    )
                    db.add(api_ep)
                    registered += 1

            db.commit()
            print(f"已注册 {registered} 个API端点")

        except Exception as e:
            print(f"初始化API端点失败: {e}")
            db.rollback()
        finally:
            db.close()

    except ImportError:
        print("无法导入应用，跳过API端点初始化")


def main():
    """主函数"""
    print("=" * 50)
    print("开始初始化预置数据...")
    print("=" * 50)

    init_content_categories()
    init_content_tags()
    init_api_endpoints()

    print("=" * 50)
    print("预置数据初始化完成!")
    print("=" * 50)


if __name__ == "__main__":
    main()
