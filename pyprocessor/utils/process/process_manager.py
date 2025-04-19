"""
Process management utilities for PyProcessor.

This module provides a centralized way to manage processes, including:
- Process creation and execution
- Process monitoring and status tracking
- Process termination and cleanup
- Inter-process communication
"""

import os
import sys
import time
import signal
import subprocess
import threading
import uuid
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Union, Callable, Tuple, Any
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, Future, CancelledError, TimeoutError
from multiprocessing import Manager, Queue, Event, Lock as ProcessLock, Value as SharedValue
from contextlib import contextmanager

from pyprocessor.utils.log_manager import get_logger
from pyprocessor.utils.path_manager import get_temp_dir, normalize_path
from pyprocessor.utils.error_manager import with_error_handling, PyProcessorError, ErrorSeverity


class ProcessError(PyProcessorError):
    """Error related to process management."""
    pass


class ProcessManager:
    """
    Centralized manager for process-related operations.

    This class handles:
    - Process creation and execution
    - Process monitoring and status tracking
    - Process termination and cleanup
    - Inter-process communication
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ProcessManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """Initialize the process manager."""
        # Only initialize once
        if self._initialized:
            return

        # Get logger
        self.logger = get_logger()

        # Initialize process tracking
        self._processes = {}  # Dict of active processes
        self._futures = {}    # Dict of futures from executors
        self._executors = {}  # Dict of executors

        # Initialize IPC
        self._manager = Manager()
        self._queues = {}     # Dict of queues for IPC

        # Initialize locks
        self._process_lock = threading.Lock()
        self._executor_lock = threading.Lock()
        self._queue_lock = threading.Lock()

        # Initialize default executors
        self._default_process_executor = None
        self._default_thread_executor = None

        # Mark as initialized
        self._initialized = True
        self.logger.debug("Process manager initialized")

    @with_error_handling
    def run_process(self, cmd: List[str], shell: bool = False,
                   cwd: Optional[Union[str, Path]] = None,
                   env: Optional[Dict[str, str]] = None,
                   input_data: Optional[str] = None,
                   timeout: Optional[float] = None,
                   capture_output: bool = True,
                   process_id: Optional[str] = None,
                   callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Run a process and return its output.

        Args:
            cmd: Command to run as a list of strings
            shell: Whether to run the command in a shell
            cwd: Working directory for the command
            env: Environment variables for the command
            input_data: Input data to pass to the process
            timeout: Timeout in seconds
            capture_output: Whether to capture stdout and stderr
            process_id: Optional ID for the process (auto-generated if None)
            callback: Optional callback function to call when the process completes

        Returns:
            Dict with process information including:
            - returncode: Return code of the process
            - stdout: Standard output (if capture_output is True)
            - stderr: Standard error (if capture_output is True)
            - pid: Process ID
            - command: Command that was run
            - duration: Duration of the process in seconds
            - process_id: ID of the process
        """
        # Generate process ID if not provided
        if process_id is None:
            process_id = str(uuid.uuid4())

        # Normalize working directory if provided
        if cwd is not None:
            cwd = str(normalize_path(cwd))

        # Log the command
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
        self.logger.debug(f"Running process: {cmd_str}", process_id=process_id)

        # Set up stdout and stderr
        stdout = subprocess.PIPE if capture_output else None
        stderr = subprocess.PIPE if capture_output else None

        # Start timing
        start_time = time.time()

        try:
            # Start the process
            process = subprocess.Popen(
                cmd,
                shell=shell,
                cwd=cwd,
                env=env,
                stdin=subprocess.PIPE if input_data is not None else None,
                stdout=stdout,
                stderr=stderr,
                text=True,
                universal_newlines=True,
                bufsize=1,  # Line buffered
            )

            # Store the process
            with self._process_lock:
                self._processes[process_id] = {
                    "process": process,
                    "command": cmd,
                    "start_time": start_time,
                    "status": "running",
                    "pid": process.pid,
                }

            # Send input data if provided
            if input_data is not None:
                process.stdin.write(input_data)
                process.stdin.close()

            # Wait for the process to complete
            stdout_data, stderr_data = process.communicate(timeout=timeout)

            # Calculate duration
            duration = time.time() - start_time

            # Update process status
            with self._process_lock:
                if process_id in self._processes:
                    self._processes[process_id].update({
                        "status": "completed",
                        "returncode": process.returncode,
                        "duration": duration,
                    })

            # Prepare result
            result = {
                "returncode": process.returncode,
                "stdout": stdout_data if capture_output else None,
                "stderr": stderr_data if capture_output else None,
                "pid": process.pid,
                "command": cmd,
                "duration": duration,
                "process_id": process_id,
            }

            # Call callback if provided
            if callback is not None:
                try:
                    callback(result)
                except Exception as e:
                    self.logger.error(f"Error in process callback: {str(e)}", process_id=process_id)

            # Log completion
            self.logger.debug(
                f"Process completed with return code {process.returncode}",
                process_id=process_id,
                duration=duration,
                returncode=process.returncode,
            )

            return result

        except subprocess.TimeoutExpired:
            # Process timed out
            self.terminate_process(process_id)

            # Update process status
            with self._process_lock:
                if process_id in self._processes:
                    self._processes[process_id].update({
                        "status": "timeout",
                        "duration": time.time() - start_time,
                    })

            # Log timeout
            self.logger.warning(
                f"Process timed out after {timeout} seconds",
                process_id=process_id,
                timeout=timeout,
            )

            raise ProcessError(
                f"Process timed out after {timeout} seconds",
                severity=ErrorSeverity.WARNING,
                details={
                    "process_id": process_id,
                    "command": cmd,
                    "timeout": timeout,
                }
            )

        except Exception as e:
            # Process failed to start or other error
            # Update process status
            with self._process_lock:
                if process_id in self._processes:
                    self._processes[process_id].update({
                        "status": "error",
                        "error": str(e),
                        "duration": time.time() - start_time,
                    })

            # Log error
            self.logger.error(
                f"Process error: {str(e)}",
                process_id=process_id,
                error=str(e),
            )

            raise ProcessError(
                f"Process error: {str(e)}",
                severity=ErrorSeverity.ERROR,
                original_exception=e,
                details={
                    "process_id": process_id,
                    "command": cmd,
                }
            )

    @with_error_handling
    def run_process_async(self, cmd: List[str], shell: bool = False,
                         cwd: Optional[Union[str, Path]] = None,
                         env: Optional[Dict[str, str]] = None,
                         input_data: Optional[str] = None,
                         process_id: Optional[str] = None,
                         callback: Optional[Callable] = None) -> str:
        """
        Run a process asynchronously.

        Args:
            cmd: Command to run as a list of strings
            shell: Whether to run the command in a shell
            cwd: Working directory for the command
            env: Environment variables for the command
            input_data: Input data to pass to the process
            process_id: Optional ID for the process (auto-generated if None)
            callback: Optional callback function to call when the process completes

        Returns:
            Process ID that can be used to check status or terminate the process
        """
        # Generate process ID if not provided
        if process_id is None:
            process_id = str(uuid.uuid4())

        # Normalize working directory if provided
        if cwd is not None:
            cwd = str(normalize_path(cwd))

        # Log the command
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
        self.logger.debug(f"Starting async process: {cmd_str}", process_id=process_id)

        # Start timing
        start_time = time.time()

        try:
            # Start the process
            process = subprocess.Popen(
                cmd,
                shell=shell,
                cwd=cwd,
                env=env,
                stdin=subprocess.PIPE if input_data is not None else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                universal_newlines=True,
                bufsize=1,  # Line buffered
            )

            # Store the process
            with self._process_lock:
                self._processes[process_id] = {
                    "process": process,
                    "command": cmd,
                    "start_time": start_time,
                    "status": "running",
                    "pid": process.pid,
                    "callback": callback,
                }

            # Send input data if provided
            if input_data is not None:
                process.stdin.write(input_data)
                process.stdin.close()

            # Start a thread to monitor the process
            threading.Thread(
                target=self._monitor_process,
                args=(process_id, process),
                daemon=True,
            ).start()

            return process_id

        except Exception as e:
            # Process failed to start or other error
            # Update process status
            with self._process_lock:
                if process_id in self._processes:
                    self._processes[process_id].update({
                        "status": "error",
                        "error": str(e),
                        "duration": time.time() - start_time,
                    })

            # Log error
            self.logger.error(
                f"Process error: {str(e)}",
                process_id=process_id,
                error=str(e),
            )

            raise ProcessError(
                f"Process error: {str(e)}",
                severity=ErrorSeverity.ERROR,
                original_exception=e,
                details={
                    "process_id": process_id,
                    "command": cmd,
                }
            )

    def _monitor_process(self, process_id: str, process: subprocess.Popen):
        """
        Monitor a process and update its status when it completes.

        Args:
            process_id: ID of the process to monitor
            process: Process object to monitor
        """
        try:
            # Wait for the process to complete
            stdout_data, stderr_data = process.communicate()

            # Calculate duration
            with self._process_lock:
                if process_id in self._processes:
                    start_time = self._processes[process_id]["start_time"]
                    duration = time.time() - start_time
                    callback = self._processes[process_id].get("callback")

                    # Update process status
                    self._processes[process_id].update({
                        "status": "completed",
                        "returncode": process.returncode,
                        "duration": duration,
                        "stdout": stdout_data,
                        "stderr": stderr_data,
                    })
                else:
                    # Process not found
                    return

            # Prepare result
            result = {
                "returncode": process.returncode,
                "stdout": stdout_data,
                "stderr": stderr_data,
                "pid": process.pid,
                "command": self._processes[process_id]["command"],
                "duration": duration,
                "process_id": process_id,
            }

            # Call callback if provided
            if callback is not None:
                try:
                    callback(result)
                except Exception as e:
                    self.logger.error(f"Error in process callback: {str(e)}", process_id=process_id)

            # Log completion
            self.logger.debug(
                f"Async process completed with return code {process.returncode}",
                process_id=process_id,
                duration=duration,
                returncode=process.returncode,
            )

        except Exception as e:
            # Error monitoring process
            with self._process_lock:
                if process_id in self._processes:
                    self._processes[process_id].update({
                        "status": "error",
                        "error": str(e),
                    })

            # Log error
            self.logger.error(
                f"Error monitoring process: {str(e)}",
                process_id=process_id,
                error=str(e),
            )

    @with_error_handling
    def terminate_process(self, process_id: str, timeout: float = 5.0) -> bool:
        """
        Terminate a process.

        Args:
            process_id: ID of the process to terminate
            timeout: Timeout in seconds to wait for graceful termination

        Returns:
            True if the process was terminated, False if it was not found
        """
        with self._process_lock:
            if process_id not in self._processes:
                return False

            process_info = self._processes[process_id]
            process = process_info["process"]

            # Check if the process is still running
            if process.poll() is not None:
                # Process already completed
                return True

            # Try to terminate gracefully
            self.logger.debug(f"Terminating process {process_id}", process_id=process_id)
            process.terminate()

            # Wait for the process to terminate
            try:
                process.wait(timeout=timeout)
                self.logger.debug(f"Process {process_id} terminated gracefully", process_id=process_id)

                # Update process status
                process_info.update({
                    "status": "terminated",
                    "duration": time.time() - process_info["start_time"],
                })

                return True

            except subprocess.TimeoutExpired:
                # Process did not terminate gracefully, kill it
                self.logger.warning(
                    f"Process {process_id} did not terminate gracefully, killing",
                    process_id=process_id,
                )
                process.kill()

                # Wait for the process to be killed
                process.wait()

                # Update process status
                process_info.update({
                    "status": "killed",
                    "duration": time.time() - process_info["start_time"],
                })

                return True

    @with_error_handling
    def get_process_status(self, process_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a process.

        Args:
            process_id: ID of the process to check

        Returns:
            Dict with process status information or None if not found
        """
        with self._process_lock:
            if process_id not in self._processes:
                return None

            process_info = self._processes[process_id].copy()

            # Remove the process object from the copy
            if "process" in process_info:
                del process_info["process"]

            # Remove the callback from the copy
            if "callback" in process_info:
                del process_info["callback"]

            return process_info

    @with_error_handling
    def list_processes(self) -> List[Dict[str, Any]]:
        """
        List all active processes.

        Returns:
            List of dicts with process information
        """
        with self._process_lock:
            result = []

            for process_id, process_info in self._processes.items():
                # Create a copy of the process info
                info = process_info.copy()

                # Remove the process object from the copy
                if "process" in info:
                    del info["process"]

                # Remove the callback from the copy
                if "callback" in info:
                    del info["callback"]

                # Add the process ID
                info["process_id"] = process_id

                result.append(info)

            return result

    @with_error_handling
    def cleanup_processes(self) -> int:
        """
        Clean up completed processes.

        Returns:
            Number of processes cleaned up
        """
        with self._process_lock:
            to_remove = []

            for process_id, process_info in self._processes.items():
                status = process_info.get("status")

                if status in ["completed", "terminated", "killed", "error"]:
                    to_remove.append(process_id)

            # Remove completed processes
            for process_id in to_remove:
                del self._processes[process_id]

            return len(to_remove)

    @with_error_handling
    def terminate_all_processes(self, timeout: float = 5.0) -> int:
        """
        Terminate all active processes.

        Args:
            timeout: Timeout in seconds to wait for graceful termination

        Returns:
            Number of processes terminated
        """
        with self._process_lock:
            count = 0

            for process_id in list(self._processes.keys()):
                if self.terminate_process(process_id, timeout):
                    count += 1

            return count

    @with_error_handling
    def create_process_pool(self, max_workers: int = None, executor_id: str = None) -> str:
        """
        Create a process pool executor.

        Args:
            max_workers: Maximum number of worker processes (default: CPU count)
            executor_id: Optional ID for the executor (auto-generated if None)

        Returns:
            Executor ID that can be used to submit tasks or shutdown the executor
        """
        # Generate executor ID if not provided
        if executor_id is None:
            executor_id = f"process_pool_{str(uuid.uuid4())}"

        # Create the executor
        executor = ProcessPoolExecutor(max_workers=max_workers)

        # Store the executor
        with self._executor_lock:
            self._executors[executor_id] = {
                "executor": executor,
                "type": "process",
                "max_workers": max_workers,
                "created_at": time.time(),
                "futures": {},
            }

        self.logger.debug(f"Created process pool executor: {executor_id}", executor_id=executor_id)
        return executor_id

    @with_error_handling
    def create_thread_pool(self, max_workers: int = None, executor_id: str = None) -> str:
        """
        Create a thread pool executor.

        Args:
            max_workers: Maximum number of worker threads (default: CPU count * 5)
            executor_id: Optional ID for the executor (auto-generated if None)

        Returns:
            Executor ID that can be used to submit tasks or shutdown the executor
        """
        # Generate executor ID if not provided
        if executor_id is None:
            executor_id = f"thread_pool_{str(uuid.uuid4())}"

        # Create the executor
        executor = ThreadPoolExecutor(max_workers=max_workers)

        # Store the executor
        with self._executor_lock:
            self._executors[executor_id] = {
                "executor": executor,
                "type": "thread",
                "max_workers": max_workers,
                "created_at": time.time(),
                "futures": {},
            }

        self.logger.debug(f"Created thread pool executor: {executor_id}", executor_id=executor_id)
        return executor_id

    @with_error_handling
    def get_default_process_pool(self) -> str:
        """
        Get the default process pool executor, creating it if necessary.

        Returns:
            Executor ID of the default process pool
        """
        with self._executor_lock:
            if self._default_process_executor is None:
                self._default_process_executor = self.create_process_pool(executor_id="default_process_pool")
            return self._default_process_executor

    @with_error_handling
    def get_default_thread_pool(self) -> str:
        """
        Get the default thread pool executor, creating it if necessary.

        Returns:
            Executor ID of the default thread pool
        """
        with self._executor_lock:
            if self._default_thread_executor is None:
                self._default_thread_executor = self.create_thread_pool(executor_id="default_thread_pool")
            return self._default_thread_executor

    @with_error_handling
    def submit_task(self, func: Callable, *args, executor_id: str = None, task_id: str = None, **kwargs) -> str:
        """
        Submit a task to an executor.

        Args:
            func: Function to execute
            *args: Arguments to pass to the function
            executor_id: ID of the executor to use (default: default process pool)
            task_id: Optional ID for the task (auto-generated if None)
            **kwargs: Keyword arguments to pass to the function

        Returns:
            Task ID that can be used to check status or get results
        """
        # Generate task ID if not provided
        if task_id is None:
            task_id = str(uuid.uuid4())

        # Get the executor ID if not provided
        if executor_id is None:
            executor_id = self.get_default_process_pool()

        # Get the executor
        with self._executor_lock:
            if executor_id not in self._executors:
                raise ProcessError(
                    f"Executor not found: {executor_id}",
                    severity=ErrorSeverity.ERROR,
                    details={"executor_id": executor_id}
                )

            executor_info = self._executors[executor_id]
            executor = executor_info["executor"]

            # Submit the task
            future = executor.submit(func, *args, **kwargs)

            # Store the future
            executor_info["futures"][task_id] = {
                "future": future,
                "function": func.__name__,
                "submitted_at": time.time(),
                "status": "pending",
            }

            # Store a reference in the global futures dict
            self._futures[task_id] = {
                "executor_id": executor_id,
                "function": func.__name__,
                "submitted_at": time.time(),
                "status": "pending",
            }

            # Add a callback to update the status when the task completes
            future.add_done_callback(lambda f: self._task_done_callback(task_id, f))

        self.logger.debug(
            f"Submitted task {task_id} to executor {executor_id}",
            task_id=task_id,
            executor_id=executor_id,
            function=func.__name__,
        )

        return task_id

    def _task_done_callback(self, task_id: str, future: Future):
        """
        Callback for when a task completes.

        Args:
            task_id: ID of the task
            future: Future object for the task
        """
        with self._executor_lock:
            # Update the global futures dict
            if task_id in self._futures:
                status = "completed"
                error = None

                try:
                    # Check if the task raised an exception
                    if future.exception() is not None:
                        status = "error"
                        error = str(future.exception())
                except (CancelledError, TimeoutError):
                    # Task was cancelled or timed out
                    status = "cancelled"

                # Update the status
                self._futures[task_id].update({
                    "status": status,
                    "completed_at": time.time(),
                    "duration": time.time() - self._futures[task_id]["submitted_at"],
                })

                if error is not None:
                    self._futures[task_id]["error"] = error

                # Get the executor ID
                executor_id = self._futures[task_id]["executor_id"]

                # Update the executor's futures dict
                if executor_id in self._executors and task_id in self._executors[executor_id]["futures"]:
                    self._executors[executor_id]["futures"][task_id].update({
                        "status": status,
                        "completed_at": time.time(),
                        "duration": time.time() - self._executors[executor_id]["futures"][task_id]["submitted_at"],
                    })

                    if error is not None:
                        self._executors[executor_id]["futures"][task_id]["error"] = error

    @with_error_handling
    def get_task_result(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """
        Get the result of a task.

        Args:
            task_id: ID of the task
            timeout: Timeout in seconds to wait for the result

        Returns:
            Result of the task

        Raises:
            ProcessError: If the task failed or timed out
        """
        with self._executor_lock:
            if task_id not in self._futures:
                raise ProcessError(
                    f"Task not found: {task_id}",
                    severity=ErrorSeverity.ERROR,
                    details={"task_id": task_id}
                )

            # Get the executor ID
            executor_id = self._futures[task_id]["executor_id"]

            # Get the executor
            if executor_id not in self._executors:
                raise ProcessError(
                    f"Executor not found: {executor_id}",
                    severity=ErrorSeverity.ERROR,
                    details={"executor_id": executor_id, "task_id": task_id}
                )

            # Get the future
            future = self._executors[executor_id]["futures"][task_id]["future"]

        try:
            # Get the result
            return future.result(timeout=timeout)
        except TimeoutError:
            raise ProcessError(
                f"Task timed out: {task_id}",
                severity=ErrorSeverity.WARNING,
                details={"task_id": task_id, "timeout": timeout}
            )
        except CancelledError:
            raise ProcessError(
                f"Task was cancelled: {task_id}",
                severity=ErrorSeverity.WARNING,
                details={"task_id": task_id}
            )
        except Exception as e:
            raise ProcessError(
                f"Task failed: {task_id}",
                severity=ErrorSeverity.ERROR,
                original_exception=e,
                details={"task_id": task_id}
            )

    @with_error_handling
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a task.

        Args:
            task_id: ID of the task

        Returns:
            Dict with task status information or None if not found
        """
        with self._executor_lock:
            if task_id not in self._futures:
                return None

            # Get a copy of the task info
            task_info = self._futures[task_id].copy()

            # Get the executor ID
            executor_id = task_info["executor_id"]

            # Get the executor
            if executor_id in self._executors and task_id in self._executors[executor_id]["futures"]:
                # Get the future
                future = self._executors[executor_id]["futures"][task_id]["future"]

                # Update the status if needed
                if future.done():
                    if future.cancelled():
                        task_info["status"] = "cancelled"
                    else:
                        try:
                            # Check if the task raised an exception
                            if future.exception() is not None:
                                task_info["status"] = "error"
                                task_info["error"] = str(future.exception())
                            else:
                                task_info["status"] = "completed"
                        except (CancelledError, TimeoutError):
                            # Task was cancelled or timed out
                            task_info["status"] = "cancelled"
                else:
                    task_info["status"] = "running"

            return task_info

    @with_error_handling
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task.

        Args:
            task_id: ID of the task to cancel

        Returns:
            True if the task was cancelled, False if it was not found or already completed
        """
        with self._executor_lock:
            if task_id not in self._futures:
                return False

            # Get the executor ID
            executor_id = self._futures[task_id]["executor_id"]

            # Get the executor
            if executor_id not in self._executors or task_id not in self._executors[executor_id]["futures"]:
                return False

            # Get the future
            future = self._executors[executor_id]["futures"][task_id]["future"]

            # Cancel the future
            if future.cancel():
                # Update the status
                self._futures[task_id]["status"] = "cancelled"
                self._futures[task_id]["completed_at"] = time.time()
                self._futures[task_id]["duration"] = time.time() - self._futures[task_id]["submitted_at"]

                self._executors[executor_id]["futures"][task_id]["status"] = "cancelled"
                self._executors[executor_id]["futures"][task_id]["completed_at"] = time.time()
                self._executors[executor_id]["futures"][task_id]["duration"] = time.time() - self._executors[executor_id]["futures"][task_id]["submitted_at"]

                self.logger.debug(f"Cancelled task {task_id}", task_id=task_id)
                return True
            else:
                # Task could not be cancelled (already running or completed)
                return False

    @with_error_handling
    def shutdown_executor(self, executor_id: str, wait: bool = True) -> bool:
        """
        Shutdown an executor.

        Args:
            executor_id: ID of the executor to shutdown
            wait: Whether to wait for pending tasks to complete

        Returns:
            True if the executor was shutdown, False if it was not found
        """
        with self._executor_lock:
            if executor_id not in self._executors:
                return False

            # Get the executor
            executor_info = self._executors[executor_id]
            executor = executor_info["executor"]

            # Shutdown the executor
            executor.shutdown(wait=wait)

            # Update the status of all tasks
            for task_id, task_info in executor_info["futures"].items():
                if task_info["status"] == "pending" or task_info["status"] == "running":
                    task_info["status"] = "cancelled"
                    task_info["completed_at"] = time.time()
                    task_info["duration"] = time.time() - task_info["submitted_at"]

                    # Update the global futures dict
                    if task_id in self._futures:
                        self._futures[task_id]["status"] = "cancelled"
                        self._futures[task_id]["completed_at"] = time.time()
                        self._futures[task_id]["duration"] = time.time() - self._futures[task_id]["submitted_at"]

            # Remove the executor
            del self._executors[executor_id]

            # Reset default executor if needed
            if executor_id == self._default_process_executor:
                self._default_process_executor = None
            elif executor_id == self._default_thread_executor:
                self._default_thread_executor = None

            self.logger.debug(f"Shutdown executor {executor_id}", executor_id=executor_id)
            return True

    @with_error_handling
    def list_executors(self) -> List[Dict[str, Any]]:
        """
        List all executors.

        Returns:
            List of dicts with executor information
        """
        with self._executor_lock:
            result = []

            for executor_id, executor_info in self._executors.items():
                # Create a copy of the executor info
                info = {
                    "executor_id": executor_id,
                    "type": executor_info["type"],
                    "max_workers": executor_info["max_workers"],
                    "created_at": executor_info["created_at"],
                    "task_count": len(executor_info["futures"]),
                }

                # Count tasks by status
                status_counts = {}
                for task_info in executor_info["futures"].values():
                    status = task_info["status"]
                    status_counts[status] = status_counts.get(status, 0) + 1

                info["status_counts"] = status_counts

                result.append(info)

            return result

    # Inter-Process Communication (IPC) Methods

    @with_error_handling
    def create_queue(self, queue_id: str = None, maxsize: int = 0) -> str:
        """
        Create a queue for inter-process communication.

        Args:
            queue_id: Optional ID for the queue (auto-generated if None)
            maxsize: Maximum size of the queue (0 means unlimited)

        Returns:
            Queue ID that can be used to put and get items
        """
        # Generate queue ID if not provided
        if queue_id is None:
            queue_id = f"queue_{str(uuid.uuid4())}"

        # Create the queue
        queue = self._manager.Queue(maxsize=maxsize)

        # Store the queue
        with self._queue_lock:
            self._queues[queue_id] = {
                "queue": queue,
                "created_at": time.time(),
                "maxsize": maxsize,
            }

        self.logger.debug(f"Created queue: {queue_id}", queue_id=queue_id)
        return queue_id

    @with_error_handling
    def put_queue_item(self, queue_id: str, item: Any, block: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Put an item in a queue.

        Args:
            queue_id: ID of the queue
            item: Item to put in the queue
            block: Whether to block if the queue is full
            timeout: Timeout in seconds if blocking

        Returns:
            True if the item was put in the queue, False if the queue is full and not blocking

        Raises:
            ProcessError: If the queue is not found or the operation times out
        """
        with self._queue_lock:
            if queue_id not in self._queues:
                raise ProcessError(
                    f"Queue not found: {queue_id}",
                    severity=ErrorSeverity.ERROR,
                    details={"queue_id": queue_id}
                )

            queue = self._queues[queue_id]["queue"]

        try:
            # Try to pickle the item to ensure it's serializable
            pickle.dumps(item)

            # Put the item in the queue
            queue.put(item, block=block, timeout=timeout)
            return True
        except pickle.PickleError as e:
            raise ProcessError(
                f"Item is not serializable: {str(e)}",
                severity=ErrorSeverity.ERROR,
                original_exception=e,
                details={"queue_id": queue_id}
            )
        except TimeoutError:
            raise ProcessError(
                f"Timed out putting item in queue: {queue_id}",
                severity=ErrorSeverity.WARNING,
                details={"queue_id": queue_id, "timeout": timeout}
            )
        except Exception as e:
            if not block and str(e).startswith("Full"):
                # Queue is full and not blocking
                return False

            raise ProcessError(
                f"Error putting item in queue: {str(e)}",
                severity=ErrorSeverity.ERROR,
                original_exception=e,
                details={"queue_id": queue_id}
            )

    @with_error_handling
    def get_queue_item(self, queue_id: str, block: bool = True, timeout: Optional[float] = None) -> Any:
        """
        Get an item from a queue.

        Args:
            queue_id: ID of the queue
            block: Whether to block if the queue is empty
            timeout: Timeout in seconds if blocking

        Returns:
            Item from the queue

        Raises:
            ProcessError: If the queue is not found, empty, or the operation times out
        """
        with self._queue_lock:
            if queue_id not in self._queues:
                raise ProcessError(
                    f"Queue not found: {queue_id}",
                    severity=ErrorSeverity.ERROR,
                    details={"queue_id": queue_id}
                )

            queue = self._queues[queue_id]["queue"]

        try:
            # Get an item from the queue
            return queue.get(block=block, timeout=timeout)
        except TimeoutError:
            raise ProcessError(
                f"Timed out getting item from queue: {queue_id}",
                severity=ErrorSeverity.WARNING,
                details={"queue_id": queue_id, "timeout": timeout}
            )
        except Exception as e:
            if not block and str(e).startswith("Empty"):
                # Queue is empty and not blocking
                raise ProcessError(
                    f"Queue is empty: {queue_id}",
                    severity=ErrorSeverity.WARNING,
                    details={"queue_id": queue_id}
                )

            raise ProcessError(
                f"Error getting item from queue: {str(e)}",
                severity=ErrorSeverity.ERROR,
                original_exception=e,
                details={"queue_id": queue_id}
            )

    @with_error_handling
    def get_queue_size(self, queue_id: str) -> int:
        """
        Get the size of a queue.

        Args:
            queue_id: ID of the queue

        Returns:
            Size of the queue

        Raises:
            ProcessError: If the queue is not found
        """
        with self._queue_lock:
            if queue_id not in self._queues:
                raise ProcessError(
                    f"Queue not found: {queue_id}",
                    severity=ErrorSeverity.ERROR,
                    details={"queue_id": queue_id}
                )

            queue = self._queues[queue_id]["queue"]

        return queue.qsize()

    @with_error_handling
    def is_queue_empty(self, queue_id: str) -> bool:
        """
        Check if a queue is empty.

        Args:
            queue_id: ID of the queue

        Returns:
            True if the queue is empty, False otherwise

        Raises:
            ProcessError: If the queue is not found
        """
        with self._queue_lock:
            if queue_id not in self._queues:
                raise ProcessError(
                    f"Queue not found: {queue_id}",
                    severity=ErrorSeverity.ERROR,
                    details={"queue_id": queue_id}
                )

            queue = self._queues[queue_id]["queue"]

        return queue.empty()

    @with_error_handling
    def is_queue_full(self, queue_id: str) -> bool:
        """
        Check if a queue is full.

        Args:
            queue_id: ID of the queue

        Returns:
            True if the queue is full, False otherwise

        Raises:
            ProcessError: If the queue is not found
        """
        with self._queue_lock:
            if queue_id not in self._queues:
                raise ProcessError(
                    f"Queue not found: {queue_id}",
                    severity=ErrorSeverity.ERROR,
                    details={"queue_id": queue_id}
                )

            queue = self._queues[queue_id]["queue"]

        return queue.full()

    @with_error_handling
    def clear_queue(self, queue_id: str) -> int:
        """
        Clear all items from a queue.

        Args:
            queue_id: ID of the queue

        Returns:
            Number of items removed from the queue

        Raises:
            ProcessError: If the queue is not found
        """
        with self._queue_lock:
            if queue_id not in self._queues:
                raise ProcessError(
                    f"Queue not found: {queue_id}",
                    severity=ErrorSeverity.ERROR,
                    details={"queue_id": queue_id}
                )

            queue = self._queues[queue_id]["queue"]

        # Get the current size
        size = queue.qsize()

        # Clear the queue
        while not queue.empty():
            try:
                queue.get(block=False)
            except:
                pass

        return size

    @with_error_handling
    def delete_queue(self, queue_id: str) -> bool:
        """
        Delete a queue.

        Args:
            queue_id: ID of the queue

        Returns:
            True if the queue was deleted, False if it was not found
        """
        with self._queue_lock:
            if queue_id not in self._queues:
                return False

            # Clear the queue
            queue = self._queues[queue_id]["queue"]
            while not queue.empty():
                try:
                    queue.get(block=False)
                except:
                    pass

            # Remove the queue
            del self._queues[queue_id]

        self.logger.debug(f"Deleted queue: {queue_id}", queue_id=queue_id)
        return True

    @with_error_handling
    def list_queues(self) -> List[Dict[str, Any]]:
        """
        List all queues.

        Returns:
            List of dicts with queue information
        """
        with self._queue_lock:
            result = []

            for queue_id, queue_info in self._queues.items():
                # Create a copy of the queue info
                info = {
                    "queue_id": queue_id,
                    "created_at": queue_info["created_at"],
                    "maxsize": queue_info["maxsize"],
                }

                # Add current size
                try:
                    info["size"] = queue_info["queue"].qsize()
                    info["empty"] = queue_info["queue"].empty()
                    info["full"] = queue_info["queue"].full()
                except:
                    info["size"] = "unknown"
                    info["empty"] = "unknown"
                    info["full"] = "unknown"

                result.append(info)

            return result

    @with_error_handling
    def create_shared_value(self, value_id: str = None, value_type: str = "i", initial_value: Any = 0) -> str:
        """
        Create a shared value for inter-process communication.

        Args:
            value_id: Optional ID for the value (auto-generated if None)
            value_type: Type of the value ('i' for int, 'd' for double, 'b' for bool)
            initial_value: Initial value

        Returns:
            Value ID that can be used to get and set the value
        """
        # Generate value ID if not provided
        if value_id is None:
            value_id = f"value_{str(uuid.uuid4())}"

        # Create the shared value
        shared_value = SharedValue(value_type, initial_value)

        # Store the shared value
        with self._queue_lock:
            self._queues[value_id] = {
                "value": shared_value,
                "type": "shared_value",
                "value_type": value_type,
                "created_at": time.time(),
            }

        self.logger.debug(f"Created shared value: {value_id}", value_id=value_id)
        return value_id

    @with_error_handling
    def get_shared_value(self, value_id: str) -> Any:
        """
        Get a shared value.

        Args:
            value_id: ID of the shared value

        Returns:
            Current value

        Raises:
            ProcessError: If the shared value is not found
        """
        with self._queue_lock:
            if value_id not in self._queues or self._queues[value_id].get("type") != "shared_value":
                raise ProcessError(
                    f"Shared value not found: {value_id}",
                    severity=ErrorSeverity.ERROR,
                    details={"value_id": value_id}
                )

            shared_value = self._queues[value_id]["value"]

        return shared_value.value

    @with_error_handling
    def set_shared_value(self, value_id: str, value: Any) -> None:
        """
        Set a shared value.

        Args:
            value_id: ID of the shared value
            value: New value

        Raises:
            ProcessError: If the shared value is not found
        """
        with self._queue_lock:
            if value_id not in self._queues or self._queues[value_id].get("type") != "shared_value":
                raise ProcessError(
                    f"Shared value not found: {value_id}",
                    severity=ErrorSeverity.ERROR,
                    details={"value_id": value_id}
                )

            shared_value = self._queues[value_id]["value"]

        shared_value.value = value

    @with_error_handling
    def create_event(self, event_id: str = None) -> str:
        """
        Create an event for inter-process synchronization.

        Args:
            event_id: Optional ID for the event (auto-generated if None)

        Returns:
            Event ID that can be used to set, clear, and wait for the event
        """
        # Generate event ID if not provided
        if event_id is None:
            event_id = f"event_{str(uuid.uuid4())}"

        # Create the event
        event = Event()

        # Store the event
        with self._queue_lock:
            self._queues[event_id] = {
                "event": event,
                "type": "event",
                "created_at": time.time(),
            }

        self.logger.debug(f"Created event: {event_id}", event_id=event_id)
        return event_id

    @with_error_handling
    def set_event(self, event_id: str) -> None:
        """
        Set an event.

        Args:
            event_id: ID of the event

        Raises:
            ProcessError: If the event is not found
        """
        with self._queue_lock:
            if event_id not in self._queues or self._queues[event_id].get("type") != "event":
                raise ProcessError(
                    f"Event not found: {event_id}",
                    severity=ErrorSeverity.ERROR,
                    details={"event_id": event_id}
                )

            event = self._queues[event_id]["event"]

        event.set()

    @with_error_handling
    def clear_event(self, event_id: str) -> None:
        """
        Clear an event.

        Args:
            event_id: ID of the event

        Raises:
            ProcessError: If the event is not found
        """
        with self._queue_lock:
            if event_id not in self._queues or self._queues[event_id].get("type") != "event":
                raise ProcessError(
                    f"Event not found: {event_id}",
                    severity=ErrorSeverity.ERROR,
                    details={"event_id": event_id}
                )

            event = self._queues[event_id]["event"]

        event.clear()

    @with_error_handling
    def wait_for_event(self, event_id: str, timeout: Optional[float] = None) -> bool:
        """
        Wait for an event to be set.

        Args:
            event_id: ID of the event
            timeout: Timeout in seconds

        Returns:
            True if the event was set, False if the timeout expired

        Raises:
            ProcessError: If the event is not found
        """
        with self._queue_lock:
            if event_id not in self._queues or self._queues[event_id].get("type") != "event":
                raise ProcessError(
                    f"Event not found: {event_id}",
                    severity=ErrorSeverity.ERROR,
                    details={"event_id": event_id}
                )

            event = self._queues[event_id]["event"]

        return event.wait(timeout=timeout)

    @with_error_handling
    def is_event_set(self, event_id: str) -> bool:
        """
        Check if an event is set.

        Args:
            event_id: ID of the event

        Returns:
            True if the event is set, False otherwise

        Raises:
            ProcessError: If the event is not found
        """
        with self._queue_lock:
            if event_id not in self._queues or self._queues[event_id].get("type") != "event":
                raise ProcessError(
                    f"Event not found: {event_id}",
                    severity=ErrorSeverity.ERROR,
                    details={"event_id": event_id}
                )

            event = self._queues[event_id]["event"]

        return event.is_set()

    @with_error_handling
    def create_lock(self, lock_id: str = None) -> str:
        """
        Create a lock for inter-process synchronization.

        Args:
            lock_id: Optional ID for the lock (auto-generated if None)

        Returns:
            Lock ID that can be used to acquire and release the lock
        """
        # Generate lock ID if not provided
        if lock_id is None:
            lock_id = f"lock_{str(uuid.uuid4())}"

        # Create the lock
        lock = ProcessLock()

        # Store the lock
        with self._queue_lock:
            self._queues[lock_id] = {
                "lock": lock,
                "type": "lock",
                "created_at": time.time(),
            }

        self.logger.debug(f"Created lock: {lock_id}", lock_id=lock_id)
        return lock_id

    @contextmanager
    def lock_context(self, lock_id: str, timeout: Optional[float] = None):
        """
        Context manager for acquiring and releasing a lock.

        Args:
            lock_id: ID of the lock
            timeout: Timeout in seconds

        Yields:
            None

        Raises:
            ProcessError: If the lock is not found or could not be acquired
        """
        # Acquire the lock
        acquired = self.acquire_lock(lock_id, timeout=timeout)

        if not acquired:
            raise ProcessError(
                f"Could not acquire lock: {lock_id}",
                severity=ErrorSeverity.WARNING,
                details={"lock_id": lock_id, "timeout": timeout}
            )

        try:
            # Yield control to the context block
            yield
        finally:
            # Release the lock
            self.release_lock(lock_id)

    @with_error_handling
    def acquire_lock(self, lock_id: str, timeout: Optional[float] = None) -> bool:
        """
        Acquire a lock.

        Args:
            lock_id: ID of the lock
            timeout: Timeout in seconds

        Returns:
            True if the lock was acquired, False if the timeout expired

        Raises:
            ProcessError: If the lock is not found
        """
        with self._queue_lock:
            if lock_id not in self._queues or self._queues[lock_id].get("type") != "lock":
                raise ProcessError(
                    f"Lock not found: {lock_id}",
                    severity=ErrorSeverity.ERROR,
                    details={"lock_id": lock_id}
                )

            lock = self._queues[lock_id]["lock"]

        return lock.acquire(timeout=timeout if timeout is not None else -1)

    @with_error_handling
    def release_lock(self, lock_id: str) -> None:
        """
        Release a lock.

        Args:
            lock_id: ID of the lock

        Raises:
            ProcessError: If the lock is not found
        """
        with self._queue_lock:
            if lock_id not in self._queues or self._queues[lock_id].get("type") != "lock":
                raise ProcessError(
                    f"Lock not found: {lock_id}",
                    severity=ErrorSeverity.ERROR,
                    details={"lock_id": lock_id}
                )

            lock = self._queues[lock_id]["lock"]

        try:
            lock.release()
        except ValueError:
            # Lock was not acquired
            pass


# Singleton instance
_process_manager = None


def get_process_manager() -> ProcessManager:
    """
    Get the singleton process manager instance.

    Returns:
        ProcessManager: The singleton process manager instance
    """
    global _process_manager
    if _process_manager is None:
        _process_manager = ProcessManager()
    return _process_manager


# Module-level functions for convenience

def run_process(cmd: List[str], shell: bool = False,
               cwd: Optional[Union[str, Path]] = None,
               env: Optional[Dict[str, str]] = None,
               input_data: Optional[str] = None,
               timeout: Optional[float] = None,
               capture_output: bool = True,
               process_id: Optional[str] = None,
               callback: Optional[Callable] = None) -> Dict[str, Any]:
    """
    Run a process and return its output.

    Args:
        cmd: Command to run as a list of strings
        shell: Whether to run the command in a shell
        cwd: Working directory for the command
        env: Environment variables for the command
        input_data: Input data to pass to the process
        timeout: Timeout in seconds
        capture_output: Whether to capture stdout and stderr
        process_id: Optional ID for the process (auto-generated if None)
        callback: Optional callback function to call when the process completes

    Returns:
        Dict with process information
    """
    return get_process_manager().run_process(
        cmd, shell, cwd, env, input_data, timeout, capture_output, process_id, callback
    )


def run_process_async(cmd: List[str], shell: bool = False,
                     cwd: Optional[Union[str, Path]] = None,
                     env: Optional[Dict[str, str]] = None,
                     input_data: Optional[str] = None,
                     process_id: Optional[str] = None,
                     callback: Optional[Callable] = None) -> str:
    """
    Run a process asynchronously.

    Args:
        cmd: Command to run as a list of strings
        shell: Whether to run the command in a shell
        cwd: Working directory for the command
        env: Environment variables for the command
        input_data: Input data to pass to the process
        process_id: Optional ID for the process (auto-generated if None)
        callback: Optional callback function to call when the process completes

    Returns:
        Process ID that can be used to check status or terminate the process
    """
    return get_process_manager().run_process_async(
        cmd, shell, cwd, env, input_data, process_id, callback
    )


def terminate_process(process_id: str, timeout: float = 5.0) -> bool:
    """
    Terminate a process.

    Args:
        process_id: ID of the process to terminate
        timeout: Timeout in seconds to wait for graceful termination

    Returns:
        True if the process was terminated, False if it was not found
    """
    return get_process_manager().terminate_process(process_id, timeout)


def get_process_status(process_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the status of a process.

    Args:
        process_id: ID of the process to check

    Returns:
        Dict with process status information or None if not found
    """
    return get_process_manager().get_process_status(process_id)


def list_processes() -> List[Dict[str, Any]]:
    """
    List all active processes.

    Returns:
        List of dicts with process information
    """
    return get_process_manager().list_processes()


def cleanup_processes() -> int:
    """
    Clean up completed processes.

    Returns:
        Number of processes cleaned up
    """
    return get_process_manager().cleanup_processes()


def terminate_all_processes(timeout: float = 5.0) -> int:
    """
    Terminate all active processes.

    Args:
        timeout: Timeout in seconds to wait for graceful termination

    Returns:
        Number of processes terminated
    """
    return get_process_manager().terminate_all_processes(timeout)


# Process Pool Management Functions

def create_process_pool(max_workers: int = None, executor_id: str = None) -> str:
    """
    Create a process pool executor.

    Args:
        max_workers: Maximum number of worker processes (default: CPU count)
        executor_id: Optional ID for the executor (auto-generated if None)

    Returns:
        Executor ID that can be used to submit tasks or shutdown the executor
    """
    return get_process_manager().create_process_pool(max_workers, executor_id)


def create_thread_pool(max_workers: int = None, executor_id: str = None) -> str:
    """
    Create a thread pool executor.

    Args:
        max_workers: Maximum number of worker threads (default: CPU count * 5)
        executor_id: Optional ID for the executor (auto-generated if None)

    Returns:
        Executor ID that can be used to submit tasks or shutdown the executor
    """
    return get_process_manager().create_thread_pool(max_workers, executor_id)


def get_default_process_pool() -> str:
    """
    Get the default process pool executor, creating it if necessary.

    Returns:
        Executor ID of the default process pool
    """
    return get_process_manager().get_default_process_pool()


def get_default_thread_pool() -> str:
    """
    Get the default thread pool executor, creating it if necessary.

    Returns:
        Executor ID of the default thread pool
    """
    return get_process_manager().get_default_thread_pool()


def submit_task(func: Callable, *args, executor_id: str = None, task_id: str = None, **kwargs) -> str:
    """
    Submit a task to an executor.

    Args:
        func: Function to execute
        *args: Arguments to pass to the function
        executor_id: ID of the executor to use (default: default process pool)
        task_id: Optional ID for the task (auto-generated if None)
        **kwargs: Keyword arguments to pass to the function

    Returns:
        Task ID that can be used to check status or get results
    """
    return get_process_manager().submit_task(func, *args, executor_id=executor_id, task_id=task_id, **kwargs)


def get_task_result(task_id: str, timeout: Optional[float] = None) -> Any:
    """
    Get the result of a task.

    Args:
        task_id: ID of the task
        timeout: Timeout in seconds to wait for the result

    Returns:
        Result of the task

    Raises:
        ProcessError: If the task failed or timed out
    """
    return get_process_manager().get_task_result(task_id, timeout)


def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the status of a task.

    Args:
        task_id: ID of the task

    Returns:
        Dict with task status information or None if not found
    """
    return get_process_manager().get_task_status(task_id)


def cancel_task(task_id: str) -> bool:
    """
    Cancel a task.

    Args:
        task_id: ID of the task to cancel

    Returns:
        True if the task was cancelled, False if it was not found or already completed
    """
    return get_process_manager().cancel_task(task_id)


def shutdown_executor(executor_id: str, wait: bool = True) -> bool:
    """
    Shutdown an executor.

    Args:
        executor_id: ID of the executor to shutdown
        wait: Whether to wait for pending tasks to complete

    Returns:
        True if the executor was shutdown, False if it was not found
    """
    return get_process_manager().shutdown_executor(executor_id, wait)


def list_executors() -> List[Dict[str, Any]]:
    """
    List all executors.

    Returns:
        List of dicts with executor information
    """
    return get_process_manager().list_executors()


# Inter-Process Communication (IPC) Functions

def create_queue(queue_id: str = None, maxsize: int = 0) -> str:
    """
    Create a queue for inter-process communication.

    Args:
        queue_id: Optional ID for the queue (auto-generated if None)
        maxsize: Maximum size of the queue (0 means unlimited)

    Returns:
        Queue ID that can be used to put and get items
    """
    return get_process_manager().create_queue(queue_id, maxsize)


def put_queue_item(queue_id: str, item: Any, block: bool = True, timeout: Optional[float] = None) -> bool:
    """
    Put an item in a queue.

    Args:
        queue_id: ID of the queue
        item: Item to put in the queue
        block: Whether to block if the queue is full
        timeout: Timeout in seconds if blocking

    Returns:
        True if the item was put in the queue, False if the queue is full and not blocking

    Raises:
        ProcessError: If the queue is not found or the operation times out
    """
    return get_process_manager().put_queue_item(queue_id, item, block, timeout)


def get_queue_item(queue_id: str, block: bool = True, timeout: Optional[float] = None) -> Any:
    """
    Get an item from a queue.

    Args:
        queue_id: ID of the queue
        block: Whether to block if the queue is empty
        timeout: Timeout in seconds if blocking

    Returns:
        Item from the queue

    Raises:
        ProcessError: If the queue is not found, empty, or the operation times out
    """
    return get_process_manager().get_queue_item(queue_id, block, timeout)


def get_queue_size(queue_id: str) -> int:
    """
    Get the size of a queue.

    Args:
        queue_id: ID of the queue

    Returns:
        Size of the queue

    Raises:
        ProcessError: If the queue is not found
    """
    return get_process_manager().get_queue_size(queue_id)


def is_queue_empty(queue_id: str) -> bool:
    """
    Check if a queue is empty.

    Args:
        queue_id: ID of the queue

    Returns:
        True if the queue is empty, False otherwise

    Raises:
        ProcessError: If the queue is not found
    """
    return get_process_manager().is_queue_empty(queue_id)


def is_queue_full(queue_id: str) -> bool:
    """
    Check if a queue is full.

    Args:
        queue_id: ID of the queue

    Returns:
        True if the queue is full, False otherwise

    Raises:
        ProcessError: If the queue is not found
    """
    return get_process_manager().is_queue_full(queue_id)


def clear_queue(queue_id: str) -> int:
    """
    Clear all items from a queue.

    Args:
        queue_id: ID of the queue

    Returns:
        Number of items removed from the queue

    Raises:
        ProcessError: If the queue is not found
    """
    return get_process_manager().clear_queue(queue_id)


def delete_queue(queue_id: str) -> bool:
    """
    Delete a queue.

    Args:
        queue_id: ID of the queue

    Returns:
        True if the queue was deleted, False if it was not found
    """
    return get_process_manager().delete_queue(queue_id)


def list_queues() -> List[Dict[str, Any]]:
    """
    List all queues.

    Returns:
        List of dicts with queue information
    """
    return get_process_manager().list_queues()


def create_shared_value(value_id: str = None, value_type: str = "i", initial_value: Any = 0) -> str:
    """
    Create a shared value for inter-process communication.

    Args:
        value_id: Optional ID for the value (auto-generated if None)
        value_type: Type of the value ('i' for int, 'd' for double, 'b' for bool)
        initial_value: Initial value

    Returns:
        Value ID that can be used to get and set the value
    """
    return get_process_manager().create_shared_value(value_id, value_type, initial_value)


def get_shared_value(value_id: str) -> Any:
    """
    Get a shared value.

    Args:
        value_id: ID of the shared value

    Returns:
        Current value

    Raises:
        ProcessError: If the shared value is not found
    """
    return get_process_manager().get_shared_value(value_id)


def set_shared_value(value_id: str, value: Any) -> None:
    """
    Set a shared value.

    Args:
        value_id: ID of the shared value
        value: New value

    Raises:
        ProcessError: If the shared value is not found
    """
    return get_process_manager().set_shared_value(value_id, value)


def create_event(event_id: str = None) -> str:
    """
    Create an event for inter-process synchronization.

    Args:
        event_id: Optional ID for the event (auto-generated if None)

    Returns:
        Event ID that can be used to set, clear, and wait for the event
    """
    return get_process_manager().create_event(event_id)


def set_event(event_id: str) -> None:
    """
    Set an event.

    Args:
        event_id: ID of the event

    Raises:
        ProcessError: If the event is not found
    """
    return get_process_manager().set_event(event_id)


def clear_event(event_id: str) -> None:
    """
    Clear an event.

    Args:
        event_id: ID of the event

    Raises:
        ProcessError: If the event is not found
    """
    return get_process_manager().clear_event(event_id)


def wait_for_event(event_id: str, timeout: Optional[float] = None) -> bool:
    """
    Wait for an event to be set.

    Args:
        event_id: ID of the event
        timeout: Timeout in seconds

    Returns:
        True if the event was set, False if the timeout expired

    Raises:
        ProcessError: If the event is not found
    """
    return get_process_manager().wait_for_event(event_id, timeout)


def is_event_set(event_id: str) -> bool:
    """
    Check if an event is set.

    Args:
        event_id: ID of the event

    Returns:
        True if the event is set, False otherwise

    Raises:
        ProcessError: If the event is not found
    """
    return get_process_manager().is_event_set(event_id)


def create_lock(lock_id: str = None) -> str:
    """
    Create a lock for inter-process synchronization.

    Args:
        lock_id: Optional ID for the lock (auto-generated if None)

    Returns:
        Lock ID that can be used to acquire and release the lock
    """
    return get_process_manager().create_lock(lock_id)


def acquire_lock(lock_id: str, timeout: Optional[float] = None) -> bool:
    """
    Acquire a lock.

    Args:
        lock_id: ID of the lock
        timeout: Timeout in seconds

    Returns:
        True if the lock was acquired, False if the timeout expired

    Raises:
        ProcessError: If the lock is not found
    """
    return get_process_manager().acquire_lock(lock_id, timeout)


def release_lock(lock_id: str) -> None:
    """
    Release a lock.

    Args:
        lock_id: ID of the lock

    Raises:
        ProcessError: If the lock is not found
    """
    return get_process_manager().release_lock(lock_id)


@contextmanager
def lock_context(lock_id: str, timeout: Optional[float] = None):
    """
    Context manager for acquiring and releasing a lock.

    Args:
        lock_id: ID of the lock
        timeout: Timeout in seconds

    Yields:
        None

    Raises:
        ProcessError: If the lock is not found or could not be acquired
    """
    with get_process_manager().lock_context(lock_id, timeout):
        yield
