"""Project type sniffing, system tool detection, and health checks."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from devpilot.core.models import (
    ProjectType,
    ProfileType,
    ProfileConfig,
    TaskConfig,
    TaskType,
    AntigravityConfig,
    ProjectConfig,
)


def detect_project_type(root_path: str) -> Tuple[ProjectType, List[str]]:
    """
    Sniff the project directory to detect its real project type based on actual files.
    Returns (ProjectType, list of matching indicator files/folders).
    """
    p = Path(root_path)
    if not p.is_dir():
        return ProjectType.OTHER, []

    indicators: List[str] = []

    # 1. Check Flutter
    flutter_files = ["pubspec.yaml", "pubspec.yml"]
    for f in flutter_files:
        if (p / f).exists():
            indicators.append(f)
    if (p / "lib" / "main.dart").exists():
        indicators.append("lib/main.dart")
    if indicators:
        return ProjectType.FLUTTER, indicators

    # 2. Check Node.js
    node_files = ["package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "tsconfig.json"]
    for f in node_files:
        if (p / f).exists():
            indicators.append(f)
    if indicators:
        return ProjectType.NODEJS, indicators

    # 3. Check Python
    py_files = ["pyproject.toml", "requirements.txt", "setup.py", "Pipfile", "environment.yml", "tox.ini"]
    for f in py_files:
        if (p / f).exists():
            indicators.append(f)
    # Check if there are any .py files in root
    py_scripts = list(p.glob("*.py"))
    if py_scripts:
        indicators.append(py_scripts[0].name)
    if indicators:
        return ProjectType.PYTHON, indicators

    # 4. Check Git
    if (p / ".git").exists():
        indicators.append(".git")
        return ProjectType.GIT, indicators

    return ProjectType.OTHER, []


def detect_installed_tools() -> Dict[str, Dict[str, Any]]:
    """
    Dynamically discover installed development CLI tools and return their paths and versions.
    """
    tools = [
        ("git", ["git", "--version"]),
        ("python", ["python", "--version"]),
        ("node", ["node", "--version"]),
        ("npm", ["npm", "--version"]),
        ("flutter", ["flutter", "--version"]),
        ("wt", ["wt", "--version"]),
        ("powershell", ["powershell", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"]),
        ("cmd", ["cmd", "/c", "ver"]),
    ]

    results = {}
    for name, ver_cmd in tools:
        path = shutil.which(name)
        # Windows-specific search for wt
        if not path and name == "wt":
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            wt_path = Path(local_appdata) / "Microsoft" / "WindowsApps" / "wt.exe"
            if wt_path.exists():
                path = str(wt_path)

        # Windows-specific search for flutter
        if not path and name == "flutter":
            c_flutter = Path("C:/flutter/bin/flutter.bat")
            if c_flutter.exists():
                path = str(c_flutter)

        if path:
            version_str = "Installed"
            try:
                # Run quick version check with 3s timeout
                proc = subprocess.run(
                    ver_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=3,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                )
                output = proc.stdout.strip() or proc.stderr.strip()
                if output:
                    version_str = output.splitlines()[0]
            except Exception:
                pass
            results[name] = {"available": True, "path": path, "version": version_str}
        else:
            results[name] = {"available": False, "path": None, "version": "Not found"}

    return results


def check_git_status(repo_path: str) -> Dict[str, Any]:
    """Retrieve Git repository status: branch, dirty files, ahead/behind count."""
    p = Path(repo_path)
    if not (p / ".git").exists():
        return {"is_git": False, "message": "Not a Git repository"}

    git_path = shutil.which("git")
    if not git_path:
        return {"is_git": True, "message": "Git CLI not found"}

    try:
        # Get current branch
        branch_proc = subprocess.run(
            ["git", "-C", repo_path, "rev-parse", "--abbrev-ref", "HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        branch = branch_proc.stdout.strip() if branch_proc.returncode == 0 else "unknown"

        # Get status porcelain
        status_proc = subprocess.run(
            ["git", "-C", repo_path, "status", "--porcelain"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        status_lines = [line.strip() for line in status_proc.stdout.splitlines() if line.strip()]

        # Check uncommitted count
        modified_count = len(status_lines)

        return {
            "is_git": True,
            "branch": branch,
            "modified_count": modified_count,
            "clean": modified_count == 0,
            "files": status_lines[:10],  # sample up to 10 files
            "message": f"Branch: {branch} | Modified files: {modified_count}"
        }
    except Exception as e:
        return {"is_git": True, "error": str(e), "message": f"Git check failed: {e}"}


def check_project_health(project: ProjectConfig) -> Dict[str, Any]:
    """Run comprehensive pre-flight health checks for a project."""
    root = Path(project.root_path)
    report = {
        "project_name": project.name,
        "root_exists": root.is_dir(),
        "project_type": project.project_type.value,
        "checks": [],
        "passed": True
    }

    if not root.is_dir():
        report["checks"].append({"name": "Root Folder", "status": "FAIL", "message": f"Directory does not exist: {project.root_path}"})
        report["passed"] = False
        return report

    report["checks"].append({"name": "Root Folder", "status": "PASS", "message": f"Found: {project.root_path}"})

    # Antigravity executable check
    ag_path = project.antigravity.executable_path
    if ag_path and Path(ag_path).exists():
        report["checks"].append({"name": "Antigravity Path", "status": "PASS", "message": f"Verified: {ag_path}"})
    else:
        report["checks"].append({"name": "Antigravity Path", "status": "WARN", "message": f"Path '{ag_path}' not found, will attempt auto-discovery."})

    # Git check
    git_res = check_git_status(project.root_path)
    if git_res.get("is_git"):
        if git_res.get("clean"):
            report["checks"].append({"name": "Git Status", "status": "PASS", "message": f"Branch {git_res.get('branch')} is clean."})
        else:
            report["checks"].append({"name": "Git Status", "status": "WARN", "message": f"Branch {git_res.get('branch')}: {git_res.get('modified_count')} uncommitted change(s)."})

    # Specific project type checks
    if project.project_type == ProjectType.PYTHON:
        venv_exists = (root / ".venv").is_dir() or (root / "venv").is_dir() or (root / "env").is_dir()
        if venv_exists:
            report["checks"].append({"name": "Python Environment", "status": "PASS", "message": "Virtual environment folder detected."})
        else:
            report["checks"].append({"name": "Python Environment", "status": "WARN", "message": "No .venv/venv found. System Python will be used."})

    elif project.project_type == ProjectType.NODEJS:
        nm_exists = (root / "node_modules").is_dir()
        if nm_exists:
            report["checks"].append({"name": "Node Modules", "status": "PASS", "message": "node_modules directory found."})
        else:
            report["checks"].append({"name": "Node Modules", "status": "WARN", "message": "node_modules missing. 'npm install' may be needed."})

    elif project.project_type == ProjectType.FLUTTER:
        pubspec = (root / "pubspec.yaml").exists()
        if pubspec:
            report["checks"].append({"name": "Flutter Pubspec", "status": "PASS", "message": "pubspec.yaml verified."})
        else:
            report["checks"].append({"name": "Flutter Pubspec", "status": "FAIL", "message": "pubspec.yaml missing."})
            report["passed"] = False

    return report


def generate_default_project_config(root_path: str, name: Optional[str] = None) -> ProjectConfig:
    """Auto-detect project type and generate smart default profiles and tasks."""
    p = Path(root_path).resolve()
    proj_type, indicators = detect_project_type(str(p))
    proj_name = name or p.name or "My Project"

    tasks: List[TaskConfig] = []

    # 1. Antigravity task (always task #1)
    ag_task = TaskConfig(
        id="task_ag",
        name="Launch Antigravity Workspace",
        task_type=TaskType.ANTIGRAVITY,
        enabled=True,
        order=1,
        is_one_time=False,
        approved=True,
        target=str(p),
        description="Open workspace root in Antigravity IDE"
    )
    tasks.append(ag_task)

    # 2. Tool checks & Terminal commands depending on project type
    if proj_type == ProjectType.PYTHON:
        tasks.append(TaskConfig(
            id="task_tool_python",
            name="Verify Python Runtime",
            task_type=TaskType.TOOL_CHECK,
            enabled=True,
            order=2,
            target="python",
            description="Ensure Python 3 is installed on system"
        ))
        tasks.append(TaskConfig(
            id="task_health_git",
            name="Check Git Status",
            task_type=TaskType.HEALTH_CHECK,
            enabled=True,
            order=3,
            target="git",
            description="Check uncommitted changes and active branch"
        ))
        tasks.append(TaskConfig(
            id="task_term_main",
            name="Open Development Terminal",
            task_type=TaskType.TERMINAL,
            enabled=True,
            order=4,
            working_dir=str(p),
            terminal_type="wt",
            description="Open interactive terminal in project root"
        ))

    elif proj_type == ProjectType.NODEJS:
        tasks.append(TaskConfig(
            id="task_tool_node",
            name="Verify Node.js & npm",
            task_type=TaskType.TOOL_CHECK,
            enabled=True,
            order=2,
            target="node",
            description="Ensure Node runtime is available"
        ))
        tasks.append(TaskConfig(
            id="task_health_git",
            name="Check Git Status",
            task_type=TaskType.HEALTH_CHECK,
            enabled=True,
            order=3,
            target="git",
            description="Check uncommitted changes and branch"
        ))
        tasks.append(TaskConfig(
            id="task_term_dev",
            name="Dev Server Terminal",
            task_type=TaskType.TERMINAL,
            enabled=True,
            order=4,
            working_dir=str(p),
            terminal_type="wt",
            description="Open terminal for dev server"
        ))
        tasks.append(TaskConfig(
            id="task_browser_local",
            name="Open Localhost Web Page",
            task_type=TaskType.BROWSER,
            enabled=False,  # disabled in basic, enabled in full
            order=5,
            target="http://localhost:3000",
            description="Open frontend URL in default browser"
        ))

    elif proj_type == ProjectType.FLUTTER:
        tasks.append(TaskConfig(
            id="task_tool_flutter",
            name="Verify Flutter SDK",
            task_type=TaskType.TOOL_CHECK,
            enabled=True,
            order=2,
            target="flutter",
            description="Ensure Flutter CLI is available"
        ))
        tasks.append(TaskConfig(
            id="task_health_git",
            name="Check Git Status",
            task_type=TaskType.HEALTH_CHECK,
            enabled=True,
            order=3,
            target="git",
            description="Check uncommitted changes and branch"
        ))
        tasks.append(TaskConfig(
            id="task_term_flutter",
            name="Flutter Terminal",
            task_type=TaskType.TERMINAL,
            enabled=True,
            order=4,
            working_dir=str(p),
            terminal_type="wt",
            description="Open terminal in Flutter project root"
        ))

    else:
        tasks.append(TaskConfig(
            id="task_tool_git",
            name="Verify Git CLI",
            task_type=TaskType.TOOL_CHECK,
            enabled=True,
            order=2,
            target="git",
            description="Ensure Git CLI is available"
        ))
        tasks.append(TaskConfig(
            id="task_term_main",
            name="Project Terminal",
            task_type=TaskType.TERMINAL,
            enabled=True,
            order=3,
            working_dir=str(p),
            terminal_type="wt",
            description="Open interactive terminal in project root"
        ))

    all_task_ids = [t.id for t in tasks]
    basic_task_ids = ["task_ag"]
    dev_task_ids = [t.id for t in tasks if t.task_type != TaskType.BROWSER and t.task_type != TaskType.APPLICATION]

    profiles = {
        ProfileType.BASIC.value: ProfileConfig(
            name=ProfileType.BASIC.value,
            profile_type=ProfileType.BASIC.value,
            description="Open Antigravity workspace only",
            enabled_task_ids=basic_task_ids
        ),
        ProfileType.DEV.value: ProfileConfig(
            name=ProfileType.DEV.value,
            profile_type=ProfileType.DEV.value,
            description="Antigravity, terminals, and dev checks",
            enabled_task_ids=dev_task_ids
        ),
        ProfileType.FULL.value: ProfileConfig(
            name=ProfileType.FULL.value,
            profile_type=ProfileType.FULL.value,
            description="Full workspace: Antigravity, terminals, tools, and URLs",
            enabled_task_ids=all_task_ids
        ),
        ProfileType.CUSTOM.value: ProfileConfig(
            name=ProfileType.CUSTOM.value,
            profile_type=ProfileType.CUSTOM.value,
            description="Custom selection of tasks",
            enabled_task_ids=dev_task_ids.copy()
        ),
    }

    return ProjectConfig(
        name=proj_name,
        root_path=str(p),
        project_type=proj_type,
        description=f"Auto-configured {proj_type.value.capitalize()} project ({', '.join(indicators) if indicators else 'general'})",
        antigravity=AntigravityConfig(),
        tasks=tasks,
        profiles=profiles,
        active_profile=ProfileType.DEV.value,
    )
