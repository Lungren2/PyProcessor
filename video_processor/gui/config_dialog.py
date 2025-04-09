from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTabWidget)
from PyQt5.QtCore import Qt

from video_processor.gui.settings_widgets import (
    EncodingSettingsWidget, ProcessingSettingsWidget, AdvancedSettingsWidget
)

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

        # Create settings widgets
        self.encoding_widget = EncodingSettingsWidget(self.config)
        self.processing_widget = ProcessingSettingsWidget(self.config)
        self.advanced_widget = AdvancedSettingsWidget(self.config)

        # Add tabs to tab widget
        tab_widget.addTab(self.encoding_widget, "Encoding")
        tab_widget.addTab(self.processing_widget, "Processing")
        tab_widget.addTab(self.advanced_widget, "Advanced")

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

    def accept(self):
        """Save settings and close dialog"""
        # Save settings from all widgets
        self.encoding_widget.save_to_config()
        self.processing_widget.save_to_config()
        self.advanced_widget.save_to_config()

        # Save config
        self.config.save()

        super().accept()
