import sys
import os
import argparse
import signal
from pathlib import Path
import time

from PyQt5.QtWidgets import QApplication

from video_processor.utils.config import Config
from video_processor.utils.logging import Logger
from video_processor.utils.theme_manager import ThemeManager
from video_processor.processing.file_manager import FileManager
from video_processor.processing.encoder import FFmpegEncoder
from video_processor.processing.scheduler import ProcessingScheduler
from video_processor.gui.main_window import show_main_window

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

def run_cli_mode(config, logger, file_manager, encoder, scheduler):
    """Run in command-line mode"""
    try:
        logger.info("Running in command-line mode")

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
