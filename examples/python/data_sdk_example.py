#!/usr/bin/env python3
"""
Alldata SDK 示例
演示如何使用 Alldata 数据集 API
"""

import requests
from typing import Dict, List, Optional


class AlldataClient:
    """Alldata API 客户端"""

    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

    def health(self) -> Dict:
        """健康检查"""
        response = self.session.get(f"{self.base_url}/api/v1/health")
        response.raise_for_status()
        return response.json()

    def list_datasets(
        self, tags: Optional[str] = None, status: Optional[str] = None
    ) -> List[Dict]:
        """获取数据集列表"""
        params = {}
        if tags:
            params["tags"] = tags
        if status:
            params["status"] = status

        response = self.session.get(f"{self.base_url}/api/v1/datasets", params=params)
        response.raise_for_status()
        return response.json()["data"]

    def get_dataset(self, dataset_id: str) -> Dict:
        """获取数据集详情"""
        response = self.session.get(f"{self.base_url}/api/v1/datasets/{dataset_id}")
        response.raise_for_status()
        return response.json()["data"]

    def create_dataset(
        self,
        name: str,
        storage_path: str,
        format: str = "csv",
        description: str = "",
        tags: Optional[List[str]] = None,
        schema: Optional[Dict] = None,
    ) -> Dict:
        """注册新数据集"""
        payload = {
            "name": name,
            "storage_path": storage_path,
            "format": format,
            "description": description,
            "tags": tags or [],
            "schema": schema or {},
        }
        response = self.session.post(
            f"{self.base_url}/api/v1/datasets", json=payload
        )
        response.raise_for_status()
        return response.json()["data"]

    def update_dataset(self, dataset_id: str, **kwargs) -> Dict:
        """更新数据集"""
        response = self.session.put(
            f"{self.base_url}/api/v1/datasets/{dataset_id}", json=kwargs
        )
        response.raise_for_status()
        return response.json()["data"]

    def delete_dataset(self, dataset_id: str) -> bool:
        """删除数据集"""
        response = self.session.delete(f"{self.base_url}/api/v1/datasets/{dataset_id}")
        response.raise_for_status()
        return True

    def get_credentials(self, dataset_id: str, purpose: str = "training") -> Dict:
        """获取数据集访问凭证"""
        payload = {"purpose": purpose, "duration_seconds": 3600}
        response = self.session.post(
            f"{self.base_url}/api/v1/datasets/{dataset_id}/credentials", json=payload
        )
        response.raise_for_status()
        return response.json()["data"]


def main():
    """示例用法"""
    # 初始化客户端
    client = AlldataClient("http://localhost:8080")

    # 1. 健康检查
    print("=== 健康检查 ===")
    health = client.health()
    print(f"服务状态: {health['message']}")

    # 2. 列出所有数据集
    print("\n=== 数据集列表 ===")
    datasets = client.list_datasets()
    for ds in datasets:
        print(f"  - {ds['dataset_id']}: {ds['name']} ({ds['format']})")

    # 3. 创建新数据集
    print("\n=== 创建数据集 ===")
    new_dataset = client.create_dataset(
        name="customer_churn_data_v1.0",
        storage_path="s3://ml-data/customer-churn/",
        format="parquet",
        description="客户流失预测训练数据",
        tags=["ml", "customer", "churn"],
        schema={
            "columns": [
                {"name": "customer_id", "type": "INT64", "description": "客户ID"},
                {"name": "age", "type": "INT32", "description": "年龄"},
                {"name": "churn", "type": "BOOLEAN", "description": "是否流失"},
            ]
        },
    )
    print(f"创建成功: {new_dataset['dataset_id']}")

    # 4. 获取数据集详情
    print("\n=== 数据集详情 ===")
    dataset = client.get_dataset(new_dataset["dataset_id"])
    print(f"名称: {dataset['name']}")
    print(f"路径: {dataset['storage_path']}")
    print(f"标签: {', '.join(dataset['tags'])}")

    # 5. 获取访问凭证
    print("\n=== 访问凭证 ===")
    creds = client.get_credentials(new_dataset["dataset_id"])
    print(f"Endpoint: {creds['endpoint']}")
    print(f"Access Key: {creds['access_key']}")
    print(f"过期时间: {creds['expires_at']}")

    # 6. 清理
    print("\n=== 清理 ===")
    client.delete_dataset(new_dataset["dataset_id"])
    print("测试数据集已删除")


if __name__ == "__main__":
    main()
