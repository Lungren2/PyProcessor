"""
Unit tests for the logging system.
"""
import pytest
import os
import sys
import tempfile
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the module to test
from video_processor.utils.logging import Logger

class TestLogger:
    """Test the Logger class functionality"""
    
    def setup_method(self):
        """Set up test environment before each test method"""
        # Create a temporary directory for log files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_dir = Path(self.temp_dir.name) / "logs"
        self.log_dir.mkdir(exist_ok=True)
        
        # Save the original log directory
        self.original_log_dir = os.environ.get("PYPROCESSOR_LOG_DIR", None)
        
        # Set the log directory environment variable
        os.environ["PYPROCESSOR_LOG_DIR"] = str(self.log_dir)
    
    def teardown_method(self):
        """Clean up after each test method"""
        # Restore the original log directory
        if self.original_log_dir:
            os.environ["PYPROCESSOR_LOG_DIR"] = self.original_log_dir
        else:
            os.environ.pop("PYPROCESSOR_LOG_DIR", None)
        
        # Clean up temporary directory
        self.temp_dir.cleanup()
    
    def test_logger_initialization(self):
        """Test that the Logger initializes correctly"""
        # Create logger
        logger = Logger(level="INFO")
        
        # Check that the logger was created
        assert logger.logger is not None
        assert isinstance(logger.logger, logging.Logger)
        assert logger.logger.level == logging.INFO
    
    def test_logger_debug_level(self):
        """Test logger with DEBUG level"""
        # Create logger with DEBUG level
        logger = Logger(level="DEBUG")
        
        # Check that the logger level is DEBUG
        assert logger.logger.level == logging.DEBUG
    
    def test_logger_file_handler(self):
        """Test that the logger creates a file handler"""
        # Create logger
        logger = Logger(level="INFO")
        
        # Check that a log file was created
        log_files = list(self.log_dir.glob("*.log"))
        assert len(log_files) > 0
    
    @patch('logging.Logger.info')
    def test_info_method(self, mock_info):
        """Test the info method"""
        # Create logger
        logger = Logger(level="INFO")
        
        # Call info method
        message = "Test info message"
        logger.info(message)
        
        # Verify that the underlying logger's info method was called
        mock_info.assert_called_once_with(message)
    
    @patch('logging.Logger.debug')
    def test_debug_method(self, mock_debug):
        """Test the debug method"""
        # Create logger
        logger = Logger(level="DEBUG")
        
        # Call debug method
        message = "Test debug message"
        logger.debug(message)
        
        # Verify that the underlying logger's debug method was called
        mock_debug.assert_called_once_with(message)
    
    @patch('logging.Logger.warning')
    def test_warning_method(self, mock_warning):
        """Test the warning method"""
        # Create logger
        logger = Logger(level="INFO")
        
        # Call warning method
        message = "Test warning message"
        logger.warning(message)
        
        # Verify that the underlying logger's warning method was called
        mock_warning.assert_called_once_with(message)
    
    @patch('logging.Logger.error')
    def test_error_method(self, mock_error):
        """Test the error method"""
        # Create logger
        logger = Logger(level="INFO")
        
        # Call error method
        message = "Test error message"
        logger.error(message)
        
        # Verify that the underlying logger's error method was called
        mock_error.assert_called_once_with(message)
    
    @patch('logging.Logger.critical')
    def test_critical_method(self, mock_critical):
        """Test the critical method"""
        # Create logger
        logger = Logger(level="INFO")
        
        # Call critical method
        message = "Test critical message"
        logger.critical(message)
        
        # Verify that the underlying logger's critical method was called
        mock_critical.assert_called_once_with(message)
    
    def test_log_file_naming(self):
        """Test that log files are named correctly"""
        # Create logger
        logger = Logger(level="INFO")
        
        # Check log file naming pattern
        log_files = list(self.log_dir.glob("*.log"))
        assert len(log_files) > 0
        
        # Log file should be named with date and time
        log_file = log_files[0]
        assert log_file.name.startswith("pyprocessor_")
        assert log_file.name.endswith(".log")
    
    def test_log_file_content(self):
        """Test that log messages are written to the log file"""
        # Create logger
        logger = Logger(level="INFO")
        
        # Get the log file
        log_files = list(self.log_dir.glob("*.log"))
        assert len(log_files) > 0
        log_file = log_files[0]
        
        # Write some log messages
        test_messages = [
            "Test info message",
            "Test warning message",
            "Test error message"
        ]
        
        logger.info(test_messages[0])
        logger.warning(test_messages[1])
        logger.error(test_messages[2])
        
        # Check that the messages were written to the log file
        with open(log_file, 'r') as f:
            log_content = f.read()
        
        for message in test_messages:
            assert message in log_content
    
    def test_custom_log_file(self):
        """Test using a custom log file"""
        # Create a custom log file path
        custom_log_file = self.log_dir / "custom_log.log"
        
        # Create logger with custom log file
        logger = Logger(level="INFO", log_file=custom_log_file)
        
        # Check that the custom log file was created
        assert custom_log_file.exists()
        
        # Write a log message
        test_message = "Test message in custom log file"
        logger.info(test_message)
        
        # Check that the message was written to the custom log file
        with open(custom_log_file, 'r') as f:
            log_content = f.read()
        
        assert test_message in log_content
