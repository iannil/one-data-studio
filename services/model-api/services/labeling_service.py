"""
数据标注平台服务

集成 Label Studio 实现专业数据标注功能：
- 图像标注（目标检测、分割、分类）
- 文本标注（NER、分类、情感分析）
- 音频标注（语音识别、分类）
- 视频标注
- 多模态标注
- 自动化标注（集成 AIHub 模型）
"""

import logging
import uuid
import time
import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum

logger = logging.getLogger(__name__)


class LabelingTaskType(str, Enum):
    """标注任务类型"""
    IMAGE_CLASSIFICATION = "image_classification"
    IMAGE_DETECTION = "image_detection"
    IMAGE_SEGMENTATION = "image_segmentation"
    IMAGE_KEYPOINT = "image_keypoint"
    TEXT_CLASSIFICATION = "text_classification"
    TEXT_NER = "text_ner"
    TEXT_RELATION = "text_relation"
    AUDIO_CLASSIFICATION = "audio_classification"
    AUDIO_TRANSCRIPTION = "audio_transcription"
    VIDEO_CLASSIFICATION = "video_classification"
    VIDEO_DETECTION = "video_detection"
    MULTIMODAL = "multimodal"


class LabelingStatus(str, Enum):
    """标注状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REVIEW = "review"
    REJECTED = "rejected"


class ProjectStatus(str, Enum):
    """项目状态"""
    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


@dataclass
class LabelConfig:
    """标注配置（Label Studio 格式）"""
    task_type: LabelingTaskType
    xml_config: str  # Label Studio XML 配置
    labels: List[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_type": self.task_type.value,
            "xml_config": self.xml_config,
            "labels": self.labels,
            "description": self.description,
        }


# 预定义的标注配置模板
LABEL_CONFIG_TEMPLATES = {
    LabelingTaskType.IMAGE_CLASSIFICATION: LabelConfig(
        task_type=LabelingTaskType.IMAGE_CLASSIFICATION,
        xml_config="""
<View>
  <Image name="image" value="$image"/>
  <Choices name="choice" toName="image">
    <Choice value="Cat"/>
    <Choice value="Dog"/>
    <Choice value="Bird"/>
  </Choices>
</View>
""",
        labels=["Cat", "Dog", "Bird"],
        description="图像分类标注",
    ),
    LabelingTaskType.IMAGE_DETECTION: LabelConfig(
        task_type=LabelingTaskType.IMAGE_DETECTION,
        xml_config="""
<View>
  <Image name="image" value="$image"/>
  <RectangleLabels name="label" toName="image">
    <Label value="Person" background="red"/>
    <Label value="Car" background="blue"/>
    <Label value="Animal" background="green"/>
  </RectangleLabels>
</View>
""",
        labels=["Person", "Car", "Animal"],
        description="图像目标检测标注",
    ),
    LabelingTaskType.IMAGE_SEGMENTATION: LabelConfig(
        task_type=LabelingTaskType.IMAGE_SEGMENTATION,
        xml_config="""
<View>
  <Image name="image" value="$image"/>
  <BrushLabels name="label" toName="image">
    <Label value="Background" background="#FF0000"/>
    <Label value="Foreground" background="#00FF00"/>
  </BrushLabels>
</View>
""",
        labels=["Background", "Foreground"],
        description="图像分割标注",
    ),
    LabelingTaskType.TEXT_CLASSIFICATION: LabelConfig(
        task_type=LabelingTaskType.TEXT_CLASSIFICATION,
        xml_config="""
<View>
  <Text name="text" value="$text"/>
  <Choices name="sentiment" toName="text">
    <Choice value="Positive"/>
    <Choice value="Negative"/>
    <Choice value="Neutral"/>
  </Choices>
</View>
""",
        labels=["Positive", "Negative", "Neutral"],
        description="文本情感分类标注",
    ),
    LabelingTaskType.TEXT_NER: LabelConfig(
        task_type=LabelingTaskType.TEXT_NER,
        xml_config="""
<View>
  <Labels name="label" toName="text">
    <Label value="PER" background="red"/>
    <Label value="ORG" background="blue"/>
    <Label value="LOC" background="green"/>
    <Label value="MISC" background="yellow"/>
  </Labels>
  <Text name="text" value="$text"/>
</View>
""",
        labels=["PER", "ORG", "LOC", "MISC"],
        description="命名实体识别标注",
    ),
    LabelingTaskType.AUDIO_TRANSCRIPTION: LabelConfig(
        task_type=LabelingTaskType.AUDIO_TRANSCRIPTION,
        xml_config="""
<View>
  <Audio name="audio" value="$audio"/>
  <TextArea name="transcription" toName="audio" rows="4" editable="true"/>
</View>
""",
        labels=[],
        description="语音转写标注",
    ),
}


@dataclass
class LabelingTask:
    """标注任务"""
    task_id: str
    project_id: str
    data: Dict[str, Any]  # 任务数据（图片URL、文本等）
    status: LabelingStatus = LabelingStatus.PENDING
    annotations: List[Dict[str, Any]] = field(default_factory=list)
    predictions: List[Dict[str, Any]] = field(default_factory=list)  # 模型预测（自动标注）
    assigned_to: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "project_id": self.project_id,
            "data": self.data,
            "status": self.status.value,
            "annotations_count": len(self.annotations),
            "predictions_count": len(self.predictions),
            "assigned_to": self.assigned_to,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class LabelingProject:
    """标注项目"""
    project_id: str
    name: str
    description: str
    owner_id: str
    task_type: LabelingTaskType
    label_config: LabelConfig
    status: ProjectStatus = ProjectStatus.CREATED

    # 成员管理
    members: List[str] = field(default_factory=list)  # 标注员 ID 列表
    reviewers: List[str] = field(default_factory=list)  # 审核员 ID 列表

    # 自动标注配置
    auto_labeling_enabled: bool = False
    auto_labeling_model_id: Optional[str] = None
    auto_labeling_endpoint: Optional[str] = None
    auto_labeling_threshold: float = 0.7  # 置信度阈值

    # 统计
    total_tasks: int = 0
    completed_tasks: int = 0
    reviewed_tasks: int = 0

    # 存储配置
    storage_path: Optional[str] = None  # 数据存储路径

    # 时间
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "owner_id": self.owner_id,
            "task_type": self.task_type.value,
            "label_config": self.label_config.to_dict(),
            "status": self.status.value,
            "members": self.members,
            "reviewers": self.reviewers,
            "auto_labeling_enabled": self.auto_labeling_enabled,
            "auto_labeling_model_id": self.auto_labeling_model_id,
            "auto_labeling_threshold": self.auto_labeling_threshold,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "reviewed_tasks": self.reviewed_tasks,
            "progress": round(self.completed_tasks / self.total_tasks * 100, 2) if self.total_tasks > 0 else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class Annotation:
    """标注结果"""
    annotation_id: str
    task_id: str
    project_id: str
    user_id: str
    result: List[Dict[str, Any]]  # Label Studio 格式的标注结果
    was_cancelled: bool = False
    lead_time: float = 0.0  # 标注耗时（秒）
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "annotation_id": self.annotation_id,
            "task_id": self.task_id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "result": self.result,
            "was_cancelled": self.was_cancelled,
            "lead_time": self.lead_time,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class LabelingService:
    """数据标注服务"""

    def __init__(
        self,
        storage_base_path: str = "/data/labeling",
        label_studio_url: Optional[str] = None,
        label_studio_token: Optional[str] = None,
    ):
        self.storage_base_path = storage_base_path
        self.label_studio_url = label_studio_url
        self.label_studio_token = label_studio_token

        # 存储（生产环境应使用数据库）
        self._projects: Dict[str, LabelingProject] = {}
        self._tasks: Dict[str, LabelingTask] = {}
        self._annotations: Dict[str, Annotation] = {}

        # 自动标注模型客户端
        self._auto_labeling_clients: Dict[str, Any] = {}

    def get_label_config_templates(
        self,
        task_type: Optional[LabelingTaskType] = None
    ) -> Dict[str, Dict[str, Any]]:
        """获取标注配置模板"""
        if task_type:
            config = LABEL_CONFIG_TEMPLATES.get(task_type)
            if config:
                return {task_type.value: config.to_dict()}
            return {}

        return {
            t.value: c.to_dict()
            for t, c in LABEL_CONFIG_TEMPLATES.items()
        }

    def create_project(
        self,
        name: str,
        owner_id: str,
        task_type: LabelingTaskType,
        description: str = "",
        labels: Optional[List[str]] = None,
        xml_config: Optional[str] = None,
        members: Optional[List[str]] = None,
        reviewers: Optional[List[str]] = None,
        auto_labeling_model_id: Optional[str] = None,
        auto_labeling_endpoint: Optional[str] = None,
        auto_labeling_threshold: float = 0.7,
    ) -> LabelingProject:
        """
        创建标注项目

        Args:
            name: 项目名称
            owner_id: 所有者 ID
            task_type: 任务类型
            description: 项目描述
            labels: 标签列表
            xml_config: 自定义 Label Studio XML 配置
            members: 标注员列表
            reviewers: 审核员列表
            auto_labeling_model_id: 自动标注模型 ID
            auto_labeling_endpoint: 自动标注服务端点
            auto_labeling_threshold: 自动标注置信度阈值
        """
        project_id = f"proj-{uuid.uuid4().hex[:12]}"

        # 获取或创建标注配置
        if xml_config:
            label_config = LabelConfig(
                task_type=task_type,
                xml_config=xml_config,
                labels=labels or [],
                description=description,
            )
        else:
            # 使用模板
            template = LABEL_CONFIG_TEMPLATES.get(task_type)
            if template:
                label_config = LabelConfig(
                    task_type=task_type,
                    xml_config=template.xml_config,
                    labels=labels or template.labels,
                    description=template.description,
                )
            else:
                raise ValueError(f"未找到任务类型 {task_type} 的配置模板")

        # 如果提供了自定义标签，更新 XML 配置
        if labels and labels != label_config.labels:
            label_config = self._update_labels_in_config(label_config, labels)

        project = LabelingProject(
            project_id=project_id,
            name=name,
            description=description,
            owner_id=owner_id,
            task_type=task_type,
            label_config=label_config,
            status=ProjectStatus.CREATED,
            members=members or [],
            reviewers=reviewers or [],
            auto_labeling_enabled=bool(auto_labeling_model_id or auto_labeling_endpoint),
            auto_labeling_model_id=auto_labeling_model_id,
            auto_labeling_endpoint=auto_labeling_endpoint,
            auto_labeling_threshold=auto_labeling_threshold,
            storage_path=f"{self.storage_base_path}/{project_id}",
            created_at=datetime.utcnow(),
        )

        self._projects[project_id] = project

        logger.info(f"创建标注项目: {project_id}, 名称: {name}, 类型: {task_type.value}")

        return project

    def _update_labels_in_config(
        self,
        config: LabelConfig,
        new_labels: List[str]
    ) -> LabelConfig:
        """更新配置中的标签"""
        xml = config.xml_config
        config.labels = new_labels

        # 简单的 XML 标签替换（生产环境应使用 XML 解析器）
        if config.task_type == LabelingTaskType.IMAGE_CLASSIFICATION:
            choices = "\n".join([f'    <Choice value="{label}"/>' for label in new_labels])
            xml = f"""
<View>
  <Image name="image" value="$image"/>
  <Choices name="choice" toName="image">
{choices}
  </Choices>
</View>
"""
        elif config.task_type == LabelingTaskType.IMAGE_DETECTION:
            colors = ["red", "blue", "green", "yellow", "purple", "orange"]
            rect_labels = "\n".join([
                f'    <Label value="{label}" background="{colors[i % len(colors)]}"/>'
                for i, label in enumerate(new_labels)
            ])
            xml = f"""
<View>
  <Image name="image" value="$image"/>
  <RectangleLabels name="label" toName="image">
{rect_labels}
  </RectangleLabels>
</View>
"""

        config.xml_config = xml
        return config

    def add_tasks(
        self,
        project_id: str,
        data_list: List[Dict[str, Any]],
        auto_label: bool = True,
    ) -> List[LabelingTask]:
        """
        添加标注任务

        Args:
            project_id: 项目 ID
            data_list: 任务数据列表，如 [{"image": "url"}, ...]
            auto_label: 是否自动标注
        """
        project = self._projects.get(project_id)
        if not project:
            raise ValueError(f"项目不存在: {project_id}")

        tasks = []
        for data in data_list:
            task_id = f"task-{uuid.uuid4().hex[:12]}"

            task = LabelingTask(
                task_id=task_id,
                project_id=project_id,
                data=data,
                status=LabelingStatus.PENDING,
                created_at=datetime.utcnow(),
            )

            # 如果启用自动标注
            if auto_label and project.auto_labeling_enabled:
                predictions = self._run_auto_labeling(project, data)
                if predictions:
                    task.predictions = predictions

            self._tasks[task_id] = task
            tasks.append(task)

        # 更新项目统计
        project.total_tasks += len(tasks)
        project.updated_at = datetime.utcnow()

        logger.info(f"添加 {len(tasks)} 个标注任务到项目 {project_id}")

        return tasks

    def _run_auto_labeling(
        self,
        project: LabelingProject,
        data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """运行自动标注"""
        predictions = []

        if not project.auto_labeling_endpoint:
            return predictions

        try:
            import requests

            # 调用自动标注服务
            response = requests.post(
                project.auto_labeling_endpoint,
                json={
                    "data": data,
                    "task_type": project.task_type.value,
                    "labels": project.label_config.labels,
                },
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()

                # 过滤低置信度预测
                for pred in result.get("predictions", []):
                    if pred.get("score", 0) >= project.auto_labeling_threshold:
                        predictions.append({
                            "result": pred.get("result", []),
                            "score": pred.get("score", 0),
                            "model_version": result.get("model_version", "unknown"),
                        })

        except Exception as e:
            logger.warning(f"自动标注失败: {e}")

        return predictions

    def submit_annotation(
        self,
        task_id: str,
        user_id: str,
        result: List[Dict[str, Any]],
        lead_time: float = 0.0,
    ) -> Annotation:
        """
        提交标注结果

        Args:
            task_id: 任务 ID
            user_id: 标注员 ID
            result: Label Studio 格式的标注结果
            lead_time: 标注耗时（秒）
        """
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")

        annotation_id = f"ann-{uuid.uuid4().hex[:12]}"

        annotation = Annotation(
            annotation_id=annotation_id,
            task_id=task_id,
            project_id=task.project_id,
            user_id=user_id,
            result=result,
            lead_time=lead_time,
            created_at=datetime.utcnow(),
        )

        self._annotations[annotation_id] = annotation

        # 更新任务
        task.annotations.append(annotation.to_dict())
        task.status = LabelingStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()

        # 更新项目统计
        project = self._projects.get(task.project_id)
        if project:
            project.completed_tasks += 1
            project.updated_at = datetime.utcnow()

        logger.info(f"提交标注: {annotation_id}, 任务: {task_id}")

        return annotation

    def get_next_task(
        self,
        project_id: str,
        user_id: str,
    ) -> Optional[LabelingTask]:
        """
        获取下一个待标注任务

        Args:
            project_id: 项目 ID
            user_id: 标注员 ID
        """
        project = self._projects.get(project_id)
        if not project:
            return None

        # 查找未完成且未分配的任务
        for task in self._tasks.values():
            if task.project_id != project_id:
                continue
            if task.status != LabelingStatus.PENDING:
                continue
            if task.assigned_to and task.assigned_to != user_id:
                continue

            # 分配任务
            task.assigned_to = user_id
            task.status = LabelingStatus.IN_PROGRESS
            task.updated_at = datetime.utcnow()

            return task

        return None

    def export_annotations(
        self,
        project_id: str,
        format: str = "json",
        include_predictions: bool = False,
    ) -> Dict[str, Any]:
        """
        导出标注结果

        Args:
            project_id: 项目 ID
            format: 导出格式 (json, coco, yolo, pascal_voc)
            include_predictions: 是否包含预测结果
        """
        project = self._projects.get(project_id)
        if not project:
            raise ValueError(f"项目不存在: {project_id}")

        tasks = [t for t in self._tasks.values() if t.project_id == project_id]

        if format == "json":
            return self._export_json(project, tasks, include_predictions)
        elif format == "coco":
            return self._export_coco(project, tasks)
        elif format == "yolo":
            return self._export_yolo(project, tasks)
        else:
            raise ValueError(f"不支持的导出格式: {format}")

    def _export_json(
        self,
        project: LabelingProject,
        tasks: List[LabelingTask],
        include_predictions: bool,
    ) -> Dict[str, Any]:
        """导出为 JSON 格式"""
        export_data = {
            "project": project.to_dict(),
            "tasks": [],
        }

        for task in tasks:
            task_data = {
                "id": task.task_id,
                "data": task.data,
                "annotations": task.annotations,
            }
            if include_predictions:
                task_data["predictions"] = task.predictions

            export_data["tasks"].append(task_data)

        return export_data

    def _export_coco(
        self,
        project: LabelingProject,
        tasks: List[LabelingTask],
    ) -> Dict[str, Any]:
        """导出为 COCO 格式（适用于目标检测）"""
        coco_data = {
            "info": {
                "description": project.name,
                "version": "1.0",
                "year": datetime.now().year,
            },
            "licenses": [],
            "images": [],
            "annotations": [],
            "categories": [],
        }

        # 添加类别
        for i, label in enumerate(project.label_config.labels):
            coco_data["categories"].append({
                "id": i + 1,
                "name": label,
                "supercategory": "object",
            })

        label_to_id = {label: i + 1 for i, label in enumerate(project.label_config.labels)}

        annotation_id = 1
        for i, task in enumerate(tasks):
            # 添加图像
            image_url = task.data.get("image", "")
            coco_data["images"].append({
                "id": i + 1,
                "file_name": image_url.split("/")[-1] if image_url else f"image_{i}.jpg",
                "width": task.meta.get("width", 0),
                "height": task.meta.get("height", 0),
            })

            # 添加标注
            for annotation in task.annotations:
                for result in annotation.get("result", []):
                    if result.get("type") == "rectanglelabels":
                        value = result.get("value", {})
                        label = value.get("rectanglelabels", [None])[0]
                        if label and label in label_to_id:
                            x = value.get("x", 0) / 100 * task.meta.get("width", 100)
                            y = value.get("y", 0) / 100 * task.meta.get("height", 100)
                            w = value.get("width", 0) / 100 * task.meta.get("width", 100)
                            h = value.get("height", 0) / 100 * task.meta.get("height", 100)

                            coco_data["annotations"].append({
                                "id": annotation_id,
                                "image_id": i + 1,
                                "category_id": label_to_id[label],
                                "bbox": [x, y, w, h],
                                "area": w * h,
                                "iscrowd": 0,
                            })
                            annotation_id += 1

        return coco_data

    def _export_yolo(
        self,
        project: LabelingProject,
        tasks: List[LabelingTask],
    ) -> Dict[str, Any]:
        """导出为 YOLO 格式"""
        yolo_data = {
            "classes": project.label_config.labels,
            "annotations": {},
        }

        label_to_id = {label: i for i, label in enumerate(project.label_config.labels)}

        for task in tasks:
            image_name = task.data.get("image", "").split("/")[-1]
            annotations = []

            for annotation in task.annotations:
                for result in annotation.get("result", []):
                    if result.get("type") == "rectanglelabels":
                        value = result.get("value", {})
                        label = value.get("rectanglelabels", [None])[0]
                        if label and label in label_to_id:
                            # YOLO 格式：class_id x_center y_center width height (归一化)
                            x_center = (value.get("x", 0) + value.get("width", 0) / 2) / 100
                            y_center = (value.get("y", 0) + value.get("height", 0) / 2) / 100
                            width = value.get("width", 0) / 100
                            height = value.get("height", 0) / 100

                            annotations.append(
                                f"{label_to_id[label]} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"
                            )

            yolo_data["annotations"][image_name] = annotations

        return yolo_data

    def get_project(self, project_id: str) -> Optional[LabelingProject]:
        """获取项目"""
        return self._projects.get(project_id)

    def list_projects(
        self,
        owner_id: Optional[str] = None,
        member_id: Optional[str] = None,
        status: Optional[ProjectStatus] = None,
    ) -> List[LabelingProject]:
        """列出项目"""
        projects = list(self._projects.values())

        if owner_id:
            projects = [p for p in projects if p.owner_id == owner_id]
        if member_id:
            projects = [p for p in projects if member_id in p.members or p.owner_id == member_id]
        if status:
            projects = [p for p in projects if p.status == status]

        return projects

    def get_task(self, task_id: str) -> Optional[LabelingTask]:
        """获取任务"""
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        project_id: str,
        status: Optional[LabelingStatus] = None,
        assigned_to: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[LabelingTask]:
        """列出任务"""
        tasks = [t for t in self._tasks.values() if t.project_id == project_id]

        if status:
            tasks = [t for t in tasks if t.status == status]
        if assigned_to:
            tasks = [t for t in tasks if t.assigned_to == assigned_to]

        # 排序
        tasks.sort(key=lambda x: x.created_at or datetime.min)

        return tasks[offset:offset + limit]

    def get_project_statistics(self, project_id: str) -> Dict[str, Any]:
        """获取项目统计"""
        project = self._projects.get(project_id)
        if not project:
            return {}

        tasks = [t for t in self._tasks.values() if t.project_id == project_id]

        status_counts = {s.value: 0 for s in LabelingStatus}
        for task in tasks:
            status_counts[task.status.value] += 1

        # 计算平均标注时间
        total_time = 0
        completed_count = 0
        for ann in self._annotations.values():
            if ann.project_id == project_id:
                total_time += ann.lead_time
                completed_count += 1

        avg_time = total_time / completed_count if completed_count > 0 else 0

        return {
            "project_id": project_id,
            "total_tasks": len(tasks),
            "status_counts": status_counts,
            "progress": round(status_counts.get("completed", 0) / len(tasks) * 100, 2) if tasks else 0,
            "total_annotations": completed_count,
            "average_annotation_time": round(avg_time, 2),
            "members_count": len(project.members),
        }

    def configure_auto_labeling(
        self,
        project_id: str,
        model_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        threshold: float = 0.7,
    ) -> bool:
        """
        配置自动标注

        Args:
            project_id: 项目 ID
            model_id: AIHub 模型 ID
            endpoint: 自动标注服务端点
            threshold: 置信度阈值
        """
        project = self._projects.get(project_id)
        if not project:
            return False

        project.auto_labeling_enabled = bool(model_id or endpoint)
        project.auto_labeling_model_id = model_id
        project.auto_labeling_endpoint = endpoint
        project.auto_labeling_threshold = threshold
        project.updated_at = datetime.utcnow()

        logger.info(f"配置自动标注: 项目 {project_id}, 模型 {model_id}")

        return True


# 全局服务实例
_labeling_service: Optional[LabelingService] = None


def get_labeling_service() -> LabelingService:
    """获取标注服务实例"""
    global _labeling_service
    if _labeling_service is None:
        _labeling_service = LabelingService()
    return _labeling_service
