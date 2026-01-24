#!/usr/bin/env python3
"""
ONE-DATA-STUDIO 集成测试
Phase 1: 持久化版本测试
"""

import logging
import sys
import time
import requests
from typing import Dict, List, Optional

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Colors:
    """终端颜色"""
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'


class TestResult:
    """测试结果"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.failures = []

    def pass_test(self, name: str):
        self.passed += 1
        print(f"{Colors.GREEN}✓{Colors.NC} {name}")

    def fail_test(self, name: str, reason: str = ""):
        self.failed += 1
        print(f"{Colors.RED}✗{Colors.NC} {name}")
        if reason:
            print(f"  {Colors.RED}原因: {reason}{Colors.NC}")
        self.failures.append((name, reason))

    def skip_test(self, name: str, reason: str = ""):
        self.skipped += 1
        print(f"{Colors.CYAN}○{Colors.NC} {name}")
        if reason:
            print(f"  {Colors.CYAN}跳过: {reason}{Colors.NC}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"测试结果: {self.passed}/{total} 通过", end="")
        if self.skipped > 0:
            print(f", {self.skipped} 跳过")
        else:
            print()
        if self.failures:
            print(f"\n{Colors.RED}失败的测试:{Colors.NC}")
            for name, reason in self.failures:
                print(f"  - {name}: {reason}")
        print(f"{'='*60}")
        return self.failed == 0


class OneDataTestClient:
    """ONE-DATA-STUDIO 测试客户端"""

    def __init__(
        self,
        alldata_url: str = "http://localhost:8080",
        cube_url: str = "http://localhost:8000",
        bisheng_url: str = "http://localhost:8081",
    ):
        self.alldata_url = alldata_url.rstrip("/")
        self.cube_url = cube_url.rstrip("/")
        self.bisheng_url = bisheng_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    # ============================================
    # 健康检查
    # ============================================
    def check_alldata_health(self) -> Dict:
        try:
            r = self.session.get(f"{self.alldata_url}/api/v1/health", timeout=5)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            logger.debug(f"Alldata health check failed: {e}")
        return {}

    def check_cube_health(self) -> Dict:
        try:
            r = self.session.get(f"{self.cube_url}/health", timeout=5)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            logger.debug(f"Cube health check failed: {e}")
        return {}

    def check_bisheng_health(self) -> Dict:
        try:
            r = self.session.get(f"{self.bisheng_url}/api/v1/health", timeout=5)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            logger.debug(f"Bisheng health check failed: {e}")
        return {}

    # ============================================
    # Alldata API 测试
    # ============================================
    def list_datasets(self) -> Optional[List]:
        try:
            r = self.session.get(f"{self.alldata_url}/api/v1/datasets", timeout=5)
            if r.status_code == 200:
                return r.json().get("data", [])
        except Exception as e:
            logger.debug(f"List datasets failed: {e}")
        return None

    def create_dataset(self, name: str, path: str, **kwargs) -> Optional[str]:
        try:
            payload = {
                "name": name,
                "storage_path": path,
                "format": kwargs.get("format", "csv"),
                "description": kwargs.get("description", ""),
                "storage_type": kwargs.get("storage_type", "s3")
            }
            r = self.session.post(
                f"{self.alldata_url}/api/v1/datasets",
                json=payload,
                timeout=5
            )
            if r.status_code in (200, 201):
                return r.json().get("data", {}).get("dataset_id")
        except Exception as e:
            logger.debug(f"Create dataset failed: {e}")
        return None

    def get_dataset(self, dataset_id: str) -> Optional[Dict]:
        try:
            r = self.session.get(f"{self.alldata_url}/api/v1/datasets/{dataset_id}", timeout=5)
            if r.status_code == 200:
                return r.json().get("data")
        except Exception as e:
            logger.debug(f"Get dataset {dataset_id} failed: {e}")
        return None

    def update_dataset(self, dataset_id: str, **kwargs) -> bool:
        try:
            r = self.session.put(
                f"{self.alldata_url}/api/v1/datasets/{dataset_id}",
                json=kwargs,
                timeout=5
            )
            return r.status_code == 200
        except Exception as e:
            logger.debug(f"Update dataset {dataset_id} failed: {e}")
            return False

    def delete_dataset(self, dataset_id: str) -> bool:
        try:
            r = self.session.delete(f"{self.alldata_url}/api/v1/datasets/{dataset_id}", timeout=5)
            return r.status_code == 200
        except Exception as e:
            logger.debug(f"Delete dataset {dataset_id} failed: {e}")
            return False

    def get_upload_url(self, dataset_id: str, file_name: str) -> Optional[Dict]:
        try:
            r = self.session.post(
                f"{self.alldata_url}/api/v1/datasets/{dataset_id}/upload-url",
                json={"file_name": file_name},
                timeout=5
            )
            if r.status_code == 200:
                return r.json().get("data")
        except Exception as e:
            logger.debug(f"Get upload URL for {dataset_id}/{file_name} failed: {e}")
        return None

    def list_databases(self) -> Optional[List]:
        try:
            r = self.session.get(f"{self.alldata_url}/api/v1/metadata/databases", timeout=5)
            if r.status_code == 200:
                return r.json().get("data", {}).get("databases", [])
        except Exception as e:
            logger.debug(f"List databases failed: {e}")
        return None

    def list_tables(self, database: str) -> Optional[List]:
        try:
            r = self.session.get(
                f"{self.alldata_url}/api/v1/metadata/databases/{database}/tables",
                timeout=5
            )
            if r.status_code == 200:
                return r.json().get("data", {}).get("tables", [])
        except Exception as e:
            logger.debug(f"List tables for {database} failed: {e}")
        return None

    def get_table_schema(self, database: str, table: str) -> Optional[Dict]:
        try:
            r = self.session.get(
                f"{self.alldata_url}/api/v1/metadata/databases/{database}/tables/{table}",
                timeout=5
            )
            if r.status_code == 200:
                return r.json().get("data")
        except Exception as e:
            logger.debug(f"Get table schema {database}.{table} failed: {e}")
        return None

    def list_dataset_versions(self, dataset_id: str) -> Optional[List]:
        try:
            r = self.session.get(
                f"{self.alldata_url}/api/v1/datasets/{dataset_id}/versions",
                timeout=5
            )
            if r.status_code == 200:
                return r.json().get("data", {}).get("versions", [])
        except Exception as e:
            logger.debug(f"List versions for {dataset_id} failed: {e}")
        return None

    def create_dataset_version(self, dataset_id: str, **kwargs) -> Optional[Dict]:
        try:
            r = self.session.post(
                f"{self.alldata_url}/api/v1/datasets/{dataset_id}/versions",
                json=kwargs,
                timeout=5
            )
            if r.status_code in (200, 201):
                return r.json().get("data")
        except Exception as e:
            logger.debug(f"Create version for {dataset_id} failed: {e}")
        return None

    # ============================================
    # Cube 模型服务测试
    # ============================================
    def list_models(self) -> Optional[List]:
        try:
            r = self.session.get(f"{self.cube_url}/v1/models", timeout=5)
            if r.status_code == 200:
                return r.json().get("data", [])
        except Exception as e:
            logger.debug(f"List models failed: {e}")
        return None

    def chat_completion(self, message: str, model: Optional[str] = None, **kwargs) -> Optional[Dict]:
        try:
            models = self.list_models()
            if not models:
                return None
            model_id = model or models[0]["id"]

            payload = {
                "model": model_id,
                "messages": [{"role": "user", "content": message}],
                "max_tokens": kwargs.get("max_tokens", 100),
                "temperature": kwargs.get("temperature", 0.7)
            }

            r = self.session.post(
                f"{self.cube_url}/v1/chat/completions",
                json=payload,
                timeout=60
            )
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    def get_prompt_templates(self) -> Optional[List]:
        try:
            r = self.session.get(f"{self.cube_url}/api/v1/templates", timeout=5)
            if r.status_code == 200:
                return r.json().get("data", {}).get("templates", [])
        except Exception:
            pass
        return None

    # ============================================
    # Bisheng API 测试
    # ============================================
    def bisheng_chat(self, message: str, **kwargs) -> Optional[Dict]:
        try:
            payload = {"message": message}
            payload.update(kwargs)
            r = self.session.post(
                f"{self.bisheng_url}/api/v1/chat",
                json=payload,
                timeout=60
            )
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    def bisheng_list_datasets(self) -> Optional[List]:
        try:
            r = self.session.get(f"{self.bisheng_url}/api/v1/datasets", timeout=5)
            if r.status_code == 200:
                return r.json().get("data", [])
        except Exception:
            pass
        return None

    def rag_query(self, question: str) -> Optional[Dict]:
        try:
            r = self.session.post(
                f"{self.bisheng_url}/api/v1/rag/query",
                json={"question": question},
                timeout=60
            )
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    def text2sql(self, question: str, database: str = "sales_dw") -> Optional[Dict]:
        try:
            r = self.session.post(
                f"{self.bisheng_url}/api/v1/text2sql",
                json={"question": question, "database": database},
                timeout=60
            )
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    def list_workflows(self) -> Optional[List]:
        try:
            r = self.session.get(f"{self.bisheng_url}/api/v1/workflows", timeout=5)
            if r.status_code == 200:
                return r.json().get("data", {}).get("workflows", [])
        except Exception:
            pass
        return None


def run_tests(client: OneDataTestClient, result: TestResult):
    """运行所有测试"""

    print(f"{Colors.BLUE}=== ONE-DATA-STUDIO Phase 1 集成测试 ==={Colors.NC}\n")

    # ============================================
    # 1. 健康检查测试
    # ============================================
    print(f"{Colors.YELLOW}[1/8] 健康检查{Colors.NC}")

    alldata_health = client.check_alldata_health()
    if alldata_health:
        result.pass_test("Alldata API 健康检查")
        db_status = alldata_health.get("database", "unknown")
        result.pass_test(f"Alldata 数据库连接 ({db_status})",
                   "数据库未连接" if db_status != "connected" else "")
    else:
        result.fail_test("Alldata API 健康检查", "服务未响应")

    cube_health = client.check_cube_health()
    if cube_health:
        result.pass_test("OpenAI Proxy 健康检查")
        openai_configured = cube_health.get("openai_configured", False)
        if openai_configured:
            result.pass_test("OpenAI API 已配置")
        else:
            result.skip_test("OpenAI API 已配置", "未配置真实 API Key（将使用 Mock 模式）")
    else:
        result.fail_test("OpenAI Proxy 健康检查", "服务未响应")

    bisheng_health = client.check_bisheng_health()
    if bisheng_health:
        result.pass_test("Bisheng API 健康检查")
    else:
        result.fail_test("Bisheng API 健康检查", "服务未响应")

    # ============================================
    # 2. Alldata 数据集 CRUD 测试
    # ============================================
    print(f"\n{Colors.YELLOW}[2/8] Alldata 数据集 CRUD{Colors.NC}")

    datasets = client.list_datasets()
    if datasets is not None:
        result.pass_test("获取数据集列表")
        initial_count = len(datasets)
    else:
        result.fail_test("获取数据集列表", "API 调用失败")
        initial_count = 0

    # 创建数据集（带 Schema）
    ds_id = client.create_dataset(
        "test_dataset_phase1",
        "s3://test/phase1/",
        format="csv",
        description="Phase 1 测试数据集",
        schema={
            "columns": [
                {"name": "id", "type": "INT64", "nullable": False, "description": "主键"},
                {"name": "name", "type": "VARCHAR", "nullable": True, "description": "名称"}
            ]
        }
    )
    if ds_id:
        result.pass_test(f"创建数据集 ({ds_id})")
    else:
        result.fail_test("创建数据集", "API 调用失败")

    # 获取数据集详情
    if ds_id:
        ds_detail = client.get_dataset(ds_id)
        if ds_detail:
            result.pass_test("获取数据集详情")
            schema = ds_detail.get("schema", {})
            if schema.get("columns"):
                result.pass_test("数据集包含 Schema 定义")
            else:
                result.fail_test("数据集包含 Schema 定义", "Schema 为空")
        else:
            result.fail_test("获取数据集详情", "API 调用失败")

    # 更新数据集
    if ds_id:
        if client.update_dataset(ds_id, description="更新后的描述"):
            result.pass_test("更新数据集")
        else:
            result.fail_test("更新数据集", "API 调用失败")

    # 删除数据集
    if ds_id:
        if client.delete_dataset(ds_id):
            result.pass_test("删除数据集")
        else:
            result.fail_test("删除数据集", "API 调用失败")

    # ============================================
    # 3. Alldata 元数据 API 测试
    # ============================================
    print(f"\n{Colors.YELLOW}[3/8] Alldata 元数据 API{Colors.NC}")

    databases = client.list_databases()
    if databases:
        result.pass_test(f"获取数据库列表 ({len(databases)} 个)")
    else:
        result.fail_test("获取数据库列表", "API 调用失败")

    if databases:
        db_name = databases[0].get("name")
        tables = client.list_tables(db_name)
        if tables:
            result.pass_test(f"获取表列表 ({len(tables)} 个)")
        else:
            result.fail_test("获取表列表", "API 调用失败")

        if tables:
            table_name = tables[0].get("name")
            schema = client.get_table_schema(db_name, table_name)
            if schema and schema.get("columns"):
                result.pass_test("获取表结构 Schema")
            else:
                result.fail_test("获取表结构 Schema", "API 调用失败或无数据")

    # ============================================
    # 4. Alldata 版本管理测试
    # ============================================
    print(f"\n{Colors.YELLOW}[4/8] 数据集版本管理{Colors.NC}")

    # 使用示例数据集 ds-001
    versions = client.list_dataset_versions("ds-001")
    if versions is not None:
        result.pass_test("获取数据集版本列表")
    else:
        result.fail_test("获取数据集版本列表", "API 调用失败")

    new_version = client.create_dataset_version(
        "ds-001",
        storage_path="s3://etl-output/sales/2024-02/",
        description="2月份数据"
    )
    if new_version:
        result.pass_test(f"创建数据集版本 ({new_version.get('version_id')})")
    else:
        result.fail_test("创建数据集版本", "API 调用失败")

    # ============================================
    # 5. MinIO 文件上传 API 测试
    # ============================================
    print(f"\n{Colors.YELLOW}[5/8] MinIO 文件上传 API{Colors.NC}")

    upload_info = client.get_upload_url("ds-001", "test.csv")
    if upload_info and upload_info.get("upload_url"):
        result.pass_test("获取上传预签名 URL")
    else:
        result.fail_test("获取上传预签名 URL", "API 调用失败")

    # ============================================
    # 6. OpenAI Proxy 测试
    # ============================================
    print(f"\n{Colors.YELLOW}[6/8] OpenAI Proxy{Colors.NC}")

    models = client.list_models()
    if models:
        result.pass_test(f"列出模型 ({len(models)} 个)")
    else:
        result.fail_test("列出模型", "API 调用失败")

    response = client.chat_completion("1+1=")
    if response:
        result.pass_test("聊天补全")
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        if content:
            result.pass_test("获取回复内容")
    else:
        result.fail_test("聊天补全", "API 调用失败")

    # Prompt 模板
    templates = client.get_prompt_templates()
    if templates:
        result.pass_test(f"获取 Prompt 模板 ({len(templates)} 个)")
    else:
        result.fail_test("获取 Prompt 模板", "API 调用失败")

    # ============================================
    # 7. Bisheng 应用层测试
    # ============================================
    print(f"\n{Colors.YELLOW}[7/8] Bisheng 应用层{Colors.NC}")

    # 调用聊天接口
    bisheng_result = client.bisheng_chat("你好")
    if bisheng_result and bisheng_result.get("code") == 0:
        result.pass_test("Bisheng 聊天接口")
    else:
        result.fail_test("Bisheng 聊天接口", "API 调用失败")

    # 查询数据集
    bisheng_datasets = client.bisheng_list_datasets()
    if bisheng_datasets is not None:
        result.pass_test("Bisheng 查询数据集")
    else:
        result.fail_test("Bisheng 查询数据集", "API 调用失败")

    # 工作流列表
    workflows = client.list_workflows()
    if workflows:
        result.pass_test(f"获取工作流列表 ({len(workflows)} 个)")
    else:
        result.fail_test("获取工作流列表", "API 调用失败")

    # ============================================
    # 8. 端到端集成测试
    # ============================================
    print(f"\n{Colors.YELLOW}[8/8] 端到端集成{Colors.NC}")

    # RAG 查询
    rag_result = client.rag_query("什么是 ONE-DATA-STUDIO?")
    if rag_result and rag_result.get("code") == 0:
        result.pass_test("RAG 查询")
        answer = rag_result.get("data", {}).get("answer", "")
        if answer:
            result.pass_test("RAG 返回回答")
    else:
        result.fail_test("RAG 查询", "API 调用失败")

    # Text-to-SQL
    sql_result = client.text2sql("查询最近的订单")
    if sql_result and sql_result.get("code") == 0:
        result.pass_test("Text-to-SQL 查询")
        sql = sql_result.get("data", {}).get("sql", "")
        if sql:
            result.pass_test("返回 SQL 语句")
    else:
        result.fail_test("Text-to-SQL 查询", "API 调用失败")


def main():
    # 配置端点
    client = OneDataTestClient(
        alldata_url="http://localhost:8080",
        cube_url="http://localhost:8000",
        bisheng_url="http://localhost:8081",
    )

    # 等待服务启动
    print(f"{Colors.BLUE}等待服务启动...{Colors.NC}")
    for i in range(30):
        if client.check_alldata_health():
            print(f"{Colors.GREEN}服务已就绪{Colors.NC}")
            break
        if i % 5 == 0:
            print(f"  等待中... ({i*2}s)")
        time.sleep(2)
    else:
        print(f"{Colors.YELLOW}警告: 部分服务未响应，继续测试...{Colors.NC}")

    # 运行测试
    result = TestResult()
    run_tests(client, result)

    # 输出结果
    success = result.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
