#!/usr/bin/env python3
"""
ONE-DATA-STUDIO 测试数据初始化脚本

用途：为 E2E 测试创建必要的测试数据

功能：
- 创建测试用户（不同角色）
- 创建测试数据源
- 创建测试数据集
- 创建示例知识库
- 创建示例工作流
- 创建示例模型
"""

import os
import sys
import json
import time
import logging
from typing import Dict, Any, List

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载环境变量
ENV_FILE = os.path.join(os.path.dirname(__file__), '..', '.env.test')

def load_env():
    """加载测试环境变量"""
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        logger.info(f"已加载环境配置: {ENV_FILE}")
    else:
        logger.warning(f"环境配置文件不存在: {ENV_FILE}")

def get_mysql_connection():
    """获取 MySQL 数据库连接"""
    try:
        import pymysql
        return pymysql.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', '3306')),
            user=os.getenv('MYSQL_USER', 'onedata_test'),
            password=os.getenv('MYSQL_PASSWORD', 'test_password_123'),
            database=os.getenv('MYSQL_DATABASE', 'onedata_test'),
        )
    except ImportError:
        logger.error("pymysql 未安装，请运行: pip install pymysql")
        sys.exit(1)
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        sys.exit(1)

def get_redis_connection():
    """获取 Redis 连接"""
    try:
        import redis
        return redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            password=os.getenv('REDIS_PASSWORD', 'test_redis_password_123'),
            decode_responses=True,
        )
    except ImportError:
        logger.warning("redis 未安装，跳过 Redis 操作")
        return None
    except Exception as e:
        logger.warning(f"Redis 连接失败: {e}")
        return None

def http_request(method: str, url: str, data: Dict = None, headers: Dict = None) -> Dict:
    """发送 HTTP 请求"""
    try:
        import requests
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, params=data, timeout=10)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=headers, json=data, timeout=10)
        elif method.upper() == 'PUT':
            response = requests.put(url, headers=headers, json=data, timeout=10)
        elif method.upper() == 'DELETE':
            response = requests.delete(url, headers=headers, json=data, timeout=10)
        else:
            raise ValueError(f"不支持的 HTTP 方法: {method}")

        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP 请求失败: {e}")
        return {}

def create_test_users(db_conn):
    """创建测试用户"""
    logger.info("创建测试用户...")

    cursor = db_conn.cursor()

    # 测试用户数据
    users = [
        {
            'username': os.getenv('TEST_USER_USERNAME', 'testuser'),
            'email': os.getenv('TEST_USER_EMAIL', 'testuser@example.com'),
            'password': os.getenv('TEST_USER_PASSWORD', 'Test1234!'),
            'role': 'user',
        },
        {
            'username': os.getenv('TEST_DEVELOPER_USERNAME', 'testdev'),
            'email': os.getenv('TEST_DEVELOPER_EMAIL', 'testdev@example.com'),
            'password': os.getenv('TEST_DEVELOPER_PASSWORD', 'Dev1234!'),
            'role': 'developer',
        },
        {
            'username': os.getenv('TEST_ADMIN_USERNAME', 'testadmin'),
            'email': os.getenv('TEST_ADMIN_EMAIL', 'testadmin@example.com'),
            'password': os.getenv('TEST_ADMIN_PASSWORD', 'Admin1234!'),
            'role': 'admin',
        },
        {
            'username': os.getenv('TEST_VIEWER_USERNAME', 'testviewer'),
            'email': os.getenv('TEST_VIEWER_EMAIL', 'testviewer@example.com'),
            'password': os.getenv('TEST_VIEWER_PASSWORD', 'Viewer1234!'),
            'role': 'viewer',
        },
    ]

    for user in users:
        try:
            # 检查用户是否已存在
            cursor.execute("SELECT id FROM users WHERE username = %s", (user['username'],))
            if cursor.fetchone():
                logger.info(f"  用户 {user['username']} 已存在，跳过")
                continue

            # 插入用户（密码应该是哈希后的，这里简化处理）
            cursor.execute(
                """INSERT INTO users (username, email, password_hash, role, created_at)
                   VALUES (%s, %s, %s, %s, NOW())""",
                (user['username'], user['email'], f"hashed_{user['password']}", user['role'])
            )
            logger.info(f"  ✓ 创建用户: {user['username']} ({user['role']})")
        except Exception as e:
            logger.warning(f"  创建用户失败 {user['username']}: {e}")

    db_conn.commit()
    cursor.close()

def create_test_datasource(db_conn):
    """创建测试数据源"""
    logger.info("创建测试数据源...")

    cursor = db_conn.cursor()

    try:
        # 检查是否已存在
        cursor.execute("SELECT id FROM datasources WHERE name = 'e2e_test_datasource'")
        if cursor.fetchone():
            logger.info("  测试数据源已存在，跳过")
            return

        cursor.execute(
            """INSERT INTO datasources (name, type, host, port, database_name, username, password, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())""",
            ('e2e_test_datasource', 'mysql', 'localhost', 3306,
             os.getenv('MYSQL_DATABASE', 'onedata_test'),
             os.getenv('MYSQL_USER', 'onedata_test'),
             os.getenv('MYSQL_PASSWORD', 'test_password_123'))
        )
        logger.info("  ✓ 创建测试数据源: e2e_test_datasource")
    except Exception as e:
        logger.warning(f"  创建测试数据源失败: {e}")
    finally:
        db_conn.commit()
        cursor.close()

def create_test_dataset(db_conn):
    """创建测试数据集"""
    logger.info("创建测试数据集...")

    cursor = db_conn.cursor()

    try:
        # 检查是否已存在
        cursor.execute("SELECT id FROM datasets WHERE name = 'e2e_test_dataset'")
        if cursor.fetchone():
            logger.info("  测试数据集已存在，跳过")
            return

        cursor.execute(
            """INSERT INTO datasets (name, description, datasource_id, table_name, row_count, created_at)
               VALUES (%s, %s, 1, %s, %s, NOW())""",
            ('e2e_test_dataset', 'E2E测试数据集', 'test_table', 1000)
        )
        logger.info("  ✓ 创建测试数据集: e2e_test_dataset")
    except Exception as e:
        logger.warning(f"  创建测试数据集失败: {e}")
    finally:
        db_conn.commit()
        cursor.close()

def create_test_knowledge_base():
    """创建测试知识库"""
    logger.info("创建测试知识库...")

    api_url = os.getenv('AGENT_API_URL', os.getenv('agent_API_URL', 'http://localhost:8000'))
    url = f"{api_url}/api/v1/knowledge"

    data = {
        'name': 'e2e_test_knowledge',
        'description': 'E2E测试知识库',
        'embedding_model': 'text-embedding-ada-002',
    }

    result = http_request('POST', url, data)

    if result and result.get('code') == 0:
        logger.info("  ✓ 创建测试知识库: e2e_test_knowledge")
    else:
        logger.warning(f"  创建测试知识库失败: {result}")

def create_test_workflow():
    """创建测试工作流"""
    logger.info("创建测试工作流...")

    api_url = os.getenv('AGENT_API_URL', os.getenv('agent_API_URL', 'http://localhost:8000'))
    url = f"{api_url}/api/v1/workflows"

    data = {
        'name': 'e2e_test_workflow',
        'description': 'E2E测试工作流',
        'type': 'rag',
        'config': {
            'nodes': [
                {
                    'id': 'input',
                    'type': 'input',
                    'position': {'x': 100, 'y': 100},
                },
                {
                    'id': 'llm',
                    'type': 'llm',
                    'position': {'x': 300, 'y': 100},
                    'data': {'model': 'gpt-3.5-turbo'},
                },
                {
                    'id': 'output',
                    'type': 'output',
                    'position': {'x': 500, 'y': 100},
                },
            ],
            'edges': [
                {'source': 'input', 'target': 'llm'},
                {'source': 'llm', 'target': 'output'},
            ],
        },
    }

    result = http_request('POST', url, data)

    if result and result.get('code') == 0:
        logger.info("  ✓ 创建测试工作流: e2e_test_workflow")
    else:
        logger.warning(f"  创建测试工作流失败: {result}")

def create_test_model():
    """创建测试模型"""
    logger.info("创建测试模型...")

    api_url = os.getenv('MODEL_API_URL', os.getenv('CUBE_API_URL', 'http://localhost:8002'))
    url = f"{api_url}/api/v1/models"

    data = {
        'name': 'e2e_test_model',
        'version': '1.0.0',
        'description': 'E2E测试模型',
        'framework': 'pytorch',
        'task_type': 'classification',
    }

    result = http_request('POST', url, data)

    if result and result.get('code') == 0:
        logger.info("  ✓ 创建测试模型: e2e_test_model")
    else:
        logger.warning(f"  创建测试模型失败: {result}")

def cleanup_test_data(db_conn, redis_conn):
    """清理旧的测试数据（可选）"""
    if os.getenv('CLEANUP_TEST_DATA', 'false').lower() == 'true':
        logger.info("清理旧测试数据...")

        cursor = db_conn.cursor()

        try:
            # 删除测试用户
            for username in ['testuser', 'testdev', 'testadmin', 'testviewer']:
                cursor.execute("DELETE FROM users WHERE username = %s", (username,))

            # 删除测试数据源
            cursor.execute("DELETE FROM datasources WHERE name LIKE 'e2e_%'")

            # 删除测试数据集
            cursor.execute("DELETE FROM datasets WHERE name LIKE 'e2e_%'")

            db_conn.commit()
            logger.info("  ✓ 清理完成")
        except Exception as e:
            logger.warning(f"  清理失败: {e}")
        finally:
            cursor.close()

        # 清理 Redis 缓存
        if redis_conn:
            try:
                keys = redis_conn.keys('e2e:*')
                if keys:
                    redis_conn.delete(*keys)
                    logger.info("  ✓ 清理 Redis 缓存完成")
            except Exception as e:
                logger.warning(f"  清理 Redis 失败: {e}")

def wait_for_services():
    """等待所有服务就绪"""
    logger.info("等待服务就绪...")

    services = [
        ('Agent API', os.getenv('AGENT_API_URL', os.getenv('agent_API_URL', 'http://localhost:8000')) + '/api/v1/health'),
        ('Data API', os.getenv('DATA_API_URL', os.getenv('data_API_URL', 'http://localhost:8001')) + '/api/v1/health'),
        ('Model API', os.getenv('MODEL_API_URL', os.getenv('CUBE_API_URL', 'http://localhost:8002')) + '/api/v1/health'),
    ]

    for name, url in services:
        max_retries = 30
        for i in range(max_retries):
            try:
                result = http_request('GET', url)
                if result:
                    logger.info(f"  ✓ {name} 已就绪")
                    break
            except:
                if i < max_retries - 1:
                    time.sleep(2)
                else:
                    logger.warning(f"  {name} 未就绪，跳过")

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("ONE-DATA-STUDIO 测试数据初始化")
    logger.info("=" * 60)

    # 加载环境变量
    load_env()

    # 等待服务就绪
    wait_for_services()

    # 连接数据库
    db_conn = None
    redis_conn = None

    try:
        db_conn = get_mysql_connection()
        redis_conn = get_redis_connection()

        # 可选：清理旧数据
        # cleanup_test_data(db_conn, redis_conn)

        # 创建测试数据
        create_test_users(db_conn)
        create_test_datasource(db_conn)
        create_test_dataset(db_conn)
        create_test_knowledge_base()
        create_test_workflow()
        create_test_model()

        logger.info("")
        logger.info("=" * 60)
        logger.info("测试数据初始化完成！")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"初始化失败: {e}")
        sys.exit(1)
    finally:
        if db_conn:
            db_conn.close()

if __name__ == '__main__':
    main()
