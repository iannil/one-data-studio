"""
Mock vLLM 服务
模拟 LLM 推理服务的行为
"""

import pytest
import json
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass, field
from unittest.mock import Mock


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str
    content: str


@dataclass
class ChatCompletionResponse:
    """聊天完成响应"""
    id: str
    object: str = "chat.completion"
    created: int = 1234567890
    model: str = "gpt-4o-mini"
    choices: List[Dict] = field(default_factory=list)
    usage: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'object': self.object,
            'created': self.created,
            'model': self.model,
            'choices': self.choices,
            'usage': self.usage
        }


@dataclass
class EmbeddingResponse:
    """向量嵌入响应"""
    object: str = "list"
    data: List[Dict] = field(default_factory=list)
    model: str = "text-embedding-ada-002"
    usage: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'object': self.object,
            'data': self.data,
            'model': self.model,
            'usage': self.usage
        }


class MockVLLMClient:
    """
    Mock vLLM 客户端

    模拟 LLM 服务的响应行为，支持:
    - 聊天补全
    - 流式响应
    - 向量嵌入生成
    - 函数调用
    """

    # 预设响应模板
    RESPONSE_TEMPLATES = {
        # 表描述相关
        'table_description': {
            'users': '这是一个用户信息表，存储平台注册用户的基本资料，包括用户名、联系方式、注册时间等。',
            'orders': '这是订单表，记录用户的交易订单信息，包括订单金额、状态、支付方式等。',
            'products': '这是产品表，存储商品的基本信息，包括名称、价格、库存等。',
            'default': '这是一个数据表，存储业务相关数据。'
        },
        # 列描述相关
        'column_description': {
            'id': '主键，唯一标识每条记录',
            'user_id': '用户ID，关联用户表的外键',
            'username': '用户名，用户的登录名称',
            'phone': '手机号码，用户联系方式',
            'id_card': '身份证号，用户身份证明',
            'email': '电子邮箱，用户联系方式',
            'created_at': '创建时间，记录创建时间戳',
            'updated_at': '更新时间，记录最后修改时间戳',
            'amount': '金额，交易金额数值',
            'status': '状态，记录当前状态',
        },
        # 敏感数据识别
        'sensitive_detection': {
            'phone': {'is_sensitive': True, 'type': 'PII', 'confidence': 0.95},
            'mobile': {'is_sensitive': True, 'type': 'PII', 'confidence': 0.95},
            'id_card': {'is_sensitive': True, 'type': 'PII', 'confidence': 0.98},
            'idcard': {'is_sensitive': True, 'type': 'PII', 'confidence': 0.98},
            'identity': {'is_sensitive': True, 'type': 'PII', 'confidence': 0.90},
            'bank_card': {'is_sensitive': True, 'type': 'FINANCIAL', 'confidence': 0.95},
            'cardno': {'is_sensitive': True, 'type': 'FINANCIAL', 'confidence': 0.85},
            'email': {'is_sensitive': True, 'type': 'PII', 'confidence': 0.90},
            'mail': {'is_sensitive': True, 'type': 'PII', 'confidence': 0.88},
            'password': {'is_sensitive': True, 'type': 'CREDENTIAL', 'confidence': 0.99},
            'passwd': {'is_sensitive': True, 'type': 'CREDENTIAL', 'confidence': 0.99},
            'secret': {'is_sensitive': True, 'type': 'CREDENTIAL', 'confidence': 0.95},
            'token': {'is_sensitive': True, 'type': 'CREDENTIAL', 'confidence': 0.93},
        },
        # SQL 生成
        'sql_generation': {
            'default': 'SELECT * FROM users WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 MONTH)'
        },
        # RAG 回答
        'rag_answer': {
            'default': '根据检索到的相关文档，这是问题的答案。具体情况请参考相关政策文档。'
        },
        # ETL 清洗建议
        'etl_cleaning': {
            'null_handling': '建议删除缺失率超过30%的记录，其余用均值填充',
            'deduplication': '建议根据主键进行去重',
            'format_standardization': '建议统一日期格式为 YYYY-MM-DD',
            'outlier_detection': '建议使用3σ原则检测异常值'
        }
    }

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.call_history: List[Dict] = []
        self._request_count = 0
        self._response_delay = 0  # 模拟延迟（秒）

    def set_response_delay(self, delay: float):
        """设置响应延迟"""
        self._response_delay = delay

    async def _delay(self):
        """模拟延迟"""
        if self._response_delay > 0:
            await asyncio.sleep(self._response_delay)

    def _record_call(self, method: str, **kwargs):
        """记录调用历史"""
        self._request_count += 1
        self.call_history.append({
            'request_id': self._request_count,
            'method': method,
            'params': kwargs,
            'timestamp': asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0
        })

    def _get_template_response(self, category: str, key: str = None, default: Any = None) -> Any:
        """获取预设响应"""
        templates = self.RESPONSE_TEMPLATES.get(category, {})
        if key and key in templates:
            return templates[key]
        return templates.get('default', default)

    async def chat_completion(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False,
        functions: Optional[List[Dict]] = None
    ) -> ChatCompletionResponse:
        """
        模拟聊天补全接口

        Args:
            messages: 聊天消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            stream: 是否流式返回
            functions: 函数定义列表

        Returns:
            ChatCompletionResponse: 聊天响应
        """
        await self._delay()

        self._record_call(
            'chat_completion',
            messages=messages,
            model=model or self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            functions=functions
        )

        last_message = messages[-1].content if messages else ""
        response_content = self._generate_chat_response(last_message, functions)

        response = ChatCompletionResponse(
            id=f"chatcmpl-{self._request_count}",
            model=model or self.model,
            choices=[{
                'index': 0,
                'message': {
                    'role': 'assistant',
                    'content': response_content,
                    'function_call': None
                },
                'finish_reason': 'stop'
            }],
            usage={
                'prompt_tokens': sum(len(m.content) for m in messages) // 4,
                'completion_tokens': len(response_content) // 4,
                'total_tokens': (sum(len(m.content) for m in messages) + len(response_content)) // 4
            }
        )

        return response

    def _generate_chat_response(self, prompt: str, functions: Optional[List[Dict]] = None) -> str:
        """生成聊天响应"""
        # 检查是否是表描述请求
        if any(keyword in prompt.lower() for keyword in ['表描述', 'table description', '描述表']):
            for table_name, desc in self.RESPONSE_TEMPLATES['table_description'].items():
                if table_name in prompt and table_name != 'default':
                    return f"表 {table_name}：{desc}"
            return self.RESPONSE_TEMPLATES['table_description']['default']

        # 检查是否是列描述请求
        if any(keyword in prompt.lower() for keyword in ['列描述', 'column description', '描述列']):
            for col_name, desc in self.RESPONSE_TEMPLATES['column_description'].items():
                if col_name in prompt.lower():
                    return desc
            return "这是数据表的列字段，存储相关业务数据。"

        # 检查是否是敏感数据识别请求
        if any(keyword in prompt.lower() for keyword in ['敏感', 'sensitive', '识别']):
            column_name = self._extract_column_name(prompt)
            if column_name:
                result = self._get_template_response('sensitive_detection', column_name.lower())
                if result:
                    return json.dumps(result, ensure_ascii=False)
            return json.dumps({'is_sensitive': False, 'confidence': 0.1}, ensure_ascii=False)

        # 检查是否是 SQL 生成请求
        if any(keyword in prompt.lower() for keyword in ['sql', '查询', '生成sql']):
            return self.RESPONSE_TEMPLATES['sql_generation']['default']

        # 检查是否是 ETL 清洗建议
        if any(keyword in prompt.lower() for keyword in ['etl', '清洗', 'cleaning', '缺失值']):
            recommendations = []
            for key, value in self.RESPONSE_TEMPLATES['etl_cleaning'].items():
                recommendations.append(f"{key}: {value}")
            return "\n".join(recommendations)

        # 默认响应
        return self.RESPONSE_TEMPLATES['rag_answer']['default']

    def _extract_column_name(self, prompt: str) -> Optional[str]:
        """从提示中提取列名"""
        # 简单的列名提取逻辑
        keywords = ['phone', 'mobile', 'id_card', 'idcard', 'identity',
                   'bank_card', 'cardno', 'email', 'mail', 'password',
                   'passwd', 'secret', 'token']
        prompt_lower = prompt.lower()
        for keyword in keywords:
            if keyword in prompt_lower:
                return keyword
        return None

    async def chat_completion_stream(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        模拟流式聊天补全

        Args:
            messages: 聊天消息列表
            model: 模型名称
            **kwargs: 其他参数

        Yields:
            str: 流式响应片段
        """
        await self._delay()
        self._record_call('chat_completion_stream', messages=messages, model=model)

        response = await self.chat_completion(messages, model, **kwargs)
        content = response.choices[0]['message']['content']

        # 模拟流式返回，每次返回几个字符
        chunk_size = 10
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i + chunk_size]
            yield chunk
            await asyncio.sleep(0.01)  # 模拟网络延迟

    async def embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None,
        dimension: int = 1536
    ) -> EmbeddingResponse:
        """
        模拟向量嵌入生成

        Args:
            texts: 输入文本列表
            model: 模型名称
            dimension: 向量维度

        Returns:
            EmbeddingResponse: 向量嵌入响应
        """
        await self._delay()
        self._record_call('embeddings', texts=texts, model=model, count=len(texts))

        # 生成固定格式的 mock 向量
        embeddings = []
        for i, text in enumerate(texts):
            # 基于文本内容生成"伪随机"向量
            vector = self._generate_mock_vector(text, dimension)
            embeddings.append({
                'object': 'embedding',
                'embedding': vector,
                'index': i
            })

        return EmbeddingResponse(
            data=embeddings,
            model=model or "text-embedding-ada-002",
            usage={
                'prompt_tokens': sum(len(text) for text in texts) // 4,
                'total_tokens': sum(len(text) for text in texts) // 4
            }
        )

    def _generate_mock_vector(self, text: str, dimension: int) -> List[float]:
        """生成 mock 向量"""
        # 基于文本的哈希值生成确定性的向量
        hash_val = hash(text)
        vector = []
        for i in range(dimension):
            # 使用简单的伪随机算法生成向量元素
            val = ((hash_val + i * 1007) % 10000) / 10000 - 0.5
            # 归一化到合理范围
            vector.append(float(val))

        return vector

    def get_call_history(self) -> List[Dict]:
        """获取调用历史"""
        return self.call_history

    def get_call_count(self) -> int:
        """获取调用次数"""
        return self._request_count

    def reset(self):
        """重置客户端状态"""
        self.call_history.clear()
        self._request_count = 0


@pytest.fixture
def mock_vllm_client():
    """Mock vLLM 客户端 fixture"""
    client = MockVLLMClient()
    return client
