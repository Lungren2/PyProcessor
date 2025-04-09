import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QPushButton, QTabWidget, QLabel,
                           QFileDialog, QMessageBox, QProgressBar, QStatusBar,
                           QMenu, QAction, QInputDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QIcon
from pathlib import Path

from video_processor.gui.config_dialog import ConfigDialog
from video_processor.gui.progress_widget import ProcessingProgressWidget

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
            QMessageBox.information(self, "Processing Complete", message)
        else:
            self.logger.error(f"Processing failed: {message}")
            QMessageBox.warning(self, "Processing Failed", message)

        self.status_bar.showMessage(message)

def show_main_window(config, logger, file_manager, encoder, scheduler):
    """Display the main application window"""
    app = QApplication(sys.argv)
    window = MainWindow(config, logger, file_manager, encoder, scheduler)
    window.show()
    return app.exec_()
