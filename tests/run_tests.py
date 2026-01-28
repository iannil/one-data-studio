#!/usr/bin/env python3
"""
ONE-DATA-STUDIO 测试执行脚本
根据测试计划自动化执行各阶段测试
"""

import os
import sys
import subprocess
import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


class TestRunner:
    """测试执行器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.reports_dir = project_root / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        self.results = []

    def run_command(self, cmd: List[str], description: str, timeout: int = 600) -> Dict:
        """执行命令并返回结果"""
        print(f"\n{'='*60}")
        print(f"执行: {description}")
        print(f"命令: {' '.join(cmd)}")
        print(f"{'='*60}")

        start_time = datetime.now()
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            duration = (datetime.now() - start_time).total_seconds()

            return {
                "description": description,
                "command": " ".join(cmd),
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": duration,
                "success": result.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return {
                "description": description,
                "command": " ".join(cmd),
                "returncode": -1,
                "error": "Timeout",
                "success": False
            }
        except Exception as e:
            return {
                "description": description,
                "command": " ".join(cmd),
                "returncode": -1,
                "error": str(e),
                "success": False
            }

    def run_unit_tests(self, module: Optional[str] = None, priority: Optional[str] = None) -> Dict:
        """运行单元测试"""
        cmd = ["pytest", "tests/unit/", "-v", "--tb=short"]

        if module:
            cmd = ["pytest", f"tests/unit/test_{module}.py", "-v", "--tb=short"]

        if priority:
            cmd.extend(["-m", priority])

        # 添加覆盖率
        cmd.extend(["--cov=services", "--cov-report=html", f"--cov-report=html:{self.reports_dir}/coverage"])

        result = self.run_command(cmd, f"单元测试 (模块: {module or 'all'}, 优先级: {priority or 'all'})")
        self.results.append(result)
        return result

    def run_integration_tests(self, module: Optional[str] = None) -> Dict:
        """运行集成测试"""
        cmd = ["pytest", "tests/integration/", "-v", "--tb=short"]

        if module:
            cmd = ["pytest", f"tests/integration/test_{module}.py", "-v", "--tb=short"]

        result = self.run_command(cmd, f"集成测试 (模块: {module or 'all'})", timeout=900)
        self.results.append(result)
        return result

    def run_e2e_tests(self, suite: Optional[str] = None) -> Dict:
        """运行 E2E 测试"""
        cmd = ["npx", "playwright", "test"]

        if suite:
            cmd.extend(["--project", suite])

        result = self.run_command(cmd, f"E2E 测试 (套件: {suite or 'all'})", timeout=1200)
        self.results.append(result)
        return result

    def run_frontend_tests(self) -> Dict:
        """运行前端测试"""
        cmd = ["npm", "run", "test", "--", "--run"]
        result = self.run_command(cmd, "前端单元测试")
        self.results.append(result)
        return result

    def run_performance_tests(self) -> Dict:
        """运行性能测试"""
        cmd = ["pytest", "tests/performance/", "-v", "--benchmark"]
        result = self.run_command(cmd, "性能测试", timeout=1800)
        self.results.append(result)
        return result

    def run_security_tests(self) -> Dict:
        """运行安全测试"""
        cmd = ["pytest", "tests/", "-m", "security", "-v"]
        result = self.run_command(cmd, "安全测试")
        self.results.append(result)
        return result

    def generate_report(self) -> str:
        """生成测试报告"""
        report_file = self.reports_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for r in self.results if r.get("success")),
                "failed": sum(1 for r in self.results if not r.get("success")),
                "total_duration": sum(r.get("duration", 0) for r in self.results)
            },
            "results": self.results
        }

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)

        return str(report_file)


def run_phase_1():
    """阶段一：环境准备"""
    print("\n" + "="*60)
    print("阶段一：环境准备")
    print("="*60)

    # 检查环境
    checks = [
        ("Python 版本", ["python", "--version"]),
        ("Node.js 版本", ["node", "--version"]),
        ("Docker 状态", ["docker", "ps"]),
    ]

    for name, cmd in checks:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            print(f"✓ {name}: {result.stdout.strip()}")
        except Exception as e:
            print(f"✗ {name}: 检查失败 - {e}")


def run_phase_2(runner: TestRunner, module: Optional[str] = None):
    """阶段二：单元测试"""
    print("\n" + "="*60)
    print("阶段二：单元测试")
    print("="*60)

    # 后端单元测试
    runner.run_unit_tests(module=module)

    # 前端单元测试
    os.chdir(runner.project_root / "web")
    runner.run_frontend_tests()
    os.chdir(runner.project_root)


def run_phase_3(runner: TestRunner, module: Optional[str] = None):
    """阶段三：集成测试"""
    print("\n" + "="*60)
    print("阶段三：集成测试")
    print("="*60)

    if module:
        runner.run_integration_tests(module=module)
    else:
        # 按模块顺序执行
        modules = [
            "metadata_scan",
            "sensitivity_scan",
            "asset_management",
            "etl_pipeline",
            "table_fusion",
            "knowledge_base",
            "intelligent_query",
            "model_training",
            "model_deployment",
            "user_management",
        ]
        for mod in modules:
            runner.run_integration_tests(module=mod)


def run_phase_4(runner: TestRunner, suite: Optional[str] = None):
    """阶段四：E2E 测试"""
    print("\n" + "="*60)
    print("阶段四：E2E 测试")
    print("="*60)

    runner.run_e2e_tests(suite=suite)


def run_phase_5(runner: TestRunner):
    """阶段五：专项测试"""
    print("\n" + "="*60)
    print("阶段五：专项测试")
    print("="*60)

    runner.run_performance_tests()
    runner.run_security_tests()


def main():
    parser = argparse.ArgumentParser(description="ONE-DATA-STUDIO 测试执行脚本")
    parser.add_argument(
        "--phase",
        type=int,
        choices=[1, 2, 3, 4, 5],
        help="执行指定阶段 (1-环境准备, 2-单元测试, 3-集成测试, 4-E2E测试, 5-专项测试)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="执行所有阶段"
    )
    parser.add_argument(
        "--module",
        type=str,
        help="指定测试模块"
    )
    parser.add_argument(
        "--suite",
        type=str,
        help="指定 E2E 测试套件"
    )
    parser.add_argument(
        "--priority",
        type=str,
        choices=["p0", "p1", "p2"],
        help="指定测试优先级"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="快速测试 (仅 P0 用例)"
    )

    args = parser.parse_args()

    # 确定项目根目录
    project_root = Path(__file__).parent.parent
    runner = TestRunner(project_root)

    print("\n" + "="*60)
    print("ONE-DATA-STUDIO 测试执行")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    priority = "p0" if args.quick else args.priority

    try:
        if args.all:
            run_phase_1()
            run_phase_2(runner, args.module)
            run_phase_3(runner, args.module)
            run_phase_4(runner, args.suite)
            run_phase_5(runner)
        elif args.phase == 1:
            run_phase_1()
        elif args.phase == 2:
            run_phase_2(runner, args.module)
        elif args.phase == 3:
            run_phase_3(runner, args.module)
        elif args.phase == 4:
            run_phase_4(runner, args.suite)
        elif args.phase == 5:
            run_phase_5(runner)
        else:
            # 默认运行单元测试
            runner.run_unit_tests(module=args.module, priority=priority)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    finally:
        # 生成报告
        if runner.results:
            report_file = runner.generate_report()
            print(f"\n测试报告已生成: {report_file}")

            # 打印摘要
            passed = sum(1 for r in runner.results if r.get("success"))
            failed = len(runner.results) - passed
            print(f"\n测试摘要:")
            print(f"  总计: {len(runner.results)}")
            print(f"  通过: {passed}")
            print(f"  失败: {failed}")

            if failed > 0:
                sys.exit(1)


if __name__ == "__main__":
    main()
