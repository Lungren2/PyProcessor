"""
Unit tests for the server optimization utilities.
"""

import pytest
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import the modules to test
from pyprocessor.utils.logging import Logger
from pyprocessor.utils.server_optimizer import ServerOptimizer


class TestServerOptimizer:
    """Test the ServerOptimizer base class"""

    def setup_method(self):
        """Set up test environment before each test method"""
        # Create a logger
        self.logger = Logger(level="INFO")
        # Create a mock config
        self.config = type("MockConfig", (), {})()

    def test_initialization(self):
        """Test that the ServerOptimizer initializes correctly"""
        # Create server optimizer
        optimizer = ServerOptimizer(self.config, self.logger)

        # Check that the optimizer was created
        assert optimizer.logger == self.logger
        assert optimizer.config == self.config


class TestIISOptimizer:
    """Test the IIS optimization method"""

    def setup_method(self):
        """Set up test environment before each test method"""
        # Create a logger
        self.logger = Logger(level="INFO")
        # Create a mock config
        self.config = type("MockConfig", (), {})()

        # Create temporary directories
        self.temp_dir = tempfile.TemporaryDirectory()
        self.video_path = Path(self.temp_dir.name) / "videos"
        self.video_path.mkdir(exist_ok=True)

    def teardown_method(self):
        """Clean up after each test method"""
        self.temp_dir.cleanup()

    @patch("subprocess.run")
    def test_optimize_iis(self, mock_run):
        """Test the optimize_iis method"""
        # Mock subprocess.run to return success
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Success"
        mock_run.return_value.stderr = ""

        # Create server optimizer
        optimizer = ServerOptimizer(self.config, self.logger)

        # Optimize IIS
        success, message = optimizer.optimize_iis(
            site_name="TestSite",
            video_path=str(self.video_path),
            enable_http2=True,
            enable_http3=True,
            enable_cors=True,
            cors_origin="*",
        )

        # Verify result
        assert success is True

        # Verify that subprocess.run was called
        assert mock_run.call_count > 0

    @patch("subprocess.run")
    def test_optimize_iis_failure(self, mock_run):
        """Test the optimize_iis method with a failure"""
        # Mock subprocess.run to return failure
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "Error"

        # Create server optimizer
        optimizer = ServerOptimizer(self.config, self.logger)

        # Optimize IIS
        success, message = optimizer.optimize_iis(
            site_name="TestSite",
            video_path=str(self.video_path),
            enable_http2=True,
            enable_http3=True,
            enable_cors=True,
            cors_origin="*",
        )

        # Verify result
        assert success is False


class TestNginxOptimizer:
    """Test the Nginx optimization method"""

    def setup_method(self):
        """Set up test environment before each test method"""
        # Create a logger
        self.logger = Logger(level="INFO")
        # Create a mock config
        self.config = type("MockConfig", (), {})()

        # Create temporary directories
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_config = Path(self.temp_dir.name) / "nginx.conf"

    def teardown_method(self):
        """Clean up after each test method"""
        self.temp_dir.cleanup()

    @patch("os.path.exists")
    @patch(
        "builtins.open",
        new_callable=unittest.mock.mock_open,
        read_data="server_name yourdomain.com;\nlisten 443 ssl http2;",
    )
    def test_optimize_nginx(self, mock_open, mock_exists):
        """Test the optimize_nginx method"""
        # Mock file existence
        mock_exists.return_value = True

        # Create server optimizer
        optimizer = ServerOptimizer(self.config, self.logger)

        # Optimize Nginx
        success, message = optimizer.optimize_nginx(
            output_path=str(self.output_config),
            server_name="example.com",
            ssl_enabled=True,
            enable_http3=True,
        )

        # Verify result
        assert success is True


class TestLinuxOptimizer:
    """Test the Linux optimization method"""

    def setup_method(self):
        """Set up test environment before each test method"""
        # Create a logger
        self.logger = Logger(level="INFO")
        # Create a mock config
        self.config = type("MockConfig", (), {})()

    @patch("os.path.exists")
    @patch("tempfile.mkdtemp")
    @patch("shutil.copy2")
    def test_optimize_linux_without_applying(
        self, mock_copy, mock_mkdtemp, mock_exists
    ):
        """Test the optimize_linux method without applying changes"""
        # Mock file existence and temp directory
        mock_exists.return_value = True
        mock_mkdtemp.return_value = "/tmp/test"

        # Create server optimizer
        optimizer = ServerOptimizer(self.config, self.logger)

        # Optimize Linux
        success, message, script_path = optimizer.optimize_linux(apply_changes=False)

        # Verify result
        assert success is True
        assert script_path is not None

    @patch("os.path.exists")
    @patch("platform.system")
    @patch("subprocess.run")
    def test_optimize_linux_with_applying(self, mock_run, mock_platform, mock_exists):
        """Test the optimize_linux method with applying changes"""
        # Mock file existence, platform, and subprocess
        mock_exists.return_value = True
        mock_platform.return_value = "Linux"
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Success"
        mock_run.return_value.stderr = ""

        # Create server optimizer
        optimizer = ServerOptimizer(self.config, self.logger)

        # Optimize Linux
        success, message, script_path = optimizer.optimize_linux(apply_changes=True)

        # Verify result
        assert success is True

    @patch("os.path.exists")
    @patch("platform.system")
    @patch("subprocess.run")
    def test_optimize_linux_with_failure(self, mock_run, mock_platform, mock_exists):
        """Test the optimize_linux method with a failure"""
        # Mock file existence, platform, and subprocess
        mock_exists.return_value = True
        mock_platform.return_value = "Linux"
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "Error"

        # Create server optimizer
        optimizer = ServerOptimizer(self.config, self.logger)

        # Optimize Linux
        success, message, script_path = optimizer.optimize_linux(apply_changes=True)

        # Verify result
        assert success is False
