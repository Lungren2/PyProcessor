import sys
import argparse
import signal
from pathlib import Path
import time

from PyQt5.QtWidgets import QApplication

from pyprocessor.utils.config import Config
from pyprocessor.utils.logging import Logger
from pyprocessor.utils.theme_manager import ThemeManager
from pyprocessor.processing.file_manager import FileManager
from pyprocessor.processing.encoder import FFmpegEncoder
from pyprocessor.processing.scheduler import ProcessingScheduler
from pyprocessor.gui.main_window import show_main_window

# Global references for clean shutdown
config = None
logger = None
encoder = None
scheduler = None

def signal_handler(sig, frame):
    """Handle termination signals for clean shutdown"""
    global logger, encoder, scheduler

    if logger:
        logger.info("Termination signal received. Shutting down...")

    # Stop any active FFmpeg process
    if encoder:
        encoder.terminate()

    # Request abort for scheduler
    if scheduler and scheduler.is_running:
        scheduler.request_abort()

    if logger:
        logger.info("Shutdown complete")

    sys.exit(0)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Video Processor")

    # File paths
    parser.add_argument("--input", help="Input directory path")
    parser.add_argument("--output", help="Output directory path")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--profile", help="Configuration profile name")

    # Processing options
    parser.add_argument("--encoder", choices=["libx265", "h264_nvenc", "libx264"],
                       help="Video encoder to use")
    parser.add_argument("--preset", choices=["ultrafast", "veryfast", "medium"],
                       help="Encoding preset")
    parser.add_argument("--tune", choices=["zerolatency", "film", "animation"],
                       help="Encoding tune parameter")
    parser.add_argument("--fps", type=int, choices=[30, 60, 120],
                       help="Frames per second")
    parser.add_argument("--no-audio", action="store_true",
                       help="Exclude audio from output")
    parser.add_argument("--jobs", type=int, help="Number of parallel jobs")

    # Execution options
    parser.add_argument("--no-gui", action="store_true",
                       help="Run without GUI")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose logging")

    # Server optimization options
    server_group = parser.add_argument_group('Server Optimization')
    server_group.add_argument("--optimize-server", choices=["iis", "nginx", "linux"],
                       help="Optimize server for video streaming")
    server_group.add_argument("--site-name", default="Default Web Site",
                       help="IIS site name (for --optimize-server=iis)")
    server_group.add_argument("--video-path",
                       help="Path to video content directory (for --optimize-server=iis)")
    server_group.add_argument("--enable-http2", action="store_true", default=True,
                       help="Enable HTTP/2 protocol (for --optimize-server=iis)")
    server_group.add_argument("--enable-http3", action="store_true", default=False,
                       help="Enable HTTP/3 with Alt-Svc headers for auto-upgrading (for --optimize-server=iis or nginx)")
    server_group.add_argument("--enable-cors", action="store_true", default=True,
                       help="Enable CORS headers (for --optimize-server=iis)")
    server_group.add_argument("--cors-origin", default="*",
                       help="CORS origin value (for --optimize-server=iis)")
    server_group.add_argument("--output-config",
                       help="Output path for server configuration (for --optimize-server=nginx)")
    server_group.add_argument("--server-name", default="yourdomain.com",
                       help="Server name for configuration (for --optimize-server=nginx)")
    server_group.add_argument("--apply-changes", action="store_true",
                       help="Apply changes directly (for --optimize-server=linux)")

    return parser.parse_args()

def apply_args_to_config(args, config):
    """Apply command line arguments to configuration"""
    if args.input:
        config.input_folder = Path(args.input)

    if args.output:
        config.output_folder = Path(args.output)

    if args.encoder:
        config.ffmpeg_params["video_encoder"] = args.encoder

    if args.preset:
        config.ffmpeg_params["preset"] = args.preset

    if args.tune:
        config.ffmpeg_params["tune"] = args.tune

    if args.fps:
        config.ffmpeg_params["fps"] = args.fps

    if args.no_audio:
        config.ffmpeg_params["include_audio"] = False

    if args.jobs:
        config.max_parallel_jobs = max(1, args.jobs)

    # Apply server optimization options
    if args.optimize_server:
        config.server_optimization["enabled"] = True
        config.server_optimization["server_type"] = args.optimize_server

        # IIS options
        if args.optimize_server == "iis":
            if args.site_name:
                config.server_optimization["iis"]["site_name"] = args.site_name
            if args.video_path:
                config.server_optimization["iis"]["video_path"] = args.video_path
            if args.enable_http2 is not None:
                config.server_optimization["iis"]["enable_http2"] = args.enable_http2
            if args.enable_http3 is not None:
                config.server_optimization["iis"]["enable_http3"] = args.enable_http3
            if args.enable_cors is not None:
                config.server_optimization["iis"]["enable_cors"] = args.enable_cors
            if args.cors_origin:
                config.server_optimization["iis"]["cors_origin"] = args.cors_origin

        # Nginx options
        elif args.optimize_server == "nginx":
            if args.output_config:
                config.server_optimization["nginx"]["output_path"] = args.output_config
            if args.server_name:
                config.server_optimization["nginx"]["server_name"] = args.server_name
            if args.enable_http3 is not None:
                config.server_optimization["nginx"]["enable_http3"] = args.enable_http3

        # Linux options
        elif args.optimize_server == "linux":
            if args.apply_changes is not None:
                config.server_optimization["linux"]["apply_changes"] = args.apply_changes

def run_cli_mode(config, logger, file_manager, encoder, scheduler):
    """Run in command-line mode"""
    try:
        logger.info("Running in command-line mode")

        # Check if server optimization is requested
        if config.server_optimization.get("enabled", False):
            from pyprocessor.utils.server_optimizer import ServerOptimizer
            server_optimizer = ServerOptimizer(config, logger)

            server_type = config.server_optimization["server_type"]
            logger.info(f"Running server optimization for {server_type}")

            success = False
            message = ""
            script_path = None

            try:
                if server_type == "iis":
                    iis_config = config.server_optimization["iis"]
                    success, message = server_optimizer.optimize_iis(
                        site_name=iis_config["site_name"],
                        video_path=iis_config["video_path"],
                        enable_http2=iis_config["enable_http2"],
                        enable_cors=iis_config["enable_cors"],
                        cors_origin=iis_config["cors_origin"]
                    )
                elif server_type == "nginx":
                    nginx_config = config.server_optimization["nginx"]
                    success, message = server_optimizer.optimize_nginx(
                        output_path=nginx_config["output_path"],
                        server_name=nginx_config["server_name"],
                        ssl_enabled=nginx_config.get("ssl_enabled", True)
                    )
                elif server_type == "linux":
                    linux_config = config.server_optimization["linux"]
                    success, message, script_path = server_optimizer.optimize_linux(
                        apply_changes=linux_config["apply_changes"]
                    )
            except Exception as e:
                success = False
                message = f"Error during server optimization: {str(e)}"
                logger.error(message)

            if success:
                logger.info(f"Server optimization successful: {message}")
                if script_path:
                    logger.info(f"Generated script at: {script_path}")
                return 0
            else:
                logger.error(f"Server optimization failed: {message}")
                return 1

        # Validate input/output directories
        if not config.input_folder.exists():
            logger.error(f"Input directory does not exist: {config.input_folder}")
            return 1

        # Ensure output directory exists
        config.output_folder.mkdir(parents=True, exist_ok=True)

        # Validate configuration
        errors, warnings = config.validate()
        if errors:
            for error in errors:
                logger.error(f"Configuration error: {error}")
            return 1

        if warnings:
            for warning in warnings:
                logger.warning(f"Configuration warning: {warning}")

        # Process files
        start_time = time.time()

        # Step 1: Rename files (if enabled)
        if config.auto_rename_files:
            logger.info("Renaming files...")
            file_manager.rename_files()

        # Step 2: Process videos
        logger.info("Processing videos...")
        success = scheduler.process_videos()

        # Step 3: Organize folders (if enabled)
        if config.auto_organize_folders:
            logger.info("Organizing folders...")
            file_manager.organize_folders()

        # Log summary
        elapsed_time = time.time() - start_time
        logger.info(f"Processing completed in {elapsed_time/60:.2f} minutes")

        return 0 if success else 1

    except Exception as e:
        logger.error(f"Error in command-line mode: {str(e)}")
        return 1

def main():
    """Main application entry point"""
    global config, logger, encoder, scheduler

    # Parse command line arguments
    args = parse_args()

    # Initialize config
    config = Config()

    # Load configuration from file or profile
    if args.config:
        config.load(args.config)
    elif args.profile:
        config.load(profile_name=args.profile)

    # Apply command line arguments
    apply_args_to_config(args, config)

    # Validate configuration
    errors, warnings = config.validate()

    # Initialize logger
    log_level = "DEBUG" if args.verbose else "INFO"
    logger = Logger(level=log_level)

    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        return 1

    if warnings:
        for warning in warnings:
            logger.warning(f"Configuration warning: {warning}")

    # Initialize components
    file_manager = FileManager(config, logger)
    encoder = FFmpegEncoder(config, logger)
    scheduler = ProcessingScheduler(config, logger, file_manager, encoder)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

    # Run in CLI or GUI mode
    if args.no_gui:
        return run_cli_mode(config, logger, file_manager, encoder, scheduler)
    else:
        # Create QApplication instance
        app = QApplication(sys.argv)

        # Initialize and setup theme manager
        try:
            theme_manager = ThemeManager(app, logger)
            theme_manager.setup_theme()
        except Exception as e:
            logger.error(f"Failed to initialize theme manager: {str(e)}")
            theme_manager = None

        return show_main_window(app, config, logger, file_manager, encoder, scheduler, theme_manager)

if __name__ == "__main__":
    sys.exit(main())
