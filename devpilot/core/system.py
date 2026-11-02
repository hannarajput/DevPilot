"""Operating system utilities, browser opener, app launcher, and Windows Autostart."""

import os
import sys
import webbrowser
import subprocess
from pathlib import Path
from typing import Optional, List
import psutil

try:
    import winreg
except ImportError:
    winreg = None


AUTOSTART_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "DevPilotWorkspaceManager"


def open_browser_url(url: str) -> bool:
    """Open a URL in the user's default browser."""
    if not url.startswith("http://") and not url.startswith("https://") and not url.startswith("file://"):
        url = "https://" + url
    try:
        webbrowser.open(url, new=2)
        return True
    except Exception as e:
        print(f"Error opening browser URL {url}: {e}")
        return False


def launch_supporting_application(executable_or_command: str, args: Optional[List[str]] = None) -> subprocess.Popen:
    """Launch a supporting application (e.g. database client, API tester)."""
    cmd = [executable_or_command]
    if args:
        cmd.extend(args)

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
        shell=False
    )
    return proc


def get_windows_autostart_status() -> bool:
    """Check if DevPilot is currently configured in HKCU Run registry."""
    if not winreg or os.name != "nt":
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_REG_KEY, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, APP_REG_NAME)
            return bool(val)
    except FileNotFoundError:
        return False
    except Exception:
        return False


def set_windows_autostart(enable: bool) -> bool:
    """Enable or disable DevPilot autostart on Windows user login (no admin required)."""
    if not winreg or os.name != "nt":
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enable:
                # Command to launch DevPilot main.py with pythonw or python
                python_exe = sys.executable
                script_path = str(Path(__file__).resolve().parent.parent.parent / "main.py")
                cmd = f'"{python_exe}" "{script_path}"'
                winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_REG_NAME)
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        print(f"Failed to set Windows autostart: {e}")
        return False


def safely_terminate_process_tree(pid: int):
    """
    Safely terminate a specific process and all its children without killing
    unrelated system or parent processes.
    """
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            try:
                child.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        parent.terminate()
        # Give grace period before killing
        gone, alive = psutil.wait_procs(children + [parent], timeout=2)
        for p in alive:
            try:
                p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    except Exception as e:
        print(f"Error terminating process {pid}: {e}")
