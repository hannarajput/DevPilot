"""Data models for DevPilot workspace automation."""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Optional, Any
import uuid
import datetime


class TaskType(str, Enum):
    ANTIGRAVITY = "antigravity"
    TERMINAL = "terminal"
    COMMAND = "command"
    TOOL_CHECK = "tool_check"
    HEALTH_CHECK = "health_check"
    BROWSER = "browser"
    APPLICATION = "application"
    RESOURCE = "resource"


class ResourceType(str, Enum):
    IDE = "ide"
    AI_CHAT = "ai_chat"
    WEBSITE = "website"
    LOCAL_FILE = "local_file"
    CUSTOM_URL = "custom_url"
    APPLICATION = "application"


@dataclass
class ResourceConfig:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    resource_type: ResourceType = ResourceType.WEBSITE
    target: str = ""  # URL, file path, directory path, or executable
    enabled: bool = True
    order: int = 0
    description: str = ""
    extra_args: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["resource_type"] = self.resource_type.value if isinstance(self.resource_type, ResourceType) else str(self.resource_type)
        d["target"] = str(self.target)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResourceConfig":
        data = dict(data)
        if "resource_type" in data and isinstance(data["resource_type"], str):
            try:
                data["resource_type"] = ResourceType(data["resource_type"])
            except ValueError:
                data["resource_type"] = ResourceType.CUSTOM_URL
        return cls(**data)


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class ProjectType(str, Enum):
    PYTHON = "python"
    FLUTTER = "flutter"
    NODEJS = "nodejs"
    GIT = "git"
    OTHER = "other"


class ProfileType(str, Enum):
    BASIC = "Basic Workspace"
    DEV = "Development"
    FULL = "Full Workspace"
    CUSTOM = "Custom"


@dataclass
class TaskConfig:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    task_type: TaskType = TaskType.COMMAND
    enabled: bool = True
    order: int = 0
    is_one_time: bool = False  # e.g., setup/install commands skipped on resume
    approved: bool = True       # approved startup command guard
    target: str = ""           # command line, executable path, URL, or tool name
    working_dir: Optional[str] = None
    terminal_type: Optional[str] = None  # 'wt', 'powershell', 'cmd'
    arguments: List[str] = field(default_factory=list)
    timeout_seconds: int = 30
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["task_type"] = self.task_type.value if isinstance(self.task_type, TaskType) else str(self.task_type)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskConfig":
        data = dict(data)
        if "task_type" in data and isinstance(data["task_type"], str):
            try:
                data["task_type"] = TaskType(data["task_type"])
            except ValueError:
                data["task_type"] = TaskType.COMMAND
        return cls(**data)


@dataclass
class ProfileConfig:
    name: str = "Development"
    profile_type: str = ProfileType.DEV.value
    description: str = ""
    enabled_task_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProfileConfig":
        return cls(**data)


@dataclass
class IDEPreference:
    ide_name: str = "Antigravity IDE"
    executable_path: str = ""
    remembered: bool = False
    reuse_window: bool = True
    new_window: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IDEPreference":
        return cls(**data)


@dataclass
class AntigravityConfig:
    executable_path: str = ""
    use_ide: bool = True
    reuse_window: bool = True
    new_window: bool = False
    profile_name: Optional[str] = None
    initial_files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AntigravityConfig":
        return cls(**data)


@dataclass
class ProjectConfig:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    root_path: str = ""
    project_type: ProjectType = ProjectType.OTHER
    description: str = ""
    antigravity: AntigravityConfig = field(default_factory=AntigravityConfig)
    ide_preference: IDEPreference = field(default_factory=IDEPreference)
    resources: List[ResourceConfig] = field(default_factory=list)
    tasks: List[TaskConfig] = field(default_factory=list)
    profiles: Dict[str, ProfileConfig] = field(default_factory=dict)
    active_profile: str = ProfileType.DEV.value
    created_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    last_launched_at: Optional[str] = None
    last_launch_status: str = "Ready"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "root_path": str(self.root_path),
            "project_type": self.project_type.value if isinstance(self.project_type, ProjectType) else str(self.project_type),
            "description": self.description,
            "antigravity": self.antigravity.to_dict(),
            "ide_preference": self.ide_preference.to_dict(),
            "resources": [r.to_dict() for r in self.resources],
            "tasks": [t.to_dict() for t in self.tasks],
            "profiles": {k: p.to_dict() for k, p in self.profiles.items()},
            "active_profile": self.active_profile,
            "created_at": self.created_at,
            "last_launched_at": self.last_launched_at,
            "last_launch_status": self.last_launch_status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectConfig":
        data = dict(data)
        if "project_type" in data and isinstance(data["project_type"], str):
            try:
                data["project_type"] = ProjectType(data["project_type"])
            except ValueError:
                data["project_type"] = ProjectType.OTHER

        if "antigravity" in data and isinstance(data["antigravity"], dict):
            data["antigravity"] = AntigravityConfig.from_dict(data["antigravity"])
        else:
            data["antigravity"] = AntigravityConfig()

        if "ide_preference" in data and isinstance(data["ide_preference"], dict):
            data["ide_preference"] = IDEPreference.from_dict(data["ide_preference"])
        elif data.get("antigravity") and data["antigravity"].executable_path:
            data["ide_preference"] = IDEPreference(
                ide_name="Antigravity IDE",
                executable_path=data["antigravity"].executable_path,
                remembered=True
            )
        else:
            data["ide_preference"] = IDEPreference()

        if "resources" in data and isinstance(data["resources"], list):
            data["resources"] = [ResourceConfig.from_dict(r) for r in data["resources"]]
        else:
            data["resources"] = []

        if "tasks" in data and isinstance(data["tasks"], list):
            data["tasks"] = [TaskConfig.from_dict(t) for t in data["tasks"]]
        else:
            data["tasks"] = []

        if "profiles" in data and isinstance(data["profiles"], dict):
            data["profiles"] = {k: ProfileConfig.from_dict(v) for k, v in data["profiles"].items()}
        else:
            data["profiles"] = {}

        return cls(**data)

    def add_resource(self, resource: ResourceConfig):
        """Add or update a resource in this project."""
        for i, r in enumerate(self.resources):
            if r.id == resource.id:
                self.resources[i] = resource
                return
        if resource.order == 0:
            resource.order = len(self.resources) + 1
        self.resources.append(resource)

    def remove_resource(self, resource_id: str) -> bool:
        """Remove a resource by ID."""
        initial_len = len(self.resources)
        self.resources = [r for r in self.resources if r.id != resource_id]
        return len(self.resources) < initial_len

    def get_resource(self, resource_id: str) -> Optional[ResourceConfig]:
        """Find resource by ID."""
        for r in self.resources:
            if r.id == resource_id:
                return r
        return None

    def get_enabled_resources(self) -> List[ResourceConfig]:
        """Return all enabled resources sorted by order."""
        enabled = [r for r in self.resources if r.enabled]
        enabled.sort(key=lambda r: r.order)
        return enabled


@dataclass
class SessionHistory:
    last_project_id: Optional[str] = None
    last_project_name: Optional[str] = None
    last_profile: Optional[str] = None
    last_launch_time: Optional[str] = None
    executed_task_ids: List[str] = field(default_factory=list)
    completed_task_ids: List[str] = field(default_factory=list)
    failed_task_ids: List[str] = field(default_factory=list)
    restored_items: List[str] = field(default_factory=list)
    unrestored_items: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionHistory":
        return cls(**data)


@dataclass
class AppSettings:
    default_antigravity_path: str = ""
    default_terminal: str = "wt"
    autostart_on_windows_login: bool = False
    confirm_unapproved_commands: bool = True
    redact_secrets: bool = True
    theme: str = "dark"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppSettings":
        return cls(**data)


@dataclass
class TaskExecutionResult:
    task_id: str
    task_name: str
    status: TaskStatus
    message: str = ""
    exit_code: Optional[int] = None
    duration_seconds: float = 0.0
    output_preview: str = ""
