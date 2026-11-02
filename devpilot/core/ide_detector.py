"""Comprehensive IDE detection and workspace launcher across all installed laptop IDEs."""

import os
import glob
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Any

from devpilot.core.models import IDEPreference


def detect_installed_ides() -> List[Dict[str, Any]]:
    """
    Scan the laptop's file system and PATH to discover all available IDEs and code editors.
    Returns a deduplicated list of discovered IDE entries.
    """
    discovered: List[Dict[str, Any]] = []
    seen_paths = set()

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    prog_files = os.environ.get("ProgramFiles", "C:\\Program Files")
    prog_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")

    # 1. Antigravity IDE (Primary / Recommended)
    ag_ide_candidates = [
        ("Antigravity IDE", Path(local_app_data) / "Programs" / "Antigravity IDE" / "bin" / "antigravity-ide.cmd"),
        ("Antigravity IDE", Path(local_app_data) / "Programs" / "Antigravity IDE" / "Antigravity IDE.exe"),
        ("Antigravity IDE", Path(prog_files) / "Antigravity IDE" / "bin" / "antigravity-ide.cmd"),
        ("Antigravity IDE", Path(prog_files) / "Antigravity IDE" / "Antigravity IDE.exe"),
    ]
    for label, p in ag_ide_candidates:
        p_str = str(p)
        if p.exists() and p_str.lower() not in seen_paths:
            seen_paths.add(p_str.lower())
            discovered.append({
                "id": "antigravity_ide",
                "name": "Antigravity IDE",
                "executable_path": p_str,
                "kind": "antigravity_ide",
                "is_recommended": True,
                "description": "Google Antigravity AI-first development environment (Recommended)"
            })
            break  # prefer the cmd wrapper or primary exe

    # 2. Antigravity 2.0 Desktop Application
    ag_app_candidates = [
        ("Antigravity 2.0 (App)", Path(local_app_data) / "Programs" / "antigravity" / "Antigravity.exe"),
        ("Antigravity 2.0 (App)", Path(prog_files) / "Antigravity" / "Antigravity.exe"),
    ]
    for label, p in ag_app_candidates:
        p_str = str(p)
        if p.exists() and p_str.lower() not in seen_paths:
            seen_paths.add(p_str.lower())
            discovered.append({
                "id": "antigravity_app",
                "name": "Antigravity 2.0 (Desktop App)",
                "executable_path": p_str,
                "kind": "antigravity_app",
                "is_recommended": False,
                "description": "Google Antigravity standalone desktop orchestrator"
            })
            break

    # 3. Microsoft Visual Studio Code
    vscode_candidates = [
        ("Visual Studio Code", Path(local_app_data) / "Programs" / "Microsoft VS Code" / "bin" / "code.cmd"),
        ("Visual Studio Code", Path(local_app_data) / "Programs" / "Microsoft VS Code" / "Code.exe"),
        ("Visual Studio Code", Path(prog_files) / "Microsoft VS Code" / "bin" / "code.cmd"),
        ("Visual Studio Code", Path(prog_files) / "Microsoft VS Code" / "Code.exe"),
    ]
    for label, p in vscode_candidates:
        p_str = str(p)
        if p.exists() and p_str.lower() not in seen_paths:
            seen_paths.add(p_str.lower())
            discovered.append({
                "id": "vscode",
                "name": "Microsoft Visual Studio Code",
                "executable_path": p_str,
                "kind": "vscode",
                "is_recommended": False,
                "description": "Microsoft VS Code editor"
            })
            break

    # 4. Cursor
    cursor_candidates = [
        ("Cursor", Path(local_app_data) / "Programs" / "cursor" / "Cursor.exe"),
        ("Cursor", Path(local_app_data) / "Programs" / "cursor" / "bin" / "cursor.cmd"),
    ]
    for label, p in cursor_candidates:
        p_str = str(p)
        if p.exists() and p_str.lower() not in seen_paths:
            seen_paths.add(p_str.lower())
            discovered.append({
                "id": "cursor",
                "name": "Cursor",
                "executable_path": p_str,
                "kind": "cursor",
                "is_recommended": False,
                "description": "AI-powered code editor"
            })
            break

    # 5. Windsurf
    windsurf_candidates = [
        ("Windsurf", Path(local_app_data) / "Programs" / "Windsurf" / "Windsurf.exe"),
        ("Windsurf", Path(local_app_data) / "Programs" / "Windsurf" / "bin" / "windsurf.cmd"),
    ]
    for label, p in windsurf_candidates:
        p_str = str(p)
        if p.exists() and p_str.lower() not in seen_paths:
            seen_paths.add(p_str.lower())
            discovered.append({
                "id": "windsurf",
                "name": "Windsurf",
                "executable_path": p_str,
                "kind": "windsurf",
                "is_recommended": False,
                "description": "Codeium Windsurf editor"
            })
            break

    # 6. JetBrains IDEs (PyCharm, IntelliJ, WebStorm, Android Studio, etc.)
    jb_base_dirs = [
        Path(prog_files) / "JetBrains",
        Path(prog_files_x86) / "JetBrains",
    ]
    for b in jb_base_dirs:
        if b.is_dir():
            for exe_file in b.glob("*/bin/*64.exe"):
                fname = exe_file.name.lower()
                p_str = str(exe_file)
                if p_str.lower() not in seen_paths:
                    seen_paths.add(p_str.lower())
                    nice_name = exe_file.stem.capitalize()
                    if "pycharm" in fname:
                        nice_name = "PyCharm"
                    elif "idea" in fname:
                        nice_name = "IntelliJ IDEA"
                    elif "webstorm" in fname:
                        nice_name = "WebStorm"
                    discovered.append({
                        "id": f"jb_{exe_file.stem}",
                        "name": nice_name,
                        "executable_path": p_str,
                        "kind": "jetbrains",
                        "is_recommended": False,
                        "description": f"JetBrains {nice_name}"
                    })

    # Android Studio
    android_studio_exe = Path(prog_files) / "Android" / "Android Studio" / "bin" / "studio64.exe"
    if android_studio_exe.exists() and str(android_studio_exe).lower() not in seen_paths:
        seen_paths.add(str(android_studio_exe).lower())
        discovered.append({
            "id": "android_studio",
            "name": "Android Studio",
            "executable_path": str(android_studio_exe),
            "kind": "jetbrains",
            "is_recommended": False,
            "description": "Android Studio"
        })

    # Direct check in LocalAppData/Programs (non-recursive, instant)
    local_progs = Path(local_app_data) / "Programs"
    if local_progs.is_dir():
        for sub in local_progs.iterdir():
            if sub.is_dir() and any(k in sub.name.lower() for k in ["pycharm", "intellij", "webstorm", "clion", "rider"]):
                bin_dir = sub / "bin"
                if bin_dir.is_dir():
                    for exe_file in bin_dir.glob("*64.exe"):
                        p_str = str(exe_file)
                        if p_str.lower() not in seen_paths:
                            seen_paths.add(p_str.lower())
                            discovered.append({
                                "id": f"jb_{exe_file.stem}",
                                "name": exe_file.stem.capitalize(),
                                "executable_path": p_str,
                                "kind": "jetbrains",
                                "is_recommended": False,
                                "description": f"JetBrains {exe_file.stem.capitalize()}"
                            })

    # 7. Microsoft Visual Studio (devenv.exe)
    for vs_base in [Path(prog_files) / "Microsoft Visual Studio", Path(prog_files_x86) / "Microsoft Visual Studio"]:
        if vs_base.is_dir():
            for dev_exe in vs_base.glob("*/*/Common7/IDE/devenv.exe"):
                p_str = str(dev_exe)
                if p_str.lower() not in seen_paths:
                    seen_paths.add(p_str.lower())
                    discovered.append({
                        "id": "visual_studio",
                        "name": "Microsoft Visual Studio",
                        "executable_path": p_str,
                        "kind": "visual_studio",
                        "is_recommended": False,
                        "description": "Microsoft Visual Studio IDE"
                    })
                    break

    # 8. Sublime Text
    for subl_dir in [Path(prog_files) / "Sublime Text", Path(prog_files) / "Sublime Text 3"]:
        subl_exe = subl_dir / "subl.exe"
        if subl_exe.exists() and str(subl_exe).lower() not in seen_paths:
            seen_paths.add(str(subl_exe).lower())
            discovered.append({
                "id": "sublime",
                "name": "Sublime Text",
                "executable_path": str(subl_exe),
                "kind": "sublime",
                "is_recommended": False,
                "description": "Sublime Text Editor"
            })

    # 9. Notepad++
    for np_dir in [Path(prog_files) / "Notepad++", Path(prog_files_x86) / "Notepad++"]:
        np_exe = np_dir / "notepad++.exe"
        if np_exe.exists() and str(np_exe).lower() not in seen_paths:
            seen_paths.add(str(np_exe).lower())
            discovered.append({
                "id": "notepadplusplus",
                "name": "Notepad++",
                "executable_path": str(np_exe),
                "kind": "notepadplusplus",
                "is_recommended": False,
                "description": "Notepad++ text editor"
            })

    # 10. Check PATH for any additional IDE commands
    path_commands = [
        ("antigravity-ide", "Antigravity IDE", "antigravity_ide"),
        ("code", "Visual Studio Code", "vscode"),
        ("cursor", "Cursor", "cursor"),
        ("windsurf", "Windsurf", "windsurf"),
        ("subl", "Sublime Text", "sublime"),
        ("pycharm", "PyCharm", "jetbrains"),
        ("idea", "IntelliJ IDEA", "jetbrains"),
    ]
    for cmd, display_name, kind in path_commands:
        resolved = shutil.which(cmd)
        if resolved and resolved.lower() not in seen_paths:
            seen_paths.add(resolved.lower())
            discovered.append({
                "id": f"path_{cmd}",
                "name": display_name,
                "executable_path": resolved,
                "kind": kind,
                "is_recommended": (cmd == "antigravity-ide"),
                "description": f"{display_name} (from PATH)"
            })

    return discovered


def build_ide_launch_command(
    executable_path: str,
    workspace_path: str,
    reuse_window: bool = True,
    new_window: bool = False
) -> List[str]:
    """
    Build the specific command list to launch a workspace directory in the target IDE.
    Handles CLI options (-r, -n) for Antigravity, VS Code, Cursor, Windsurf, etc.
    """
    clean_workspace = str(Path(workspace_path).resolve())
    exe_lower = executable_path.lower()

    cmd = [executable_path]

    # Check if IDE supports -r (reuse window) and -n (new window) flags
    supports_flags = any(k in exe_lower for k in [
        "antigravity", "code", "cursor", "windsurf", "vscodium"
    ])

    if supports_flags:
        if reuse_window:
            cmd.append("-r")
        elif new_window:
            cmd.append("-n")

    cmd.append(clean_workspace)
    return cmd


def launch_ide_workspace(
    executable_path: str,
    workspace_path: str,
    reuse_window: bool = True,
    new_window: bool = False
) -> subprocess.Popen:
    """
    Launch the selected IDE in a detached process with the workspace folder.
    """
    if not executable_path or not Path(executable_path).exists():
        raise FileNotFoundError(f"Selected IDE executable was not found at '{executable_path}'")

    cmd = build_ide_launch_command(
        executable_path=executable_path,
        workspace_path=workspace_path,
        reuse_window=reuse_window,
        new_window=new_window
    )

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
