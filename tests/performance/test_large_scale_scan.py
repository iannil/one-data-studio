"""
大规模元数据扫描性能测试
用例覆盖: DM-MS-006

测试场景:
1. 大规模元数据扫描性能
2. 并发扫描任务性能
3. 扫描结果处理性能
4. 敏感数据识别性能
5. AI 标注性能基准
"""

import os
import sys
import pytest
import time
import threading
from typing import List, Dict, Any
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


# ==================== 测试数据生成 ====================

def generate_table_metadata(num_tables: int, columns_per_table: int = 20) -> List[Dict[str, Any]]:
    """生成模拟表元数据"""
    tables = []
    for i in range(num_tables):
        columns = []
        for j in range(columns_per_table):
            col_type = ["varchar", "int", "float", "datetime", "text"][j % 5]
            columns.append({
                "name": f"col_{j}",
                "type": col_type,
                "nullable": j % 3 != 0,
                "comment": f"列 {j} 说明",
            })
        tables.append({
            "name": f"table_{i}",
            "schema": "public",
            "columns": columns,
            "row_count": (i + 1) * 1000,
            "size_bytes": (i + 1) * 1024 * 1024,
        })
    return tables


def generate_sensitivity_samples(num_records: int) -> List[Dict[str, str]]:
    """生成敏感数据样本"""
    samples = []
    for i in range(num_records):
        samples.append({
            "id": str(i),
            "phone": f"138{str(i).zfill(8)}",
            "id_card": f"11010119900101{str(i).zfill(4)}",
            "email": f"user_{i}@example.com",
            "name": f"用户{i}",
            "address": f"北京市朝阳区第{i}号",
        })
    return samples


class TestLargeScaleMetadataScan:
    """大规模元数据扫描性能测试 - DM-MS-006"""

    def test_scan_100_tables(self):
        """扫描 100 张表的元数据"""
        tables = generate_table_metadata(100)

        start = time.perf_counter()

        # 模拟元数据扫描处理
        results = []
        for table in tables:
            result = {
                "name": table["name"],
                "schema": table["schema"],
                "column_count": len(table["columns"]),
                "row_count": table["row_count"],
                "size_bytes": table["size_bytes"],
                "columns": [
                    {"name": col["name"], "type": col["type"]}
                    for col in table["columns"]
                ],
            }
            results.append(result)

        elapsed = time.perf_counter() - start
        throughput = len(tables) / elapsed

        print(f"\n扫描 100 张表: {elapsed:.3f}秒")
        print(f"吞吐量: {throughput:.2f} tables/秒")

        # 性能基准: 100 表 < 5 秒
        assert elapsed < 5, f"扫描 100 张表耗时 {elapsed}秒 超过基准"

    def test_scan_500_tables(self):
        """扫描 500 张表的元数据"""
        tables = generate_table_metadata(500)

        start = time.perf_counter()

        results = []
        for table in tables:
            result = {
                "name": table["name"],
                "column_count": len(table["columns"]),
                "columns": [
                    {"name": col["name"], "type": col["type"]}
                    for col in table["columns"]
                ],
            }
            results.append(result)

        elapsed = time.perf_counter() - start
        throughput = len(tables) / elapsed

        print(f"\n扫描 500 张表: {elapsed:.3f}秒")
        print(f"吞吐量: {throughput:.2f} tables/秒")

        # 性能基准: 500 表 < 15 秒
        assert elapsed < 15, f"扫描 500 张表耗时 {elapsed}秒 超过基准"

    def test_scan_1000_tables_with_columns(self):
        """扫描 1000 张表 (每表 50 列)"""
        tables = generate_table_metadata(1000, columns_per_table=50)

        start = time.perf_counter()

        total_columns = 0
        for table in tables:
            total_columns += len(table["columns"])
            for col in table["columns"]:
                # 模拟列级分析
                _ = {
                    "name": col["name"],
                    "type": col["type"],
                    "is_nullable": col["nullable"],
                }

        elapsed = time.perf_counter() - start

        print(f"\n扫描 1000 张表 (50 列/表): {elapsed:.3f}秒")
        print(f"总列数: {total_columns:,}")
        print(f"列处理速度: {total_columns/elapsed:.2f} columns/秒")

        # 性能基准: 1000 表 × 50 列 < 30 秒
        assert elapsed < 30, f"扫描耗时 {elapsed}秒 超过基准"


class TestConcurrentScanning:
    """并发扫描性能测试"""

    def test_concurrent_datasource_scans(self):
        """并发扫描多个数据源"""

        def scan_datasource(ds_id: int, num_tables: int) -> Dict[str, Any]:
            start = time.perf_counter()
            tables = generate_table_metadata(num_tables)
            results = [
                {"name": t["name"], "columns": len(t["columns"])}
                for t in tables
            ]
            elapsed = time.perf_counter() - start
            return {
                "datasource_id": ds_id,
                "tables_scanned": len(results),
                "elapsed": elapsed,
            }

        num_datasources = 10
        tables_per_ds = 50

        start_time = time.perf_counter()

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(scan_datasource, i, tables_per_ds)
                for i in range(num_datasources)
            ]
            results = [f.result() for f in as_completed(futures)]

        total_elapsed = time.perf_counter() - start_time
        total_tables = sum(r["tables_scanned"] for r in results)

        print(f"\n并发扫描 {num_datasources} 个数据源")
        print(f"总表数: {total_tables}")
        print(f"总耗时: {total_elapsed:.3f}秒")
        print(f"吞吐量: {total_tables/total_elapsed:.2f} tables/秒")

        # 性能基准: 10 数据源 × 50 表 < 10 秒
        assert total_elapsed < 10, f"并发扫描耗时 {total_elapsed}秒 超过基准"

    def test_parallel_column_analysis(self):
        """并行列级分析"""
        tables = generate_table_metadata(100, columns_per_table=30)
        all_columns = []
        for table in tables:
            for col in table["columns"]:
                all_columns.append({
                    "table": table["name"],
                    "column": col["name"],
                    "type": col["type"],
                })

        def analyze_column(col_info: Dict) -> Dict:
            # 模拟列级分析（类型识别、敏感检测等）
            return {
                "table": col_info["table"],
                "column": col_info["column"],
                "type_category": "numeric" if col_info["type"] in ("int", "float") else "text",
                "is_sensitive": col_info["column"] in ("phone", "id_card", "email"),
            }

        start = time.perf_counter()

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(analyze_column, all_columns))

        elapsed = time.perf_counter() - start

        print(f"\n并行分析 {len(all_columns)} 列")
        print(f"耗时: {elapsed:.3f}秒")
        print(f"列分析速度: {len(all_columns)/elapsed:.2f} columns/秒")

        # 性能基准: 3000 列 < 5 秒
        assert elapsed < 5, f"列分析耗时 {elapsed}秒 超过基准"


class TestSensitivityScanPerformance:
    """敏感数据识别性能测试"""

    def test_scan_1000_records(self):
        """扫描 1000 条记录的敏感数据"""
        import re

        records = generate_sensitivity_samples(1000)

        # 敏感数据正则规则
        patterns = {
            "phone": re.compile(r"1[3-9]\d{9}"),
            "id_card": re.compile(r"\d{17}[\dXx]"),
            "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
        }

        start = time.perf_counter()

        detections = []
        for record in records:
            for field, value in record.items():
                for pattern_name, pattern in patterns.items():
                    if pattern.search(str(value)):
                        detections.append({
                            "record_id": record["id"],
                            "field": field,
                            "type": pattern_name,
                        })

        elapsed = time.perf_counter() - start
        throughput = len(records) / elapsed

        print(f"\n扫描 1000 条记录: {elapsed:.3f}秒")
        print(f"检测到 {len(detections)} 个敏感字段")
        print(f"吞吐量: {throughput:.2f} records/秒")

        # 性能基准: 1000 条 < 1 秒
        assert elapsed < 1, f"敏感扫描耗时 {elapsed}秒 超过基准"

    def test_scan_10000_records(self):
        """扫描 10000 条记录的敏感数据"""
        import re

        records = generate_sensitivity_samples(10000)

        patterns = {
            "phone": re.compile(r"1[3-9]\d{9}"),
            "id_card": re.compile(r"\d{17}[\dXx]"),
            "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
        }

        start = time.perf_counter()

        detections = []
        for record in records:
            for field, value in record.items():
                for pattern_name, pattern in patterns.items():
                    if pattern.search(str(value)):
                        detections.append({
                            "record_id": record["id"],
                            "field": field,
                            "type": pattern_name,
                        })

        elapsed = time.perf_counter() - start
        throughput = len(records) / elapsed

        print(f"\n扫描 10000 条记录: {elapsed:.3f}秒")
        print(f"检测到 {len(detections)} 个敏感字段")
        print(f"吞吐量: {throughput:.2f} records/秒")

        # 性能基准: 10000 条 < 5 秒
        assert elapsed < 5, f"敏感扫描耗时 {elapsed}秒 超过基准"

    def test_scan_100000_records(self):
        """扫描 100000 条记录的敏感数据"""
        import re

        records = generate_sensitivity_samples(100000)

        patterns = {
            "phone": re.compile(r"1[3-9]\d{9}"),
            "id_card": re.compile(r"\d{17}[\dXx]"),
            "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
        }

        start = time.perf_counter()

        detection_count = 0
        for record in records:
            for field, value in record.items():
                for pattern_name, pattern in patterns.items():
                    if pattern.search(str(value)):
                        detection_count += 1

        elapsed = time.perf_counter() - start
        throughput = len(records) / elapsed

        print(f"\n扫描 100000 条记录: {elapsed:.3f}秒")
        print(f"检测到 {detection_count} 个敏感字段")
        print(f"吞吐量: {throughput:.2f} records/秒")

        # 性能基准: 100000 条 < 30 秒
        assert elapsed < 30, f"敏感扫描耗时 {elapsed}秒 超过基准"


class TestAIAnnotationPerformance:
    """AI 标注性能基准测试"""

    def test_ai_annotation_throughput(self):
        """AI 标注吞吐量测试"""
        # 模拟 LLM 响应
        mock_llm = Mock(return_value={
            "description": "自动生成的列描述",
            "business_name": "业务名称",
            "sensitivity": "non-sensitive",
        })

        columns = [
            {"name": f"col_{i}", "type": "varchar", "sample_values": [f"value_{j}" for j in range(5)]}
            for i in range(100)
        ]

        start = time.perf_counter()

        annotations = []
        for col in columns:
            # 模拟 AI 标注调用
            annotation = mock_llm(
                prompt=f"请为列 {col['name']} 生成描述",
                samples=col["sample_values"],
            )
            annotations.append(annotation)

        elapsed = time.perf_counter() - start
        throughput = len(columns) / elapsed

        print(f"\nAI 标注 100 列: {elapsed:.3f}秒")
        print(f"吞吐量: {throughput:.2f} columns/秒")

        # 性能基准: 100 列 AI 标注 < 10 秒 (模拟环境)
        assert elapsed < 10, f"AI 标注耗时 {elapsed}秒 超过基准"

    def test_batch_ai_annotation(self):
        """批量 AI 标注性能"""
        mock_llm = Mock(return_value={
            "annotations": [
                {"column": f"col_{i}", "description": f"描述_{i}"}
                for i in range(10)
            ]
        })

        tables = generate_table_metadata(50, columns_per_table=10)

        start = time.perf_counter()

        for table in tables:
            # 批量标注：每次传递一张表的所有列
            mock_llm(
                prompt=f"请为表 {table['name']} 的所有列生成描述",
                columns=[col["name"] for col in table["columns"]],
            )

        elapsed = time.perf_counter() - start
        throughput = len(tables) / elapsed

        print(f"\n批量标注 50 张表: {elapsed:.3f}秒")
        print(f"表处理速度: {throughput:.2f} tables/秒")

        # 性能基准: 50 表批量标注 < 5 秒 (模拟环境)
        assert elapsed < 5, f"批量标注耗时 {elapsed}秒 超过基准"


class TestScanResultProcessing:
    """扫描结果处理性能测试"""

    def test_result_aggregation(self):
        """测试扫描结果聚合性能"""
        tables = generate_table_metadata(500, columns_per_table=30)

        start = time.perf_counter()

        # 聚合统计
        stats = {
            "total_tables": len(tables),
            "total_columns": 0,
            "total_rows": 0,
            "total_size_bytes": 0,
            "column_type_distribution": {},
            "nullable_count": 0,
        }

        for table in tables:
            stats["total_rows"] += table["row_count"]
            stats["total_size_bytes"] += table["size_bytes"]
            for col in table["columns"]:
                stats["total_columns"] += 1
                col_type = col["type"]
                stats["column_type_distribution"][col_type] = (
                    stats["column_type_distribution"].get(col_type, 0) + 1
                )
                if col["nullable"]:
                    stats["nullable_count"] += 1

        elapsed = time.perf_counter() - start

        print(f"\n聚合 500 表元数据: {elapsed:.3f}秒")
        print(f"总列数: {stats['total_columns']:,}")
        print(f"总行数: {stats['total_rows']:,}")
        print(f"总大小: {stats['total_size_bytes']/1024/1024:.2f}MB")

        # 性能基准: 聚合 500 表 < 1 秒
        assert elapsed < 1, f"聚合耗时 {elapsed}秒 超过基准"

    def test_result_comparison(self):
        """测试扫描结果对比性能（增量检测）"""
        old_tables = generate_table_metadata(200, columns_per_table=20)
        new_tables = generate_table_metadata(210, columns_per_table=22)

        start = time.perf_counter()

        old_table_map = {t["name"]: t for t in old_tables}
        new_table_map = {t["name"]: t for t in new_tables}

        changes = {
            "added_tables": [],
            "removed_tables": [],
            "modified_tables": [],
        }

        # 检测新增表
        for name in new_table_map:
            if name not in old_table_map:
                changes["added_tables"].append(name)

        # 检测删除表
        for name in old_table_map:
            if name not in new_table_map:
                changes["removed_tables"].append(name)

        # 检测修改表
        for name in new_table_map:
            if name in old_table_map:
                old = old_table_map[name]
                new = new_table_map[name]
                if len(old["columns"]) != len(new["columns"]):
                    changes["modified_tables"].append(name)

        elapsed = time.perf_counter() - start

        print(f"\n对比 200→210 表变更: {elapsed:.3f}秒")
        print(f"新增: {len(changes['added_tables'])}")
        print(f"删除: {len(changes['removed_tables'])}")
        print(f"修改: {len(changes['modified_tables'])}")

        # 性能基准: 对比 < 1 秒
        assert elapsed < 1, f"对比耗时 {elapsed}秒 超过基准"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
