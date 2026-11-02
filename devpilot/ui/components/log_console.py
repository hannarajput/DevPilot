"""Real-time log console component with color-coded levels, search, and copy."""

import customtkinter as ctk
import tkinter as tk
from typing import Optional

from devpilot.utils.logger import logger
from devpilot.ui.theme import Theme


class LogConsole(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color=Theme.BG_CARD,
            corner_radius=14,
            border_width=1,
            border_color=Theme.BORDER_SUBTLE,
            **kwargs
        )

        self._auto_scroll = True
        self._filter_text = ""

        self._build_header()
        self._build_text_area()

        logger.subscribe(self._on_log_received)

    def _build_header(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=14, pady=(10, 6))

        title = ctk.CTkLabel(
            header_frame,
            text="Execution Logs",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        title.pack(side="left")

        # Clear button
        clear_btn = ctk.CTkButton(
            header_frame,
            text="Clear",
            width=50,
            height=24,
            fg_color=Theme.BTN_SECONDARY_BG,
            hover_color=Theme.BTN_SECONDARY_HOVER,
            text_color=Theme.BTN_SECONDARY_TEXT,
            corner_radius=6,
            font=ctk.CTkFont(size=11),
            command=self.clear_logs
        )
        clear_btn.pack(side="right", padx=(4, 0))

        # Copy button
        copy_btn = ctk.CTkButton(
            header_frame,
            text="Copy",
            width=50,
            height=24,
            fg_color=Theme.BTN_SECONDARY_BG,
            hover_color=Theme.BTN_SECONDARY_HOVER,
            text_color=Theme.BTN_SECONDARY_TEXT,
            corner_radius=6,
            font=ctk.CTkFont(size=11),
            command=self.copy_logs
        )
        copy_btn.pack(side="right", padx=(4, 0))

        # Filter entry
        self.filter_entry = ctk.CTkEntry(
            header_frame,
            placeholder_text="Filter logs...",
            width=130,
            height=26,
            corner_radius=6,
            fg_color=Theme.BG_INPUT,
            border_color=Theme.BORDER_SUBTLE,
            text_color=Theme.TEXT_PRIMARY,
            placeholder_text_color=Theme.TEXT_MUTED,
            font=ctk.CTkFont(size=11)
        )
        self.filter_entry.pack(side="right", padx=(4, 4))
        self.filter_entry.bind("<KeyRelease>", self._on_filter_changed)

    def _build_text_area(self):
        self.text_box = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word",
            corner_radius=8,
            fg_color=Theme.BG_SURFACE,
            text_color=Theme.TEXT_PRIMARY,
            activate_scrollbars=True
        )
        self.text_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        try:
            tk_text = self.text_box._textbox
            # Neutral professional accents
            tk_text.tag_config("INFO", foreground="#2563EB")
            tk_text.tag_config("WARN", foreground="#D97706")
            tk_text.tag_config("ERROR", foreground="#DC2626")
            tk_text.tag_config("SUCCESS", foreground="#16A34A")
            tk_text.tag_config("TIME", foreground="#9CA3AF")
        except Exception:
            pass

    def _on_log_received(self, timestamp: str, level: str, message: str):
        try:
            self.after(0, self._append_line, timestamp, level, message)
        except Exception:
            pass

    def _append_line(self, timestamp: str, level: str, message: str):
        if self._filter_text and self._filter_text.lower() not in message.lower() and self._filter_text.lower() not in level.lower():
            return

        try:
            tk_text = self.text_box._textbox
            tk_text.configure(state="normal")
            
            tk_text.insert("end", f"[{timestamp}] ", "TIME")
            tk_text.insert("end", f"[{level}] ", level)
            tk_text.insert("end", f"{message}\n")
            
            if self._auto_scroll:
                tk_text.see("end")
            tk_text.configure(state="disabled")
        except Exception:
            pass

    def _on_filter_changed(self, event=None):
        self._filter_text = self.filter_entry.get().strip()
        self.refresh_logs()

    def refresh_logs(self):
        try:
            tk_text = self.text_box._textbox
            tk_text.configure(state="normal")
            tk_text.delete("1.0", "end")
            tk_text.configure(state="disabled")
        except Exception:
            pass

        history = logger.get_history()
        for line in history:
            if line.startswith("[") and "]" in line:
                parts = line.split("] [", 1)
                time_str = parts[0][1:]
                rest = parts[1] if len(parts) > 1 else ""
                lvl_and_msg = rest.split("] ", 1)
                lvl = lvl_and_msg[0]
                msg = lvl_and_msg[1] if len(lvl_and_msg) > 1 else ""
                self._append_line(time_str, lvl, msg)

    def clear_logs(self):
        logger.clear()
        try:
            tk_text = self.text_box._textbox
            tk_text.configure(state="normal")
            tk_text.delete("1.0", "end")
            tk_text.configure(state="disabled")
        except Exception:
            pass

    def copy_logs(self):
        try:
            content = self.text_box.get("1.0", "end")
            self.clipboard_clear()
            self.clipboard_append(content)
        except Exception:
            pass
