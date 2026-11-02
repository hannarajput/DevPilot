"""Modal dialog displaying pre-flight health check results."""

import customtkinter as ctk
from devpilot.core.models import ProjectConfig
from devpilot.core.detector import check_project_health
from devpilot.ui.theme import Theme


class HealthCheckModal(ctk.CTkToplevel):
    def __init__(self, master, project: ProjectConfig):
        super().__init__(master)
        self.title(f"Project Health Check — {project.name}")
        self.geometry("560x420")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.project = project
        self._build_ui()
        self._run_audit()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(16, 8))

        ctk.CTkLabel(
            header,
            text=f"Health Diagnostic: {self.project.name}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor="w")

        self.summary_label = ctk.CTkLabel(
            header,
            text="Running diagnostics...",
            font=ctk.CTkFont(size=12),
            text_color=Theme.TEXT_MUTED
        )
        self.summary_label.pack(anchor="w", pady=(2, 0))

        # Results area
        self.scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=Theme.BG_SURFACE,
            corner_radius=10,
            border_width=1,
            border_color=Theme.BORDER_SUBTLE
        )
        self.scroll.pack(fill="both", expand=True, padx=18, pady=8)

        # Bottom close button
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=18, pady=(8, 16))

        ctk.CTkButton(
            bottom,
            text="Close",
            fg_color=Theme.BTN_SECONDARY_BG,
            hover_color=Theme.BTN_SECONDARY_HOVER,
            text_color=Theme.BTN_SECONDARY_TEXT,
            corner_radius=8,
            width=100,
            command=self.destroy
        ).pack(side="right")

    def _run_audit(self):
        report = check_project_health(self.project)

        if report.get("passed"):
            self.summary_label.configure(text="All required health checks passed.", text_color=Theme.STATUS_SUCCESS_TEXT)
        else:
            self.summary_label.configure(text="One or more critical checks failed.", text_color=Theme.STATUS_FAILED_TEXT)

        for check in report.get("checks", []):
            row = ctk.CTkFrame(
                self.scroll,
                fg_color=Theme.BG_CARD,
                corner_radius=8,
                border_width=1,
                border_color=Theme.BORDER_SUBTLE
            )
            row.pack(fill="x", pady=4, padx=4)

            status = check.get("status", "INFO")
            icon = "✓" if status == "PASS" else ("⚠" if status == "WARN" else "✕")
            color = Theme.STATUS_SUCCESS_TEXT if status == "PASS" else (Theme.STATUS_RUNNING_TEXT if status == "WARN" else Theme.STATUS_FAILED_TEXT)

            ctk.CTkLabel(
                row,
                text=icon,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=color,
                width=30
            ).pack(side="left", padx=(8, 4), pady=8)

            info_f = ctk.CTkFrame(row, fg_color="transparent")
            info_f.pack(side="left", fill="x", expand=True, pady=8)

            ctk.CTkLabel(
                info_f,
                text=check.get("name", "Check"),
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=Theme.TEXT_PRIMARY,
                anchor="w"
            ).pack(anchor="w")

            ctk.CTkLabel(
                info_f,
                text=check.get("message", ""),
                font=ctk.CTkFont(size=11),
                text_color=color,
                anchor="w"
            ).pack(anchor="w")
