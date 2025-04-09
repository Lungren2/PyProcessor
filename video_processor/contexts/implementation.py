# Enhanced Video Processor Implementation

## 1. Enhanced Configuration and Logging System

### Improved Configuration System (utils/config.py)

# video_processor/utils/config.py
import os
import json
import multiprocessing
from pathlib import Path
import datetime

class Config:
    """Enhanced configuration management for video processor"""
    
    def __init__(self):
        # Base directories
        self.input_folder = Path(r"C:\inetpub\wwwroot\media\input")
        self.output_folder = Path(r"C:\inetpub\wwwroot\media\output")
        
        # FFmpeg parameters
        self.ffmpeg_params = {
            "video_encoder": "libx265",
            "preset": "ultrafast",
            "tune": "zerolatency",
            "fps": 60,
            "include_audio": True,  # New option to include/exclude audio
            "bitrates": {
                "1080p": "11000k",
                "720p": "6500k",
                "480p": "4000k",
                "360p": "1500k"
            },
            "audio_bitrates": ["192k", "128k", "96k", "64k"]
        }
        
        # Processing options
        self.max_parallel_jobs = self._calculate_parallel_jobs()
        
        # Additional settings
        self.auto_rename_files = True
        self.auto_organize_folders = True
        self.last_used_profile = "default"
        
        # Create directories if they don't exist
        self._ensure_directories()
    
    def _calculate_parallel_jobs(self):
        """Calculate optimal number of parallel jobs based on CPU cores"""
        cores = multiprocessing.cpu_count()
        return max(1, int(cores * 0.75))
    
    def _ensure_directories(self):
        """Create required directories if they don't exist"""
        try:
            self.input_folder.mkdir(parents=True, exist_ok=True)
            self.output_folder.mkdir(parents=True, exist_ok=True)
            
            # Create a profiles directory in the output folder
            profiles_dir = self.output_folder / "profiles"
            profiles_dir.mkdir(exist_ok=True)
            
            return True
        except Exception as e:
            print(f"Error creating directories: {str(e)}")
            return False
    
    def save(self, filepath=None, profile_name=None):
        """
        Save configuration to file
        
        Args:
            filepath: Optional custom path for saving
            profile_name: Optional profile name to save as
        """
        try:
            # Convert Path objects to strings for JSON serialization
            config_dict = {
                "input_folder": str(self.input_folder),
                "output_folder": str(self.output_folder),
                "ffmpeg_params": self.ffmpeg_params,
                "max_parallel_jobs": self.max_parallel_jobs,
                "auto_rename_files": self.auto_rename_files,
                "auto_organize_folders": self.auto_organize_folders,
                "last_used_profile": self.last_used_profile,
                "saved_at": datetime.datetime.now().isoformat()
            }
            
            # If profile name is provided, save as a profile
            if profile_name:
                profile_path = self.output_folder / "profiles" / f"{profile_name}.json"
                filepath = profile_path
                self.last_used_profile = profile_name
            
            # If no filepath is specified, use default
            if not filepath:
                filepath = self.output_folder / "config.json"
            
            # Ensure directory exists
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            
            # Save the configuration
            with open(filepath, 'w') as f:
                json.dump(config_dict, f, indent=4)
                
            return True
        except Exception as e:
            print(f"Error saving config: {str(e)}")
            return False
    
    def load(self, filepath=None, profile_name=None):
        """
        Load configuration from file
        
        Args:
            filepath: Optional custom path for loading
            profile_name: Optional profile name to load
        """
        try:
            # If profile name is provided, load from profiles directory
            if profile_name:
                filepath = self.output_folder / "profiles" / f"{profile_name}.json"
                self.last_used_profile = profile_name
            
            # If no filepath is specified, use default
            if not filepath:
                filepath = self.output_folder / "config.json"
            
            if not os.path.exists(filepath):
                print(f"Configuration file not found: {filepath}")
                return False
            
            with open(filepath, 'r') as f:
                config_dict = json.load(f)
                
                # Load paths
                if "input_folder" in config_dict:
                    self.input_folder = Path(config_dict["input_folder"])
                if "output_folder" in config_dict:
                    self.output_folder = Path(config_dict["output_folder"])
                
                # Load FFmpeg parameters
                if "ffmpeg_params" in config_dict:
                    self.ffmpeg_params.update(config_dict["ffmpeg_params"])
                    
                # Load other settings
                if "max_parallel_jobs" in config_dict:
                    self.max_parallel_jobs = int(config_dict["max_parallel_jobs"])
                if "auto_rename_files" in config_dict:
                    self.auto_rename_files = bool(config_dict["auto_rename_files"])
                if "auto_organize_folders" in config_dict:
                    self.auto_organize_folders = bool(config_dict["auto_organize_folders"])
                if "last_used_profile" in config_dict:
                    self.last_used_profile = config_dict["last_used_profile"]
                
            return True
        except Exception as e:
            print(f"Error loading config: {str(e)}")
            return False
    
    def get_available_profiles(self):
        """Get a list of available configuration profiles"""
        profiles_dir = self.output_folder / "profiles"
        
        if not profiles_dir.exists():
            return []
        
        profile_files = list(profiles_dir.glob("*.json"))
        profiles = [file.stem for file in profile_files]
        return profiles
    
    def validate(self):
        """Validate configuration and return any errors or warnings"""
        errors = []
        warnings = []
        
        # Check directories
        if not isinstance(self.input_folder, Path):
            try:
                self.input_folder = Path(self.input_folder)
            except:
                errors.append("Invalid input folder path")
        
        if not isinstance(self.output_folder, Path):
            try:
                self.output_folder = Path(self.output_folder)
            except:
                errors.append("Invalid output folder path")
        
        # Check FFmpeg parameters
        valid_encoders = ["libx265", "h264_nvenc", "libx264"]
        if self.ffmpeg_params["video_encoder"] not in valid_encoders:
            warnings.append(f"Invalid encoder: {self.ffmpeg_params['video_encoder']}. Using libx265.")
            self.ffmpeg_params["video_encoder"] = "libx265"
        
        valid_presets = ["ultrafast", "veryfast", "medium", None]
        if self.ffmpeg_params["preset"] not in valid_presets:
            warnings.append(f"Invalid preset: {self.ffmpeg_params['preset']}. Using ultrafast.")
            self.ffmpeg_params["preset"] = "ultrafast"
        
        valid_tunes = ["zerolatency", "film", "animation", None]
        if self.ffmpeg_params["tune"] not in valid_tunes:
            warnings.append(f"Invalid tune: {self.ffmpeg_params['tune']}. Using zerolatency.")
            self.ffmpeg_params["tune"] = "zerolatency"
        
        valid_fps = [30, 60, 120]
        if self.ffmpeg_params["fps"] not in valid_fps:
            warnings.append(f"Invalid FPS: {self.ffmpeg_params['fps']}. Using 60.")
            self.ffmpeg_params["fps"] = 60
        
        # Check audio inclusion (ensure it's boolean)
        if not isinstance(self.ffmpeg_params.get("include_audio", True), bool):
            warnings.append("Invalid audio inclusion setting. Using default (True).")
            self.ffmpeg_params["include_audio"] = True
        
        # Check parallel jobs
        if not isinstance(self.max_parallel_jobs, int) or self.max_parallel_jobs < 1:
            warnings.append(f"Invalid parallel jobs: {self.max_parallel_jobs}. Recalculating.")
            self.max_parallel_jobs = self._calculate_parallel_jobs()
        
        return errors, warnings


### Advanced Logging System (utils/logging.py)


# video_processor/utils/logging.py
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
import re

class Logger:
    """Advanced logging system with rotation and detailed levels"""
    
    def __init__(self, output_folder, max_logs=10, level=logging.INFO):
        self.output_folder = Path(output_folder)
        self.log_dir = self.output_folder / "logs"
        self.max_logs = max_logs
        
        # Create logs directory if it doesn't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.log_file = self.log_dir / f"processing_log_{timestamp}.txt"
        
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
            log_files = list(self.log_dir.glob("processing_log_*.txt"))
            
            # Sort by creation time (oldest first)
            log_files.sort(key=lambda x: x.stat().st_ctime)
            
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


## 2. Improved GUI with Audio Option

### Main GUI Components (gui/main_window.py)


# video_processor/gui/main_window.py
import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QTabWidget, QLabel, 
                           QFileDialog, QMessageBox, QProgressBar, QStatusBar,
                           QMenu, QAction)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QIcon

from .config_dialog import ConfigDialog
from .progress_widget import ProcessingProgressWidget

class ProcessingThread(QThread):
    """Background thread for file processing operations"""
    progress_updated = pyqtSignal(str, int, int)
    processing_finished = pyqtSignal(bool, str)
    
    def __init__(self, file_manager, encoder, scheduler):
        super().__init__()
        self.file_manager = file_manager
        self.encoder = encoder
        self.scheduler = scheduler
        self.is_running = False
    
    def run(self):
        """Run the processing sequence"""
        self.is_running = True
        success = True
        message = "Processing completed successfully"
        
        try:
            # Set progress callback
            self.scheduler.set_progress_callback(
                lambda filename, current, total: 
                    self.progress_updated.emit(filename, current, total)
            )
            
            # Step 1: Rename files (if needed)
            self.file_manager.rename_files()
            
            # Step 2: Process videos
            if not self.scheduler.process_videos():
                success = False
                message = "Some videos failed to process. Check the logs for details."
            
            # Step 3: Organize folders (if needed)
            self.file_manager.organize_folders()
            
        except Exception as e:
            success = False
            message = f"Processing error: {str(e)}"
        
        finally:
            self.is_running = False
            self.processing_finished.emit(success, message)

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self, config, logger, file_manager, encoder, scheduler):
        super().__init__()
        self.config = config
        self.logger = logger
        self.file_manager = file_manager
        self.encoder = encoder
        self.scheduler = scheduler
        self.processing_thread = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Video Processor")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create top control panel
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        
        # Add directories selection
        self.input_dir_btn = QPushButton("Select Input Directory")
        self.input_dir_btn.clicked.connect(self.select_input_directory)
        
        self.output_dir_btn = QPushButton("Select Output Directory")
        self.output_dir_btn.clicked.connect(self.select_output_directory)
        
        # Add configuration button
        self.config_btn = QPushButton("Configure Settings")
        self.config_btn.clicked.connect(self.show_config_dialog)
        
        # Add start processing button
        self.start_btn = QPushButton("Start Processing")
        self.start_btn.clicked.connect(self.start_processing)
        
        # Add buttons to control panel
        control_layout.addWidget(self.input_dir_btn)
        control_layout.addWidget(self.output_dir_btn)
        control_layout.addWidget(self.config_btn)
        control_layout.addWidget(self.start_btn)
        
        # Add current directory labels
        dir_info = QWidget()
        dir_layout = QHBoxLayout(dir_info)
        
        dir_layout.addWidget(QLabel("Input directory:"))
        self.input_dir_label = QLabel(str(self.config.input_folder))
        dir_layout.addWidget(self.input_dir_label)
        
        dir_layout.addWidget(QLabel("Output directory:"))
        self.output_dir_label = QLabel(str(self.config.output_folder))
        dir_layout.addWidget(self.output_dir_label)
        
        # Create progress panel
        self.progress_widget = ProcessingProgressWidget()
        
        # Add all panels to main layout
        main_layout.addWidget(control_panel)
        main_layout.addWidget(dir_info)
        main_layout.addWidget(self.progress_widget)
        
        # Add status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Create menu bar
        self.create_menu_bar()
    
    def create_menu_bar(self):
        """Create application menu bar"""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("File")
        
        # Save config action
        save_config_action = QAction("Save Configuration", self)
        save_config_action.triggered.connect(self.save_config)
        file_menu.addAction(save_config_action)
        
        # Load config action
        load_config_action = QAction("Load Configuration", self)
        load_config_action.triggered.connect(self.load_config)
        file_menu.addAction(load_config_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menu_bar.addMenu("Tools")
        
        # View logs action
        view_logs_action = QAction("View Logs", self)
        view_logs_action.triggered.connect(self.view_logs)
        tools_menu.addAction(view_logs_action)
        
        # Clear output directory action
        clear_output_action = QAction("Clear Output Directory", self)
        clear_output_action.triggered.connect(self.clear_output_directory)
        tools_menu.addAction(clear_output_action)
    
    def save_config(self):
        """Save current configuration"""
        profile_name, ok = QInputDialog.getText(
            self, "Save Configuration", "Enter profile name (leave empty for default):")
        
        if ok:
            success = self.config.save(profile_name=profile_name if profile_name else None)
            if success:
                QMessageBox.information(self, "Success", "Configuration saved successfully")
            else:
                QMessageBox.warning(self, "Error", "Failed to save configuration")
    
    def load_config(self):
        """Load configuration"""
        profiles = self.config.get_available_profiles()
        if not profiles:
            QMessageBox.information(self, "No Profiles", "No saved profiles found")
            return
        
        profile, ok = QInputDialog.getItem(
            self, "Load Profile", "Select profile:", profiles, 0, False)
        
        if ok and profile:
            success = self.config.load(profile_name=profile)
            if success:
                self.update_ui_from_config()
                QMessageBox.information(self, "Success", f"Profile '{profile}' loaded successfully")
            else:
                QMessageBox.warning(self, "Error", f"Failed to load profile '{profile}'")
    
    def update_ui_from_config(self):
        """Update UI elements with current configuration"""
        self.input_dir_label.setText(str(self.config.input_folder))
        self.output_dir_label.setText(str(self.config.output_folder))
    
    def view_logs(self):
        """View application logs"""
        from .log_viewer import LogViewerDialog
        log_viewer = LogViewerDialog(self.logger)
        log_viewer.exec_()
    
    def clear_output_directory(self):
        """Clear the output directory"""
        reply = QMessageBox.question(
            self, "Confirm", "Are you sure you want to clear the output directory?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                import shutil
                output_dir = self.config.output_folder
                
                # Don't delete the directory itself, just its contents
                for item in output_dir.iterdir():
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                
                QMessageBox.information(self, "Success", "Output directory cleared")
                self.logger.info(f"Output directory cleared: {output_dir}")
                
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to clear directory: {str(e)}")
                self.logger.error(f"Failed to clear output directory: {str(e)}")
    
    def select_input_directory(self):
        """Select input directory via dialog"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Input Directory", str(self.config.input_folder))
        
        if directory:
            self.config.input_folder = Path(directory)
            self.input_dir_label.setText(directory)
            self.logger.info(f"Input directory changed to: {directory}")
    
    def select_output_directory(self):
        """Select output directory via dialog"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", str(self.config.output_folder))
        
        if directory:
            self.config.output_folder = Path(directory)
            self.output_dir_label.setText(directory)
            self.logger.info(f"Output directory changed to: {directory}")
    
    def show_config_dialog(self):
        """Show configuration dialog"""
        dialog = ConfigDialog(self.config)
        if dialog.exec_():
            # Config was updated
            self.logger.info("Configuration updated")
    
    def start_processing(self):
        """Start the video processing"""
        if self.processing_thread and self.processing_thread.is_running:
            QMessageBox.warning(self, "Processing Active", 
                              "Processing is already running. Please wait for it to complete.")
            return
        
        # Check if files exist in input directory
        input_files = list(self.config.input_folder.glob('*.mp4'))
        if not input_files:
            QMessageBox.warning(self, "No Files", 
                              "No MP4 files found in the input directory.")
            return
        
        # Validate configuration
        errors, warnings = self.config.validate()
        if errors:
            QMessageBox.critical(self, "Configuration Error", 
                               "\n".join(errors))
            return
        
        if warnings:
            reply = QMessageBox.warning(self, "Configuration Warning", 
                                      "\n".join(warnings) + "\n\nContinue anyway?",
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return
        
        # Disable controls during processing
        self.input_dir_btn.setEnabled(False)
        self.output_dir_btn.setEnabled(False)
        self.config_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        
        # Reset progress display
        self.progress_widget.reset()
        
        # Create and start the processing thread
        self.processing_thread = ProcessingThread(
            self.file_manager, self.encoder, self.scheduler)
        
        # Connect signals
        self.processing_thread.progress_updated.connect(self.update_progress)
        self.processing_thread.processing_finished.connect(self.processing_finished)
        
        # Start processing
        self.logger.info("Starting video processing")
        self.status_bar.showMessage("Processing videos...")
        self.processing_thread.start()
    
    def update_progress(self, filename, current, total):
        """Update progress display"""
        self.progress_widget.update_file_progress(filename, 100)  # File is complete
        self.progress_widget.update_overall_progress(current, total)
        self.status_bar.showMessage(f"Processing: {current} of {total} complete")
    
    def processing_finished(self, success, message):
        """Handle processing completion"""
        # Re-enable controls
        self.input_dir_btn.setEnabled(True)
        self.output_dir_btn.setEnabled(True)
        self.config_btn.setEnabled(True)
        self.start_btn.setEnabled(True)
        
        if success:
            self.logger.info("Processing completed successfully")
            icon = QMessageBox.Information
        else:
            self.logger.error(f"Processing failed: {message}")
            icon = QMessageBox.Warning
        
        QMessageBox.information(self, "Processing Complete", message, icon)
        self.status_bar.showMessage(message)

def show_main_window(config, logger, file_manager, encoder, scheduler):
    """Display the main application window"""
    app = QApplication(sys.argv)
    window = MainWindow(config, logger, file_manager, encoder, scheduler)
    window.show()
    return app.exec_()


### Configuration Dialog with Audio Option (gui/config_dialog.py)


# video_processor/gui/config_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QRadioButton, QButtonGroup, QPushButton, QGroupBox,
                           QCheckBox, QSpinBox, QSlider, QTabWidget)
from PyQt5.QtCore import Qt

class ConfigDialog(QDialog):
    """Enhanced configuration dialog with audio option"""
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI components"""
        self.setWindowTitle("Video Processing Configuration")
        self.setMinimumWidth(500)
        
        # Create tab widget for better organization
        tab_widget = QTabWidget()
        
        # Create tabs
        encoding_tab = QWidget()
        processing_tab = QWidget()
        advanced_tab = QWidget()
        
        # Set up layouts
        encoding_layout = QVBoxLayout(encoding_tab)
        processing_layout = QVBoxLayout(processing_tab)
        advanced_layout = QVBoxLayout(advanced_tab)
        
        # ------ Encoding Options Tab ------
        
        # Encoder selection
        encoder_group = QGroupBox("Video Encoder")
        encoder_layout = QHBoxLayout()
        
        self.encoder_group = QButtonGroup()
        self.rb_libx265 = QRadioButton("libx265")
        self.rb_h264_nvenc = QRadioButton("h264_nvenc")
        self.rb_libx264 = QRadioButton("libx264")
        
        self.encoder_group.addButton(self.rb_libx265)
        self.encoder_group.addButton(self.rb_h264_nvenc)
        self.encoder_group.addButton(self.rb_libx264)
        
        encoder_layout.addWidget(self.rb_libx265)
        encoder_layout.addWidget(self.rb_h264_nvenc)
        encoder_layout.addWidget(self.rb_libx264)
        encoder_group.setLayout(encoder_layout)
        
        # Preset selection
        preset_group = QGroupBox("Encoding Preset")
        preset_layout = QHBoxLayout()
        
        self.preset_group = QButtonGroup()
        self.rb_ultrafast = QRadioButton("ultrafast")
        self.rb_veryfast = QRadioButton("veryfast")
        self.rb_medium = QRadioButton("medium")
        
        self.preset_group.addButton(self.rb_ultrafast)
        self.preset_group.addButton(self.rb_veryfast)
        self.preset_group.addButton(self.rb_medium)
        
        preset_layout.addWidget(self.rb_ultrafast)
        preset_layout.addWidget(self.rb_veryfast)
        preset_layout.addWidget(self.rb_medium)
        preset_group.setLayout(preset_layout)
        
        # Tune selection
        tune_group = QGroupBox("Encoding Tune")
        tune_layout = QHBoxLayout()
        
        self.tune_group = QButtonGroup()
        self.rb_zerolatency = QRadioButton("zerolatency")
        self.rb_film = QRadioButton("film")
        self.rb_animation = QRadioButton("animation")
        
        self.tune_group.addButton(self.rb_zerolatency)
        self.tune_group.addButton(self.rb_film)
        self.tune_group.addButton(self.rb_animation)
        
        tune_layout.addWidget(self.rb_zerolatency)
        tune_layout.addWidget(self.rb_film)
        tune_layout.addWidget(self.rb_animation)
        tune_group.setLayout(tune_layout)
        
        # FPS selection
        fps_group = QGroupBox("Frames Per Second")
        fps_layout = QHBoxLayout()
        
        self.fps_group = QButtonGroup()
        self.rb_120fps = QRadioButton("120")
        self.rb_60fps = QRadioButton("60")
        self.rb_30fps = QRadioButton("30")
        
        self.fps_group.addButton(self.rb_120fps)
        self.fps_group.addButton(self.rb_60fps)
        self.fps_group.addButton(self.rb_30fps)
        
        fps_layout.addWidget(self.rb_120fps)
        fps_layout.addWidget(self.rb_60fps)
        fps_layout.addWidget(self.rb_30fps)
        fps_group.setLayout(fps_layout)
        
        # Audio inclusion option (new)
        audio_group = QGroupBox("Audio Options")
        audio_layout = QVBoxLayout()
        
        self.include_audio_cb = QCheckBox("Include Audio in Output")
        audio_layout.addWidget(self.include_audio_cb)
        
        audio_group.setLayout(audio_layout)
        
        # Add everything to encoding tab
        encoding_layout.addWidget(encoder_group)
        encoding_layout.addWidget(preset_group)
        encoding_layout.addWidget(tune_group)
        encoding_layout.addWidget(fps_group)
        encoding_layout.addWidget(audio_group)
        encoding_layout.addStretch()
        
        # ------ Processing Options Tab ------
        
        # Parallel processing
        parallel_group = QGroupBox("Parallel Processing")
        parallel_layout = QVBoxLayout()
        
        parallel_layout.addWidget(QLabel("Maximum parallel jobs:"))
        self.parallel_jobs_spin = QSpinBox()
        self.parallel_jobs_spin.setMinimum(1)
        self.parallel_jobs_spin.setMaximum(32)
        self.parallel_jobs_spin.setValue(self.config.max_parallel_jobs)
        parallel_layout.addWidget(self.parallel_jobs_spin)
        
        parallel_group.setLayout(parallel_layout)
        
        # File operations
        file_ops_group = QGroupBox("File Operations")
        file_ops_layout = QVBoxLayout()
        
        self.auto_rename_cb = QCheckBox("Automatically rename files")
        self.auto_organize_cb = QCheckBox("Automatically organize folders")
        
        file_ops_layout.addWidget(self.auto_rename_cb)
        file_ops_layout.addWidget(self.auto_organize_cb)
        
        file_ops_group.setLayout(file_ops_layout)
        
        # Add to processing tab
        processing_layout.addWidget(parallel_group)
        processing_layout.addWidget(file_ops_group)
        processing_layout.addStretch()
        
        # ------ Advanced Options Tab ------
        # (Could add more advanced options here)
        
        advanced_layout.addWidget(QLabel("Advanced options will be added in future versions."))
        advanced_layout.addStretch()
        
        # Add tabs to tab widget
        tab_widget.addTab(encoding_tab, "Encoding")
        tab_widget.addTab(processing_tab, "Processing")
        tab_widget.addTab(advanced_tab, "Advanced")
        
        # Create dialog buttons
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(tab_widget)
        main_layout.addLayout(button_layout)
        
        # Set initial values from config
        self.load_config_values()
        
        # Connect signals
        self.rb_h264_nvenc.toggled.connect(self.update_options)
        self.rb_libx265.toggled.connect(self.update_options)
        self.rb_libx264.toggled.connect(self.update_options)
        
        # Update UI state
        self.update_options()
    
    def load_config_values(self):
        """Load values from config into UI controls"""
        # Set encoder
        if self.config.ffmpeg_params["video_encoder"] == "libx265":
            self.rb_libx265.setChecked(True)
        elif self.config.ffmpeg_params["video_encoder"] == "h264_nvenc":
            self.rb_h264_nvenc.setChecked(True)
        elif self.config.ffmpeg_params["video_encoder"] == "libx264":
            self.rb_libx264.setChecked(True)
        
        # Set preset
        if self.config.ffmpeg_params["preset"] == "ultrafast":
            self.rb_ultrafast.setChecked(True)
        elif self.config.ffmpeg_params["preset"] == "veryfast":
            self.rb_veryfast.setChecked(True)
        elif self.config.ffmpeg_params["preset"] == "medium":
            self.rb_medium.setChecked(True)
        
        # Set tune
        if self.config.ffmpeg_params["tune"] == "zerolatency":
            self.rb_zerolatency.setChecked(True)
        elif self.config.ffmpeg_params["tune"] == "film":
            self.rb_film.setChecked(True)
        elif self.config.ffmpeg_params["tune"] == "animation":
            self.rb_animation.setChecked(True)
        
        # Set FPS
        if self.config.ffmpeg_params["fps"] == 120:
            self.rb_120fps.setChecked(True)
        elif self.config.ffmpeg_params["fps"] == 60:
            self.rb_60fps.setChecked(True)
        elif self.config.ffmpeg_params["fps"] == 30:
            self.rb_30fps.setChecked(True)
        
        # Set audio inclusion
        self.include_audio_cb.setChecked(
            self.config.ffmpeg_params.get("include_audio", True)
        )
        
        # Set processing options
        self.parallel_jobs_spin.setValue(self.config.max_parallel_jobs)
        self.auto_rename_cb.setChecked(self.config.auto_rename_files)
        self.auto_organize_cb.setChecked(self.config.auto_organize_folders)
    
    def update_options(self):
        """Enable/disable options based on encoder selection"""
        is_nvenc = self.rb_h264_nvenc.isChecked()
        
        # h264_nvenc doesn't support preset or tune
        self.rb_ultrafast.setEnabled(not is_nvenc)
        self.rb_veryfast.setEnabled(not is_nvenc)
        self.rb_medium.setEnabled(not is_nvenc)
        
        self.rb_zerolatency.setEnabled(not is_nvenc)
        self.rb_film.setEnabled(not is_nvenc)
        self.rb_animation.setEnabled(not is_nvenc)
    
    def accept(self):
        """Save settings and close dialog"""
        # Encoder
        if self.rb_libx265.isChecked():
            self.config.ffmpeg_params["video_encoder"] = "libx265"
        elif self.rb_h264_nvenc.isChecked():
            self.config.ffmpeg_params["video_encoder"] = "h264_nvenc"
        elif self.rb_libx264.isChecked():
            self.config.ffmpeg_params["video_encoder"] = "libx264"
        
        # Preset
        if self.rb_ultrafast.isChecked() and self.rb_ultrafast.isEnabled():
            self.config.ffmpeg_params["preset"] = "ultrafast"
        elif self.rb_veryfast.isChecked() and self.rb_veryfast.isEnabled():
            self.config.ffmpeg_params["preset"] = "veryfast"
        elif self.rb_medium.isChecked() and self.rb_medium.isEnabled():
            self.config.ffmpeg_params["preset"] = "medium"
        else:
            self.config.ffmpeg_params["preset"] = None
        
        # Tune
        if self.rb_zerolatency.isChecked() and self.rb_zerolatency.isEnabled():
            self.config.ffmpeg_params["tune"] = "zerolatency"
        elif self.rb_film.isChecked() and self.rb_film.isEnabled():
            self.config.ffmpeg_params["tune"] = "film"
        elif self.rb_animation.isChecked() and self.rb_animation.isEnabled():
            self.config.ffmpeg_params["tune"] = "animation"
        else:
            self.config.ffmpeg_params["tune"] = None
        
        # FPS
        if self.rb_120fps.isChecked():
            self.config.ffmpeg_params["fps"] = 120
        elif self.rb_60fps.isChecked():
            self.config.ffmpeg_params["fps"] = 60
        elif self.rb_30fps.isChecked():
            self.config.ffmpeg_params["fps"] = 30
        
        # Audio inclusion
        self.config.ffmpeg_params["include_audio"] = self.include_audio_cb.isChecked()
        
        # Processing options
        self.config.max_parallel_jobs = self.parallel_jobs_spin.value()
        self.config.auto_rename_files = self.auto_rename_cb.isChecked()
        self.config.auto_organize_folders = self.auto_organize_cb.isChecked()
        
        # Save config
        self.config.save()
        
        super().accept()


### Progress Widget (gui/progress_widget.py)


# video_processor/gui/progress_widget.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QProgressBar, QGroupBox)
from PyQt5.QtCore import Qt, pyqtSignal

class ProcessingProgressWidget(QWidget):
    """Widget for displaying processing progress"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI components"""
        main_layout = QVBoxLayout(self)
        
        # Current file group
        file_group = QGroupBox("Current File")
        file_layout = QVBoxLayout(file_group)
        
        # File info layout
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel("Processing:"))
        self.file_label = QLabel("")
        info_layout.addWidget(self.file_label, 1)
        
        # File progress bar
        self.file_progress = QProgressBar()
        self.file_progress.setRange(0, 100)
        
        file_layout.addLayout(info_layout)
        file_layout.addWidget(self.file_progress)
        
        # Overall progress group
        overall_group = QGroupBox("Overall Progress")
        overall_layout = QVBoxLayout(overall_group)
        
        # Progress count
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("Files:"))
        self.progress_count = QLabel("0/0")
        count_layout.addWidget(self.progress_count)
        count_layout.addStretch()
        
        # Overall progress bar
        self.overall_progress = QProgressBar()
        self.overall_progress.setRange(0, 100)
        
        # Estimated time
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("Estimated time remaining:"))
        self.time_label = QLabel("Calculating...")
        time_layout.addWidget(self.time_label)
        time_layout.addStretch()
        
        overall_layout.addLayout(count_layout)
        overall_layout.addWidget(self.overall_progress)
        overall_layout.addLayout(time_layout)
        
        # Add groups to main layout
        main_layout.addWidget(file_group)
        main_layout.addWidget(overall_group)
        
        # Initialize process timing
        self.process_start_time = 0
        self.files_processed = 0
    
    def reset(self):
        """Reset all progress indicators"""
        self.file_label.setText("")
        self.file_progress.setValue(0)
        self.progress_count.setText("0/0")
        self.overall_progress.setValue(0)
        self.time_label.setText("Calculating...")
        
        import time
        self.process_start_time = time.time()
        self.files_processed = 0
    
    def update_file_progress(self, filename, percent):
        """Update the current file progress"""
        self.file_label.setText(filename)
        self.file_progress.setValue(percent)
    
    def update_overall_progress(self, current, total):
        """Update the overall progress"""
        if total <= 0:
            return
            
        self.progress_count.setText(f"{current}/{total}")
        percent = int((current / total) * 100)
        self.overall_progress.setValue(percent)
        
        # Update estimated time
        if current > self.files_processed:
            self.files_processed = current
            self._update_estimated_time(current, total)
    
    def _update_estimated_time(self, current, total):
        """Calculate and update the estimated time remaining"""
        import time
        
        if current <= 0 or self.process_start_time == 0:
            return
        
        elapsed_time = time.time() - self.process_start_time
        avg_time_per_file = elapsed_time / current
        
        remaining_files = total - current
        estimated_time = remaining_files * avg_time_per_file
        
        # Format time string
        if estimated_time < 60:
            time_str = f"{int(estimated_time)} seconds"
        elif estimated_time < 3600:
            minutes = int(estimated_time / 60)
            seconds = int(estimated_time % 60)
            time_str = f"{minutes} minutes, {seconds} seconds"
        else:
            hours = int(estimated_time / 3600)
            minutes = int((estimated_time % 3600) / 60)
            time_str = f"{hours} hours, {minutes} minutes"
        
        self.time_label.setText(time_str)


### Log Viewer (gui/log_viewer.py)


# video_processor/gui/log_viewer.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QTextEdit, QPushButton, 
                           QHBoxLayout, QLabel, QComboBox)
from PyQt5.QtCore import Qt, QTimer

class LogViewerDialog(QDialog):
    """Dialog for viewing application logs"""
    
    def __init__(self, logger, parent=None):
        super().__init__(parent)
        self.logger = logger
        self.timer = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI components"""
        self.setWindowTitle("Log Viewer")
        self.setGeometry(200, 200, 800, 500)
        
        layout = QVBoxLayout(self)
        
        # Controls at the top
        controls_layout = QHBoxLayout()
        
        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_log)
        
        # Auto-refresh checkbox
        self.auto_refresh_cb = QComboBox()
        self.auto_refresh_cb.addItem("Manual refresh", 0)
        self.auto_refresh_cb.addItem("Auto (5s)", 5000)
        self.auto_refresh_cb.addItem("Auto (10s)", 10000)
        self.auto_refresh_cb.addItem("Auto (30s)", 30000)
        self.auto_refresh_cb.currentIndexChanged.connect(self.set_auto_refresh)
        
        # Line count
        controls_layout.addWidget(QLabel("Lines:"))
        self.lines_cb = QComboBox()
        self.lines_cb.addItem("50", 50)
        self.lines_cb.addItem("100", 100)
        self.lines_cb.addItem("200", 200)
        self.lines_cb.addItem("500", 500)
        self.lines_cb.addItem("All", -1)
        self.lines_cb.currentIndexChanged.connect(self.refresh_log)
        
        controls_layout.addWidget(self.lines_cb)
        controls_layout.addStretch()
        controls_layout.addWidget(QLabel("Refresh:"))
        controls_layout.addWidget(self.auto_refresh_cb)
        controls_layout.addWidget(self.refresh_btn)
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier New", 10))
        
        # Close button
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)
        
        # Add to main layout
        layout.addLayout(controls_layout)
        layout.addWidget(self.log_text)
        layout.addLayout(button_layout)
        
        # Initial log load
        self.refresh_log()
    
    def refresh_log(self):
        """Refresh log content"""
        lines = self.lines_cb.currentData()
        log_content = self.logger.get_log_content(lines)
        self.log_text.setText(log_content)
        
        # Scroll to bottom
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)
    
    def set_auto_refresh(self, index):
        """Set auto-refresh interval"""
        # Stop existing timer if running
        if self.timer:
            self.timer.stop()
            self.timer = None
        
        # Get refresh interval
        interval = self.auto_refresh_cb.currentData()
        if interval > 0:
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.refresh_log)
            self.timer.start(interval)


## 3. Enhanced FFmpeg Encoder with Audio Option


# video_processor/processing/encoder.py
import os
import re
import subprocess
import time
from pathlib import Path

class FFmpegEncoder:
    """FFmpeg encoder with advanced options including audio control"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.process = None
        self.encoding_progress = 0
    
    def check_ffmpeg(self):
        """Check if FFmpeg is installed and available"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            if "ffmpeg version" in result.stdout:
                self.logger.info(f"Found FFmpeg: {result.stdout.split('\\n')[0]}")
                return True
            return False
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            self.logger.error(f"FFmpeg check failed: {str(e)}")
            return False
    
    def has_audio(self, file_path):
        """Check if the video file has audio streams"""
        try:
            result = subprocess.run(
                ["ffprobe", "-i", str(file_path), "-show_streams", 
                 "-select_streams", "a", "-loglevel", "error"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            return bool(result.stdout.strip())
        except subprocess.SubprocessError as e:
            self.logger.error(f"Error checking audio streams: {str(e)}")
            return False
    
    def build_command(self, input_file, output_folder):
        """Build FFmpeg command for HLS encoding with audio option"""
        # Check for audio streams and respect the include_audio setting
        has_audio = self.has_audio(input_file) and self.config.ffmpeg_params.get("include_audio", True)
        
        # Calculate buffer sizes
        bitrates = self.config.ffmpeg_params["bitrates"]
        bufsizes = {}
        for res, bitrate in bitrates.items():
            bufsize_value = int(bitrate.rstrip('k')) * 2
            bufsizes[res] = f"{bufsize_value}k"
        
        # Build filter complex string
        filter_complex = "[0:v]split=4[v1][v2][v3][v4];[v1]scale=1920:1080[v1out];[v2]scale=1280:720[v2out];[v3]scale=854:480[v3out];[v4]scale=640:360[v4out]"
        
        # Build FFmpeg command
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "info", "-stats", 
               "-i", str(input_file), "-filter_complex", filter_complex]
        
        # Video streams for all resolutions
        for i, (res, bitrate) in enumerate([("1080p", bitrates["1080p"]), 
                                           ("720p", bitrates["720p"]), 
                                           ("480p", bitrates["480p"]), 
                                           ("360p", bitrates["360p"])]):
            # Map video stream
            cmd.extend(["-map", f"[v{i+1}out]", 
                       "-c:v:" + str(i), self.config.ffmpeg_params["video_encoder"]])
            
            # Add preset and tune if applicable
            if self.config.ffmpeg_params["preset"]:
                cmd.extend([f"-preset:v:{i}", self.config.ffmpeg_params["preset"]])
            if self.config.ffmpeg_params["tune"]:
                cmd.extend([f"-tune:v:{i}", self.config.ffmpeg_params["tune"]])
            
            # Bitrate settings
            cmd.extend([f"-b:v:{i}", bitrate, 
                       f"-maxrate:v:{i}", bitrate, 
                       f"-bufsize:v:{i}", bufsizes[res]])
        
        # Audio streams if available and enabled
        audio_bitrates = self.config.ffmpeg_params["audio_bitrates"]
        if has_audio:
            for i, bitrate in enumerate(audio_bitrates):
                cmd.extend(["-map", "a:0", 
                           f"-c:a:{i}", "aac", 
                           f"-b:a:{i}", bitrate, 
                           "-ac", "2"])
            var_stream_map = "v:0,a:0 v:1,a:1 v:2,a:2 v:3,a:3"
        else:
            var_stream_map = "v:0 v:1 v:2 v:3"
            
            # If we're intentionally excluding audio, log it
            if not self.config.ffmpeg_params.get("include_audio", True):
                self.logger.info(f"Audio excluded per user settings for {input_file.name}")
        
        # HLS parameters
        segment_path = str(output_folder) + "/%v/segment_%03d.ts"
        playlist_path = str(output_folder) + "/%v/playlist.m3u8"
        
        cmd.extend(["-f", "hls", 
                   "-g", str(self.config.ffmpeg_params["fps"]), 
                   "-hls_time", "1", 
                   "-hls_playlist_type", "vod", 
                   "-hls_flags", "independent_segments", 
                   "-hls_segment_type", "mpegts", 
                   "-hls_segment_filename", segment_path, 
                   "-master_pl_name", "master.m3u8", 
                   "-var_stream_map", var_stream_map, 
                   playlist_path])
        
        return cmd
    
    def encode_video(self, input_file, output_folder):
        """Encode a video file to HLS format"""
        try:
            # Create output directory structure
            output_folder = Path(output_folder)
            output_folder.mkdir(parents=True, exist_ok=True)
            
            # Create directories for different resolutions
            for res in ["1080p", "720p", "480p", "360p"]:
                (output_folder / res).mkdir(parents=True, exist_ok=True)
            
            # Build command
            cmd = self.build_command(input_file, output_folder)
            self.logger.debug(f"Executing: {' '.join(cmd)}")
            
            # Execute FFmpeg
            self.process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True,
                universal_newlines=True
            )
            
            # Process stdout and stderr
            stdout, stderr = self.process.communicate()
            
            # Check for errors
            if self.process.returncode != 0:
                error_message = stderr.strip()
                self.logger.error(f"FFmpeg error encoding {input_file.name}: {error_message}")
                return False
            
            # Check if output files were created
            m3u8_file = output_folder / "master.m3u8"
            if not m3u8_file.exists():
                self.logger.error(f"Failed to create master playlist for {input_file.name}")
                return False
            
            self.logger.info(f"Successfully encoded {input_file.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Encoding error for {input_file.name}: {str(e)}")
            return False
    
    def terminate(self):
        """Terminate any active FFmpeg process"""
        if self.process and self.process.poll() is None:
            try:
                self.logger.info("Terminating active FFmpeg process")
                self.process.terminate()
                
                # Wait up to 5 seconds for graceful termination
                for _ in range(50):
                    if self.process.poll() is not None:
                        break
                    time.sleep(0.1)
                
                # Force kill if still running
                if self.process.poll() is None:
                    self.logger.warning("FFmpeg process did not terminate gracefully, force killing")
                    self.process.kill()
                    self.process.wait()
                
                return True
            except Exception as e:
                self.logger.error(f"Error terminating FFmpeg process: {str(e)}")
                return False
        return False


## 4. Enhanced Parallel Processing Scheduler


# video_processor/processing/scheduler.py
import time
import os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from threading import Lock

class ProcessingScheduler:
    """Enhanced parallel processing scheduler for video encoding"""
    
    def __init__(self, config, logger, file_manager, encoder):
        self.config = config
        self.logger = logger
        self.file_manager = file_manager
        self.encoder = encoder
        self.lock = Lock()
        self.processed_count = 0
        self.total_files = 0
        self.progress_callback = None
        self.is_running = False
        self.abort_requested = False
    
    def set_progress_callback(self, callback):
        """Set a callback function for progress updates"""
        self.progress_callback = callback
    
    def request_abort(self):
        """Request abortion of the processing"""
        if not self.is_running:
            return False
            
        self.logger.warning("Processing abort requested")
        self.abort_requested = True
        return True
    
    def process_video(self, file):
        """Process a single video file"""
        # Check for abort
        if self.abort_requested:
            return False
            
        base_name = file.stem
        output_subfolder = self.config.output_folder / base_name
        
        start_time = time.time()
        self.logger.info(f"Starting processing: {base_name}")
        
        try:
            # Encode the video
            result = self.encoder.encode_video(file, output_subfolder)
            
            duration = time.time() - start_time
            if result:
                self.logger.info(f"Completed processing: {base_name} ({duration:.2f}s)")
            else:
                self.logger.error(f"Failed to process: {base_name}")
            
            # Update progress counter
            with self.lock:
                self.processed_count += 1
                current = self.processed_count
            
            # Call progress callback if set
            if self.progress_callback:
                self.progress_callback(file.name, current, self.total_files)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing {base_name}: {str(e)}")
            
            # Still update progress counter
            with self.lock:
                self.processed_count += 1
                current = self.processed_count
            
            # Call progress callback if set
            if self.progress_callback:
                self.progress_callback(file.name, current, self.total_files)
            
            return False
    
    def process_videos(self):
        """Process all video files in parallel"""
        self.is_running = True
        self.abort_requested = False
        
        try:
            # Validate files
            valid_files, invalid_files = self.file_manager.validate_files()
            
            if invalid_files:
                self.logger.warning("The following files have invalid naming format:")
                for file in invalid_files:
                    self.logger.warning(f"  - {file}")
            
            if not valid_files:
                self.logger.error("No valid files found to process")
                self.is_running = False
                return False
            
            self.logger.info(f"Found {len(valid_files)} valid files to process")
            self.total_files = len(valid_files)
            self.processed_count = 0
            
            processing_start = time.time()
            
            # Process files in parallel using ProcessPoolExecutor
            with ProcessPoolExecutor(max_workers=self.config.max_parallel_jobs) as executor:
                # Submit all tasks
                futures = []
                for file in valid_files:
                    future = executor.submit(self.process_video, file)
                    futures.append(future)
                
                # Process results as they complete
                successful_count = 0
                failed_count = 0
                
                for future in futures:
                    # Check for abort
                    if self.abort_requested:
                        executor.shutdown(wait=False)
                        self.logger.warning("Processing aborted by user")
                        break
                    
                    try:
                        result = future.result()
                        if result:
                            successful_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        self.logger.error(f"Error in processing task: {str(e)}")
                        failed_count += 1
            
            # Calculate statistics
            processing_duration = time.time() - processing_start
            processing_minutes = processing_duration / 60
            
            self.logger.info(f"Processing completed: {successful_count} successful, {failed_count} failed")
            self.logger.info(f"Total processing time: {processing_minutes:.2f} minutes")
            
            self.is_running = False
            return failed_count == 0
            
        except Exception as e:
            self.logger.error(f"Error in process_videos: {str(e)}")
            self.is_running = False
            return False
        
        finally:
            self.is_running = False


## 5. Enhanced File Manager


# video_processor/processing/file_manager.py
import os
import re
import shutil
from pathlib import Path

class FileManager:
    """Enhanced file manager with option controls"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.input_folder = Path(config.input_folder)
        self.output_folder = Path(config.output_folder)
    
    def rename_files(self):
        """Rename files based on pattern matching and configuration"""
        # Skip if auto-rename is disabled
        if not self.config.auto_rename_files:
            self.logger.info("File renaming skipped (disabled in config)")
            return 0
            
        self.logger.info("Starting file renaming process")
        files = list(self.input_folder.glob('*.mp4'))
        total_files = len(files)
        renamed_count = 0
        
        for i, file in enumerate(files):
            try:
                # Remove all whitespace first
                name_without_spaces = file.name.replace(' ', '')
                
                # Check if matches pattern
                match = re.match(r".*?(\d+-\d+).*?\.mp4$", name_without_spaces)
                if match:
                    new_name = f"{match.group(1)}.mp4"
                    new_path = file.parent / new_name
                    
                    # Skip if file already has correct name
                    if file.name == new_name:
                        self.logger.debug(f"Skipping already correctly named file: {file.name}")
                        continue
                    
                    # Check if destination exists
                    if new_path.exists():
                        self.logger.warning(f"Cannot rename {file.name} to {new_name} - destination exists")
                        continue
                    
                    # Rename the file
                    file.rename(new_path)
                    self.logger.info(f"Renamed: {file.name} to {new_name}")
                    renamed_count += 1
                else:
                    self.logger.warning(f"Skipping non-matching file: {file.name}")
            except Exception as e:
                self.logger.error(f"Failed to rename {file.name}: {str(e)}")
        
        self.logger.info(f"File renaming completed: {renamed_count} of {total_files} files renamed")
        return renamed_count
    
    def validate_files(self):
        """Validate files for correct naming pattern"""
        valid_files = []
        invalid_files = []
        
        for file in self.input_folder.glob('*.mp4'):
            if re.match(r'^\d+-\d+\.mp4$', file.name):
                valid_files.append(file)
            else:
                invalid_files.append(file.name)
        
        return valid_files, invalid_files
    
    def organize_folders(self):
        """Organize processed folders based on naming patterns and configuration"""
        # Skip if auto-organize is disabled
        if not self.config.auto_organize_folders:
            self.logger.info("Folder organization skipped (disabled in config)")
            return 0
            
        self.logger.info("Starting folder organization")
        folders = list(self.output_folder.glob('*-*'))
        moved_count = 0
        
        for folder in folders:
            try:
                if not folder.is_dir():
                    continue
                    
                match = re.match(r"^(\d+)-\d+", folder.name)
                if match:
                    parent_folder = self.output_folder / match.group(1)
                    parent_folder.mkdir(exist_ok=True)
                    
                    # Destination path
                    dest = parent_folder / folder.name
                    
                    # Skip if already in correct location
                    if str(folder.parent) == str(parent_folder):
                        self.logger.debug(f"Folder already correctly organized: {folder.name}")
                        continue
                    
                    # Check if destination exists
                    if dest.exists():
                        self.logger.warning(f"Cannot move {folder.name} - destination exists")
                        continue
                    
                    # Move the folder
                    shutil.move(str(folder), str(dest))
                    self.logger.info(f"Moved {folder.name} to {parent_folder}")
                    moved_count += 1
            except Exception as e:
                self.logger.error(f"Failed to organize folder {folder.name}: {str(e)}")
        
        self.logger.info(f"Folder organization completed: {moved_count} folders moved")
        return moved_count
    
    def get_input_files_info(self):
        """Get information about input files"""
        files = list(self.input_folder.glob('*.mp4'))
        valid_files, invalid_files = self.validate_files()
        
        total_size = sum(f.stat().st_size for f in files)
        # Convert to MB
        total_size_mb = total_size / (1024 * 1024)
        
        return {
            'total_files': len(files),
            'valid_files': len(valid_files),
            'invalid_files': len(invalid_files),
            'total_size_mb': total_size_mb
        }
    
    def clean_input_directory(self):
        """Clean up processed files from input directory (optional)"""
        try:
            # This is a potentially destructive operation, so we'll implement
            # it with safeguards
            
            # Get all processed video names from output directory
            processed_videos = set()
            for folder in self.output_folder.glob('*-*'):
                if folder.is_dir():
                    processed_videos.add(folder.name + '.mp4')
            
            # Count how many files would be deleted
            to_delete = []
            for file in self.input_folder.glob('*.mp4'):
                if file.name in processed_videos:
                    to_delete.append(file)
            
            if not to_delete:
                self.logger.info("No processed files found to clean up")
                return 0
            
            self.logger.warning(f"Would delete {len(to_delete)} processed files from input directory")
            # Since this is destructive, we won't actually implement the deletion here
            # but would require explicit confirmation from the user
            
            return len(to_delete)
        except Exception as e:
            self.logger.error(f"Error in clean_input_directory: {str(e)}")
            return 0


# video_processor/main.py
import sys
import os
import argparse
import signal
from pathlib import Path
import time

from PyQt5.QtWidgets import QApplication

from utils.config import Config
from utils.logging import Logger
from processing.file_manager import FileManager
from processing.encoder import FFmpegEncoder
from processing.scheduler import ProcessingScheduler
from gui.main_window import show_main_window

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
        
        # Log configuration
        logger.info(f"Input directory: {config.input_folder}")
        logger.info(f"Output directory: {config.output_folder}")
        logger.info(f"Encoder: {config.ffmpeg_params['video_encoder']}")
        logger.info(f"Preset: {config.ffmpeg_params.get('preset', 'None')}")
        logger.info(f"Tune: {config.ffmpeg_params.get('tune', 'None')}")
        logger.info(f"FPS: {config.ffmpeg_params['fps']}")
        logger.info(f"Include audio: {config.ffmpeg_params.get('include_audio', True)}")
        logger.info(f"Parallel jobs: {config.max_parallel_jobs}")
        
        # Check FFmpeg
        if not encoder.check_ffmpeg():
            logger.error("FFmpeg not found or not accessible")
            return 1
        
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
    logger = Logger(config.output_folder, level=log_level)
    
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
        return show_main_window(config, logger, file_manager, encoder, scheduler)

if __name__ == "__main__":
    sys.exit(main())
