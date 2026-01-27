#!/usr/bin/env python3
"""
OCR服务性能测试脚本
测试服务的吞吐量、响应时间、并发能力等性能指标
"""

import time
import statistics
import concurrent.futures
from typing import List, Dict
from dataclasses import dataclass
from pathlib import Path
import requests
import json

# 配置
OCR_API_URL = "http://localhost:8007/api/v1/ocr"
TEST_FILE = Path(__file__).parent.parent / "tests" / "documents" / "sample_invoice.pdf"
WARMUP_COUNT = 3
TEST_COUNT = 10
MAX_WORKERS = 5


@dataclass
class TestResult:
    """测试结果"""
    name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_time: float
    min_time: float
    max_time: float
    p50_time: float
    p95_time: float
    p99_time: float
    throughput: float  # requests per second


class PerformanceTester:
    """性能测试器"""

    def __init__(self, api_url: str):
        self.api_url = api_url
        self.session = requests.Session()

    def health_check(self) -> bool:
        """健康检查"""
        try:
            response = self.session.get(f"{self.api_url.replace('/api/v1/ocr', '')}/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def single_request(self, file_path: str) -> Dict:
        """执行单次请求"""
        start_time = time.time()

        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                data = {'extraction_type': 'invoice'}
                response = self.session.post(
                    f"{self.api_url}/tasks",
                    files=files,
                    data=data,
                    timeout=60
                )

            if response.status_code == 200:
                task_id = response.json().get('task_id')

                # 等待结果
                while True:
                    result_response = self.session.get(
                        f"{self.api_url}/tasks/{task_id}/result/enhanced",
                        timeout=10
                    )
                    if result_response.status_code == 200:
                        result = result_response.json()
                        if result.get('status') == 'completed':
                            elapsed = time.time() - start_time
                            return {'success': True, 'time': elapsed}
                        elif result.get('status') == 'failed':
                            elapsed = time.time() - start_time
                            return {'success': False, 'time': elapsed, 'error': 'Processing failed'}
                    time.sleep(0.5)

        except Exception as e:
            elapsed = time.time() - start_time
            return {'success': False, 'time': elapsed, 'error': str(e)}

    def warmup(self, count: int = 3):
        """预热测试"""
        print(f"🔥 预热中 ({count} 次请求)...")

        for i in range(count):
            result = self.single_request(str(TEST_FILE))
            status = "✅" if result['success'] else "❌"
            print(f"  {status} 请求 {i+1}/{count}: {result['time']:.2f}s")

    def test_single_thread(self, count: int = 10) -> TestResult:
        """单线程性能测试"""
        print(f"\n📊 单线程性能测试 ({count} 次请求)...")
        print("-" * 50)

        times = []
        successful = 0
        failed = 0

        for i in range(count):
            result = self.single_request(str(TEST_FILE))
            times.append(result['time'])

            if result['success']:
                successful += 1
                print(f"  ✅ 请求 {i+1}/{count}: {result['time']:.2f}s")
            else:
                failed += 1
                print(f"  ❌ 请求 {i+1}/{count}: {result['time']:.2f}s - {result.get('error', 'Unknown')}")

        return TestResult(
            name="单线程测试",
            total_requests=count,
            successful_requests=successful,
            failed_requests=failed,
            avg_time=statistics.mean(times),
            min_time=min(times),
            max_time=max(times),
            p50_time=statistics.median(times),
            p95_time=sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else times[0],
            p99_time=sorted(times)[int(len(times) * 0.99)] if len(times) > 1 else times[0],
            throughput=successful / sum(times)
        )

    def test_concurrent(self, workers: int = 5, count: int = 20) -> TestResult:
        """并发性能测试"""
        print(f"\n🚀 并发性能测试 ({workers} 线程, {count} 请求)...")
        print("-" * 50)

        times = []
        successful = 0
        failed = 0
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = []

            for i in range(count):
                future = executor.submit(self.single_request, str(TEST_FILE))
                futures.append(future)

            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                result = future.result()
                times.append(result['time'])

                if result['success']:
                    successful += 1
                    print(f"  ✅ 请求完成: {result['time']:.2f}s")
                else:
                    failed += 1
                    print(f"  ❌ 请求失败: {result['time']:.2f}s")

        total_time = time.time() - start_time

        return TestResult(
            name=f"并发测试 ({workers}线程)",
            total_requests=count,
            successful_requests=successful,
            failed_requests=failed,
            avg_time=statistics.mean(times) if times else 0,
            min_time=min(times) if times else 0,
            max_time=max(times) if times else 0,
            p50_time=statistics.median(times) if times else 0,
            p95_time=sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else (times[0] if times else 0),
            p99_time=sorted(times)[int(len(times) * 0.99)] if len(times) > 1 else (times[0] if times else 0),
            throughput=successful / total_time
        )

    def print_result(self, result: TestResult):
        """打印测试结果"""
        print(f"\n📋 {result.name} 结果:")
        print("=" * 50)
        print(f"  总请求数:      {result.total_requests}")
        print(f"  成功请求:      {result.successful_requests} ✅")
        print(f"  失败请求:      {result.failed_requests} ❌")
        print(f"  成功率:        {result.successful_requests / result.total_requests * 100:.1f}%")
        print(f"\n  响应时间:")
        print(f"    平均:        {result.avg_time:.2f}s")
        print(f"    最小:        {result.min_time:.2f}s")
        print(f"    最大:        {result.max_time:.2f}s")
        print(f"    P50:         {result.p50_time:.2f}s")
        print(f"    P95:         {result.p95_time:.2f}s")
        print(f"    P99:         {result.p99_time:.2f}s")
        print(f"\n  吞吐量:        {result.throughput:.2f} 请求/秒")

    def generate_report(self, results: List[TestResult]):
        """生成性能测试报告"""
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'results': [
                {
                    'name': r.name,
                    'total_requests': r.total_requests,
                    'successful_requests': r.successful_requests,
                    'failed_requests': r.failed_requests,
                    'avg_time': round(r.avg_time, 2),
                    'min_time': round(r.min_time, 2),
                    'max_time': round(r.max_time, 2),
                    'p50_time': round(r.p50_time, 2),
                    'p95_time': round(r.p95_time, 2),
                    'p99_time': round(r.p99_time, 2),
                    'throughput': round(r.throughput, 2)
                }
                for r in results
            ]
        }

        report_path = Path(__file__).parent / f"performance_report_{time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n📄 性能报告已保存: {report_path}")


def main():
    """主函数"""
    print("=" * 60)
    print("OCR服务性能测试")
    print("=" * 60)
    print(f"📅 开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔗 API地址: {OCR_API_URL}")
    print(f"📁 测试文件: {TEST_FILE}")

    # 检查服务
    tester = PerformanceTester(OCR_API_URL)

    if not tester.health_check():
        print("\n❌ 服务不可用，请先启动OCR服务")
        return

    print("✅ 服务健康检查通过")

    # 检查测试文件
    if not TEST_FILE.exists():
        print(f"\n⚠️  测试文件不存在: {TEST_FILE}")
        print("请将测试文档放在 tests/documents/ 目录下")
        return

    # 预热
    print()
    tester.warmup(WARMUP_COUNT)

    # 运行测试
    results = []

    # 单线程测试
    result1 = tester.test_single_thread(TEST_COUNT)
    tester.print_result(result1)
    results.append(result1)

    # 并发测试
    result2 = tester.test_concurrent(MAX_WORKERS, TEST_COUNT * 2)
    tester.print_result(result2)
    results.append(result2)

    # 生成报告
    tester.generate_report(results)

    # 总结
    print("\n" + "=" * 60)
    print("性能测试完成")
    print("=" * 60)

    avg_throughput = statistics.mean([r.throughput for r in results])
    print(f"\n📊 平均吞吐量: {avg_throughput:.2f} 请求/秒")


if __name__ == "__main__":
    main()
