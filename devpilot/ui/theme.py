"""Humanized, minimal design system and color theme for DevPilot.
Inspired by modern editorial Swiss & Scandinavian minimalist UI (light & dark mode).
"""

from typing import Tuple


class Theme:
    # Canvas & Backgrounds (Light, Dark)
    BG_ROOT: Tuple[str, str] = ("#F2F4F7", "#0E0F12")
    BG_HEADER: Tuple[str, str] = ("#FFFFFF", "#16171C")
    BG_CARD: Tuple[str, str] = ("#FFFFFF", "#1A1B22")
    BG_CARD_ALT: Tuple[str, str] = ("#18181B", "#22232B")  # Signature dark contrast tile
    BG_SURFACE: Tuple[str, str] = ("#F9FAFB", "#20212A")
    BG_INPUT: Tuple[str, str] = ("#FFFFFF", "#1E1F27")
    BG_HOVER: Tuple[str, str] = ("#E5E7EB", "#2D2E38")

    # Borders & Dividers
    BORDER_SUBTLE: Tuple[str, str] = ("#E5E7EB", "#272832")
    BORDER_FOCUS: Tuple[str, str] = ("#18181B", "#F9FAFB")

    # Typography
    TEXT_PRIMARY: Tuple[str, str] = ("#111827", "#F9FAFB")
    TEXT_SECONDARY: Tuple[str, str] = ("#4B5563", "#D1D5DB")
    TEXT_MUTED: Tuple[str, str] = ("#6B7280", "#9CA3AF")
    TEXT_ON_DARK: Tuple[str, str] = ("#FFFFFF", "#FFFFFF")
    TEXT_ON_LIGHT: Tuple[str, str] = ("#111827", "#111827")

    # Buttons - Primary (High-contrast solid pill)
    BTN_PRIMARY_BG: Tuple[str, str] = ("#18181B", "#F9FAFB")
    BTN_PRIMARY_TEXT: Tuple[str, str] = ("#FFFFFF", "#111827")
    BTN_PRIMARY_HOVER: Tuple[str, str] = ("#27272A", "#E5E7EB")

    # Buttons - Secondary (Clean neutral surface)
    BTN_SECONDARY_BG: Tuple[str, str] = ("#F3F4F6", "#252630")
    BTN_SECONDARY_TEXT: Tuple[str, str] = ("#1F2937", "#E5E7EB")
    BTN_SECONDARY_HOVER: Tuple[str, str] = ("#E5E7EB", "#333442")

    # Buttons - Danger / Stop
    BTN_DANGER_BG: Tuple[str, str] = ("#EF4444", "#DC2626")
    BTN_DANGER_TEXT: Tuple[str, str] = ("#FFFFFF", "#FFFFFF")
    BTN_DANGER_HOVER: Tuple[str, str] = ("#DC2626", "#B91C1C")

    # Status Badges
    STATUS_READY: Tuple[str, str] = ("#F3F4F6", "#252630")
    STATUS_READY_TEXT: Tuple[str, str] = ("#4B5563", "#9CA3AF")

    STATUS_RUNNING: Tuple[str, str] = ("#FEF3C7", "#78350F")
    STATUS_RUNNING_TEXT: Tuple[str, str] = ("#92400E", "#FCD34D")

    STATUS_SUCCESS: Tuple[str, str] = ("#ECFDF5", "#064E3B")
    STATUS_SUCCESS_TEXT: Tuple[str, str] = ("#065F46", "#6EE7B7")

    STATUS_FAILED: Tuple[str, str] = ("#FEF2F2", "#7F1D1D")
    STATUS_FAILED_TEXT: Tuple[str, str] = ("#991B1B", "#FCA5A5")

    STATUS_SKIPPED: Tuple[str, str] = ("#EFF6FF", "#1E3A8A")
    STATUS_SKIPPED_TEXT: Tuple[str, str] = ("#1E40AF", "#93C5FD")

    # Project Type Badges (Subtle modern neutral tinting)
    BADGE_PYTHON: Tuple[str, str] = ("#EEF2FF", "#2E365A")
    BADGE_PYTHON_TEXT: Tuple[str, str] = ("#3730A3", "#C7D2FE")

    BADGE_NODE: Tuple[str, str] = ("#ECFDF5", "#1C3E2F")
    BADGE_NODE_TEXT: Tuple[str, str] = ("#065F46", "#A7F3D0")

    BADGE_FLUTTER: Tuple[str, str] = ("#F0FDF4", "#1E3B30")
    BADGE_FLUTTER_TEXT: Tuple[str, str] = ("#166534", "#BBF7D0")

    BADGE_GIT: Tuple[str, str] = ("#FFF1F2", "#4C1D24")
    BADGE_GIT_TEXT: Tuple[str, str] = ("#9F1239", "#FECDD3")

    BADGE_OTHER: Tuple[str, str] = ("#F3F4F6", "#282933")
    BADGE_OTHER_TEXT: Tuple[str, str] = ("#4B5563", "#D1D5DB")

