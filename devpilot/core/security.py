"""Security, secret scrubbing, and command approval guard for DevPilot."""

import re
from typing import Tuple, List

# Regex patterns matching potential secrets and credentials
SECRET_PATTERNS = [
    # API Keys / Tokens
    re.compile(r"(?i)(api[_-]?key|access[_-]?token|auth[_-]?token|secret[_-]?key|bearer|client[_-]?secret)[\s:=]+([a-zA-Z0-9_\-\.]{8,})"),
    # AWS-style keys
    re.compile(r"(AKIA[0-9A-Z]{16})"),
    # Generic high-entropy hex/base64 password strings
    re.compile(r"(?i)(password|passwd|pwd)[\s:=]+([^\s,;]+)"),
    # Private keys
    re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----.*?-----END (?:RSA |EC )?PRIVATE KEY-----", re.DOTALL),
]


def redact_secrets(text: str) -> str:
    """Scrub sensitive keys, passwords, and tokens from log messages and console output."""
    if not text:
        return ""
    
    redacted = text
    for pattern in SECRET_PATTERNS:
        def _replace_match(m):
            if len(m.groups()) == 2:
                # e.g., key_name + key_value
                prefix = m.group(1)
                secret = m.group(2)
                masked = secret[:2] + "*" * (len(secret) - 4) + secret[-2:] if len(secret) > 6 else "********"
                return f"{prefix}=[{masked}]"
            elif len(m.groups()) == 1:
                secret = m.group(1)
                masked = secret[:2] + "*" * (len(secret) - 4) + secret[-2:] if len(secret) > 6 else "********"
                return f"[{masked}]"
            return "[REDACTED_SECRET]"

        redacted = pattern.sub(_replace_match, redacted)
    return redacted


def is_safe_startup_command(command: str) -> Tuple[bool, str]:
    """
    Check if a command is considered potentially dangerous or requires explicit warning.
    Disallows accidental data deletion or destructive system changes.
    """
    cmd_lower = command.lower().strip()
    
    # Destructive commands to flag/block
    dangerous_patterns = [
        (r"\brm\s+-rf\s+[/~]", "Recursive deletion of root or home directory is prohibited."),
        (r"\bdel\s+(?:/[a-z]\s*)+\s*[c-z]:[\\/]", "System drive deletion is prohibited."),
        (r"\bformat\s+[c-z]:", "Drive formatting is prohibited."),
        (r"\bdrop\s+database\b", "Database drop operation detected."),
        (r"\brmdir\s+(?:/[a-z]\s*)+\s*[c-z]:[\\/]", "System directory removal is prohibited."),
        (r"\bgit\s+push\s+--force\b", "Force push is restricted during automatic startup."),
        (r"\bgit\s+reset\s+--hard\b", "Hard git reset could cause data loss during automatic startup."),
    ]
    
    for pattern, reason in dangerous_patterns:
        if re.search(pattern, cmd_lower):
            return False, reason
            
    return True, "Safe"


def sanitize_project_name(name: str) -> str:
    """Sanitize project name for safe UI display and file references."""
    # Remove characters not suitable for identifiers or folder names
    clean = re.sub(r'[<>:"/\\|?*]', '_', name)
    return clean.strip()
