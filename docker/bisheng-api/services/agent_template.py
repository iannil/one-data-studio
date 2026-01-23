"""
Agent 模板服务
P1 - Agent 模板管理功能

提供 Agent 模板的 CRUD 操作
"""

import json
import uuid
from typing import List, Optional, Dict, Any

from models import get_db, AgentTemplate


class AgentTemplateService:
    """Agent 模板服务

    管理 Agent 模板的创建、查询、更新和删除
    """

    def create_template(
        self,
        name: str,
        agent_type: str = "react",
        model: str = "gpt-4o-mini",
        max_iterations: int = 10,
        description: str = None,
        system_prompt: str = None,
        selected_tools: List[str] = None,
        created_by: str = "unknown"
    ) -> Dict[str, Any]:
        """创建新的 Agent 模板

        Args:
            name: 模板名称
            agent_type: Agent 类型 (react, function_calling, plan_execute)
            model: 模型名称
            max_iterations: 最大迭代次数
            description: 模板描述
            system_prompt: 系统 Prompt
            selected_tools: 选用的工具列表
            created_by: 创建者

        Returns:
            包含模板信息的字典
        """
        db = next(get_db())
        try:
            template_id = f"tpl-{uuid.uuid4().hex[:12]}"

            template = AgentTemplate(
                template_id=template_id,
                name=name,
                description=description,
                agent_type=agent_type,
                model=model,
                max_iterations=max_iterations,
                system_prompt=system_prompt,
                created_by=created_by
            )

            if selected_tools:
                template.set_tools_list(selected_tools)

            db.add(template)
            db.commit()

            return template.to_dict()
        finally:
            db.close()

    def list_templates(
        self,
        limit: int = 50,
        agent_type: str = None
    ) -> List[Dict[str, Any]]:
        """列出所有模板

        Args:
            limit: 返回数量限制
            agent_type: 过滤特定类型的 Agent

        Returns:
            模板列表
        """
        db = next(get_db())
        try:
            query = db.query(AgentTemplate)

            if agent_type:
                query = query.filter(AgentTemplate.agent_type == agent_type)

            templates = query.order_by(
                AgentTemplate.created_at.desc()
            ).limit(limit).all()

            return [tpl.to_dict() for tpl in templates]
        finally:
            db.close()

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """获取单个模板

        Args:
            template_id: 模板 ID

        Returns:
            模板信息，如果不存在则返回 None
        """
        db = next(get_db())
        try:
            template = db.query(AgentTemplate).filter(
                AgentTemplate.template_id == template_id
            ).first()

            if template:
                return template.to_dict()
            return None
        finally:
            db.close()

    def delete_template(self, template_id: str) -> bool:
        """删除模板

        Args:
            template_id: 模板 ID

        Returns:
            是否成功删除
        """
        db = next(get_db())
        try:
            template = db.query(AgentTemplate).filter(
                AgentTemplate.template_id == template_id
            ).first()

            if template:
                db.delete(template)
                db.commit()
                return True
            return False
        except Exception:
            db.rollback()
            return False
        finally:
            db.close()

    def update_template(
        self,
        template_id: str,
        name: str = None,
        description: str = None,
        agent_type: str = None,
        model: str = None,
        max_iterations: int = None,
        system_prompt: str = None,
        selected_tools: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """更新模板

        Args:
            template_id: 模板 ID
            name: 新名称
            description: 新描述
            agent_type: 新 Agent 类型
            model: 新模型
            max_iterations: 新最大迭代次数
            system_prompt: 新系统 Prompt
            selected_tools: 新工具列表

        Returns:
            更新后的模板信息，如果模板不存在则返回 None
        """
        db = next(get_db())
        try:
            template = db.query(AgentTemplate).filter(
                AgentTemplate.template_id == template_id
            ).first()

            if not template:
                return None

            if name is not None:
                template.name = name
            if description is not None:
                template.description = description
            if agent_type is not None:
                template.agent_type = agent_type
            if model is not None:
                template.model = model
            if max_iterations is not None:
                template.max_iterations = max_iterations
            if system_prompt is not None:
                template.system_prompt = system_prompt
            if selected_tools is not None:
                template.set_tools_list(selected_tools)

            db.commit()
            db.refresh(template)

            return template.to_dict()
        except Exception:
            db.rollback()
            return None
        finally:
            db.close()


# 全局服务实例
_global_service: Optional[AgentTemplateService] = None


def get_agent_template_service() -> AgentTemplateService:
    """获取全局 Agent 模板服务实例"""
    global _global_service

    if _global_service is None:
        _global_service = AgentTemplateService()

    return _global_service
