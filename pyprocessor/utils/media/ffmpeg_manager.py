"""
FFmpeg manager module for handling all FFmpeg-related operations.

This module provides a centralized manager for all FFmpeg-related operations,
including locating executables, downloading binaries, checking availability,
and executing FFmpeg commands.
"""

import os
import sys
import platform
import subprocess
import zipfile
import tarfile
import urllib.request
import re
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List, Union, Callable

from pyprocessor.utils.file_system.path_utils import (
    find_executable, get_base_dir, get_executable_extension
)
from pyprocessor.utils.file_system.file_manager import get_file_manager
from pyprocessor.utils.logging.error_manager import (
    get_error_manager, with_error_handling, safe_call,
    EncodingError, ProcessError, FileSystemError, NetworkError, ValidationError,
    ErrorSeverity, ErrorCategory
)


class FFmpegManager:
    """
    Centralized manager for all FFmpeg-related operations.

    This class handles:
    - Locating FFmpeg and FFprobe executables
    - Downloading FFmpeg binaries
    - Checking FFmpeg availability
    - Executing FFmpeg commands
    - Monitoring encoding progress
    """

    def __init__(self, logger=None):
        """
        Initialize the FFmpeg manager.

        Args:
            logger: Logger instance for logging messages
        """
        self.logger = logger
        self.process = None
        self.encoding_progress = 0
        self.file_manager = get_file_manager()

        # If logger is a function, create a wrapper
        if callable(logger) and not hasattr(logger, 'info'):
            self.log_func = logger
        else:
            self.log_func = None

    def log(self, level, message):
        """
        Log a message using the provided logger or print to console.

        Args:
            level: Log level (info, debug, warning, error)
            message: Message to log
        """
        if self.log_func:
            # Use the provided log function
            self.log_func(level, message)
        elif self.logger:
            # Use the logger object
            if level == "info":
                self.logger.info(message)
            elif level == "debug":
                self.logger.debug(message)
            elif level == "warning":
                self.logger.warning(message)
            elif level == "error":
                self.logger.error(message)
        else:
            # Fall back to print
            print(f"[{level.upper()}] {message}")

    def get_base_dir(self):
        """
        Get the base directory for the application.

        Returns:
            Path: Base directory path
        """
        return get_base_dir()

    def get_ffmpeg_path(self):
        """
        Get the path to the FFmpeg executable.

        Searches for FFmpeg in the following locations (in order):
        1. Bundled with the application (if frozen)
        2. In the development directory (if not frozen)
        3. In common installation locations based on platform
        4. In the system PATH

        Returns:
            str: Path to the FFmpeg executable
        """
        # Determine executable name based on platform
        exe_ext = get_executable_extension()
        executable_name = f"ffmpeg{exe_ext}"

        # List of paths to check
        paths_to_check = []

        # 1. Check for bundled FFmpeg first
        base_dir = self.get_base_dir()
        if getattr(sys, "frozen", False):
            # When running as a bundled executable
            paths_to_check.extend([
                base_dir / "ffmpeg" / executable_name,
                base_dir / executable_name,
            ])
        else:
            # When running in development mode, check relative paths
            paths_to_check.extend([
                base_dir.parent / "ffmpeg_temp" / "bin" / executable_name,
                base_dir / "ffmpeg_temp" / "bin" / executable_name,
                base_dir.parent / "ffmpeg" / executable_name,
                base_dir / "ffmpeg" / executable_name,
            ])

        # 2. Check platform-specific common installation locations
        system = platform.system().lower()
        if system == "windows":
            # Windows common locations
            paths_to_check.extend([
                Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "FFmpeg" / "bin" / executable_name,
                Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "FFmpeg" / "bin" / executable_name,
                Path(os.environ.get("LOCALAPPDATA", "")) / "FFmpeg" / "bin" / executable_name,
            ])
        elif system == "darwin":
            # macOS common locations
            paths_to_check.extend([
                Path("/usr/local/bin") / executable_name,
                Path("/opt/homebrew/bin") / executable_name,
                Path("/opt/local/bin") / executable_name,
                Path(os.path.expanduser("~/homebrew/bin")) / executable_name,
            ])
        else:
            # Linux common locations
            paths_to_check.extend([
                Path("/usr/bin") / executable_name,
                Path("/usr/local/bin") / executable_name,
                Path("/opt/ffmpeg/bin") / executable_name,
            ])

        # Check all paths
        for path in paths_to_check:
            if self.file_manager.get_file_size(path) > 0 and os.access(str(path), os.X_OK):
                return str(path)

        # 3. Fall back to system PATH
        system_ffmpeg = find_executable("ffmpeg")
        if system_ffmpeg:
            return system_ffmpeg

        # 4. Last resort: just return the name and hope it's in PATH when executed
        return "ffmpeg"

    def get_ffprobe_path(self):
        """
        Get the path to the FFprobe executable.

        Searches for FFprobe in the following locations (in order):
        1. Bundled with the application (if frozen)
        2. In the development directory (if not frozen)
        3. In common installation locations based on platform
        4. In the system PATH

        Returns:
            str: Path to the FFprobe executable
        """
        # Determine executable name based on platform
        exe_ext = get_executable_extension()
        executable_name = f"ffprobe{exe_ext}"

        # List of paths to check
        paths_to_check = []

        # 1. Check for bundled FFprobe first
        base_dir = self.get_base_dir()
        if getattr(sys, "frozen", False):
            # When running as a bundled executable
            paths_to_check.extend([
                base_dir / "ffmpeg" / executable_name,
                base_dir / executable_name,
            ])
        else:
            # When running in development mode, check relative paths
            paths_to_check.extend([
                base_dir.parent / "ffmpeg_temp" / "bin" / executable_name,
                base_dir / "ffmpeg_temp" / "bin" / executable_name,
                base_dir.parent / "ffmpeg" / executable_name,
                base_dir / "ffmpeg" / executable_name,
            ])

        # 2. Check platform-specific common installation locations
        system = platform.system().lower()
        if system == "windows":
            # Windows common locations
            paths_to_check.extend([
                Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "FFmpeg" / "bin" / executable_name,
                Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "FFmpeg" / "bin" / executable_name,
                Path(os.environ.get("LOCALAPPDATA", "")) / "FFmpeg" / "bin" / executable_name,
            ])
        elif system == "darwin":
            # macOS common locations
            paths_to_check.extend([
                Path("/usr/local/bin") / executable_name,
                Path("/opt/homebrew/bin") / executable_name,
                Path("/opt/local/bin") / executable_name,
                Path(os.path.expanduser("~/homebrew/bin")) / executable_name,
            ])
        else:
            # Linux common locations
            paths_to_check.extend([
                Path("/usr/bin") / executable_name,
                Path("/usr/local/bin") / executable_name,
                Path("/opt/ffmpeg/bin") / executable_name,
            ])

        # Check all paths
        for path in paths_to_check:
            if self.file_manager.get_file_size(path) > 0 and os.access(str(path), os.X_OK):
                return str(path)

        # 3. Fall back to system PATH
        system_ffprobe = find_executable("ffprobe")
        if system_ffprobe:
            return system_ffprobe

        # 4. Last resort: just return the name and hope it's in PATH when executed
        return "ffprobe"

    @with_error_handling
    def check_ffmpeg(self) -> bool:
        """
        Check if FFmpeg is installed and available.

        Returns:
            bool: True if FFmpeg is available, False otherwise

        Raises:
            ProcessError: If FFmpeg check fails
        """
        ffmpeg_path = self.get_ffmpeg_path()

        try:
            result = subprocess.run(
                [ffmpeg_path, "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                raise ProcessError(
                    f"FFmpeg check failed with return code {result.returncode}",
                    severity=ErrorSeverity.ERROR,
                    details={
                        "ffmpeg_path": ffmpeg_path,
                        "stderr": result.stderr,
                        "returncode": result.returncode
                    }
                )

            if "ffmpeg version" in result.stdout:
                self.log("info", f"Found FFmpeg: {result.stdout.split(chr(10))[0]}")
                return True

            raise ProcessError(
                "FFmpeg check failed: version string not found in output",
                severity=ErrorSeverity.ERROR,
                details={
                    "ffmpeg_path": ffmpeg_path,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
            )

        except (subprocess.SubprocessError, FileNotFoundError) as e:
            raise ProcessError(
                f"FFmpeg check failed: {str(e)}",
                severity=ErrorSeverity.ERROR,
                original_exception=e,
                details={"ffmpeg_path": ffmpeg_path}
            )

    def get_ffmpeg_version(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Get the FFmpeg version string.

        Returns:
            tuple: (is_installed, version_string, error_message)
        """
        error_manager = get_error_manager()

        try:
            # Try to check FFmpeg using the error-handled method
            if self.check_ffmpeg():
                # FFmpeg is available, get the version string
                ffmpeg_path = self.get_ffmpeg_path()
                result = subprocess.run(
                    [ffmpeg_path, "-version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=5,
                )

                # Extract version string
                version_line = result.stdout.split('\n')[0]
                return True, version_line, None
        except ProcessError as e:
            # Convert the error to a user-friendly message
            return False, None, str(e)
        except Exception as e:
            # Handle any other exceptions
            error = error_manager.convert_exception(e)
            error_manager.handle_error(error)
            return False, None, str(error)

    @with_error_handling
    def has_audio(self, file_path: Union[str, Path]) -> bool:
        """
        Check if the video file has audio streams.

        Args:
            file_path: Path to the video file

        Returns:
            bool: True if the file has audio streams, False otherwise

        Raises:
            FileSystemError: If the file does not exist
            ProcessError: If FFprobe fails to analyze the file
        """
        # Convert to string and check if file exists
        file_path_str = str(file_path)
        if not os.path.exists(file_path_str):
            raise FileSystemError(
                f"File not found: {file_path_str}",
                severity=ErrorSeverity.ERROR,
                details={"file_path": file_path_str}
            )

        try:
            ffprobe_path = self.get_ffprobe_path()
            result = subprocess.run(
                [
                    ffprobe_path,
                    "-i",
                    file_path_str,
                    "-show_streams",
                    "-select_streams",
                    "a",
                    "-loglevel",
                    "error",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                raise ProcessError(
                    f"FFprobe failed to analyze audio streams with return code {result.returncode}",
                    severity=ErrorSeverity.ERROR,
                    details={
                        "file_path": file_path_str,
                        "stderr": result.stderr,
                        "returncode": result.returncode
                    }
                )

            return bool(result.stdout.strip())

        except subprocess.SubprocessError as e:
            raise ProcessError(
                f"Error checking audio streams: {str(e)}",
                severity=ErrorSeverity.ERROR,
                original_exception=e,
                details={"file_path": file_path_str}
            )

    @with_error_handling
    def get_video_info(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Get information about a video file using FFprobe.

        Args:
            file_path: Path to the video file

        Returns:
            dict: Dictionary containing video information

        Raises:
            FileSystemError: If the file does not exist
            ProcessError: If FFprobe fails to analyze the file
            EncodingError: If the JSON output cannot be parsed
        """
        # Convert to string and check if file exists
        file_path_str = str(file_path)
        if not os.path.exists(file_path_str):
            raise FileSystemError(
                f"File not found: {file_path_str}",
                severity=ErrorSeverity.ERROR,
                details={"file_path": file_path_str}
            )

        try:
            ffprobe_path = self.get_ffprobe_path()
            result = subprocess.run(
                [
                    ffprobe_path,
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_format",
                    "-show_streams",
                    file_path_str,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                raise ProcessError(
                    f"FFprobe failed to analyze video with return code {result.returncode}",
                    severity=ErrorSeverity.ERROR,
                    details={
                        "file_path": file_path_str,
                        "stderr": result.stderr,
                        "returncode": result.returncode
                    }
                )

            try:
                import json
                return json.loads(result.stdout)
            except json.JSONDecodeError as e:
                raise EncodingError(
                    f"Failed to parse FFprobe JSON output: {str(e)}",
                    severity=ErrorSeverity.ERROR,
                    original_exception=e,
                    details={
                        "file_path": file_path_str,
                        "stdout": result.stdout
                    }
                )

        except subprocess.SubprocessError as e:
            raise ProcessError(
                f"Error running FFprobe: {str(e)}",
                severity=ErrorSeverity.ERROR,
                original_exception=e,
                details={"file_path": file_path_str}
            )

    def get_ffmpeg_download_url(self):
        """
        Get the appropriate FFmpeg download URL based on the platform.

        Returns:
            tuple: (download_url, archive_type)
        """
        system = platform.system().lower()
        machine = platform.machine().lower()

        if system == "windows":
            # Windows - use gyan.dev builds
            return "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip", "zip"

        elif system == "darwin":  # macOS
            if "arm" in machine or machine == "arm64":
                # Apple Silicon (M1/M2)
                return "https://evermeet.cx/ffmpeg/getrelease/zip", "zip"
            else:
                # Intel Mac
                return "https://evermeet.cx/ffmpeg/getrelease/zip", "zip"

        elif system == "linux":
            # Linux - use static builds
            if "aarch64" in machine or "arm64" in machine:
                # ARM64
                return "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz", "tar.xz"
            elif "armv7" in machine or "armhf" in machine:
                # ARM 32-bit
                return "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-armhf-static.tar.xz", "tar.xz"
            elif "x86_64" in machine or "amd64" in machine:
                # x86_64
                return "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz", "tar.xz"
            else:
                # i686/x86
                return "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-i686-static.tar.xz", "tar.xz"

        # Default fallback
        self.log("warning", f"No specific FFmpeg build for {system} {machine}, using generic build")
        return "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip", "zip"

    @with_error_handling
    def extract_archive(self, archive_path: Union[str, Path], extract_dir: Union[str, Path], archive_type: str) -> bool:
        """
        Extract the downloaded archive based on its type.

        Args:
            archive_path: Path to the archive file
            extract_dir: Directory to extract to
            archive_type: Type of archive (zip, tar.gz, tar.xz, tar)

        Returns:
            bool: True if extraction was successful

        Raises:
            FileSystemError: If the archive file does not exist or cannot be accessed
            ValidationError: If the archive type is not supported
            ProcessError: If the extraction process fails
        """
        # Convert paths to strings
        archive_path_str = str(archive_path)
        extract_dir_str = str(extract_dir)

        # Check if archive exists
        if not os.path.exists(archive_path_str):
            raise FileSystemError(
                f"Archive file not found: {archive_path_str}",
                severity=ErrorSeverity.ERROR,
                details={
                    "archive_path": archive_path_str,
                    "extract_dir": extract_dir_str,
                    "archive_type": archive_type
                }
            )

        # Validate archive type
        valid_types = ["zip", "tar.gz", "tgz", "tar.xz", "txz", "tar"]
        if archive_type not in valid_types:
            raise ValidationError(
                f"Unsupported archive type: {archive_type}. Supported types: {', '.join(valid_types)}",
                severity=ErrorSeverity.ERROR,
                details={
                    "archive_path": archive_path_str,
                    "extract_dir": extract_dir_str,
                    "archive_type": archive_type,
                    "valid_types": valid_types
                }
            )

        try:
            # Extract based on archive type
            if archive_type == "zip":
                with zipfile.ZipFile(archive_path_str, "r") as zip_ref:
                    zip_ref.extractall(extract_dir_str)
            elif archive_type in ["tar.gz", "tgz"]:
                with tarfile.open(archive_path_str, "r:gz") as tar_ref:
                    tar_ref.extractall(extract_dir_str)
            elif archive_type in ["tar.xz", "txz"]:
                with tarfile.open(archive_path_str, "r:xz") as tar_ref:
                    tar_ref.extractall(extract_dir_str)
            elif archive_type == "tar":
                with tarfile.open(archive_path_str, "r:") as tar_ref:
                    tar_ref.extractall(extract_dir_str)

            self.log("info", f"Successfully extracted {archive_type} archive to {extract_dir_str}")
            return True

        except (zipfile.BadZipFile, tarfile.ReadError) as e:
            raise FileSystemError(
                f"Invalid or corrupted archive file: {str(e)}",
                severity=ErrorSeverity.ERROR,
                original_exception=e,
                details={
                    "archive_path": archive_path_str,
                    "extract_dir": extract_dir_str,
                    "archive_type": archive_type
                }
            )
        except (PermissionError, OSError) as e:
            raise FileSystemError(
                f"Permission or I/O error during extraction: {str(e)}",
                severity=ErrorSeverity.ERROR,
                original_exception=e,
                details={
                    "archive_path": archive_path_str,
                    "extract_dir": extract_dir_str,
                    "archive_type": archive_type
                }
            )
        except Exception as e:
            raise ProcessError(
                f"Error extracting archive: {str(e)}",
                severity=ErrorSeverity.ERROR,
                original_exception=e,
                details={
                    "archive_path": archive_path_str,
                    "extract_dir": extract_dir_str,
                    "archive_type": archive_type
                }
            )

    def find_ffmpeg_executables(self, extract_dir):
        """
        Find FFmpeg and FFprobe executables in the extracted directory.

        Args:
            extract_dir: Directory containing the extracted files

        Returns:
            tuple: (ffmpeg_path, ffprobe_path)
        """
        exe_ext = get_executable_extension()

        ffmpeg_name = f"ffmpeg{exe_ext}"
        ffprobe_name = f"ffprobe{exe_ext}"

        # Find the executables
        ffmpeg_path = None
        ffprobe_path = None

        # Use file_manager to find the executables
        all_files = self.file_manager.list_files(extract_dir, "*", recursive=True)

        for file_path in all_files:
            if file_path.name.lower() == ffmpeg_name.lower():
                ffmpeg_path = str(file_path)
            elif file_path.name.lower() == ffprobe_name.lower():
                ffprobe_path = str(file_path)

        return ffmpeg_path, ffprobe_path

    def copy_executables(self, ffmpeg_path, ffprobe_path, target_dir):
        """
        Copy FFmpeg executables to the target directory.

        Args:
            ffmpeg_path: Path to the FFmpeg executable
            ffprobe_path: Path to the FFprobe executable
            target_dir: Directory to copy the executables to

        Returns:
            bool: True if copying was successful, False otherwise
        """
        if not ffmpeg_path or not ffprobe_path:
            self.log("error", "Could not find FFmpeg executables in the extracted files")
            return False

        try:
            # Create target directory
            self.file_manager.ensure_directory(target_dir)

            # Get target paths
            exe_ext = get_executable_extension()

            target_ffmpeg = Path(target_dir) / f"ffmpeg{exe_ext}"
            target_ffprobe = Path(target_dir) / f"ffprobe{exe_ext}"

            # Copy files
            self.file_manager.copy_file(ffmpeg_path, target_ffmpeg)
            self.file_manager.copy_file(ffprobe_path, target_ffprobe)

            # Make executable on Unix-like systems
            if platform.system().lower() != "windows":
                os.chmod(target_ffmpeg, 0o755)
                os.chmod(target_ffprobe, 0o755)

            self.log("info", f"Copied FFmpeg to: {target_ffmpeg}")
            self.log("info", f"Copied FFprobe to: {target_ffprobe}")

            return True
        except Exception as e:
            self.log("error", f"Error copying executables: {str(e)}")
            return False

    def download_ffmpeg(self, target_dir=None):
        """
        Download and extract FFmpeg binaries.

        Args:
            target_dir: Directory to store the FFmpeg binaries (default: ffmpeg_temp/bin)

        Returns:
            bool: True if download was successful, False otherwise
        """
        self.log("info", f"Downloading FFmpeg binaries for {platform.system()} ({platform.machine()})...")

        # Create directories if they don't exist
        temp_dir = self.file_manager.ensure_directory("ffmpeg_temp")
        extract_dir = self.file_manager.ensure_directory(temp_dir / "extracted")

        if target_dir is None:
            target_dir = self.file_manager.ensure_directory(temp_dir / "bin")
        else:
            target_dir = self.file_manager.ensure_directory(target_dir)

        # Get download URL based on platform
        download_url, archive_type = self.get_ffmpeg_download_url()
        archive_path = temp_dir / f"ffmpeg.{archive_type}"

        # Download FFmpeg
        try:
            self.log("info", f"Downloading from {download_url}...")
            urllib.request.urlretrieve(download_url, archive_path)
            self.log("info", "Download complete.")
        except Exception as e:
            self.log("error", f"Error downloading FFmpeg: {str(e)}")
            if self.file_manager.get_file_size(archive_path) > 0:
                self.file_manager.remove_file(archive_path)
            return False

        # Extract FFmpeg
        try:
            self.log("info", f"Extracting {archive_type} archive...")
            if not self.extract_archive(archive_path, extract_dir, archive_type):
                return False
            self.log("info", "Extraction complete.")

            # Remove the archive file after successful extraction
            if self.file_manager.get_file_size(archive_path) > 0:
                self.file_manager.remove_file(archive_path)
        except Exception as e:
            self.log("error", f"Error during extraction: {str(e)}")
            return False

        # Find and copy executables
        ffmpeg_path, ffprobe_path = self.find_ffmpeg_executables(extract_dir)
        if not self.copy_executables(ffmpeg_path, ffprobe_path, target_dir):
            return False

        # Create README file
        readme_path = temp_dir / "README.txt"
        readme_content = f"""FFmpeg Binaries for PyProcessor
==============================

These FFmpeg binaries are bundled with PyProcessor to enable video processing functionality
without requiring a separate FFmpeg installation.

Platform: {platform.system()} {platform.machine()}
Downloaded from: {download_url}

FFmpeg is licensed under the GNU Lesser General Public License (LGPL) version 2.1 or later.
For more information, visit: https://ffmpeg.org/legal.html

These binaries are included for convenience and are not modified in any way from their original distribution.
"""

        try:
            with open(readme_path, "w") as f:
                f.write(readme_content)
            self.log("info", "Created README file.")
        except Exception as e:
            self.log("error", f"Error creating README file: {str(e)}")

        self.log("info", "FFmpeg preparation complete.")
        return True

    @with_error_handling
    def execute_command(self, cmd: List[str], input_file: Optional[Union[str, Path]] = None,
                       output_folder: Optional[Union[str, Path]] = None,
                       progress_callback: Optional[Callable[[Union[str, Path], int], None]] = None) -> bool:
        """
        Execute an FFmpeg command with progress monitoring.

        Args:
            cmd: FFmpeg command to execute
            input_file: Input file path (for progress reporting)
            output_folder: Output folder path
            progress_callback: Callback function for progress updates

        Returns:
            bool: True if command execution was successful

        Raises:
            ProcessError: If the FFmpeg process fails to start or returns an error
            EncodingError: If there's an error during the encoding process
        """
        self.log("debug", f"Executing: {' '.join(cmd)}")

        # Convert input file to string if provided
        input_file_str = str(input_file) if input_file else None

        try:
            # Execute FFmpeg
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                universal_newlines=True,
                bufsize=1,  # Line buffered
            )

            # Process stderr in real-time to extract progress
            duration_regex = re.compile(r"Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})")
            time_regex = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
            duration_seconds = 0
            error_lines = []

            # Parse output in real-time
            for line in self.process.stderr:
                # Store error lines for potential error reporting
                error_lines.append(line.strip())

                # Check for duration information
                duration_match = duration_regex.search(line)
                if duration_match and duration_seconds == 0:
                    hours, minutes, seconds, centiseconds = map(
                        int, duration_match.groups()
                    )
                    duration_seconds = (
                        hours * 3600 + minutes * 60 + seconds + centiseconds / 100
                    )
                    self.log("debug", f"Video duration: {duration_seconds:.2f} seconds")

                # Check for progress information
                time_match = time_regex.search(line)
                if time_match and duration_seconds > 0:
                    hours, minutes, seconds, centiseconds = map(int, time_match.groups())
                    current_seconds = (
                        hours * 3600 + minutes * 60 + seconds + centiseconds / 100
                    )
                    progress = min(int((current_seconds / duration_seconds) * 100), 100)
                    self.encoding_progress = progress

                    # Call progress callback if provided
                    if progress_callback and input_file_str:
                        progress_callback(input_file_str, progress)

                # Log FFmpeg output
                self.log("debug", line.strip())

            # Wait for process to complete
            self.process.wait()

            # Check for errors
            if self.process.returncode != 0:
                error_message = "\n".join(error_lines[-10:])  # Last 10 lines of error output
                raise EncodingError(
                    f"FFmpeg encoding failed with return code {self.process.returncode}",
                    severity=ErrorSeverity.ERROR,
                    details={
                        "command": ' '.join(cmd),
                        "input_file": input_file_str,
                        "returncode": self.process.returncode,
                        "error_message": error_message,
                        "full_error": "\n".join(error_lines)
                    }
                )

            # Ensure we report 100% at the end
            if progress_callback and input_file_str:
                progress_callback(input_file_str, 100)

            return True

        except subprocess.SubprocessError as e:
            raise ProcessError(
                f"Error starting FFmpeg process: {str(e)}",
                severity=ErrorSeverity.ERROR,
                original_exception=e,
                details={
                    "command": ' '.join(cmd),
                    "input_file": input_file_str
                }
            )
        except Exception as e:
            # Handle other exceptions
            if isinstance(e, EncodingError):
                # Re-raise EncodingError
                raise
            else:
                # Convert other exceptions to EncodingError
                raise EncodingError(
                    f"Error during FFmpeg encoding: {str(e)}",
                    severity=ErrorSeverity.ERROR,
                    original_exception=e,
                    details={
                        "command": ' '.join(cmd),
                        "input_file": input_file_str
                    }
                )

    @with_error_handling
    def terminate(self) -> bool:
        """
        Terminate any active FFmpeg process.

        Returns:
            bool: True if termination was successful, False if no process was running

        Raises:
            ProcessError: If there's an error terminating the process
        """
        if self.process and self.process.poll() is None:
            self.log("info", "Terminating active FFmpeg process")

            try:
                # Attempt graceful termination
                self.process.terminate()

                # Wait up to 5 seconds for graceful termination
                for _ in range(50):
                    if self.process.poll() is not None:
                        self.log("info", "FFmpeg process terminated gracefully")
                        return True
                    time.sleep(0.1)

                # Force kill if still running
                if self.process.poll() is None:
                    self.log("warning", "FFmpeg process did not terminate gracefully, force killing")
                    self.process.kill()
                    self.process.wait()
                    self.log("info", "FFmpeg process force killed")
                    return True

            except subprocess.SubprocessError as e:
                raise ProcessError(
                    f"Error terminating FFmpeg subprocess: {str(e)}",
                    severity=ErrorSeverity.ERROR,
                    original_exception=e,
                    details={"pid": self.process.pid if self.process else None}
                )
            except Exception as e:
                raise ProcessError(
                    f"Error terminating FFmpeg process: {str(e)}",
                    severity=ErrorSeverity.ERROR,
                    original_exception=e,
                    details={"pid": self.process.pid if self.process else None}
                )

        # No process was running
        return False
