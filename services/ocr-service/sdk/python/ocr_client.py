"""
OCR服务Python客户端SDK
简化OCR服务调用，提供类型提示和错误处理
"""

from typing import Optional, Dict, List, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import requests
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DocumentType(str, Enum):
    """文档类型枚举"""
    INVOICE = "invoice"
    CONTRACT = "contract"
    PURCHASE_ORDER = "purchase_order"
    DELIVERY_NOTE = "delivery_note"
    QUOTATION = "quotation"
    RECEIPT = "receipt"
    REPORT = "report"
    TABLE = "table"
    GENERAL = "general"
    AUTO = "auto"


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ExtractionResult:
    """提取结果"""
    task_id: str
    document_type: str
    status: TaskStatus
    structured_data: Dict[str, Any] = field(default_factory=dict)
    raw_text: Optional[str] = None
    tables: List[Dict] = field(default_factory=list)
    confidence_score: float = 0.0
    validation_issues: List[Dict] = field(default_factory=list)
    cross_field_validation: Dict = field(default_factory=dict)
    layout_info: Dict = field(default_factory=dict)
    completeness: Dict = field(default_factory=dict)
    error_message: Optional[str] = None

    def is_valid(self) -> bool:
        """检查提取结果是否有效"""
        return (
            self.status == TaskStatus.COMPLETED and
            self.confidence_score > 0.7 and
            not self.cross_field_validation.get("errors")
        )

    def get_field(self, key: str, default=None):
        """获取字段值"""
        return self.structured_data.get(key, default)


@dataclass
class Template:
    """提取模板"""
    id: str
    name: str
    template_type: str
    category: Optional[str] = None
    is_active: bool = True
    extraction_rules: Dict = field(default_factory=dict)


class OCRClientError(Exception):
    """OCR客户端错误基类"""
    pass


class ServiceUnavailableError(OCRClientError):
    """服务不可用错误"""
    pass


class TaskFailedError(OCRClientError):
    """任务处理失败错误"""
    def __init__(self, task_id: str, message: str):
        self.task_id = task_id
        super().__init__(f"Task {task_id} failed: {message}")


class OCRClient:
    """
    OCR服务客户端

    示例:
        client = OCRClient("http://localhost:8007")

        # 创建任务
        result = client.extract("document.pdf", DocumentType.INVOICE)
        print(result.get_field("total_amount"))

        # 批量处理
        results = client.extract_batch(["doc1.pdf", "doc2.pdf"])
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8007",
        api_version: str = "v1",
        timeout: int = 300,
        poll_interval: int = 2
    ):
        """
        初始化客户端

        Args:
            base_url: 服务基础URL
            api_version: API版本
            timeout: 超时时间（秒）
            poll_interval: 轮询间隔（秒）
        """
        self.base_url = base_url.rstrip("/")
        self.api_prefix = f"/api/{api_version}/ocr"
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.session = requests.Session()

    def _url(self, path: str) -> str:
        """构建完整URL"""
        return f"{self.base_url}{self.api_prefix}{path}"

    def health_check(self) -> Dict:
        """
        健康检查

        Returns:
            健康状态信息
        """
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise ServiceUnavailableError(f"Service health check failed: {e}")

    def extract(
        self,
        file_path: Union[str, Path],
        document_type: Union[str, DocumentType] = DocumentType.AUTO,
        template_id: Optional[str] = None,
        wait_for_result: bool = True
    ) -> Union[str, ExtractionResult]:
        """
        提取文档信息

        Args:
            file_path: 文件路径
            document_type: 文档类型
            template_id: 自定义模板ID
            wait_for_result: 是否等待结果

        Returns:
            如果wait_for_result为True，返回ExtractionResult
            否则返回任务ID
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # 准备请求数据
        files = {'file': open(file_path, 'rb')}
        data = {
            'extraction_type': document_type.value if isinstance(document_type, DocumentType) else document_type
        }
        if template_id:
            data['template_id'] = template_id

        try:
            # 创建任务
            response = self.session.post(
                self._url("/tasks"),
                files=files,
                data=data,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            task_id = result.get('task_id')

            if not task_id:
                raise OCRClientError("No task ID in response")

            if wait_for_result:
                return self.get_result(task_id)
            else:
                return task_id

        except requests.RequestException as e:
            raise OCRClientError(f"Failed to create task: {e}")
        finally:
            files['file'].close()

    def extract_batch(
        self,
        file_paths: List[Union[str, Path]],
        document_type: Union[str, DocumentType] = DocumentType.AUTO
    ) -> List[ExtractionResult]:
        """
        批量提取文档信息

        Args:
            file_paths: 文件路径列表
            document_type: 文档类型

        Returns:
            提取结果列表
        """
        import time

        # 准备文件
        files = []
        for path in file_paths:
            p = Path(path)
            if p.exists():
                files.append(('files', open(p, 'rb')))

        if not files:
            raise FileNotFoundError("No valid files found")

        try:
            data = {
                'extraction_type': document_type.value if isinstance(document_type, DocumentType) else document_type
            }

            # 创建批量任务
            response = self.session.post(
                self._url("/tasks/batch"),
                files=files,
                data=data,
                timeout=60
            )
            response.raise_for_status()

            result = response.json()
            task_ids = result.get('task_ids', [])

            # 获取所有结果
            results = []
            for task_id in task_ids:
                try:
                    r = self.get_result(task_id)
                    results.append(r)
                except Exception as e:
                    logger.error(f"Failed to get result for task {task_id}: {e}")
                    # 添加失败结果
                    results.append(ExtractionResult(
                        task_id=task_id,
                        document_type=document_type.value if isinstance(document_type, DocumentType) else document_type,
                        status=TaskStatus.FAILED,
                        error_message=str(e)
                    ))

            return results

        finally:
            for _, f in files:
                f.close()

    def get_result(self, task_id: str, wait: bool = True) -> ExtractionResult:
        """
        获取任务结果

        Args:
            task_id: 任务ID
            wait: 是否等待完成

        Returns:
            提取结果
        """
        import time

        start_time = time.time()

        while True:
            try:
                response = self.session.get(
                    self._url(f"/tasks/{task_id}/result/enhanced"),
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()

                status = TaskStatus(data.get('status', 'pending'))

                if status == TaskStatus.COMPLETED:
                    return ExtractionResult(
                        task_id=task_id,
                        document_type=data.get('document_type', ''),
                        status=status,
                        structured_data=data.get('structured_data', {}),
                        raw_text=data.get('raw_text'),
                        tables=data.get('tables', []),
                        confidence_score=data.get('confidence_score', 0.0),
                        validation_issues=data.get('validation_issues', []),
                        cross_field_validation=data.get('cross_field_validation', {}),
                        layout_info=data.get('layout_info', {}),
                        completeness=data.get('completeness', {})
                    )

                elif status == TaskStatus.FAILED:
                    raise TaskFailedError(task_id, data.get('error_message', 'Unknown error'))

                elif not wait:
                    return ExtractionResult(
                        task_id=task_id,
                        document_type=data.get('document_type', ''),
                        status=status
                    )

                elif time.time() - start_time > self.timeout:
                    raise OCRClientError(f"Timeout waiting for task {task_id}")

                else:
                    time.sleep(self.poll_interval)

            except requests.RequestException as e:
                raise OCRClientError(f"Failed to get result: {e}")

    def detect_type(self, file_path: Union[str, Path]) -> Dict:
        """
        自动检测文档类型

        Args:
            file_path: 文件路径

        Returns:
            检测结果，包含类型和置信度
        """
        file_path = Path(file_path)

        with open(file_path, 'rb') as f:
            files = {'file': f}
            try:
                response = self.session.post(
                    self._url("/detect-type"),
                    files=files,
                    timeout=30
                )
                response.raise_for_status()
                return response.json()
            except requests.RequestException as e:
                raise OCRClientError(f"Failed to detect type: {e}")

    def list_templates(
        self,
        template_type: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[Template]:
        """
        获取模板列表

        Args:
            template_type: 模板类型筛选
            is_active: 是否只返回启用的模板

        Returns:
            模板列表
        """
        params = {}
        if template_type:
            params['template_type'] = template_type
        if is_active is not None:
            params['is_active'] = is_active

        try:
            response = self.session.get(
                self._url("/templates"),
                params=params,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            return [
                Template(
                    id=t['id'],
                    name=t['name'],
                    template_type=t['template_type'],
                    category=t.get('category'),
                    is_active=t['is_active'],
                    extraction_rules=t.get('extraction_rules', {})
                )
                for t in data
            ]
        except requests.RequestException as e:
            raise OCRClientError(f"Failed to list templates: {e}")

    def load_default_templates(self) -> bool:
        """
        加载默认模板

        Returns:
            是否成功
        """
        try:
            response = self.session.post(
                self._url("/templates/load-defaults"),
                timeout=30
            )
            response.raise_for_status()
            return True
        except requests.RequestException:
            return False

    def get_supported_types(self) -> Dict[str, str]:
        """
        获取支持的文档类型

        Returns:
            文档类型映射
        """
        try:
            response = self.session.get(
                self._url("/templates/types"),
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise OCRClientError(f"Failed to get types: {e}")

    def close(self):
        """关闭客户端"""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 便捷函数
def extract_document(
    file_path: Union[str, Path],
    api_url: str = "http://localhost:8007",
    document_type: Union[str, DocumentType] = DocumentType.AUTO
) -> ExtractionResult:
    """
    便捷函数：提取单个文档

    Args:
        file_path: 文件路径
        api_url: API地址
        document_type: 文档类型

    Returns:
        提取结果
    """
    with OCRClient(api_url) as client:
        return client.extract(file_path, document_type)
