"""Modal dialog for adding and editing project resources (AI Chats, Websites, Local Files, IDEs)."""

import os
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox
from typing import Callable, Optional

from devpilot.core.models import ResourceConfig, ResourceType
from devpilot.core.resource_launcher import (
    infer_resource_type,
    get_resource_icon,
    validate_resource_target,
)
from devpilot.ui.theme import Theme


TYPE_DISPLAY_MAP = {
    ResourceType.AI_CHAT: "🤖 AI Conversation (ChatGPT, Claude, Gemini)",
    ResourceType.WEBSITE: "🌐 Website / Repository (GitHub, Docs, Figma)",
    ResourceType.LOCAL_FILE: "📁 Local File or Folder",
    ResourceType.IDE: "💻 IDE / Code Editor",
    ResourceType.CUSTOM_URL: "🔗 Custom URL",
    ResourceType.APPLICATION: "⚙️ Custom Application",
}

DISPLAY_TO_TYPE_MAP = {v: k for k, v in TYPE_DISPLAY_MAP.items()}


class ResourceEditorModal(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        resource: Optional[ResourceConfig] = None,
        project_root: str = "",
        on_save: Optional[Callable[[ResourceConfig], None]] = None
    ):
        super().__init__(master)
        self.is_edit = resource is not None
        self.project_root = project_root
        self.on_save = on_save

        if resource:
            self.resource = ResourceConfig.from_dict(resource.to_dict())
        else:
            self.resource = ResourceConfig(name="", resource_type=ResourceType.WEBSITE)

        self.title("DevPilot — " + ("Edit Resource" if self.is_edit else "Add New Resource"))
        self.geometry("600x520")
        self.minsize(560, 460)
        self.transient(master)
        self.grab_set()

        self._build_ui()
        self._populate_fields()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(18, 8))

        title_text = f"Edit Resource: {self.resource.name}" if self.is_edit else "Add Workspace Resource"
        ctk.CTkLabel(
            header,
            text=title_text,
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="Attach AI conversations, websites, documentation, or local files to launch with one click.",
            font=ctk.CTkFont(size=12),
            text_color=Theme.TEXT_MUTED
        ).pack(anchor="w", pady=(2, 0))

        # Main container
        content = ctk.CTkFrame(
            self,
            fg_color=Theme.BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=Theme.BORDER_SUBTLE
        )
        content.pack(fill="both", expand=True, padx=20, pady=8)

        # 1. Resource Type
        ctk.CTkLabel(
            content,
            text="Resource Type:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor="w", padx=16, pady=(14, 2))

        self.type_var = ctk.StringVar(value=TYPE_DISPLAY_MAP.get(self.resource.resource_type, TYPE_DISPLAY_MAP[ResourceType.WEBSITE]))
        self.type_menu = ctk.CTkOptionMenu(
            content,
            values=list(TYPE_DISPLAY_MAP.values()),
            variable=self.type_var,
            command=self._on_type_changed,
            height=28,
            corner_radius=8,
            fg_color=Theme.BTN_SECONDARY_BG,
            button_color=Theme.BTN_SECONDARY_HOVER,
            text_color=Theme.BTN_SECONDARY_TEXT
        )
        self.type_menu.pack(fill="x", padx=16, pady=(0, 10))

        # 2. Resource Name
        ctk.CTkLabel(
            content,
            text="Resource Name:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor="w", padx=16, pady=(2, 2))

        self.name_var = ctk.StringVar(value=self.resource.name)
        self.name_entry = ctk.CTkEntry(
            content,
            textvariable=self.name_var,
            placeholder_text="e.g. ChatGPT Context, GitHub Repo, Project Docs",
            font=ctk.CTkFont(size=11),
            height=30,
            corner_radius=8,
            fg_color=Theme.BG_INPUT,
            border_color=Theme.BORDER_SUBTLE,
            text_color=Theme.TEXT_PRIMARY
        )
        self.name_entry.pack(fill="x", padx=16, pady=(0, 10))

        # 3. Target (URL or Local Path)
        self.target_label = ctk.CTkLabel(
            content,
            text="Target URL or Path:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        self.target_label.pack(anchor="w", padx=16, pady=(2, 2))

        target_row = ctk.CTkFrame(content, fg_color="transparent")
        target_row.pack(fill="x", padx=16, pady=(0, 4))

        self.target_var = ctk.StringVar(value=self.resource.target)
        self.target_entry = ctk.CTkEntry(
            target_row,
            textvariable=self.target_var,
            placeholder_text="https://... or C:\\path\\to\\file",
            font=ctk.CTkFont(size=11),
            height=30,
            corner_radius=8,
            fg_color=Theme.BG_INPUT,
            border_color=Theme.BORDER_SUBTLE,
            text_color=Theme.TEXT_PRIMARY
        )
        self.target_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.target_entry.bind("<KeyRelease>", self._on_target_typed)

        # Browse buttons for local files/folders
        self.browse_btn = ctk.CTkButton(
            target_row,
            text="Browse...",
            width=75,
            height=30,
            fg_color=Theme.BTN_SECONDARY_BG,
            hover_color=Theme.BTN_SECONDARY_HOVER,
            text_color=Theme.BTN_SECONDARY_TEXT,
            corner_radius=8,
            command=self._browse_target
        )
        self.browse_btn.pack(side="left")

        # Hint text under target
        self.hint_label = ctk.CTkLabel(
            content,
            text="Paste any valid URL or click Browse to select a local file or folder.",
            font=ctk.CTkFont(size=10),
            text_color=Theme.TEXT_MUTED
        )
        self.hint_label.pack(anchor="w", padx=16, pady=(0, 10))

        # 4. Description / Notes
        ctk.CTkLabel(
            content,
            text="Description / Notes (Optional):",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor="w", padx=16, pady=(2, 2))

        self.desc_var = ctk.StringVar(value=self.resource.description)
        self.desc_entry = ctk.CTkEntry(
            content,
            textvariable=self.desc_var,
            placeholder_text="e.g. Main project documentation or ticket board",
            font=ctk.CTkFont(size=11),
            height=28,
            corner_radius=8,
            fg_color=Theme.BG_INPUT,
            border_color=Theme.BORDER_SUBTLE,
            text_color=Theme.TEXT_PRIMARY
        )
        self.desc_entry.pack(fill="x", padx=16, pady=(0, 12))

        # 5. Enable Checkbox
        self.enabled_var = ctk.BooleanVar(value=self.resource.enabled)
        self.enabled_chk = ctk.CTkCheckBox(
            content,
            text="Enable this resource for One-Click Project Launch",
            variable=self.enabled_var,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=Theme.TEXT_PRIMARY,
            fg_color=Theme.BTN_PRIMARY_BG
        )
        self.enabled_chk.pack(anchor="w", padx=16, pady=(0, 14))

        # Bottom Buttons
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=20, pady=(6, 16))

        ctk.CTkButton(
            bottom,
            text="Cancel",
            fg_color=Theme.BTN_SECONDARY_BG,
            hover_color=Theme.BTN_SECONDARY_HOVER,
            text_color=Theme.BTN_SECONDARY_TEXT,
            corner_radius=8,
            width=80,
            command=self.destroy
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            bottom,
            text="Save Resource",
            fg_color=Theme.BTN_PRIMARY_BG,
            hover_color=Theme.BTN_PRIMARY_HOVER,
            text_color=Theme.BTN_PRIMARY_TEXT,
            font=ctk.CTkFont(weight="bold"),
            corner_radius=18,
            width=120,
            height=32,
            command=self._handle_save
        ).pack(side="right")

    def _populate_fields(self):
        curr_display = TYPE_DISPLAY_MAP.get(self.resource.resource_type, TYPE_DISPLAY_MAP[ResourceType.WEBSITE])
        self.type_var.set(curr_display)
        self._update_hint_for_type(self.resource.resource_type)

    def _on_type_changed(self, chosen: str):
        res_type = DISPLAY_TO_TYPE_MAP.get(chosen, ResourceType.WEBSITE)
        self.resource.resource_type = res_type
        self._update_hint_for_type(res_type)

    def _update_hint_for_type(self, res_type: ResourceType):
        if res_type == ResourceType.AI_CHAT:
            self.target_label.configure(text="AI Conversation URL:")
            self.hint_label.configure(text="Paste your ChatGPT, Claude, Gemini, or any AI chat URL.")
        elif res_type in (ResourceType.WEBSITE, ResourceType.CUSTOM_URL):
            self.target_label.configure(text="Website URL:")
            self.hint_label.configure(text="Paste any web address (e.g. GitHub repository, Figma, live website).")
        elif res_type == ResourceType.LOCAL_FILE:
            self.target_label.configure(text="Local File or Folder Path:")
            self.hint_label.configure(text="Select a local project directory, PDF document, or configuration file.")
        elif res_type == ResourceType.IDE:
            self.target_label.configure(text="IDE Executable / Path:")
            self.hint_label.configure(text="Specify path to IDE executable (VS Code, Antigravity, PyCharm, etc.).")
        elif res_type == ResourceType.APPLICATION:
            self.target_label.configure(text="Application Executable:")
            self.hint_label.configure(text="Select an executable application to launch.")

    def _on_target_typed(self, event=None):
        target = self.target_var.get().strip()
        # If user hasn't set a name yet, auto-suggest name based on target
        if not self.name_var.get():
            if "chatgpt.com" in target.lower():
                self.name_var.set("ChatGPT Conversation")
                self.type_var.set(TYPE_DISPLAY_MAP[ResourceType.AI_CHAT])
            elif "claude.ai" in target.lower():
                self.name_var.set("Claude AI Chat")
                self.type_var.set(TYPE_DISPLAY_MAP[ResourceType.AI_CHAT])
            elif "gemini.google.com" in target.lower():
                self.name_var.set("Gemini AI Chat")
                self.type_var.set(TYPE_DISPLAY_MAP[ResourceType.AI_CHAT])
            elif "github.com" in target.lower():
                repo_parts = target.rstrip("/").split("/")
                repo_name = repo_parts[-1] if len(repo_parts) > 1 else "GitHub Repo"
                self.name_var.set(f"GitHub: {repo_name}")
                self.type_var.set(TYPE_DISPLAY_MAP[ResourceType.WEBSITE])
            elif "figma.com" in target.lower():
                self.name_var.set("Figma Design")
                self.type_var.set(TYPE_DISPLAY_MAP[ResourceType.WEBSITE])
            elif "trello.com" in target.lower():
                self.name_var.set("Trello Board")
                self.type_var.set(TYPE_DISPLAY_MAP[ResourceType.WEBSITE])

    def _browse_target(self):
        curr_type = DISPLAY_TO_TYPE_MAP.get(self.type_var.get(), ResourceType.WEBSITE)
        init_dir = self.project_root if Path(self.project_root).is_dir() else None

        if curr_type in (ResourceType.LOCAL_FILE,):
            # Prompt user if they want file or folder
            choice = messagebox.askquestion(
                "Browse Resource",
                "Do you want to select a Folder?\n(Click 'Yes' for Folder, 'No' for a specific File)",
                icon="question"
            )
            if choice == "yes":
                folder = filedialog.askdirectory(title="Select Folder", initialdir=init_dir)
                if folder:
                    self.target_var.set(folder)
                    if not self.name_var.get():
                        self.name_var.set(Path(folder).name)
            else:
                f = filedialog.askopenfilename(title="Select File", initialdir=init_dir)
                if f:
                    self.target_var.set(f)
                    if not self.name_var.get():
                        self.name_var.set(Path(f).name)

        elif curr_type in (ResourceType.APPLICATION, ResourceType.IDE):
            f = filedialog.askopenfilename(
                title="Select Executable",
                filetypes=[("Executables", "*.exe;*.cmd;*.bat"), ("All Files", "*.*")]
            )
            if f:
                self.target_var.set(f)
                if not self.name_var.get():
                    self.name_var.set(Path(f).stem.capitalize())
        else:
            # Default file browse
            f = filedialog.askopenfilename(title="Select File or Document", initialdir=init_dir)
            if f:
                self.target_var.set(f)
                self.type_var.set(TYPE_DISPLAY_MAP[ResourceType.LOCAL_FILE])
                if not self.name_var.get():
                    self.name_var.set(Path(f).name)

    def _handle_save(self):
        raw_name = self.name_var.get().strip()
        raw_target = self.target_var.get().strip()
        res_type = DISPLAY_TO_TYPE_MAP.get(self.type_var.get(), ResourceType.WEBSITE)

        if not raw_target:
            messagebox.showwarning("Validation Error", "Target URL or local path cannot be empty.")
            return

        is_valid, norm_target, err_msg = validate_resource_target(raw_target, res_type)
        if not is_valid:
            messagebox.showwarning("Validation Error", err_msg)
            return

        name = raw_name or (Path(norm_target).name if res_type == ResourceType.LOCAL_FILE else "Workspace Resource")

        self.resource.name = name
        self.resource.resource_type = res_type
        self.resource.target = norm_target
        self.resource.description = self.desc_var.get().strip()
        self.resource.enabled = self.enabled_var.get()

        if self.on_save:
            self.on_save(self.resource)

        self.destroy()

