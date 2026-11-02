"""Modal dialog for selecting an installed IDE on the laptop with 'Remember' preference."""

import os
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox
from typing import Callable, Optional, List, Dict, Any

from devpilot.core.models import ProjectConfig, IDEPreference
from devpilot.core.ide_detector import detect_installed_ides
from devpilot.ui.theme import Theme


class IDESelectionModal(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        project: ProjectConfig,
        on_confirm: Callable[[IDEPreference], None],
        on_cancel: Optional[Callable[[], None]] = None,
        action_button_text: str = "Confirm & Launch"
    ):
        super().__init__(master)
        self.project = project
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.action_button_text = action_button_text

        self.title(f"Select IDE — {project.name}")
        self.geometry("620x550")
        self.minsize(580, 480)
        self.transient(master)
        self.grab_set()

        self.available_ides: List[Dict[str, Any]] = detect_installed_ides()
        self.selected_ide_var = ctk.StringVar()
        self.remember_var = ctk.BooleanVar(value=True)
        self.custom_path_var = ctk.StringVar(value="")

        self._init_selection()
        self._build_ui()

    def _init_selection(self):
        current_exe = self.project.ide_preference.executable_path or self.project.antigravity.executable_path
        if current_exe:
            for ide in self.available_ides:
                if ide["executable_path"].lower() == current_exe.lower():
                    self.selected_ide_var.set(ide["executable_path"])
                    return

        for ide in self.available_ides:
            if ide.get("is_recommended"):
                self.selected_ide_var.set(ide["executable_path"])
                return

        if self.available_ides:
            self.selected_ide_var.set(self.available_ides[0]["executable_path"])

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(18, 8))

        ctk.CTkLabel(
            header,
            text=f"Choose IDE for: {self.project.name}",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="Select which installed IDE on your laptop to open this project with:",
            font=ctk.CTkFont(size=12),
            text_color=Theme.TEXT_MUTED
        ).pack(anchor="w", pady=(2, 0))

        # IDE List scrollable frame
        list_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=Theme.BG_SURFACE,
            corner_radius=12,
            border_width=1,
            border_color=Theme.BORDER_SUBTLE
        )
        list_frame.pack(fill="both", expand=True, padx=20, pady=8)

        if not self.available_ides:
            ctk.CTkLabel(
                list_frame,
                text="No common IDEs were auto-detected in standard locations.\nPlease browse for your IDE executable below.",
                text_color=Theme.STATUS_RUNNING_TEXT
            ).pack(pady=20)

        for ide in self.available_ides:
            self._build_ide_item(list_frame, ide)

        # Custom IDE option
        self._build_custom_item(list_frame)

        # Bottom Frame: Remember option + Action buttons
        bottom = ctk.CTkFrame(
            self,
            fg_color=Theme.BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=Theme.BORDER_SUBTLE
        )
        bottom.pack(fill="x", padx=20, pady=(6, 16))

        # Remember Checkbox with explanation
        remember_box = ctk.CTkFrame(bottom, fg_color="transparent")
        remember_box.pack(fill="x", padx=16, pady=(12, 6))

        self.remember_chk = ctk.CTkCheckBox(
            remember_box,
            text="Remember this choice for this project",
            variable=self.remember_var,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=Theme.TEXT_PRIMARY,
            fg_color=Theme.BTN_PRIMARY_BG,
            hover_color=Theme.BORDER_FOCUS
        )
        self.remember_chk.pack(anchor="w")

        ctk.CTkLabel(
            remember_box,
            text="Next time you launch this project, DevPilot will not ask again and will open directly in this IDE.",
            font=ctk.CTkFont(size=11),
            text_color=Theme.TEXT_MUTED
        ).pack(anchor="w", padx=(26, 0), pady=(2, 0))

        # Buttons
        btn_box = ctk.CTkFrame(bottom, fg_color="transparent")
        btn_box.pack(fill="x", padx=16, pady=(8, 14))

        ctk.CTkButton(
            btn_box,
            text="Cancel",
            fg_color=Theme.BTN_SECONDARY_BG,
            hover_color=Theme.BTN_SECONDARY_HOVER,
            text_color=Theme.BTN_SECONDARY_TEXT,
            corner_radius=8,
            width=80,
            command=self._handle_cancel
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btn_box,
            text=self.action_button_text,
            fg_color=Theme.BTN_PRIMARY_BG,
            hover_color=Theme.BTN_PRIMARY_HOVER,
            text_color=Theme.BTN_PRIMARY_TEXT,
            font=ctk.CTkFont(weight="bold"),
            corner_radius=18,
            width=140,
            height=32,
            command=self._handle_confirm
        ).pack(side="right")

    def _build_ide_item(self, parent, ide: Dict[str, Any]):
        card = ctk.CTkFrame(
            parent,
            fg_color=Theme.BG_CARD,
            corner_radius=10,
            border_width=1,
            border_color=Theme.BORDER_SUBTLE
        )
        card.pack(fill="x", pady=4, padx=2)

        radio = ctk.CTkRadioButton(
            card,
            text="",
            value=ide["executable_path"],
            variable=self.selected_ide_var,
            width=24,
            fg_color=Theme.BTN_PRIMARY_BG
        )
        radio.pack(side="left", padx=(12, 4), pady=10)

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, pady=6)

        title_row = ctk.CTkFrame(info, fg_color="transparent")
        title_row.pack(fill="x")

        ctk.CTkLabel(
            title_row,
            text=ide["name"],
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(side="left")

        if ide.get("is_recommended"):
            ctk.CTkLabel(
                title_row,
                text=" RECOMMENDED ",
                font=ctk.CTkFont(size=9, weight="bold"),
                fg_color=Theme.BADGE_PYTHON,
                text_color=Theme.BADGE_PYTHON_TEXT,
                corner_radius=6
            ).pack(side="left", padx=8)

        path_text = ide["executable_path"]
        if len(path_text) > 65:
            path_text = path_text[:28] + "..." + path_text[-34:]

        ctk.CTkLabel(
            info,
            text=f"📁 {path_text}",
            font=ctk.CTkFont(size=10),
            text_color=Theme.TEXT_MUTED
        ).pack(anchor="w", pady=(1, 0))

        card.bind("<Button-1>", lambda e, p=ide["executable_path"]: self.selected_ide_var.set(p))
        info.bind("<Button-1>", lambda e, p=ide["executable_path"]: self.selected_ide_var.set(p))

    def _build_custom_item(self, parent):
        card = ctk.CTkFrame(
            parent,
            fg_color=Theme.BG_CARD,
            corner_radius=10,
            border_width=1,
            border_color=Theme.BORDER_SUBTLE
        )
        card.pack(fill="x", pady=4, padx=2)

        radio = ctk.CTkRadioButton(
            card,
            text="",
            value="__custom__",
            variable=self.selected_ide_var,
            width=24,
            fg_color=Theme.BTN_PRIMARY_BG
        )
        radio.pack(side="left", padx=(12, 4), pady=10)

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, pady=6)

        ctk.CTkLabel(
            info,
            text="Browse Other Custom IDE / Editor...",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor="w")

        input_row = ctk.CTkFrame(info, fg_color="transparent")
        input_row.pack(fill="x", pady=(2, 0))

        self.custom_entry = ctk.CTkEntry(
            input_row,
            textvariable=self.custom_path_var,
            placeholder_text="Path to executable (.exe, .cmd)...",
            font=ctk.CTkFont(size=10),
            fg_color=Theme.BG_INPUT,
            border_color=Theme.BORDER_SUBTLE,
            text_color=Theme.TEXT_PRIMARY,
            height=26,
            corner_radius=6
        )
        self.custom_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            input_row,
            text="Browse",
            width=65,
            height=26,
            fg_color=Theme.BTN_SECONDARY_BG,
            hover_color=Theme.BTN_SECONDARY_HOVER,
            text_color=Theme.BTN_SECONDARY_TEXT,
            corner_radius=6,
            command=self._browse_custom_exe
        ).pack(side="left")

    def _browse_custom_exe(self):
        f = filedialog.askopenfilename(
            title="Select IDE Executable",
            filetypes=[("Executables", "*.exe;*.cmd;*.bat"), ("All Files", "*.*")]
        )
        if f:
            self.custom_path_var.set(f)
            self.selected_ide_var.set("__custom__")

    def _handle_cancel(self):
        if self.on_cancel:
            self.on_cancel()
        self.destroy()

    def _handle_confirm(self):
        chosen_val = self.selected_ide_var.get()
        if not chosen_val:
            messagebox.showwarning("Selection Required", "Please select an IDE to open the project.")
            return

        if chosen_val == "__custom__":
            custom_path = self.custom_path_var.get().strip()
            if not custom_path or not Path(custom_path).exists():
                messagebox.showwarning("Invalid Path", "Please browse and select a valid executable path.")
                return
            ide_path = custom_path
            ide_name = Path(custom_path).stem.capitalize()
        else:
            ide_path = chosen_val
            ide_name = "Selected IDE"
            for ide in self.available_ides:
                if ide["executable_path"] == ide_path:
                    ide_name = ide["name"]
                    break

        remembered = self.remember_var.get()

        pref = IDEPreference(
            ide_name=ide_name,
            executable_path=ide_path,
            remembered=remembered,
            reuse_window=self.project.ide_preference.reuse_window,
            new_window=self.project.ide_preference.new_window
        )

        self.on_confirm(pref)
        self.destroy()
