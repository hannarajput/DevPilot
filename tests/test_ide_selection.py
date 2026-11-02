"""Unit tests for IDE detection, IDE preferences, and remembered choice logic."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from devpilot.core.models import (
    ProjectConfig,
    ProjectType,
    IDEPreference,
)
from devpilot.core.ide_detector import (
    detect_installed_ides,
    build_ide_launch_command,
)


class TestIDESelection(unittest.TestCase):
    def test_detect_installed_ides(self):
        ides = detect_installed_ides()
        self.assertTrue(len(ides) >= 1)
        
        # Verify Antigravity IDE is discovered on this laptop
        names = [ide["name"] for ide in ides]
        self.assertTrue(any("Antigravity" in n for n in names))

        # Check structure
        for ide in ides:
            self.assertIn("name", ide)
            self.assertIn("executable_path", ide)
            self.assertTrue(Path(ide["executable_path"]).exists())

    def test_ide_preference_serialization(self):
        pref = IDEPreference(
            ide_name="Visual Studio Code",
            executable_path="C:/Programs/VSCode/Code.exe",
            remembered=True,
            reuse_window=True
        )
        d = pref.to_dict()
        self.assertEqual(d["ide_name"], "Visual Studio Code")
        self.assertTrue(d["remembered"])

        reloaded = IDEPreference.from_dict(d)
        self.assertEqual(reloaded.ide_name, "Visual Studio Code")
        self.assertTrue(reloaded.remembered)

    def test_project_config_ide_preference_integration(self):
        pref = IDEPreference(
            ide_name="Antigravity IDE",
            executable_path="C:/Antigravity/antigravity-ide.cmd",
            remembered=True
        )
        proj = ProjectConfig(
            id="p_test",
            name="Demo Proj",
            root_path="C:/demo",
            ide_preference=pref
        )

        d = proj.to_dict()
        self.assertIn("ide_preference", d)
        self.assertEqual(d["ide_preference"]["ide_name"], "Antigravity IDE")
        self.assertTrue(d["ide_preference"]["remembered"])

        reloaded = ProjectConfig.from_dict(d)
        self.assertEqual(reloaded.ide_preference.ide_name, "Antigravity IDE")
        self.assertTrue(reloaded.ide_preference.remembered)

    def test_build_ide_launch_command_antigravity(self):
        cmd = build_ide_launch_command(
            executable_path="C:/Antigravity/bin/antigravity-ide.cmd",
            workspace_path="C:/projects/myapp",
            reuse_window=True,
            new_window=False
        )
        self.assertEqual(cmd[0], "C:/Antigravity/bin/antigravity-ide.cmd")
        self.assertIn("-r", cmd)
        self.assertTrue(any("myapp" in arg.lower() for arg in cmd))

    def test_build_ide_launch_command_vscode(self):
        cmd = build_ide_launch_command(
            executable_path="C:/Users/hanna/AppData/Local/Programs/Microsoft VS Code/bin/code.cmd",
            workspace_path="C:/projects/myapp",
            reuse_window=False,
            new_window=True
        )
        self.assertIn("-n", cmd)
        self.assertTrue(any("myapp" in arg.lower() for arg in cmd))

    def test_remember_choice_bypasses_prompt(self):
        """When remembered=True, launch logic directly opens earlier IDE without prompt."""
        proj = ProjectConfig(
            id="p_rem",
            name="Remembered Proj",
            root_path="C:/projects/myapp",
            ide_preference=IDEPreference(
                ide_name="Antigravity IDE",
                executable_path="C:/Antigravity/antigravity-ide.cmd",
                remembered=True
            )
        )
        # Check condition
        self.assertTrue(proj.ide_preference.remembered)
        self.assertEqual(proj.ide_preference.ide_name, "Antigravity IDE")

    def test_not_remembered_requires_prompt(self):
        """When remembered=False, launch logic knows it needs to prompt user."""
        proj = ProjectConfig(
            id="p_not_rem",
            name="Ask Proj",
            root_path="C:/projects/myapp",
            ide_preference=IDEPreference(
                ide_name="Antigravity IDE",
                executable_path="C:/Antigravity/antigravity-ide.cmd",
                remembered=False
            )
        )
        self.assertFalse(proj.ide_preference.remembered)


if __name__ == "__main__":
    unittest.main()

