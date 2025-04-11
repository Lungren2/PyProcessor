"""
Unit tests for GUI components.
"""
import pytest
import os
import sys
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import Qt

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the modules to test
from video_processor.utils.config import Config
from video_processor.utils.logging import Logger
from video_processor.gui.main_window import MainWindow
from video_processor.gui.settings_widgets import (
    EncodingSettingsWidget, ProcessingSettingsWidget, AdvancedSettingsWidget
)
from video_processor.gui.progress_widget import ProcessingProgressWidget

# Create a QApplication instance for testing
app = QApplication.instance()
if app is None:
    app = QApplication([])

class TestMainWindow:
    """Test the MainWindow class"""
    
    def setup_method(self):
        """Set up test environment before each test method"""
        # Create mocked components
        self.config = MagicMock(spec=Config)
        self.logger = MagicMock(spec=Logger)
        self.file_manager = MagicMock()
        self.encoder = MagicMock()
        self.scheduler = MagicMock()
        self.theme_manager = MagicMock()
        
        # Configure mocks
        self.config.input_folder = "/test/input"
        self.config.output_folder = "/test/output"
        self.config.ffmpeg_params = {
            "encoder": "libx264",
            "preset": "medium",
            "tune": "film",
            "fps": 30,
            "include_audio": True,
            "bitrates": {
                "1080p": "5000k",
                "720p": "3000k",
                "480p": "1500k",
                "360p": "800k"
            }
        }
        self.config.max_parallel_jobs = 2
        self.config.auto_rename_files = True
        self.config.auto_organize_folders = True
        
        # Create main window
        self.main_window = MainWindow(
            self.config, self.logger, self.file_manager,
            self.encoder, self.scheduler, self.theme_manager
        )
    
    def test_initialization(self):
        """Test that the MainWindow initializes correctly"""
        # Check that the window was created
        assert isinstance(self.main_window, QMainWindow)
        
        # Check that components were set
        assert self.main_window.config == self.config
        assert self.main_window.logger == self.logger
        assert self.main_window.file_manager == self.file_manager
        assert self.main_window.encoder == self.encoder
        assert self.main_window.scheduler == self.scheduler
        assert self.main_window.theme_manager == self.theme_manager
    
    def test_input_output_paths(self):
        """Test setting input and output paths"""
        # Get the input and output path fields
        input_path_field = self.main_window.input_path_field
        output_path_field = self.main_window.output_path_field
        
        # Check initial values
        assert input_path_field.text() == str(self.config.input_folder)
        assert output_path_field.text() == str(self.config.output_folder)
        
        # Set new values
        new_input_path = "/new/input"
        new_output_path = "/new/output"
        input_path_field.setText(new_input_path)
        output_path_field.setText(new_output_path)
        
        # Trigger path changed signals
        self.main_window.input_path_changed()
        self.main_window.output_path_changed()
        
        # Check that config was updated
        self.config.input_folder = new_input_path
        self.config.output_folder = new_output_path
    
    @patch('PyQt5.QtWidgets.QFileDialog.getExistingDirectory')
    def test_browse_input_path(self, mock_get_directory):
        """Test browsing for input path"""
        # Mock QFileDialog.getExistingDirectory to return a path
        mock_get_directory.return_value = "/browsed/input"
        
        # Click the browse input button
        self.main_window.browse_input_button.click()
        
        # Check that QFileDialog.getExistingDirectory was called
        mock_get_directory.assert_called_once()
        
        # Check that the input path field was updated
        assert self.main_window.input_path_field.text() == "/browsed/input"
    
    @patch('PyQt5.QtWidgets.QFileDialog.getExistingDirectory')
    def test_browse_output_path(self, mock_get_directory):
        """Test browsing for output path"""
        # Mock QFileDialog.getExistingDirectory to return a path
        mock_get_directory.return_value = "/browsed/output"
        
        # Click the browse output button
        self.main_window.browse_output_button.click()
        
        # Check that QFileDialog.getExistingDirectory was called
        mock_get_directory.assert_called_once()
        
        # Check that the output path field was updated
        assert self.main_window.output_path_field.text() == "/browsed/output"
    
    def test_start_processing(self):
        """Test starting processing"""
        # Mock the scheduler's process_videos method
        self.scheduler.process_videos.return_value = True
        
        # Click the start button
        self.main_window.start_button.click()
        
        # Check that processing was started
        assert self.main_window.processing_thread is not None
    
    def test_stop_processing(self):
        """Test stopping processing"""
        # Set up a mock processing thread
        self.main_window.processing_thread = MagicMock()
        self.main_window.is_processing = True
        
        # Click the stop button
        self.main_window.stop_button.click()
        
        # Check that abort was requested
        self.scheduler.request_abort.assert_called_once()

class TestEncodingSettingsWidget:
    """Test the EncodingSettingsWidget class"""
    
    def setup_method(self):
        """Set up test environment before each test method"""
        # Create mocked components
        self.config = MagicMock(spec=Config)
        self.logger = MagicMock(spec=Logger)
        
        # Configure mocks
        self.config.ffmpeg_params = {
            "encoder": "libx264",
            "preset": "medium",
            "tune": "film",
            "fps": 30,
            "include_audio": True,
            "bitrates": {
                "1080p": "5000k",
                "720p": "3000k",
                "480p": "1500k",
                "360p": "800k"
            }
        }
        
        # Create widget
        self.widget = EncodingSettingsWidget(self.config, self.logger)
    
    def test_initialization(self):
        """Test that the EncodingSettingsWidget initializes correctly"""
        # Check that components were set
        assert self.widget.config == self.config
        assert self.widget.logger == self.logger
        
        # Check that controls were initialized with correct values
        assert self.widget.encoder_combo.currentText() == self.config.ffmpeg_params["encoder"]
        assert self.widget.preset_combo.currentText() == self.config.ffmpeg_params["preset"]
        assert self.widget.tune_combo.currentText() == self.config.ffmpeg_params["tune"]
        assert self.widget.fps_spin.value() == self.config.ffmpeg_params["fps"]
        assert self.widget.audio_check.isChecked() == self.config.ffmpeg_params["include_audio"]
    
    def test_encoder_changed(self):
        """Test changing the encoder"""
        # Change the encoder
        self.widget.encoder_combo.setCurrentText("libx265")
        
        # Check that config was updated
        assert self.config.ffmpeg_params["encoder"] == "libx265"
    
    def test_preset_changed(self):
        """Test changing the preset"""
        # Change the preset
        self.widget.preset_combo.setCurrentText("fast")
        
        # Check that config was updated
        assert self.config.ffmpeg_params["preset"] == "fast"
    
    def test_tune_changed(self):
        """Test changing the tune"""
        # Change the tune
        self.widget.tune_combo.setCurrentText("animation")
        
        # Check that config was updated
        assert self.config.ffmpeg_params["tune"] == "animation"
    
    def test_fps_changed(self):
        """Test changing the FPS"""
        # Change the FPS
        self.widget.fps_spin.setValue(60)
        
        # Check that config was updated
        assert self.config.ffmpeg_params["fps"] == 60
    
    def test_audio_toggled(self):
        """Test toggling audio"""
        # Toggle audio off
        self.widget.audio_check.setChecked(False)
        
        # Check that config was updated
        assert self.config.ffmpeg_params["include_audio"] is False
        
        # Toggle audio on
        self.widget.audio_check.setChecked(True)
        
        # Check that config was updated
        assert self.config.ffmpeg_params["include_audio"] is True

class TestProcessingSettingsWidget:
    """Test the ProcessingSettingsWidget class"""
    
    def setup_method(self):
        """Set up test environment before each test method"""
        # Create mocked components
        self.config = MagicMock(spec=Config)
        self.logger = MagicMock(spec=Logger)
        
        # Configure mocks
        self.config.max_parallel_jobs = 2
        self.config.auto_rename_files = True
        self.config.auto_organize_folders = True
        
        # Create widget
        self.widget = ProcessingSettingsWidget(self.config, self.logger)
    
    def test_initialization(self):
        """Test that the ProcessingSettingsWidget initializes correctly"""
        # Check that components were set
        assert self.widget.config == self.config
        assert self.widget.logger == self.logger
        
        # Check that controls were initialized with correct values
        assert self.widget.parallel_jobs_spin.value() == self.config.max_parallel_jobs
        assert self.widget.auto_rename_check.isChecked() == self.config.auto_rename_files
        assert self.widget.auto_organize_check.isChecked() == self.config.auto_organize_folders
    
    def test_parallel_jobs_changed(self):
        """Test changing the number of parallel jobs"""
        # Change the number of parallel jobs
        self.widget.parallel_jobs_spin.setValue(4)
        
        # Check that config was updated
        assert self.config.max_parallel_jobs == 4
    
    def test_auto_rename_toggled(self):
        """Test toggling auto rename"""
        # Toggle auto rename off
        self.widget.auto_rename_check.setChecked(False)
        
        # Check that config was updated
        assert self.config.auto_rename_files is False
        
        # Toggle auto rename on
        self.widget.auto_rename_check.setChecked(True)
        
        # Check that config was updated
        assert self.config.auto_rename_files is True
    
    def test_auto_organize_toggled(self):
        """Test toggling auto organize"""
        # Toggle auto organize off
        self.widget.auto_organize_check.setChecked(False)
        
        # Check that config was updated
        assert self.config.auto_organize_folders is False
        
        # Toggle auto organize on
        self.widget.auto_organize_check.setChecked(True)
        
        # Check that config was updated
        assert self.config.auto_organize_folders is True

class TestProcessingProgressWidget:
    """Test the ProcessingProgressWidget class"""
    
    def setup_method(self):
        """Set up test environment before each test method"""
        # Create widget
        self.widget = ProcessingProgressWidget()
    
    def test_initialization(self):
        """Test that the ProcessingProgressWidget initializes correctly"""
        # Check initial state
        assert self.widget.current_file_label.text() == "No file processing"
        assert self.widget.file_progress_bar.value() == 0
        assert self.widget.overall_progress_bar.value() == 0
        assert self.widget.output_files_list.count() == 0
    
    def test_update_progress(self):
        """Test updating progress"""
        # Update progress
        self.widget.update_progress("test.mp4", 50, 1, 2)
        
        # Check that progress was updated
        assert self.widget.current_file_label.text() == "Processing: test.mp4"
        assert self.widget.file_progress_bar.value() == 50
        assert self.widget.overall_progress_bar.value() == 50  # 1/2 = 50%
    
    def test_add_output_file(self):
        """Test adding an output file"""
        # Add an output file
        self.widget.add_output_file("output.mp4", "1080p")
        
        # Check that the file was added
        assert self.widget.output_files_list.count() == 1
        assert self.widget.output_files_list.item(0).text() == "output.mp4 (1080p)"
    
    def test_reset(self):
        """Test resetting the widget"""
        # Set up some state
        self.widget.update_progress("test.mp4", 50, 1, 2)
        self.widget.add_output_file("output.mp4", "1080p")
        
        # Reset
        self.widget.reset()
        
        # Check that state was reset
        assert self.widget.current_file_label.text() == "No file processing"
        assert self.widget.file_progress_bar.value() == 0
        assert self.widget.overall_progress_bar.value() == 0
        assert self.widget.output_files_list.count() == 0
