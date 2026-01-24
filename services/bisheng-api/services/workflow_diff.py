"""
ONE-DATA-STUDIO Workflow Version Control
Sprint 32: Developer Experience Optimization

Provides workflow versioning with diff comparison and rollback capabilities.
"""

import json
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import difflib
import logging

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Type of change in workflow diff"""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


@dataclass
class NodeChange:
    """Represents a change to a single node"""
    node_id: str
    node_type: str
    change_type: ChangeType
    old_config: Optional[Dict[str, Any]] = None
    new_config: Optional[Dict[str, Any]] = None
    field_changes: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class EdgeChange:
    """Represents a change to an edge (connection)"""
    source_id: str
    target_id: str
    change_type: ChangeType
    old_config: Optional[Dict[str, Any]] = None
    new_config: Optional[Dict[str, Any]] = None


@dataclass
class WorkflowDiff:
    """Complete diff between two workflow versions"""
    old_version: int
    new_version: int
    timestamp: datetime
    node_changes: List[NodeChange] = field(default_factory=list)
    edge_changes: List[EdgeChange] = field(default_factory=list)
    metadata_changes: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""

    @property
    def has_changes(self) -> bool:
        return bool(self.node_changes or self.edge_changes or self.metadata_changes)

    @property
    def change_count(self) -> int:
        return len(self.node_changes) + len(self.edge_changes) + len(self.metadata_changes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "old_version": self.old_version,
            "new_version": self.new_version,
            "timestamp": self.timestamp.isoformat(),
            "node_changes": [
                {
                    "node_id": nc.node_id,
                    "node_type": nc.node_type,
                    "change_type": nc.change_type.value,
                    "old_config": nc.old_config,
                    "new_config": nc.new_config,
                    "field_changes": nc.field_changes,
                }
                for nc in self.node_changes
            ],
            "edge_changes": [
                {
                    "source_id": ec.source_id,
                    "target_id": ec.target_id,
                    "change_type": ec.change_type.value,
                    "old_config": ec.old_config,
                    "new_config": ec.new_config,
                }
                for ec in self.edge_changes
            ],
            "metadata_changes": self.metadata_changes,
            "summary": self.summary,
            "has_changes": self.has_changes,
            "change_count": self.change_count,
        }


@dataclass
class WorkflowVersion:
    """A single version of a workflow"""
    id: int
    workflow_id: str
    version_number: int
    content: Dict[str, Any]
    content_hash: str
    created_at: datetime
    created_by: str
    comment: str = ""
    parent_version: Optional[int] = None

    @classmethod
    def create(
        cls,
        workflow_id: str,
        version_number: int,
        content: Dict[str, Any],
        created_by: str,
        comment: str = "",
        parent_version: Optional[int] = None,
    ) -> "WorkflowVersion":
        """Create a new workflow version"""
        content_hash = cls._compute_hash(content)
        return cls(
            id=0,  # Will be set by database
            workflow_id=workflow_id,
            version_number=version_number,
            content=content,
            content_hash=content_hash,
            created_at=datetime.utcnow(),
            created_by=created_by,
            comment=comment,
            parent_version=parent_version,
        )

    @staticmethod
    def _compute_hash(content: Dict[str, Any]) -> str:
        """Compute content hash for change detection"""
        content_str = json.dumps(content, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content_str.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "version_number": self.version_number,
            "content_hash": self.content_hash,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "comment": self.comment,
            "parent_version": self.parent_version,
        }


class WorkflowDiffEngine:
    """Engine for computing workflow diffs"""

    def compute_diff(
        self,
        old_version: WorkflowVersion,
        new_version: WorkflowVersion,
    ) -> WorkflowDiff:
        """Compute diff between two workflow versions"""
        diff = WorkflowDiff(
            old_version=old_version.version_number,
            new_version=new_version.version_number,
            timestamp=datetime.utcnow(),
        )

        # Compare nodes
        old_nodes = self._extract_nodes(old_version.content)
        new_nodes = self._extract_nodes(new_version.content)
        diff.node_changes = self._diff_nodes(old_nodes, new_nodes)

        # Compare edges
        old_edges = self._extract_edges(old_version.content)
        new_edges = self._extract_edges(new_version.content)
        diff.edge_changes = self._diff_edges(old_edges, new_edges)

        # Compare metadata
        diff.metadata_changes = self._diff_metadata(
            old_version.content, new_version.content
        )

        # Generate summary
        diff.summary = self._generate_summary(diff)

        return diff

    def _extract_nodes(self, content: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Extract nodes from workflow content"""
        nodes = content.get("nodes", [])
        return {node.get("id", str(i)): node for i, node in enumerate(nodes)}

    def _extract_edges(self, content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract edges from workflow content"""
        return content.get("edges", [])

    def _diff_nodes(
        self,
        old_nodes: Dict[str, Dict[str, Any]],
        new_nodes: Dict[str, Dict[str, Any]],
    ) -> List[NodeChange]:
        """Compute node-level diff"""
        changes = []
        all_node_ids = set(old_nodes.keys()) | set(new_nodes.keys())

        for node_id in all_node_ids:
            old_node = old_nodes.get(node_id)
            new_node = new_nodes.get(node_id)

            if old_node is None and new_node is not None:
                # Node added
                changes.append(NodeChange(
                    node_id=node_id,
                    node_type=new_node.get("type", "unknown"),
                    change_type=ChangeType.ADDED,
                    new_config=new_node,
                ))
            elif old_node is not None and new_node is None:
                # Node removed
                changes.append(NodeChange(
                    node_id=node_id,
                    node_type=old_node.get("type", "unknown"),
                    change_type=ChangeType.REMOVED,
                    old_config=old_node,
                ))
            elif old_node != new_node:
                # Node modified
                field_changes = self._diff_node_fields(old_node, new_node)
                changes.append(NodeChange(
                    node_id=node_id,
                    node_type=new_node.get("type", old_node.get("type", "unknown")),
                    change_type=ChangeType.MODIFIED,
                    old_config=old_node,
                    new_config=new_node,
                    field_changes=field_changes,
                ))

        return changes

    def _diff_node_fields(
        self,
        old_node: Dict[str, Any],
        new_node: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Compute field-level diff within a node"""
        changes = []
        all_keys = set(old_node.keys()) | set(new_node.keys())

        for key in all_keys:
            old_value = old_node.get(key)
            new_value = new_node.get(key)

            if old_value != new_value:
                changes.append({
                    "field": key,
                    "old_value": old_value,
                    "new_value": new_value,
                })

        return changes

    def _diff_edges(
        self,
        old_edges: List[Dict[str, Any]],
        new_edges: List[Dict[str, Any]],
    ) -> List[EdgeChange]:
        """Compute edge-level diff"""
        changes = []

        def edge_key(edge: Dict[str, Any]) -> Tuple[str, str]:
            return (edge.get("source", ""), edge.get("target", ""))

        old_edge_map = {edge_key(e): e for e in old_edges}
        new_edge_map = {edge_key(e): e for e in new_edges}

        all_edge_keys = set(old_edge_map.keys()) | set(new_edge_map.keys())

        for key in all_edge_keys:
            old_edge = old_edge_map.get(key)
            new_edge = new_edge_map.get(key)

            if old_edge is None and new_edge is not None:
                changes.append(EdgeChange(
                    source_id=key[0],
                    target_id=key[1],
                    change_type=ChangeType.ADDED,
                    new_config=new_edge,
                ))
            elif old_edge is not None and new_edge is None:
                changes.append(EdgeChange(
                    source_id=key[0],
                    target_id=key[1],
                    change_type=ChangeType.REMOVED,
                    old_config=old_edge,
                ))
            elif old_edge != new_edge:
                changes.append(EdgeChange(
                    source_id=key[0],
                    target_id=key[1],
                    change_type=ChangeType.MODIFIED,
                    old_config=old_edge,
                    new_config=new_edge,
                ))

        return changes

    def _diff_metadata(
        self,
        old_content: Dict[str, Any],
        new_content: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compare workflow metadata (excluding nodes and edges)"""
        changes = {}
        metadata_keys = {"name", "description", "variables", "settings", "viewport"}

        for key in metadata_keys:
            old_value = old_content.get(key)
            new_value = new_content.get(key)

            if old_value != new_value:
                changes[key] = {
                    "old": old_value,
                    "new": new_value,
                }

        return changes

    def _generate_summary(self, diff: WorkflowDiff) -> str:
        """Generate human-readable summary of changes"""
        parts = []

        added_nodes = sum(1 for n in diff.node_changes if n.change_type == ChangeType.ADDED)
        removed_nodes = sum(1 for n in diff.node_changes if n.change_type == ChangeType.REMOVED)
        modified_nodes = sum(1 for n in diff.node_changes if n.change_type == ChangeType.MODIFIED)

        if added_nodes:
            parts.append(f"{added_nodes} node(s) added")
        if removed_nodes:
            parts.append(f"{removed_nodes} node(s) removed")
        if modified_nodes:
            parts.append(f"{modified_nodes} node(s) modified")

        added_edges = sum(1 for e in diff.edge_changes if e.change_type == ChangeType.ADDED)
        removed_edges = sum(1 for e in diff.edge_changes if e.change_type == ChangeType.REMOVED)

        if added_edges:
            parts.append(f"{added_edges} connection(s) added")
        if removed_edges:
            parts.append(f"{removed_edges} connection(s) removed")

        if diff.metadata_changes:
            parts.append(f"{len(diff.metadata_changes)} metadata field(s) changed")

        return "; ".join(parts) if parts else "No changes"


class WorkflowVersionManager:
    """
    Manages workflow versions with storage and retrieval

    Usage:
        manager = WorkflowVersionManager(session)

        # Create new version
        version = manager.create_version(
            workflow_id="wf-123",
            content=workflow_content,
            created_by="user-456",
            comment="Added new LLM node"
        )

        # Get version history
        history = manager.get_history("wf-123")

        # Compare versions
        diff = manager.compare_versions("wf-123", 1, 3)

        # Rollback to version
        new_version = manager.rollback("wf-123", target_version=2, created_by="user-456")
    """

    def __init__(self, db_session=None):
        self.session = db_session
        self.diff_engine = WorkflowDiffEngine()
        self._version_cache: Dict[str, List[WorkflowVersion]] = {}

    def create_version(
        self,
        workflow_id: str,
        content: Dict[str, Any],
        created_by: str,
        comment: str = "",
    ) -> WorkflowVersion:
        """
        Create a new version of a workflow

        Args:
            workflow_id: Workflow identifier
            content: Workflow content (nodes, edges, metadata)
            created_by: User ID of creator
            comment: Optional version comment

        Returns:
            Created WorkflowVersion
        """
        # Get latest version number
        history = self.get_history(workflow_id)
        latest_version = max((v.version_number for v in history), default=0)

        # Check for duplicate content
        if history:
            latest = history[0]
            new_hash = WorkflowVersion._compute_hash(content)
            if new_hash == latest.content_hash:
                logger.debug(f"No changes detected for workflow {workflow_id}")
                return latest

        # Create new version
        version = WorkflowVersion.create(
            workflow_id=workflow_id,
            version_number=latest_version + 1,
            content=content,
            created_by=created_by,
            comment=comment,
            parent_version=latest_version if latest_version > 0 else None,
        )

        # Persist to storage
        self._save_version(version)

        logger.info(
            f"Created version {version.version_number} for workflow {workflow_id}"
        )
        return version

    def get_version(
        self,
        workflow_id: str,
        version_number: int,
    ) -> Optional[WorkflowVersion]:
        """Get a specific version of a workflow"""
        history = self.get_history(workflow_id)
        for version in history:
            if version.version_number == version_number:
                return version
        return None

    def get_latest_version(self, workflow_id: str) -> Optional[WorkflowVersion]:
        """Get the latest version of a workflow"""
        history = self.get_history(workflow_id)
        return history[0] if history else None

    def get_history(
        self,
        workflow_id: str,
        limit: int = 50,
    ) -> List[WorkflowVersion]:
        """
        Get version history for a workflow

        Args:
            workflow_id: Workflow identifier
            limit: Maximum versions to return

        Returns:
            List of WorkflowVersion, newest first
        """
        return self._load_versions(workflow_id, limit)

    def compare_versions(
        self,
        workflow_id: str,
        old_version: int,
        new_version: int,
    ) -> Optional[WorkflowDiff]:
        """
        Compare two versions of a workflow

        Args:
            workflow_id: Workflow identifier
            old_version: Older version number
            new_version: Newer version number

        Returns:
            WorkflowDiff or None if versions not found
        """
        old = self.get_version(workflow_id, old_version)
        new = self.get_version(workflow_id, new_version)

        if not old or not new:
            logger.warning(
                f"Version not found: old={old_version}, new={new_version}"
            )
            return None

        return self.diff_engine.compute_diff(old, new)

    def rollback(
        self,
        workflow_id: str,
        target_version: int,
        created_by: str,
    ) -> Optional[WorkflowVersion]:
        """
        Rollback workflow to a previous version

        Creates a new version with content from target version.

        Args:
            workflow_id: Workflow identifier
            target_version: Version number to rollback to
            created_by: User performing rollback

        Returns:
            New WorkflowVersion or None if target not found
        """
        target = self.get_version(workflow_id, target_version)
        if not target:
            logger.error(f"Target version {target_version} not found")
            return None

        # Create new version with old content
        return self.create_version(
            workflow_id=workflow_id,
            content=target.content,
            created_by=created_by,
            comment=f"Rollback to version {target_version}",
        )

    def get_text_diff(
        self,
        workflow_id: str,
        old_version: int,
        new_version: int,
    ) -> str:
        """Get unified diff as text (for display)"""
        old = self.get_version(workflow_id, old_version)
        new = self.get_version(workflow_id, new_version)

        if not old or not new:
            return ""

        old_json = json.dumps(old.content, indent=2, ensure_ascii=False)
        new_json = json.dumps(new.content, indent=2, ensure_ascii=False)

        diff = difflib.unified_diff(
            old_json.splitlines(keepends=True),
            new_json.splitlines(keepends=True),
            fromfile=f"v{old_version}",
            tofile=f"v{new_version}",
        )

        return "".join(diff)

    def _save_version(self, version: WorkflowVersion):
        """Save version to storage (override for database)"""
        # In-memory cache for now
        if version.workflow_id not in self._version_cache:
            self._version_cache[version.workflow_id] = []

        # Insert at beginning (newest first)
        self._version_cache[version.workflow_id].insert(0, version)

        # If database session available, persist
        if self.session:
            self._persist_to_database(version)

    def _load_versions(
        self,
        workflow_id: str,
        limit: int,
    ) -> List[WorkflowVersion]:
        """Load versions from storage"""
        # Try database first
        if self.session:
            versions = self._load_from_database(workflow_id, limit)
            if versions:
                return versions

        # Fall back to cache
        cached = self._version_cache.get(workflow_id, [])
        return cached[:limit]

    def _persist_to_database(self, version: WorkflowVersion):
        """Persist version to database"""
        try:
            # Import here to avoid circular dependency
            from sqlalchemy import text

            self.session.execute(
                text("""
                    INSERT INTO workflow_versions
                    (workflow_id, version_number, content, content_hash,
                     created_at, created_by, comment, parent_version)
                    VALUES
                    (:workflow_id, :version_number, :content, :content_hash,
                     :created_at, :created_by, :comment, :parent_version)
                """),
                {
                    "workflow_id": version.workflow_id,
                    "version_number": version.version_number,
                    "content": json.dumps(version.content),
                    "content_hash": version.content_hash,
                    "created_at": version.created_at,
                    "created_by": version.created_by,
                    "comment": version.comment,
                    "parent_version": version.parent_version,
                }
            )
            self.session.commit()
        except Exception as e:
            logger.error(f"Failed to persist version: {e}")
            self.session.rollback()

    def _load_from_database(
        self,
        workflow_id: str,
        limit: int,
    ) -> List[WorkflowVersion]:
        """Load versions from database"""
        try:
            from sqlalchemy import text

            result = self.session.execute(
                text("""
                    SELECT id, workflow_id, version_number, content, content_hash,
                           created_at, created_by, comment, parent_version
                    FROM workflow_versions
                    WHERE workflow_id = :workflow_id
                    ORDER BY version_number DESC
                    LIMIT :limit
                """),
                {"workflow_id": workflow_id, "limit": limit}
            )

            versions = []
            for row in result:
                versions.append(WorkflowVersion(
                    id=row.id,
                    workflow_id=row.workflow_id,
                    version_number=row.version_number,
                    content=json.loads(row.content),
                    content_hash=row.content_hash,
                    created_at=row.created_at,
                    created_by=row.created_by,
                    comment=row.comment or "",
                    parent_version=row.parent_version,
                ))
            return versions
        except Exception as e:
            logger.error(f"Failed to load versions from database: {e}")
            return []


# Convenience function for API endpoints
def get_version_manager(session=None) -> WorkflowVersionManager:
    """Get a WorkflowVersionManager instance"""
    return WorkflowVersionManager(db_session=session)
