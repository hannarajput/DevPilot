"""Workflow Progress Panel showing live task execution checklist and retries."""

import customtkinter as ctk
from typing import Dict, Optional, Callable

from devpilot.core.models import TaskStatus, TaskExecutionResult
from devpilot.ui.theme import Theme


class TaskItemRow(ctk.CTkFrame):
    def __init__(self, master, task_id: str, task_name: str, on_retry: Optional[Callable[[str], None]] = None, **kwargs):
        super().__init__(
            master,
            fg_color=Theme.BG_SURFACE,
            corner_radius=8,
            border_width=1,
            border_color=Theme.BORDER_SUBTLE,
            **kwargs
        )
        self.task_id = task_id
        self.task_name = task_name
        self.on_retry = on_retry
        self.status = TaskStatus.QUEUED

        self._build_ui()

    def _build_ui(self):
        # Icon / status indicator
        self.icon_label = ctk.CTkLabel(
            self,
            text="⏳",
            width=24,
            font=ctk.CTkFont(size=13)
        )
        self.icon_label.pack(side="left", padx=(8, 4), pady=6)

        # Task Name
        self.name_label = ctk.CTkLabel(
            self,
            text=self.task_name,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=Theme.TEXT_PRIMARY,
            anchor="w"
        )
        self.name_label.pack(side="left", fill="x", expand=True, padx=4, pady=6)

        # Message / Status detail
        self.msg_label = ctk.CTkLabel(
            self,
            text="Queued",
            font=ctk.CTkFont(size=11),
            text_color=Theme.TEXT_MUTED,
            anchor="e"
        )
        self.msg_label.pack(side="left", padx=6, pady=6)

        # Retry button (visible only on failure)
        self.retry_btn = ctk.CTkButton(
            self,
            text="Retry",
            width=50,
            height=22,
            fg_color=Theme.BTN_DANGER_BG,
            hover_color=Theme.BTN_DANGER_HOVER,
            text_color=Theme.BTN_DANGER_TEXT,
            corner_radius=6,
            font=ctk.CTkFont(size=10, weight="bold"),
            command=self._handle_retry
        )
        # Unpacked initially

    def update_status(self, status: TaskStatus, message: str, result: Optional[TaskExecutionResult] = None):
        self.status = status
        
        icons = {
            TaskStatus.QUEUED: ("⏳", Theme.TEXT_MUTED),
            TaskStatus.RUNNING: ("🔄", Theme.STATUS_RUNNING_TEXT),
            TaskStatus.SUCCESS: ("✓", Theme.STATUS_SUCCESS_TEXT),
            TaskStatus.FAILED: ("✕", Theme.STATUS_FAILED_TEXT),
            TaskStatus.SKIPPED: ("⏭", Theme.STATUS_SKIPPED_TEXT),
            TaskStatus.CANCELLED: ("⏹", Theme.TEXT_MUTED),
        }
        icon, color = icons.get(status, ("•", Theme.TEXT_MUTED))
        self.icon_label.configure(text=icon)

        display_msg = message
        if result and result.duration_seconds > 0:
            display_msg = f"{message} ({result.duration_seconds:.1f}s)"

        self.msg_label.configure(text=display_msg[:45], text_color=color)

        if status == TaskStatus.FAILED:
            self.retry_btn.pack(side="right", padx=(4, 8), pady=6)
        else:
            self.retry_btn.pack_forget()

    def _handle_retry(self):
        if self.on_retry:
            self.on_retry(self.task_id)


class ProgressPanel(ctk.CTkFrame):
    def __init__(self, master, on_retry_task: Optional[Callable[[str], None]] = None, **kwargs):
        super().__init__(
            master,
            fg_color=Theme.BG_CARD,
            corner_radius=14,
            border_width=1,
            border_color=Theme.BORDER_SUBTLE,
            **kwargs
        )
        self.on_retry_task = on_retry_task
        self.task_rows: Dict[str, TaskItemRow] = {}

        self._build_header()
        self._build_progress_bar()
        self._build_tasks_scroll()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(12, 4))

        self.title_label = ctk.CTkLabel(
            header,
            text="Workflow Execution",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        self.title_label.pack(side="left")

        self.subtitle_label = ctk.CTkLabel(
            header,
            text="No active launch",
            font=ctk.CTkFont(size=11),
            text_color=Theme.TEXT_MUTED
        )
        self.subtitle_label.pack(side="right")

    def _build_progress_bar(self):
        bar_frame = ctk.CTkFrame(self, fg_color="transparent")
        bar_frame.pack(fill="x", padx=14, pady=4)

        self.progress_bar = ctk.CTkProgressBar(
            bar_frame,
            height=8,
            corner_radius=4,
            progress_color=Theme.BTN_PRIMARY_BG
        )
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0.0)

    def _build_tasks_scroll(self):
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=(4, 10))

    def reset_for_workflow(self, project_name: str, profile_name: str, tasks: list):
        self.title_label.configure(text=f"Launching: {project_name}")
        self.subtitle_label.configure(text=f"Profile: {profile_name}")
        self.progress_bar.set(0.0)

        for row in self.task_rows.values():
            row.destroy()
        self.task_rows.clear()

        for task in tasks:
            row = TaskItemRow(
                self.scroll_frame,
                task_id=task.id,
                task_name=task.name,
                on_retry=self.on_retry_task
            )
            row.pack(fill="x", pady=3, padx=2)
            self.task_rows[task.id] = row

    def update_task_status(self, task_id: str, status: TaskStatus, message: str, result: Optional[TaskExecutionResult] = None):
        row = self.task_rows.get(task_id)
        if row:
            row.update_status(status, message, result)

        total = len(self.task_rows)
        if total > 0:
            finished = sum(
                1 for r in self.task_rows.values()
                if r.status in (TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.SKIPPED, TaskStatus.CANCELLED)
            )
            self.progress_bar.set(finished / total)

    def set_finished_status(self, success: bool, summary: str):
        self.subtitle_label.configure(
            text="Completed" if success else "Failed",
            text_color=Theme.STATUS_SUCCESS_TEXT if success else Theme.STATUS_FAILED_TEXT
        )
        if success:
            self.progress_bar.set(1.0)
