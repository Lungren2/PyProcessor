"""
Unit tests for the server optimization utilities.
"""
import pytest
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the modules to test
from video_processor.utils.logging import Logger
from video_processor.utils.server_optimizer import (
    ServerOptimizer, IISOptimizer, NginxOptimizer, LinuxOptimizer
)

class TestServerOptimizer:
    """Test the ServerOptimizer base class"""
    
    def setup_method(self):
        """Set up test environment before each test method"""
        # Create a logger
        self.logger = Logger(level="INFO")
    
    def test_initialization(self):
        """Test that the ServerOptimizer initializes correctly"""
        # Create server optimizer
        optimizer = ServerOptimizer(self.logger)
        
        # Check that the optimizer was created
        assert optimizer.logger == self.logger
    
    def test_optimize_not_implemented(self):
        """Test that the optimize method raises NotImplementedError"""
        # Create server optimizer
        optimizer = ServerOptimizer(self.logger)
        
        # Check that optimize raises NotImplementedError
        with pytest.raises(NotImplementedError):
            optimizer.optimize()

class TestIISOptimizer:
    """Test the IISOptimizer class"""
    
    def setup_method(self):
        """Set up test environment before each test method"""
        # Create a logger
        self.logger = Logger(level="INFO")
        
        # Create temporary directories
        self.temp_dir = tempfile.TemporaryDirectory()
        self.video_path = Path(self.temp_dir.name) / "videos"
        self.video_path.mkdir(exist_ok=True)
    
    def teardown_method(self):
        """Clean up after each test method"""
        self.temp_dir.cleanup()
    
    def test_initialization(self):
        """Test that the IISOptimizer initializes correctly"""
        # Create IIS optimizer
        optimizer = IISOptimizer(
            self.logger,
            site_name="TestSite",
            video_path=str(self.video_path),
            enable_http2=True,
            enable_http3=True,
            enable_cors=True,
            cors_origin="*"
        )
        
        # Check that the optimizer was created
        assert optimizer.logger == self.logger
        assert optimizer.site_name == "TestSite"
        assert optimizer.video_path == str(self.video_path)
        assert optimizer.enable_http2 is True
        assert optimizer.enable_http3 is True
        assert optimizer.enable_cors is True
        assert optimizer.cors_origin == "*"
    
    @patch('subprocess.run')
    def test_optimize(self, mock_run):
        """Test the optimize method"""
        # Mock subprocess.run to return success
        mock_run.return_value.returncode = 0
        
        # Create IIS optimizer
        optimizer = IISOptimizer(
            self.logger,
            site_name="TestSite",
            video_path=str(self.video_path),
            enable_http2=True,
            enable_http3=True,
            enable_cors=True,
            cors_origin="*"
        )
        
        # Optimize
        result = optimizer.optimize()
        
        # Verify result
        assert result is True
        
        # Verify that subprocess.run was called
        assert mock_run.call_count > 0
    
    @patch('subprocess.run')
    def test_optimize_failure(self, mock_run):
        """Test the optimize method with a failure"""
        # Mock subprocess.run to return failure
        mock_run.return_value.returncode = 1
        
        # Create IIS optimizer
        optimizer = IISOptimizer(
            self.logger,
            site_name="TestSite",
            video_path=str(self.video_path),
            enable_http2=True,
            enable_http3=True,
            enable_cors=True,
            cors_origin="*"
        )
        
        # Optimize
        result = optimizer.optimize()
        
        # Verify result
        assert result is False

class TestNginxOptimizer:
    """Test the NginxOptimizer class"""
    
    def setup_method(self):
        """Set up test environment before each test method"""
        # Create a logger
        self.logger = Logger(level="INFO")
        
        # Create temporary directories
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_config = Path(self.temp_dir.name) / "nginx.conf"
    
    def teardown_method(self):
        """Clean up after each test method"""
        self.temp_dir.cleanup()
    
    def test_initialization(self):
        """Test that the NginxOptimizer initializes correctly"""
        # Create Nginx optimizer
        optimizer = NginxOptimizer(
            self.logger,
            server_name="example.com",
            output_config=str(self.output_config),
            enable_http2=True,
            enable_http3=True,
            enable_cors=True,
            cors_origin="*"
        )
        
        # Check that the optimizer was created
        assert optimizer.logger == self.logger
        assert optimizer.server_name == "example.com"
        assert optimizer.output_config == str(self.output_config)
        assert optimizer.enable_http2 is True
        assert optimizer.enable_http3 is True
        assert optimizer.enable_cors is True
        assert optimizer.cors_origin == "*"
    
    def test_optimize(self):
        """Test the optimize method"""
        # Create Nginx optimizer
        optimizer = NginxOptimizer(
            self.logger,
            server_name="example.com",
            output_config=str(self.output_config),
            enable_http2=True,
            enable_http3=True,
            enable_cors=True,
            cors_origin="*"
        )
        
        # Optimize
        result = optimizer.optimize()
        
        # Verify result
        assert result is True
        
        # Verify that the config file was created
        assert self.output_config.exists()
        
        # Check the content of the config file
        with open(self.output_config, 'r') as f:
            content = f.read()
        
        # Verify that the config contains the expected settings
        assert "server_name example.com" in content
        assert "http2" in content
        assert "add_header Alt-Svc" in content
        assert "add_header Access-Control-Allow-Origin" in content

class TestLinuxOptimizer:
    """Test the LinuxOptimizer class"""
    
    def setup_method(self):
        """Set up test environment before each test method"""
        # Create a logger
        self.logger = Logger(level="INFO")
    
    def test_initialization(self):
        """Test that the LinuxOptimizer initializes correctly"""
        # Create Linux optimizer
        optimizer = LinuxOptimizer(
            self.logger,
            apply_changes=False
        )
        
        # Check that the optimizer was created
        assert optimizer.logger == self.logger
        assert optimizer.apply_changes is False
    
    @patch('subprocess.run')
    def test_optimize_without_applying(self, mock_run):
        """Test the optimize method without applying changes"""
        # Create Linux optimizer
        optimizer = LinuxOptimizer(
            self.logger,
            apply_changes=False
        )
        
        # Optimize
        result = optimizer.optimize()
        
        # Verify result
        assert result is True
        
        # Verify that subprocess.run was not called
        mock_run.assert_not_called()
    
    @patch('subprocess.run')
    def test_optimize_with_applying(self, mock_run):
        """Test the optimize method with applying changes"""
        # Mock subprocess.run to return success
        mock_run.return_value.returncode = 0
        
        # Create Linux optimizer
        optimizer = LinuxOptimizer(
            self.logger,
            apply_changes=True
        )
        
        # Optimize
        result = optimizer.optimize()
        
        # Verify result
        assert result is True
        
        # Verify that subprocess.run was called
        assert mock_run.call_count > 0
    
    @patch('subprocess.run')
    def test_optimize_with_failure(self, mock_run):
        """Test the optimize method with a failure"""
        # Mock subprocess.run to return failure
        mock_run.return_value.returncode = 1
        
        # Create Linux optimizer
        optimizer = LinuxOptimizer(
            self.logger,
            apply_changes=True
        )
        
        # Optimize
        result = optimizer.optimize()
        
        # Verify result
        assert result is False
