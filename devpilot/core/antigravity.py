"""Antigravity integration: launcher, process detection, window reuse, and CLI options."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple
import psutil

from devpilot.core.models import AntigravityConfig


def find_antigravity_executable() -> Optional[str]:
    """
    Auto-detect the Antigravity IDE or Antigravity desktop executable on Windows.
    Prefers the IDE command line wrapper 'antigravity-ide.cmd' which cleanly supports
    workspace folders and window reuse arguments (-r, -n).
    """
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    candidates = []

    if local_app_data:
        candidates.extend([
            # Antigravity IDE CLI wrapper (ideal for workspace automation)
            str(Path(local_app_data) / "Programs" / "Antigravity IDE" / "bin" / "antigravity-ide.cmd"),
            # Antigravity IDE executable
            str(Path(local_app_data) / "Programs" / "Antigravity IDE" / "Antigravity IDE.exe"),
            # Antigravity 2.0 Electron Desktop App
            str(Path(local_app_data) / "Programs" / "antigravity" / "Antigravity.exe"),
        ])

    # Check Program Files
    program_files = os.environ.get("ProgramFiles", "")
    if program_files:
        candidates.extend([
            str(Path(program_files) / "Antigravity IDE" / "bin" / "antigravity-ide.cmd"),
            str(Path(program_files) / "Antigravity IDE" / "Antigravity IDE.exe"),
            str(Path(program_files) / "Antigravity" / "Antigravity.exe"),
        ])

    for path in candidates:
        if Path(path).exists():
            return path

    # Check PATH
    which_cmd = shutil.which("antigravity-ide") or shutil.which("antigravity") or shutil.which("agy")
    if which_cmd:
        return which_cmd

    return None


def is_antigravity_running() -> Tuple[bool, List[int]]:
    """
    Check if Antigravity IDE or Antigravity app process is currently active.
    Returns (is_running, list of process IDs).
    """
    pids = []
    target_names = {"antigravity ide.exe", "antigravity.exe"}
    
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            name = proc.info.get("name")
            if name and name.lower() in target_names:
                pids.append(proc.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    return len(pids) > 0, pids


def is_workspace_open_in_antigravity(workspace_path: str) -> bool:
    """
    Check if the specific workspace path is already loaded by a running Antigravity process.
    """
    norm_target = str(Path(workspace_path).resolve()).lower()
    target_names = {"antigravity ide.exe", "antigravity.exe"}

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = proc.info.get("name")
            if name and name.lower() in target_names:
                cmdline = proc.info.get("cmdline") or []
                for arg in cmdline:
                    if norm_target in arg.lower():
                        return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    return False


def build_antigravity_launch_command(
    executable_path: Optional[str],
    workspace_path: str,
    config: Optional[AntigravityConfig] = None
) -> Tuple[List[str], str]:
    """
    Build the exact command list to launch the Antigravity workspace.
    Returns (cmd_list, description).
    """
    exe = executable_path or find_antigravity_executable()
    if not exe or not Path(exe).exists():
        raise FileNotFoundError(f"Antigravity executable not found at '{exe}' and auto-detection failed.")

    cfg = config or AntigravityConfig()
    norm_workspace = str(Path(workspace_path).resolve())
    
    cmd = [exe]

    # If calling the .cmd wrapper or IDE executable
    is_ide = "ide" in exe.lower()

    if is_ide:
        if cfg.reuse_window:
            cmd.append("-r")  # Force reuse opened window
        elif cfg.new_window:
            cmd.append("-n")  # Force new window

        if cfg.profile_name:
            cmd.extend(["--profile", cfg.profile_name])

    # Add workspace path
    cmd.append(norm_workspace)

    # Optional initial files to open
    for file_name in cfg.initial_files:
        target_file = Path(norm_workspace) / file_name
        if target_file.exists():
            cmd.append(str(target_file))

    desc = f"Antigravity {'(Reuse Window)' if cfg.reuse_window else '(New Window)'}: {norm_workspace}"
    return cmd, desc


def launch_antigravity_workspace(
    workspace_path: str,
    executable_path: Optional[str] = None,
    config: Optional[AntigravityConfig] = None
) -> subprocess.Popen:
    """
    Launch or focus the Antigravity workspace in a detached process.
    Returns the created subprocess.Popen instance.
    """
    cmd, desc = build_antigravity_launch_command(executable_path, workspace_path, config)
    
    # Detach process so it persists independently of DevPilot
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

    proc = subprocess.Popen(
        cmd,
        cwd=workspace_path,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
        shell=False
    )
    return proc
