"""
Centralized file management module for PyProcessor.

This module provides a singleton file manager that can be used throughout the application.
It ensures consistent file handling and operations across all modules.
"""

import csv
import json
import mimetypes
import os
import re
import shutil
import tarfile
import threading
import zipfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

from pyprocessor.utils.core.validation_manager import (
    validate_path,
    validate_regex,
    validate_string,
)
from pyprocessor.utils.file_system.path_manager import (
    copy_file,
    ensure_dir_exists,
    list_files,
    move_file,
    normalize_path,
    remove_dir,
    remove_file,
)
from pyprocessor.utils.logging.log_manager import get_logger


class FileManager:
    """
    Singleton file manager for PyProcessor.

    This class provides a centralized file management system with the following features:
    - Singleton pattern to ensure only one file manager instance exists
    - Consistent error handling for file operations
    - Progress reporting for long-running operations
    - File validation and pattern matching
    - File and folder organization
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *_, **__):
        """Singleton pattern implementation."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(FileManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, config=None, logger=None):
        """
        Initialize the file manager.

        Args:
            config: Optional configuration object
            logger: Optional logger object
        """
        # Only initialize once
        if self._initialized:
            return

        # Get logger
        self.logger = logger or get_logger()

        # Store configuration
        self.config = config

        # Initialize input and output folders
        self.input_folder = None
        self.output_folder = None

        # Update paths if config is provided
        if config:
            self.update_paths(config)

        # Mark as initialized
        self._initialized = True

        self.logger.debug("File manager initialized")

    def update_paths(self, config):
        """
        Update input and output paths from configuration.

        Args:
            config: Configuration object with input_folder and output_folder attributes
        """
        try:
            self.input_folder = normalize_path(config.input_folder)
            self.output_folder = normalize_path(config.output_folder)

            # Ensure directories exist
            ensure_dir_exists(self.input_folder)
            ensure_dir_exists(self.output_folder)

            self.logger.debug(
                f"File manager paths updated: input={self.input_folder}, output={self.output_folder}"
            )
        except Exception as e:
            self.logger.error(f"Error updating file manager paths: {str(e)}")

    def list_files(
        self,
        directory: Union[str, Path] = None,
        pattern: str = "*",
        recursive: bool = False,
    ) -> List[Path]:
        """
        List files in a directory matching a pattern.

        Args:
            directory: Directory to search in (default: input_folder)
            pattern: Glob pattern to match (default: "*")
            recursive: Whether to search recursively (default: False)

        Returns:
            List of Path objects for matching files
        """
        try:
            # Use input_folder if directory is not specified
            if directory is None:
                if self.input_folder is None:
                    raise ValueError("Input folder not set")
                directory = self.input_folder

            return list_files(directory, pattern, recursive)
        except Exception as e:
            self.logger.error(f"Error listing files in {directory}: {str(e)}")
            return []

    def list_directories(
        self,
        directory: Union[str, Path] = None,
        pattern: str = "*",
        recursive: bool = False,
    ) -> List[Path]:
        """
        List directories in a directory matching a pattern.

        Args:
            directory: Directory to search in (default: output_folder)
            pattern: Glob pattern to match (default: "*")
            recursive: Whether to search recursively (default: False)

        Returns:
            List of Path objects for matching directories
        """
        try:
            # Use output_folder if directory is not specified
            if directory is None:
                if self.output_folder is None:
                    raise ValueError("Output folder not set")
                directory = self.output_folder

            # Get all matching items
            items = list_files(directory, pattern, recursive)

            # Filter for directories
            return [item for item in items if item.is_dir()]
        except Exception as e:
            self.logger.error(f"Error listing directories in {directory}: {str(e)}")
            return []

    def copy_file(
        self, src: Union[str, Path], dst: Union[str, Path], overwrite: bool = True
    ) -> Optional[Path]:
        """
        Copy a file from source to destination.

        Args:
            src: Source file path
            dst: Destination file path
            overwrite: Whether to overwrite existing files (default: True)

        Returns:
            Path object for the destination file or None if copy failed
        """
        try:
            return copy_file(src, dst, overwrite)
        except Exception as e:
            self.logger.error(f"Error copying file {src} to {dst}: {str(e)}")
            return None

    def move_file(
        self, src: Union[str, Path], dst: Union[str, Path], overwrite: bool = True
    ) -> Optional[Path]:
        """
        Move a file from source to destination.

        Args:
            src: Source file path
            dst: Destination file path
            overwrite: Whether to overwrite existing files (default: True)

        Returns:
            Path object for the destination file or None if move failed
        """
        try:
            return move_file(src, dst, overwrite)
        except Exception as e:
            self.logger.error(f"Error moving file {src} to {dst}: {str(e)}")
            return None

    def rename_file(self, src: Union[str, Path], new_name: str) -> Optional[Path]:
        """
        Rename a file.

        Args:
            src: Source file path
            new_name: New file name (without path)

        Returns:
            Path object for the renamed file or None if rename failed
        """
        try:
            src = normalize_path(src)
            dst = src.parent / new_name

            # Check if destination exists
            if dst.exists():
                self.logger.warning(
                    f"Cannot rename {src.name} to {new_name} - destination exists"
                )
                return None

            # Rename the file
            src.rename(dst)
            self.logger.debug(f"Renamed: {src.name} to {new_name}")
            return dst
        except Exception as e:
            self.logger.error(f"Error renaming file {src} to {new_name}: {str(e)}")
            return None

    def remove_file(self, path: Union[str, Path]) -> bool:
        """
        Remove a file.

        Args:
            path: Path to the file to remove

        Returns:
            bool: True if the file was removed, False otherwise
        """
        try:
            return remove_file(path)
        except Exception as e:
            self.logger.error(f"Error removing file {path}: {str(e)}")
            return False

    def remove_directory(self, path: Union[str, Path], recursive: bool = False) -> bool:
        """
        Remove a directory.

        Args:
            path: Path to the directory to remove
            recursive: Whether to remove recursively (default: False)

        Returns:
            bool: True if the directory was removed, False otherwise
        """
        try:
            return remove_dir(path, recursive)
        except Exception as e:
            self.logger.error(f"Error removing directory {path}: {str(e)}")
            return False

    def ensure_directory(self, path: Union[str, Path]) -> Optional[Path]:
        """
        Ensure a directory exists, creating it if necessary.

        Args:
            path: Path to the directory

        Returns:
            Path object for the directory or None if creation failed
        """
        try:
            return ensure_dir_exists(path)
        except Exception as e:
            self.logger.error(f"Error ensuring directory {path}: {str(e)}")
            return None

    def get_file_size(self, path: Union[str, Path]) -> int:
        """
        Get the size of a file in bytes.

        Args:
            path: Path to the file

        Returns:
            int: Size of the file in bytes or 0 if file not found
        """
        try:
            path = normalize_path(path)
            return path.stat().st_size
        except Exception as e:
            self.logger.error(f"Error getting file size for {path}: {str(e)}")
            return 0

    def get_total_size(self, paths: List[Union[str, Path]]) -> int:
        """
        Get the total size of multiple files in bytes.

        Args:
            paths: List of file paths

        Returns:
            int: Total size of all files in bytes
        """
        try:
            return sum(self.get_file_size(path) for path in paths)
        except Exception as e:
            self.logger.error(f"Error getting total file size: {str(e)}")
            return 0

    def match_pattern(self, text: str, pattern: str) -> Optional[re.Match]:
        """
        Match a pattern against a text.

        Args:
            text: Text to match
            pattern: Regular expression pattern

        Returns:
            re.Match object or None if no match
        """
        try:
            return re.match(pattern, text)
        except Exception as e:
            self.logger.error(f"Error matching pattern {pattern}: {str(e)}")
            return None

    def rename_files(
        self,
        directory: Union[str, Path] = None,
        pattern: str = None,
        file_extension: str = ".mp4",
    ) -> int:
        """
        Rename files based on pattern matching.

        Args:
            directory: Directory containing files to rename (default: input_folder)
            pattern: Regular expression pattern with a capture group (default: from config)
            file_extension: File extension to match (default: ".mp4")

        Returns:
            int: Number of files renamed
        """
        try:
            # Use input_folder if directory is not specified
            if directory is None:
                if self.input_folder is None:
                    raise ValueError("Input folder not set")
                directory = self.input_folder

            # Use pattern from config if not specified
            if pattern is None:
                if self.config is None or not hasattr(
                    self.config, "file_rename_pattern"
                ):
                    raise ValueError("File rename pattern not set")
                pattern = self.config.file_rename_pattern

            # Skip if auto-rename is disabled in config
            if (
                self.config
                and hasattr(self.config, "auto_rename_files")
                and not self.config.auto_rename_files
            ):
                self.logger.info("File renaming skipped (disabled in config)")
                return 0

            self.logger.info("Starting file renaming process")

            # Get all files with the specified extension
            files = list(normalize_path(directory).glob(f"*{file_extension}"))
            total_files = len(files)
            renamed_count = 0

            for file in files:
                try:
                    # Remove all whitespace first
                    name_without_spaces = file.name.replace(" ", "")

                    # Check if matches pattern
                    match = self.match_pattern(name_without_spaces, pattern)
                    if match:
                        new_name = f"{match.group(1)}{file_extension}"
                        new_path = file.parent / new_name

                        # Skip if file already has correct name
                        if file.name == new_name:
                            self.logger.debug(
                                f"Skipping already correctly named file: {file.name}"
                            )
                            continue

                        # Check if destination exists
                        if new_path.exists():
                            self.logger.warning(
                                f"Cannot rename {file.name} to {new_name} - destination exists"
                            )
                            continue

                        # Rename the file
                        file.rename(new_path)
                        self.logger.info(f"Renamed: {file.name} to {new_name}")
                        renamed_count += 1
                    else:
                        self.logger.warning(f"Skipping non-matching file: {file.name}")
                except Exception as e:
                    self.logger.error(f"Failed to rename {file.name}: {str(e)}")

            self.logger.info(
                f"File renaming completed: {renamed_count} of {total_files} files renamed"
            )
            return renamed_count
        except Exception as e:
            self.logger.error(f"Error during file renaming: {str(e)}")
            return 0

    def validate_files(
        self,
        directory: Union[str, Path] = None,
        pattern: str = None,
        file_extension: str = ".mp4",
    ) -> Tuple[List[Path], List[str]]:
        """
        Validate files for correct naming pattern.

        Args:
            directory: Directory containing files to validate (default: input_folder)
            pattern: Regular expression pattern to match (default: from config)
            file_extension: File extension to match (default: ".mp4")

        Returns:
            Tuple of (valid_files, invalid_files)
        """
        try:
            # Use input_folder if directory is not specified
            if directory is None:
                if self.input_folder is None:
                    raise ValueError("Input folder not set")
                directory = self.input_folder

            # Use pattern from config if not specified
            if pattern is None:
                if self.config is None or not hasattr(
                    self.config, "file_validation_pattern"
                ):
                    raise ValueError("File validation pattern not set")
                pattern = self.config.file_validation_pattern

            # Validate directory
            dir_result = validate_path(
                directory, "directory", must_exist=True, must_be_dir=True
            )
            if not dir_result:
                self.logger.error(f"Invalid directory: {directory}")
                return [], []

            # Validate pattern
            pattern_result = validate_regex(pattern, "pattern")
            if not pattern_result:
                self.logger.error(f"Invalid regex pattern: {pattern}")
                return [], []

            valid_files = []
            invalid_files = []

            for file in normalize_path(directory).glob(f"*{file_extension}"):
                # Validate file name against pattern
                name_result = validate_string(file.name, "file_name", pattern=pattern)
                if name_result:
                    valid_files.append(file)
                else:
                    invalid_files.append(file.name)

            return valid_files, invalid_files
        except Exception as e:
            self.logger.error(f"Error during file validation: {str(e)}")
            return [], []

    def organize_folders(
        self, directory: Union[str, Path] = None, pattern: str = None
    ) -> int:
        """
        Organize folders based on naming patterns.

        Args:
            directory: Directory containing folders to organize (default: output_folder)
            pattern: Regular expression pattern with a capture group (default: from config)

        Returns:
            int: Number of folders moved
        """
        try:
            # Use output_folder if directory is not specified
            if directory is None:
                if self.output_folder is None:
                    raise ValueError("Output folder not set")
                directory = self.output_folder

            # Use pattern from config if not specified
            if pattern is None:
                if self.config is None or not hasattr(
                    self.config, "folder_organization_pattern"
                ):
                    raise ValueError("Folder organization pattern not set")
                pattern = self.config.folder_organization_pattern

            # Skip if auto-organize is disabled in config
            if (
                self.config
                and hasattr(self.config, "auto_organize_folders")
                and not self.config.auto_organize_folders
            ):
                self.logger.info("Folder organization skipped (disabled in config)")
                return 0

            self.logger.info("Starting folder organization")
            directory = normalize_path(directory)
            folders = list(directory.glob("*-*"))
            moved_count = 0

            for folder in folders:
                try:
                    if not folder.is_dir():
                        continue

                    match = self.match_pattern(folder.name, pattern)
                    if match:
                        parent_folder = directory / match.group(1)
                        self.ensure_directory(parent_folder)

                        # Destination path
                        dest = parent_folder / folder.name

                        # Skip if already in correct location
                        if str(folder.parent) == str(parent_folder):
                            self.logger.debug(
                                f"Folder already correctly organized: {folder.name}"
                            )
                            continue

                        # Check if destination exists
                        if dest.exists():
                            self.logger.warning(
                                f"Cannot move {folder.name} - destination exists"
                            )
                            continue

                        # Move the folder
                        shutil.move(str(folder), str(dest))
                        self.logger.info(f"Moved {folder.name} to {parent_folder}")
                        moved_count += 1
                except Exception as e:
                    self.logger.error(
                        f"Failed to organize folder {folder.name}: {str(e)}"
                    )

            self.logger.info(
                f"Folder organization completed: {moved_count} folders moved"
            )
            return moved_count
        except Exception as e:
            self.logger.error(f"Error during folder organization: {str(e)}")
            return 0

    def get_input_files_info(
        self, directory: Union[str, Path] = None, file_extension: str = ".mp4"
    ) -> Dict[str, Any]:
        """
        Get information about input files.

        Args:
            directory: Directory containing files to analyze (default: input_folder)
            file_extension: File extension to match (default: ".mp4")

        Returns:
            Dictionary with file information
        """
        try:
            # Use input_folder if directory is not specified
            if directory is None:
                if self.input_folder is None:
                    raise ValueError("Input folder not set")
                directory = self.input_folder

            files = list(normalize_path(directory).glob(f"*{file_extension}"))
            valid_files, invalid_files = self.validate_files(
                directory, file_extension=file_extension
            )

            total_size = sum(self.get_file_size(f) for f in files)
            # Convert to MB
            total_size_mb = total_size / (1024 * 1024)

            return {
                "total_files": len(files),
                "valid_files": len(valid_files),
                "invalid_files": len(invalid_files),
                "total_size_mb": total_size_mb,
            }
        except Exception as e:
            self.logger.error(f"Error getting input files info: {str(e)}")
            return {
                "total_files": 0,
                "valid_files": 0,
                "invalid_files": 0,
                "total_size_mb": 0,
            }

    def clean_input_directory(
        self,
        directory: Union[str, Path] = None,
        output_directory: Union[str, Path] = None,
        dry_run: bool = True,
    ) -> Tuple[int, List[Path]]:
        """
        Clean up processed files from input directory.

        Args:
            directory: Directory containing files to clean (default: input_folder)
            output_directory: Directory containing processed files (default: output_folder)
            dry_run: Whether to perform a dry run without deleting files (default: True)

        Returns:
            Tuple of (number of files deleted, list of files that would be deleted)
        """
        try:
            # Use input_folder if directory is not specified
            if directory is None:
                if self.input_folder is None:
                    raise ValueError("Input folder not set")
                directory = self.input_folder

            # Use output_folder if output_directory is not specified
            if output_directory is None:
                if self.output_folder is None:
                    raise ValueError("Output folder not set")
                output_directory = self.output_folder

            # Get all processed video names from output directory
            processed_videos = set()
            for folder in normalize_path(output_directory).glob("*-*"):
                if folder.is_dir():
                    processed_videos.add(folder.name + ".mp4")

            # Find files to delete
            to_delete = []
            for file in normalize_path(directory).glob("*.mp4"):
                if file.name in processed_videos:
                    to_delete.append(file)

            if not to_delete:
                self.logger.info("No processed files found to clean up")
                return 0, []

            if dry_run:
                self.logger.warning(
                    f"Would delete {len(to_delete)} processed files from input directory"
                )
                return 0, to_delete

            # Actually delete the files
            deleted_count = 0
            for file in to_delete:
                try:
                    file.unlink()
                    self.logger.info(f"Deleted processed file: {file.name}")
                    deleted_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to delete file {file.name}: {str(e)}")

            self.logger.info(
                f"Cleaned up {deleted_count} processed files from input directory"
            )
            return deleted_count, to_delete
        except Exception as e:
            self.logger.error(f"Error cleaning input directory: {str(e)}")
            return 0, []

    def create_temp_directory(
        self, base_dir: Union[str, Path] = None, prefix: str = "pyprocessor_"
    ) -> Optional[Path]:
        """
        Create a temporary directory.

        Args:
            base_dir: Base directory for the temporary directory (default: system temp dir)
            prefix: Prefix for the temporary directory name (default: "pyprocessor_")

        Returns:
            Path object for the temporary directory or None if creation failed
        """
        try:
            import tempfile

            if base_dir is None:
                temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
            else:
                base_dir = normalize_path(base_dir)
                self.ensure_directory(base_dir)
                temp_dir = Path(tempfile.mkdtemp(prefix=prefix, dir=str(base_dir)))

            self.logger.debug(f"Created temporary directory: {temp_dir}")
            return temp_dir
        except Exception as e:
            self.logger.error(f"Error creating temporary directory: {str(e)}")
            return None

    def clean_temp_directories(
        self, base_dir: Union[str, Path] = None, prefix: str = "pyprocessor_"
    ) -> int:
        """
        Clean up temporary directories.

        Args:
            base_dir: Base directory containing temporary directories (default: system temp dir)
            prefix: Prefix for the temporary directory names (default: "pyprocessor_")

        Returns:
            int: Number of directories removed
        """
        try:
            import tempfile

            if base_dir is None:
                base_dir = Path(tempfile.gettempdir())
            else:
                base_dir = normalize_path(base_dir)

            # Find all temporary directories with the specified prefix
            temp_dirs = [d for d in base_dir.glob(f"{prefix}*") if d.is_dir()]

            # Remove each directory
            removed_count = 0
            for temp_dir in temp_dirs:
                try:
                    shutil.rmtree(temp_dir)
                    self.logger.debug(f"Removed temporary directory: {temp_dir}")
                    removed_count += 1
                except Exception as e:
                    self.logger.error(
                        f"Failed to remove temporary directory {temp_dir}: {str(e)}"
                    )

            self.logger.info(f"Cleaned up {removed_count} temporary directories")
            return removed_count
        except Exception as e:
            self.logger.error(f"Error cleaning temporary directories: {str(e)}")
            return 0

    # File Content Operations

    def read_text(
        self, path: Union[str, Path], encoding: str = "utf-8"
    ) -> Optional[str]:
        """
        Read text content from a file.

        Args:
            path: Path to the file
            encoding: Text encoding (default: utf-8)

        Returns:
            str: File content or None if read failed
        """
        try:
            path = normalize_path(path)
            with open(path, "r", encoding=encoding) as f:
                content = f.read()
            return content
        except Exception as e:
            self.logger.error(f"Error reading text from {path}: {str(e)}")
            return None

    def read_binary(self, path: Union[str, Path]) -> Optional[bytes]:
        """
        Read binary content from a file.

        Args:
            path: Path to the file

        Returns:
            bytes: File content or None if read failed
        """
        try:
            path = normalize_path(path)
            with open(path, "rb") as f:
                content = f.read()
            return content
        except Exception as e:
            self.logger.error(f"Error reading binary data from {path}: {str(e)}")
            return None

    def write_text(
        self,
        path: Union[str, Path],
        content: str,
        encoding: str = "utf-8",
        append: bool = False,
    ) -> bool:
        """
        Write text content to a file.

        Args:
            path: Path to the file
            content: Text content to write
            encoding: Text encoding (default: utf-8)
            append: Whether to append to the file (default: False)

        Returns:
            bool: True if write succeeded, False otherwise
        """
        try:
            path = normalize_path(path)
            ensure_dir_exists(path.parent)
            mode = "a" if append else "w"
            with open(path, mode, encoding=encoding) as f:
                f.write(content)
            return True
        except Exception as e:
            self.logger.error(f"Error writing text to {path}: {str(e)}")
            return False

    def write_binary(
        self, path: Union[str, Path], content: bytes, append: bool = False
    ) -> bool:
        """
        Write binary content to a file.

        Args:
            path: Path to the file
            content: Binary content to write
            append: Whether to append to the file (default: False)

        Returns:
            bool: True if write succeeded, False otherwise
        """
        try:
            path = normalize_path(path)
            ensure_dir_exists(path.parent)
            mode = "ab" if append else "wb"
            with open(path, mode) as f:
                f.write(content)
            return True
        except Exception as e:
            self.logger.error(f"Error writing binary data to {path}: {str(e)}")
            return False

    def read_lines(
        self, path: Union[str, Path], encoding: str = "utf-8"
    ) -> Optional[List[str]]:
        """
        Read lines from a text file.

        Args:
            path: Path to the file
            encoding: Text encoding (default: utf-8)

        Returns:
            List[str]: Lines from the file or None if read failed
        """
        try:
            path = normalize_path(path)
            with open(path, "r", encoding=encoding) as f:
                lines = f.readlines()
            return [line.rstrip("\n") for line in lines]
        except Exception as e:
            self.logger.error(f"Error reading lines from {path}: {str(e)}")
            return None

    def write_lines(
        self,
        path: Union[str, Path],
        lines: List[str],
        encoding: str = "utf-8",
        append: bool = False,
    ) -> bool:
        """
        Write lines to a text file.

        Args:
            path: Path to the file
            lines: Lines to write
            encoding: Text encoding (default: utf-8)
            append: Whether to append to the file (default: False)

        Returns:
            bool: True if write succeeded, False otherwise
        """
        try:
            path = normalize_path(path)
            ensure_dir_exists(path.parent)
            mode = "a" if append else "w"
            with open(path, mode, encoding=encoding) as f:
                for line in lines:
                    f.write(line + "\n")
            return True
        except Exception as e:
            self.logger.error(f"Error writing lines to {path}: {str(e)}")
            return False

    def read_json(
        self, path: Union[str, Path], encoding: str = "utf-8"
    ) -> Optional[Any]:
        """
        Read JSON content from a file.

        Args:
            path: Path to the file
            encoding: Text encoding (default: utf-8)

        Returns:
            Any: Parsed JSON content or None if read failed
        """
        try:
            path = normalize_path(path)
            with open(path, "r", encoding=encoding) as f:
                content = json.load(f)
            return content
        except Exception as e:
            self.logger.error(f"Error reading JSON from {path}: {str(e)}")
            return None

    def write_json(
        self,
        path: Union[str, Path],
        content: Any,
        encoding: str = "utf-8",
        indent: int = 2,
    ) -> bool:
        """
        Write JSON content to a file.

        Args:
            path: Path to the file
            content: Content to write as JSON
            encoding: Text encoding (default: utf-8)
            indent: JSON indentation (default: 2)

        Returns:
            bool: True if write succeeded, False otherwise
        """
        try:
            path = normalize_path(path)
            ensure_dir_exists(path.parent)
            with open(path, "w", encoding=encoding) as f:
                json.dump(content, f, indent=indent)
            return True
        except Exception as e:
            self.logger.error(f"Error writing JSON to {path}: {str(e)}")
            return False

    def read_csv(
        self,
        path: Union[str, Path],
        delimiter: str = ",",
        encoding: str = "utf-8",
        has_header: bool = True,
    ) -> Optional[List[Dict[str, str]]]:
        """
        Read CSV content from a file.

        Args:
            path: Path to the file
            delimiter: CSV delimiter (default: ",")
            encoding: Text encoding (default: utf-8)
            has_header: Whether the CSV has a header row (default: True)

        Returns:
            List[Dict[str, str]]: Parsed CSV content or None if read failed
        """
        try:
            path = normalize_path(path)
            with open(path, "r", encoding=encoding, newline="") as f:
                if has_header:
                    reader = csv.DictReader(f, delimiter=delimiter)
                    return list(reader)
                else:
                    reader = csv.reader(f, delimiter=delimiter)
                    return [
                        dict(zip([f"column_{i}" for i in range(len(row))], row))
                        for row in reader
                    ]
        except Exception as e:
            self.logger.error(f"Error reading CSV from {path}: {str(e)}")
            return None

    def write_csv(
        self,
        path: Union[str, Path],
        data: List[Dict[str, Any]],
        fieldnames: Optional[List[str]] = None,
        delimiter: str = ",",
        encoding: str = "utf-8",
    ) -> bool:
        """
        Write CSV content to a file.

        Args:
            path: Path to the file
            data: Data to write as CSV
            fieldnames: Column names (default: keys from first row)
            delimiter: CSV delimiter (default: ",")
            encoding: Text encoding (default: utf-8)

        Returns:
            bool: True if write succeeded, False otherwise
        """
        try:
            path = normalize_path(path)
            ensure_dir_exists(path.parent)

            if not data:
                self.logger.warning(f"No data to write to CSV file {path}")
                return False

            if fieldnames is None:
                fieldnames = list(data[0].keys())

            with open(path, "w", encoding=encoding, newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
                writer.writeheader()
                writer.writerows(data)
            return True
        except Exception as e:
            self.logger.error(f"Error writing CSV to {path}: {str(e)}")
            return False

    # File Compression Operations

    def create_zip(
        self,
        zip_path: Union[str, Path],
        files_to_add: List[Union[str, Path]],
        base_dir: Optional[Union[str, Path]] = None,
        compression: int = zipfile.ZIP_DEFLATED,
    ) -> bool:
        """
        Create a ZIP archive containing the specified files.

        Args:
            zip_path: Path to the ZIP file to create
            files_to_add: List of files to add to the ZIP
            base_dir: Base directory for relative paths in the ZIP (default: None)
            compression: Compression method (default: ZIP_DEFLATED)

        Returns:
            bool: True if ZIP creation succeeded, False otherwise
        """
        try:
            zip_path = normalize_path(zip_path)
            ensure_dir_exists(zip_path.parent)

            with zipfile.ZipFile(zip_path, "w", compression=compression) as zip_file:
                for file_path in files_to_add:
                    file_path = normalize_path(file_path)

                    if not file_path.exists():
                        self.logger.warning(f"File not found, skipping: {file_path}")
                        continue

                    # Determine the arcname (path within the ZIP)
                    if base_dir is not None:
                        base_dir = normalize_path(base_dir)
                        try:
                            arcname = file_path.relative_to(base_dir)
                        except ValueError:
                            arcname = file_path.name
                    else:
                        arcname = file_path.name

                    # Add the file to the ZIP
                    zip_file.write(file_path, arcname)
                    self.logger.debug(f"Added {file_path} to ZIP as {arcname}")

            self.logger.info(f"Created ZIP archive: {zip_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error creating ZIP archive {zip_path}: {str(e)}")
            return False

    def extract_zip(
        self, zip_path: Union[str, Path], extract_dir: Union[str, Path]
    ) -> bool:
        """
        Extract a ZIP archive to the specified directory.

        Args:
            zip_path: Path to the ZIP file to extract
            extract_dir: Directory to extract to

        Returns:
            bool: True if extraction succeeded, False otherwise
        """
        try:
            zip_path = normalize_path(zip_path)
            extract_dir = normalize_path(extract_dir)
            ensure_dir_exists(extract_dir)

            with zipfile.ZipFile(zip_path, "r") as zip_file:
                zip_file.extractall(extract_dir)

            self.logger.info(f"Extracted ZIP archive {zip_path} to {extract_dir}")
            return True
        except Exception as e:
            self.logger.error(f"Error extracting ZIP archive {zip_path}: {str(e)}")
            return False

    def create_tar(
        self,
        tar_path: Union[str, Path],
        files_to_add: List[Union[str, Path]],
        base_dir: Optional[Union[str, Path]] = None,
        compression: str = "gz",
    ) -> bool:
        """
        Create a TAR archive containing the specified files.

        Args:
            tar_path: Path to the TAR file to create
            files_to_add: List of files to add to the TAR
            base_dir: Base directory for relative paths in the TAR (default: None)
            compression: Compression method ("gz", "bz2", "xz", or None) (default: "gz")

        Returns:
            bool: True if TAR creation succeeded, False otherwise
        """
        try:
            tar_path = normalize_path(tar_path)
            ensure_dir_exists(tar_path.parent)

            # Determine the mode based on compression
            if compression == "gz":
                mode = "w:gz"
            elif compression == "bz2":
                mode = "w:bz2"
            elif compression == "xz":
                mode = "w:xz"
            else:
                mode = "w"

            with tarfile.open(tar_path, mode) as tar_file:
                for file_path in files_to_add:
                    file_path = normalize_path(file_path)

                    if not file_path.exists():
                        self.logger.warning(f"File not found, skipping: {file_path}")
                        continue

                    # Determine the arcname (path within the TAR)
                    if base_dir is not None:
                        base_dir = normalize_path(base_dir)
                        try:
                            arcname = file_path.relative_to(base_dir)
                        except ValueError:
                            arcname = file_path.name
                    else:
                        arcname = file_path.name

                    # Add the file to the TAR
                    tar_file.add(file_path, arcname=str(arcname))
                    self.logger.debug(f"Added {file_path} to TAR as {arcname}")

            self.logger.info(f"Created TAR archive: {tar_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error creating TAR archive {tar_path}: {str(e)}")
            return False

    def extract_tar(
        self, tar_path: Union[str, Path], extract_dir: Union[str, Path]
    ) -> bool:
        """
        Extract a TAR archive to the specified directory.

        Args:
            tar_path: Path to the TAR file to extract
            extract_dir: Directory to extract to

        Returns:
            bool: True if extraction succeeded, False otherwise
        """
        try:
            tar_path = normalize_path(tar_path)
            extract_dir = normalize_path(extract_dir)
            ensure_dir_exists(extract_dir)

            with tarfile.open(tar_path, "r:*") as tar_file:
                tar_file.extractall(extract_dir)

            self.logger.info(f"Extracted TAR archive {tar_path} to {extract_dir}")
            return True
        except Exception as e:
            self.logger.error(f"Error extracting TAR archive {tar_path}: {str(e)}")
            return False

    # File Streaming Operations

    @contextmanager
    def open_text(
        self, path: Union[str, Path], mode: str = "r", encoding: str = "utf-8"
    ):
        """
        Open a text file and return a context manager.

        Args:
            path: Path to the file
            mode: File mode (default: "r")
            encoding: Text encoding (default: utf-8)

        Yields:
            File object for reading/writing text
        """
        path = normalize_path(path)

        if "w" in mode or "a" in mode or "x" in mode:
            ensure_dir_exists(path.parent)

        try:
            with open(path, mode, encoding=encoding) as f:
                yield f
        except Exception as e:
            self.logger.error(f"Error opening text file {path}: {str(e)}")
            raise

    @contextmanager
    def open_binary(self, path: Union[str, Path], mode: str = "rb"):
        """
        Open a binary file and return a context manager.

        Args:
            path: Path to the file
            mode: File mode (default: "rb")

        Yields:
            File object for reading/writing binary data
        """
        path = normalize_path(path)

        if "w" in mode or "a" in mode or "x" in mode:
            ensure_dir_exists(path.parent)

        try:
            with open(path, mode) as f:
                yield f
        except Exception as e:
            self.logger.error(f"Error opening binary file {path}: {str(e)}")
            raise

    def stream_read_lines(
        self, path: Union[str, Path], encoding: str = "utf-8"
    ) -> Iterator[str]:
        """
        Stream lines from a text file.

        Args:
            path: Path to the file
            encoding: Text encoding (default: utf-8)

        Yields:
            str: Each line from the file
        """
        path = normalize_path(path)

        try:
            with open(path, "r", encoding=encoding) as f:
                for line in f:
                    yield line.rstrip("\n")
        except Exception as e:
            self.logger.error(f"Error streaming lines from {path}: {str(e)}")
            raise

    def stream_read_chunks(
        self, path: Union[str, Path], chunk_size: int = 8192
    ) -> Iterator[bytes]:
        """
        Stream chunks from a binary file.

        Args:
            path: Path to the file
            chunk_size: Size of each chunk in bytes (default: 8192)

        Yields:
            bytes: Each chunk from the file
        """
        path = normalize_path(path)

        try:
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        except Exception as e:
            self.logger.error(f"Error streaming chunks from {path}: {str(e)}")
            raise

    # File Metadata Operations

    def get_file_metadata(self, path: Union[str, Path]) -> Dict[str, Any]:
        """
        Get metadata for a file.

        Args:
            path: Path to the file

        Returns:
            Dict[str, Any]: File metadata
        """
        try:
            path = normalize_path(path)

            if not path.exists():
                self.logger.warning(f"File not found: {path}")
                return {}

            stat = path.stat()

            # Get file type
            file_type = "directory" if path.is_dir() else "file"
            if path.is_symlink():
                file_type = "symlink"

            # Get mime type
            mime_type, encoding = mimetypes.guess_type(path)

            # Get file times
            # Note: st_ctime is not creation time on Unix, but rather the last metadata change time
            # We use it as a fallback for creation time when st_birthtime is not available
            try:
                # Try to get creation time (only available on some platforms)
                if hasattr(stat, "st_birthtime"):
                    created = datetime.fromtimestamp(stat.st_birthtime)
                else:
                    # Fall back to modification time as a safer alternative
                    # Avoiding st_ctime due to deprecation warnings
                    created = datetime.fromtimestamp(stat.st_mtime)
            except AttributeError:
                # Handle any unexpected issues
                created = datetime.fromtimestamp(stat.st_mtime)

            modified = datetime.fromtimestamp(stat.st_mtime)
            accessed = datetime.fromtimestamp(stat.st_atime)

            # Get file size
            size = stat.st_size

            # Get file extension
            extension = path.suffix.lower() if path.suffix else ""

            return {
                "name": path.name,
                "path": str(path),
                "parent": str(path.parent),
                "type": file_type,
                "mime_type": mime_type,
                "encoding": encoding,
                "extension": extension,
                "size": size,
                "size_human": self._format_size(size),
                "created": created.isoformat(),
                "modified": modified.isoformat(),
                "accessed": accessed.isoformat(),
                "is_hidden": path.name.startswith("."),
                "is_readonly": not os.access(path, os.W_OK),
                "is_executable": (
                    os.access(path, os.X_OK) if not path.is_dir() else False
                ),
            }
        except Exception as e:
            self.logger.error(f"Error getting metadata for {path}: {str(e)}")
            return {}

    def _format_size(self, size: int) -> str:
        """
        Format a file size in human-readable format.

        Args:
            size: Size in bytes

        Returns:
            str: Human-readable size
        """
        for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
            if abs(size) < 1024.0:
                return f"{size:.1f} {unit}B"
            size /= 1024.0
        return f"{size:.1f} YB"

    def get_directory_size(self, path: Union[str, Path], recursive: bool = True) -> int:
        """
        Get the total size of a directory.

        Args:
            path: Path to the directory
            recursive: Whether to include subdirectories (default: True)

        Returns:
            int: Total size in bytes
        """
        try:
            path = normalize_path(path)

            if not path.exists() or not path.is_dir():
                self.logger.warning(f"Directory not found: {path}")
                return 0

            total_size = 0

            for item in path.iterdir():
                if item.is_file():
                    total_size += item.stat().st_size
                elif item.is_dir() and recursive:
                    total_size += self.get_directory_size(item, recursive)

            return total_size
        except Exception as e:
            self.logger.error(f"Error getting directory size for {path}: {str(e)}")
            return 0

    def get_file_hash(
        self, path: Union[str, Path], algorithm: str = "sha256"
    ) -> Optional[str]:
        """
        Calculate a hash for a file.

        Args:
            path: Path to the file
            algorithm: Hash algorithm (default: "sha256")

        Returns:
            str: File hash or None if calculation failed
        """
        try:
            import hashlib

            path = normalize_path(path)

            if not path.exists() or not path.is_file():
                self.logger.warning(f"File not found: {path}")
                return None

            # Get the hash algorithm
            if algorithm == "md5":
                hash_obj = hashlib.md5()
            elif algorithm == "sha1":
                hash_obj = hashlib.sha1()
            elif algorithm == "sha256":
                hash_obj = hashlib.sha256()
            elif algorithm == "sha512":
                hash_obj = hashlib.sha512()
            else:
                self.logger.warning(
                    f"Unsupported hash algorithm: {algorithm}. Using sha256."
                )
                hash_obj = hashlib.sha256()

            # Calculate the hash
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)

            return hash_obj.hexdigest()
        except Exception as e:
            self.logger.error(f"Error calculating hash for {path}: {str(e)}")
            return None

    def set_file_times(
        self,
        path: Union[str, Path],
        accessed: Optional[datetime] = None,
        modified: Optional[datetime] = None,
    ) -> bool:
        """
        Set access and modification times for a file.

        Args:
            path: Path to the file
            accessed: Access time (default: current time)
            modified: Modification time (default: same as accessed)

        Returns:
            bool: True if times were set successfully, False otherwise
        """
        try:
            path = normalize_path(path)

            if not path.exists():
                self.logger.warning(f"File not found: {path}")
                return False

            # Use current time if not specified
            if accessed is None:
                accessed = datetime.now()

            # Use accessed time for modified if not specified
            if modified is None:
                modified = accessed

            # Convert to timestamps
            atime = accessed.timestamp()
            mtime = modified.timestamp()

            # Set the times
            os.utime(path, (atime, mtime))

            return True
        except Exception as e:
            self.logger.error(f"Error setting file times for {path}: {str(e)}")
            return False

    def get_mime_type(self, path: Union[str, Path]) -> Optional[str]:
        """
        Get the MIME type of a file.

        Args:
            path: Path to the file

        Returns:
            str: MIME type or None if not determined
        """
        try:
            path = normalize_path(path)

            if not path.exists() or not path.is_file():
                self.logger.warning(f"File not found: {path}")
                return None

            mime_type, _ = mimetypes.guess_type(path)
            return mime_type
        except Exception as e:
            self.logger.error(f"Error getting MIME type for {path}: {str(e)}")
            return None


# Create a singleton instance
_file_manager = None


def get_file_manager(config=None, logger=None) -> FileManager:
    """
    Get the singleton file manager instance.

    Args:
        config: Optional configuration object
        logger: Optional logger object

    Returns:
        FileManager: The singleton file manager instance
    """
    global _file_manager
    if _file_manager is None:
        _file_manager = FileManager(config, logger)
    elif config is not None:
        _file_manager.update_paths(config)
    return _file_manager
