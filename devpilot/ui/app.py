"""Main DevPilot desktop application window and user interface coordinator."""

import os
import datetime
from pathlib import Path
from typing import List, Optional, Dict
import customtkinter as ctk
from tkinter import messagebox

from devpilot.core.models import (
    ProjectConfig,
    ProjectType,
    ProfileType,
    AppSettings,
    SessionHistory,
    TaskStatus,
    TaskExecutionResult,
    ResourceConfig,
)
from devpilot.core.storage import StorageManager
from devpilot.core.orchestrator import WorkflowOrchestrator
from devpilot.core.detector import generate_default_project_config
from devpilot.core.antigravity import find_antigravity_executable
from devpilot.core.resource_launcher import get_resource_icon
from devpilot.ui.components.project_card import ProjectCard
from devpilot.ui.components.progress_panel import ProgressPanel
from devpilot.ui.components.log_console import LogConsole
from devpilot.ui.components.status_bar import StatusBar
from devpilot.ui.dialogs.project_editor import ProjectEditorDialog
from devpilot.ui.dialogs.health_check_modal import HealthCheckModal
from devpilot.ui.dialogs.settings_dialog import SettingsDialog
from devpilot.ui.dialogs.ide_selection_modal import IDESelectionModal
from devpilot.ui.dialogs.resource_editor_modal import ResourceEditorModal
from devpilot.core.models import IDEPreference
from devpilot.ui.theme import Theme
from devpilot.utils.logger import logger


class DevPilotApp(ctk.CTk):
    def __init__(self, storage_manager: Optional[StorageManager] = None):
        super().__init__()

        # Setup CustomTkinter appearance with humanized minimal theme
        self.storage = storage_manager or StorageManager()
        self.settings: AppSettings = self.storage.load_settings()
        self.session: SessionHistory = self.storage.load_session()
        self.projects: List[ProjectConfig] = self.storage.load_projects()

        initial_mode = self.settings.theme if self.settings.theme in ("light", "dark") else "light"
        ctk.set_appearance_mode(initial_mode)
        ctk.set_default_color_theme("blue")

        self.title("DevPilot — Development Workspace Manager")
        self.geometry("1300x840")
        self.minsize(1040, 720)

        self.orchestrator = WorkflowOrchestrator()
        self.orchestrator.on_task_update = self._on_task_update_received
        self.orchestrator.on_workflow_finished = self._on_workflow_finished_received

        self.active_project: Optional[ProjectConfig] = None
        self.active_category = "All"
        self.search_query = ""

        self.project_cards: Dict[str, ProjectCard] = {}

        # Initialize defaults if store is completely empty
        self._ensure_sample_projects_if_empty()

        # Build UI layout
        self._build_top_header()
        self._build_main_split()
        self._build_status_bar()

        # Populate
        self.refresh_project_list()
        self._update_resume_button_state()

        logger.info("DevPilot initialized. Antigravity integration ready.")

    def _ensure_sample_projects_if_empty(self):
        """If brand new installation, detect current directory as a project or add sample."""
        if not self.projects:
            # Add current DevPilot workspace itself as a detected Python project
            cwd = os.getcwd()
            proj = generate_default_project_config(cwd, "DevPilot Workspace")
            self.projects.append(proj)
            self.storage.save_projects(self.projects)

    # ---------------- UI Construction ---------------- #

    def _build_top_header(self):
        self.header_frame = ctk.CTkFrame(
            self,
            fg_color=Theme.BG_HEADER,
            height=70,
            corner_radius=0,
            border_width=1,
            border_color=Theme.BORDER_SUBTLE
        )
        self.header_frame.pack(fill="x", side="top")
        self.header_frame.pack_propagate(False)

        # App Logo & Title
        title_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=(20, 16), pady=12)

        logo_label = ctk.CTkLabel(
            title_box,
            text="⚡ DevPilot",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        logo_label.pack(side="left")

        sub_label = ctk.CTkLabel(
            title_box,
            text="  workspace",
            font=ctk.CTkFont(size=12),
            text_color=Theme.TEXT_MUTED
        )
        sub_label.pack(side="left")

        # Resume Last Session Button
        self.resume_btn = ctk.CTkButton(
            self.header_frame,
            text="↺ Resume Last Session",
            fg_color=Theme.BTN_SECONDARY_BG,
            hover_color=Theme.BTN_SECONDARY_HOVER,
            text_color=Theme.BTN_SECONDARY_TEXT,
            corner_radius=18,
            font=ctk.CTkFont(size=12, weight="bold"),
            height=34,
            command=self._handle_resume_last_session
        )
        self.resume_btn.pack(side="left", padx=10, pady=14)

        # Search box (Pill minimal design)
        self.search_entry = ctk.CTkEntry(
            self.header_frame,
            placeholder_text="Search projects...",
            width=240,
            height=34,
            corner_radius=18,
            fg_color=Theme.BG_INPUT,
            border_color=Theme.BORDER_SUBTLE,
            text_color=Theme.TEXT_PRIMARY,
            placeholder_text_color=Theme.TEXT_MUTED,
            font=ctk.CTkFont(size=11)
        )
        self.search_entry.pack(side="left", padx=(16, 10), pady=14)
        self.search_entry.bind("<KeyRelease>", self._on_search_key)

        # Action Buttons (Right)
        right_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        right_box.pack(side="right", padx=20, pady=14)

        # Theme Toggle Button (☀️ / 🌙)
        current_mode = ctk.get_appearance_mode().lower()
        theme_icon_text = "🌙 Dark" if current_mode == "light" else "☀️ Light"
        self.theme_btn = ctk.CTkButton(
            right_box,
            text=theme_icon_text,
            width=78,
            height=34,
            fg_color=Theme.BTN_SECONDARY_BG,
            hover_color=Theme.BTN_SECONDARY_HOVER,
            text_color=Theme.BTN_SECONDARY_TEXT,
            corner_radius=18,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._toggle_theme
        )
        self.theme_btn.pack(side="left", padx=(0, 8))

        self.settings_btn = ctk.CTkButton(
            right_box,
            text="⚙ Settings",
            width=85,
            height=34,
            fg_color=Theme.BTN_SECONDARY_BG,
            hover_color=Theme.BTN_SECONDARY_HOVER,
            text_color=Theme.BTN_SECONDARY_TEXT,
            corner_radius=18,
            font=ctk.CTkFont(size=11),
            command=self._open_settings_dialog
        )
        self.settings_btn.pack(side="left", padx=(0, 8))

        self.add_btn = ctk.CTkButton(
            right_box,
            text="+ Add Project",
            width=115,
            height=34,
            fg_color=Theme.BTN_PRIMARY_BG,
            hover_color=Theme.BTN_PRIMARY_HOVER,
            text_color=Theme.BTN_PRIMARY_TEXT,
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=18,
            command=self._open_add_project_dialog
        )
        self.add_btn.pack(side="left")

    def _toggle_theme(self):
        """Toggle dynamically between Light and Dark mode."""
        current_mode = ctk.get_appearance_mode().lower()
        new_mode = "dark" if current_mode == "light" else "light"
        ctk.set_appearance_mode(new_mode)
        self.settings.theme = new_mode
        self.storage.save_settings(self.settings)

        self.theme_btn.configure(text="🌙 Dark" if new_mode == "light" else "☀️ Light")
        logger.info(f"Appearance theme switched to: {new_mode.upper()} mode")

    def _build_main_split(self):
        self.main_container = ctk.CTkFrame(self, fg_color=Theme.BG_ROOT, corner_radius=0)
        self.main_container.pack(fill="both", expand=True)

        # Left Column: Overview Metric Banner + Filter tabs + Project cards
        self.left_column = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.left_column.pack(side="left", fill="both", expand=True, padx=(18, 9), pady=14)

        # Minimal Overview Banner (Inspired by the editorial design in the reference image)
        self._build_overview_banner(self.left_column)

        # Filter Tabs (Segmented pill button)
        self.tab_filter = ctk.CTkSegmentedButton(
            self.left_column,
            values=["All", "Python", "Node.js", "Flutter", "Git", "Recent"],
            command=self._on_category_switch,
            height=30,
            corner_radius=18,
            fg_color=Theme.BG_CARD,
            selected_color=Theme.BTN_PRIMARY_BG,
            selected_hover_color=Theme.BTN_PRIMARY_HOVER,
            text_color=Theme.TEXT_PRIMARY
        )
        self.tab_filter.set("All")
        self.tab_filter.pack(fill="x", pady=(0, 10))

        # Project Cards Scrollable Frame
        self.cards_scroll = ctk.CTkScrollableFrame(self.left_column, fg_color="transparent")
        self.cards_scroll.pack(fill="both", expand=True)

        # Right Column: Workflow checklist + Logs
        self.right_column = ctk.CTkFrame(self.main_container, fg_color="transparent", width=490)
        self.right_column.pack(side="right", fill="both", padx=(9, 18), pady=14)
        self.right_column.pack_propagate(False)

        # Top Right: Progress Checklist
        self.progress_panel = ProgressPanel(
            self.right_column,
            on_retry_task=self._handle_retry_task,
            height=280
        )
        self.progress_panel.pack(fill="x", pady=(0, 10))

        # Bottom Right: Real-time Log Console
        self.log_console = LogConsole(
            self.right_column
        )
        self.log_console.pack(fill="both", expand=True)

    def _build_overview_banner(self, parent):
        """Minimal overview card showing project count and IDE status."""
        banner = ctk.CTkFrame(
            parent,
            fg_color=Theme.BG_CARD,
            corner_radius=14,
            border_width=1,
            border_color=Theme.BORDER_SUBTLE
        )
        banner.pack(fill="x", pady=(0, 12))

        inner = ctk.CTkFrame(banner, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=12)

        # Left: greeting/title
        left_f = ctk.CTkFrame(inner, fg_color="transparent")
        left_f.pack(side="left")

        ctk.CTkLabel(
            left_f,
            text="Workspace Dashboard",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor="w")

        self.project_stats_label = ctk.CTkLabel(
            left_f,
            text=f"{len(self.projects)} configured projects ready for one-click launch",
            font=ctk.CTkFont(size=11),
            text_color=Theme.TEXT_MUTED
        )
        self.project_stats_label.pack(anchor="w")

        # Right: Quick badges
        right_f = ctk.CTkFrame(inner, fg_color="transparent")
        right_f.pack(side="right")

        self.ag_badge = ctk.CTkLabel(
            right_f,
            text=" Antigravity IDE: Ready ",
            fg_color=Theme.STATUS_SUCCESS,
            text_color=Theme.STATUS_SUCCESS_TEXT,
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.ag_badge.pack(side="right", padx=(8, 0))

    def _build_status_bar(self):
        self.status_bar = StatusBar(self)
        self.status_bar.pack(side="bottom", fill="x")

    # ---------------- Project Filtering & Rendering ---------------- #

    def refresh_project_list(self):
        for card in self.project_cards.values():
            card.destroy()
        self.project_cards.clear()

        filtered = self._filter_projects()

        if not filtered:
            empty_lbl = ctk.CTkLabel(
                self.cards_scroll,
                text="No projects match your filter.\nClick '+ Add Project' to configure a project workspace.",
                font=ctk.CTkFont(size=13),
                text_color=Theme.TEXT_MUTED,
                justify="center"
            )
            empty_lbl.pack(pady=40)
            return

        for proj in filtered:
            card = ProjectCard(
                self.cards_scroll,
                project=proj,
                on_launch=self._handle_launch_project,
                on_stop=self._handle_stop_project,
                on_configure=self._handle_configure_project,
                on_health_check=self._handle_health_check_project,
                on_delete=self._handle_delete_project,
                on_profile_change=self._handle_profile_change,
                on_change_ide=self._handle_change_ide_prompt,
                on_add_resource=self._handle_add_resource_to_project
            )
            card.pack(fill="x", pady=6, padx=2)
            self.project_cards[proj.id] = card

    def _filter_projects(self) -> List[ProjectConfig]:
        results = []
        for p in self.projects:
            # Text search
            if self.search_query:
                q = self.search_query.lower()
                if q not in p.name.lower() and q not in p.root_path.lower() and q not in p.project_type.value.lower():
                    continue

            # Category filter
            if self.active_category == "Python" and p.project_type != ProjectType.PYTHON:
                continue
            elif self.active_category == "Node.js" and p.project_type != ProjectType.NODEJS:
                continue
            elif self.active_category == "Flutter" and p.project_type != ProjectType.FLUTTER:
                continue
            elif self.active_category == "Git" and p.project_type != ProjectType.GIT:
                continue
            elif self.active_category == "Recent":
                if not p.last_launched_at:
                    continue

            results.append(p)

        # Sort recent if requested
        if self.active_category == "Recent":
            results.sort(key=lambda x: x.last_launched_at or "", reverse=True)

        return results

    def _on_category_switch(self, value: str):
        self.active_category = value
        self.refresh_project_list()

    def _on_search_key(self, event=None):
        self.search_query = self.search_entry.get().strip()
        self.refresh_project_list()

    def _update_resume_button_state(self):
        if self.session.last_project_id and self.session.last_project_name:
            self.resume_btn.configure(
                text=f"↺ Resume: {self.session.last_project_name[:18]}",
                state="normal",
                fg_color=Theme.BTN_SECONDARY_BG,
                text_color=Theme.TEXT_PRIMARY
            )
        else:
            self.resume_btn.configure(
                text="↺ Resume Last Session",
                state="disabled",
                fg_color=Theme.BG_CARD,
                text_color=Theme.TEXT_MUTED
            )

    # ---------------- Actions & Workflow Execution ---------------- #

    def _handle_launch_project(self, project: ProjectConfig, profile_name: str, is_resume: bool = False):
        if self.orchestrator.is_running:
            messagebox.showinfo("Busy", "A workflow is already executing. Please stop it or wait for completion.")
            return

        # Prompt user to choose IDE if not remembered for this project
        if not is_resume and not project.ide_preference.remembered:
            card = self.project_cards.get(project.id)
            if card:
                card.set_running_state(False)

            IDESelectionModal(
                self,
                project=project,
                action_button_text="Confirm & Launch",
                on_confirm=lambda pref: self._on_ide_confirmed_and_launch(project, profile_name, pref, is_resume=is_resume),
                on_cancel=lambda: self._on_launch_cancelled(project)
            )
            return

        # If already remembered, directly launch earlier chosen IDE!
        self._execute_project_workflow(project, profile_name, is_resume=is_resume)

    def _on_ide_confirmed_and_launch(self, project: ProjectConfig, profile_name: str, pref: IDEPreference, is_resume: bool = False):
        project.ide_preference = pref
        project.antigravity.executable_path = pref.executable_path
        self.storage.save_or_update_project(project)
        card = self.project_cards.get(project.id)
        if card:
            card.refresh_ide_display()
        logger.info(f"IDE chosen for '{project.name}': {pref.ide_name} (Remembered: {pref.remembered})")
        self._execute_project_workflow(project, profile_name, is_resume=is_resume)

    def _on_launch_cancelled(self, project: ProjectConfig):
        card = self.project_cards.get(project.id)
        if card:
            card.set_running_state(False)

    def _execute_project_workflow(self, project: ProjectConfig, profile_name: str, is_resume: bool = False):
        self.active_project = project
        project.last_launch_status = "Running"
        project.last_launched_at = datetime.datetime.now().isoformat()
        self.storage.save_or_update_project(project)

        # Save session history
        self.session.last_project_id = project.id
        self.session.last_project_name = project.name
        self.session.last_profile = profile_name
        self.session.last_launch_time = project.last_launched_at
        self.storage.save_session(self.session)
        self._update_resume_button_state()

        # Update Card UI
        card = self.project_cards.get(project.id)
        if card:
            card.set_running_state(True)

        # Reset Progress Panel with tasks and attached resources
        profile = project.profiles.get(profile_name)
        enabled_ids = set(profile.enabled_task_ids) if profile else {t.id for t in project.tasks if t.enabled}
        tasks_to_run = [t for t in project.tasks if t.id in enabled_ids and t.enabled]
        tasks_to_run.sort(key=lambda x: x.order)

        class WorkflowDisplayItem:
            def __init__(self, item_id: str, name: str):
                self.id = item_id
                self.name = name

        display_items = [WorkflowDisplayItem(t.id, t.name) for t in tasks_to_run]
        for res in project.get_enabled_resources():
            icon = get_resource_icon(res.resource_type, res.target)
            display_items.append(WorkflowDisplayItem(f"res_{res.id}", f"{icon} {res.name}"))

        self.progress_panel.reset_for_workflow(project.name, profile_name, display_items)

        # Launch workflow asynchronously
        self.orchestrator.launch_project_async(project, profile_name, is_resume=is_resume)

    def _handle_change_ide_prompt(self, project: ProjectConfig):
        """Allow user to switch IDE or toggle the remembered preference anytime from the card."""
        IDESelectionModal(
            self,
            project=project,
            action_button_text="Save IDE Choice",
            on_confirm=lambda pref: self._on_ide_changed_from_card(project, pref)
        )

    def _on_ide_changed_from_card(self, project: ProjectConfig, pref: IDEPreference):
        project.ide_preference = pref
        project.antigravity.executable_path = pref.executable_path
        self.storage.save_or_update_project(project)
        card = self.project_cards.get(project.id)
        if card:
            card.refresh_ide_display()
        logger.success(f"Updated IDE for '{project.name}' to: {pref.ide_name} (Remembered: {pref.remembered})")

    def _handle_stop_project(self, project: ProjectConfig):
        self.orchestrator.stop_workflow()
        project.last_launch_status = "Stopped"
        self.storage.save_or_update_project(project)

        card = self.project_cards.get(project.id)
        if card:
            card.set_running_state(False)
            card.update_status("Stopped")

    def _handle_resume_last_session(self):
        last_id = self.session.last_project_id
        if not last_id:
            messagebox.showinfo("No Previous Session", "No previously active project found to resume.")
            return

        target_proj = None
        for p in self.projects:
            if p.id == last_id:
                target_proj = p
                break

        if not target_proj:
            messagebox.showwarning("Project Not Found", f"Project with ID {last_id} could not be found.")
            return

        last_prof = self.session.last_profile or target_proj.active_profile
        logger.info(f"Resuming previous session for project: '{target_proj.name}' [Profile: {last_prof}]")
        self._handle_launch_project(target_proj, last_prof, is_resume=True)

    def _handle_retry_task(self, task_id: str):
        if not self.active_project:
            return
        logger.info(f"Initiating single task retry for task ID: {task_id}")
        self.orchestrator.retry_single_task_async(self.active_project, task_id)

    def _handle_profile_change(self, project: ProjectConfig, new_profile: str):
        project.active_profile = new_profile
        self.storage.save_or_update_project(project)
        logger.info(f"Project '{project.name}' profile set to: {new_profile}")

    def _handle_configure_project(self, project: ProjectConfig):
        ProjectEditorDialog(self, project=project, on_save=self._on_project_saved)

    def _handle_health_check_project(self, project: ProjectConfig):
        HealthCheckModal(self, project=project)

    def _handle_delete_project(self, project: ProjectConfig):
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to remove '{project.name}' from DevPilot?\n(Your project files on disk will not be touched)."
        )
        if confirm:
            self.storage.delete_project(project.id)
            self.projects = self.storage.load_projects()
            self.refresh_project_list()
            logger.info(f"Removed project: {project.name}")

    def _open_add_project_dialog(self):
        ProjectEditorDialog(self, project=None, on_save=self._on_project_saved)

    def _on_project_saved(self, project: ProjectConfig):
        self.storage.save_or_update_project(project)
        self.projects = self.storage.load_projects()
        self.refresh_project_list()
        logger.success(f"Saved configuration for: {project.name}")

    def _handle_add_resource_to_project(self, project: ProjectConfig):
        """Open Add Resource dialog directly from the project card."""
        ResourceEditorModal(
            self,
            resource=None,
            project_root=project.root_path,
            on_save=lambda r: self._on_resource_added_from_card(project, r)
        )

    def _on_resource_added_from_card(self, project: ProjectConfig, resource: ResourceConfig):
        project.add_resource(resource)
        self.storage.save_or_update_project(project)
        card = self.project_cards.get(project.id)
        if card:
            card.refresh_resources_display()
        logger.success(f"Attached resource '{resource.name}' to project '{project.name}'")

    def _open_settings_dialog(self):
        SettingsDialog(self, self.settings, on_save=self._on_settings_saved)

    def _on_settings_saved(self, settings: AppSettings):
        self.settings = settings
        self.storage.save_settings(settings)
        self.status_bar.refresh_tools()
        logger.success("Updated global settings.")

    # ---------------- Orchestrator Callbacks ---------------- #

    def _on_task_update_received(self, task_id: str, status: TaskStatus, message: str, result: Optional[TaskExecutionResult]):
        # Schedule onto main Tkinter UI thread
        self.after(0, self.progress_panel.update_task_status, task_id, status, message, result)

    def _on_workflow_finished_received(self, project_id: str, success: bool, summary: str):
        def _ui_update():
            self.progress_panel.set_finished_status(success, summary)
            proj = self.storage.get_project(project_id)
            if proj:
                new_status = "Success" if success else "Failed"
                proj.last_launch_status = new_status
                self.storage.save_or_update_project(proj)
                card = self.project_cards.get(project_id)
                if card:
                    card.set_running_state(False)
                    card.update_status(new_status)
                    card.refresh_resources_display()

        self.after(0, _ui_update)
