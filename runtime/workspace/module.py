"""
Workspace Runtime Module

Provides project/workspace management, isolation, resource quotas,
and collaboration features.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import asyncio
import logging
import uuid
from collections import defaultdict

from runtime.modules import (
    RuntimeModule,
    ModuleMetadata,
    ModuleState,
)

logger = logging.getLogger(__name__)


class WorkspaceStatus(Enum):
    """Workspace status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class WorkspaceType(Enum):
    """Workspace type."""
    PERSONAL = "personal"
    TEAM = "team"
    ORGANIZATION = "organization"
    PROJECT = "project"
    TEMPORARY = "temporary"


class ResourceType(Enum):
    """Resource types for quotas."""
    CPU = "cpu"
    MEMORY = "memory"
    STORAGE = "storage"
    NETWORK = "network"
    AGENTS = "agents"
    CONVERSATIONS = "conversations"
    WORKFLOWS = "workflows"
    API_CALLS = "api_calls"
    STORAGE_OBJECTS = "storage_objects"
    CUSTOM = "custom"


class MemberRole(Enum):
    """Workspace member roles."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
    GUEST = "guest"


class InvitationStatus(Enum):
    """Invitation status."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class ResourceQuota:
    """Resource quota definition."""
    resource_type: ResourceType
    limit: int  # -1 = unlimited
    used: int = 0
    unit: str = "count"  # count, bytes, seconds, etc.
    warning_threshold: float = 0.8  # 80%
    hard_limit: bool = True

    def is_exceeded(self) -> bool:
        return self.limit > 0 and self.used >= self.limit

    def is_warning(self) -> bool:
        if self.limit <= 0:
            return False
        return self.used >= self.limit * self.warning_threshold

    def available(self) -> int:
        if self.limit <= 0:
            return -1
        return max(0, self.limit - self.used)

    def usage_percentage(self) -> float:
        if self.limit <= 0:
            return 0.0
        return (self.used / self.limit) * 100


@dataclass
class Workspace:
    """Workspace definition."""
    workspace_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    workspace_type: WorkspaceType = WorkspaceType.PERSONAL
    status: WorkspaceStatus = WorkspaceStatus.ACTIVE
    owner_id: str = ""
    parent_workspace_id: Optional[str] = None
    quotas: Dict[ResourceType, ResourceQuota] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    def get_quota(self, resource_type: ResourceType) -> Optional[ResourceQuota]:
        return self.quotas.get(resource_type)

    def set_quota(self, quota: ResourceQuota) -> None:
        self.quotas[quota.resource_type] = quota

    def check_quota(self, resource_type: ResourceType, amount: int = 1) -> bool:
        quota = self.quotas.get(resource_type)
        if not quota or quota.limit <= 0:
            return True
        return quota.used + amount <= quota.limit

    def consume_quota(self, resource_type: ResourceType, amount: int = 1) -> bool:
        quota = self.quotas.get(resource_type)
        if not quota or quota.limit <= 0:
            return True
        if quota.used + amount <= quota.limit:
            quota.used += amount
            return True
        return False

    def release_quota(self, resource_type: ResourceType, amount: int = 1) -> bool:
        quota = self.quotas.get(resource_type)
        if quota:
            quota.used = max(0, quota.used - amount)
            return True
        return False


@dataclass
class WorkspaceMember:
    """Workspace member."""
    member_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    workspace_id: str = ""
    user_id: str = ""
    role: MemberRole = MemberRole.MEMBER
    permissions: List[str] = field(default_factory=list)
    joined_at: datetime = field(default_factory=datetime.utcnow)
    invited_by: Optional[str] = None
    invited_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    last_active_at: Optional[datetime] = None
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def has_permission(self, permission: str) -> bool:
        if self.role in (MemberRole.OWNER, MemberRole.ADMIN):
            return True
        return permission in self.permissions


@dataclass
class WorkspaceInvitation:
    """Workspace invitation."""
    invitation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    workspace_id: str = ""
    email: str = ""
    role: MemberRole = MemberRole.MEMBER
    permissions: List[str] = field(default_factory=list)
    invited_by: str = ""
    status: InvitationStatus = InvitationStatus.PENDING
    token: str = field(default_factory=lambda: str(uuid.uuid4()))
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(days=7))
    created_at: datetime = field(default_factory=datetime.utcnow)
    accepted_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkspaceActivity:
    """Workspace activity log."""
    activity_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    workspace_id: str = ""
    user_id: str = ""
    action: str = ""
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class WorkspaceBackend(ABC):
    """Abstract workspace storage backend."""

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    async def save_workspace(self, workspace: Workspace) -> Workspace:
        pass

    @abstractmethod
    async def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        pass

    @abstractmethod
    async def list_workspaces(
        self,
        owner_id: Optional[str] = None,
        status: Optional[WorkspaceStatus] = None,
        workspace_type: Optional[WorkspaceType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Workspace]:
        pass

    @abstractmethod
    async def delete_workspace(self, workspace_id: str) -> bool:
        pass

    @abstractmethod
    async def save_member(self, member: WorkspaceMember) -> WorkspaceMember:
        pass

    @abstractmethod
    async def get_member(self, workspace_id: str, user_id: str) -> Optional[WorkspaceMember]:
        pass

    @abstractmethod
    async def list_members(
        self,
        workspace_id: str,
        role: Optional[MemberRole] = None,
        active_only: bool = True
    ) -> List[WorkspaceMember]:
        pass

    @abstractmethod
    async def delete_member(self, workspace_id: str, user_id: str) -> bool:
        pass

    @abstractmethod
    async def save_invitation(self, invitation: WorkspaceInvitation) -> WorkspaceInvitation:
        pass

    @abstractmethod
    async def get_invitation(self, token: str) -> Optional[WorkspaceInvitation]:
        pass

    @abstractmethod
    async def list_invitations(
        self,
        workspace_id: str,
        status: Optional[InvitationStatus] = None
    ) -> List[WorkspaceInvitation]:
        pass

    @abstractmethod
    async def delete_invitation(self, invitation_id: str) -> bool:
        pass

    @abstractmethod
    async def log_activity(self, activity: WorkspaceActivity) -> None:
        pass

    @abstractmethod
    async def get_activities(
        self,
        workspace_id: str,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[WorkspaceActivity]:
        pass


class LocalWorkspaceBackend(WorkspaceBackend):
    """Local filesystem workspace backend."""

    def __init__(self):
        self._workspaces: Dict[str, Workspace] = {}
        self._members: Dict[str, Dict[str, WorkspaceMember]] = defaultdict(dict)
        self._invitations: Dict[str, WorkspaceInvitation] = {}
        self._activities: Dict[str, List[WorkspaceActivity]] = defaultdict(list)

    async def initialize(self, config: Dict[str, Any]) -> None:
        # Load from disk if configured
        pass

    async def save_workspace(self, workspace: Workspace) -> Workspace:
        workspace.updated_at = datetime.utcnow()
        self._workspaces[workspace.workspace_id] = workspace
        return workspace

    async def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        return self._workspaces.get(workspace_id)

    async def list_workspaces(
        self,
        owner_id: Optional[str] = None,
        status: Optional[WorkspaceStatus] = None,
        workspace_type: Optional[WorkspaceType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Workspace]:
        workspaces = list(self._workspaces.values())

        if owner_id:
            workspaces = [w for w in workspaces if w.owner_id == owner_id]
        if status:
            workspaces = [w for w in workspaces if w.status == status]
        if workspace_type:
            workspaces = [w for w in workspaces if w.workspace_type == workspace_type]

        workspaces.sort(key=lambda w: w.updated_at, reverse=True)
        return workspaces[offset:offset + limit]

    async def delete_workspace(self, workspace_id: str) -> bool:
        if workspace_id in self._workspaces:
            ws = self._workspaces[workspace_id]
            ws.status = WorkspaceStatus.DELETED
            ws.deleted_at = datetime.utcnow()
            ws.updated_at = datetime.utcnow()
            return True
        return False

    async def save_member(self, member: WorkspaceMember) -> WorkspaceMember:
        self._members[member.workspace_id][member.user_id] = member
        return member

    async def get_member(self, workspace_id: str, user_id: str) -> Optional[WorkspaceMember]:
        return self._members.get(workspace_id, {}).get(user_id)

    async def list_members(
        self,
        workspace_id: str,
        role: Optional[MemberRole] = None,
        active_only: bool = True
    ) -> List[WorkspaceMember]:
        members = list(self._members.get(workspace_id, {}).values())

        if role:
            members = [m for m in members if m.role == role]
        if active_only:
            members = [m for m in members if m.is_active]

        members.sort(key=lambda m: m.joined_at)
        return members

    async def delete_member(self, workspace_id: str, user_id: str) -> bool:
        if workspace_id in self._members and user_id in self._members[workspace_id]:
            del self._members[workspace_id][user_id]
            return True
        return False

    async def save_invitation(self, invitation: WorkspaceInvitation) -> WorkspaceInvitation:
        self._invitations[invitation.invitation_id] = invitation
        return invitation

    async def get_invitation(self, token: str) -> Optional[WorkspaceInvitation]:
        for inv in self._invitations.values():
            if inv.token == token:
                return inv
        return None

    async def list_invitations(
        self,
        workspace_id: str,
        status: Optional[InvitationStatus] = None
    ) -> List[WorkspaceInvitation]:
        invitations = [i for i in self._invitations.values() if i.workspace_id == workspace_id]
        if status:
            invitations = [i for i in invitations if i.status == status]
        invitations.sort(key=lambda i: i.created_at, reverse=True)
        return invitations

    async def delete_invitation(self, invitation_id: str) -> bool:
        return self._invitations.pop(invitation_id, None) is not None

    async def log_activity(self, activity: WorkspaceActivity) -> None:
        self._activities[activity.workspace_id].append(activity)
        # Keep only last 1000 activities per workspace
        if len(self._activities[activity.workspace_id]) > 1000:
            self._activities[activity.workspace_id] = self._activities[activity.workspace_id][-1000:]

    async def get_activities(
        self,
        workspace_id: str,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[WorkspaceActivity]:
        activities = self._activities.get(workspace_id, [])

        if user_id:
            activities = [a for a in activities if a.user_id == user_id]
        if action:
            activities = [a for a in activities if a.action == action]
        if since:
            activities = [a for a in activities if a.timestamp >= since]

        activities.sort(key=lambda a: a.timestamp, reverse=True)
        return activities[:limit]


class WorkspaceModule(RuntimeModule):
    """
    Workspace management module.

    Provides:
    - Workspace lifecycle (create, update, delete, archive)
    - Member management with roles and permissions
    - Resource quotas and usage tracking
    - Invitations and collaboration
    - Activity logging
    - Hierarchical workspaces (parent/child)
    """

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="workspace",
            version="1.0.0",
            description="Workspace and project management with isolation and quotas",
            author="AIPENSA",
            dependencies=["authentication", "storage"],
            provides=["workspace_management", "member_management", "quota_management", "invitations"],
            tags={"workspace", "project", "collaboration", "isolation", "quotas"}
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._backend: Optional[WorkspaceBackend] = None
        self._default_quotas: Dict[ResourceType, ResourceQuota] = {}
        self._config: Dict[str, Any] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        """Initialize workspace module."""
        self._runtime = runtime
        self._config = {**self._config, **config}

        # Create backend
        backend_type = self._config.get("backend", "local")
        if backend_type == "local":
            self._backend = LocalWorkspaceBackend()
        else:
            raise ValueError(f"Unknown backend: {backend_type}")

        await self._backend.initialize(self._config.get("backend_config", {}))

        # Default quotas
        for resource_type in ResourceType:
            limit = self._config.get("default_quotas", {}).get(resource_type.value, -1)
            self._default_quotas[resource_type] = ResourceQuota(
                resource_type=resource_type,
                limit=limit
            )

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        self.state = ModuleState.INITIALIZED
        logger.info("Workspace module initialized")

    async def start(self) -> None:
        self.state = ModuleState.RUNNING
        logger.info("Workspace module started")

    async def stop(self) -> None:
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        self.state = ModuleState.STOPPED
        logger.info("Workspace module stopped")

    async def cleanup(self) -> None:
        await self.stop()
        self._backend = None
        self.state = ModuleState.UNINITIALIZED
        logger.info("Workspace module cleaned up")

    async def health_check(self) -> Dict[str, Any]:
        return {
            "module": "workspace",
            "status": self.state.value,
            "healthy": self.state == ModuleState.RUNNING,
            "workspaces": len(await self.list_workspaces()),
            "default_quotas": {k.value: v.used for k, v in self._default_quotas.items()}
        }

    def _apply_default_quotas(self, workspace: Workspace) -> None:
        """Apply default quotas to workspace."""
        for resource_type, quota in self._default_quotas.items():
            if resource_type not in workspace.quotas:
                workspace.quotas[resource_type] = ResourceQuota(
                    resource_type=resource_type,
                    limit=quota.limit,
                    warning_threshold=quota.warning_threshold,
                    hard_limit=quota.hard_limit
                )

    # Workspace Operations
    async def create_workspace(
        self,
        name: str,
        owner_id: str,
        description: str = "",
        workspace_type: WorkspaceType = WorkspaceType.PERSONAL,
        parent_workspace_id: Optional[str] = None,
        quotas: Optional[Dict[ResourceType, ResourceQuota]] = None,
        settings: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[str] = None
    ) -> Workspace:
        """Create a new workspace."""
        workspace = Workspace(
            workspace_id=workspace_id or str(uuid.uuid4())[:8],
            name=name,
            description=description,
            workspace_type=workspace_type,
            owner_id=owner_id,
            parent_workspace_id=parent_workspace_id,
            settings=settings or {}
        )

        # Apply quotas
        self._apply_default_quotas(workspace)
        if quotas:
            for resource_type, quota in quotas.items():
                workspace.quotas[resource_type] = quota

        # Add owner as member
        owner_member = WorkspaceMember(
            workspace_id=workspace.workspace_id,
            user_id=owner_id,
            role=MemberRole.OWNER,
            accepted_at=datetime.utcnow()
        )
        await self._backend.save_member(owner_member)

        # Save workspace
        workspace = await self._backend.save_workspace(workspace)

        # Log activity
        await self._log_activity(workspace.workspace_id, owner_id, "workspace_created", {
            "name": name,
            "type": workspace_type.value
        })

        logger.info(f"Created workspace: {workspace.workspace_id} - {name}")
        return workspace

    async def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """Get workspace by ID."""
        return await self._backend.get_workspace(workspace_id)

    async def update_workspace(
        self,
        workspace_id: str,
        user_id: str,
        **updates
    ) -> Optional[Workspace]:
        """Update workspace."""
        workspace = await self.get_workspace(workspace_id)
        if not workspace:
            return None

        # Check permissions
        if not await self._check_permission(workspace_id, user_id, "workspace.update"):
            raise PermissionError("Insufficient permissions")

        # Apply updates
        for key, value in updates.items():
            if hasattr(workspace, key) and key not in ("workspace_id", "owner_id", "created_at"):
                setattr(workspace, key, value)

        workspace = await self._backend.save_workspace(workspace)

        await self._log_activity(workspace_id, user_id, "workspace_updated", {"updates": list(updates.keys())})
        return workspace

    async def delete_workspace(self, workspace_id: str, user_id: str, force: bool = False) -> bool:
        """Delete or archive workspace."""
        workspace = await self.get_workspace(workspace_id)
        if not workspace:
            return False

        if not await self._check_permission(workspace_id, user_id, "workspace.delete"):
            raise PermissionError("Insufficient permissions")

        if force:
            result = await self._backend.delete_workspace(workspace_id)
            # Clean up members
            members = await self._backend.list_members(workspace_id, active_only=False)
            for member in members:
                await self._backend.delete_member(workspace_id, member.user_id)
        else:
            workspace.status = WorkspaceStatus.DELETED
            workspace.deleted_at = datetime.utcnow()
            await self._backend.save_workspace(workspace)

        await self._log_activity(workspace_id, user_id, "workspace_deleted", {"force": force})
        return True

    async def list_workspaces(
        self,
        user_id: Optional[str] = None,
        status: Optional[WorkspaceStatus] = None,
        workspace_type: Optional[WorkspaceType] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Workspace]:
        """List workspaces."""
        if user_id:
            # Get workspaces where user is a member
            # This would need a more efficient implementation
            all_workspaces = await self._backend.list_workspaces(status=status, workspace_type=workspace_type, limit=1000)
            workspaces = []
            for ws in all_workspaces:
                member = await self._backend.get_member(ws.workspace_id, user_id)
                if member and member.is_active:
                    workspaces.append(ws)
            return workspaces[offset:offset + limit]

        return await self._backend.list_workspaces(
            status=status,
            workspace_type=workspace_type,
            limit=limit,
            offset=offset
        )

    async def get_workspace_tree(self, root_id: str) -> Dict[str, Any]:
        """Get workspace hierarchy tree."""
        workspace = await self.get_workspace(root_id)
        if not workspace:
            return {}

        children = await self._backend.list_workspaces(
            parent_workspace_id=root_id
        )

        return {
            "workspace": workspace,
            "children": [
                await self.get_workspace_tree(child.workspace_id)
                for child in children
                if child.status == WorkspaceStatus.ACTIVE
            ]
        }

    # Member Management
    async def add_member(
        self,
        workspace_id: str,
        user_id: str,
        role: MemberRole = MemberRole.MEMBER,
        permissions: Optional[List[str]] = None,
        invited_by: Optional[str] = None
    ) -> WorkspaceMember:
        """Add member to workspace."""
        workspace = await self.get_workspace(workspace_id)
        if not workspace:
            raise ValueError("Workspace not found")

        if not await self._check_permission(workspace_id, invited_by or user_id, "member.add"):
            raise PermissionError("Insufficient permissions")

        member = await self._backend.get_member(workspace_id, user_id)
        if member:
            # Update existing
            member.role = role
            member.permissions = permissions or []
            member.is_active = True
            member.last_active_at = datetime.utcnow()
        else:
            member = WorkspaceMember(
                workspace_id=workspace_id,
                user_id=user_id,
                role=role,
                permissions=permissions or [],
                invited_by=invited_by,
                invited_at=datetime.utcnow() if invited_by else None,
                accepted_at=datetime.utcnow() if not invited_by else None
            )

        member = await self._backend.save_member(member)

        await self._log_activity(workspace_id, invited_by or user_id, "member_added", {
            "target_user": user_id,
            "role": role.value
        })

        return member

    async def remove_member(
        self,
        workspace_id: str,
        user_id: str,
        removed_by: str
    ) -> bool:
        """Remove member from workspace."""
        if not await self._check_permission(workspace_id, removed_by, "member.remove"):
            raise PermissionError("Insufficient permissions")

        # Can't remove owner
        member = await self._backend.get_member(workspace_id, user_id)
        if member and member.role == MemberRole.OWNER:
            raise ValueError("Cannot remove workspace owner")

        result = await self._backend.delete_member(workspace_id, user_id)

        if result:
            await self._log_activity(workspace_id, removed_by, "member_removed", {"target_user": user_id})

        return result

    async def update_member_role(
        self,
        workspace_id: str,
        user_id: str,
        role: MemberRole,
        updated_by: str
    ) -> Optional[WorkspaceMember]:
        """Update member role."""
        if not await self._check_permission(workspace_id, updated_by, "member.update"):
            raise PermissionError("Insufficient permissions")

        member = await self._backend.get_member(workspace_id, user_id)
        if not member:
            return None

        # Can't demote owner
        if member.role == MemberRole.OWNER and role != MemberRole.OWNER:
            raise ValueError("Cannot change owner role")

        member.role = role
        member = await self._backend.save_member(member)

        await self._log_activity(workspace_id, updated_by, "member_role_updated", {
            "target_user": user_id,
            "new_role": role.value
        })

        return member

    async def get_member(self, workspace_id: str, user_id: str) -> Optional[WorkspaceMember]:
        """Get workspace member."""
        return await self._backend.get_member(workspace_id, user_id)

    async def list_members(
        self,
        workspace_id: str,
        role: Optional[MemberRole] = None,
        active_only: bool = True
    ) -> List[WorkspaceMember]:
        """List workspace members."""
        return await self._backend.list_members(workspace_id, role, active_only)

    async def check_member_permission(
        self,
        workspace_id: str,
        user_id: str,
        permission: str
    ) -> bool:
        """Check if member has permission."""
        member = await self.get_member(workspace_id, user_id)
        if not member or not member.is_active:
            return False

        # Owners and admins have all permissions
        if member.role in (MemberRole.OWNER, MemberRole.ADMIN):
            return True

        return member.has_permission(permission)

    # Quota Management
    async def set_quota(
        self,
        workspace_id: str,
        user_id: str,
        resource_type: ResourceType,
        limit: int,
        warning_threshold: float = 0.8,
        hard_limit: bool = True
    ) -> Optional[ResourceQuota]:
        """Set resource quota for workspace."""
        workspace = await self.get_workspace(workspace_id)
        if not workspace:
            return None

        if not await self._check_permission(workspace_id, user_id, "quota.manage"):
            raise PermissionError("Insufficient permissions")

        quota = ResourceQuota(
            resource_type=resource_type,
            limit=limit,
            warning_threshold=warning_threshold,
            hard_limit=hard_limit
        )
        workspace.quotas[resource_type] = quota
        await self._backend.save_workspace(workspace)

        await self._log_activity(workspace_id, user_id, "quota_updated", {
            "resource_type": resource_type.value,
            "limit": limit
        })

        return quota

    async def get_quota(self, workspace_id: str, resource_type: ResourceType) -> Optional[ResourceQuota]:
        """Get resource quota."""
        workspace = await self.get_workspace(workspace_id)
        if workspace:
            return workspace.get_quota(resource_type)
        return None

    async def get_all_quotas(self, workspace_id: str) -> Dict[ResourceType, ResourceQuota]:
        """Get all quotas for workspace."""
        workspace = await self.get_workspace(workspace_id)
        return workspace.quotas if workspace else {}

    async def consume_quota(
        self,
        workspace_id: str,
        resource_type: ResourceType,
        amount: int = 1
    ) -> bool:
        """Consume quota."""
        workspace = await self.get_workspace(workspace_id)
        if not workspace:
            return False

        result = workspace.consume_quota(resource_type, amount)
        if result:
            await self._backend.save_workspace(workspace)
        return result

    async def release_quota(
        self,
        workspace_id: str,
        resource_type: ResourceType,
        amount: int = 1
    ) -> bool:
        """Release quota."""
        workspace = await self.get_workspace(workspace_id)
        if not workspace:
            return False

        result = workspace.release_quota(resource_type, amount)
        if result:
            await self._backend.save_workspace(workspace)
        return result

    async def check_quota(
        self,
        workspace_id: str,
        resource_type: ResourceType,
        amount: int = 1
    ) -> bool:
        """Check if quota available."""
        workspace = await self.get_workspace(workspace_id)
        if not workspace:
            return False
        return workspace.check_quota(resource_type, amount)

    # Invitations
    async def create_invitation(
        self,
        workspace_id: str,
        email: str,
        role: MemberRole = MemberRole.MEMBER,
        permissions: Optional[List[str]] = None,
        invited_by: str = "",
        expires_in_days: int = 7
    ) -> WorkspaceInvitation:
        """Create workspace invitation."""
        if not await self._check_permission(workspace_id, invited_by, "invitation.create"):
            raise PermissionError("Insufficient permissions")

        invitation = WorkspaceInvitation(
            workspace_id=workspace_id,
            email=email,
            role=role,
            permissions=permissions or [],
            invited_by=invited_by,
            expires_at=datetime.utcnow() + timedelta(days=expires_in_days)
        )

        invitation = await self._backend.save_invitation(invitation)

        await self._log_activity(workspace_id, invited_by, "invitation_created", {
            "email": email,
            "role": role.value
        })

        return invitation

    async def accept_invitation(
        self,
        token: str,
        user_id: str
    ) -> Optional[WorkspaceMember]:
        """Accept workspace invitation."""
        invitation = await self._backend.get_invitation(token)
        if not invitation or invitation.status != InvitationStatus.PENDING:
            return None

        if invitation.expires_at < datetime.utcnow():
            invitation.status = InvitationStatus.EXPIRED
            await self._backend.save_invitation(invitation)
            return None

        # Add member
        member = await self.add_member(
            invitation.workspace_id,
            user_id,
            invitation.role,
            invitation.permissions,
            invited_by=invitation.invited_by
        )

        invitation.status = InvitationStatus.ACCEPTED
        invitation.accepted_at = datetime.utcnow()
        await self._backend.save_invitation(invitation)

        await self._log_activity(invitation.workspace_id, user_id, "invitation_accepted", {
            "invitation_id": invitation.invitation_id
        })

        return member

    async def decline_invitation(self, token: str) -> bool:
        """Decline invitation."""
        invitation = await self._backend.get_invitation(token)
        if not invitation or invitation.status != InvitationStatus.PENDING:
            return False

        invitation.status = InvitationStatus.DECLINED
        await self._backend.save_invitation(invitation)
        return True

    async def revoke_invitation(self, invitation_id: str, revoked_by: str) -> bool:
        """Revoke invitation."""
        invitations = await self._backend.list_invitations("", InvitationStatus.PENDING)
        invitation = next((i for i in invitations if i.invitation_id == invitation_id), None)

        if not invitation:
            return False

        if not await self._check_permission(invitation.workspace_id, revoked_by, "invitation.revoke"):
            raise PermissionError("Insufficient permissions")

        invitation.status = InvitationStatus.REVOKED
        await self._backend.save_invitation(invitation)

        await self._log_activity(invitation.workspace_id, revoked_by, "invitation_revoked", {
            "invitation_id": invitation_id
        })

        return True

    async def list_invitations(
        self,
        workspace_id: str,
        status: Optional[InvitationStatus] = None
    ) -> List[WorkspaceInvitation]:
        """List workspace invitations."""
        return await self._backend.list_invitations(workspace_id, status)

    # Activity Logging
    async def _log_activity(
        self,
        workspace_id: str,
        user_id: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None
    ) -> None:
        """Log workspace activity."""
        activity = WorkspaceActivity(
            workspace_id=workspace_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {}
        )
        await self._backend.log_activity(activity)

    async def get_activities(
        self,
        workspace_id: str,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[WorkspaceActivity]:
        """Get workspace activities."""
        return await self._backend.get_activities(workspace_id, user_id, action, since, limit)

    # Permission Helper
    async def _check_permission(
        self,
        workspace_id: str,
        user_id: str,
        permission: str
    ) -> bool:
        """Check if user has permission in workspace."""
        return await self.check_member_permission(workspace_id, user_id, permission)

    # Cleanup
    async def _cleanup_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(3600)  # Every hour
                await self._cleanup_expired_invitations()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

    async def _cleanup_expired_invitations(self) -> None:
        """Clean up expired invitations."""
        invitations = await self._backend.list_invitations("", InvitationStatus.PENDING)
        now = datetime.utcnow()
        for inv in invitations:
            if inv.expires_at < now:
                inv.status = InvitationStatus.EXPIRED
                await self._backend.save_invitation(inv)

    # Module Operations
    async def execute(self, operation: str, **kwargs) -> Any:
        mapping = {
            "create_workspace": self.create_workspace,
            "get_workspace": self.get_workspace,
            "update_workspace": self.update_workspace,
            "delete_workspace": self.delete_workspace,
            "list_workspaces": self.list_workspaces,
            "get_workspace_tree": self.get_workspace_tree,
            "add_member": self.add_member,
            "remove_member": self.remove_member,
            "update_member_role": self.update_member_role,
            "get_member": self.get_member,
            "list_members": self.list_members,
            "check_permission": self.check_member_permission,
            "set_quota": self.set_quota,
            "get_quota": self.get_quota,
            "get_all_quotas": self.get_all_quotas,
            "consume_quota": self.consume_quota,
            "release_quota": self.release_quota,
            "check_quota": self.check_quota,
            "create_invitation": self.create_invitation,
            "accept_invitation": self.accept_invitation,
            "decline_invitation": self.decline_invitation,
            "revoke_invitation": self.revoke_invitation,
            "list_invitations": self.list_invitations,
            "get_activities": self.get_activities,
        }
        if operation in mapping:
            return await mapping[operation](**kwargs)
        raise NotImplementedError(f"Operation '{operation}' not supported")


__all__ = [
    "WorkspaceModule",
    "WorkspaceBackend",
    "LocalWorkspaceBackend",
    "Workspace",
    "WorkspaceMember",
    "WorkspaceInvitation",
    "WorkspaceActivity",
    "ResourceQuota",
    "WorkspaceStatus",
    "WorkspaceType",
    "ResourceType",
    "MemberRole",
    "InvitationStatus",
]