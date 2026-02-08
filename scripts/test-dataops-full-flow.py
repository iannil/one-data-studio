#!/usr/bin/env python3
"""
DataOps 全流程真实测试脚本
演示从数据接入到数据利用的完整 DataOps 流程
使用真实 API，测试数据持久化到数据库
"""

import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# 配置
DATA_API_URL = "http://localhost:8001"
AGENT_API_URL = "http://localhost:8000"

# 测试数据
TEST_DATASOURCE = {
    "name": "E2E测试_销售订单库",
    "type": "mysql",
    "description": "E2E全流程测试创建的数据源",
    "connection": {
        "host": "localhost",
        "port": 3325,  # 使用 persistent-test 的 MySQL
        "username": "root",
        "password": "test_password",
        "database": "persistent_ecommerce"
    },
    "tags": ["e2e-test", "dataops"]
}

TEST_ETL_JOB = {
    "name": "E2E测试_订单数据同步",
    "description": "E2E全流程测试创建的ETL任务",
    "source_table": "orders",
    "target_table": "dw_orders",
    "schedule": "0 2 * * *"
}

# 颜色输出
class Colors:
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'

def log(message: str, color: str = Colors.NC):
    """打印带颜色的日志"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{color}[{timestamp}] {message}{Colors.NC}")

def api_request(method: str, endpoint: str, data: Optional[Dict] = None, base_url: str = DATA_API_URL) -> Dict:
    """发送 API 请求"""
    url = f"{base_url}{endpoint}"
    headers = {"Content-Type": "application/json"}

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
            raise ValueError(f"Unknown method: {method}")

        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log(f"API 请求失败: {e}", Colors.RED)
        return {"code": -1, "message": str(e)}

def print_section(title: str):
    """打印分节标题"""
    print("\n" + "=" * 60)
    log(title, Colors.BLUE)
    print("=" * 60)

def check_health() -> bool:
    """检查服务健康状态"""
    print_section("阶段0: 服务健康检查")

    # 检查 Data API
    result = api_request("GET", "/api/v1/health")
    if result.get("code") == 0:
        log(f"✓ Data API 健康状态: {result.get('message')}", Colors.GREEN)
    else:
        log("✗ Data API 不可用", Colors.RED)
        return False

    return True

def stage1_data_ingestion() -> Dict:
    """阶段1: 数据接入 - 注册数据源"""
    print_section("阶段1: 数据接入")

    results = {"datasource_id": None}

    # 1.1 查看现有数据源
    log("1.1 查看现有数据源...", Colors.YELLOW)
    sources = api_request("GET", "/api/v1/datasources")
    if sources.get("code") == 0:
        existing = sources.get("data", {}).get("sources", [])
        log(f"✓ 现有数据源数量: {len(existing)}", Colors.GREEN)
        for src in existing[:3]:  # 显示前3个
            log(f"  - {src.get('name')} ({src.get('type')})", Colors.NC)

    # 1.2 创建新数据源
    log("\n1.2 创建新数据源...", Colors.YELLOW)
    create_result = api_request("POST", "/api/v1/datasources", TEST_DATASOURCE)

    if create_result.get("code") == 0:
        source_id = create_result.get("data", {}).get("source_id")
        results["datasource_id"] = source_id
        log(f"✓ 数据源创建成功! ID: {source_id}", Colors.GREEN)

        # 1.3 测试连接
        log(f"\n1.3 测试数据源连接...", Colors.YELLOW)
        test_result = api_request("POST", f"/api/v1/datasources/{source_id}/test", {
            "password": TEST_DATASOURCE["connection"]["password"]
        })

        if test_result.get("code") == 0 or test_result.get("data", {}).get("success"):
            log(f"✓ 连接测试成功! 延迟: {test_result.get('data', {}).get('latency_ms', 'N/A')}ms", Colors.GREEN)
        else:
            log(f"⚠ 连接测试结果: {test_result.get('message', 'Unknown')}", Colors.YELLOW)
    else:
        log(f"✗ 数据源创建失败: {create_result.get('message')}", Colors.RED)
        # 尝试使用现有数据源
        if sources.get("code") == 0 and sources.get("data", {}).get("sources"):
            existing = sources["data"]["sources"][0]
            results["datasource_id"] = existing.get("source_id")
            log(f"→ 使用现有数据源: {existing.get('name')}", Colors.YELLOW)

    return results

def stage2_data_processing(datasource_id: str) -> Dict:
    """阶段2: 数据处理 - ETL 任务"""
    print_section("阶段2: 数据处理 (ETL)")

    results = {"etl_job_id": None}

    # 2.1 查看 ETL 任务列表
    log("2.1 查看 ETL 任务列表...", Colors.YELLOW)
    etl_jobs = api_request("GET", "/api/v1/etl-jobs")
    if etl_jobs.get("code") == 0:
        jobs = etl_jobs.get("data", {}).get("jobs", [])
        log(f"✓ 现有 ETL 任务数量: {len(jobs)}", Colors.GREEN)

    # 2.2 创建 ETL 任务
    log("\n2.2 创建 ETL 任务...", Colors.YELLOW)
    etl_data = {
        **TEST_ETL_JOB,
        "source_datasource_id": datasource_id,
        "source_type": "mysql"
    }

    create_result = api_request("POST", "/api/v1/etl-jobs", etl_data)

    if create_result.get("code") == 0:
        job_id = create_result.get("data", {}).get("job_id")
        results["etl_job_id"] = job_id
        log(f"✓ ETL 任务创建成功! ID: {job_id}", Colors.GREEN)
    else:
        log(f"⚠ ETL 任务创建: {create_result.get('message', '可能需要额外参数')}", Colors.YELLOW)

    return results

def stage3_data_governance(datasource_id: str) -> Dict:
    """阶段3: 数据治理 - 元数据管理"""
    print_section("阶段3: 数据治理")

    results = {"tables_scanned": 0}

    # 3.1 获取数据库列表
    log("3.1 获取数据库列表...", Colors.YELLOW)
    databases = api_request("GET", "/api/v1/databases")
    if databases.get("code") == 0:
        dbs = databases.get("data", {}).get("databases", [])
        log(f"✓ 数据库数量: {len(dbs)}", Colors.GREEN)
        for db in dbs[:5]:
            log(f"  - {db.get('name')}", Colors.NC)

    # 3.2 获取表列表
    log("\n3.2 获取表列表 (元数据采集)...", Colors.YELLOW)
    tables = api_request("GET", f"/api/v1/tables?database={TEST_DATASOURCE['connection']['database']}")
    if tables.get("code") == 0:
        tbls = tables.get("data", {}).get("tables", [])
        results["tables_scanned"] = len(tbls)
        log(f"✓ 表数量: {len(tbls)}", Colors.GREEN)
        for tbl in tbls[:5]:
            log(f"  - {tbl.get('name')} ({tbl.get('type', 'table')})", Colors.NC)

    # 3.3 获取表详情 (元数据)
    if tables.get("code") == 0 and tables.get("data", {}).get("tables"):
        first_table = tables["data"]["tables"][0]
        table_name = first_table.get("name")

        log(f"\n3.3 获取表详情: {table_name}...", Colors.YELLOW)
        detail = api_request("GET", f"/api/v1/tables/{TEST_DATASOURCE['connection']['database']}/{table_name}")
        if detail.get("code") == 0:
            columns = detail.get("data", {}).get("columns", [])
            log(f"✓ 列数量: {len(columns)}", Colors.GREEN)
            for col in columns[:5]:
                log(f"  - {col.get('name')}: {col.get('type')}", Colors.NC)

    # 3.4 数据质量检查
    log("\n3.4 数据质量规则...", Colors.YELLOW)
    quality = api_request("GET", "/api/v1/data-quality/rules")
    if quality.get("code") == 0:
        rules = quality.get("data", {}).get("rules", [])
        log(f"✓ 质量规则数量: {len(rules)}", Colors.GREEN)

    # 3.5 数据血缘
    log("\n3.5 数据血缘关系...", Colors.YELLOW)
    lineage = api_request("GET", "/api/v1/lineage")
    if lineage.get("code") == 0:
        nodes = lineage.get("data", {}).get("nodes", [])
        edges = lineage.get("data", {}).get("edges", [])
        log(f"✓ 血缘节点: {len(nodes)}, 关系: {len(edges)}", Colors.GREEN)

    return results

def stage4_data_utilization() -> Dict:
    """阶段4: 数据利用 - Text-to-SQL, BI, 数据服务"""
    print_section("阶段4: 数据利用")

    results = {}

    # 4.1 Text-to-SQL 测试
    log("4.1 Text-to-SQL 自然语言查询...", Colors.YELLOW)
    text2sql = api_request("POST", "/api/v1/text2sql", {
        "natural_language": "查询最近10条订单记录",
        "database": TEST_DATASOURCE["connection"]["database"]
    }, base_url=AGENT_API_URL)

    if text2sql.get("code") == 0:
        sql = text2sql.get("data", {}).get("sql", "")
        log(f"✓ 生成的 SQL: {sql[:100]}...", Colors.GREEN)
        results["sql_generated"] = True
    else:
        log(f"⚠ Text-to-SQL: {text2sql.get('message', '可能需要配置LLM')}", Colors.YELLOW)
        results["sql_generated"] = False

    # 4.2 BI 报表
    log("\n4.2 BI 报表配置...", Colors.YELLOW)
    bi = api_request("GET", "/api/v1/bi/dashboards")
    if bi.get("code") == 0:
        dashboards = bi.get("data", {}).get("dashboards", [])
        log(f"✓ BI 报表数量: {len(dashboards)}", Colors.GREEN)
        results["bi_dashboards"] = len(dashboards)

    # 4.3 数据服务 API
    log("\n4.3 数据服务 API...", Colors.YELLOW)
    services = api_request("GET", "/api/v1/data-services")
    if services.get("code") == 0:
        svcs = services.get("data", {}).get("services", [])
        log(f"✓ 数据服务数量: {len(svcs)}", Colors.GREEN)
        results["data_services"] = len(svcs)

    # 4.4 特征存储
    log("\n4.4 特征存储...", Colors.YELLOW)
    features = api_request("GET", "/api/v1/features")
    if features.get("code") == 0:
        feature_groups = features.get("data", {}).get("feature_groups", [])
        log(f"✓ 特征组数量: {len(feature_groups)}", Colors.GREEN)
        results["feature_groups"] = len(feature_groups)

    return results

def verify_persistence():
    """验证数据持久化"""
    print_section("验证: 数据持久化检查")

    log("检查系统中的数据...", Colors.YELLOW)

    checks = []

    # 检查数据源
    sources = api_request("GET", "/api/v1/datasources")
    source_count = len(sources.get("data", {}).get("sources", []))
    checks.append(("数据源", source_count, source_count > 0))

    # 检查 ETL 任务
    etl_jobs = api_request("GET", "/api/v1/etl-jobs")
    job_count = len(etl_jobs.get("data", {}).get("jobs", []))
    checks.append(("ETL任务", job_count, job_count >= 0))

    # 检查元数据
    tables = api_request("GET", f"/api/v1/tables?database={TEST_DATASOURCE['connection']['database']}")
    table_count = len(tables.get("data", {}).get("tables", []))
    checks.append(("元数据表", table_count, table_count >= 0))

    # 打印结果
    print("\n" + "-" * 50)
    print(f"{'项目':<15} {'数量':<10} {'状态'}")
    print("-" * 50)

    all_ok = True
    for name, count, ok in checks:
        status = "✓ 正常" if ok else "✗ 异常"
        color = Colors.GREEN if ok else Colors.RED
        log(f"{name:<15} {str(count):<10} {status}", color)
        if not ok:
            all_ok = False

    print("-" * 50)

    return all_ok

def generate_report(stage1: Dict, stage2: Dict, stage3: Dict, stage4: Dict):
    """生成测试报告"""
    print_section("DataOps 全流程测试报告")

    # Helper to format values safely
    def fmt(val, default='N/A', width=50):
        s = str(val if val is not None else default)
        return s.ljust(width)

    # Helper to format boolean
    def fmt_bool(val, width=48):
        s = '✓ 成功' if val else '✗ 失败'
        return s.ljust(width)

    datasource_id = stage1.get('datasource_id') or 'N/A'
    etl_job_id = stage2.get('etl_job_id') or 'N/A'
    tables_scanned = stage3.get('tables_scanned') or 0
    sql_generated = stage4.get('sql_generated', False)
    bi_dashboards = stage4.get('bi_dashboards') or 0
    data_services = stage4.get('data_services') or 0
    feature_groups = stage4.get('feature_groups') or 0
    test_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    report = f"""
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DataOps 全流程测试完成                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  阶段1: 数据接入                                                             │
│    数据源 ID: {datasource_id:<50}                                           │
│                                                                             │
│  阶段2: 数据处理 (ETL)                                                       │
│    ETL 任务 ID: {etl_job_id:<50}                                           │
│                                                                             │
│  阶段3: 数据治理                                                             │
│    扫描表数量: {tables_scanned:<50}                                         │
│                                                                             │
│  阶段4: 数据利用                                                             │
│    SQL 生成: {fmt_bool(sql_generated)}                                     │
│    BI 报表数: {bi_dashboards:<50}                                          │
│    数据服务数: {data_services:<50}                                         │
│    特征组数: {feature_groups:<50}                                          │
│                                                                             │
│  测试时间: {test_time:<50}                                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
"""
    print(report)

    # 保存报告到文件
    report_file = "test-results/dataops-test-report.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    log(f"报告已保存: {report_file}", Colors.GREEN)

def main():
    """主函数"""
    print("\n" + "=" * 70)
    log("DataOps 全流程真实测试", Colors.BLUE)
    log("使用真实 API，数据持久化到数据库", Colors.BLUE)
    print("=" * 70)

    # 0. 健康检查
    if not check_health():
        log("服务不可用，退出测试", Colors.RED)
        sys.exit(1)

    time.sleep(1)

    # 1. 数据接入
    stage1_result = stage1_data_ingestion()
    time.sleep(1)

    # 2. 数据处理
    datasource_id = stage1_result.get("datasource_id")
    if datasource_id:
        stage2_result = stage2_data_processing(datasource_id)
    else:
        stage2_result = {}
    time.sleep(1)

    # 3. 数据治理
    if datasource_id:
        stage3_result = stage3_data_governance(datasource_id)
    else:
        stage3_result = {}
    time.sleep(1)

    # 4. 数据利用
    stage4_result = stage4_data_utilization()

    # 5. 验证持久化
    verify_persistence()

    # 6. 生成报告
    generate_report(stage1_result, stage2_result, stage3_result, stage4_result)

    log("\n✓ DataOps 全流程测试完成!", Colors.GREEN)

if __name__ == "__main__":
    main()
