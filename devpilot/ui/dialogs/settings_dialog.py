"""Global Settings Modal Dialog with Theme, Terminal, and Autostart preferences."""

import customtkinter as ctk
from tkinter import filedialog
from typing import Callable, Optional

from devpilot.core.models import AppSettings
from devpilot.core.antigravity import find_antigravity_executable
from devpilot.core.system import get_windows_autostart_status, set_windows_autostart
from devpilot.ui.theme import Theme


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, master, settings: AppSettings, on_save: Callable[[AppSettings], None]):
        super().__init__(master)
        self.title("DevPilot — Global Settings")
        self.geometry("580x500")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.settings = settings
        self.on_save = on_save

        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(18, 12))

        ctk.CTkLabel(
            header,
            text="Global Configuration",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="Configure system defaults, theme appearance, and startup preferences.",
            font=ctk.CTkFont(size=12),
            text_color=Theme.TEXT_MUTED
        ).pack(anchor="w")

        # Main content
        content = ctk.CTkFrame(
            self,
            fg_color=Theme.BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=Theme.BORDER_SUBTLE
        )
        content.pack(fill="both", expand=True, padx=20, pady=4)

        # 1. Theme Appearance (Light / Dark Mode option)
        theme_frame = ctk.CTkFrame(content, fg_color="transparent")
        theme_frame.pack(fill="x", padx=16, pady=(14, 8))

        ctk.CTkLabel(
            theme_frame,
            text="Interface Appearance Theme:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor="w")

        self.theme_var = ctk.StringVar(value=self.settings.theme or "light")
        self.theme_menu = ctk.CTkSegmentedButton(
            theme_frame,
            values=["light", "dark", "system"],
            variable=self.theme_var,
            corner_radius=8,
            selected_color=Theme.BTN_PRIMARY_BG,
            selected_hover_color=Theme.BTN_PRIMARY_HOVER
        )
        self.theme_menu.pack(anchor="w", pady=(4, 0))

        # 2. Antigravity Path
        ag_frame = ctk.CTkFrame(content, fg_color="transparent")
        ag_frame.pack(fill="x", padx=16, pady=8)

        ctk.CTkLabel(
            ag_frame,
            text="Antigravity Executable Path:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor="w")

        ag_input_f = ctk.CTkFrame(ag_frame, fg_color="transparent")
        ag_input_f.pack(fill="x", pady=(4, 0))

        self.ag_path_var = ctk.StringVar(value=self.settings.default_antigravity_path or find_antigravity_executable() or "")
        self.ag_entry = ctk.CTkEntry(
            ag_input_f,
            textvariable=self.ag_path_var,
            font=ctk.CTkFont(size=11),
            fg_color=Theme.BG_INPUT,
            border_color=Theme.BORDER_SUBTLE,
            text_color=Theme.TEXT_PRIMARY
        )
        self.ag_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            ag_input_f,
            text="Browse",
            width=65,
            fg_color=Theme.BTN_SECONDARY_BG,
            hover_color=Theme.BTN_SECONDARY_HOVER,
            text_color=Theme.BTN_SECONDARY_TEXT,
            corner_radius=6,
            command=self._browse_ag
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            ag_input_f,
            text="Auto-Detect",
            width=80,
            fg_color=Theme.BTN_SECONDARY_BG,
            hover_color=Theme.BTN_SECONDARY_HOVER,
            text_color=Theme.BTN_SECONDARY_TEXT,
            corner_radius=6,
            command=self._autodetect_ag
        ).pack(side="left")

        # 3. Preferred Terminal
        term_frame = ctk.CTkFrame(content, fg_color="transparent")
        term_frame.pack(fill="x", padx=16, pady=8)

        ctk.CTkLabel(
            term_frame,
            text="Preferred Terminal Emulator:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor="w")

        self.term_var = ctk.StringVar(value=self.settings.default_terminal)
        self.term_menu = ctk.CTkOptionMenu(
            term_frame,
            values=["wt", "powershell", "cmd"],
            variable=self.term_var,
            corner_radius=8,
            fg_color=Theme.BTN_SECONDARY_BG,
            button_color=Theme.BTN_SECONDARY_HOVER,
            text_color=Theme.BTN_SECONDARY_TEXT,
            width=180
        )
        self.term_menu.pack(anchor="w", pady=(4, 0))

        # 4. Windows Autostart toggle
        auto_frame = ctk.CTkFrame(content, fg_color="transparent")
        auto_frame.pack(fill="x", padx=16, pady=8)

        current_autostart = get_windows_autostart_status()
        self.autostart_var = ctk.BooleanVar(value=current_autostart)
        self.autostart_chk = ctk.CTkCheckBox(
            auto_frame,
            text="Launch DevPilot automatically on Windows login (HKCU)",
            variable=self.autostart_var,
            font=ctk.CTkFont(size=12),
            text_color=Theme.TEXT_PRIMARY,
            fg_color=Theme.BTN_PRIMARY_BG
        )
        self.autostart_chk.pack(anchor="w")

        # 5. Redact Secrets toggle
        sec_frame = ctk.CTkFrame(content, fg_color="transparent")
        sec_frame.pack(fill="x", padx=16, pady=8)

        self.sec_var = ctk.BooleanVar(value=self.settings.redact_secrets)
        self.sec_chk = ctk.CTkCheckBox(
            sec_frame,
            text="Redact API keys, tokens, and secrets from execution logs",
            variable=self.sec_var,
            font=ctk.CTkFont(size=12),
            text_color=Theme.TEXT_PRIMARY,
            fg_color=Theme.BTN_PRIMARY_BG
        )
        self.sec_chk.pack(anchor="w")

        # Bottom buttons
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=20, pady=(12, 16))

        ctk.CTkButton(
            bottom,
            text="Cancel",
            fg_color=Theme.BTN_SECONDARY_BG,
            hover_color=Theme.BTN_SECONDARY_HOVER,
            text_color=Theme.BTN_SECONDARY_TEXT,
            corner_radius=8,
            width=80,
            command=self.destroy
        ).pack(side="right", padx=(6, 0))

        ctk.CTkButton(
            bottom,
            text="Save Settings",
            fg_color=Theme.BTN_PRIMARY_BG,
            hover_color=Theme.BTN_PRIMARY_HOVER,
            text_color=Theme.BTN_PRIMARY_TEXT,
            font=ctk.CTkFont(weight="bold"),
            corner_radius=18,
            width=110,
            height=32,
            command=self._handle_save
        ).pack(side="right")

    def _browse_ag(self):
        f = filedialog.askopenfilename(
            title="Select Antigravity Executable",
            filetypes=[("Executables", "*.exe;*.cmd;*.bat"), ("All Files", "*.*")]
        )
        if f:
            self.ag_path_var.set(f)

    def _autodetect_ag(self):
        detected = find_antigravity_executable()
        if detected:
            self.ag_path_var.set(detected)

    def _handle_save(self):
        self.settings.default_antigravity_path = self.ag_path_var.get().strip()
        self.settings.default_terminal = self.term_var.get()
        self.settings.redact_secrets = self.sec_var.get()
        
        # Theme appearance
        chosen_theme = self.theme_var.get()
        self.settings.theme = chosen_theme
        ctk.set_appearance_mode(chosen_theme)

        # Windows autostart toggle
        new_autostart = self.autostart_var.get()
        set_windows_autostart(new_autostart)
        self.settings.autostart_on_windows_login = new_autostart

        self.on_save(self.settings)
        self.destroy()
