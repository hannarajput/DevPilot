"""Acceptance test suite for DevPilot Multi-Resource Project Workspace Manager.

Validates all 9 acceptance criteria required by the specification:
1. Add a new project.
2. Attach an IDE, ChatGPT link, GitHub link, and two custom website links.
3. Save and restart DevPilot (reload from storage).
4. Confirm all resources are still saved.
5. Click Launch Project.
6. Confirm the IDE opens the correct project folder.
7. Confirm all four URLs open in browser tabs.
8. Disable one resource and verify it is skipped during the next launch.
9. Edit and delete resources successfully.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from devpilot.core.models import (
    ProjectConfig,
    ProjectType,
    ResourceType,
    ResourceConfig,
    IDEPreference,
    TaskStatus,
)
from devpilot.core.storage import StorageManager
from devpilot.core.orchestrator import WorkflowOrchestrator
from devpilot.core.resource_launcher import (
    infer_resource_type,
    get_resource_icon,
    validate_resource_target,
    launch_single_resource,
    DANGEROUS_SCHEMES,
)


class TestMultiResourceWorkspaceAcceptance(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.storage = StorageManager(self.temp_dir)
        self.project_path_obj = self.temp_dir / "BuildStory"
        self.project_path_obj.mkdir(parents=True, exist_ok=True)
        self.project_dir = str(self.project_path_obj)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_criterion_1_to_4_add_attach_save_restart_confirm(self):
        """
        Criteria 1, 2, 3, 4:
        - Add a new project
        - Attach IDE, ChatGPT link, GitHub link, and two custom website links
        - Save and restart DevPilot (reload from storage)
        - Confirm all resources are still saved
        """
        # Criterion 1: Add a new project
        proj = ProjectConfig(
            id="proj-buildstory",
            name="BuildStory",
            root_path=self.project_dir,
            project_type=ProjectType.PYTHON,
            description="BuildStory SaaS Workspace"
        )
        self.assertEqual(len(proj.resources), 0)

        # Criterion 2: Attach an IDE, ChatGPT link, GitHub link, and two custom website links
        res_ide = ResourceConfig(
            name="Antigravity IDE",
            resource_type=ResourceType.IDE,
            target="C:/Users/hanna/AppData/Local/Programs/Antigravity/antigravity.exe",
            enabled=True
        )
        res_chatgpt = ResourceConfig(
            name="ChatGPT System Architecture",
            resource_type=ResourceType.AI_CHAT,
            target="https://chatgpt.com/c/6721abcd-1234-5678-90ab-cdef12345678",
            enabled=True
        )
        res_github = ResourceConfig(
            name="GitHub Repository",
            resource_type=ResourceType.WEBSITE,
            target="https://github.com/org/buildstory-core",
            enabled=True
        )
        res_docs = ResourceConfig(
            name="Documentation Portal",
            resource_type=ResourceType.CUSTOM_URL,
            target="https://docs.buildstory.dev",
            enabled=True
        )
        res_live = ResourceConfig(
            name="Live Staging Web App",
            resource_type=ResourceType.CUSTOM_URL,
            target="https://staging.buildstory.dev",
            enabled=True
        )

        proj.add_resource(res_ide)
        proj.add_resource(res_chatgpt)
        proj.add_resource(res_github)
        proj.add_resource(res_docs)
        proj.add_resource(res_live)

        self.assertEqual(len(proj.resources), 5)

        # Criterion 3: Save and restart DevPilot (simulate restart by re-initializing storage)
        self.storage.save_or_update_project(proj)

        # Re-initialize StorageManager from disk storage
        restarted_storage = StorageManager(self.temp_dir)
        loaded_projects = restarted_storage.load_projects()

        # Criterion 4: Confirm all resources are still saved
        self.assertEqual(len(loaded_projects), 1)
        loaded_proj = loaded_projects[0]
        self.assertEqual(loaded_proj.name, "BuildStory")
        self.assertEqual(len(loaded_proj.resources), 5)

        # Check resource details
        self.assertEqual(loaded_proj.resources[0].name, "Antigravity IDE")
        self.assertEqual(loaded_proj.resources[0].resource_type, ResourceType.IDE)
        self.assertEqual(loaded_proj.resources[1].name, "ChatGPT System Architecture")
        self.assertEqual(loaded_proj.resources[1].resource_type, ResourceType.AI_CHAT)
        self.assertEqual(loaded_proj.resources[2].name, "GitHub Repository")
        self.assertEqual(loaded_proj.resources[2].resource_type, ResourceType.WEBSITE)
        self.assertEqual(loaded_proj.resources[3].name, "Documentation Portal")
        self.assertEqual(loaded_proj.resources[3].resource_type, ResourceType.CUSTOM_URL)
        self.assertEqual(loaded_proj.resources[4].name, "Live Staging Web App")
        self.assertEqual(loaded_proj.resources[4].resource_type, ResourceType.CUSTOM_URL)

    @patch("devpilot.core.resource_launcher.launch_antigravity_workspace")
    @patch("webbrowser.open_new_tab")
    def test_criterion_5_to_7_launch_project_opens_ide_and_browser_tabs(
        self,
        mock_open_tab,
        mock_launch_ag
    ):
        """
        Criteria 5, 6, 7:
        - Click Launch Project
        - Confirm the IDE opens the correct project folder
        - Confirm all four URLs open in browser tabs
        """
        mock_open_tab.return_value = True
        mock_proc = MagicMock()
        mock_proc.pid = 9999
        mock_launch_ag.return_value = mock_proc

        fake_ag_exe = self.temp_dir / "antigravity.exe"
        fake_ag_exe.write_text("dummy")

        proj = ProjectConfig(
            id="proj-launch",
            name="BuildStory",
            root_path=str(self.project_dir),
            project_type=ProjectType.PYTHON
        )
        proj.ide_preference = IDEPreference(
            ide_name="Antigravity IDE",
            executable_path=str(fake_ag_exe),
            remembered=True
        )

        # Attach 1 IDE resource and 4 web URLs
        res_ide = ResourceConfig(
            name="Antigravity",
            resource_type=ResourceType.IDE,
            target=str(fake_ag_exe),
            enabled=True
        )
        res_chat = ResourceConfig(
            name="ChatGPT",
            resource_type=ResourceType.AI_CHAT,
            target="https://chatgpt.com/c/test-chat-123",
            enabled=True
        )
        res_git = ResourceConfig(
            name="GitHub",
            resource_type=ResourceType.WEBSITE,
            target="https://github.com/user/buildstory",
            enabled=True
        )
        res_site1 = ResourceConfig(
            name="Docs",
            resource_type=ResourceType.CUSTOM_URL,
            target="https://docs.buildstory.dev",
            enabled=True
        )
        res_site2 = ResourceConfig(
            name="Live Website",
            resource_type=ResourceType.CUSTOM_URL,
            target="https://buildstory.dev",
            enabled=True
        )
        proj.resources = [res_ide, res_chat, res_git, res_site1, res_site2]

        orchestrator = WorkflowOrchestrator()
        notifications = []
        orchestrator.on_task_update = lambda tid, status, msg, res: notifications.append((tid, status, msg))

        # Launch synchronously for verification
        orchestrator._run_workflow(proj)

        # Criterion 6: Confirm IDE opens the correct project folder
        mock_launch_ag.assert_called()
        call_args = mock_launch_ag.call_args[0]
        self.assertEqual(os.path.normpath(call_args[0]), os.path.normpath(self.project_dir))

        # Criterion 7: Confirm all four URLs open in browser tabs
        self.assertEqual(mock_open_tab.call_count, 4)
        opened_urls = [call[0][0] for call in mock_open_tab.call_args_list]
        self.assertIn("https://chatgpt.com/c/test-chat-123", opened_urls)
        self.assertIn("https://github.com/user/buildstory", opened_urls)
        self.assertIn("https://docs.buildstory.dev", opened_urls)
        self.assertIn("https://buildstory.dev", opened_urls)

    @patch("devpilot.core.resource_launcher.launch_antigravity_workspace")
    @patch("webbrowser.open_new_tab")
    def test_criterion_8_disable_resource_and_verify_skipped(
        self,
        mock_open_tab,
        mock_launch_ag
    ):
        """
        Criterion 8:
        - Disable one resource and verify it is skipped during the next launch
        """
        mock_open_tab.return_value = True
        mock_proc = MagicMock()
        mock_proc.pid = 9999
        mock_launch_ag.return_value = mock_proc

        proj = ProjectConfig(
            id="proj-skip",
            name="BuildStory",
            root_path=self.project_dir,
            project_type=ProjectType.PYTHON
        )

        res_chat = ResourceConfig(
            name="ChatGPT",
            resource_type=ResourceType.AI_CHAT,
            target="https://chatgpt.com/c/disabled-chat",
            enabled=False  # DISABLED!
        )
        res_git = ResourceConfig(
            name="GitHub",
            resource_type=ResourceType.WEBSITE,
            target="https://github.com/user/buildstory",
            enabled=True
        )
        res_site = ResourceConfig(
            name="Docs",
            resource_type=ResourceType.CUSTOM_URL,
            target="https://docs.buildstory.dev",
            enabled=True
        )
        proj.resources = [res_chat, res_git, res_site]

        orchestrator = WorkflowOrchestrator()
        orchestrator._run_workflow(proj)

        # Verify disabled resource was skipped
        opened_urls = [call[0][0] for call in mock_open_tab.call_args_list]
        self.assertNotIn("https://chatgpt.com/c/disabled-chat", opened_urls)
        self.assertIn("https://github.com/user/buildstory", opened_urls)
        self.assertIn("https://docs.buildstory.dev", opened_urls)
        self.assertEqual(len(opened_urls), 2)

    def test_criterion_9_edit_and_delete_resources_successfully(self):
        """
        Criterion 9:
        - Edit and delete resources successfully
        """
        proj = ProjectConfig(
            id="proj-crud",
            name="BuildStory",
            root_path=self.project_dir,
            project_type=ProjectType.PYTHON
        )
        r1 = ResourceConfig(name="Old Name", resource_type=ResourceType.WEBSITE, target="https://old.com")
        r2 = ResourceConfig(name="To Delete", resource_type=ResourceType.WEBSITE, target="https://delete.me")
        proj.add_resource(r1)
        proj.add_resource(r2)
        self.storage.save_or_update_project(proj)

        # Edit r1
        target_r = proj.get_resource(r1.id)
        self.assertIsNotNone(target_r)
        target_r.name = "New Updated Name"
        target_r.target = "https://new-updated.com"

        # Delete r2
        proj.remove_resource(r2.id)

        # Save and reload
        self.storage.save_or_update_project(proj)
        reloaded = self.storage.get_project(proj.id)

        self.assertEqual(len(reloaded.resources), 1)
        self.assertEqual(reloaded.resources[0].id, r1.id)
        self.assertEqual(reloaded.resources[0].name, "New Updated Name")
        self.assertEqual(reloaded.resources[0].target, "https://new-updated.com")
        self.assertIsNone(reloaded.get_resource(r2.id))

    def test_error_isolation_between_resources(self):
        """Verify that a failure in one resource does not prevent others from opening."""
        with patch("webbrowser.open_new_tab") as mock_open:
            mock_open.return_value = True

            proj = ProjectConfig(name="TestIsolation", root_path=self.project_dir)
            r_bad = ResourceConfig(name="Bad File", resource_type=ResourceType.LOCAL_FILE, target="Z:/nonexistent/file.txt")
            r_good = ResourceConfig(name="Good Site", resource_type=ResourceType.WEBSITE, target="https://good.com")
            proj.resources = [r_bad, r_good]

            orchestrator = WorkflowOrchestrator()
            results = {}
            orchestrator.on_task_update = lambda tid, status, msg, r: results.update({tid: status})

            orchestrator._run_workflow(proj)

            self.assertEqual(results.get(f"res_{r_bad.id}"), TaskStatus.FAILED)
            self.assertEqual(results.get(f"res_{r_good.id}"), TaskStatus.SUCCESS)
            mock_open.assert_called_with("https://good.com")

    def test_security_blocks_dangerous_schemes(self):
        """Verify that hazardous protocol schemes like javascript: are rejected."""
        for scheme in DANGEROUS_SCHEMES:
            valid, _, err = validate_resource_target(f"{scheme}:alert(1)", ResourceType.WEBSITE)
            self.assertFalse(valid, f"Scheme {scheme} should have been blocked!")
            self.assertIn("blocked for security", err.lower())


if __name__ == "__main__":
    unittest.main()
