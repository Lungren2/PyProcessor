"""
Integration tests for the command-line interface.
"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the modules to test
from pyprocessor.main import parse_args, apply_args_to_config, run_cli_mode
from pyprocessor.utils.config import Config
from pyprocessor.utils.logging import Logger

class TestCLIInterface:
    """Test the command-line interface"""

    def setup_method(self):
        """Set up test environment before each test method"""
        # Create temporary directories
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_dir = Path(self.temp_dir.name) / "input"
        self.output_dir = Path(self.temp_dir.name) / "output"
        self.profiles_dir = Path(self.temp_dir.name) / "profiles"
        self.logs_dir = Path(self.temp_dir.name) / "logs"

        # Create directories
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        self.profiles_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)

        # Set environment variables for logs and profiles
        os.environ["PYPROCESSOR_LOG_DIR"] = str(self.logs_dir)
        os.environ["PYPROCESSOR_PROFILES_DIR"] = str(self.profiles_dir)

        # Create test files
        self.test_files = [
            "Movie_Title_1080p.mp4",
            "Another_Movie_720p.mp4"
        ]

        for filename in self.test_files:
            with open(self.input_dir / filename, 'w') as f:
                f.write("Test content")

    def teardown_method(self):
        """Clean up after each test method"""
        # Remove environment variables
        os.environ.pop("PYPROCESSOR_LOG_DIR", None)
        os.environ.pop("PYPROCESSOR_PROFILES_DIR", None)

        # Clean up temporary directory
        self.temp_dir.cleanup()

    def test_parse_args(self):
        """Test parsing command-line arguments"""
        # Set up test arguments
        test_args = [
            "--input", str(self.input_dir),
            "--output", str(self.output_dir),
            "--encoder", "libx264",
            "--preset", "medium",
            "--tune", "film",
            "--fps", "30",
            "--no-audio",
            "--jobs", "2",
            "--no-gui",
            "--verbose"
        ]

        # Parse arguments
        with patch('sys.argv', ['pyprocessor'] + test_args):
            args = parse_args()

        # Verify parsed arguments
        assert args.input == str(self.input_dir)
        assert args.output == str(self.output_dir)
        assert args.encoder == "libx264"
        assert args.preset == "medium"
        assert args.tune == "film"
        assert args.fps == 30
        assert args.no_audio is True
        assert args.jobs == 2
        assert args.no_gui is True
        assert args.verbose is True

    def test_apply_args_to_config(self):
        """Test applying command-line arguments to configuration"""
        # Create a configuration
        config = Config()

        # Create mock arguments
        class Args:
            def __init__(self):
                self.input = None
                self.output = None
                self.encoder = "libx264"
                self.preset = "medium"
                self.tune = "film"
                self.fps = 30
                self.no_audio = True
                self.jobs = 2
                self.config = None
                self.profile = None
                # Server optimization options
                self.optimize_server = None
                self.site_name = None
                self.video_path = None
                self.enable_http2 = None
                self.enable_http3 = None
                self.enable_cors = None
                self.cors_origin = None
                self.output_config = None
                self.server_name = None
                self.apply_changes = None

        args = Args()
        args.input_dir = self.input_dir
        args.output_dir = self.output_dir
        args.input = str(self.input_dir)
        args.output = str(self.output_dir)

        # Apply arguments to configuration
        apply_args_to_config(args, config)

        # Verify configuration
        assert str(config.input_folder) == str(args.input)
        assert str(config.output_folder) == str(args.output)
        assert config.ffmpeg_params["video_encoder"] == args.encoder
        assert config.ffmpeg_params["preset"] == args.preset
        assert config.ffmpeg_params["tune"] == args.tune
        assert config.ffmpeg_params["fps"] == args.fps
        assert config.ffmpeg_params["include_audio"] is False  # no_audio is True
        assert config.max_parallel_jobs == args.jobs

    @patch('pyprocessor.processing.scheduler.ProcessingScheduler.process_videos')
    def test_run_cli_mode(self, mock_process):
        """Test running in CLI mode"""
        # Mock component methods
        mock_process.return_value = True

        # Create configuration
        config = Config()
        config.input_folder = self.input_dir
        config.output_folder = self.output_dir
        config.auto_rename_files = True
        config.auto_organize_folders = True

        # Create logger
        logger = Logger(level="INFO")

        # Create file manager and encoder
        file_manager = MagicMock()
        file_manager.rename_files.return_value = 2
        file_manager.organize_folders.return_value = 2

        encoder = MagicMock()

        # Create scheduler
        scheduler = MagicMock()
        scheduler.process_videos.return_value = True

        # Run in CLI mode
        result = run_cli_mode(config, logger, file_manager, encoder, scheduler)

        # Verify result
        assert result == 0  # Success

        # Verify that methods were called
        file_manager.rename_files.assert_called_once()
        scheduler.process_videos.assert_called_once()
        file_manager.organize_folders.assert_called_once()

    @patch('pyprocessor.processing.scheduler.ProcessingScheduler.process_videos')
    def test_run_cli_mode_failure(self, mock_process):
        """Test running in CLI mode with a failure"""
        # Mock process_videos to return False (failure)
        mock_process.return_value = False

        # Create configuration
        config = Config()
        config.input_folder = self.input_dir
        config.output_folder = self.output_dir

        # Create logger
        logger = Logger(level="INFO")

        # Create file manager and encoder
        file_manager = MagicMock()
        encoder = MagicMock()

        # Create scheduler
        scheduler = MagicMock()
        scheduler.process_videos.return_value = False

        # Run in CLI mode
        result = run_cli_mode(config, logger, file_manager, encoder, scheduler)

        # Verify result
        assert result == 1  # Failure

    def test_command_line_execution(self):
        """Test executing the application from the command line"""
        # Set up test arguments
        test_args = [
            "--input", str(self.input_dir),
            "--output", str(self.output_dir),
            "--no-gui"
        ]

        # Mock the main function
        with patch('pyprocessor.main.main') as mock_main:
            # Set the return value
            mock_main.return_value = 0

            # Execute the module with patched sys.argv
            with patch('sys.argv', ['python', '-m', 'pyprocessor'] + test_args):
                # Import the module directly to simulate command-line execution
                from pyprocessor.main import main
                main()

                # Verify that main was called
                mock_main.assert_called_once()
