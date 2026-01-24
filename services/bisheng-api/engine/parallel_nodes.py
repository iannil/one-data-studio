"""
并行执行节点
Sprint 18: 工作流节点扩展

支持工作流中的并行分支执行
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ParallelStrategy(Enum):
    """并行执行策略"""
    ALL = "all"  # 等待所有分支完成
    ANY = "any"  # 任意一个分支完成即可
    MAJORITY = "majority"  # 多数分支完成即可


@dataclass
class BranchResult:
    """分支执行结果"""
    branch_id: str
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time: float = 0.0


@dataclass
class ParallelNodeConfig:
    """并行节点配置"""
    branches: List[Dict[str, Any]] = field(default_factory=list)
    strategy: ParallelStrategy = ParallelStrategy.ALL
    timeout: float = 300.0  # 总超时时间
    fail_fast: bool = False  # 是否在第一个失败时停止
    max_concurrent: int = 10  # 最大并发数


class ParallelNode:
    """
    并行执行节点
    Sprint 18: 工作流节点扩展

    支持:
    - 多分支并行执行
    - 多种完成策略（全部/任意/多数）
    - 超时控制
    - 错误处理
    """

    node_type = "parallel"
    name = "ParallelNode"
    description = "并行执行多个分支任务"

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化并行节点

        Args:
            config: 节点配置
                - branches: 分支定义列表
                - strategy: 完成策略
                - timeout: 超时时间
                - fail_fast: 快速失败
        """
        self.config = ParallelNodeConfig(
            branches=config.get("branches", []),
            strategy=ParallelStrategy(config.get("strategy", "all")),
            timeout=config.get("timeout", 300.0),
            fail_fast=config.get("fail_fast", False),
            max_concurrent=config.get("max_concurrent", 10),
        ) if config else ParallelNodeConfig()

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any] = None,
        executor = None
    ) -> Dict[str, Any]:
        """
        执行并行节点

        Args:
            input_data: 输入数据
            context: 执行上下文
            executor: 工作流执行器（用于执行分支）

        Returns:
            执行结果
        """
        branches = self.config.branches
        if not branches:
            return {
                "success": True,
                "results": [],
                "message": "No branches to execute"
            }

        logger.info(f"Starting parallel execution with {len(branches)} branches")

        # 创建信号量限制并发
        semaphore = asyncio.Semaphore(self.config.max_concurrent)

        async def execute_branch(branch: Dict[str, Any]) -> BranchResult:
            """执行单个分支"""
            branch_id = branch.get("id", f"branch_{branches.index(branch)}")
            import time
            start_time = time.time()

            async with semaphore:
                try:
                    # 分支可以是节点列表或子工作流
                    if "workflow_id" in branch:
                        # 执行子工作流
                        if executor:
                            result = await executor.execute_subworkflow(
                                branch["workflow_id"],
                                input_data,
                                context
                            )
                        else:
                            result = {"error": "No executor provided for subworkflow"}
                    elif "nodes" in branch:
                        # 执行节点列表
                        if executor:
                            result = await executor.execute_nodes(
                                branch["nodes"],
                                input_data,
                                context
                            )
                        else:
                            result = {"error": "No executor provided for nodes"}
                    else:
                        # 直接返回分支数据
                        result = branch.get("data", {})

                    execution_time = time.time() - start_time
                    return BranchResult(
                        branch_id=branch_id,
                        success=True,
                        output=result,
                        execution_time=execution_time
                    )

                except Exception as e:
                    execution_time = time.time() - start_time
                    logger.error(f"Branch {branch_id} failed: {e}")
                    return BranchResult(
                        branch_id=branch_id,
                        success=False,
                        output=None,
                        error=str(e),
                        execution_time=execution_time
                    )

        try:
            # 根据策略执行
            if self.config.strategy == ParallelStrategy.ALL:
                results = await self._execute_all(branches, execute_branch)
            elif self.config.strategy == ParallelStrategy.ANY:
                results = await self._execute_any(branches, execute_branch)
            elif self.config.strategy == ParallelStrategy.MAJORITY:
                results = await self._execute_majority(branches, execute_branch)
            else:
                results = await self._execute_all(branches, execute_branch)

            # 汇总结果
            success_count = sum(1 for r in results if r.success)
            total_count = len(results)

            return {
                "success": success_count == total_count if self.config.strategy == ParallelStrategy.ALL else success_count > 0,
                "strategy": self.config.strategy.value,
                "total_branches": total_count,
                "success_count": success_count,
                "results": [
                    {
                        "branch_id": r.branch_id,
                        "success": r.success,
                        "output": r.output,
                        "error": r.error,
                        "execution_time": r.execution_time
                    }
                    for r in results
                ]
            }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"Parallel execution timeout after {self.config.timeout}s"
            }
        except Exception as e:
            logger.exception(f"Parallel execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _execute_all(self, branches, execute_branch) -> List[BranchResult]:
        """执行所有分支并等待全部完成"""
        tasks = [execute_branch(branch) for branch in branches]

        if self.config.fail_fast:
            # 快速失败模式
            results = []
            for coro in asyncio.as_completed(tasks, timeout=self.config.timeout):
                result = await coro
                results.append(result)
                if not result.success:
                    # 取消剩余任务
                    for task in tasks:
                        if hasattr(task, 'cancel'):
                            task.cancel()
                    break
            return results
        else:
            return await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.config.timeout
            )

    async def _execute_any(self, branches, execute_branch) -> List[BranchResult]:
        """执行所有分支，任意一个成功完成即可"""
        tasks = [asyncio.create_task(execute_branch(branch)) for branch in branches]
        completed_results = []

        try:
            done, pending = await asyncio.wait(
                tasks,
                timeout=self.config.timeout,
                return_when=asyncio.FIRST_COMPLETED
            )

            # 收集已完成的结果
            for task in done:
                result = task.result()
                completed_results.append(result)
                if result.success:
                    # 取消剩余任务
                    for p in pending:
                        p.cancel()
                    break

            return completed_results

        finally:
            # 确保所有任务被清理
            for task in tasks:
                if not task.done():
                    task.cancel()

    async def _execute_majority(self, branches, execute_branch) -> List[BranchResult]:
        """执行所有分支，多数成功即可"""
        tasks = [asyncio.create_task(execute_branch(branch)) for branch in branches]
        required = len(branches) // 2 + 1
        completed_results = []
        success_count = 0

        try:
            for coro in asyncio.as_completed(tasks, timeout=self.config.timeout):
                result = await coro
                completed_results.append(result)
                if result.success:
                    success_count += 1
                    if success_count >= required:
                        # 已达到多数，可以提前返回
                        for task in tasks:
                            if not task.done():
                                task.cancel()
                        break

            return completed_results

        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()

    def get_schema(self) -> Dict[str, Any]:
        """获取节点 schema"""
        return {
            "type": self.node_type,
            "name": self.name,
            "description": self.description,
            "inputs": {
                "branches": {
                    "type": "array",
                    "description": "分支定义列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "nodes": {"type": "array"},
                            "workflow_id": {"type": "string"},
                        }
                    }
                },
                "strategy": {
                    "type": "string",
                    "enum": ["all", "any", "majority"],
                    "default": "all"
                },
                "timeout": {"type": "number", "default": 300},
                "fail_fast": {"type": "boolean", "default": False},
            },
            "outputs": {
                "success": {"type": "boolean"},
                "results": {"type": "array"},
            }
        }
