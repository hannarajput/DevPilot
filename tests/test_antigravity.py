"""Unit tests for Antigravity launcher and CLI builder."""

import unittest
import tempfile
import shutil
from pathlib import Path

from devpilot.core.models import AntigravityConfig
from devpilot.core.antigravity import (
    find_antigravity_executable,
    build_antigravity_launch_command,
)


class TestAntigravity(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="devpilot_ag_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_find_antigravity_executable(self):
        # In our inspected Windows environment, Antigravity IDE is installed
        exe = find_antigravity_executable()
        self.assertIsNotNone(exe)
        self.assertTrue("antigravity" in exe.lower())

    def test_build_launch_command_ide_reuse_window(self):
        fake_exe = str(Path(self.test_dir) / "antigravity-ide.cmd")
        Path(fake_exe).write_text("@echo off")

        cfg = AntigravityConfig(
            reuse_window=True,
            new_window=False
        )

        cmd, desc = build_antigravity_launch_command(
            executable_path=fake_exe,
            workspace_path=self.test_dir,
            config=cfg
        )

        self.assertEqual(cmd[0], fake_exe)
        self.assertIn("-r", cmd)
        self.assertIn(str(Path(self.test_dir).resolve()), cmd)

    def test_build_launch_command_ide_new_window_and_profile(self):
        fake_exe = str(Path(self.test_dir) / "antigravity-ide.cmd")
        Path(fake_exe).write_text("@echo off")

        cfg = AntigravityConfig(
            reuse_window=False,
            new_window=True,
            profile_name="PythonDev"
        )

        cmd, desc = build_antigravity_launch_command(
            executable_path=fake_exe,
            workspace_path=self.test_dir,
            config=cfg
        )

        self.assertIn("-n", cmd)
        self.assertIn("--profile", cmd)
        self.assertIn("PythonDev", cmd)

    def test_build_launch_command_with_initial_files(self):
        fake_exe = str(Path(self.test_dir) / "antigravity-ide.cmd")
        Path(fake_exe).write_text("@echo off")

        # Create sample file
        sample_file = Path(self.test_dir) / "README.md"
        sample_file.write_text("# Readme")

        cfg = AntigravityConfig(
            reuse_window=True,
            initial_files=["README.md"]
        )

        cmd, _ = build_antigravity_launch_command(
            executable_path=fake_exe,
            workspace_path=self.test_dir,
            config=cfg
        )

        self.assertIn(str(sample_file), cmd)


if __name__ == "__main__":
    unittest.main()
