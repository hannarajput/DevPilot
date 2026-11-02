"""Integration test for DevPilot UI initialization, theme switching, and widget rendering."""

import unittest
import tempfile
import shutil
from pathlib import Path
import customtkinter as ctk

from devpilot.core.storage import StorageManager
from devpilot.core.models import ProjectConfig, ProjectType, AppSettings
from devpilot.ui.app import DevPilotApp


class TestUILaunch(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="devpilot_ui_test_")
        self.storage = StorageManager(config_dir=Path(self.test_dir))

        # Add a couple of sample projects to verify card rendering
        p1 = ProjectConfig(id="proj1", name="Flask API", root_path=self.test_dir, project_type=ProjectType.PYTHON)
        p2 = ProjectConfig(id="proj2", name="Next.js App", root_path=self.test_dir, project_type=ProjectType.NODEJS)
        self.storage.save_projects([p1, p2])

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_app_lifecycle_light_mode(self):
        self.storage.save_settings(AppSettings(theme="light"))
        app = DevPilotApp(storage_manager=self.storage)
        self.assertIsNotNone(app)

        app.update()

        self.assertEqual(len(app.project_cards), 2)
        self.assertIn("proj1", app.project_cards)
        self.assertIn("proj2", app.project_cards)
        self.assertEqual(ctk.get_appearance_mode().lower(), "light")

        # Test toggle to dark mode
        app._toggle_theme()
        self.assertEqual(ctk.get_appearance_mode().lower(), "dark")
        self.assertEqual(app.settings.theme, "dark")

        # Test toggle back to light mode
        app._toggle_theme()
        self.assertEqual(ctk.get_appearance_mode().lower(), "light")
        self.assertEqual(app.settings.theme, "light")

        app.update_idletasks()
        app.destroy()

    def test_app_lifecycle_dark_mode(self):
        self.storage.save_settings(AppSettings(theme="dark"))
        app = DevPilotApp(storage_manager=self.storage)
        app.update()

        self.assertEqual(ctk.get_appearance_mode().lower(), "dark")
        app.update_idletasks()
        app.destroy()


if __name__ == "__main__":
    unittest.main()
