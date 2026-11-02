"""Unit tests for Workflow Orchestrator execution, cancellation, and retry."""

import unittest
import tempfile
import shutil
import time
from pathlib import Path

from devpilot.core.models import (
    ProjectConfig,
    TaskConfig,
    TaskType,
    TaskStatus,
    ProfileConfig,
)
from devpilot.core.orchestrator import WorkflowOrchestrator


class TestOrchestrator(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="devpilot_orch_")
        self.orchestrator = WorkflowOrchestrator()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_run_workflow_synchronous_tasks(self):
        updates = []
        finished = []

        self.orchestrator.on_task_update = lambda tid, st, msg, res: updates.append((tid, st))
        self.orchestrator.on_workflow_finished = lambda pid, succ, sum_str: finished.append((succ, sum_str))

        t1 = TaskConfig(
            id="t1",
            name="Check Tool",
            task_type=TaskType.TOOL_CHECK,
            target="python",
            enabled=True,
            order=1
        )
        t2 = TaskConfig(
            id="t2",
            name="Run Safe Echo",
            task_type=TaskType.COMMAND,
            target="echo Hello DevPilot",
            working_dir=self.test_dir,
            enabled=True,
            order=2,
            approved=True
        )

        proj = ProjectConfig(
            id="p1",
            name="Test Proj",
            root_path=self.test_dir,
            tasks=[t1, t2],
            profiles={"Dev": ProfileConfig(name="Dev", enabled_task_ids=["t1", "t2"])},
            active_profile="Dev"
        )

        t = self.orchestrator.launch_project_async(proj, "Dev")
        t.join(timeout=10)

        self.assertFalse(self.orchestrator.is_running)
        self.assertTrue(len(finished) > 0)
        self.assertTrue(finished[0][0])  # overall_success == True

        # Check status transitions
        statuses = [u[1] for u in updates if u[0] == "t2"]
        self.assertIn(TaskStatus.QUEUED, statuses)
        self.assertIn(TaskStatus.RUNNING, statuses)
        self.assertIn(TaskStatus.SUCCESS, statuses)

    def test_skip_one_time_tasks_on_resume(self):
        updates = []
        self.orchestrator.on_task_update = lambda tid, st, msg, res: updates.append((tid, st))

        t_onetime = TaskConfig(
            id="t_setup",
            name="Install Dependencies",
            task_type=TaskType.COMMAND,
            target="echo Installing...",
            is_one_time=True,
            enabled=True,
            order=1,
            approved=True
        )
        t_regular = TaskConfig(
            id="t_reg",
            name="Verify Python",
            task_type=TaskType.TOOL_CHECK,
            target="python",
            is_one_time=False,
            enabled=True,
            order=2
        )

        proj = ProjectConfig(
            id="p1",
            name="Resume Proj",
            root_path=self.test_dir,
            tasks=[t_onetime, t_regular],
            profiles={"Dev": ProfileConfig(name="Dev", enabled_task_ids=["t_setup", "t_reg"])},
            active_profile="Dev"
        )

        # Launch with is_resume=True
        t = self.orchestrator.launch_project_async(proj, "Dev", is_resume=True)
        t.join(timeout=10)

        # Check that t_setup was skipped
        statuses_setup = [u[1] for u in updates if u[0] == "t_setup"]
        self.assertIn(TaskStatus.SKIPPED, statuses_setup)

        # t_reg should succeed
        statuses_reg = [u[1] for u in updates if u[0] == "t_reg"]
        self.assertIn(TaskStatus.SUCCESS, statuses_reg)

    def test_unapproved_command_is_blocked(self):
        updates = []
        self.orchestrator.on_task_update = lambda tid, st, msg, res: updates.append((tid, st))

        t_unapproved = TaskConfig(
            id="t_unapp",
            name="Unapproved Command",
            task_type=TaskType.COMMAND,
            target="npm run something",
            approved=False,
            enabled=True,
            order=1
        )

        proj = ProjectConfig(
            id="p1",
            name="Unapproved Proj",
            root_path=self.test_dir,
            tasks=[t_unapproved],
            profiles={"Dev": ProfileConfig(name="Dev", enabled_task_ids=["t_unapp"])},
            active_profile="Dev"
        )

        t = self.orchestrator.launch_project_async(proj, "Dev")
        t.join(timeout=10)

        statuses = [u[1] for u in updates if u[0] == "t_unapp"]
        self.assertIn(TaskStatus.FAILED, statuses)

    def test_single_task_retry(self):
        updates = []
        self.orchestrator.on_task_update = lambda tid, st, msg, res: updates.append((tid, st))

        task = TaskConfig(
            id="t_retry",
            name="Retryable Task",
            task_type=TaskType.TOOL_CHECK,
            target="python",
            enabled=True
        )

        proj = ProjectConfig(
            id="p1",
            name="Retry Proj",
            root_path=self.test_dir,
            tasks=[task]
        )

        t = self.orchestrator.retry_single_task_async(proj, "t_retry")
        t.join(timeout=5)

        statuses = [u[1] for u in updates if u[0] == "t_retry"]
        self.assertIn(TaskStatus.RUNNING, statuses)
        self.assertIn(TaskStatus.SUCCESS, statuses)


if __name__ == "__main__":
    unittest.main()
