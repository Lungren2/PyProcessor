import logging
import sys
from datetime import datetime
from pathlib import Path

class Logger:
    """Advanced logging system with rotation and detailed levels"""

    def __init__(self, unused_param=None, max_logs=10, level=logging.INFO):
        # Get the video_processor package directory
        import video_processor
        package_dir = Path(video_processor.__file__).parent

        # Use a dedicated logs directory in the package
        self.log_dir = package_dir / "logs"
        self.max_logs = max_logs

        # Create logs directory if it doesn't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Generate log filename with detailed information
        now = datetime.now()
        date_part = now.strftime("%Y-%m-%d")
        time_part = now.strftime("%H-%M-%S")

        # Get log level as a string
        if isinstance(level, str):
            level_str = level.lower()
        else:
            level_map = {
                logging.DEBUG: "debug",
                logging.INFO: "info",
                logging.WARNING: "warn",
                logging.ERROR: "error",
                logging.CRITICAL: "critical"
            }
            level_str = level_map.get(level, "info")

        # Get username for the log file
        import getpass
        username = getpass.getuser()

        # Get system info
        import platform
        system_info = platform.system().lower()

        # Create a descriptive filename
        filename = f"vp_{date_part}_{time_part}_{level_str}_{username}_{system_info}.log"
        self.log_file = self.log_dir / filename

        # Set up logger
        self.logger = logging.getLogger('video_processor')
        self.logger.setLevel(level)

        # Remove existing handlers if necessary
        if self.logger.hasHandlers():
            for handler in self.logger.handlers:
                self.logger.removeHandler(handler)

        # Create file handler
        self.file_handler = logging.FileHandler(self.log_file)
        self.file_handler.setLevel(level)

        # Create console handler
        self.console_handler = logging.StreamHandler(sys.stdout)
        self.console_handler.setLevel(level)

        # Create formatters
        detailed_formatter = logging.Formatter(
            '[%(asctime)s][%(levelname)s] %(message)s',
            '%Y-%m-%d %H:%M:%S'
        )
        simple_formatter = logging.Formatter('[%(levelname)s] %(message)s')

        # Set formatters
        self.file_handler.setFormatter(detailed_formatter)
        self.console_handler.setFormatter(simple_formatter)

        # Add handlers to logger
        self.logger.addHandler(self.file_handler)
        self.logger.addHandler(self.console_handler)

        # Perform log rotation
        self._rotate_logs()

        self.info(f"Logging initialized: {self.log_file}")

    def _rotate_logs(self):
        """Delete old log files if there are more than max_logs"""
        try:
            log_files = list(self.log_dir.glob("vp_*.log"))

            # Sort by modification time (oldest first)
            log_files.sort(key=lambda x: x.stat().st_mtime)

            # If we have more logs than allowed, delete the oldest ones
            if len(log_files) > self.max_logs:
                for old_log in log_files[:-self.max_logs]:
                    try:
                        old_log.unlink()
                        print(f"Deleted old log: {old_log}")
                    except Exception as e:
                        print(f"Failed to delete log {old_log}: {str(e)}")
        except Exception as e:
            print(f"Error during log rotation: {str(e)}")

    def debug(self, message):
        """Log a debug message"""
        self.logger.debug(message)

    def info(self, message):
        """Log an info message"""
        self.logger.info(message)

    def warning(self, message):
        """Log a warning message"""
        self.logger.warning(message)

    def error(self, message):
        """Log an error message"""
        self.logger.error(message)

    def critical(self, message):
        """Log a critical message"""
        self.logger.critical(message)

    def set_level(self, level):
        """Set the logging level"""
        self.logger.setLevel(level)
        self.file_handler.setLevel(level)

    def get_log_content(self, lines=50):
        """Get the most recent log content"""
        if not self.log_file.exists():
            return "Log file not found"

        try:
            with open(self.log_file, 'r') as f:
                # Read all lines and get the last 'lines' number
                all_lines = f.readlines()
                return ''.join(all_lines[-lines:])
        except Exception as e:
            return f"Error reading log: {str(e)}"
