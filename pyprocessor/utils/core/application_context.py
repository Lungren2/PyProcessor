"""
Application context for managing application state and lifecycle.
"""

import signal
import sys
import time

from pyprocessor.processing.encoder import FFmpegEncoder
from pyprocessor.utils.file_system.file_manager import get_file_manager
from pyprocessor.processing.scheduler import ProcessingScheduler
from pyprocessor.utils.config.config_manager import Config, get_config
from pyprocessor.utils.logging.log_manager import get_logger
from pyprocessor.utils.file_system.path_utils import normalize_path, ensure_dir_exists
from pyprocessor.utils.core.plugin_manager import get_plugin_manager, load_all_plugins, discover_plugins


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
        self.plugin_manager = None
        self.plugins = {}
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
        self.logger = get_logger(level=log_level)

        if errors:
            for error in errors:
                self.logger.error(f"Configuration error: {error}")
            return False

        if warnings:
            for warning in warnings:
                self.logger.warning(f"Configuration warning: {warning}")

        # Initialize components
        self.file_manager = get_file_manager(self.config, self.logger)
        self.encoder = FFmpegEncoder(self.config, self.logger)
        self.scheduler = ProcessingScheduler(
            self.config, self.logger, self.file_manager, self.encoder
        )

        # Initialize plugin system
        self.plugin_manager = get_plugin_manager()
        self.logger.info("Discovering plugins...")
        discover_plugins()

        # Load plugins if enabled
        if self.config.get("enable_plugins", True):
            self.logger.info("Loading plugins...")
            self.plugins = load_all_plugins()
            self.logger.info(f"Loaded {len(self.plugins)} plugins")

            # Log loaded plugins
            for plugin_name, plugin in self.plugins.items():
                self.logger.info(f"Loaded plugin: {plugin_name} (v{plugin.version})")

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
        # Use the apply_args method from the Config class
        self.config.apply_args(args)

        # Handle server optimization options
        if hasattr(args, "optimize_server") and args.optimize_server:
            # Set server optimization enabled and type
            self.config.config_manager.set("server_optimization.enabled", True)
            self.config.config_manager.set("server_optimization.server_type", args.optimize_server)

            # IIS options
            if args.optimize_server == "iis":
                if hasattr(args, "site_name") and args.site_name:
                    self.config.config_manager.set("server_optimization.iis.site_name", args.site_name)
                if hasattr(args, "video_path") and args.video_path:
                    self.config.config_manager.set("server_optimization.iis.video_path", args.video_path)
                if hasattr(args, "enable_http2"):
                    self.config.config_manager.set("server_optimization.iis.enable_http2", args.enable_http2)
                if hasattr(args, "enable_http3"):
                    self.config.config_manager.set("server_optimization.iis.enable_http3", args.enable_http3)
                if hasattr(args, "enable_cors"):
                    self.config.config_manager.set("server_optimization.iis.enable_cors", args.enable_cors)
                if hasattr(args, "cors_origin") and args.cors_origin:
                    self.config.config_manager.set("server_optimization.iis.cors_origin", args.cors_origin)

            # Nginx options
            elif args.optimize_server == "nginx":
                if hasattr(args, "output_config") and args.output_config:
                    self.config.config_manager.set("server_optimization.nginx.output_path", args.output_config)
                if hasattr(args, "server_name") and args.server_name:
                    self.config.config_manager.set("server_optimization.nginx.server_name", args.server_name)
                if hasattr(args, "enable_http3"):
                    self.config.config_manager.set("server_optimization.nginx.enable_http3", args.enable_http3)

            # Linux options
            elif args.optimize_server == "linux":
                if hasattr(args, "apply_changes"):
                    self.config.config_manager.set("server_optimization.linux.apply_changes", args.apply_changes)

    def _register_signal_handlers(self):
        """Register signal handlers for clean shutdown."""
        signal.signal(signal.SIGINT, self._signal_handler)  # Ctrl+C
        signal.signal(signal.SIGTERM, self._signal_handler)  # Termination signal

    def _signal_handler(self, *_):
        """
        Handle termination signals for clean shutdown.

        Args:
            *_: Signal arguments (signal number and stack frame) - not used
        """
        if self.logger:
            self.logger.info("Termination signal received. Shutting down...")

        # Stop any active FFmpeg process
        if self.encoder:
            self.encoder.terminate()

        # Request abort for scheduler
        if self.scheduler and self.scheduler.is_running:
            self.scheduler.request_abort()

        # Unload plugins
        if self.plugin_manager and self.plugins:
            self.logger.info("Unloading plugins...")
            from pyprocessor.utils.core.plugin_manager import unload_all_plugins
            unload_all_plugins()

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
            self.logger.info("Running in command-line mode")

            # Check if server optimization is requested
            if self.config.server_optimization.get("enabled", False):
                from pyprocessor.utils.server.server_optimizer import ServerOptimizer

                server_optimizer = ServerOptimizer(self.config, self.logger)

                server_type = self.config.server_optimization["server_type"]
                self.logger.info(f"Running server optimization for {server_type}")

                success = False
                message = ""
                script_path = None

                try:
                    # Get server-specific configuration
                    server_config = self.config.server_optimization.get(server_type, {})

                    # Call the unified server optimizer interface
                    success, message, script_path = server_optimizer.optimize_server(
                        server_type=server_type,
                        **server_config
                    )
                except Exception as e:
                    success = False
                    message = f"Error during server optimization: {str(e)}"
                    script_path = None
                    self.logger.error(message)

                if success:
                    self.logger.info(f"Server optimization successful: {message}")
                    if script_path:
                        self.logger.info(f"Generated script at: {script_path}")
                    return 0
                else:
                    self.logger.error(f"Server optimization failed: {message}")
                    return 1

            # Check if FFmpeg is available
            if not self.encoder.check_ffmpeg():
                self.logger.error("FFmpeg is not available. Please install FFmpeg.")
                return 1

            # Validate input/output directories
            if not self.config.input_folder.exists():
                self.logger.error(f"Input directory does not exist: {self.config.input_folder}")
                return 1

            # Ensure output directory exists
            ensure_dir_exists(self.config.output_folder)

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

        # Unload plugins
        if self.plugin_manager and self.plugins:
            self.logger.info("Unloading plugins...")
            from pyprocessor.utils.core.plugin_manager import unload_all_plugins
            unload_all_plugins()
            self.logger.info("All plugins unloaded")

        # Log shutdown
        if self.logger:
            self.logger.info("Application shutdown complete")
