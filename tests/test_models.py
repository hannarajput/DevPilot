"""Unit tests for DevPilot core data models."""

import unittest
from devpilot.core.models import (
    TaskConfig,
    TaskType,
    TaskStatus,
    ProfileConfig,
    ProfileType,
    AntigravityConfig,
    ProjectConfig,
    ProjectType,
    SessionHistory,
    AppSettings,
)


class TestModels(unittest.TestCase):
    def test_task_config_serialization(self):
        task = TaskConfig(
            id="t1",
            name="Run Dev Server",
            task_type=TaskType.COMMAND,
            target="npm run dev",
            working_dir="C:/app",
            is_one_time=False,
            approved=True
        )
        data = task.to_dict()
        self.assertEqual(data["id"], "t1")
        self.assertEqual(data["task_type"], "command")
        self.assertEqual(data["target"], "npm run dev")

        reconstructed = TaskConfig.from_dict(data)
        self.assertEqual(reconstructed.id, "t1")
        self.assertEqual(reconstructed.task_type, TaskType.COMMAND)
        self.assertTrue(reconstructed.approved)

    def test_project_config_serialization(self):
        ag = AntigravityConfig(
            executable_path="C:/antigravity/antigravity.exe",
            reuse_window=True,
            initial_files=["README.md"]
        )
        task = TaskConfig(id="t1", name="Task 1", task_type=TaskType.ANTIGRAVITY)
        prof = ProfileConfig(name="Dev", enabled_task_ids=["t1"])

        proj = ProjectConfig(
            id="p1",
            name="My Test App",
            root_path="C:/projects/app",
            project_type=ProjectType.PYTHON,
            antigravity=ag,
            tasks=[task],
            profiles={"Dev": prof},
            active_profile="Dev"
        )

        d = proj.to_dict()
        self.assertEqual(d["name"], "My Test App")
        self.assertEqual(d["project_type"], "python")
        self.assertEqual(len(d["tasks"]), 1)
        self.assertEqual(d["antigravity"]["initial_files"], ["README.md"])

        reloaded = ProjectConfig.from_dict(d)
        self.assertEqual(reloaded.id, "p1")
        self.assertEqual(reloaded.project_type, ProjectType.PYTHON)
        self.assertEqual(reloaded.antigravity.reuse_window, True)
        self.assertEqual(len(reloaded.tasks), 1)
        self.assertEqual(reloaded.tasks[0].id, "t1")

    def test_session_history(self):
        sess = SessionHistory(
            last_project_id="p1",
            last_project_name="Test Project",
            last_profile="Full Workspace",
            completed_task_ids=["t1", "t2"]
        )
        d = sess.to_dict()
        reloaded = SessionHistory.from_dict(d)
        self.assertEqual(reloaded.last_project_id, "p1")
        self.assertEqual(reloaded.completed_task_ids, ["t1", "t2"])

    def test_app_settings(self):
        settings = AppSettings(
            default_terminal="powershell",
            autostart_on_windows_login=True,
            redact_secrets=True
        )
        d = settings.to_dict()
        reloaded = AppSettings.from_dict(d)
        self.assertEqual(reloaded.default_terminal, "powershell")
        self.assertTrue(reloaded.autostart_on_windows_login)


if __name__ == "__main__":
    unittest.main()
