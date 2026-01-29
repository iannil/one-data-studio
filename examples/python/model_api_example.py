#!/usr/bin/env python3
"""
Cube 模型服务示例
演示如何调用 OpenAI 兼容的模型推理 API
"""

import requests
from typing import List, Dict, Optional


class CubeModelClient:
    """Cube 模型服务客户端（OpenAI 兼容）"""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    def list_models(self) -> List[Dict]:
        """列出可用模型"""
        response = self.session.get(f"{self.base_url}/v1/models")
        response.raise_for_status()
        return response.json()["data"]

    def chat_completion(
        self,
        messages: List[Dict],
        model: str = "Qwen/Qwen-0.5B-Chat",
        temperature: float = 0.7,
        max_tokens: int = 500,
        stream: bool = False,
    ) -> Dict:
        """聊天补全"""
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        response = self.session.post(
            f"{self.base_url}/v1/chat/completions", json=payload
        )
        response.raise_for_status()
        return response.json()

    def text_completion(
        self,
        prompt: str,
        model: str = "Qwen/Qwen-0.5B-Chat",
        temperature: float = 0.7,
        max_tokens: int = 100,
    ) -> Dict:
        """文本补全"""
        payload = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        response = self.session.post(f"{self.base_url}/v1/completions", json=payload)
        response.raise_for_status()
        return response.json()

    def get_embeddings(
        self, texts: List[str], model: str = "bge-base-zh"
    ) -> List[List[float]]:
        """获取文本嵌入向量"""
        payload = {"model": model, "input": texts}
        response = self.session.post(f"{self.base_url}/v1/embeddings", json=payload)
        response.raise_for_status()
        return [item["embedding"] for item in response.json()["data"]]


class ChatHelper:
    """聊天助手类 - 管理对话上下文"""

    def __init__(self, client: CubeModelClient, system_prompt: str = ""):
        self.client = client
        self.messages = []
        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})

    def chat(self, user_message: str) -> str:
        """发送消息并获取回复"""
        self.messages.append({"role": "user", "content": user_message})

        response = self.client.chat_completion(self.messages)
        assistant_message = response["choices"][0]["message"]["content"]

        self.messages.append({"role": "assistant", "content": assistant_message})
        return assistant_message

    def clear_history(self):
        """清空对话历史"""
        self.messages = []

    def get_history(self) -> List[Dict]:
        """获取对话历史"""
        return self.messages.copy()


def main():
    """示例用法"""
    # 初始化客户端
    client = CubeModelClient("http://localhost:8000")

    # 1. 列出可用模型
    print("=== 可用模型 ===")
    models = client.list_models()
    for model in models:
        print(f"  - {model['id']} (owned_by: {model['owned_by']})")

    # 2. 单次对话
    print("\n=== 单次对话 ===")
    response = client.chat_completion(
        messages=[{"role": "user", "content": "用一句话介绍人工智能。"}],
        max_tokens=100,
    )
    print(f"回复: {response['choices'][0]['message']['content']}")
    print(f"Token 使用: {response['usage']}")

    # 3. 多轮对话
    print("\n=== 多轮对话 ===")
    helper = ChatHelper(
        client, system_prompt="你是一个专业的技术顾问，请简洁专业地回答问题。"
    )

    questions = [
        "什么是 Kubernetes？",
        "它和 Docker 有什么区别？",
        "能推荐一些学习资源吗？",
    ]

    for q in questions:
        print(f"\n问题: {q}")
        answer = helper.chat(q)
        print(f"回答: {answer}")

    # 4. 文本补全
    print("\n=== 文本补全 ===")
    response = client.text_completion(prompt="机器学习是", max_tokens=50)
    print(f"补全: {prompt}{response['choices'][0]['text']}")

    # 5. 向量嵌入
    print("\n=== 向量嵌入 ===")
    texts = ["人工智能改变世界", "机器学习是AI的子集"]
    embeddings = client.get_embeddings(texts)
    for i, (text, emb) in enumerate(zip(texts, embeddings)):
        print(f"  '{text}' -> 向量维度: {len(emb)}")


if __name__ == "__main__":
    main()
