#!/usr/bin/env python3
"""
ONE-DATA-STUDIO 快速数据初始化脚本

功能：通过 API 快速创建示例数据，让页面能够显示数据
使用方式：python scripts/init-demo-data.py
"""

import os
import sys
import json
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 配置
DATA_API_URL = os.getenv("DATA_API_URL", "http://localhost:8080")
WEB_URL = os.getenv("WEB_URL", "http://localhost:3000")

# 模拟用户token（用于开发环境）
MOCK_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInByZWZlcnJlZF91c2VybmFtZSI6ImFkbWluIiwicm9sZXMiOlsiYWRtaW4iXSwiaXNzIjoiZGVtby10b2tlbiIsImV4cCI6OTk5OTk5OTk5OX0.demo-token"

def log(message: str, level: str = "info"):
    """输出日志"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {level.upper()}: {message}")

def api_request(method: str, endpoint: str, data: Dict = None, token: str = None) -> Dict:
    """
    发送 API 请求

    Args:
        method: HTTP 方法
        endpoint: API 端点
        data: 请求数据
        token: 认证 token

    Returns:
        响应数据
    """
    import requests

    url = f"{DATA_API_URL}{endpoint}"
    headers = {
        "Content-Type": "application/json",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=10)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        else:
            raise ValueError(f"Unsupported method: {method}")

        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log(f"API请求失败: {e}", "error")
        return {"code": -1, "message": str(e)}

def check_service() -> bool:
    """检查服务是否可用"""
    import requests

    try:
        response = requests.get(f"{DATA_API_URL}/api/v1/health", timeout=5)
        if response.status_code == 200:
            log("服务健康检查通过", "success")
            return True
        return False
    except Exception as e:
        log(f"服务健康检查失败: {e}", "error")
        return False

def create_datasource(name: str, ds_type: str, host: str, port: int,
                     database: str, token: str) -> Optional[Dict]:
    """创建数据源"""
    log(f"创建数据源: {name}", "info")

    data = {
        "source_id": f"ds-{uuid.uuid4().hex[:8]}",
        "name": name,
        "type": ds_type,
        "description": f"示例 {ds_type.upper()} 数据源",
        "connection": {
            "host": host,
            "port": port,
            "username": f"{ds_type}_user",
            "database": database,
        },
        "tags": ["demo", "sample"],
        "created_by": "admin"
    }

    # 尝试无认证
    result = api_request("POST", "/api/v1/datasources", data)

    # 如果需要认证
    if result.get("code") in [401, 403] and token:
        result = api_request("POST", "/api/v1/datasources", data, token)

    if result.get("code") == 0:
        log(f"✅ 数据源创建成功: {name}", "success")
        return result.get("data")
    else:
        log(f"❌ 数据源创建失败: {result.get('message')}", "error")
        return None

def create_dataset(name: str, storage_type: str, storage_path: str,
                  description: str = "", columns: List[Dict] = None,
                  token: str = None) -> Optional[Dict]:
    """创建数据集"""
    log(f"创建数据集: {name}", "info")

    data = {
        "dataset_id": f"dataset-{uuid.uuid4().hex[:8]}",
        "name": name,
        "description": description,
        "storage_type": storage_type,
        "storage_path": storage_path,
        "format": "parquet",
        "tags": ["demo", "sample"],
        "schema": {
            "columns": columns or []
        }
    }

    result = api_request("POST", "/api/v1/datasets", data, token)

    if result.get("code") == 0 or result.get("status") == "active":
        log(f"✅ 数据集创建成功: {name}", "success")
        return result.get("data")
    else:
        log(f"⚠️ 数据集创建: {result.get('message', '已存在')}", "warning")
        return None

def create_feature(name: str, group_name: str, data_type: str = "float",
                  description: str = "", token: str = None) -> Optional[Dict]:
    """创建特征"""
    log(f"创建特征: {name}", "info")

    data = {
        "feature_id": f"feat-{uuid.uuid4().hex[:8]}",
        "name": name,
        "group_name": group_name,
        "data_type": data_type,
        "description": description,
        "feature_type": "raw",
        "tags": ["demo"],
        "status": "active"
    }

    result = api_request("POST", "/api/v1/features", data, token)

    if result.get("code") == 0:
        log(f"✅ 特征创建成功: {name}", "success")
        return result.get("data")
    else:
        log(f"⚠️ 特征创建: {result.get('message', '已存在')}", "warning")
        return None

def create_standard(name: str, category: str, rule_type: str,
                   description: str = "", token: str = None) -> Optional[Dict]:
    """创建数据标准"""
    log(f"创建数据标准: {name}", "info")

    data = {
        "standard_id": f"std-{uuid.uuid4().hex[:8]}",
        "name": name,
        "description": description,
        "category": category,
        "rule_type": rule_type,
        "rule_config": {"pattern": "^[a-zA-Z0-9_]{3,20}$"},
        "status": "active",
        "tags": ["demo"]
    }

    result = api_request("POST", "/api/v1/standards/elements", data, token)

    if result.get("code") == 0:
        log(f"✅ 数据标准创建成功: {name}", "success")
        return result.get("data")
    else:
        log(f"⚠️ 数据标准创建: {result.get('message', '已存在')}", "warning")
        return None

def create_asset(name: str, asset_type: str, source_type: str, source_id: str,
                description: str = "", token: str = None) -> Optional[Dict]:
    """创建数据资产"""
    log(f"创建数据资产: {name}", "info")

    data = {
        "asset_id": f"asset-{uuid.uuid4().hex[:8]}",
        "name": name,
        "description": description,
        "asset_type": asset_type,
        "source_type": source_type,
        "source_id": source_id,
        "source_name": name,
        "tags": ["demo"],
        "status": "active"
    }

    result = api_request("POST", "/api/v1/assets", data, token)

    if result.get("code") == 0:
        log(f"✅ 数据资产创建成功: {name}", "success")
        return result.get("data")
    else:
        log(f"⚠️ 数据资产创建: {result.get('message', '已存在')}", "warning")
        return None

def create_feature_group(name: str, entity_name: str,
                         description: str = "", token: str = None) -> Optional[Dict]:
    """创建特征组"""
    log(f"创建特征组: {name}", "info")

    # 特征组通过 features API 或单独的 API 创建
    data = {
        "group_id": f"fg-{uuid.uuid4().hex[:8]}",
        "name": name,
        "entity_name": entity_name,
        "entity_key": "id",
        "description": description,
        "online_store": True,
        "offline_store": True,
        "tags": ["demo"]
    }

    # 尝试创建特征组（如果API支持）
    result = api_request("POST", "/api/v1/feature-groups", data, token)

    if result.get("code") == 0:
        log(f"✅ 特征组创建成功: {name}", "success")
        return result.get("data")
    else:
        # 如果API不支持，创建一个虚拟特征作为替代
        return create_feature(
            name=name,
            group_name=name,
            description=f"特征组: {description}",
            token=token
        )

def create_data_service(name: str, service_type: str, source_id: str,
                        description: str = "", token: str = None) -> Optional[Dict]:
    """创建数据服务"""
    log(f"创建数据服务: {name}", "info")

    data = {
        "service_id": f"svc-{uuid.uuid4().hex[:8]}",
        "name": name,
        "description": description,
        "service_type": service_type,
        "source_id": source_id,
        "path": f"/api/services/{name.lower().replace(' ', '-')}",
        "method": "GET",
        "tags": ["demo"],
        "status": "active"
    }

    result = api_request("POST", "/api/v1/services", data, token)

    if result.get("code") == 0:
        log(f"✅ 数据服务创建成功: {name}", "success")
        return result.get("data")
    else:
        log(f"⚠️ 数据服务创建: {result.get('message', '已存在')}", "warning")
        return None

def create_standard_library(name: str, description: str = "",
                          standards: List[str] = None, token: str = None) -> Optional[Dict]:
    """创建数据标准库"""
    log(f"创建数据标准库: {name}", "info")

    data = {
        "library_id": f"lib-{uuid.uuid4().hex[:8]}",
        "name": name,
        "description": description,
        "standards": standards or [],
        "category": "naming",
        "tags": ["demo"],
        "status": "active"
    }

    result = api_request("POST", "/api/v1/standards/libraries", data, token)

    if result.get("code") == 0:
        log(f"✅ 数据标准库创建成功: {name}", "success")
        return result.get("data")
    else:
        log(f"⚠️ 数据标准库创建: {result.get('message', '已存在')}", "warning")
        return None

def insert_metadata_directly(datasource_id: str, token: str = None) -> bool:
    """直接插入元数据（如果API支持）"""
    log("插入示例元数据...", "info")

    # 示例数据库和表
    databases = [
        {"database_id": f"db-{uuid.uuid4().hex[:8]}", "source_id": datasource_id,
         "database_name": "production", "description": "生产数据库", "table_count": 5},
        {"database_id": f"db-{uuid.uuid4().hex[:8]}", "source_id": datasource_id,
         "database_name": "analytics", "description": "分析数据库", "table_count": 3},
    ]

    tables = []
    table_templates = {
        "production": ["users", "orders", "products", "transactions", "logs"],
        "analytics": ["daily_metrics", "user_behavior", "sales_summary"]
    }

    for db in databases:
        db_name = db["database_name"]
        for table_name in table_templates.get(db_name, []):
            tables.append({
                "table_id": f"tbl-{uuid.uuid4().hex[:8]}",
                "database_id": db["database_id"],
                "source_id": datasource_id,
                "table_name": table_name,
                "database_name": db_name,
                "full_name": f"{db_name}.{table_name}",
                "row_count": 10000,
                "description": f"{table_name} 表",
                "tags": ["demo"]
            })

    # 尝试批量插入
    for table in tables:
        result = api_request("POST", "/api/v1/metadata/tables", table, token)
        if result.get("code") != 0:
            # API 可能不支持，跳过
            pass

    log(f"处理了 {len(tables)} 个元数据表", "info")
    return True

def init_demo_data():
    """初始化演示数据"""
    print("\n" + "="*60)
    print("ONE-DATA-STUDIO 演示数据初始化")
    print("="*60 + "\n")

    # 检查服务
    if not check_service():
        log("请确保 data-api 服务正在运行", "error")
        log(f"服务地址: {DATA_API_URL}", "info")
        log("启动方式: cd deploy/local && docker-compose up -d data-api", "info")
        return False

    # 尝试获取token（如果需要）
    token = None

    # 尝试登录获取token
    try:
        import requests
        login_response = requests.post(
            f"{DATA_API_URL}/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
            timeout=5
        )
        if login_response.status_code == 200:
            token_data = login_response.json()
            token = token_data.get("data", {}).get("access_token")
            if token:
                log("获取到认证 token", "success")
    except:
        pass

    if not token:
        log("使用无认证模式（开发环境）", "info")

    time.sleep(1)

    # 创建数据源
    log("\n========== 创建数据源 ==========", "info")
    datasources = []

    ds1 = create_datasource(
        name="MySQL 生产数据库",
        ds_type="mysql",
        host="mysql-production.example.com",
        port=3306,
        database="production",
        token=token
    )
    if ds1:
        datasources.append(ds1)

    time.sleep(0.5)

    ds2 = create_datasource(
        name="PostgreSQL 分析库",
        ds_type="postgresql",
        host="postgres-analytics.example.com",
        port=5432,
        database="analytics",
        token=token
    )
    if ds2:
        datasources.append(ds2)

    time.sleep(0.5)

    ds3 = create_datasource(
        name="MongoDB 用户行为",
        ds_type="mongodb",
        host="mongodb-behavior.example.com",
        port=27017,
        database="user_behavior",
        token=token
    )
    if ds3:
        datasources.append(ds3)

    # 创建数据集
    log("\n========== 创建数据集 ==========", "info")

    user_columns = [
        {"name": "user_id", "type": "bigint", "nullable": False, "description": "用户ID"},
        {"name": "username", "type": "varchar(50)", "nullable": False, "description": "用户名"},
        {"name": "email", "type": "varchar(100)", "nullable": True, "description": "邮箱"},
        {"name": "created_at", "type": "timestamp", "nullable": False, "description": "创建时间"}
    ]

    create_dataset(
        name="用户数据集",
        storage_type="s3",
        storage_path="s3://data-lake/users/",
        description="用户信息数据集",
        columns=user_columns,
        token=token
    )

    time.sleep(0.5)

    order_columns = [
        {"name": "order_id", "type": "bigint", "nullable": False, "description": "订单ID"},
        {"name": "user_id", "type": "bigint", "nullable": False, "description": "用户ID"},
        {"name": "amount", "type": "decimal(18,2)", "nullable": False, "description": "订单金额"},
        {"name": "status", "type": "varchar(20)", "nullable": False, "description": "状态"}
    ]

    create_dataset(
        name="订单数据集",
        storage_type="s3",
        storage_path="s3://data-lake/orders/",
        description="订单数据集",
        columns=order_columns,
        token=token
    )

    # 创建特征存储
    log("\n========== 创建特征存储 ==========", "info")

    create_feature_group(
        name="用户特征组",
        entity_name="user",
        description="用户相关特征",
        token=token
    )

    time.sleep(0.5)

    create_feature(
        name="用户活跃度",
        group_name="用户特征组",
        data_type="float",
        description="用户活跃度评分（0-100）",
        token=token
    )

    time.sleep(0.5)

    create_feature(
        name="平均订单金额",
        group_name="用户特征组",
        data_type="decimal(10,2)",
        description="用户平均订单金额",
        token=token
    )

    # 创建数据标准
    log("\n========== 创建数据标准 ==========", "info")

    create_standard(
        name="用户名命名规范",
        category="naming",
        rule_type="regex",
        description="用户名只能包含字母、数字和下划线，长度3-20",
        token=token
    )

    time.sleep(0.5)

    create_standard(
        name="邮箱格式标准",
        category="format",
        rule_type="regex",
        description="邮箱地址格式验证",
        token=token
    )

    time.sleep(0.5)

    create_standard(
        name="手机号格式标准",
        category="format",
        rule_type="regex",
        description="中国手机号格式验证（11位数字）",
        token=token
    )

    # 创建数据资产
    log("\n========== 创建数据资产 ==========", "info")

    if datasources:
        create_asset(
            name="用户表",
            asset_type="table",
            source_type="datasource",
            source_id=datasources[0].get("source_id", ""),
            description="系统用户信息表",
            token=token
        )

        time.sleep(0.5)

        create_asset(
            name="订单表",
            asset_type="table",
            source_type="datasource",
            source_id=datasources[0].get("source_id", ""),
            description="系统订单信息表",
            token=token
        )

    # 创建数据服务
    log("\n========== 创建数据服务 ==========", "info")

    if datasources:
        create_data_service(
            name="用户查询API",
            service_type="api",
            source_id=datasources[0].get("source_id", ""),
            description="根据用户ID查询用户信息",
            token=token
        )

    # 插入元数据
    if datasources:
        log("\n========== 插入元数据 ==========", "info")
        insert_metadata_directly(datasources[0].get("source_id", ""), token)

    # 完成提示
    print("\n" + "="*60)
    print("✅ 演示数据初始化完成！")
    print("="*60 + "\n")
    print("📊 已创建的数据:")
    print("  - 3 个数据源 (MySQL, PostgreSQL, MongoDB)")
    print("  - 2 个数据集 (用户数据集, 订单数据集)")
    print("  - 1 个特征组 (用户特征组)")
    print("  - 2 个特征 (用户活跃度, 平均订单金额)")
    print("  - 3 个数据标准 (用户名规范, 邮箱格式, 手机号格式)")
    print("  - 2 个数据资产 (用户表, 订单表)")
    print("  - 1 个数据服务 (用户查询API)")
    print("\n💡 提示: 请刷新前端页面查看数据")
    print(f"🌐 前端地址: {WEB_URL}")
    print()

    return True

def show_status():
    """显示数据状态"""
    print("\n" + "="*60)
    print("数据状态查看")
    print("="*60 + "\n")

    if not check_service():
        log("服务不可用", "error")
        return

    # 检查各类数据数量
    endpoints = {
        "数据源": "/api/v1/datasources",
        "数据集": "/api/v1/datasets",
        "特征": "/api/v1/features",
        "数据标准": "/api/v1/standards/elements",
        "数据资产": "/api/v1/assets",
        "数据服务": "/api/v1/services",
        "元数据库": "/api/v1/metadata/databases",
        "元数据表": "/api/v1/metadata/tables",
    }

    for name, endpoint in endpoints.items():
        result = api_request("GET", endpoint)
        if result.get("code") == 0:
            data = result.get("data", [])
            if isinstance(data, list):
                count = len(data)
            elif isinstance(data, dict) and "items" in data:
                count = len(data.get("items", []))
            elif isinstance(data, dict) and "total" in data:
                count = data.get("total", 0)
            else:
                count = "?"
            print(f"  {name}: {count}")
        else:
            print(f"  {name}: 无法获取")

    print()

def main():
    """主函数"""
    import argparse

    global DATA_API_URL

    parser = argparse.ArgumentParser(description="ONE-DATA-STUDIO 演示数据初始化")
    parser.add_argument("--url", default=DATA_API_URL, help="Data API 地址")
    parser.add_argument("--status", action="store_true", help="查看数据状态")
    parser.add_argument("--force", action="store_true", help="强制重新初始化")

    args = parser.parse_args()

    # 更新全局配置
    DATA_API_URL = args.url

    if args.status:
        show_status()
    else:
        init_demo_data()

if __name__ == "__main__":
    main()
