"""Unit tests for project detection, tool discovery, and health checks."""

import unittest
import tempfile
import shutil
from pathlib import Path

from devpilot.core.models import ProjectType, ProjectConfig, TaskType
from devpilot.core.detector import (
    detect_project_type,
    detect_installed_tools,
    check_project_health,
    generate_default_project_config,
)


class TestDetector(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="devpilot_test_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_detect_python_project(self):
        pyproject = Path(self.test_dir) / "pyproject.toml"
        pyproject.write_text("[project]\nname = 'test'")

        p_type, ind = detect_project_type(self.test_dir)
        self.assertEqual(p_type, ProjectType.PYTHON)
        self.assertIn("pyproject.toml", ind)

    def test_detect_nodejs_project(self):
        pkg = Path(self.test_dir) / "package.json"
        pkg.write_text('{"name": "test-node"}')

        p_type, ind = detect_project_type(self.test_dir)
        self.assertEqual(p_type, ProjectType.NODEJS)
        self.assertIn("package.json", ind)

    def test_detect_flutter_project(self):
        pubspec = Path(self.test_dir) / "pubspec.yaml"
        pubspec.write_text("name: test_flutter\ndescription: A Flutter project.")

        p_type, ind = detect_project_type(self.test_dir)
        self.assertEqual(p_type, ProjectType.FLUTTER)
        self.assertIn("pubspec.yaml", ind)

    def test_detect_git_project(self):
        git_dir = Path(self.test_dir) / ".git"
        git_dir.mkdir()

        p_type, ind = detect_project_type(self.test_dir)
        self.assertEqual(p_type, ProjectType.GIT)
        self.assertIn(".git", ind)

    def test_generate_default_config_for_python(self):
        # Create a Python repo with pyproject.toml
        Path(self.test_dir, "pyproject.toml").write_text("[project]\nname = 'demo'")
        
        config = generate_default_project_config(self.test_dir, "Demo Python")
        self.assertEqual(config.project_type, ProjectType.PYTHON)
        self.assertEqual(config.name, "Demo Python")
        self.assertTrue(len(config.tasks) >= 3)
        
        # Verify Antigravity task is first
        self.assertEqual(config.tasks[0].task_type, TaskType.ANTIGRAVITY)
        # Verify profiles exist
        self.assertIn("Basic Workspace", config.profiles)
        self.assertIn("Development", config.profiles)
        self.assertIn("Full Workspace", config.profiles)

    def test_check_project_health(self):
        Path(self.test_dir, "requirements.txt").write_text("requests==2.31.0")
        config = generate_default_project_config(self.test_dir, "Health Test")
        
        report = check_project_health(config)
        self.assertEqual(report["project_name"], "Health Test")
        self.assertTrue(report["root_exists"])
        self.assertTrue(len(report["checks"]) >= 2)


if __name__ == "__main__":
    unittest.main()
