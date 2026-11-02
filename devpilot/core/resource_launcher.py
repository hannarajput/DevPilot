"""Safe validation and one-click execution engine for project workspace resources."""

import os
import re
import urllib.parse
import webbrowser
import subprocess
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List

from devpilot.core.models import ResourceConfig, ResourceType, IDEPreference
from devpilot.core.ide_detector import launch_ide_workspace
from devpilot.core.antigravity import launch_antigravity_workspace
from devpilot.core.system import launch_supporting_application


DANGEROUS_SCHEMES = {
    "javascript", "vbscript", "data", "shell", "ms-msdt", "ms-cxh",
    "search-ms", "cmd", "powershell", "wscript", "cscript"
}

KNOWN_AI_DOMAINS = [
    "chatgpt.com", "chat.openai.com", "claude.ai", "gemini.google.com",
    "perplexity.ai", "copilot.microsoft.com", "poe.com", "groq.com",
    "deepseek.com", "chat.mistral.ai", "huggingface.co/chat"
]


def infer_resource_type(target: str) -> ResourceType:
    """Intelligently infer resource type from a URL or file/folder path."""
    t = target.strip().lower()
    
    # Check if local path
    if t.startswith("\\\\") or (len(t) >= 2 and t[1] == ":") or t.startswith(("./", ".\\", "/")):
        if t.endswith((".exe", ".cmd", ".bat")):
            return ResourceType.APPLICATION
        return ResourceType.LOCAL_FILE

    # Check if AI chat
    for domain in KNOWN_AI_DOMAINS:
        if domain in t:
            return ResourceType.AI_CHAT

    # Check common editors/IDEs
    if any(k in t for k in ["code.exe", "antigravity", "pycharm", "cursor.exe", "windsurf.exe"]):
        return ResourceType.IDE

    # Default URL check
    if t.startswith(("http://", "https://", "www.")) or "." in t:
        if any(repo in t for repo in ["github.com", "gitlab.com", "bitbucket.org", "figma.com", "trello.com", "linear.app", "docs."]):
            return ResourceType.WEBSITE
        return ResourceType.CUSTOM_URL

    return ResourceType.WEBSITE


def get_resource_icon(resource_type: ResourceType, target: str = "") -> str:
    """Return an intuitive emoji icon for the resource."""
    t = target.lower()
    if resource_type == ResourceType.AI_CHAT:
        return "🤖"
    elif resource_type == ResourceType.IDE:
        return "💻"
    elif resource_type == ResourceType.LOCAL_FILE:
        p = Path(target)
        if p.is_dir() or target.endswith(("/", "\\")):
            return "📁"
        return "📄"
    elif resource_type == ResourceType.APPLICATION:
        return "⚙️"
    elif resource_type in (ResourceType.WEBSITE, ResourceType.CUSTOM_URL):
        if "github.com" in t:
            return "🐙"
        elif "gitlab.com" in t or "bitbucket.org" in t:
            return "📦"
        elif "figma.com" in t:
            return "🎨"
        elif "trello.com" in t or "linear.app" in t or "jira" in t:
            return "📋"
        elif "docs." in t or "readme" in t or "wiki" in t:
            return "📚"
        return "🌐"
    return "🔗"


def validate_resource_target(target: str, resource_type: ResourceType) -> Tuple[bool, str, str]:
    """
    Validate and normalize resource target string.
    Returns: (is_valid, normalized_target, error_message)
    """
    clean_target = target.strip()
    if not clean_target:
        return False, "", "Target URL or path cannot be empty."

    # 1. Local files and folders
    if resource_type == ResourceType.LOCAL_FILE:
        p = Path(clean_target).resolve()
        if not p.exists():
            return False, str(p), f"Local path not found on disk: {clean_target}"
        return True, str(p), ""

    # 2. Executables / Custom Applications / IDEs
    if resource_type in (ResourceType.APPLICATION, ResourceType.IDE):
        # Could be path or executable command name
        p = Path(clean_target)
        if p.is_file() or clean_target.endswith((".exe", ".cmd", ".bat")):
            if not p.exists():
                return False, clean_target, f"Executable file not found: {clean_target}"
            return True, str(p.resolve()), ""
        # Could also be a known command or URL
        return True, clean_target, ""

    # 3. Web URLs (AI_CHAT, WEBSITE, CUSTOM_URL)
    url = clean_target

    # Security check: disallow dangerous protocols
    for scheme in DANGEROUS_SCHEMES:
        if url.lower().startswith(f"{scheme}:"):
            return False, url, f"Dangerous URL scheme '{scheme}:' is blocked for security."

    # Prepend https:// if protocol is omitted
    if not url.startswith("http://") and not url.startswith("https://"):
        if url.startswith("www.") or "." in url.split("/")[0]:
            url = "https://" + url
        else:
            return False, url, "Invalid URL: please provide a valid web address starting with https://"

    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme.lower() not in ("http", "https"):
            return False, url, f"Unsupported scheme: {parsed.scheme}"
        if not parsed.netloc:
            return False, url, "Invalid URL: missing domain host"
    except Exception as e:
        return False, url, f"URL parse error: {e}"

    return True, url, ""


def launch_single_resource(
    resource: ResourceConfig,
    project_root: str,
    ide_preference: Optional[IDEPreference] = None
) -> Tuple[bool, str, Optional[int]]:
    """
    Launch an individual resource safely.
    Returns: (success, status_message, pid_or_none)
    """
    if not resource.enabled:
        return True, "Skipped (disabled by user)", None

    t_type = resource.resource_type
    target = resource.target.strip()

    is_valid, norm_target, err = validate_resource_target(target, t_type)
    if not is_valid:
        return False, err, None

    try:
        # 1. Web URLs & AI Chats
        if t_type in (ResourceType.AI_CHAT, ResourceType.WEBSITE, ResourceType.CUSTOM_URL):
            opened = webbrowser.open_new_tab(norm_target)
            if opened:
                return True, f"Opened in browser: {norm_target}", None
            else:
                # Fallback to system browser open
                if os.name == "nt":
                    os.startfile(norm_target)
                    return True, f"Opened in system browser: {norm_target}", None
                return False, f"Failed to open browser tab for: {norm_target}", None

        # 2. Local Files & Folders
        elif t_type == ResourceType.LOCAL_FILE:
            p = Path(norm_target).resolve()
            if not p.exists():
                return False, f"File or folder does not exist: {norm_target}", None

            if os.name == "nt":
                try:
                    os.startfile(str(p))
                    return True, f"Opened local resource: {p.name}", None
                except Exception:
                    # Fallback to explorer
                    proc = subprocess.Popen(["explorer", str(p)])
                    return True, f"Opened via Explorer: {p.name}", proc.pid
            else:
                proc = subprocess.Popen(["xdg-open", str(p)])
                return True, f"Opened: {p.name}", proc.pid

        # 3. IDE / Code Editor
        elif t_type == ResourceType.IDE:
            workspace_dir = project_root if Path(project_root).is_dir() else str(Path.cwd())
            exe_path = norm_target or (ide_preference.executable_path if ide_preference else "")
            
            reuse = ide_preference.reuse_window if ide_preference else True
            new_win = ide_preference.new_window if ide_preference else False

            if exe_path and "antigravity" in exe_path.lower():
                proc = launch_antigravity_workspace(workspace_dir, executable_path=exe_path)
            elif exe_path and Path(exe_path).exists():
                proc = launch_ide_workspace(exe_path, workspace_dir, reuse_window=reuse, new_window=new_win)
            else:
                return False, f"IDE executable not found: {exe_path}", None

            return True, f"IDE workspace launched (PID: {proc.pid})", proc.pid

        # 4. Custom Application
        elif t_type == ResourceType.APPLICATION:
            proc = launch_supporting_application(norm_target, resource.extra_args)
            return True, f"Application launched: {Path(norm_target).stem} (PID: {proc.pid})", proc.pid

        else:
            return False, f"Unsupported resource type: {t_type}", None

    except Exception as e:
        return False, f"Execution failed: {str(e)}", None

