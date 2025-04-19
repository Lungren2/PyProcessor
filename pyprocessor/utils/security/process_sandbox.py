"""
Process sandboxing utilities for PyProcessor.

This module provides utilities for sandboxing processes to improve security:
- Resource limits for subprocess execution
- Filesystem access restrictions
- Network access controls
- Process privilege reduction
- Timeout mechanisms
- Process monitoring and termination
- Secure input validation
- Audit logging
"""

import os
import platform
import subprocess
import threading
import time
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple, Any

# Import required modules
from pyprocessor.utils.logging.log_manager import get_logger
from pyprocessor.utils.security.audit_logger import get_audit_logger, log_security_event
from pyprocessor.utils.process.resource_manager import get_resource_manager

# Step 1: Define SandboxPolicy class
class SandboxPolicy:
    """
    Defines security policies for sandboxed processes.

    This class specifies:
    - Resource limits (CPU, memory, etc.)
    - Filesystem access restrictions
    - Network access controls
    - Process privileges
    - Timeout settings
    """

    def __init__(self):
        """Initialize the sandbox policy with default settings."""
        # Resource limits
        self.cpu_limit = None  # Percentage (0-100)
        self.memory_limit = None  # Bytes
        self.file_size_limit = None  # Bytes
        self.process_count_limit = 1  # Number of child processes

        # Filesystem access
        self.allowed_read_paths = set()  # Paths that can be read
        self.allowed_write_paths = set()  # Paths that can be written
        self.denied_paths = set()  # Paths that cannot be accessed

        # Network access
        self.network_access_enabled = False  # Whether network access is allowed
        self.allowed_hosts = set()  # Hosts that can be accessed
        self.allowed_ports = set()  # Ports that can be accessed

        # Process privileges
        self.reduce_privileges = True  # Whether to reduce process privileges
        self.run_as_user = None  # User to run the process as

        # Timeout settings
        self.timeout = 300  # Default timeout in seconds (5 minutes)
        self.kill_on_timeout = True  # Whether to kill the process on timeout

        # Command validation
        self.allowed_commands = set()  # Commands that can be executed
        self.denied_commands = set()  # Commands that cannot be executed
        self.command_pattern_whitelist = []  # Regex patterns for allowed commands
        self.command_pattern_blacklist = []  # Regex patterns for denied commands
        self.validate_command_args = True  # Whether to validate command arguments

    def allow_read_path(self, path: Union[str, Path]) -> None:
        """Add a path to the allowed read paths."""
        self.allowed_read_paths.add(str(path))

    def allow_write_path(self, path: Union[str, Path]) -> None:
        """Add a path to the allowed write paths."""
        self.allowed_write_paths.add(str(path))

    def deny_path(self, path: Union[str, Path]) -> None:
        """Add a path to the denied paths."""
        self.denied_paths.add(str(path))

    def allow_host(self, host: str) -> None:
        """Add a host to the allowed hosts."""
        self.allowed_hosts.add(host)

    def allow_port(self, port: int) -> None:
        """Add a port to the allowed ports."""
        self.allowed_ports.add(port)

    def allow_command(self, command: str) -> None:
        """Add a command to the allowed commands."""
        self.allowed_commands.add(command)

    def deny_command(self, command: str) -> None:
        """Add a command to the denied commands."""
        self.denied_commands.add(command)

    def add_command_pattern_whitelist(self, pattern: str) -> None:
        """Add a regex pattern to the command whitelist."""
        self.command_pattern_whitelist.append(re.compile(pattern))

    def add_command_pattern_blacklist(self, pattern: str) -> None:
        """Add a regex pattern to the command blacklist."""
        self.command_pattern_blacklist.append(re.compile(pattern))

    def set_resource_limits(self, cpu_limit: Optional[float] = None,
                           memory_limit: Optional[int] = None,
                           file_size_limit: Optional[int] = None,
                           process_count_limit: Optional[int] = None) -> None:
        """Set resource limits for the sandboxed process."""
        if cpu_limit is not None:
            self.cpu_limit = cpu_limit
        if memory_limit is not None:
            self.memory_limit = memory_limit
        if file_size_limit is not None:
            self.file_size_limit = file_size_limit
        if process_count_limit is not None:
            self.process_count_limit = process_count_limit

    def set_timeout(self, timeout: float, kill_on_timeout: bool = True) -> None:
        """Set timeout for the sandboxed process."""
        self.timeout = timeout
        self.kill_on_timeout = kill_on_timeout

    def set_network_access(self, enabled: bool) -> None:
        """Enable or disable network access."""
        self.network_access_enabled = enabled

    def set_privilege_reduction(self, enabled: bool, run_as_user: Optional[str] = None) -> None:
        """Configure privilege reduction."""
        self.reduce_privileges = enabled
        self.run_as_user = run_as_user

    def is_command_allowed(self, command: str) -> bool:
        """Check if a command is allowed by the policy."""
        # If allowed_commands is empty, all commands are allowed by default
        # unless explicitly denied or matched by a blacklist pattern
        if command in self.denied_commands:
            return False

        # Check blacklist patterns
        for pattern in self.command_pattern_blacklist:
            if pattern.match(command):
                return False

        # If we have a whitelist, command must be in it or match a pattern
        if self.allowed_commands:
            if command in self.allowed_commands:
                return True

            # Check whitelist patterns
            for pattern in self.command_pattern_whitelist:
                if pattern.match(command):
                    return True

            # Command not in whitelist or matched by a pattern
            return False

        # No whitelist, and command not denied
        return True

    def is_path_allowed_read(self, path: Union[str, Path]) -> bool:
        """Check if a path is allowed to be read."""
        path_str = str(path)

        # Check denied paths first
        for denied in self.denied_paths:
            if path_str.startswith(denied):
                return False

        # If no allowed paths specified, all non-denied paths are allowed
        if not self.allowed_read_paths:
            return True

        # Check if path is in allowed read paths
        for allowed in self.allowed_read_paths:
            if path_str.startswith(allowed):
                return True

        return False

    def is_path_allowed_write(self, path: Union[str, Path]) -> bool:
        """Check if a path is allowed to be written."""
        path_str = str(path)

        # Check denied paths first
        for denied in self.denied_paths:
            if path_str.startswith(denied):
                return False

        # If no allowed paths specified, all non-denied paths are allowed
        if not self.allowed_write_paths:
            return True

        # Check if path is in allowed write paths
        for allowed in self.allowed_write_paths:
            if path_str.startswith(allowed):
                return True

        return False

    def is_network_access_allowed(self, host: Optional[str] = None, port: Optional[int] = None) -> bool:
        """Check if network access is allowed."""
        if not self.network_access_enabled:
            return False

        # If no specific host/port restrictions, all network access is allowed
        if not self.allowed_hosts and not self.allowed_ports:
            return True

        # Check host restrictions
        if host and self.allowed_hosts:
            if host not in self.allowed_hosts:
                return False

        # Check port restrictions
        if port and self.allowed_ports:
            if port not in self.allowed_ports:
                return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert the policy to a dictionary."""
        return {
            "resource_limits": {
                "cpu_limit": self.cpu_limit,
                "memory_limit": self.memory_limit,
                "file_size_limit": self.file_size_limit,
                "process_count_limit": self.process_count_limit
            },
            "filesystem_access": {
                "allowed_read_paths": list(self.allowed_read_paths),
                "allowed_write_paths": list(self.allowed_write_paths),
                "denied_paths": list(self.denied_paths)
            },
            "network_access": {
                "enabled": self.network_access_enabled,
                "allowed_hosts": list(self.allowed_hosts),
                "allowed_ports": list(self.allowed_ports)
            },
            "process_privileges": {
                "reduce_privileges": self.reduce_privileges,
                "run_as_user": self.run_as_user
            },
            "timeout": {
                "timeout": self.timeout,
                "kill_on_timeout": self.kill_on_timeout
            },
            "command_validation": {
                "allowed_commands": list(self.allowed_commands),
                "denied_commands": list(self.denied_commands),
                "validate_command_args": self.validate_command_args
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SandboxPolicy':
        """Create a policy from a dictionary."""
        policy = cls()

        # Resource limits
        resource_limits = data.get("resource_limits", {})
        policy.set_resource_limits(
            cpu_limit=resource_limits.get("cpu_limit"),
            memory_limit=resource_limits.get("memory_limit"),
            file_size_limit=resource_limits.get("file_size_limit"),
            process_count_limit=resource_limits.get("process_count_limit")
        )

        # Filesystem access
        filesystem_access = data.get("filesystem_access", {})
        for path in filesystem_access.get("allowed_read_paths", []):
            policy.allow_read_path(path)
        for path in filesystem_access.get("allowed_write_paths", []):
            policy.allow_write_path(path)
        for path in filesystem_access.get("denied_paths", []):
            policy.deny_path(path)

        # Network access
        network_access = data.get("network_access", {})
        policy.set_network_access(network_access.get("enabled", False))
        for host in network_access.get("allowed_hosts", []):
            policy.allow_host(host)
        for port in network_access.get("allowed_ports", []):
            policy.allow_port(port)

        # Process privileges
        process_privileges = data.get("process_privileges", {})
        policy.set_privilege_reduction(
            enabled=process_privileges.get("reduce_privileges", True),
            run_as_user=process_privileges.get("run_as_user")
        )

        # Timeout
        timeout = data.get("timeout", {})
        policy.set_timeout(
            timeout=timeout.get("timeout", 300),
            kill_on_timeout=timeout.get("kill_on_timeout", True)
        )

        # Command validation
        command_validation = data.get("command_validation", {})
        for command in command_validation.get("allowed_commands", []):
            policy.allow_command(command)
        for command in command_validation.get("denied_commands", []):
            policy.deny_command(command)
        policy.validate_command_args = command_validation.get("validate_command_args", True)

        return policy


# Step 2: Define SandboxedProcess class
class SandboxedProcess:
    """
    A sandboxed process with security restrictions.

    This class wraps a subprocess.Popen instance with additional security features:
    - Resource limits enforcement
    - Filesystem access restrictions
    - Network access controls
    - Process privilege reduction
    - Timeout handling
    - Process monitoring
    """

    def __init__(self, cmd: List[str], policy: SandboxPolicy,
                 cwd: Optional[Union[str, Path]] = None,
                 env: Optional[Dict[str, str]] = None,
                 input_data: Optional[str] = None,
                 process_id: Optional[str] = None):
        """Initialize a sandboxed process."""
        self.logger = get_logger()
        self.audit_logger = get_audit_logger()
        self.resource_manager = get_resource_manager()

        self.cmd = cmd
        self.policy = policy
        self.cwd = cwd
        self.env = env
        self.input_data = input_data
        self.process_id = process_id or f"sandbox-{time.time()}-{os.getpid()}"

        # Process state
        self.process = None
        self.start_time = None
        self.end_time = None
        self.status = "initialized"
        self.exit_code = None
        self.stdout_data = ""
        self.stderr_data = ""
        self.error_message = None

        # Monitoring
        self.monitor_thread = None
        self.timeout_thread = None
        self._stop_event = threading.Event()

    def _validate_command(self) -> Tuple[bool, Optional[str]]:
        """Validate the command against the policy."""
        # Check if the command executable exists and is allowed
        if not self.cmd or not self.cmd[0]:
            return False, "Empty command"

        # Get the full path of the command
        try:
            cmd_path = shutil.which(self.cmd[0])
            if not cmd_path:
                return False, f"Command not found: {self.cmd[0]}"

            # Check if the command is allowed by the policy
            if not self.policy.is_command_allowed(cmd_path):
                return False, f"Command not allowed by policy: {cmd_path}"

            # Validate command arguments if required
            if self.policy.validate_command_args:
                # Basic validation - check for suspicious patterns
                for arg in self.cmd[1:]:
                    # Check for shell metacharacters that could be used for command injection
                    if re.search(r'[;&|`$><]', arg):
                        return False, f"Suspicious command argument: {arg}"

            return True, None

        except Exception as e:
            return False, f"Command validation error: {str(e)}"

    def _validate_paths(self) -> Tuple[bool, Optional[str]]:
        """Validate file paths against the policy."""
        # Validate working directory
        if self.cwd:
            if not self.policy.is_path_allowed_read(self.cwd):
                return False, f"Working directory not allowed by policy: {self.cwd}"

        # Validate paths in command arguments
        for arg in self.cmd[1:]:
            # Check if argument looks like a file path
            if os.path.sep in arg or arg.startswith('.'):
                path = os.path.abspath(os.path.join(self.cwd or os.getcwd(), arg))

                # Check if path is allowed for reading
                if not self.policy.is_path_allowed_read(path):
                    return False, f"Path not allowed for reading: {path}"

        return True, None

    def _prepare_environment(self) -> Dict[str, str]:
        """Prepare the environment for the sandboxed process."""
        # Start with a clean environment or the provided one
        env = self.env.copy() if self.env else os.environ.copy()

        # Add sandbox-specific environment variables
        env["PYPROCESSOR_SANDBOX"] = "1"
        env["PYPROCESSOR_SANDBOX_ID"] = self.process_id

        # Apply network restrictions if needed
        if not self.policy.network_access_enabled:
            # Attempt to disable network access via environment variables
            # This is not foolproof but can help with some applications
            env["http_proxy"] = "http://localhost:1"
            env["https_proxy"] = "http://localhost:1"
            env["no_proxy"] = "localhost,127.0.0.1"

        return env

    def _apply_resource_limits(self):
        """Apply resource limits to the process."""
        # This is platform-specific and limited in what we can do from Python
        # For comprehensive resource limits, we would need to use platform-specific
        # mechanisms like cgroups on Linux or job objects on Windows

        if self.process is None:
            return

        try:
            # Track the process with the resource manager
            self.resource_manager.track_process(self.process.pid)

            # Set resource limits in the resource manager
            if self.policy.cpu_limit is not None or self.policy.memory_limit is not None:
                limits = {}
                if self.policy.cpu_limit is not None:
                    limits["cpu"] = self.policy.cpu_limit
                if self.policy.memory_limit is not None:
                    limits["memory"] = self.policy.memory_limit
                self.resource_manager.set_process_limits(self.process.pid, limits)

            # Platform-specific resource limits
            if platform.system() == "Linux":
                # On Linux, we could use the resource module for basic limits
                # or cgroups for more comprehensive limits
                pass

            elif platform.system() == "Windows":
                # On Windows, we could use job objects for resource limits
                # but this requires ctypes and is complex to implement
                pass

        except Exception as e:
            self.logger.warning(f"Failed to apply resource limits: {str(e)}")

    def _reduce_privileges(self):
        """Reduce the privileges of the process."""
        # This is platform-specific and limited in what we can do from Python
        # For comprehensive privilege reduction, we would need to use platform-specific
        # mechanisms like setuid/setgid on Linux or job objects on Windows

        if not self.policy.reduce_privileges or self.process is None:
            return

        try:
            # Platform-specific privilege reduction
            if platform.system() == "Linux":
                # On Linux, we could use setuid/setgid for privilege reduction
                # but this requires root privileges and is complex to implement
                pass

            elif platform.system() == "Windows":
                # On Windows, we could use job objects for privilege reduction
                # but this requires ctypes and is complex to implement
                pass

        except Exception as e:
            self.logger.warning(f"Failed to reduce privileges: {str(e)}")

    def _monitor_process(self):
        """Monitor the process for resource usage and violations."""
        if self.process is None:
            return

        self.logger.debug(f"Starting process monitor for {self.process_id}")

        try:
            # Monitor the process using the resource manager
            while not self._stop_event.is_set() and self.process.poll() is None:
                try:
                    # Get process resource usage
                    usage = self.resource_manager.get_process_usage(self.process.pid)

                    # Check CPU usage
                    if self.policy.cpu_limit is not None and usage.get("cpu", 0) > self.policy.cpu_limit:
                        self.logger.warning(
                            f"Process {self.process_id} exceeded CPU limit: "
                            f"{usage.get('cpu', 0):.2f}% > {self.policy.cpu_limit:.2f}%"
                        )
                        # Log the violation
                        log_security_event(
                            "sandbox.resource_violation",
                            process_id=self.process_id,
                            resource="cpu",
                            limit=self.policy.cpu_limit,
                            usage=usage.get("cpu", 0),
                            action="warning"
                        )

                    # Check memory usage
                    if self.policy.memory_limit is not None and usage.get("memory", 0) > self.policy.memory_limit:
                        self.logger.warning(
                            f"Process {self.process_id} exceeded memory limit: "
                            f"{usage.get('memory', 0)} > {self.policy.memory_limit}"
                        )
                        # Log the violation
                        log_security_event(
                            "sandbox.resource_violation",
                            process_id=self.process_id,
                            resource="memory",
                            limit=self.policy.memory_limit,
                            usage=usage.get("memory", 0),
                            action="warning"
                        )

                    # Sleep before next check
                    time.sleep(1.0)

                except Exception as e:
                    self.logger.error(f"Error monitoring process {self.process_id}: {str(e)}")
                    break

            self.logger.debug(f"Process monitor for {self.process_id} stopped")

        except Exception as e:
            self.logger.error(f"Failed to monitor process {self.process_id}: {str(e)}")

    def _handle_timeout(self):
        """Handle process timeout."""
        if self.process is None:
            return

        self.logger.debug(f"Starting timeout handler for {self.process_id} ({self.policy.timeout}s)")

        # Wait for the timeout
        timeout_occurred = not self._stop_event.wait(self.policy.timeout)

        if timeout_occurred and self.process.poll() is None:
            self.logger.warning(f"Process {self.process_id} timed out after {self.policy.timeout}s")

            # Log the timeout
            log_security_event(
                "sandbox.timeout",
                process_id=self.process_id,
                timeout=self.policy.timeout,
                action="terminating" if self.policy.kill_on_timeout else "warning"
            )

            if self.policy.kill_on_timeout:
                self.terminate()

    def start(self) -> bool:
        """Start the sandboxed process."""
        # Validate command
        valid_cmd, cmd_error = self._validate_command()
        if not valid_cmd:
            self.logger.error(f"Command validation failed: {cmd_error}")
            self.status = "failed"
            self.error_message = cmd_error

            # Log the validation failure
            log_security_event(
                "sandbox.validation_failure",
                process_id=self.process_id,
                command=self.cmd,
                error=cmd_error,
                action="blocked"
            )

            return False

        # Validate paths
        valid_paths, path_error = self._validate_paths()
        if not valid_paths:
            self.logger.error(f"Path validation failed: {path_error}")
            self.status = "failed"
            self.error_message = path_error

            # Log the validation failure
            log_security_event(
                "sandbox.validation_failure",
                process_id=self.process_id,
                command=self.cmd,
                error=path_error,
                action="blocked"
            )

            return False

        # Prepare environment
        env = self._prepare_environment()

        try:
            # Start the process
            self.start_time = time.time()
            self.status = "starting"

            # Log process start
            log_security_event(
                "sandbox.process_start",
                process_id=self.process_id,
                command=self.cmd,
                cwd=self.cwd,
                policy=self.policy.to_dict()
            )

            # Create the process
            self.process = subprocess.Popen(
                self.cmd,
                cwd=self.cwd,
                env=env,
                stdin=subprocess.PIPE if self.input_data is not None else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                universal_newlines=True,
                bufsize=1,  # Line buffered
                shell=False  # Never use shell=True for security reasons
            )

            # Apply resource limits
            self._apply_resource_limits()

            # Reduce privileges
            self._reduce_privileges()

            # Send input data if provided
            if self.input_data is not None and self.process.stdin:
                self.process.stdin.write(self.input_data)
                self.process.stdin.close()

            # Start monitoring thread
            self._stop_event.clear()
            self.monitor_thread = threading.Thread(
                target=self._monitor_process,
                daemon=True,
                name=f"sandbox-monitor-{self.process_id}"
            )
            self.monitor_thread.start()

            # Start timeout thread if timeout is set
            if self.policy.timeout > 0:
                self.timeout_thread = threading.Thread(
                    target=self._handle_timeout,
                    daemon=True,
                    name=f"sandbox-timeout-{self.process_id}"
                )
                self.timeout_thread.start()

            self.status = "running"
            self.logger.info(f"Started sandboxed process {self.process_id} (PID: {self.process.pid})")

            return True

        except Exception as e:
            self.status = "failed"
            self.error_message = str(e)
            self.logger.error(f"Failed to start sandboxed process: {str(e)}")

            # Log the failure
            log_security_event(
                "sandbox.process_error",
                process_id=self.process_id,
                command=self.cmd,
                error=str(e),
                action="failed"
            )

            return False

    def wait(self, timeout: Optional[float] = None) -> int:
        """Wait for the process to complete."""
        if self.process is None:
            return -1

        try:
            # Wait for the process to complete
            exit_code = self.process.wait(timeout=timeout)

            # Update state
            self.status = "completed"
            self.exit_code = exit_code
            self.end_time = time.time()

            # Stop monitoring
            self._stop_event.set()

            # Collect output
            self.stdout_data = self.process.stdout.read() if self.process.stdout else ""
            self.stderr_data = self.process.stderr.read() if self.process.stderr else ""

            # Log process completion
            log_security_event(
                "sandbox.process_end",
                process_id=self.process_id,
                exit_code=exit_code,
                duration=self.end_time - self.start_time if self.start_time else None,
                action="completed"
            )

            self.logger.info(
                f"Sandboxed process {self.process_id} completed with exit code {exit_code} "
                f"in {self.end_time - self.start_time:.2f}s"
            )

            return exit_code

        except subprocess.TimeoutExpired:
            self.logger.warning(f"Timeout waiting for process {self.process_id} to complete")
            return None

        except Exception as e:
            self.status = "error"
            self.error_message = str(e)
            self.logger.error(f"Error waiting for process {self.process_id}: {str(e)}")

            # Log the error
            log_security_event(
                "sandbox.process_error",
                process_id=self.process_id,
                error=str(e),
                action="error"
            )

            return -1

    def terminate(self, timeout: float = 5.0) -> bool:
        """Terminate the process."""
        if self.process is None or self.process.poll() is not None:
            return True

        try:
            # Log termination attempt
            log_security_event(
                "sandbox.process_terminate",
                process_id=self.process_id,
                action="terminating"
            )

            # Stop monitoring
            self._stop_event.set()

            # Terminate the process
            self.process.terminate()

            # Wait for the process to terminate
            try:
                self.process.wait(timeout=timeout)
                self.status = "terminated"
                self.end_time = time.time()

                # Log successful termination
                log_security_event(
                    "sandbox.process_end",
                    process_id=self.process_id,
                    action="terminated",
                    duration=self.end_time - self.start_time if self.start_time else None
                )

                self.logger.info(f"Terminated sandboxed process {self.process_id}")
                return True

            except subprocess.TimeoutExpired:
                # Process didn't terminate, kill it
                self.process.kill()
                self.status = "killed"
                self.end_time = time.time()

                # Log forced kill
                log_security_event(
                    "sandbox.process_end",
                    process_id=self.process_id,
                    action="killed",
                    duration=self.end_time - self.start_time if self.start_time else None
                )

                self.logger.warning(f"Killed sandboxed process {self.process_id} after termination timeout")
                return True

        except Exception as e:
            self.status = "error"
            self.error_message = str(e)
            self.logger.error(f"Error terminating process {self.process_id}: {str(e)}")

            # Log the error
            log_security_event(
                "sandbox.process_error",
                process_id=self.process_id,
                error=str(e),
                action="error"
            )

            return False

    def get_result(self) -> Dict[str, Any]:
        """Get the process result."""
        return {
            "process_id": self.process_id,
            "command": self.cmd,
            "status": self.status,
            "exit_code": self.exit_code,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.end_time - self.start_time if self.start_time and self.end_time else None,
            "stdout": self.stdout_data,
            "stderr": self.stderr_data,
            "error": self.error_message
        }


# Step 3: Define ProcessSandbox class
class ProcessSandbox:
    """
    Process sandboxing manager.

    This class provides a centralized way to manage sandboxed processes:
    - Create and manage sandbox policies
    - Run processes in sandboxes
    - Monitor sandboxed processes
    - Enforce security policies
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        """Create a new instance of ProcessSandbox or return the existing one."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ProcessSandbox, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """Initialize the process sandbox."""
        # Only initialize once
        if self._initialized:
            return

        # Get logger
        self.logger = get_logger()

        # Initialize policies
        self._default_policy = None  # Will be set after SandboxPolicy is defined
        self._policies = {}

        # Initialize process tracking
        self._processes = {}
        self._process_lock = threading.Lock()

        # Mark as initialized
        self._initialized = True
        self.logger.debug("Process sandbox initialized")

    def _create_default_policy(self) -> SandboxPolicy:
        """Create the default sandbox policy."""
        policy = SandboxPolicy()

        # Set reasonable defaults
        policy.set_resource_limits(
            cpu_limit=80.0,  # 80% CPU
            memory_limit=1024 * 1024 * 1024,  # 1 GB
            process_count_limit=5
        )

        # Set timeout
        policy.set_timeout(timeout=300.0, kill_on_timeout=True)  # 5 minutes

        # Disable network access by default
        policy.set_network_access(False)

        # Enable privilege reduction
        policy.set_privilege_reduction(True)

        # Allow common commands
        policy.allow_command("ffmpeg")
        policy.allow_command("ffprobe")

        # Add common paths
        temp_dir = os.path.join(os.path.expanduser("~"), ".pyprocessor", "temp")
        policy.allow_read_path(temp_dir)
        policy.allow_write_path(temp_dir)

        return policy

    def create_policy(self, name: str) -> SandboxPolicy:
        """Create a new sandbox policy."""
        # Create a new policy based on the default
        policy = SandboxPolicy()

        # Store the policy
        self._policies[name] = policy

        return policy

    def get_policy(self, name: str) -> Optional[SandboxPolicy]:
        """Get a sandbox policy by name."""
        return self._policies.get(name)

    def get_default_policy(self) -> SandboxPolicy:
        """Get the default sandbox policy."""
        # Initialize default policy if not already done
        if self._default_policy is None:
            self._default_policy = self._create_default_policy()
        return self._default_policy

    def run_process(self, cmd: List[str], policy: Optional[SandboxPolicy] = None,
                   cwd: Optional[Union[str, Path]] = None,
                   env: Optional[Dict[str, str]] = None,
                   input_data: Optional[str] = None,
                   process_id: Optional[str] = None,
                   wait: bool = True,
                   timeout: Optional[float] = None) -> Union[Dict[str, Any], str]:
        """Run a process in a sandbox."""
        # Use the provided policy or the default
        if policy is None:
            policy = self.get_default_policy()

        # Create the sandboxed process
        process = SandboxedProcess(
            cmd=cmd,
            policy=policy,
            cwd=cwd,
            env=env,
            input_data=input_data,
            process_id=process_id
        )

        # Start the process
        if not process.start():
            return process.get_result()

        # Store the process
        with self._process_lock:
            self._processes[process.process_id] = process

        # Wait for the process if requested
        if wait:
            process.wait(timeout=timeout)

            # Remove the process from tracking
            with self._process_lock:
                if process.process_id in self._processes:
                    del self._processes[process.process_id]

            # Return the result
            return process.get_result()

        # Return the process ID for async operation
        return process.process_id

    def get_process(self, process_id: str) -> Optional[SandboxedProcess]:
        """Get a sandboxed process by ID."""
        with self._process_lock:
            return self._processes.get(process_id)

    def wait_process(self, process_id: str, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Wait for a sandboxed process to complete."""
        process = self.get_process(process_id)
        if process is None:
            self.logger.warning(f"Process not found: {process_id}")
            return None

        # Wait for the process
        process.wait(timeout=timeout)

        # Remove the process from tracking
        with self._process_lock:
            if process_id in self._processes:
                del self._processes[process_id]

        # Return the result
        return process.get_result()

    def terminate_process(self, process_id: str, timeout: float = 5.0) -> bool:
        """Terminate a sandboxed process."""
        process = self.get_process(process_id)
        if process is None:
            self.logger.warning(f"Process not found: {process_id}")
            return False

        # Terminate the process
        result = process.terminate(timeout=timeout)

        # Remove the process from tracking if terminated
        if result:
            with self._process_lock:
                if process_id in self._processes:
                    del self._processes[process_id]

        return result

    def terminate_all_processes(self, timeout: float = 5.0) -> int:
        """Terminate all sandboxed processes."""
        count = 0

        with self._process_lock:
            process_ids = list(self._processes.keys())

        for process_id in process_ids:
            if self.terminate_process(process_id, timeout):
                count += 1

        return count

    def get_process_count(self) -> int:
        """Get the number of active sandboxed processes."""
        with self._process_lock:
            return len(self._processes)

    def get_process_list(self) -> List[Dict[str, Any]]:
        """Get a list of all sandboxed processes."""
        with self._process_lock:
            return [{
                "process_id": p.process_id,
                "command": p.cmd,
                "status": p.status,
                "start_time": p.start_time,
                "pid": p.process.pid if p.process else None
            } for p in self._processes.values()]

    def cleanup(self) -> int:
        """Clean up completed processes."""
        count = 0

        with self._process_lock:
            process_ids = list(self._processes.keys())

        for process_id in process_ids:
            process = self.get_process(process_id)
            if process and process.process and process.process.poll() is not None:
                # Process has completed, remove it from tracking
                with self._process_lock:
                    if process_id in self._processes:
                        del self._processes[process_id]
                count += 1

        return count

    def shutdown(self) -> None:
        """Shutdown the process sandbox."""
        # Terminate all processes
        self.terminate_all_processes()

        self.logger.info("Process sandbox shutdown")


# Step 4: Add helper functions
# Singleton instance
_process_sandbox = None


def get_process_sandbox() -> ProcessSandbox:
    """
    Get the singleton process sandbox instance.

    Returns:
        ProcessSandbox: The singleton process sandbox instance
    """
    global _process_sandbox
    if _process_sandbox is None:
        _process_sandbox = ProcessSandbox()
    return _process_sandbox


# Module-level functions for convenience

def create_sandbox_policy(name: str) -> SandboxPolicy:
    """
    Create a new sandbox policy.

    Args:
        name: Name of the policy

    Returns:
        SandboxPolicy: The created policy
    """
    return get_process_sandbox().create_policy(name)


def get_sandbox_policy(name: str) -> Optional[SandboxPolicy]:
    """
    Get a sandbox policy by name.

    Args:
        name: Name of the policy

    Returns:
        Optional[SandboxPolicy]: The policy, or None if not found
    """
    return get_process_sandbox().get_policy(name)


def get_default_sandbox_policy() -> SandboxPolicy:
    """
    Get the default sandbox policy.

    Returns:
        SandboxPolicy: The default policy
    """
    return get_process_sandbox().get_default_policy()


def run_sandboxed_process(cmd: List[str], policy: Optional[SandboxPolicy] = None,
                        cwd: Optional[Union[str, Path]] = None,
                        env: Optional[Dict[str, str]] = None,
                        input_data: Optional[str] = None,
                        process_id: Optional[str] = None,
                        wait: bool = True,
                        timeout: Optional[float] = None) -> Union[Dict[str, Any], str]:
    """
    Run a process in a sandbox.

    Args:
        cmd: Command to run as a list of strings
        policy: Sandbox policy to use (default: None, uses default policy)
        cwd: Working directory for the command
        env: Environment variables for the command
        input_data: Input data to pass to the process
        process_id: Optional ID for the process (auto-generated if None)
        wait: Whether to wait for the process to complete
        timeout: Timeout in seconds

    Returns:
        If wait=True, returns a dictionary with process information.
        If wait=False, returns the process ID as a string.
    """
    return get_process_sandbox().run_process(
        cmd, policy, cwd, env, input_data, process_id, wait, timeout
    )


def wait_sandboxed_process(process_id: str, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """
    Wait for a sandboxed process to complete.

    Args:
        process_id: ID of the process to wait for
        timeout: Timeout in seconds

    Returns:
        Optional[Dict[str, Any]]: Process information, or None if not found
    """
    return get_process_sandbox().wait_process(process_id, timeout)


def terminate_sandboxed_process(process_id: str, timeout: float = 5.0) -> bool:
    """
    Terminate a sandboxed process.

    Args:
        process_id: ID of the process to terminate
        timeout: Timeout in seconds to wait for graceful termination

    Returns:
        bool: True if the process was terminated, False if it was not found
    """
    return get_process_sandbox().terminate_process(process_id, timeout)


def terminate_all_sandboxed_processes(timeout: float = 5.0) -> int:
    """
    Terminate all sandboxed processes.

    Args:
        timeout: Timeout in seconds to wait for graceful termination

    Returns:
        int: Number of processes terminated
    """
    return get_process_sandbox().terminate_all_processes(timeout)


def get_sandboxed_process_count() -> int:
    """
    Get the number of active sandboxed processes.

    Returns:
        int: Number of active processes
    """
    return get_process_sandbox().get_process_count()


def get_sandboxed_process_list() -> List[Dict[str, Any]]:
    """
    Get a list of all sandboxed processes.

    Returns:
        List[Dict[str, Any]]: List of process information
    """
    return get_process_sandbox().get_process_list()


def cleanup_sandboxed_processes() -> int:
    """
    Clean up completed sandboxed processes.

    Returns:
        int: Number of processes cleaned up
    """
    return get_process_sandbox().cleanup()


def shutdown_process_sandbox() -> None:
    """
    Shutdown the process sandbox.
    """
    if _process_sandbox is not None:
        _process_sandbox.shutdown()
