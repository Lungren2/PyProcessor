"""
Performance tests for the GUI components.
"""
import os
import sys
import time
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from PyQt5.QtWidgets import QApplication

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the modules to test
from pyprocessor.utils.config import Config
from pyprocessor.utils.logging import Logger
from pyprocessor.processing.file_manager import FileManager
from pyprocessor.processing.encoder import FFmpegEncoder
from pyprocessor.processing.scheduler import ProcessingScheduler
from pyprocessor.gui.main_window import MainWindow
from pyprocessor.gui.progress_widget import ProcessingProgressWidget
from pyprocessor.gui.settings_widgets import (
    EncodingSettingsWidget, ProcessingSettingsWidget, AdvancedSettingsWidget,
    ServerOptimizationWidget
)

# Import performance test base
from tests.performance.test_performance_base import PerformanceTest, PerformanceResult, MemoryUsage, time_function

# Create a QApplication instance for testing
app = QApplication.instance()
if app is None:
    app = QApplication([])

class MainWindowInitializationPerformanceTest(PerformanceTest):
    """Test the performance of main window initialization."""

    def __init__(self, iterations: int = 5):
        """
        Initialize the test.

        Args:
            iterations: Number of iterations to run
        """
        super().__init__("Main Window Initialization", iterations)
        self.temp_dir = None
        self.input_dir = None
        self.output_dir = None
        self.config = None
        self.logger = None
        self.file_manager = None
        self.encoder = None
        self.scheduler = None
        self.theme_manager = None

    def setup(self) -> None:
        """Set up the test environment."""
        # Create temporary directories
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_dir = Path(self.temp_dir.name) / "input"
        self.output_dir = Path(self.temp_dir.name) / "output"
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

        # Create config
        self.config = Config()
        self.config.input_folder = self.input_dir
        self.config.output_folder = self.output_dir

        # Create logger
        self.logger = Logger(level="INFO")

        # Create file manager
        self.file_manager = FileManager(self.config, self.logger)

        # Create encoder
        self.encoder = FFmpegEncoder(self.config, self.logger)

        # Create scheduler
        self.scheduler = ProcessingScheduler(self.config, self.logger, self.file_manager, self.encoder)

        # Create theme manager mock
        self.theme_manager = MagicMock()

    def teardown(self) -> None:
        """Clean up the test environment."""
        if self.temp_dir:
            self.temp_dir.cleanup()

    def run_iteration(self) -> PerformanceResult:
        """Run a single iteration of the test."""
        _, execution_time = time_function(
            MainWindow,
            self.config, self.logger, self.file_manager,
            self.encoder, self.scheduler, self.theme_manager
        )
        # Create a dummy memory usage object with zero values
        memory_usage = MemoryUsage(0, 0, 0)
        return PerformanceResult(execution_time, memory_usage)

class ProgressWidgetUpdatePerformanceTest(PerformanceTest):
    """Test the performance of progress widget updates."""

    def __init__(self, update_count: int, iterations: int = 5):
        """
        Initialize the test.

        Args:
            update_count: Number of progress updates to perform
            iterations: Number of iterations to run
        """
        super().__init__(f"Progress Widget Update ({update_count} updates)", iterations)
        self.update_count = update_count
        self.progress_widget = None

    def setup(self) -> None:
        """Set up the test environment."""
        self.progress_widget = ProcessingProgressWidget()
        self.progress_widget.show()  # Need to show for accurate rendering performance

    def teardown(self) -> None:
        """Clean up the test environment."""
        if self.progress_widget:
            self.progress_widget.hide()
            self.progress_widget.deleteLater()
            self.progress_widget = None

    def run_iteration(self) -> PerformanceResult:
        """Run a single iteration of the test."""
        start_time = time.time()

        # Perform multiple progress updates
        for i in range(self.update_count):
            filename = f"test_file_{i}.mp4"
            file_progress = (i % 100) + 1  # 1-100
            current = i + 1
            total = self.update_count

            self.progress_widget.update_file_progress(filename, file_progress)
            self.progress_widget.update_overall_progress(current, total)

            # Process events to ensure UI updates
            QApplication.processEvents()

        end_time = time.time()
        execution_time = end_time - start_time
        # Create a dummy memory usage object with zero values
        memory_usage = MemoryUsage(0, 0, 0)
        return PerformanceResult(execution_time, memory_usage)

class TabSwitchingPerformanceTest(PerformanceTest):
    """Test the performance of switching between tabs in the main window."""

    def __init__(self, switch_count: int, iterations: int = 5):
        """
        Initialize the test.

        Args:
            switch_count: Number of tab switches to perform
            iterations: Number of iterations to run
        """
        super().__init__(f"Tab Switching ({switch_count} switches)", iterations)
        self.switch_count = switch_count
        self.main_window = None
        self.config = None
        self.logger = None
        self.file_manager = None
        self.encoder = None
        self.scheduler = None
        self.theme_manager = None

    def setup(self) -> None:
        """Set up the test environment."""
        # Create config
        self.config = Config()

        # Create logger
        self.logger = Logger(level="INFO")

        # Create file manager
        self.file_manager = FileManager(self.config, self.logger)

        # Create encoder
        self.encoder = FFmpegEncoder(self.config, self.logger)

        # Create scheduler
        self.scheduler = ProcessingScheduler(self.config, self.logger, self.file_manager, self.encoder)

        # Create theme manager mock
        self.theme_manager = MagicMock()

        # Create main window
        self.main_window = MainWindow(
            self.config, self.logger, self.file_manager,
            self.encoder, self.scheduler, self.theme_manager
        )
        self.main_window.show()

    def teardown(self) -> None:
        """Clean up the test environment."""
        if self.main_window:
            self.main_window.hide()
            self.main_window.deleteLater()
            self.main_window = None

    def run_iteration(self) -> PerformanceResult:
        """Run a single iteration of the test."""
        start_time = time.time()

        # Switch between tabs multiple times
        tab_count = self.main_window.tab_widget.count()
        for i in range(self.switch_count):
            tab_index = i % tab_count
            self.main_window.tab_widget.setCurrentIndex(tab_index)
            QApplication.processEvents()

        end_time = time.time()
        execution_time = end_time - start_time
        # Create a dummy memory usage object with zero values
        memory_usage = MemoryUsage(0, 0, 0)
        return PerformanceResult(execution_time, memory_usage)

class SettingsWidgetLoadPerformanceTest(PerformanceTest):
    """Test the performance of loading settings into widgets."""

    def __init__(self, iterations: int = 5):
        """
        Initialize the test.

        Args:
            iterations: Number of iterations to run
        """
        super().__init__("Settings Widget Load", iterations)
        self.config = None
        self.logger = None
        self.encoding_widget = None
        self.processing_widget = None
        self.advanced_widget = None
        self.server_widget = None

    def setup(self) -> None:
        """Set up the test environment."""
        # Create config with complex settings
        self.config = Config()
        self.config.ffmpeg_params = {
            "video_encoder": "libx264",
            "preset": "medium",
            "tune": "film",
            "include_audio": True,
            "audio_encoder": "aac",
            "audio_bitrate": "128k",
            "fps": 30,
            "bitrates": {
                "1080p": "5000k",
                "720p": "3000k",
                "480p": "1500k",
                "360p": "800k"
            }
        }
        self.config.file_rename_pattern = r"(.+?)_\d+p"
        self.config.file_validation_pattern = r".+_\d+p\.mp4$"
        self.config.folder_organization_pattern = r"(.+?)_"
        self.config.max_parallel_jobs = 4
        self.config.auto_rename_files = True
        self.config.auto_organize_folders = True

        # Create logger
        self.logger = Logger(level="INFO")

        # Create widgets
        self.encoding_widget = EncodingSettingsWidget(self.config)
        self.processing_widget = ProcessingSettingsWidget(self.config, self.logger)
        self.advanced_widget = AdvancedSettingsWidget(self.config)
        self.server_widget = ServerOptimizationWidget(self.config, self.logger)

    def teardown(self) -> None:
        """Clean up the test environment."""
        if self.encoding_widget:
            self.encoding_widget.deleteLater()
            self.encoding_widget = None

        if self.processing_widget:
            self.processing_widget.deleteLater()
            self.processing_widget = None

        if self.advanced_widget:
            self.advanced_widget.deleteLater()
            self.advanced_widget = None

        if self.server_widget:
            self.server_widget.deleteLater()
            self.server_widget = None

    def run_iteration(self) -> PerformanceResult:
        """Run a single iteration of the test."""
        start_time = time.time()

        # Load settings into widgets
        self.encoding_widget.load_config_values()
        self.processing_widget.load_config_values()
        self.advanced_widget.load_config_values()
        self.server_widget.load_config_values()

        # Process events to ensure UI updates
        QApplication.processEvents()

        end_time = time.time()
        execution_time = end_time - start_time
        # Create a dummy memory usage object with zero values
        memory_usage = MemoryUsage(0, 0, 0)
        return PerformanceResult(execution_time, memory_usage)

def test_main_window_initialization_performance():
    """Test the performance of main window initialization."""
    test = MainWindowInitializationPerformanceTest()
    results = test.run()
    test.print_results(results)

    # Assert that the performance is reasonable
    assert results["avg_time"] < 0.5, "Main window initialization is too slow"

def test_progress_widget_update_performance():
    """Test the performance of progress widget updates with different update counts."""
    update_counts = [10, 100, 1000]

    for update_count in update_counts:
        test = ProgressWidgetUpdatePerformanceTest(update_count)
        results = test.run()
        test.print_results(results)

        # Assert that the performance is reasonable
        if update_count == 10:
            assert results["avg_time"] < 0.1, f"Progress widget update for {update_count} updates is too slow"
        elif update_count == 100:
            assert results["avg_time"] < 0.5, f"Progress widget update for {update_count} updates is too slow"
        elif update_count == 1000:
            assert results["avg_time"] < 5.0, f"Progress widget update for {update_count} updates is too slow"

def test_tab_switching_performance():
    """Test the performance of tab switching with different switch counts."""
    switch_counts = [10, 50, 100]

    for switch_count in switch_counts:
        test = TabSwitchingPerformanceTest(switch_count)
        results = test.run()
        test.print_results(results)

        # Assert that the performance is reasonable
        if switch_count == 10:
            assert results["avg_time"] < 0.1, f"Tab switching for {switch_count} switches is too slow"
        elif switch_count == 50:
            assert results["avg_time"] < 0.5, f"Tab switching for {switch_count} switches is too slow"
        elif switch_count == 100:
            assert results["avg_time"] < 1.0, f"Tab switching for {switch_count} switches is too slow"

def test_settings_widget_load_performance():
    """Test the performance of loading settings into widgets."""
    test = SettingsWidgetLoadPerformanceTest()
    results = test.run()
    test.print_results(results)

    # Assert that the performance is reasonable
    assert results["avg_time"] < 0.1, "Settings widget load is too slow"

if __name__ == "__main__":
    test_main_window_initialization_performance()
    test_progress_widget_update_performance()
    test_tab_switching_performance()
    test_settings_widget_load_performance()
