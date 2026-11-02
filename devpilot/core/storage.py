"""Persistence layer for DevPilot configurations and session history."""

import os
import json
import shutil
import tempfile
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from devpilot.core.models import (
    ProjectConfig,
    AppSettings,
    SessionHistory,
    ProjectType,
    ProfileType,
    ProfileConfig,
    TaskConfig,
    TaskType,
    AntigravityConfig,
)


def get_default_config_dir() -> Path:
    """Return standard configuration directory (%APPDATA%/DevPilot on Windows or ~/.devpilot)."""
    app_data = os.environ.get("APPDATA")
    if app_data:
        base = Path(app_data) / "DevPilot"
    else:
        base = Path.home() / ".devpilot"
    base.mkdir(parents=True, exist_ok=True)
    return base


class StorageManager:
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = Path(config_dir) if config_dir else get_default_config_dir()
        self.projects_file = self.config_dir / "projects.json"
        self.settings_file = self.config_dir / "settings.json"
        self.session_file = self.config_dir / "session.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _atomic_write_json(self, file_path: Path, data: dict):
        """Atomically write JSON to file via temporary file to prevent corruption."""
        temp_dir = self.config_dir / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        with tempfile.NamedTemporaryFile("w", dir=temp_dir, delete=False, encoding="utf-8") as tf:
            json.dump(data, tf, indent=2)
            temp_name = tf.name

        # Make backup of existing file
        if file_path.exists():
            backup_path = file_path.with_suffix(".bak")
            try:
                shutil.copy2(file_path, backup_path)
            except Exception:
                pass

        shutil.move(temp_name, file_path)

    # ------------------ Projects ------------------ #
    def load_projects(self) -> List[ProjectConfig]:
        if not self.projects_file.exists():
            return []
        try:
            with open(self.projects_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            projects = []
            for item in data.get("projects", []):
                try:
                    projects.append(ProjectConfig.from_dict(item))
                except Exception as e:
                    print(f"Error parsing project: {e}")
            return projects
        except Exception as e:
            print(f"Error loading {self.projects_file}: {e}")
            # Try restore from backup
            backup = self.projects_file.with_suffix(".bak")
            if backup.exists():
                try:
                    with open(backup, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    return [ProjectConfig.from_dict(p) for p in data.get("projects", [])]
                except Exception:
                    pass
            return []

    def save_projects(self, projects: List[ProjectConfig]):
        data = {
            "version": 1,
            "projects": [p.to_dict() for p in projects],
        }
        self._atomic_write_json(self.projects_file, data)

    def get_project(self, project_id: str) -> Optional[ProjectConfig]:
        for p in self.load_projects():
            if p.id == project_id:
                return p
        return None

    def save_or_update_project(self, project: ProjectConfig):
        projects = self.load_projects()
        updated = False
        for i, p in enumerate(projects):
            if p.id == project.id:
                projects[i] = project
                updated = True
                break
        if not updated:
            projects.append(project)
        self.save_projects(projects)

    def delete_project(self, project_id: str) -> bool:
        projects = self.load_projects()
        initial_len = len(projects)
        projects = [p for p in projects if p.id != project_id]
        if len(projects) != initial_len:
            self.save_projects(projects)
            return True
        return False

    # ------------------ Settings ------------------ #
    def load_settings(self) -> AppSettings:
        if not self.settings_file.exists():
            return AppSettings()
        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return AppSettings.from_dict(data)
        except Exception:
            return AppSettings()

    def save_settings(self, settings: AppSettings):
        self._atomic_write_json(self.settings_file, settings.to_dict())

    # ------------------ Session History ------------------ #
    def load_session(self) -> SessionHistory:
        if not self.session_file.exists():
            return SessionHistory()
        try:
            with open(self.session_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return SessionHistory.from_dict(data)
        except Exception:
            return SessionHistory()

    def save_session(self, session: SessionHistory):
        self._atomic_write_json(self.session_file, session.to_dict())
