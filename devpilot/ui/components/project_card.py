"""Individual Project Card component for the DevPilot dashboard."""

import os
import subprocess
import customtkinter as ctk
from typing import Callable, Optional

from devpilot.core.models import ProjectConfig, ProjectType, ProfileType
from devpilot.core.resource_launcher import get_resource_icon
from devpilot.ui.theme import Theme


class ProjectCard(ctk.CTkFrame):
    def __init__(
        self,
        master,
        project: ProjectConfig,
        on_launch: Callable[[ProjectConfig, str], None],
        on_stop: Callable[[ProjectConfig], None],
        on_configure: Callable[[ProjectConfig], None],
        on_health_check: Callable[[ProjectConfig], None],
        on_delete: Callable[[ProjectConfig], None],
        on_profile_change: Callable[[ProjectConfig, str], None],
        on_change_ide: Optional[Callable[[ProjectConfig], None]] = None,
        on_add_resource: Optional[Callable[[ProjectConfig], None]] = None,
        **kwargs
    ):
        super().__init__(
            master,
            fg_color=Theme.BG_CARD,
            corner_radius=14,
            border_width=1,
            border_color=Theme.BORDER_SUBTLE,
            **kwargs
        )
        self.project = project
        self.on_launch = on_launch
        self.on_stop = on_stop
        self.on_configure = on_configure
        self.on_health_check = on_health_check
        self.on_delete = on_delete
        self.on_profile_change = on_profile_change
        self.on_change_ide = on_change_ide
        self.on_add_resource = on_add_resource

        self._build_ui()

    def _get_badge_colors(self) -> tuple:
        t = self.project.project_type
        if t == ProjectType.PYTHON:
            return Theme.BADGE_PYTHON, Theme.BADGE_PYTHON_TEXT
        elif t == ProjectType.NODEJS:
            return Theme.BADGE_NODE, Theme.BADGE_NODE_TEXT
        elif t == ProjectType.FLUTTER:
            return Theme.BADGE_FLUTTER, Theme.BADGE_FLUTTER_TEXT
        elif t == ProjectType.GIT:
            return Theme.BADGE_GIT, Theme.BADGE_GIT_TEXT
        else:
            return Theme.BADGE_OTHER, Theme.BADGE_OTHER_TEXT

    def _get_status_colors(self, status: str) -> tuple:
        if status == "Running":
            return Theme.STATUS_RUNNING, Theme.STATUS_RUNNING_TEXT
        elif status == "Success":
            return Theme.STATUS_SUCCESS, Theme.STATUS_SUCCESS_TEXT
        elif status == "Failed":
            return Theme.STATUS_FAILED, Theme.STATUS_FAILED_TEXT
        elif status == "Stopped":
            return Theme.STATUS_SKIPPED, Theme.STATUS_SKIPPED_TEXT
        else:
            return Theme.STATUS_READY, Theme.STATUS_READY_TEXT

    def _build_ui(self):
        # Top row: Type badge, Name, Status badge
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=16, pady=(14, 4))

        bg_col, fg_col = self._get_badge_colors()
        self.type_badge = ctk.CTkLabel(
            top_frame,
            text=f" {self.project.project_type.value.upper()} ",
            fg_color=bg_col,
            text_color=fg_col,
            corner_radius=6,
            font=ctk.CTkFont(size=10, weight="bold")
        )
        self.type_badge.pack(side="left", padx=(0, 8))

        self.name_label = ctk.CTkLabel(
            top_frame,
            text=self.project.name,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=Theme.TEXT_PRIMARY,
            anchor="w"
        )
        self.name_label.pack(side="left", fill="x", expand=True)

        s_bg, s_fg = self._get_status_colors(self.project.last_launch_status)
        self.status_badge = ctk.CTkLabel(
            top_frame,
            text=f" {self.project.last_launch_status} ",
            fg_color=s_bg,
            text_color=s_fg,
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.status_badge.pack(side="right")

        # Second row: Path and open folder action
        path_frame = ctk.CTkFrame(self, fg_color="transparent")
        path_frame.pack(fill="x", padx=16, pady=(2, 6))

        short_path = self.project.root_path
        if len(short_path) > 55:
            short_path = short_path[:25] + "..." + short_path[-27:]

        self.path_label = ctk.CTkLabel(
            path_frame,
            text=f"📁 {short_path}",
            font=ctk.CTkFont(size=11),
            text_color=Theme.TEXT_MUTED,
            anchor="w"
        )
        self.path_label.pack(side="left", fill="x", expand=True)

        open_folder_btn = ctk.CTkButton(
            path_frame,
            text="Open Folder",
            width=75,
            height=22,
            fg_color=Theme.BTN_SECONDARY_BG,
            hover_color=Theme.BTN_SECONDARY_HOVER,
            text_color=Theme.BTN_SECONDARY_TEXT,
            corner_radius=6,
            font=ctk.CTkFont(size=10, weight="bold"),
            command=self._open_in_explorer
        )
        open_folder_btn.pack(side="right")

        # Third row: Profile selection & IDE Preference
        prof_frame = ctk.CTkFrame(self, fg_color="transparent")
        prof_frame.pack(fill="x", padx=16, pady=(4, 8))

        prof_label = ctk.CTkLabel(
            prof_frame,
            text="Profile:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=Theme.TEXT_SECONDARY
        )
        prof_label.pack(side="left", padx=(0, 6))

        profile_options = list(self.project.profiles.keys())
        if not profile_options:
            profile_options = [p.value for p in ProfileType]

        current_val = self.project.active_profile if self.project.active_profile in profile_options else profile_options[0]

        self.profile_dropdown = ctk.CTkOptionMenu(
            prof_frame,
            values=profile_options,
            command=self._on_profile_selected,
            height=26,
            width=150,
            font=ctk.CTkFont(size=11),
            corner_radius=8,
            fg_color=Theme.BTN_SECONDARY_BG,
            button_color=Theme.BTN_SECONDARY_HOVER,
            button_hover_color=Theme.BORDER_FOCUS,
            text_color=Theme.BTN_SECONDARY_TEXT
        )
        self.profile_dropdown.set(current_val)
        self.profile_dropdown.pack(side="left")

        # IDE indicator & Change button
        self.ide_frame = ctk.CTkFrame(prof_frame, fg_color="transparent")
        self.ide_frame.pack(side="right")

        self.ide_label = ctk.CTkLabel(
            self.ide_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=Theme.TEXT_MUTED
        )
        self.ide_label.pack(side="left", padx=(0, 6))

        self.change_ide_btn = ctk.CTkButton(
            self.ide_frame,
            text="Change IDE",
            width=78,
            height=22,
            fg_color=Theme.BTN_SECONDARY_BG,
            hover_color=Theme.BTN_SECONDARY_HOVER,
            text_color=Theme.BTN_SECONDARY_TEXT,
            corner_radius=6,
            font=ctk.CTkFont(size=10, weight="bold"),
            command=self._handle_change_ide
        )
        self.change_ide_btn.pack(side="left")

        self.refresh_ide_display()

        # Attached Workspace Resources Row
        self.resources_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.resources_frame.pack(fill="x", padx=16, pady=(2, 6))

        self.refresh_resources_display()

        # Fourth row: Action buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(6, 14))

        # Launch Button (Signature solid pill button)
        self.launch_btn = ctk.CTkButton(
            btn_frame,
            text="▶  Launch Project",
            fg_color=Theme.BTN_PRIMARY_BG,
            hover_color=Theme.BTN_PRIMARY_HOVER,
            text_color=Theme.BTN_PRIMARY_TEXT,
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=18,
            height=32,
            command=self._handle_launch
        )
        self.launch_btn.pack(side="left", padx=(0, 8))

        # Stop Button
        self.stop_btn = ctk.CTkButton(
            btn_frame,
            text="⏹ Stop",
            fg_color=Theme.BTN_DANGER_BG,
            hover_color=Theme.BTN_DANGER_HOVER,
            text_color=Theme.BTN_DANGER_TEXT,
            font=ctk.CTkFont(size=11, weight="bold"),
            corner_radius=18,
            height=32,
            width=75,
            command=self._handle_stop
        )
        # Unpacked initially

        # Health Check Button
        health_btn = ctk.CTkButton(
            btn_frame,
            text="Health Check",
            fg_color=Theme.BTN_SECONDARY_BG,
            hover_color=Theme.BTN_SECONDARY_HOVER,
            text_color=Theme.BTN_SECONDARY_TEXT,
            font=ctk.CTkFont(size=11),
            corner_radius=8,
            height=32,
            width=92,
            command=lambda: self.on_health_check(self.project)
        )
        health_btn.pack(side="left", padx=(0, 8))

        # Configure Button
        config_btn = ctk.CTkButton(
            btn_frame,
            text="⚙ Configure",
            fg_color=Theme.BTN_SECONDARY_BG,
            hover_color=Theme.BTN_SECONDARY_HOVER,
            text_color=Theme.BTN_SECONDARY_TEXT,
            font=ctk.CTkFont(size=11),
            corner_radius=8,
            height=32,
            width=90,
            command=lambda: self.on_configure(self.project)
        )
        config_btn.pack(side="left", padx=(0, 8))

        # Delete Button
        del_btn = ctk.CTkButton(
            btn_frame,
            text="✕",
            fg_color="transparent",
            hover_color=Theme.STATUS_FAILED,
            text_color=Theme.TEXT_MUTED,
            font=ctk.CTkFont(size=13),
            corner_radius=8,
            height=32,
            width=32,
            command=lambda: self.on_delete(self.project)
        )
        del_btn.pack(side="right")

    def _open_in_explorer(self):
        p = self.project.root_path
        if os.path.exists(p):
            subprocess.Popen(f'explorer "{p}"')

    def _on_profile_selected(self, chosen: str):
        self.project.active_profile = chosen
        self.on_profile_change(self.project, chosen)

    def _handle_change_ide(self):
        if self.on_change_ide:
            self.on_change_ide(self.project)

    def refresh_ide_display(self):
        pref = self.project.ide_preference
        if pref and pref.remembered and pref.ide_name:
            self.ide_label.configure(
                text=f"💻 {pref.ide_name} (Remembered)",
                text_color=Theme.STATUS_SUCCESS_TEXT
            )
        elif pref and pref.ide_name:
            self.ide_label.configure(
                text=f"💻 {pref.ide_name} (Ask on launch)",
                text_color=Theme.STATUS_RUNNING_TEXT
            )
        else:
            self.ide_label.configure(
                text="💻 IDE: Not set (Ask on launch)",
                text_color=Theme.TEXT_MUTED
            )

    def refresh_resources_display(self):
        for w in self.resources_frame.winfo_children():
            w.destroy()

        left_chips = ctk.CTkFrame(self.resources_frame, fg_color="transparent")
        left_chips.pack(side="left", fill="x", expand=True)

        res_list = self.project.resources
        enabled_count = len(self.project.get_enabled_resources())
        total_count = len(res_list)

        if not res_list:
            ctk.CTkLabel(
                left_chips,
                text="🔗 No resources attached",
                font=ctk.CTkFont(size=11),
                text_color=Theme.TEXT_MUTED
            ).pack(side="left", padx=(0, 8))
        else:
            # Display up to 4 resource badges
            for r in res_list[:4]:
                icon = get_resource_icon(r.resource_type, r.target)
                name_disp = r.name if len(r.name) <= 14 else r.name[:12] + "…"
                chip_col = Theme.BG_SURFACE if r.enabled else Theme.BG_CARD
                text_col = Theme.TEXT_PRIMARY if r.enabled else Theme.TEXT_MUTED
                chip = ctk.CTkFrame(
                    left_chips,
                    fg_color=chip_col,
                    corner_radius=6,
                    border_width=1,
                    border_color=Theme.BORDER_SUBTLE
                )
                chip.pack(side="left", padx=(0, 6))
                ctk.CTkLabel(
                    chip,
                    text=f"{icon} {name_disp}",
                    font=ctk.CTkFont(size=10, weight="bold" if r.enabled else "normal"),
                    text_color=text_col
                ).pack(padx=6, pady=2)

            if total_count > 4:
                ctk.CTkLabel(
                    left_chips,
                    text=f"+{total_count - 4} more",
                    font=ctk.CTkFont(size=10),
                    text_color=Theme.TEXT_MUTED
                ).pack(side="left", padx=(0, 6))

        # Right side: status indicator + Add Resource quick action
        right_box = ctk.CTkFrame(self.resources_frame, fg_color="transparent")
        right_box.pack(side="right")

        if total_count > 0:
            status_text = f"✓ {enabled_count}/{total_count} Active" if enabled_count == total_count else f"{enabled_count}/{total_count} Active"
            ctk.CTkLabel(
                right_box,
                text=status_text,
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color=Theme.STATUS_SUCCESS_TEXT if enabled_count > 0 else Theme.TEXT_MUTED
            ).pack(side="left", padx=(0, 8))

        add_res_btn = ctk.CTkButton(
            right_box,
            text="+ Resource",
            width=78,
            height=22,
            fg_color=Theme.BTN_SECONDARY_BG,
            hover_color=Theme.BTN_SECONDARY_HOVER,
            text_color=Theme.BTN_SECONDARY_TEXT,
            corner_radius=6,
            font=ctk.CTkFont(size=10, weight="bold"),
            command=self._handle_add_resource
        )
        add_res_btn.pack(side="left")

    def _handle_add_resource(self):
        if self.on_add_resource:
            self.on_add_resource(self.project)

    def _handle_launch(self):
        active_prof = self.profile_dropdown.get()
        self.set_running_state(True)
        self.on_launch(self.project, active_prof)

    def _handle_stop(self):
        self.on_stop(self.project)
        self.set_running_state(False)

    def set_running_state(self, running: bool):
        if running:
            s_bg, s_fg = self._get_status_colors("Running")
            self.status_badge.configure(text=" Running ", fg_color=s_bg, text_color=s_fg)
            self.launch_btn.pack_forget()
            self.stop_btn.pack(side="left", padx=(0, 8))
        else:
            self.stop_btn.pack_forget()
            self.launch_btn.pack(side="left", padx=(0, 8))

    def update_status(self, status: str):
        self.project.last_launch_status = status
        s_bg, s_fg = self._get_status_colors(status)
        self.status_badge.configure(text=f" {status} ", fg_color=s_bg, text_color=s_fg)
        self.set_running_state(status == "Running")
