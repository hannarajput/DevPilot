"""Comprehensive End-to-End workflow test for DevPilot."""

import unittest
import tempfile
import shutil
import time
from pathlib import Path

from unittest.mock import patch, MagicMock
from devpilot.core.storage import StorageManager
from devpilot.core.models import (
    ProjectType,
    ProfileType,
    TaskType,
    TaskStatus,
)
from devpilot.core.detector import (
    detect_project_type,
    generate_default_project_config,
    check_project_health,
)
from devpilot.core.orchestrator import WorkflowOrchestrator


class TestE2EWorkflow(unittest.TestCase):
    def setUp(self):
        self.base_dir = tempfile.mkdtemp(prefix="devpilot_e2e_")
        self.storage = StorageManager(config_dir=Path(self.base_dir) / "config")
        self.orchestrator = WorkflowOrchestrator()

        # Create demo projects
        self.py_dir = Path(self.base_dir) / "python_api"
        self.py_dir.mkdir()
        (self.py_dir / "pyproject.toml").write_text("[project]\nname = 'py-api'\nversion = '0.1.0'")
        (self.py_dir / "main.py").write_text("print('Hello from Python API')")

        self.node_dir = Path(self.base_dir) / "node_app"
        self.node_dir.mkdir()
        (self.node_dir / "package.json").write_text('{"name": "node-app", "version": "1.0.0"}')

        self.flutter_dir = Path(self.base_dir) / "flutter_app"
        self.flutter_dir.mkdir()
        (self.flutter_dir / "pubspec.yaml").write_text("name: flutter_app\ndescription: Demo")
        (self.flutter_dir / "lib").mkdir()
        (self.flutter_dir / "lib" / "main.dart").write_text("void main() {}")

    def tearDown(self):
        shutil.rmtree(self.base_dir, ignore_errors=True)

    def test_e2e_project_detection_and_creation(self):
        # 1. Sniff projects
        py_type, _ = detect_project_type(str(self.py_dir))
        self.assertEqual(py_type, ProjectType.PYTHON)

        node_type, _ = detect_project_type(str(self.node_dir))
        self.assertEqual(node_type, ProjectType.NODEJS)

        fl_type, _ = detect_project_type(str(self.flutter_dir))
        self.assertEqual(fl_type, ProjectType.FLUTTER)

        # 2. Auto-generate configurations
        py_proj = generate_default_project_config(str(self.py_dir), "Python API")
        node_proj = generate_default_project_config(str(self.node_dir), "Node App")
        fl_proj = generate_default_project_config(str(self.flutter_dir), "Flutter App")

        self.storage.save_projects([py_proj, node_proj, fl_proj])

        loaded = self.storage.load_projects()
        self.assertEqual(len(loaded), 3)

        # 3. Pre-flight health checks
        report_py = check_project_health(py_proj)
        self.assertTrue(report_py["passed"])

        report_node = check_project_health(node_proj)
        self.assertTrue(report_node["passed"])

        report_fl = check_project_health(fl_proj)
        self.assertTrue(report_fl["passed"])

    @patch("devpilot.core.orchestrator.launch_antigravity_workspace")
    def test_e2e_launch_and_resume_session(self, mock_launch_ag):
        mock_proc = MagicMock()
        mock_proc.pid = 99999
        mock_launch_ag.return_value = mock_proc

        # Build a safe project for live execution test
        proj = generate_default_project_config(str(self.py_dir), "Python API")
        
        # Replace Antigravity and Terminal with mockable safe commands for headless runner verification
        for t in proj.tasks:
            if t.task_type == TaskType.TERMINAL:
                # Use a safe command task so it finishes synchronously in the test
                t.task_type = TaskType.COMMAND
                t.target = "echo Terminal Ready"
                t.approved = True

        self.storage.save_or_update_project(proj)

        completed_tasks = []
        workflow_done = []

        self.orchestrator.on_task_update = lambda tid, st, msg, res: (
            completed_tasks.append(tid) if st == TaskStatus.SUCCESS else None
        )
        self.orchestrator.on_workflow_finished = lambda pid, succ, sum_str: workflow_done.append((pid, succ))

        # Launch workflow
        t = self.orchestrator.launch_project_async(proj, ProfileType.DEV.value, is_resume=False)
        t.join(timeout=10)

        self.assertTrue(len(workflow_done) > 0)
        self.assertTrue(workflow_done[0][1])  # success == True

        # Verify session saving
        session = self.storage.load_session()
        session.last_project_id = proj.id
        session.last_project_name = proj.name
        session.last_profile = ProfileType.DEV.value
        self.storage.save_session(session)

        # Test resume
        resumed_session = self.storage.load_session()
        self.assertEqual(resumed_session.last_project_id, proj.id)
        self.assertEqual(resumed_session.last_profile, ProfileType.DEV.value)


if __name__ == "__main__":
    unittest.main()
