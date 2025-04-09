import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QPushButton, QTabWidget, QLabel,
                           QFileDialog, QMessageBox, QProgressBar, QStatusBar,
                           QMenu, QAction, QInputDialog, QLineEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QIcon
from pathlib import Path

from video_processor.gui.settings_widgets import (
    EncodingSettingsWidget, ProcessingSettingsWidget, AdvancedSettingsWidget
)
from video_processor.gui.progress_widget import ProcessingProgressWidget

class ProcessingThread(QThread):
    """Background thread for file processing operations"""
    progress_updated = pyqtSignal(str, int, int, int)  # filename, file_progress, current, total
    output_file_created = pyqtSignal(str, str)  # filename, resolution
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
                lambda filename, file_progress, current, total:
                    self.progress_updated.emit(filename, file_progress, current, total)
            )

            # Set output file callback
            self.scheduler.set_output_file_callback(
                lambda filename, resolution:
                    self.output_file_created.emit(filename, resolution if resolution else "")
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

    def __init__(self, config, logger, file_manager, encoder, scheduler, theme_manager=None):
        super().__init__()
        self.config = config
        self.logger = logger
        self.file_manager = file_manager
        self.encoder = encoder
        self.scheduler = scheduler
        self.theme_manager = theme_manager
        self.processing_thread = None

        self.init_ui()

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Video Processor")
        self.setGeometry(100, 100, 900, 700)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create tab widget
        self.tab_widget = QTabWidget()

        # Create Home tab
        home_tab = QWidget()
        home_layout = QVBoxLayout(home_tab)

        # Create top control panel
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)

        # Add start processing button
        self.start_btn = QPushButton("Start Processing ▶️")
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setMinimumHeight(40)  # Make button larger

        # Add buttons to control panel
        control_layout.addStretch()
        control_layout.addWidget(self.start_btn)
        control_layout.addStretch()

        # Add directory input fields
        dir_info = QWidget()
        dir_layout = QHBoxLayout(dir_info)

        # Input directory
        dir_layout.addWidget(QLabel("Input directory:"))
        self.input_dir_edit = QLineEdit(str(self.config.input_folder))
        self.input_dir_edit.setMinimumWidth(200)  # Ensure enough space for paths
        self.input_dir_edit.editingFinished.connect(self.input_path_edited)
        dir_layout.addWidget(self.input_dir_edit)

        self.input_dir_btn = QPushButton("📁")
        self.input_dir_btn.clicked.connect(self.select_input_directory)
        dir_layout.addWidget(self.input_dir_btn)

        # Output directory
        dir_layout.addWidget(QLabel("Output directory:"))
        self.output_dir_edit = QLineEdit(str(self.config.output_folder))
        self.output_dir_edit.setMinimumWidth(200)  # Ensure enough space for paths
        self.output_dir_edit.editingFinished.connect(self.output_path_edited)
        dir_layout.addWidget(self.output_dir_edit)

        self.output_dir_btn = QPushButton("📁")
        self.output_dir_btn.clicked.connect(self.select_output_directory)
        dir_layout.addWidget(self.output_dir_btn)

        # Create progress panel
        self.progress_widget = ProcessingProgressWidget()

        # Add all panels to home layout
        home_layout.addWidget(control_panel)
        home_layout.addWidget(dir_info)
        home_layout.addWidget(self.progress_widget)

        # Create settings tabs
        self.encoding_widget = EncodingSettingsWidget(self.config)
        self.processing_widget = ProcessingSettingsWidget(self.config)
        self.advanced_widget = AdvancedSettingsWidget(self.config)

        # Connect settings change signals
        self.encoding_widget.settings_changed.connect(self.on_settings_changed)
        self.processing_widget.settings_changed.connect(self.on_settings_changed)
        self.advanced_widget.settings_changed.connect(self.on_settings_changed)

        # Add tabs to tab widget
        self.tab_widget.addTab(home_tab, "Home")
        self.tab_widget.addTab(self.encoding_widget, "Encoding Settings")
        self.tab_widget.addTab(self.processing_widget, "Processing Settings")
        self.tab_widget.addTab(self.advanced_widget, "Advanced Settings")

        # Add tab widget to main layout
        main_layout.addWidget(self.tab_widget)

        # Add status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Create menu bar
        self.create_menu_bar()

        # Track if settings have been modified
        self.settings_modified = False

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

        # Add Theme menu if theme manager is available
        if self.theme_manager:
            theme_menu = menu_bar.addMenu("Theme")

            # Dark theme action
            dark_theme_action = QAction("Dark Mode", self)
            dark_theme_action.triggered.connect(self.theme_manager.set_dark_theme)
            theme_menu.addAction(dark_theme_action)

            # Light theme action
            light_theme_action = QAction("Light Mode", self)
            light_theme_action.triggered.connect(self.theme_manager.set_light_theme)
            theme_menu.addAction(light_theme_action)

            # System theme action
            system_theme_action = QAction("Follow System Settings", self)
            system_theme_action.triggered.connect(self.theme_manager.follow_system)
            theme_menu.addAction(system_theme_action)

    def save_settings(self):
        """Save current settings to config"""
        # Save settings from all widgets
        self.encoding_widget.save_to_config()
        self.processing_widget.save_to_config()
        self.advanced_widget.save_to_config()
        self.settings_modified = False
        self.status_bar.showMessage("Settings applied")

    def save_config(self):
        """Save current configuration"""
        # First save current settings
        self.save_settings()

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
        self.input_dir_edit.setText(str(self.config.input_folder))
        self.output_dir_edit.setText(str(self.config.output_folder))

        # Update settings widgets
        self.encoding_widget.load_config_values()
        self.processing_widget.load_config_values()
        self.advanced_widget.load_config_values()

        self.settings_modified = False

    def view_logs(self):
        """View application logs"""
        from video_processor.gui.log_viewer import LogViewerDialog
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

    def input_path_edited(self):
        """Handle manual edits to the input directory path"""
        new_path = self.input_dir_edit.text().strip()
        if new_path and new_path != str(self.config.input_folder):
            try:
                path = Path(new_path)
                # Create directory if it doesn't exist
                if not path.exists():
                    reply = QMessageBox.question(
                        self, "Directory Not Found",
                        f"The directory '{new_path}' does not exist. Create it?",
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                    )
                    if reply == QMessageBox.Yes:
                        path.mkdir(parents=True, exist_ok=True)
                    else:
                        # Revert to previous path
                        self.input_dir_edit.setText(str(self.config.input_folder))
                        return

                self.config.input_folder = path
                self.logger.info(f"Input directory changed to: {new_path}")
            except Exception as e:
                QMessageBox.warning(self, "Invalid Path", f"Error setting input path: {str(e)}")
                # Revert to previous path
                self.input_dir_edit.setText(str(self.config.input_folder))

    def output_path_edited(self):
        """Handle manual edits to the output directory path"""
        new_path = self.output_dir_edit.text().strip()
        if new_path and new_path != str(self.config.output_folder):
            try:
                path = Path(new_path)
                # Create directory if it doesn't exist
                if not path.exists():
                    reply = QMessageBox.question(
                        self, "Directory Not Found",
                        f"The directory '{new_path}' does not exist. Create it?",
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                    )
                    if reply == QMessageBox.Yes:
                        path.mkdir(parents=True, exist_ok=True)
                    else:
                        # Revert to previous path
                        self.output_dir_edit.setText(str(self.config.output_folder))
                        return

                self.config.output_folder = path
                self.logger.info(f"Output directory changed to: {new_path}")
            except Exception as e:
                QMessageBox.warning(self, "Invalid Path", f"Error setting output path: {str(e)}")
                # Revert to previous path
                self.output_dir_edit.setText(str(self.config.output_folder))

    def select_input_directory(self):
        """Select input directory via dialog"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Input Directory", str(self.config.input_folder))

        if directory:
            self.config.input_folder = Path(directory)
            self.input_dir_edit.setText(directory)
            self.logger.info(f"Input directory changed to: {directory}")

    def select_output_directory(self):
        """Select output directory via dialog"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", str(self.config.output_folder))

        if directory:
            self.config.output_folder = Path(directory)
            self.output_dir_edit.setText(directory)
            self.logger.info(f"Output directory changed to: {directory}")

    def on_settings_changed(self):
        """Handle settings changes"""
        self.settings_modified = True
        self.status_bar.showMessage("Settings modified. Remember to save your configuration.")

    def start_processing(self):
        """Start the video processing"""
        if self.processing_thread and self.processing_thread.is_running:
            QMessageBox.warning(self, "Processing Active",
                              "Processing is already running. Please wait for it to complete.")
            return

        # Save current settings to config
        self.save_settings()

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

        # Switch to Home tab
        self.tab_widget.setCurrentIndex(0)

        # Disable controls during processing
        self.input_dir_edit.setEnabled(False)
        self.input_dir_btn.setEnabled(False)
        self.output_dir_edit.setEnabled(False)
        self.output_dir_btn.setEnabled(False)
        self.start_btn.setEnabled(False)

        # Disable settings tabs
        for i in range(1, self.tab_widget.count()):
            self.tab_widget.setTabEnabled(i, False)

        # Reset progress display
        self.progress_widget.reset()

        # Create and start the processing thread
        self.processing_thread = ProcessingThread(
            self.file_manager, self.encoder, self.scheduler)

        # Connect signals
        self.processing_thread.progress_updated.connect(self.update_progress)
        self.processing_thread.output_file_created.connect(self.output_file_created)
        self.processing_thread.processing_finished.connect(self.processing_finished)

        # Start processing
        self.logger.info("Starting video processing")
        self.status_bar.showMessage("Processing videos...")
        self.processing_thread.start()

    def update_progress(self, filename, file_progress, current, total):
        """Update progress display"""
        self.progress_widget.update_file_progress(filename, file_progress)
        self.progress_widget.update_overall_progress(current, total)
        self.status_bar.showMessage(f"Processing: {current} of {total} complete - Current file: {file_progress}%")

    def output_file_created(self, filename, resolution):
        """Add an output file to the log"""
        self.progress_widget.add_output_file(filename, resolution if resolution else None)

    def processing_finished(self, success, message):
        """Handle processing completion"""
        # Re-enable controls
        self.input_dir_edit.setEnabled(True)
        self.input_dir_btn.setEnabled(True)
        self.output_dir_edit.setEnabled(True)
        self.output_dir_btn.setEnabled(True)
        self.start_btn.setEnabled(True)

        # Re-enable settings tabs
        for i in range(1, self.tab_widget.count()):
            self.tab_widget.setTabEnabled(i, True)

        if success:
            self.logger.info("Processing completed successfully")
            QMessageBox.information(self, "Processing Complete", message)
        else:
            self.logger.error(f"Processing failed: {message}")
            QMessageBox.warning(self, "Processing Failed", message)

        self.status_bar.showMessage(message)

def show_main_window(app, config, logger, file_manager, encoder, scheduler, theme_manager=None):
    """Display the main application window

    Args:
        app: QApplication instance
        config: Configuration instance
        logger: Logger instance
        file_manager: FileManager instance
        encoder: Encoder instance
        scheduler: Scheduler instance
        theme_manager: ThemeManager instance for handling UI themes

    Returns:
        Application exit code
    """
    window = MainWindow(config, logger, file_manager, encoder, scheduler, theme_manager)
    window.show()
    return app.exec_()
