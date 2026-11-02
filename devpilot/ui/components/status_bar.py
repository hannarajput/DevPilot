"""Bottom status bar showing detected environment tools and session state."""

import customtkinter as ctk
from typing import Dict, Any

from devpilot.core.antigravity import find_antigravity_executable
from devpilot.core.detector import detect_installed_tools
from devpilot.ui.theme import Theme


class StatusBar(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            height=30,
            fg_color=Theme.BG_HEADER,
            corner_radius=0,
            border_width=1,
            border_color=Theme.BORDER_SUBTLE,
            **kwargs
        )
        self.pack_propagate(False)

        self._build_ui()
        self.refresh_tools()

    def _build_ui(self):
        # Antigravity detection status
        self.ag_label = ctk.CTkLabel(
            self,
            text="Antigravity: Detecting...",
            font=ctk.CTkFont(size=11),
            text_color=Theme.TEXT_MUTED
        )
        self.ag_label.pack(side="left", padx=16)

        # Tools status
        self.tools_label = ctk.CTkLabel(
            self,
            text="Tools: Scanning...",
            font=ctk.CTkFont(size=11),
            text_color=Theme.TEXT_MUTED
        )
        self.tools_label.pack(side="left", padx=16)

        # Right side: Version info
        v_label = ctk.CTkLabel(
            self,
            text="DevPilot v1.0.0",
            font=ctk.CTkFont(size=11),
            text_color=Theme.TEXT_MUTED
        )
        v_label.pack(side="right", padx=16)

    def refresh_tools(self):
        ag_exe = find_antigravity_executable()
        if ag_exe:
            if "ide" in ag_exe.lower():
                self.ag_label.configure(text="● Antigravity IDE: Ready", text_color=Theme.STATUS_SUCCESS_TEXT)
            else:
                self.ag_label.configure(text="● Antigravity App: Ready", text_color=Theme.STATUS_SUCCESS_TEXT)
        else:
            self.ag_label.configure(text="○ Antigravity: Not Detected", text_color=Theme.STATUS_RUNNING_TEXT)

        tools = detect_installed_tools()
        active = [k for k, v in tools.items() if v.get("available")]
        self.tools_label.configure(
            text=f"Detected: {', '.join(active[:5])}" if active else "No dev tools on PATH",
            text_color=Theme.TEXT_MUTED
        )
