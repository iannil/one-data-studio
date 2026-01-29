"""
数据库初始化脚本
Sprint 4.2: 创建表并加载示例数据
"""

import logging
import os
import sys

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from models import Base, engine, SessionLocal, Workflow, Conversation, Message

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def init_database():
    """初始化数据库：创建表和加载示例数据"""
    logger.info("开始初始化 Agent 数据库...")

    # 创建所有表
    logger.info("创建数据库表...")
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表创建完成")

    # 加载示例数据
    logger.info("加载示例数据...")
    db = SessionLocal()
    try:
        # 检查是否已有数据
        existing_workflow = db.query(Workflow).first()
        if existing_workflow:
            logger.info("数据库已有数据，跳过示例数据加载")
            return

        # 创建示例工作流
        workflows = [
            Workflow(
                workflow_id="wf-001",
                name="知识问答助手",
                description="基于 RAG 的智能问答",
                type="rag",
                status="running",
                created_by="admin"
            ),
            Workflow(
                workflow_id="wf-002",
                name="数据分析助手",
                description="Text-to-SQL 数据分析",
                type="sql",
                status="stopped",
                created_by="admin"
            ),
        ]
        db.add_all(workflows)
        db.flush()

        # 创建示例会话
        conversation = Conversation(
            conversation_id="conv-001",
            user_id="admin",
            title="ONE-DATA-STUDIO 咨询",
            model="gpt-4o-mini"
        )
        db.add(conversation)
        db.flush()

        # 创建示例消息
        messages = [
            Message(
                message_id="msg-001",
                conversation_id="conv-001",
                role="user",
                content="ONE-DATA-STUDIO 是什么？",
                tokens=20
            ),
            Message(
                message_id="msg-002",
                conversation_id="conv-001",
                role="assistant",
                content="ONE-DATA-STUDIO 是一个融合了 Data（数据治理）、Model（模型训练）、Agent（应用编排）的企业级 AI 平台。",
                tokens=80
            ),
        ]
        db.add_all(messages)

        db.commit()
        logger.info("示例数据加载完成")

    except Exception as e:
        db.rollback()
        logger.error(f"初始化失败: {e}")
        raise
    finally:
        db.close()

    logger.info("数据库初始化完成!")


if __name__ == "__main__":
    init_database()
