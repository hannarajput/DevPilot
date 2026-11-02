"""Terminal window spawner and command execution orchestration."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple


def get_available_terminals() -> List[str]:
    """Return available terminal emulator keys in preference order."""
    available = []
    
    # 1. Windows Terminal
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    wt_default = Path(local_appdata) / "Microsoft" / "WindowsApps" / "wt.exe"
    if wt_default.exists() or shutil.which("wt"):
        available.append("wt")

    # 2. PowerShell
    if shutil.which("powershell"):
        available.append("powershell")

    # 3. CMD
    if shutil.which("cmd"):
        available.append("cmd")

    return available


def build_terminal_command(
    terminal_type: str,
    working_dir: str,
    startup_command: Optional[str] = None,
    title: Optional[str] = None
) -> List[str]:
    """
    Build the command list to launch an interactive terminal window.
    Leaves the terminal open (-NoExit or /k) after running any optional startup command.
    """
    clean_dir = str(Path(working_dir).resolve())
    term = terminal_type.lower()

    if term == "wt":
        # Windows Terminal
        # Syntax: wt.exe -d "<dir>" --title "<title>" powershell.exe -NoExit -Command "<command>"
        cmd = ["wt.exe", "-d", clean_dir]
        if title:
            cmd.extend(["--title", title])

        if startup_command and startup_command.strip():
            cmd.extend(["powershell.exe", "-NoExit", "-Command", startup_command.strip()])
        else:
            cmd.extend(["powershell.exe", "-NoExit"])
        return cmd

    elif term == "powershell":
        cmd = ["powershell.exe", "-NoExit"]
        if startup_command and startup_command.strip():
            # Set working dir then run command
            full_ps = f"Set-Location -LiteralPath '{clean_dir}'; {startup_command.strip()}"
            cmd.extend(["-Command", full_ps])
        else:
            cmd.extend(["-Command", f"Set-Location -LiteralPath '{clean_dir}'"])
        return cmd

    elif term == "cmd":
        cmd = ["cmd.exe", "/k"]
        if startup_command and startup_command.strip():
            full_cmd = f"cd /d \"{clean_dir}\" && {startup_command.strip()}"
            cmd.append(full_cmd)
        else:
            cmd.append(f"cd /d \"{clean_dir}\"")
        return cmd

    else:
        # Default fallback to powershell
        return build_terminal_command("powershell", working_dir, startup_command, title)


def launch_terminal_window(
    terminal_type: str,
    working_dir: str,
    startup_command: Optional[str] = None,
    title: Optional[str] = None
) -> subprocess.Popen:
    """
    Launch an interactive visible terminal window.
    Uses CREATE_NEW_CONSOLE so that the terminal opens in its own window.
    """
    cmd = build_terminal_command(terminal_type, working_dir, startup_command, title)
    
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_CONSOLE

    proc = subprocess.Popen(
        cmd,
        cwd=working_dir,
        creationflags=creationflags
    )
    return proc


def run_command_capture(
    command: str,
    working_dir: str,
    timeout_seconds: int = 30
) -> Tuple[int, str, str]:
    """
    Run a background command synchronously and capture stdout/stderr.
    Useful for health checks, pre-flight tool verification, or batch tasks.
    """
    try:
        proc = subprocess.run(
            command,
            cwd=working_dir,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_seconds,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout_seconds} seconds."
    except Exception as e:
        return -1, "", f"Execution error: {str(e)}"
