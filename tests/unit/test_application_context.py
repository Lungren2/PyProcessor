"""
Unit tests for ApplicationContext.
"""

import os
import signal
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from pyprocessor.utils.application_context import ApplicationContext


class TestApplicationContext:
    """Test the ApplicationContext class"""

    def setup_method(self):
        """Set up test environment before each test method"""
        # Create temporary directories
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_dir = Path(self.temp_dir.name) / "input"
        self.output_dir = Path(self.temp_dir.name) / "output"

        # Create directories
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

        # Create a mock args object
        self.args = MagicMock()
        self.args.config = None
        self.args.profile = None
        self.args.input = str(self.input_dir)
        self.args.output = str(self.output_dir)
        self.args.verbose = False
        self.args.no_gui = True

        # Save original signal handlers
        self.original_sigint = signal.getsignal(signal.SIGINT)
        self.original_sigterm = signal.getsignal(signal.SIGTERM)

    def teardown_method(self):
        """Clean up after each test method"""
        # Restore original signal handlers
        signal.signal(signal.SIGINT, self.original_sigint)
        signal.signal(signal.SIGTERM, self.original_sigterm)

        # Clean up temporary directory
        self.temp_dir.cleanup()

    def test_initialization(self):
        """Test that ApplicationContext initializes correctly"""
        # Create context
        context = ApplicationContext()

        # Check initial state
        assert context.config is None
        assert context.logger is None
        assert context.file_manager is None
        assert context.encoder is None
        assert context.scheduler is None
        assert context._initialized is False

        # Initialize context
        with patch('pyprocessor.utils.application_context.Logger'):
            result = context.initialize(self.args)

        # Check that initialization was successful
        assert result is True
        assert context._initialized is True
        assert context.config is not None
        assert context.logger is not None
        assert context.file_manager is not None
        assert context.encoder is not None
        assert context.scheduler is not None

    def test_signal_handler_registration(self):
        """Test that signal handlers are registered"""
        # Create and initialize context
        context = ApplicationContext()

        with patch('pyprocessor.utils.application_context.Logger'):
            with patch('signal.signal') as mock_signal:
                context.initialize(self.args)

                # Check that signal handlers were registered
                assert mock_signal.call_count == 2
                mock_signal.assert_has_calls([
                    call(signal.SIGINT, context._signal_handler),
                    call(signal.SIGTERM, context._signal_handler)
                ])

    def test_signal_handler(self):
        """Test the signal handler"""
        # Create and initialize context
        context = ApplicationContext()

        with patch('pyprocessor.utils.application_context.Logger'):
            context.initialize(self.args)

        # Mock the components
        context.logger = MagicMock()
        context.encoder = MagicMock()
        context.scheduler = MagicMock()
        context.scheduler.is_running = True

        # Mock sys.exit to prevent test from exiting
        with patch('sys.exit') as mock_exit:
            # Call the signal handler
            context._signal_handler(signal.SIGINT, None)

            # Check that components were called
            context.logger.info.assert_called()
            context.encoder.terminate.assert_called_once()
            context.scheduler.request_abort.assert_called_once()
            mock_exit.assert_called_once_with(0)

    def test_apply_args_to_config(self):
        """Test applying command line arguments to configuration"""
        # Create context
        context = ApplicationContext()
        context.config = MagicMock()
        context.config.ffmpeg_params = {}

        # Set up args
        args = MagicMock()
        args.input = "/test/input"
        args.output = "/test/output"
        args.encoder = "libx264"
        args.preset = "medium"
        args.tune = "film"
        args.fps = 30
        args.no_audio = True
        args.jobs = 4

        # Apply args
        with patch('pyprocessor.utils.application_context.normalize_path',
                  side_effect=lambda x: Path(x)):
            context._apply_args_to_config(args)

        # Check that config was updated
        assert context.config.ffmpeg_params["video_encoder"] == "libx264"
        assert context.config.ffmpeg_params["preset"] == "medium"
        assert context.config.ffmpeg_params["tune"] == "film"
        assert context.config.ffmpeg_params["fps"] == 30
        assert context.config.ffmpeg_params["include_audio"] is False
        assert context.config.max_parallel_jobs == 4
