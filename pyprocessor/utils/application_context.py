"""
Application context for managing application state and lifecycle.
"""

import signal
import sys
import time

from pyprocessor.processing.encoder import FFmpegEncoder
from pyprocessor.processing.file_manager import FileManager
from pyprocessor.processing.scheduler import ProcessingScheduler
from pyprocessor.utils.config import Config
from pyprocessor.utils.logging import Logger
from pyprocessor.utils.path_utils import normalize_path


class ApplicationContext:
    """
    Encapsulates the application state and lifecycle management.

    This class manages the core components of the application and handles
    signal processing for clean shutdown.
    """

    def __init__(self):
        """Initialize the application context."""
        self.config = None
        self.logger = None
        self.file_manager = None
        self.encoder = None
        self.scheduler = None
        # GUI components removed
        self._initialized = False

    def initialize(self, args):
        """
        Initialize the application components.

        Args:
            args: Command line arguments

        Returns:
            True if initialization was successful, False otherwise
        """
        if self._initialized:
            return True

        # Initialize config
        self.config = Config()

        # Load configuration from file or profile
        if args.config:
            self.config.load(args.config)
        elif args.profile:
            self.config.load(profile_name=args.profile)

        # Apply command line arguments to config
        self._apply_args_to_config(args)

        # Validate configuration
        errors, warnings = self.config.validate()

        # Initialize logger
        log_level = "DEBUG" if args.verbose else "INFO"
        self.logger = Logger(level=log_level)

        if errors:
            for error in errors:
                self.logger.error(f"Configuration error: {error}")
            return False

        if warnings:
            for warning in warnings:
                self.logger.warning(f"Configuration warning: {warning}")

        # Initialize components
        self.file_manager = FileManager(self.config, self.logger)
        self.encoder = FFmpegEncoder(self.config, self.logger)
        self.scheduler = ProcessingScheduler(
            self.config, self.logger, self.file_manager, self.encoder
        )

        # Register signal handlers
        self._register_signal_handlers()

        self._initialized = True
        return True

    def _apply_args_to_config(self, args):
        """
        Apply command line arguments to configuration.

        Args:
            args: Command line arguments
        """
        if hasattr(args, "input") and args.input:
            self.config.input_folder = normalize_path(args.input)

        if hasattr(args, "output") and args.output:
            self.config.output_folder = normalize_path(args.output)

        if hasattr(args, "encoder") and args.encoder:
            self.config.ffmpeg_params["video_encoder"] = args.encoder

        if hasattr(args, "preset") and args.preset:
            self.config.ffmpeg_params["preset"] = args.preset

        if hasattr(args, "tune") and args.tune:
            self.config.ffmpeg_params["tune"] = args.tune

        if hasattr(args, "fps") and args.fps is not None:
            self.config.ffmpeg_params["fps"] = args.fps

        if hasattr(args, "no_audio") and args.no_audio:
            self.config.ffmpeg_params["include_audio"] = False

        if hasattr(args, "jobs") and args.jobs is not None:
            self.config.max_parallel_jobs = args.jobs

    def _register_signal_handlers(self):
        """Register signal handlers for clean shutdown."""
        signal.signal(signal.SIGINT, self._signal_handler)  # Ctrl+C
        signal.signal(signal.SIGTERM, self._signal_handler)  # Termination signal

    def _signal_handler(self, sig, frame):
        """
        Handle termination signals for clean shutdown.

        Args:
            sig: Signal number
            frame: Current stack frame
        """
        if self.logger:
            self.logger.info("Termination signal received. Shutting down...")

        # Stop any active FFmpeg process
        if self.encoder:
            self.encoder.terminate()

        # Request abort for scheduler
        if self.scheduler and self.scheduler.is_running:
            self.scheduler.request_abort()

        if self.logger:
            self.logger.info("Shutdown complete")

        sys.exit(0)

    def run_cli_mode(self):
        """
        Run the application in CLI mode.

        Returns:
            Exit code (0 for success, non-zero for error)
        """
        if not self._initialized:
            return 1

        try:
            # Check if FFmpeg is available
            if not self.encoder.check_ffmpeg():
                self.logger.error("FFmpeg is not available. Please install FFmpeg.")
                return 1

            # Ensure output directory exists
            self.config.output_folder.mkdir(parents=True, exist_ok=True)

            # Process files
            start_time = time.time()

            # Step 1: Rename files (if enabled)
            if self.config.auto_rename_files:
                self.logger.info("Renaming files...")
                self.file_manager.rename_files()

            # Step 2: Process videos
            self.logger.info("Processing videos...")
            success = self.scheduler.process_videos()

            # Step 3: Organize folders (if enabled)
            if self.config.auto_organize_folders:
                self.logger.info("Organizing folders...")
                self.file_manager.organize_folders()

            # Report results
            end_time = time.time()
            duration = end_time - start_time
            self.logger.info(f"Processing completed in {duration:.2f} seconds")

            return 0 if success else 1

        except Exception as e:
            self.logger.error(f"Error in CLI mode: {str(e)}")
            return 1

    # GUI mode removed

    def shutdown(self):
        """Perform cleanup operations before shutdown."""
        # Stop any active FFmpeg process
        if self.encoder:
            self.encoder.terminate()

        # Request abort for scheduler
        if self.scheduler and self.scheduler.is_running:
            self.scheduler.request_abort()

        # Log shutdown
        if self.logger:
            self.logger.info("Application shutdown complete")
