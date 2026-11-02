"""Comprehensive Project Configuration and Creation Modal Dialog."""

import os
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox
from typing import Callable, Optional, List, Dict

from devpilot.core.models import (
    ProjectConfig,
    ProjectType,
    ProfileType,
    ProfileConfig,
    TaskConfig,
    TaskType,
    AntigravityConfig,
    IDEPreference,
    ResourceConfig,
    ResourceType,
)
from devpilot.core.detector import detect_project_type, generate_default_project_config
from devpilot.core.antigravity import find_antigravity_executable
from devpilot.core.ide_detector import detect_installed_ides
from devpilot.core.security import is_safe_startup_command
from devpilot.core.resource_launcher import get_resource_icon, launch_single_resource
from devpilot.ui.dialogs.ide_selection_modal import IDESelectionModal
from devpilot.ui.dialogs.resource_editor_modal import ResourceEditorModal
from devpilot.ui.theme import Theme


class ProjectEditorDialog(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        project: Optional[ProjectConfig] = None,
        on_save: Optional[Callable[[ProjectConfig], None]] = None
    ):
        super().__init__(master)
        self.is_edit_mode = project is not None
        self.title("DevPilot — " + ("Edit Project Configuration" if self.is_edit_mode else "Add New Project"))
        self.geometry("740x620")
        self.resizable(True, True)
        self.minsize(680, 560)
        self.transient(master)
        self.grab_set()

        # Working copy of project
        if project:
            self.project = ProjectConfig.from_dict(project.to_dict())
        else:
            self.project = ProjectConfig(name="New Project")
            self.project.antigravity.executable_path = find_antigravity_executable() or ""

        self.on_save = on_save
        self._build_ui()
        self._populate_fields()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(16, 8))

        title_text = f"Configure Project: {self.project.name}" if self.is_edit_mode else "Add New Development Project"
        ctk.CTkLabel(
            header,
            text=title_text,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="Configure workspace root, Antigravity integration, startup terminals, commands, and profiles.",
            font=ctk.CTkFont(size=11),
            text_color=Theme.TEXT_MUTED
        ).pack(anchor="w")

        # Tabview
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=Theme.BG_CARD,
            segmented_button_selected_color=Theme.BTN_PRIMARY_BG,
            segmented_button_selected_hover_color=Theme.BTN_PRIMARY_HOVER,
            text_color=Theme.TEXT_PRIMARY
        )
        self.tabview.pack(fill="both", expand=True, padx=20, pady=8)

        self.tab_general = self.tabview.add("General")
        self.tab_antigravity = self.tabview.add("IDE & Editor")
        self.tab_resources = self.tabview.add("Resources")
        self.tab_tasks = self.tabview.add("Startup Tasks")
        self.tab_profiles = self.tabview.add("Profiles")

        self._build_general_tab()
        self._build_antigravity_tab()
        self._build_resources_tab()
        self._build_tasks_tab()
        self._build_profiles_tab()

        # Bottom buttons
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=20, pady=(8, 16))

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
            text="Save Project",
            fg_color=Theme.BTN_PRIMARY_BG,
            hover_color=Theme.BTN_PRIMARY_HOVER,
            text_color=Theme.BTN_PRIMARY_TEXT,
            font=ctk.CTkFont(weight="bold"),
            corner_radius=18,
            width=120,
            command=self._handle_save
        ).pack(side="right")

    # ------------------ Tab 1: General ------------------ #
    def _build_general_tab(self):
        f = self.tab_general

        # Root Path with Browse & Auto-detect
        ctk.CTkLabel(f, text="Project Root Folder:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=12, pady=(12, 2))
        
        path_box = ctk.CTkFrame(f, fg_color="transparent")
        path_box.pack(fill="x", padx=12, pady=(0, 10))

        self.root_path_var = ctk.StringVar()
        self.root_path_entry = ctk.CTkEntry(path_box, textvariable=self.root_path_var, font=ctk.CTkFont(size=11))
        self.root_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(path_box, text="Browse...", width=80, command=self._browse_root_folder).pack(side="left")

        # Project Name
        ctk.CTkLabel(f, text="Project Name:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=12, pady=(4, 2))
        self.name_var = ctk.StringVar()
        self.name_entry = ctk.CTkEntry(f, textvariable=self.name_var)
        self.name_entry.pack(fill="x", padx=12, pady=(0, 10))

        # Project Type
        ctk.CTkLabel(f, text="Project Type:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=12, pady=(4, 2))
        self.type_var = ctk.StringVar(value=ProjectType.OTHER.value)
        self.type_menu = ctk.CTkOptionMenu(
            f,
            values=[t.value for t in ProjectType],
            variable=self.type_var,
            width=160
        )
        self.type_menu.pack(anchor="w", padx=12, pady=(0, 10))

        # Description
        ctk.CTkLabel(f, text="Description / Notes:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=12, pady=(4, 2))
        self.desc_entry = ctk.CTkEntry(f, placeholder_text="e.g. Backend API service")
        self.desc_entry.pack(fill="x", padx=12, pady=(0, 10))

    # ------------------ Tab 2: IDE & Editor ------------------ #
    def _build_antigravity_tab(self):
        f = self.tab_antigravity

        # IDE Selection Box
        ide_box = ctk.CTkFrame(f, fg_color="#242533", corner_radius=8)
        ide_box.pack(fill="x", padx=12, pady=(12, 10))

        ide_header = ctk.CTkFrame(ide_box, fg_color="transparent")
        ide_header.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(
            ide_header,
            text="Target IDE for this Project:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left")

        ctk.CTkButton(
            ide_header,
            text="Choose from Installed IDEs...",
            width=180,
            height=26,
            fg_color="#7aa2f7",
            hover_color="#5d84dc",
            text_color="#1a1b26",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._open_ide_picker_modal
        ).pack(side="right")

        self.ide_name_display_label = ctk.CTkLabel(
            ide_box,
            text=f"Selected IDE: {self.project.ide_preference.ide_name or 'Antigravity IDE'}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#7dcfff"
        )
        self.ide_name_display_label.pack(anchor="w", padx=12, pady=(2, 2))

        # Executable Path field
        ctk.CTkLabel(ide_box, text="Executable Path:", font=ctk.CTkFont(size=11), text_color="#8888aa").pack(anchor="w", padx=12, pady=(4, 2))
        
        exe_row = ctk.CTkFrame(ide_box, fg_color="transparent")
        exe_row.pack(fill="x", padx=12, pady=(0, 10))

        self.ag_exe_var = ctk.StringVar(value=self.project.ide_preference.executable_path or self.project.antigravity.executable_path)
        self.ag_exe_entry = ctk.CTkEntry(exe_row, textvariable=self.ag_exe_var, font=ctk.CTkFont(size=11))
        self.ag_exe_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(exe_row, text="Browse", width=65, command=self._browse_ag_exe).pack(side="left", padx=(0, 4))
        ctk.CTkButton(exe_row, text="Auto-Detect", width=80, fg_color="#3d4055", hover_color="#4f526b", command=self._autodetect_ag).pack(side="left")

        # Remember Checkbox
        self.remember_ide_var = ctk.BooleanVar(value=self.project.ide_preference.remembered)
        self.remember_ide_chk = ctk.CTkCheckBox(
            ide_box,
            text="Remember this IDE choice (do not ask again when launching this project)",
            variable=self.remember_ide_var,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#7aa2f7"
        )
        self.remember_ide_chk.pack(anchor="w", padx=12, pady=(0, 10))

        # Window reuse options
        opts_box = ctk.CTkFrame(f, fg_color="#282a36", corner_radius=6)
        opts_box.pack(fill="x", padx=12, pady=10)

        self.reuse_var = ctk.BooleanVar(value=self.project.ide_preference.reuse_window)
        ctk.CTkCheckBox(
            opts_box,
            text="Reuse existing window if already open (-r / --reuse-window)",
            variable=self.reuse_var,
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=12, pady=8)

        self.new_win_var = ctk.BooleanVar(value=self.project.ide_preference.new_window)
        ctk.CTkCheckBox(
            opts_box,
            text="Force new window (-n / --new-window)",
            variable=self.new_win_var,
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=12, pady=(0, 8))

        # Initial files
        ctk.CTkLabel(f, text="Initial Files to Open (comma-separated relative paths):", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=12, pady=(8, 2))
        self.init_files_var = ctk.StringVar()
        self.init_files_entry = ctk.CTkEntry(f, textvariable=self.init_files_var, placeholder_text="e.g. README.md, src/main.py")
        self.init_files_entry.pack(fill="x", padx=12, pady=(0, 10))

        # Note about chat restoration boundary
        note_box = ctk.CTkFrame(f, fg_color="#262838", corner_radius=6)
        note_box.pack(fill="x", padx=12, pady=10)
        ctk.CTkLabel(
            note_box,
            text="ℹ Workspace Launch Integration:\nDevPilot opens the exact workspace root and initial files in your chosen IDE.\nSession history within the IDE is preserved by the editor's workspace manager.",
            font=ctk.CTkFont(size=11),
            text_color="#7dcfff",
            justify="left"
        ).pack(padx=10, pady=8, anchor="w")

    def _open_ide_picker_modal(self):
        IDESelectionModal(
            self,
            project=self.project,
            action_button_text="Apply IDE Choice",
            on_confirm=self._on_ide_picked_in_editor
        )

    def _on_ide_picked_in_editor(self, pref: IDEPreference):
        self.project.ide_preference = pref
        self.ag_exe_var.set(pref.executable_path)
        self.remember_ide_var.set(pref.remembered)
        self.ide_name_display_label.configure(
            text=f"Selected IDE: {pref.ide_name} {'(Remembered)' if pref.remembered else '(Ask on launch)'}"
        )

    # ------------------ Tab: Attached Resources ------------------ #
    def _build_resources_tab(self):
        f = self.tab_resources

        header_frame = ctk.CTkFrame(f, fg_color="transparent")
        header_frame.pack(fill="x", padx=14, pady=(10, 4))

        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            title_box,
            text="Attached Workspace Resources",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_box,
            text="Connect AI chats, repositories, documentation, local files & apps to launch in one click.",
            font=ctk.CTkFont(size=11),
            text_color=Theme.TEXT_MUTED
        ).pack(anchor="w")

        self.add_resource_btn = ctk.CTkButton(
            header_frame,
            text="+ Add Resource",
            width=110,
            height=28,
            fg_color=Theme.BTN_PRIMARY_BG,
            hover_color=Theme.BTN_PRIMARY_HOVER,
            text_color=Theme.BTN_PRIMARY_TEXT,
            corner_radius=14,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._open_add_resource_modal
        )
        self.add_resource_btn.pack(side="right")

        self.resources_scroll = ctk.CTkScrollableFrame(
            f,
            fg_color=Theme.BG_SURFACE,
            corner_radius=8,
            border_width=1,
            border_color=Theme.BORDER_SUBTLE
        )
        self.resources_scroll.pack(fill="both", expand=True, padx=14, pady=(6, 10))

        self._render_resources_list()

    def _render_resources_list(self):
        for w in self.resources_scroll.winfo_children():
            w.destroy()

        if not self.project.resources:
            empty_box = ctk.CTkFrame(self.resources_scroll, fg_color="transparent")
            empty_box.pack(fill="both", expand=True, pady=30)

            ctk.CTkLabel(
                empty_box,
                text="🔗 No resources attached yet.",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=Theme.TEXT_SECONDARY
            ).pack(pady=(0, 4))

            ctk.CTkLabel(
                empty_box,
                text="Attach your ChatGPT/Claude conversations, GitHub repo, live sites, Figma,\nor local project notes to launch them all seamlessly with your workspace.",
                font=ctk.CTkFont(size=11),
                text_color=Theme.TEXT_MUTED,
                justify="center"
            ).pack(pady=(0, 10))

            ctk.CTkButton(
                empty_box,
                text="+ Add First Resource",
                width=140,
                height=28,
                fg_color=Theme.BTN_SECONDARY_BG,
                hover_color=Theme.BTN_SECONDARY_HOVER,
                text_color=Theme.BTN_SECONDARY_TEXT,
                corner_radius=8,
                font=ctk.CTkFont(size=11, weight="bold"),
                command=self._open_add_resource_modal
            ).pack()
            return

        for idx, res in enumerate(self.project.resources):
            card = ctk.CTkFrame(
                self.resources_scroll,
                fg_color=Theme.BG_CARD,
                corner_radius=8,
                border_width=1,
                border_color=Theme.BORDER_SUBTLE
            )
            card.pack(fill="x", pady=4, padx=2)

            # Left section: Icon + Info
            left_f = ctk.CTkFrame(card, fg_color="transparent")
            left_f.pack(side="left", fill="x", expand=True, padx=10, pady=6)

            top_row = ctk.CTkFrame(left_f, fg_color="transparent")
            top_row.pack(fill="x", anchor="w")

            icon = get_resource_icon(res.resource_type, res.target)
            ctk.CTkLabel(
                top_row,
                text=icon,
                font=ctk.CTkFont(size=14),
                width=22
            ).pack(side="left", padx=(0, 6))

            ctk.CTkLabel(
                top_row,
                text=res.name,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=Theme.TEXT_PRIMARY
            ).pack(side="left", padx=(0, 8))

            # Type badge
            type_label = res.resource_type.value.upper()
            ctk.CTkLabel(
                top_row,
                text=f" {type_label} ",
                fg_color=Theme.BG_SURFACE,
                text_color=Theme.TEXT_MUTED,
                corner_radius=4,
                font=ctk.CTkFont(size=9, weight="bold")
            ).pack(side="left")

            # Target URL or path
            target_str = res.target
            if len(target_str) > 65:
                target_str = target_str[:35] + "..." + target_str[-25:]

            ctk.CTkLabel(
                left_f,
                text=target_str,
                font=ctk.CTkFont(size=10),
                text_color=Theme.TEXT_MUTED,
                anchor="w"
            ).pack(fill="x", padx=(28, 0), pady=(2, 0))

            # Right actions
            act_f = ctk.CTkFrame(card, fg_color="transparent")
            act_f.pack(side="right", padx=10, pady=6)

            # Enabled checkbox
            enable_var = ctk.BooleanVar(value=res.enabled)
            def _toggle_enable(val=enable_var, r=res):
                r.enabled = val.get()

            chk = ctk.CTkCheckBox(
                act_f,
                text="Enable",
                variable=enable_var,
                command=_toggle_enable,
                font=ctk.CTkFont(size=10),
                width=65,
                checkbox_width=18,
                checkbox_height=18
            )
            chk.pack(side="left", padx=(0, 6))

            # Move up
            if idx > 0:
                ctk.CTkButton(
                    act_f,
                    text="▲",
                    width=24,
                    height=22,
                    fg_color=Theme.BTN_SECONDARY_BG,
                    hover_color=Theme.BTN_SECONDARY_HOVER,
                    text_color=Theme.TEXT_PRIMARY,
                    command=lambda i=idx: self._move_resource(i, -1)
                ).pack(side="left", padx=2)

            # Move down
            if idx < len(self.project.resources) - 1:
                ctk.CTkButton(
                    act_f,
                    text="▼",
                    width=24,
                    height=22,
                    fg_color=Theme.BTN_SECONDARY_BG,
                    hover_color=Theme.BTN_SECONDARY_HOVER,
                    text_color=Theme.TEXT_PRIMARY,
                    command=lambda i=idx: self._move_resource(i, 1)
                ).pack(side="left", padx=2)

            # Test Launch button
            ctk.CTkButton(
                act_f,
                text="▶ Test",
                width=45,
                height=22,
                fg_color=Theme.BTN_SECONDARY_BG,
                hover_color=Theme.BTN_SECONDARY_HOVER,
                text_color=Theme.TEXT_PRIMARY,
                font=ctk.CTkFont(size=10),
                command=lambda r=res: self._test_launch_resource(r)
            ).pack(side="left", padx=2)

            # Edit button
            ctk.CTkButton(
                act_f,
                text="Edit",
                width=40,
                height=22,
                fg_color=Theme.BTN_SECONDARY_BG,
                hover_color=Theme.BTN_SECONDARY_HOVER,
                text_color=Theme.TEXT_PRIMARY,
                font=ctk.CTkFont(size=10),
                command=lambda r=res: self._open_edit_resource_modal(r)
            ).pack(side="left", padx=2)

            # Delete button
            ctk.CTkButton(
                act_f,
                text="✕",
                width=24,
                height=22,
                fg_color=Theme.BTN_DANGER_BG,
                hover_color=Theme.BTN_DANGER_HOVER,
                text_color=Theme.BTN_DANGER_TEXT,
                font=ctk.CTkFont(size=11),
                command=lambda r=res: self._delete_resource(r)
            ).pack(side="left", padx=2)

    def _open_add_resource_modal(self):
        ResourceEditorModal(
            self,
            resource=None,
            project_root=self.root_path_var.get().strip() or self.project.root_path,
            on_save=self._on_resource_added
        )

    def _on_resource_added(self, res: ResourceConfig):
        self.project.add_resource(res)
        self._render_resources_list()

    def _open_edit_resource_modal(self, res: ResourceConfig):
        ResourceEditorModal(
            self,
            resource=res,
            project_root=self.root_path_var.get().strip() or self.project.root_path,
            on_save=lambda updated: self._on_resource_updated(res.id, updated)
        )

    def _on_resource_updated(self, old_id: str, updated: ResourceConfig):
        for i, r in enumerate(self.project.resources):
            if r.id == old_id:
                self.project.resources[i] = updated
                break
        self._render_resources_list()

    def _delete_resource(self, res: ResourceConfig):
        self.project.remove_resource(res.id)
        self._render_resources_list()

    def _move_resource(self, index: int, delta: int):
        target_idx = index + delta
        if 0 <= target_idx < len(self.project.resources):
            self.project.resources[index], self.project.resources[target_idx] = (
                self.project.resources[target_idx],
                self.project.resources[index],
            )
            for i, r in enumerate(self.project.resources):
                r.order = i + 1
            self._render_resources_list()

    def _test_launch_resource(self, res: ResourceConfig):
        ok, msg, pid = launch_single_resource(
            res,
            self.root_path_var.get().strip() or self.project.root_path,
            self.project.ide_preference
        )
        if ok:
            messagebox.showinfo("Resource Test Succeeded", f"{res.name}:\n{msg}")
        else:
            messagebox.showwarning("Resource Test Failed", f"{res.name}:\n{msg}")

    # ------------------ Tab 3: Startup Tasks ------------------ #
    def _build_tasks_tab(self):
        f = self.tab_tasks

        # Task list controls
        ctrl_frame = ctk.CTkFrame(f, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=12, pady=(8, 4))

        ctk.CTkLabel(ctrl_frame, text="Configured Tasks:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")

        ctk.CTkButton(
            ctrl_frame,
            text="+ Add Task",
            width=80,
            height=24,
            command=self._add_new_task
        ).pack(side="right", padx=(4, 0))

        # Task scrollable frame
        self.tasks_scroll = ctk.CTkScrollableFrame(
            f,
            fg_color=Theme.BG_SURFACE,
            corner_radius=8,
            border_width=1,
            border_color=Theme.BORDER_SUBTLE
        )
        self.tasks_scroll.pack(fill="both", expand=True, padx=12, pady=4)

    def _render_tasks_list(self):
        for widget in self.tasks_scroll.winfo_children():
            widget.destroy()

        for idx, task in enumerate(self.project.tasks):
            card = ctk.CTkFrame(
                self.tasks_scroll,
                fg_color=Theme.BG_CARD,
                corner_radius=8,
                border_width=1,
                border_color=Theme.BORDER_SUBTLE
            )
            card.pack(fill="x", pady=3, padx=2)

            # Left badge & name
            info_f = ctk.CTkFrame(card, fg_color="transparent")
            info_f.pack(side="left", fill="x", expand=True, padx=8, pady=4)

            name_row = ctk.CTkFrame(info_f, fg_color="transparent")
            name_row.pack(fill="x")

            ctk.CTkLabel(
                name_row,
                text=f"[{task.task_type.value.upper()}]",
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color=Theme.TEXT_SECONDARY
            ).pack(side="left", padx=(0, 6))

            ctk.CTkLabel(
                name_row,
                text=task.name,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=Theme.TEXT_PRIMARY
            ).pack(side="left")

            if task.is_one_time:
                ctk.CTkLabel(
                    name_row,
                    text="(One-time)",
                    font=ctk.CTkFont(size=10),
                    text_color=Theme.STATUS_RUNNING_TEXT
                ).pack(side="left", padx=6)

            if not task.approved and task.task_type in (TaskType.COMMAND, TaskType.TERMINAL):
                ctk.CTkLabel(
                    name_row,
                    text="⚠️ Unapproved",
                    font=ctk.CTkFont(size=10, weight="bold"),
                    text_color=Theme.STATUS_FAILED_TEXT
                ).pack(side="left", padx=6)

            target_text = task.target or task.working_dir or "Default"
            ctk.CTkLabel(
                info_f,
                text=f"Target: {target_text[:50]}",
                font=ctk.CTkFont(size=10),
                text_color=Theme.TEXT_MUTED
            ).pack(anchor="w")

            # Right actions: Up, Down, Edit, Delete
            act_f = ctk.CTkFrame(card, fg_color="transparent")
            act_f.pack(side="right", padx=6, pady=4)

            if idx > 0:
                ctk.CTkButton(
                    act_f, text="▲", width=24, height=22, fg_color="#343647",
                    command=lambda i=idx: self._move_task(i, -1)
                ).pack(side="left", padx=2)

            if idx < len(self.project.tasks) - 1:
                ctk.CTkButton(
                    act_f, text="▼", width=24, height=22, fg_color="#343647",
                    command=lambda i=idx: self._move_task(i, 1)
                ).pack(side="left", padx=2)

            ctk.CTkButton(
                act_f, text="Edit", width=42, height=22, fg_color="#3d4055",
                command=lambda t=task: self._edit_task(t)
            ).pack(side="left", padx=2)

            ctk.CTkButton(
                act_f, text="✕", width=24, height=22, fg_color="#5a2e36", hover_color="#f7768e",
                command=lambda t=task: self._delete_task(t)
            ).pack(side="left", padx=2)

    def _move_task(self, index: int, delta: int):
        target_idx = index + delta
        if 0 <= target_idx < len(self.project.tasks):
            self.project.tasks[index], self.project.tasks[target_idx] = (
                self.project.tasks[target_idx],
                self.project.tasks[index],
            )
            # Re-index order
            for i, t in enumerate(self.project.tasks):
                t.order = i + 1
            self._render_tasks_list()

    def _delete_task(self, task: TaskConfig):
        self.project.tasks = [t for t in self.project.tasks if t.id != task.id]
        self._render_tasks_list()

    def _add_new_task(self):
        new_task = TaskConfig(
            name="New Terminal Task",
            task_type=TaskType.TERMINAL,
            order=len(self.project.tasks) + 1,
            working_dir=self.root_path_var.get() or "e:\\"
        )
        self._edit_task(new_task, is_new=True)

    def _edit_task(self, task: TaskConfig, is_new: bool = False):
        # Open inline edit dialog for task
        dlg = ctk.CTkToplevel(self)
        dlg.title("Edit Task")
        dlg.geometry("520x460")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        f = ctk.CTkFrame(dlg, fg_color="#1e1f29", corner_radius=8)
        f.pack(fill="both", expand=True, padx=16, pady=16)

        # Task Name
        ctk.CTkLabel(f, text="Task Name:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(6, 2))
        name_v = ctk.StringVar(value=task.name)
        ctk.CTkEntry(f, textvariable=name_v).pack(fill="x", padx=10, pady=(0, 6))

        # Task Type
        ctk.CTkLabel(f, text="Task Type:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(4, 2))
        type_v = ctk.StringVar(value=task.task_type.value)
        ctk.CTkOptionMenu(
            f,
            values=[tt.value for tt in TaskType],
            variable=type_v
        ).pack(anchor="w", padx=10, pady=(0, 6))

        # Target / Command / URL
        ctk.CTkLabel(f, text="Target (Command / Script / URL / App Path):", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(4, 2))
        target_v = ctk.StringVar(value=task.target)
        ctk.CTkEntry(f, textvariable=target_v).pack(fill="x", padx=10, pady=(0, 6))

        # Working Dir
        ctk.CTkLabel(f, text="Working Directory:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(4, 2))
        wdir_v = ctk.StringVar(value=task.working_dir or "")
        ctk.CTkEntry(f, textvariable=wdir_v).pack(fill="x", padx=10, pady=(0, 6))

        # Terminal Type
        ctk.CTkLabel(f, text="Terminal Emulator (if Terminal task):", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(4, 2))
        term_v = ctk.StringVar(value=task.terminal_type or "wt")
        ctk.CTkOptionMenu(f, values=["wt", "powershell", "cmd"], variable=term_v).pack(anchor="w", padx=10, pady=(0, 6))

        # Checkboxes
        one_time_v = ctk.BooleanVar(value=task.is_one_time)
        ctk.CTkCheckBox(f, text="One-time task (Skip on 'Resume Last Session')", variable=one_time_v).pack(anchor="w", padx=10, pady=4)

        approved_v = ctk.BooleanVar(value=task.approved)
        ctk.CTkCheckBox(f, text="Approved Command (Permitted to execute automatically)", variable=approved_v).pack(anchor="w", padx=10, pady=4)

        # Buttons
        btn_box = ctk.CTkFrame(f, fg_color="transparent")
        btn_box.pack(fill="x", padx=10, pady=(12, 6))

        def _save_task_edits():
            task.name = name_v.get().strip() or "Unnamed Task"
            try:
                task.task_type = TaskType(type_v.get())
            except ValueError:
                task.task_type = TaskType.COMMAND
            task.target = target_v.get().strip()
            task.working_dir = wdir_v.get().strip() or None
            task.terminal_type = term_v.get()
            task.is_one_time = one_time_v.get()
            task.approved = approved_v.get()

            if is_new:
                self.project.tasks.append(task)

            self._render_tasks_list()
            dlg.destroy()

        ctk.CTkButton(btn_box, text="Cancel", width=70, fg_color="#3a3a4c", command=dlg.destroy).pack(side="right", padx=(6, 0))
        ctk.CTkButton(btn_box, text="Save Task", width=90, fg_color="#7aa2f7", text_color="#1a1b26", command=_save_task_edits).pack(side="right")

    # ------------------ Tab 4: Profiles ------------------ #
    def _build_profiles_tab(self):
        f = self.tab_profiles

        ctk.CTkLabel(
            f,
            text="Automation Profiles Configuration",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=12, pady=(10, 4))

        ctk.CTkLabel(
            f,
            text="Choose which tasks are executed for each automation profile.",
            font=ctk.CTkFont(size=11),
            text_color="#8888aa"
        ).pack(anchor="w", padx=12, pady=(0, 8))

        # Profile selector tabs/buttons
        self.prof_select_frame = ctk.CTkFrame(f, fg_color="transparent")
        self.prof_select_frame.pack(fill="x", padx=12, pady=4)

        self.active_profile_edit_var = ctk.StringVar(value=ProfileType.DEV.value)
        self.prof_tabs = ctk.CTkSegmentedButton(
            self.prof_select_frame,
            values=[ProfileType.BASIC.value, ProfileType.DEV.value, ProfileType.FULL.value, ProfileType.CUSTOM.value],
            variable=self.active_profile_edit_var,
            command=self._on_profile_tab_switch
        )
        self.prof_tabs.pack(fill="x")

        # Scrollable checklist of tasks for the selected profile
        self.prof_tasks_scroll = ctk.CTkScrollableFrame(
            f,
            fg_color=Theme.BG_SURFACE,
            corner_radius=8,
            border_width=1,
            border_color=Theme.BORDER_SUBTLE
        )
        self.prof_tasks_scroll.pack(fill="both", expand=True, padx=12, pady=(8, 12))

        self.prof_task_vars: Dict[str, ctk.BooleanVar] = {}

    def _on_profile_tab_switch(self, chosen: str):
        self._render_profile_tasks_checklist(chosen)

    def _render_profile_tasks_checklist(self, profile_name: str):
        for w in self.prof_tasks_scroll.winfo_children():
            w.destroy()
        self.prof_task_vars.clear()

        prof = self.project.profiles.get(profile_name)
        enabled_ids = set(prof.enabled_task_ids) if prof else set()

        for task in self.project.tasks:
            var = ctk.BooleanVar(value=(task.id in enabled_ids))
            self.prof_task_vars[task.id] = var

            chk = ctk.CTkCheckBox(
                self.prof_tasks_scroll,
                text=f"{task.name}  [{task.task_type.value}]",
                variable=var,
                command=lambda: self._save_profile_task_state(profile_name)
            )
            chk.pack(anchor="w", padx=8, pady=4)

    def _save_profile_task_state(self, profile_name: str):
        enabled = [tid for tid, var in self.prof_task_vars.items() if var.get()]
        if profile_name not in self.project.profiles:
            self.project.profiles[profile_name] = ProfileConfig(name=profile_name, profile_type=profile_name)
        self.project.profiles[profile_name].enabled_task_ids = enabled

    # ------------------ Helpers ------------------ #
    def _populate_fields(self):
        self.root_path_var.set(self.project.root_path)
        self.name_var.set(self.project.name)
        self.type_var.set(self.project.project_type.value)
        self.desc_entry.insert(0, self.project.description)

        self.ag_exe_var.set(self.project.antigravity.executable_path)
        self.reuse_var.set(self.project.antigravity.reuse_window)
        self.new_win_var.set(self.project.antigravity.new_window)
        self.init_files_var.set(", ".join(self.project.antigravity.initial_files))

        self._render_tasks_list()
        self._render_profile_tasks_checklist(self.active_profile_edit_var.get())

    def _browse_root_folder(self):
        folder = filedialog.askdirectory(title="Select Project Root Folder")
        if folder:
            self.root_path_var.set(folder)
            # Sniff and auto-populate
            p_type, indicators = detect_project_type(folder)
            self.type_var.set(p_type.value)
            if not self.name_var.get() or self.name_var.get() == "New Project":
                self.name_var.set(Path(folder).name)

            # Auto-generate default tasks if brand new
            if not self.is_edit_mode and not self.project.tasks:
                gen_proj = generate_default_project_config(folder, self.name_var.get())
                self.project.tasks = gen_proj.tasks
                self.project.profiles = gen_proj.profiles
                self._render_tasks_list()
                self._render_profile_tasks_checklist(self.active_profile_edit_var.get())

    def _browse_ag_exe(self):
        f = filedialog.askopenfilename(
            title="Select Antigravity Executable",
            filetypes=[("Executables", "*.exe;*.cmd;*.bat"), ("All Files", "*.*")]
        )
        if f:
            self.ag_exe_var.set(f)

    def _autodetect_ag(self):
        detected = find_antigravity_executable()
        if detected:
            self.ag_exe_var.set(detected)
        else:
            messagebox.showinfo("Auto-Detect", "Antigravity was not found in standard paths.")

    def _handle_save(self):
        root_p = self.root_path_var.get().strip()
        if not root_p or not Path(root_p).is_dir():
            messagebox.showwarning("Validation Error", "Please provide a valid existing Project Root Folder.")
            return

        # Check if remember is checked in the tab
        if self.remember_ide_var.get():
            self.project.ide_preference.remembered = True
            self.project.ide_preference.executable_path = self.ag_exe_var.get().strip()
            self._finalize_save()
            return

        # If not remembered, prompt user at the time of final submission to pick an IDE
        IDESelectionModal(
            self,
            project=self.project,
            action_button_text="Confirm & Save Project",
            on_confirm=self._on_ide_confirmed_final_submission
        )

    def _on_ide_confirmed_final_submission(self, pref: IDEPreference):
        self.project.ide_preference = pref
        self.ag_exe_var.set(pref.executable_path)
        self.remember_ide_var.set(pref.remembered)
        self._finalize_save()

    def _finalize_save(self):
        root_p = self.root_path_var.get().strip()
        name = self.name_var.get().strip() or Path(root_p).name
        self.project.name = name
        self.project.root_path = root_p
        try:
            self.project.project_type = ProjectType(self.type_var.get())
        except ValueError:
            self.project.project_type = ProjectType.OTHER
        self.project.description = self.desc_entry.get().strip()

        # IDE & Antigravity config
        chosen_exe = self.ag_exe_var.get().strip()
        self.project.antigravity.executable_path = chosen_exe
        self.project.ide_preference.executable_path = chosen_exe
        self.project.ide_preference.reuse_window = self.reuse_var.get()
        self.project.ide_preference.new_window = self.new_win_var.get()
        self.project.ide_preference.remembered = self.remember_ide_var.get()

        self.project.antigravity.reuse_window = self.reuse_var.get()
        self.project.antigravity.new_window = self.new_win_var.get()
        raw_files = [f.strip() for f in self.init_files_var.get().split(",") if f.strip()]
        self.project.antigravity.initial_files = raw_files

        # Ensure profiles exist
        for prof_type in ProfileType:
            if prof_type.value not in self.project.profiles:
                self.project.profiles[prof_type.value] = ProfileConfig(
                    name=prof_type.value,
                    profile_type=prof_type.value,
                    enabled_task_ids=[t.id for t in self.project.tasks]
                )

        if self.on_save:
            self.on_save(self.project)

        self.destroy()
