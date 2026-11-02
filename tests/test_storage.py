"""Unit tests for storage persistence and atomic writing."""

import unittest
import tempfile
import shutil
from pathlib import Path

from devpilot.core.storage import StorageManager
from devpilot.core.models import (
    ProjectConfig,
    AppSettings,
    SessionHistory,
    ProjectType,
)


class TestStorage(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="devpilot_store_")
        self.storage = StorageManager(config_dir=Path(self.test_dir))

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_save_and_load_projects(self):
        p1 = ProjectConfig(id="p1", name="Alpha", root_path="C:/alpha", project_type=ProjectType.PYTHON)
        p2 = ProjectConfig(id="p2", name="Beta", root_path="C:/beta", project_type=ProjectType.NODEJS)

        self.storage.save_projects([p1, p2])

        loaded = self.storage.load_projects()
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0].name, "Alpha")
        self.assertEqual(loaded[1].name, "Beta")

    def test_save_or_update_project(self):
        p1 = ProjectConfig(id="p1", name="Alpha", root_path="C:/alpha")
        self.storage.save_or_update_project(p1)

        # Update
        p1.name = "Alpha Updated"
        self.storage.save_or_update_project(p1)

        loaded = self.storage.load_projects()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].name, "Alpha Updated")

    def test_delete_project(self):
        p1 = ProjectConfig(id="p1", name="Alpha", root_path="C:/alpha")
        self.storage.save_or_update_project(p1)
        self.assertEqual(len(self.storage.load_projects()), 1)

        deleted = self.storage.delete_project("p1")
        self.assertTrue(deleted)
        self.assertEqual(len(self.storage.load_projects()), 0)

    def test_save_and_load_settings(self):
        s = AppSettings(default_terminal="cmd", autostart_on_windows_login=True)
        self.storage.save_settings(s)

        loaded = self.storage.load_settings()
        self.assertEqual(loaded.default_terminal, "cmd")
        self.assertTrue(loaded.autostart_on_windows_login)

    def test_save_and_load_session(self):
        sess = SessionHistory(last_project_id="p10", last_project_name="My Session")
        self.storage.save_session(sess)

        loaded = self.storage.load_session()
        self.assertEqual(loaded.last_project_id, "p10")
        self.assertEqual(loaded.last_project_name, "My Session")


if __name__ == "__main__":
    unittest.main()
