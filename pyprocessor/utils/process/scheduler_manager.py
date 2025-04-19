"""
Scheduler management utilities for PyProcessor.

This module provides a centralized way to manage scheduling of tasks, including:
- Task scheduling and execution
- Task prioritization and dependencies
- Task monitoring and status tracking
- Task cancellation and cleanup
"""

import os
import sys
import time
import threading
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Callable, Tuple, Set

from pyprocessor.utils.log_manager import get_logger
from pyprocessor.utils.process_manager import get_process_manager, submit_task
from pyprocessor.utils.error_manager import with_error_handling, PyProcessorError, ErrorSeverity


class SchedulerError(PyProcessorError):
    """Error related to scheduler management."""
    pass


class Task:
    """
    Represents a scheduled task.

    A task is a unit of work that can be scheduled for execution.
    """

    def __init__(self,
                 task_id: str,
                 func: Callable,
                 args: tuple = (),
                 kwargs: dict = None,
                 priority: int = 0,
                 dependencies: List[str] = None,
                 timeout: Optional[float] = None,
                 callback: Optional[Callable] = None):
        """
        Initialize a task.

        Args:
            task_id: Unique identifier for the task
            func: Function to execute
            args: Arguments to pass to the function
            kwargs: Keyword arguments to pass to the function
            priority: Priority of the task (higher values = higher priority)
            dependencies: List of task IDs that must complete before this task
            timeout: Timeout in seconds
            callback: Function to call when the task completes
        """
        self.task_id = task_id
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.priority = priority
        self.dependencies = dependencies or []
        self.timeout = timeout
        self.callback = callback

        # Task status
        self.status = "pending"  # pending, running, completed, failed, cancelled
        self.result = None
        self.error = None
        self.submitted_at = None
        self.started_at = None
        self.completed_at = None
        self.process_task_id = None  # ID of the task in the process manager

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the task to a dictionary.

        Returns:
            Dict[str, Any]: Task information
        """
        return {
            "task_id": self.task_id,
            "func": self.func.__name__,
            "args": self.args,
            "kwargs": self.kwargs,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "timeout": self.timeout,
            "status": self.status,
            "submitted_at": self.submitted_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "process_task_id": self.process_task_id,
        }


class SchedulerManager:
    """
    Centralized manager for scheduling tasks.

    This class handles:
    - Task scheduling and execution
    - Task prioritization and dependencies
    - Task monitoring and status tracking
    - Task cancellation and cleanup
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SchedulerManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """Initialize the scheduler manager."""
        # Only initialize once
        if self._initialized:
            return

        # Get logger
        self.logger = get_logger()

        # Get process manager
        self.process_manager = get_process_manager()

        # Initialize task tracking
        self._tasks = {}  # Dict of all tasks
        self._pending_tasks = {}  # Dict of pending tasks
        self._running_tasks = {}  # Dict of running tasks
        self._completed_tasks = {}  # Dict of completed tasks

        # Initialize locks
        self._task_lock = threading.Lock()

        # Initialize scheduler thread
        self._scheduler_thread = None
        self._scheduler_running = False

        # Mark as initialized
        self._initialized = True
        self.logger.debug("Scheduler manager initialized")

    @with_error_handling
    def start_scheduler(self):
        """Start the scheduler thread."""
        with self._task_lock:
            if self._scheduler_running:
                return

            self._scheduler_running = True
            self._scheduler_thread = threading.Thread(
                target=self._scheduler_loop,
                daemon=True,
                name="SchedulerThread"
            )
            self._scheduler_thread.start()
            self.logger.debug("Scheduler thread started")

    @with_error_handling
    def stop_scheduler(self):
        """Stop the scheduler thread."""
        with self._task_lock:
            if not self._scheduler_running:
                return

            self._scheduler_running = False

            # Wait for the scheduler thread to stop
            if self._scheduler_thread and self._scheduler_thread.is_alive():
                self._scheduler_thread.join(timeout=5.0)

            self.logger.debug("Scheduler thread stopped")

    def _scheduler_loop(self):
        """Main scheduler loop that processes pending tasks."""
        while self._scheduler_running:
            try:
                # Process pending tasks
                self._process_pending_tasks()

                # Check running tasks
                self._check_running_tasks()

                # Sleep to avoid CPU spinning
                time.sleep(0.1)

            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {str(e)}")
                time.sleep(1.0)  # Sleep longer on error

    def _process_pending_tasks(self):
        """Process pending tasks and submit them for execution."""
        with self._task_lock:
            # Get all pending tasks
            pending_tasks = list(self._pending_tasks.values())

            # Sort by priority (higher values first)
            pending_tasks.sort(key=lambda t: t.priority, reverse=True)

            for task in pending_tasks:
                # Skip if task is no longer pending
                if task.status != "pending":
                    continue

                # Check if all dependencies are completed
                dependencies_met = True
                for dep_id in task.dependencies:
                    if dep_id not in self._completed_tasks:
                        dependencies_met = False
                        break

                if not dependencies_met:
                    continue

                # Submit the task to the process manager
                try:
                    # Update task status
                    task.status = "running"
                    task.started_at = time.time()

                    # Submit the task
                    process_task_id = submit_task(
                        task.func,
                        *task.args,
                        **task.kwargs
                    )

                    # Update task with process task ID
                    task.process_task_id = process_task_id

                    # Move task from pending to running
                    self._running_tasks[task.task_id] = task
                    del self._pending_tasks[task.task_id]

                    self.logger.debug(
                        f"Task {task.task_id} submitted for execution",
                        task_id=task.task_id,
                        process_task_id=process_task_id
                    )

                except Exception as e:
                    # Update task status on error
                    task.status = "failed"
                    task.error = str(e)
                    task.completed_at = time.time()

                    # Move task from pending to completed
                    self._completed_tasks[task.task_id] = task
                    del self._pending_tasks[task.task_id]

                    self.logger.error(
                        f"Error submitting task {task.task_id}: {str(e)}",
                        task_id=task.task_id,
                        error=str(e)
                    )

    def _check_running_tasks(self):
        """Check the status of running tasks and update their status."""
        with self._task_lock:
            # Get all running tasks
            running_tasks = list(self._running_tasks.values())

            for task in running_tasks:
                # Skip if task is no longer running
                if task.status != "running":
                    continue

                # Get task status from process manager
                process_status = self.process_manager.get_task_status(task.process_task_id)

                # If process task is not found, mark as failed
                if process_status is None:
                    task.status = "failed"
                    task.error = "Process task not found"
                    task.completed_at = time.time()

                    # Move task from running to completed
                    self._completed_tasks[task.task_id] = task
                    del self._running_tasks[task.task_id]

                    self.logger.error(
                        f"Process task not found for task {task.task_id}",
                        task_id=task.task_id,
                        process_task_id=task.process_task_id
                    )

                    # Call callback if provided
                    if task.callback:
                        try:
                            task.callback(task.task_id, False, task.error)
                        except Exception as e:
                            self.logger.error(
                                f"Error in task callback: {str(e)}",
                                task_id=task.task_id,
                                error=str(e)
                            )

                    continue

                # Check if process task is completed
                if process_status["status"] in ["completed", "error", "cancelled"]:
                    # Get the result or error
                    try:
                        if process_status["status"] == "completed":
                            # Get the result
                            result = self.process_manager.get_task_result(task.process_task_id)

                            # Update task status
                            task.status = "completed"
                            task.result = result
                            task.completed_at = time.time()

                            self.logger.debug(
                                f"Task {task.task_id} completed successfully",
                                task_id=task.task_id,
                                process_task_id=task.process_task_id
                            )

                            # Call callback if provided
                            if task.callback:
                                try:
                                    task.callback(task.task_id, True, result)
                                except Exception as e:
                                    self.logger.error(
                                        f"Error in task callback: {str(e)}",
                                        task_id=task.task_id,
                                        error=str(e)
                                    )
                        else:
                            # Update task status on error or cancellation
                            task.status = "failed" if process_status["status"] == "error" else "cancelled"
                            task.error = process_status.get("error", "Unknown error")
                            task.completed_at = time.time()

                            self.logger.error(
                                f"Task {task.task_id} {task.status}: {task.error}",
                                task_id=task.task_id,
                                process_task_id=task.process_task_id,
                                error=task.error
                            )

                            # Call callback if provided
                            if task.callback:
                                try:
                                    task.callback(task.task_id, False, task.error)
                                except Exception as e:
                                    self.logger.error(
                                        f"Error in task callback: {str(e)}",
                                        task_id=task.task_id,
                                        error=str(e)
                                    )
                    except Exception as e:
                        # Update task status on error
                        task.status = "failed"
                        task.error = str(e)
                        task.completed_at = time.time()

                        self.logger.error(
                            f"Error getting task result: {str(e)}",
                            task_id=task.task_id,
                            process_task_id=task.process_task_id,
                            error=str(e)
                        )

                        # Call callback if provided
                        if task.callback:
                            try:
                                task.callback(task.task_id, False, str(e))
                            except Exception as e:
                                self.logger.error(
                                    f"Error in task callback: {str(e)}",
                                    task_id=task.task_id,
                                    error=str(e)
                                )

                    # Move task from running to completed
                    self._completed_tasks[task.task_id] = task
                    del self._running_tasks[task.task_id]

    @with_error_handling
    def schedule_task(self, func, *args, task_id=None, priority=0, dependencies=None, timeout=None, callback=None, **kwargs):
        """
        Schedule a task for execution.

        Args:
            func: Function to execute
            *args: Arguments to pass to the function
            task_id: Optional ID for the task (auto-generated if None)
            priority: Priority of the task (higher values = higher priority)
            dependencies: List of task IDs that must complete before this task
            timeout: Timeout in seconds
            callback: Function to call when the task completes
            **kwargs: Keyword arguments to pass to the function

        Returns:
            str: Task ID
        """
        # Generate task ID if not provided
        if task_id is None:
            task_id = str(uuid.uuid4())

        # Create the task
        task = Task(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            dependencies=dependencies or [],
            timeout=timeout,
            callback=callback
        )

        # Set submission time
        task.submitted_at = time.time()

        # Add the task to the pending queue
        with self._task_lock:
            self._tasks[task_id] = task
            self._pending_tasks[task_id] = task

        self.logger.debug(
            f"Task {task_id} scheduled",
            task_id=task_id,
            func=func.__name__,
            priority=priority
        )

        # Start the scheduler if not already running
        if not self._scheduler_running:
            self.start_scheduler()

        return task_id

    @with_error_handling
    def cancel_task(self, task_id):
        """
        Cancel a scheduled task.

        Args:
            task_id: ID of the task to cancel

        Returns:
            bool: True if the task was cancelled, False otherwise
        """
        with self._task_lock:
            # Check if task exists
            if task_id not in self._tasks:
                return False

            task = self._tasks[task_id]

            # If task is pending, just remove it
            if task.status == "pending":
                task.status = "cancelled"
                task.completed_at = time.time()

                # Move task from pending to completed
                self._completed_tasks[task_id] = task
                del self._pending_tasks[task_id]

                self.logger.debug(
                    f"Pending task {task_id} cancelled",
                    task_id=task_id
                )

                # Call callback if provided
                if task.callback:
                    try:
                        task.callback(task_id, False, "Task cancelled")
                    except Exception as e:
                        self.logger.error(
                            f"Error in task callback: {str(e)}",
                            task_id=task_id,
                            error=str(e)
                        )

                return True

            # If task is running, cancel the process task
            elif task.status == "running" and task.process_task_id:
                # Cancel the process task
                cancelled = self.process_manager.cancel_task(task.process_task_id)

                if cancelled:
                    task.status = "cancelled"
                    task.completed_at = time.time()

                    # Move task from running to completed
                    self._completed_tasks[task_id] = task
                    del self._running_tasks[task_id]

                    self.logger.debug(
                        f"Running task {task_id} cancelled",
                        task_id=task_id,
                        process_task_id=task.process_task_id
                    )

                    # Call callback if provided
                    if task.callback:
                        try:
                            task.callback(task_id, False, "Task cancelled")
                        except Exception as e:
                            self.logger.error(
                                f"Error in task callback: {str(e)}",
                                task_id=task_id,
                                error=str(e)
                            )

                    return True
                else:
                    self.logger.warning(
                        f"Failed to cancel running task {task_id}",
                        task_id=task_id,
                        process_task_id=task.process_task_id
                    )
                    return False

            # Task is already completed or cancelled
            return False

    @with_error_handling
    def get_task_status(self, task_id):
        """
        Get the status of a task.

        Args:
            task_id: ID of the task

        Returns:
            Dict[str, Any]: Task status information or None if not found
        """
        with self._task_lock:
            # Check if task exists
            if task_id not in self._tasks:
                return None

            # Return task information
            return self._tasks[task_id].to_dict()

    @with_error_handling
    def get_all_tasks(self):
        """
        Get all tasks.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of task information
        """
        with self._task_lock:
            return {task_id: task.to_dict() for task_id, task in self._tasks.items()}

    @with_error_handling
    def get_pending_tasks(self):
        """
        Get all pending tasks.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of pending task information
        """
        with self._task_lock:
            return {task_id: task.to_dict() for task_id, task in self._pending_tasks.items()}

    @with_error_handling
    def get_running_tasks(self):
        """
        Get all running tasks.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of running task information
        """
        with self._task_lock:
            return {task_id: task.to_dict() for task_id, task in self._running_tasks.items()}

    @with_error_handling
    def get_completed_tasks(self):
        """
        Get all completed tasks.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of completed task information
        """
        with self._task_lock:
            return {task_id: task.to_dict() for task_id, task in self._completed_tasks.items()}

    @with_error_handling
    def clear_completed_tasks(self):
        """
        Clear all completed tasks.

        Returns:
            int: Number of tasks cleared
        """
        with self._task_lock:
            count = len(self._completed_tasks)

            # Remove completed tasks from the main tasks dict
            for task_id in list(self._completed_tasks.keys()):
                del self._tasks[task_id]

            # Clear the completed tasks dict
            self._completed_tasks.clear()

            return count

    @with_error_handling
    def wait_for_task(self, task_id, timeout=None):
        """
        Wait for a task to complete.

        Args:
            task_id: ID of the task to wait for
            timeout: Timeout in seconds

        Returns:
            Any: Task result or None if the task failed or timed out

        Raises:
            SchedulerError: If the task is not found
        """
        # Check if task exists
        with self._task_lock:
            if task_id not in self._tasks:
                raise SchedulerError(
                    f"Task not found: {task_id}",
                    severity=ErrorSeverity.ERROR,
                    details={"task_id": task_id}
                )

            task = self._tasks[task_id]

            # If task is already completed, return the result
            if task.status in ["completed", "failed", "cancelled"]:
                return task.result if task.status == "completed" else None

            # If task is running, get the process task ID
            process_task_id = task.process_task_id if task.status == "running" else None

        # If task is running, wait for the process task to complete
        if process_task_id:
            try:
                return self.process_manager.get_task_result(process_task_id, timeout=timeout)
            except Exception as e:
                self.logger.error(
                    f"Error waiting for task {task_id}: {str(e)}",
                    task_id=task_id,
                    process_task_id=process_task_id,
                    error=str(e)
                )
                return None

        # Task is pending, wait for it to complete
        start_time = time.time()
        while True:
            # Check if timeout has expired
            if timeout is not None and time.time() - start_time > timeout:
                self.logger.warning(
                    f"Timeout waiting for task {task_id}",
                    task_id=task_id,
                    timeout=timeout
                )
                return None

            # Get task status
            with self._task_lock:
                if task_id not in self._tasks:
                    raise SchedulerError(
                        f"Task not found: {task_id}",
                        severity=ErrorSeverity.ERROR,
                        details={"task_id": task_id}
                    )

                task = self._tasks[task_id]

                # If task is completed, return the result
                if task.status in ["completed", "failed", "cancelled"]:
                    return task.result if task.status == "completed" else None

            # Sleep before checking again
            time.sleep(0.1)


# Singleton instance
_scheduler_manager = None


def get_scheduler_manager() -> SchedulerManager:
    """
    Get the singleton scheduler manager instance.

    Returns:
        SchedulerManager: The singleton scheduler manager instance
    """
    global _scheduler_manager
    if _scheduler_manager is None:
        _scheduler_manager = SchedulerManager()
    return _scheduler_manager


# Module-level functions for convenience

def start_scheduler():
    """
    Start the scheduler thread.
    """
    return get_scheduler_manager().start_scheduler()


def stop_scheduler():
    """
    Stop the scheduler thread.
    """
    return get_scheduler_manager().stop_scheduler()


def schedule_task(func, *args, task_id=None, priority=0, dependencies=None, timeout=None, callback=None, **kwargs):
    """
    Schedule a task for execution.

    Args:
        func: Function to execute
        *args: Arguments to pass to the function
        task_id: Optional ID for the task (auto-generated if None)
        priority: Priority of the task (higher values = higher priority)
        dependencies: List of task IDs that must complete before this task
        timeout: Timeout in seconds
        callback: Function to call when the task completes
        **kwargs: Keyword arguments to pass to the function

    Returns:
        str: Task ID
    """
    return get_scheduler_manager().schedule_task(
        func, *args, task_id=task_id, priority=priority, dependencies=dependencies,
        timeout=timeout, callback=callback, **kwargs
    )


def cancel_task(task_id):
    """
    Cancel a scheduled task.

    Args:
        task_id: ID of the task to cancel

    Returns:
        bool: True if the task was cancelled, False otherwise
    """
    return get_scheduler_manager().cancel_task(task_id)


def get_task_status(task_id):
    """
    Get the status of a task.

    Args:
        task_id: ID of the task

    Returns:
        Dict[str, Any]: Task status information or None if not found
    """
    return get_scheduler_manager().get_task_status(task_id)


def get_all_tasks():
    """
    Get all tasks.

    Returns:
        Dict[str, Dict[str, Any]]: Dictionary of task information
    """
    return get_scheduler_manager().get_all_tasks()


def get_pending_tasks():
    """
    Get all pending tasks.

    Returns:
        Dict[str, Dict[str, Any]]: Dictionary of pending task information
    """
    return get_scheduler_manager().get_pending_tasks()


def get_running_tasks():
    """
    Get all running tasks.

    Returns:
        Dict[str, Dict[str, Any]]: Dictionary of running task information
    """
    return get_scheduler_manager().get_running_tasks()


def get_completed_tasks():
    """
    Get all completed tasks.

    Returns:
        Dict[str, Dict[str, Any]]: Dictionary of completed task information
    """
    return get_scheduler_manager().get_completed_tasks()


def clear_completed_tasks():
    """
    Clear all completed tasks.

    Returns:
        int: Number of tasks cleared
    """
    return get_scheduler_manager().clear_completed_tasks()


def wait_for_task(task_id, timeout=None):
    """
    Wait for a task to complete.

    Args:
        task_id: ID of the task to wait for
        timeout: Timeout in seconds

    Returns:
        Any: Task result or None if the task failed or timed out

    Raises:
        SchedulerError: If the task is not found
    """
    return get_scheduler_manager().wait_for_task(task_id, timeout)
