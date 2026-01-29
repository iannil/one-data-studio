"""
Mock Kettle ETL 服务
模拟 Pentaho Data Integration (Kettle) 的行为
"""

import pytest
import asyncio
from unittest.mock import Mock
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import xml.etree.ElementTree as ET


class ETLStatus(Enum):
    """ETL任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class ETLJob:
    """ETL任务"""
    job_id: str
    job_name: str
    xml_content: str
    status: ETLStatus = ETLStatus.PENDING
    progress: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None

    # 执行统计
    input_rows: int = 0
    output_rows: int = 0
    error_rows: int = 0
    duration_seconds: float = 0


class MockKettleClient:
    """
    Mock Kettle 客户端

    模拟 Pentaho Data Integration (Kettle) ETL 工具的行为，支持:
    - 生成 Kettle 转换 XML
    - 提交和执行 ETL 任务
    - 查询任务状态
    - 获取执行报告
    """

    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port
        self.jobs: Dict[str, ETLJob] = {}
        self._job_counter = 1
        self._call_history: List[Dict] = []

        # 模拟任务执行配置
        self._execution_delay = 1.0  # 默认执行时间（秒）
        self._success_rate = 1.0  # 默认成功率

    def set_execution_delay(self, delay: float):
        """设置模拟执行延迟"""
        self._execution_delay = delay

    def set_success_rate(self, rate: float):
        """设置模拟成功率"""
        self._success_rate = max(0.0, min(1.0, rate))

    def _record_call(self, method: str, **kwargs):
        """记录调用历史"""
        self._call_history.append({
            'method': method,
            'params': kwargs,
            'timestamp': datetime.utcnow().isoformat()
        })

    def generate_transformation_xml(
        self,
        transformation_name: str,
        source_tables: List[str],
        target_table: str,
        steps: List[Dict[str, Any]]
    ) -> str:
        """
        生成 Kettle 转换 XML

        Args:
            transformation_name: 转换名称
            source_tables: 源表列表
            target_table: 目标表
            steps: 转换步骤列表

        Returns:
            Kettle XML 内容
        """
        self._record_call(
            'generate_transformation_xml',
            transformation_name=transformation_name,
            source_tables=source_tables,
            target_table=target_table,
            steps_count=len(steps)
        )

        # 创建 XML 根元素
        root = ET.Element('transformation')
        root.set('name', transformation_name)

        # 添加 info 节点
        info = ET.SubElement(root, 'info')
        name = ET.SubElement(info, 'name')
        name.text = transformation_name

        # 添加 step 节点
        steps_elem = ET.SubElement(root, 'step')
        for i, step in enumerate(steps):
            step_elem = ET.SubElement(steps_elem, 'step')
            step_elem.set('id', str(i + 1))
            step_elem.set('type', step.get('type', 'Dummy'))

            name_elem = ET.SubElement(step_elem, 'name')
            name_elem.text = step.get('name', f'Step_{i + 1}')

            # 添加步骤配置
            for key, value in step.items():
                if key not in ['type', 'name']:
                    config_elem = ET.SubElement(step_elem, key)
                    if isinstance(value, (dict, list)):
                        config_elem.text = str(value)
                    else:
                        config_elem.text = str(value)

        # 返回格式化的 XML
        return ET.tostring(root, encoding='unicode')

    def generate_job_xml(
        self,
        job_name: str,
        transformations: List[str],
        entries: List[Dict[str, Any]]
    ) -> str:
        """
        生成 Kettle 作业 XML

        Args:
            job_name: 作业名称
            transformations: 转换名称列表
            entries: 作业条目列表

        Returns:
            Kettle Job XML 内容
        """
        self._record_call(
            'generate_job_xml',
            job_name=job_name,
            transformations=transformations,
            entries_count=len(entries)
        )

        root = ET.Element('job')
        root.set('name', job_name)

        # 添加 entries
        entries_elem = ET.SubElement(root, 'entries')
        for i, entry in enumerate(entries):
            entry_elem = ET.SubElement(entries_elem, 'entry')
            entry_elem.set('id', str(i + 1))
            entry_elem.set('type', entry.get('type', 'Special'))

            name_elem = ET.SubElement(entry_elem, 'name')
            name_elem.text = entry.get('name', f'Entry_{i + 1}')

        return ET.tostring(root, encoding='unicode')

    async def submit_job(
        self,
        job_name: str,
        xml_content: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        提交 ETL 任务

        Args:
            job_name: 任务名称
            xml_content: Kettle XML 内容
            params: 任务参数

        Returns:
            提交结果
        """
        job_id = f"job_{self._job_counter:04d}"
        self._job_counter += 1

        self._record_call(
            'submit_job',
            job_id=job_id,
            job_name=job_name
        )

        job = ETLJob(
            job_id=job_id,
            job_name=job_name,
            xml_content=xml_content
        )
        self.jobs[job_id] = job

        return {
            'success': True,
            'job_id': job_id,
            'job_name': job_name,
            'status': job.status.value
        }

    async def start_job(self, job_id: str) -> Dict[str, Any]:
        """启动 ETL 任务"""
        self._record_call('start_job', job_id=job_id)

        if job_id not in self.jobs:
            return {'success': False, 'error': f'Job {job_id} not found'}

        job = self.jobs[job_id]
        job.status = ETLStatus.RUNNING
        job.start_time = datetime.utcnow()

        # 异步执行任务
        asyncio.create_task(self._execute_job(job_id))

        return {
            'success': True,
            'job_id': job_id,
            'status': job.status.value
        }

    async def _execute_job(self, job_id: str):
        """执行任务的内部方法"""
        await asyncio.sleep(self._execution_delay)

        if job_id not in self.jobs:
            return

        job = self.jobs[job_id]

        # 根据成功率决定任务是否成功
        import random
        if random.random() < self._success_rate:
            job.status = ETLStatus.COMPLETED
            job.progress = 100.0
            # 模拟处理行数
            job.input_rows = random.randint(10000, 100000)
            job.output_rows = int(job.input_rows * 0.98)
            job.error_rows = job.input_rows - job.output_rows
        else:
            job.status = ETLStatus.FAILED
            job.error_message = "模拟的执行失败"

        job.end_time = datetime.utcnow()
        job.duration_seconds = (
            job.end_time - job.start_time
        ).total_seconds() if job.start_time else 0

    async def stop_job(self, job_id: str) -> Dict[str, Any]:
        """停止 ETL 任务"""
        self._record_call('stop_job', job_id=job_id)

        if job_id not in self.jobs:
            return {'success': False, 'error': f'Job {job_id} not found'}

        job = self.jobs[job_id]
        if job.status == ETLStatus.RUNNING:
            job.status = ETLStatus.STOPPED
            job.end_time = datetime.utcnow()

        return {
            'success': True,
            'job_id': job_id,
            'status': job.status.value
        }

    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        self._record_call('get_job_status', job_id=job_id)

        if job_id not in self.jobs:
            return None

        job = self.jobs[job_id]
        return {
            'job_id': job.job_id,
            'job_name': job.job_name,
            'status': job.status.value,
            'progress': job.progress,
            'start_time': job.start_time.isoformat() if job.start_time else None,
            'end_time': job.end_time.isoformat() if job.end_time else None,
            'error_message': job.error_message
        }

    async def get_job_report(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取任务执行报告"""
        self._record_call('get_job_report', job_id=job_id)

        if job_id not in self.jobs:
            return None

        job = self.jobs[job_id]
        return {
            'job_id': job.job_id,
            'job_name': job.job_name,
            'status': job.status.value,
            'input_rows': job.input_rows,
            'output_rows': job.output_rows,
            'error_rows': job.error_rows,
            'success_rate': (job.output_rows / job.input_rows * 100) if job.input_rows > 0 else 0,
            'duration_seconds': job.duration_seconds,
            'error_message': job.error_message,
            'steps': [
                {
                    'name': 'Input',
                    'status': 'completed',
                    'rows': job.input_rows
                },
                {
                    'name': 'Cleaning',
                    'status': 'completed',
                    'rows': int(job.input_rows * 0.99)
                },
                {
                    'name': 'Masking',
                    'status': 'completed',
                    'rows': int(job.input_rows * 0.99)
                },
                {
                    'name': 'Output',
                    'status': 'completed',
                    'rows': job.output_rows
                }
            ]
        }

    async def list_jobs(self) -> List[Dict[str, Any]]:
        """列出所有任务"""
        self._record_call('list_jobs')

        return [
            {
                'job_id': job.job_id,
                'job_name': job.job_name,
                'status': job.status.value,
                'start_time': job.start_time.isoformat() if job.start_time else None
            }
            for job in self.jobs.values()
        ]

    def generate_cleaning_steps(
        self,
        null_handling: str = 'remove',
        deduplication: bool = True,
        format_standardization: bool = False
    ) -> List[Dict[str, Any]]:
        """
        生成数据清洗步骤配置

        Args:
            null_handling: 空值处理方式
            deduplication: 是否去重
            format_standardization: 是否格式标准化

        Returns:
            清洗步骤列表
        """
        steps = []

        if null_handling == 'remove':
            steps.append({
                'type': 'FilterRows',
                'name': 'RemoveNullRows',
                'condition': 'NOT ISNULL(field)'
            })
        elif null_handling == 'fill':
            steps.append({
                'type': 'AnalyticQuery',
                'name': 'FillNullWithDefault',
                'fill_type': 'mean'
            })

        if deduplication:
            steps.append({
                'type': 'Unique',
                'name': 'RemoveDuplicates',
                'compare_fields': ['id']
            })

        if format_standardization:
            steps.append({
                'type': 'SelectValues',
                'name': 'StandardizeFormats',
                'metadata': {
                    'date_format': 'yyyy-MM-dd',
                    'number_format': '#.##'
                }
            })

        return steps

    def generate_masking_steps(
        self,
        columns: List[str],
        strategy: str = 'partial_mask'
    ) -> List[Dict[str, Any]]:
        """
        生成数据脱敏步骤配置

        Args:
            columns: 需要脱敏的列
            strategy: 脱敏策略

        Returns:
            脱敏步骤列表
        """
        steps = []

        if strategy == 'partial_mask':
            script = """
# 手机号脱敏
if (field != null) {
    masked = field.substring(0, 3) + "****" + field.substring(7);
}
            """
        elif strategy == 'hash':
            script = """
# SHA256 哈希
import hashlib;
if (field != null) {
    hashed = hashlib.sha256(field.encode()).hexdigest();
}
            """
        else:
            script = "// 未定义的脱敏策略"

        steps.append({
            'type': 'ScriptValueMod',
            'name': 'MaskSensitiveData',
            'target_columns': columns,
            'script': script.strip(),
            'strategy': strategy
        })

        return steps

    def get_call_history(self) -> List[Dict]:
        """获取调用历史"""
        return self._call_history

    def reset(self):
        """重置客户端状态"""
        self.jobs.clear()
        self._job_counter = 1
        self._call_history.clear()


@pytest.fixture
def mock_kettle_client():
    """Mock Kettle 客户端 fixture"""
    client = MockKettleClient()
    # 设置较短的延迟用于测试
    client.set_execution_delay(0.1)
    return client


@pytest.fixture
async def mock_kettle_with_job(mock_kettle_client):
    """带有预创建任务的 Kettle fixture"""
    xml_content = mock_kettle_client.generate_transformation_xml(
        transformation_name="test_transformation",
        source_tables=["users"],
        target_table="users_clean",
        steps=[
            {'type': 'TableInput', 'name': 'Read from source'},
            {'type': 'FilterRows', 'name': 'Remove nulls'},
            {'type': 'Unique', 'name': 'Deduplicate'},
            {'type': 'TableOutput', 'name': 'Write to target'}
        ]
    )

    result = await mock_kettle_client.submit_job(
        job_name="test_job",
        xml_content=xml_content
    )

    await mock_kettle_client.start_job(result['job_id'])

    # 等待任务完成
    await asyncio.sleep(0.2)

    return mock_kettle_client, result['job_id']
