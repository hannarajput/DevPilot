"""Workflow execution engine, task sequencing, cancellation, and retry manager."""

import os
import time
import shutil
import threading
import subprocess
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any

from devpilot.core.models import (
    ProjectConfig,
    TaskConfig,
    TaskType,
    TaskStatus,
    TaskExecutionResult,
    SessionHistory,
    ProfileType,
    ResourceConfig,
)
from devpilot.core.resource_launcher import (
    launch_single_resource,
    get_resource_icon,
    validate_resource_target,
)
from devpilot.core.antigravity import (
    launch_antigravity_workspace,
    is_workspace_open_in_antigravity,
    find_antigravity_executable,
)
from devpilot.core.ide_detector import launch_ide_workspace
from devpilot.core.terminal import (
    launch_terminal_window,
    run_command_capture,
)
from devpilot.core.system import (
    open_browser_url,
    launch_supporting_application,
    safely_terminate_process_tree,
)
from devpilot.core.security import is_safe_startup_command
from devpilot.core.detector import check_git_status, detect_installed_tools
from devpilot.utils.logger import logger


class WorkflowOrchestrator:
    def __init__(self):
        self._cancel_requested = threading.Event()
        self._is_running = False
        self._current_project: Optional[ProjectConfig] = None
        self._active_pids: List[int] = []
        self._lock = threading.Lock()

        # Callbacks
        self.on_task_update: Optional[Callable[[str, TaskStatus, str, Optional[TaskExecutionResult]], None]] = None
        self.on_workflow_finished: Optional[Callable[[str, bool, str], None]] = None

    @property
    def is_running(self) -> bool:
        return self._is_running

    def stop_workflow(self):
        """Request immediate safe cancellation of currently executing DevPilot tasks."""
        if not self._is_running:
            return

        logger.warn("Stop requested by user. Cancelling workflow tasks...")
        self._cancel_requested.set()

        # Safely terminate only PIDs spawned directly by this workflow
        with self._lock:
            for pid in self._active_pids:
                safely_terminate_process_tree(pid)
            self._active_pids.clear()

    def launch_project_async(
        self,
        project: ProjectConfig,
        profile_name: Optional[str] = None,
        is_resume: bool = False
    ) -> threading.Thread:
        """Start project workflow asynchronously in a background thread."""
        thread = threading.Thread(
            target=self._run_workflow,
            args=(project, profile_name, is_resume),
            name=f"Workflow-{project.name}",
            daemon=True
        )
        thread.start()
        return thread

    def _notify_task(self, task_id: str, status: TaskStatus, message: str, result: Optional[TaskExecutionResult] = None):
        if self.on_task_update:
            try:
                self.on_task_update(task_id, status, message, result)
            except Exception as e:
                logger.error(f"Error in on_task_update callback: {e}")

    def _run_workflow(self, project: ProjectConfig, profile_name: Optional[str] = None, is_resume: bool = False):
        self._is_running = True
        self._cancel_requested.clear()
        self._current_project = project
        self._active_pids.clear()

        active_prof_name = profile_name or project.active_profile
        logger.info(f"{'Resuming' if is_resume else 'Launching'} project: '{project.name}' [Profile: {active_prof_name}]")

        # Determine enabled tasks for the selected profile
        profile = project.profiles.get(active_prof_name)
        enabled_ids = set(profile.enabled_task_ids) if profile else {t.id for t in project.tasks if t.enabled}

        # Filter and sort tasks by order
        tasks_to_run = [t for t in project.tasks if t.id in enabled_ids and t.enabled]
        tasks_to_run.sort(key=lambda x: x.order)

        # Retrieve enabled attached workspace resources
        resources_to_run = project.get_enabled_resources()

        # Notify UI of queued status for all tasks and attached resources
        for task in tasks_to_run:
            self._notify_task(task.id, TaskStatus.QUEUED, "Queued")
        for res in resources_to_run:
            self._notify_task(f"res_{res.id}", TaskStatus.QUEUED, "Queued")

        completed_ids = []
        failed_ids = []
        overall_success = True

        # Phase 1: Execute configured workflow tasks (IDE, terminals, commands, health checks)
        for task in tasks_to_run:
            if self._cancel_requested.is_set():
                logger.warn(f"Task skipped due to cancellation: '{task.name}'")
                self._notify_task(task.id, TaskStatus.CANCELLED, "Cancelled by user")
                continue

            # In resume mode, skip one-time tasks (like npm install or initial setup)
            if is_resume and task.is_one_time:
                logger.info(f"Skipping one-time setup task for session resume: '{task.name}'")
                self._notify_task(task.id, TaskStatus.SKIPPED, "Skipped (one-time setup already completed)")
                continue

            self._notify_task(task.id, TaskStatus.RUNNING, "Executing...")
            res = self._execute_single_task(project, task)

            if res.status == TaskStatus.SUCCESS:
                completed_ids.append(task.id)
                self._notify_task(task.id, TaskStatus.SUCCESS, res.message, res)
            elif res.status == TaskStatus.SKIPPED:
                self._notify_task(task.id, TaskStatus.SKIPPED, res.message, res)
            else:
                failed_ids.append(task.id)
                overall_success = False
                self._notify_task(task.id, TaskStatus.FAILED, res.message, res)
                # Failure logged clearly
                logger.error(f"Task failed: '{task.name}': {res.message}")

        # Phase 2: Launch attached workspace resources (AI Chats, Websites, Local Files/Folders, Apps)
        for res in resources_to_run:
            res_id = f"res_{res.id}"
            if self._cancel_requested.is_set():
                logger.warn(f"Resource skipped due to cancellation: '{res.name}'")
                self._notify_task(res_id, TaskStatus.CANCELLED, "Cancelled by user")
                continue

            self._notify_task(res_id, TaskStatus.RUNNING, "Opening...")
            start_t = time.time()
            try:
                success, msg, pid = launch_single_resource(res, project.root_path, project.ide_preference)
                duration = time.time() - start_t
                if pid:
                    with self._lock:
                        self._active_pids.append(pid)

                status = TaskStatus.SUCCESS if success else TaskStatus.FAILED
                if success:
                    completed_ids.append(res_id)
                    logger.info(f"Resource launched successfully: '{res.name}': {msg}")
                else:
                    failed_ids.append(res_id)
                    overall_success = False
                    logger.error(f"Failed to launch resource '{res.name}': {msg}")

                res_exec = TaskExecutionResult(
                    task_id=res_id,
                    task_name=res.name,
                    status=status,
                    message=msg,
                    duration_seconds=duration
                )
                self._notify_task(res_id, status, msg, res_exec)
            except Exception as e:
                duration = time.time() - start_t
                failed_ids.append(res_id)
                overall_success = False
                err_msg = f"Resource exception: {str(e)}"
                logger.error(f"Resource '{res.name}' threw exception: {err_msg}")
                res_exec = TaskExecutionResult(
                    task_id=res_id,
                    task_name=res.name,
                    status=TaskStatus.FAILED,
                    message=err_msg,
                    duration_seconds=duration
                )
                self._notify_task(res_id, TaskStatus.FAILED, err_msg, res_exec)

        self._is_running = False
        summary = f"Workflow finished. {len(completed_ids)} completed, {len(failed_ids)} failed."
        if self._cancel_requested.is_set():
            summary = "Workflow stopped by user."
            logger.warn(summary)
        elif overall_success:
            logger.success(f"Project '{project.name}' launched successfully! {summary}")
        else:
            logger.error(f"Project '{project.name}' finished with failures. {summary}")

        if self.on_workflow_finished:
            try:
                self.on_workflow_finished(project.id, overall_success and not self._cancel_requested.is_set(), summary)
            except Exception as e:
                logger.error(f"Error in on_workflow_finished callback: {e}")

    def _execute_single_task(self, project: ProjectConfig, task: TaskConfig) -> TaskExecutionResult:
        start_time = time.time()
        task_type = task.task_type

        try:
            # 1. Antigravity launch
            if task_type == TaskType.ANTIGRAVITY:
                return self._task_antigravity(project, task, start_time)

            # 2. Terminal launch
            elif task_type == TaskType.TERMINAL:
                return self._task_terminal(project, task, start_time)

            # 3. Synchronous / Background command
            elif task_type == TaskType.COMMAND:
                return self._task_command(project, task, start_time)

            # 4. Tool check
            elif task_type == TaskType.TOOL_CHECK:
                return self._task_tool_check(task, start_time)

            # 5. Health check
            elif task_type == TaskType.HEALTH_CHECK:
                return self._task_health_check(project, task, start_time)

            # 6. Browser
            elif task_type == TaskType.BROWSER:
                return self._task_browser(task, start_time)

            # 7. Supporting Application
            elif task_type == TaskType.APPLICATION:
                return self._task_application(task, start_time)

            else:
                return TaskExecutionResult(
                    task_id=task.id,
                    task_name=task.name,
                    status=TaskStatus.FAILED,
                    message=f"Unknown task type: {task_type}",
                    duration_seconds=time.time() - start_time
                )

        except Exception as e:
            return TaskExecutionResult(
                task_id=task.id,
                task_name=task.name,
                status=TaskStatus.FAILED,
                message=f"Exception: {str(e)}",
                duration_seconds=time.time() - start_time
            )

    # ---------------- Specific Task Executors ---------------- #

    def _task_antigravity(self, project: ProjectConfig, task: TaskConfig, start_time: float) -> TaskExecutionResult:
        workspace_dir = task.target or project.root_path
        if not Path(workspace_dir).is_dir():
            return TaskExecutionResult(
                task_id=task.id,
                task_name=task.name,
                status=TaskStatus.FAILED,
                message=f"Workspace path does not exist: {workspace_dir}",
                duration_seconds=time.time() - start_time
            )

        # Determine target IDE executable and settings
        ide_name = project.ide_preference.ide_name if project.ide_preference else "Antigravity IDE"
        ide_exe = (
            (project.ide_preference.executable_path if project.ide_preference else None)
            or project.antigravity.executable_path
            or find_antigravity_executable()
        )

        if not ide_exe or not Path(ide_exe).exists():
            return TaskExecutionResult(
                task_id=task.id,
                task_name=task.name,
                status=TaskStatus.FAILED,
                message=f"IDE executable not found: {ide_exe}",
                duration_seconds=time.time() - start_time
            )

        # Check if Antigravity already open
        if "antigravity" in ide_exe.lower() and is_workspace_open_in_antigravity(workspace_dir):
            logger.info(f"{ide_name} already running with workspace '{workspace_dir}'. Reusing active instance.")
            msg = f"Reused existing active {ide_name} workspace instance"
        else:
            logger.info(f"Opening workspace in {ide_name}: {workspace_dir}")
            reuse = project.ide_preference.reuse_window if project.ide_preference else project.antigravity.reuse_window
            new_win = project.ide_preference.new_window if project.ide_preference else project.antigravity.new_window
            proc = launch_ide_workspace(
                executable_path=ide_exe,
                workspace_path=workspace_dir,
                reuse_window=reuse,
                new_window=new_win
            )
            with self._lock:
                self._active_pids.append(proc.pid)
            msg = f"Launched {ide_name} (PID: {proc.pid})"

        return TaskExecutionResult(
            task_id=task.id,
            task_name=task.name,
            status=TaskStatus.SUCCESS,
            message=msg,
            duration_seconds=time.time() - start_time
        )

    def _task_terminal(self, project: ProjectConfig, task: TaskConfig, start_time: float) -> TaskExecutionResult:
        working_dir = task.working_dir or project.root_path
        term_type = task.terminal_type or "wt"

        # Check command approval if startup command is present
        startup_cmd = task.target if task.target else None
        if startup_cmd:
            if not task.approved:
                safe, reason = is_safe_startup_command(startup_cmd)
                if not safe:
                    return TaskExecutionResult(
                        task_id=task.id,
                        task_name=task.name,
                        status=TaskStatus.FAILED,
                        message=f"Command safety restriction: {reason}",
                        duration_seconds=time.time() - start_time
                    )

        logger.info(f"Opening {term_type} terminal in '{working_dir}'" + (f" with command '{startup_cmd}'" if startup_cmd else ""))
        proc = launch_terminal_window(
            terminal_type=term_type,
            working_dir=working_dir,
            startup_command=startup_cmd,
            title=f"DevPilot: {project.name}"
        )
        with self._lock:
            self._active_pids.append(proc.pid)

        return TaskExecutionResult(
            task_id=task.id,
            task_name=task.name,
            status=TaskStatus.SUCCESS,
            message=f"Terminal launched ({term_type}, PID: {proc.pid})",
            duration_seconds=time.time() - start_time
        )

    def _task_command(self, project: ProjectConfig, task: TaskConfig, start_time: float) -> TaskExecutionResult:
        cmd = task.target
        if not cmd:
            return TaskExecutionResult(
                task_id=task.id,
                task_name=task.name,
                status=TaskStatus.SKIPPED,
                message="No command specified",
                duration_seconds=time.time() - start_time
            )

        if not task.approved:
            return TaskExecutionResult(
                task_id=task.id,
                task_name=task.name,
                status=TaskStatus.FAILED,
                message="Startup command requires user approval before execution.",
                duration_seconds=time.time() - start_time
            )

        working_dir = task.working_dir or project.root_path
        logger.info(f"Running startup command in '{working_dir}': {cmd}")
        
        code, stdout, stderr = run_command_capture(cmd, working_dir, timeout_seconds=task.timeout_seconds)
        
        output_preview = (stdout + "\n" + stderr).strip()
        if output_preview:
            # Mask secrets from output
            logger.info(f"Command output: {output_preview[:200]}")

        if code == 0:
            return TaskExecutionResult(
                task_id=task.id,
                task_name=task.name,
                status=TaskStatus.SUCCESS,
                message="Command finished successfully",
                exit_code=code,
                output_preview=output_preview,
                duration_seconds=time.time() - start_time
            )
        else:
            return TaskExecutionResult(
                task_id=task.id,
                task_name=task.name,
                status=TaskStatus.FAILED,
                message=f"Command exited with code {code}: {stderr[:150] or stdout[:150]}",
                exit_code=code,
                output_preview=output_preview,
                duration_seconds=time.time() - start_time
            )

    def _task_tool_check(self, task: TaskConfig, start_time: float) -> TaskExecutionResult:
        tool_name = task.target or "git"
        logger.info(f"Checking environment tool: {tool_name}")
        tools = detect_installed_tools()
        info = tools.get(tool_name.lower())

        if info and info.get("available"):
            ver = info.get("version", "Installed")
            return TaskExecutionResult(
                task_id=task.id,
                task_name=task.name,
                status=TaskStatus.SUCCESS,
                message=f"Verified: {ver}",
                duration_seconds=time.time() - start_time
            )
        else:
            # Fallback path lookup
            which_p = shutil.which(tool_name)
            if which_p:
                return TaskExecutionResult(
                    task_id=task.id,
                    task_name=task.name,
                    status=TaskStatus.SUCCESS,
                    message=f"Found: {which_p}",
                    duration_seconds=time.time() - start_time
                )
            return TaskExecutionResult(
                task_id=task.id,
                task_name=task.name,
                status=TaskStatus.FAILED,
                message=f"Tool '{tool_name}' not found on system PATH",
                duration_seconds=time.time() - start_time
            )

    def _task_health_check(self, project: ProjectConfig, task: TaskConfig, start_time: float) -> TaskExecutionResult:
        logger.info(f"Running health check: {task.name}")
        if task.target.lower() == "git":
            git_info = check_git_status(project.root_path)
            if not git_info.get("is_git"):
                return TaskExecutionResult(
                    task_id=task.id,
                    task_name=task.name,
                    status=TaskStatus.SKIPPED,
                    message="Not a git repository",
                    duration_seconds=time.time() - start_time
                )
            msg = git_info.get("message", "Git checked")
            return TaskExecutionResult(
                task_id=task.id,
                task_name=task.name,
                status=TaskStatus.SUCCESS,
                message=msg,
                duration_seconds=time.time() - start_time
            )
        else:
            return TaskExecutionResult(
                task_id=task.id,
                task_name=task.name,
                status=TaskStatus.SUCCESS,
                message="Health check passed",
                duration_seconds=time.time() - start_time
            )

    def _task_browser(self, task: TaskConfig, start_time: float) -> TaskExecutionResult:
        url = task.target
        if not url:
            return TaskExecutionResult(
                task_id=task.id,
                task_name=task.name,
                status=TaskStatus.SKIPPED,
                message="No URL specified",
                duration_seconds=time.time() - start_time
            )
        logger.info(f"Opening browser URL: {url}")
        ok = open_browser_url(url)
        return TaskExecutionResult(
            task_id=task.id,
            task_name=task.name,
            status=TaskStatus.SUCCESS if ok else TaskStatus.FAILED,
            message=f"Opened in browser: {url}" if ok else f"Failed to open URL {url}",
            duration_seconds=time.time() - start_time
        )

    def _task_application(self, task: TaskConfig, start_time: float) -> TaskExecutionResult:
        app_path = task.target
        if not app_path:
            return TaskExecutionResult(
                task_id=task.id,
                task_name=task.name,
                status=TaskStatus.SKIPPED,
                message="No application path specified",
                duration_seconds=time.time() - start_time
            )

        logger.info(f"Launching supporting application: {app_path}")
        proc = launch_supporting_application(app_path, task.arguments)
        with self._lock:
            self._active_pids.append(proc.pid)

        return TaskExecutionResult(
            task_id=task.id,
            task_name=task.name,
            status=TaskStatus.SUCCESS,
            message=f"Application launched (PID: {proc.pid})",
            duration_seconds=time.time() - start_time
        )

    # ---------------- Retry Support ---------------- #

    def retry_single_task_async(self, project: ProjectConfig, task_id: str) -> threading.Thread:
        """Allow retrying a single failed task without restarting the entire workflow."""
        thread = threading.Thread(
            target=self._retry_single_task,
            args=(project, task_id),
            name=f"Retry-{task_id}",
            daemon=True
        )
        thread.start()
        return thread

    def _retry_single_task(self, project: ProjectConfig, task_id: str):
        if task_id.startswith("res_"):
            res_id = task_id[4:]
            target_res = project.get_resource(res_id)
            if not target_res:
                logger.error(f"Cannot retry resource: resource ID '{res_id}' not found.")
                return

            logger.info(f"Retrying attached resource: '{target_res.name}'...")
            self._notify_task(task_id, TaskStatus.RUNNING, "Retrying...")
            start_t = time.time()
            try:
                success, msg, pid = launch_single_resource(target_res, project.root_path, project.ide_preference)
                duration = time.time() - start_t
                if pid:
                    with self._lock:
                        self._active_pids.append(pid)

                status = TaskStatus.SUCCESS if success else TaskStatus.FAILED
                res_exec = TaskExecutionResult(
                    task_id=task_id,
                    task_name=target_res.name,
                    status=status,
                    message=msg,
                    duration_seconds=duration
                )
                self._notify_task(task_id, status, msg, res_exec)
                if success:
                    logger.success(f"Retry succeeded for resource '{target_res.name}': {msg}")
                else:
                    logger.error(f"Retry failed for resource '{target_res.name}': {msg}")
            except Exception as e:
                duration = time.time() - start_t
                err_msg = f"Resource retry exception: {str(e)}"
                res_exec = TaskExecutionResult(
                    task_id=task_id,
                    task_name=target_res.name,
                    status=TaskStatus.FAILED,
                    message=err_msg,
                    duration_seconds=duration
                )
                self._notify_task(task_id, TaskStatus.FAILED, err_msg, res_exec)
                logger.error(f"Retry failed for resource '{target_res.name}': {err_msg}")
            return

        target_task = None
        for t in project.tasks:
            if t.id == task_id:
                target_task = t
                break

        if not target_task:
            logger.error(f"Cannot retry task: task ID '{task_id}' not found.")
            return

        logger.info(f"Retrying task: '{target_task.name}'...")
        self._notify_task(target_task.id, TaskStatus.RUNNING, "Retrying...")
        res = self._execute_single_task(project, target_task)

        if res.status == TaskStatus.SUCCESS:
            logger.success(f"Retry succeeded for '{target_task.name}': {res.message}")
            self._notify_task(target_task.id, TaskStatus.SUCCESS, res.message, res)
        else:
            logger.error(f"Retry failed for '{target_task.name}': {res.message}")
            self._notify_task(target_task.id, TaskStatus.FAILED, res.message, res)
