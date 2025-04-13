"""
Unit tests for path utilities.
"""

import os
import platform
from pathlib import Path

import pytest

from pyprocessor.utils.path_utils import (
    expand_env_vars,
    get_app_data_dir,
    get_default_media_root,
    normalize_path,
)


class TestPathUtils:
    """Test the path utilities"""

    def setup_method(self):
        """Set up test environment before each test method"""
        # Save original environment variables
        self.original_env = os.environ.copy()

        # Set test environment variables
        os.environ["TEST_PATH_VAR"] = "/test/path"
        os.environ["MEDIA_ROOT"] = "/media/root"

    def teardown_method(self):
        """Clean up after each test method"""
        # Restore original environment variables
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_expand_env_vars_unix_style(self):
        """Test expanding Unix-style environment variables"""
        path_str = "${TEST_PATH_VAR}/subdir"
        expanded = expand_env_vars(path_str)
        assert expanded == "/test/path/subdir"

    def test_expand_env_vars_windows_style(self):
        """Test expanding Windows-style environment variables"""
        # This test only works on Windows
        if platform.system() == "Windows":
            os.environ["TEST_WIN_VAR"] = "C:\\test\\win"
            path_str = "%TEST_WIN_VAR%\\subdir"
            expanded = expand_env_vars(path_str)
            assert expanded == "C:\\test\\win\\subdir"

    def test_normalize_path(self):
        """Test normalizing paths"""
        # Test with environment variable
        path_str = "${TEST_PATH_VAR}/subdir"
        normalized = normalize_path(path_str)
        assert isinstance(normalized, Path)
        assert str(normalized).replace("\\", "/") == "/test/path/subdir"

        # Test with regular path
        path_str = "/regular/path"
        normalized = normalize_path(path_str)
        assert isinstance(normalized, Path)
        assert str(normalized).replace("\\", "/") == "/regular/path"

    def test_get_default_media_root(self):
        """Test getting default media root"""
        media_root = get_default_media_root()
        assert isinstance(media_root, Path)
        # We can't test the exact value as it depends on the platform,
        # but we can check that it's a valid path
        assert media_root.is_absolute()

    def test_get_app_data_dir(self):
        """Test getting application data directory"""
        app_data_dir = get_app_data_dir()
        assert isinstance(app_data_dir, Path)
        assert app_data_dir.is_absolute()
        # Check that it contains "PyProcessor" in the path
        assert "PyProcessor" in str(app_data_dir) or "pyprocessor" in str(app_data_dir)
