from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QRadioButton, QButtonGroup, QGroupBox,
                           QCheckBox, QSpinBox, QLineEdit, QPushButton,
                           QFormLayout, QComboBox, QFileDialog, QMessageBox,
                           QTabWidget)
from PyQt5.QtCore import pyqtSignal
import os
import platform

from pyprocessor.utils.server_optimizer import ServerOptimizer

class EncodingSettingsWidget(QWidget):
    """Widget for encoding settings"""

    settings_changed = pyqtSignal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.init_ui()

    def init_ui(self):
        """Initialize UI components"""
        main_layout = QVBoxLayout(self)

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

        # Audio inclusion option
        audio_group = QGroupBox("Audio Options")
        audio_layout = QVBoxLayout()

        self.include_audio_cb = QCheckBox("Include Audio in Output")
        audio_layout.addWidget(self.include_audio_cb)

        audio_group.setLayout(audio_layout)

        # Add everything to main layout
        main_layout.addWidget(encoder_group)
        main_layout.addWidget(preset_group)
        main_layout.addWidget(tune_group)
        main_layout.addWidget(fps_group)
        main_layout.addWidget(audio_group)
        main_layout.addStretch()

        # Load initial values
        self.load_config_values()

        # Connect signals
        self.rb_h264_nvenc.toggled.connect(self.update_options)
        self.rb_libx265.toggled.connect(self.update_options)
        self.rb_libx264.toggled.connect(self.update_options)

        # Connect change signals
        self.rb_libx265.toggled.connect(self.settings_changed.emit)
        self.rb_h264_nvenc.toggled.connect(self.settings_changed.emit)
        self.rb_libx264.toggled.connect(self.settings_changed.emit)
        self.rb_ultrafast.toggled.connect(self.settings_changed.emit)
        self.rb_veryfast.toggled.connect(self.settings_changed.emit)
        self.rb_medium.toggled.connect(self.settings_changed.emit)
        self.rb_zerolatency.toggled.connect(self.settings_changed.emit)
        self.rb_film.toggled.connect(self.settings_changed.emit)
        self.rb_animation.toggled.connect(self.settings_changed.emit)
        self.rb_120fps.toggled.connect(self.settings_changed.emit)
        self.rb_60fps.toggled.connect(self.settings_changed.emit)
        self.rb_30fps.toggled.connect(self.settings_changed.emit)
        self.include_audio_cb.toggled.connect(self.settings_changed.emit)

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

    def save_to_config(self):
        """Save settings to config"""
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


class ProcessingSettingsWidget(QWidget):
    """Widget for processing settings"""

    settings_changed = pyqtSignal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.init_ui()

    def init_ui(self):
        """Initialize UI components"""
        main_layout = QVBoxLayout(self)

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

        # Add to main layout
        main_layout.addWidget(parallel_group)
        main_layout.addWidget(file_ops_group)
        main_layout.addStretch()

        # Load initial values
        self.load_config_values()

        # Connect change signals
        self.parallel_jobs_spin.valueChanged.connect(self.settings_changed.emit)
        self.auto_rename_cb.toggled.connect(self.settings_changed.emit)
        self.auto_organize_cb.toggled.connect(self.settings_changed.emit)

    def load_config_values(self):
        """Load values from config into UI controls"""
        self.parallel_jobs_spin.setValue(self.config.max_parallel_jobs)
        self.auto_rename_cb.setChecked(self.config.auto_rename_files)
        self.auto_organize_cb.setChecked(self.config.auto_organize_folders)

    def save_to_config(self):
        """Save settings to config"""
        self.config.max_parallel_jobs = self.parallel_jobs_spin.value()
        self.config.auto_rename_files = self.auto_rename_cb.isChecked()
        self.config.auto_organize_folders = self.auto_organize_cb.isChecked()


class AdvancedSettingsWidget(QWidget):
    """Widget for advanced settings"""

    settings_changed = pyqtSignal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.init_ui()

    def init_ui(self):
        """Initialize UI components"""
        main_layout = QVBoxLayout(self)

        # File pattern settings
        pattern_group = QGroupBox("File Pattern Settings")
        pattern_layout = QFormLayout()

        # File rename pattern
        self.rename_pattern_edit = QLineEdit()
        self.rename_pattern_edit.setToolTip(
            "Pattern used to extract the correct filename from existing files.\n"
            "Must include a capture group (in parentheses) that will be used as the new filename.\n"
            "Default: r\"(\\d+-\\d+)(?:[_-].*?)?\\.mp4$\" - extracts numbers-numbers pattern.\n"
            "Example: 'video-123-456.mp4' or '123-456_720p.mp4' will be renamed to '123-456.mp4'."
        )
        reset_rename_btn = QPushButton("Reset")
        reset_rename_btn.clicked.connect(self.reset_rename_pattern)

        rename_layout = QHBoxLayout()
        rename_layout.addWidget(self.rename_pattern_edit)
        rename_layout.addWidget(reset_rename_btn)

        # File validation pattern
        self.validation_pattern_edit = QLineEdit()
        self.validation_pattern_edit.setToolTip(
            "Pattern used to validate filenames before processing.\n"
            "Files that don't match this pattern will be considered invalid.\n"
            "Default: r\"^\\d+-\\d+\\.mp4$\" - requires exact numbers-numbers.mp4 format."
        )
        reset_validation_btn = QPushButton("Reset")
        reset_validation_btn.clicked.connect(self.reset_validation_pattern)

        validation_layout = QHBoxLayout()
        validation_layout.addWidget(self.validation_pattern_edit)
        validation_layout.addWidget(reset_validation_btn)

        # Folder organization pattern
        self.folder_pattern_edit = QLineEdit()
        self.folder_pattern_edit.setToolTip(
            "Pattern used to organize folders after processing.\n"
            "Must include a capture group (in parentheses) that will be used as the parent folder name.\n"
            "Default: r\"^(\\d+)-\\d+\" - uses first number group as parent folder."
        )
        reset_folder_btn = QPushButton("Reset")
        reset_folder_btn.clicked.connect(self.reset_folder_pattern)

        folder_layout = QHBoxLayout()
        folder_layout.addWidget(self.folder_pattern_edit)
        folder_layout.addWidget(reset_folder_btn)

        # Add to form layout
        pattern_layout.addRow(QLabel("File Rename Pattern:"), rename_layout)
        pattern_layout.addRow(QLabel("File Validation Pattern:"), validation_layout)
        pattern_layout.addRow(QLabel("Folder Organization Pattern:"), folder_layout)

        # Help text
        help_label = QLabel(
            "<b>Note:</b> These patterns use regular expressions (regex). "
            "Hover over each field for more information. "
            "Incorrect patterns may cause unexpected behavior."
        )
        help_label.setWordWrap(True)
        pattern_layout.addRow(help_label)

        pattern_group.setLayout(pattern_layout)

        # Add to main layout
        main_layout.addWidget(pattern_group)
        main_layout.addStretch()

        # Connect signals
        self.rename_pattern_edit.textChanged.connect(self.settings_changed.emit)
        self.validation_pattern_edit.textChanged.connect(self.settings_changed.emit)
        self.folder_pattern_edit.textChanged.connect(self.settings_changed.emit)

        # Load initial values
        self.load_config_values()

    def reset_rename_pattern(self):
        """Reset the rename pattern to default"""
        self.rename_pattern_edit.setText(r"(\d+-\d+)(?:[_-].*?)?\.mp4$")

    def reset_validation_pattern(self):
        """Reset the validation pattern to default"""
        self.validation_pattern_edit.setText(r"^\d+-\d+\.mp4$")

    def reset_folder_pattern(self):
        """Reset the folder pattern to default"""
        self.folder_pattern_edit.setText(r"^(\d+)-\d+")

    def load_config_values(self):
        """Load values from config into UI controls"""
        self.rename_pattern_edit.setText(self.config.file_rename_pattern)
        self.validation_pattern_edit.setText(self.config.file_validation_pattern)
        self.folder_pattern_edit.setText(self.config.folder_organization_pattern)

    def save_to_config(self):
        """Save settings to config"""
        self.config.file_rename_pattern = self.rename_pattern_edit.text()
        self.config.file_validation_pattern = self.validation_pattern_edit.text()
        self.config.folder_organization_pattern = self.folder_pattern_edit.text()


class ServerOptimizationWidget(QWidget):
    """Widget for server optimization settings"""

    settings_changed = pyqtSignal()
    optimization_started = pyqtSignal()
    optimization_finished = pyqtSignal(bool, str)  # success, message

    def __init__(self, config, logger=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.logger = logger
        self.server_optimizer = ServerOptimizer(config, logger)
        self.init_ui()

    def init_ui(self):
        """Initialize UI components"""
        main_layout = QVBoxLayout(self)

        # Server type selection
        server_type_group = QGroupBox("Server Type")
        server_type_layout = QVBoxLayout()

        # Add help button
        help_layout = QHBoxLayout()
        self.server_type_combo = QComboBox()
        self.server_type_combo.addItem("Microsoft IIS", "iis")
        self.server_type_combo.addItem("Nginx", "nginx")
        self.server_type_combo.addItem("Linux System", "linux")
        help_layout.addWidget(self.server_type_combo)

        self.help_btn = QPushButton("Prerequisites")
        self.help_btn.setToolTip("View prerequisites for server optimization")
        self.help_btn.clicked.connect(self.show_prerequisites)
        help_layout.addWidget(self.help_btn)

        server_type_layout.addLayout(help_layout)

        # Add note about prerequisites
        prereq_note = QLabel(
            "<b>Note:</b> Server optimization requires specific prerequisites. "
            "Click the 'Prerequisites' button for details."
        )
        prereq_note.setWordWrap(True)
        server_type_layout.addWidget(prereq_note)

        server_type_group.setLayout(server_type_layout)

        # Create tab widget for server-specific settings
        self.server_settings_tabs = QTabWidget()

        # IIS Settings Tab
        iis_tab = QWidget()
        iis_layout = QFormLayout(iis_tab)

        self.iis_site_name_edit = QLineEdit()
        self.iis_site_name_edit.setPlaceholderText("Default Web Site")

        self.iis_video_path_edit = QLineEdit()
        self.iis_video_path_edit.setPlaceholderText(str(self.config.output_folder))
        self.iis_video_path_btn = QPushButton("Browse...")
        self.iis_video_path_btn.clicked.connect(self.browse_iis_video_path)

        video_path_layout = QHBoxLayout()
        video_path_layout.addWidget(self.iis_video_path_edit)
        video_path_layout.addWidget(self.iis_video_path_btn)

        self.iis_http2_cb = QCheckBox("Enable HTTP/2")
        self.iis_http3_cb = QCheckBox("Enable HTTP/3 with Alt-Svc headers")
        self.iis_http3_cb.setToolTip("Enables HTTP/3 auto-upgrading via Alt-Svc headers. Improves performance for mobile users.")

        # Add HTTP/3 info label
        http3_info = QLabel(
            "<small>HTTP/3 uses UDP/443 and improves performance for mobile users (>20% of typical user base). "
            "Recommended for Adaptive Bitrate (ABR) streaming.</small>"
        )
        http3_info.setWordWrap(True)

        self.iis_cors_cb = QCheckBox("Enable CORS")
        self.iis_cors_origin_edit = QLineEdit()
        self.iis_cors_origin_edit.setPlaceholderText("*")

        iis_layout.addRow(QLabel("Site Name:"), self.iis_site_name_edit)
        iis_layout.addRow(QLabel("Video Path:"), video_path_layout)
        iis_layout.addRow(self.iis_http2_cb)
        iis_layout.addRow(self.iis_http3_cb)
        iis_layout.addRow(http3_info)
        iis_layout.addRow(self.iis_cors_cb)
        iis_layout.addRow(QLabel("CORS Origin:"), self.iis_cors_origin_edit)

        # Nginx Settings Tab
        nginx_tab = QWidget()
        nginx_layout = QFormLayout(nginx_tab)

        self.nginx_output_path_edit = QLineEdit()
        self.nginx_output_path_edit.setPlaceholderText(str(self.config.output_folder / "nginx.conf"))
        self.nginx_output_path_btn = QPushButton("Browse...")
        self.nginx_output_path_btn.clicked.connect(self.browse_nginx_output_path)

        nginx_output_layout = QHBoxLayout()
        nginx_output_layout.addWidget(self.nginx_output_path_edit)
        nginx_output_layout.addWidget(self.nginx_output_path_btn)

        self.nginx_server_name_edit = QLineEdit()
        self.nginx_server_name_edit.setPlaceholderText("yourdomain.com")
        self.nginx_ssl_cb = QCheckBox("Enable SSL/TLS Configuration")
        self.nginx_http3_cb = QCheckBox("Enable HTTP/3 with Alt-Svc headers")
        self.nginx_http3_cb.setToolTip("Enables HTTP/3 auto-upgrading via Alt-Svc headers. Improves performance for mobile users.")

        # Add HTTP/3 info label
        nginx_http3_info = QLabel(
            "<small>HTTP/3 uses UDP/443 and improves performance for mobile users (>20% of typical user base). "
            "Recommended for Adaptive Bitrate (ABR) streaming.</small>"
        )
        nginx_http3_info.setWordWrap(True)

        nginx_layout.addRow(QLabel("Output Path:"), nginx_output_layout)
        nginx_layout.addRow(QLabel("Server Name:"), self.nginx_server_name_edit)
        nginx_layout.addRow(self.nginx_ssl_cb)
        nginx_layout.addRow(self.nginx_http3_cb)
        nginx_layout.addRow(nginx_http3_info)

        # Linux Settings Tab
        linux_tab = QWidget()
        linux_layout = QVBoxLayout(linux_tab)

        self.linux_apply_cb = QCheckBox("Apply changes directly (requires Linux and sudo privileges)")
        linux_note = QLabel(
            "<b>Note:</b> If not applying changes directly, a script will be generated "
            "that you can run manually with sudo privileges."
        )
        linux_note.setWordWrap(True)

        linux_layout.addWidget(self.linux_apply_cb)
        linux_layout.addWidget(linux_note)
        linux_layout.addStretch()

        # Add tabs to tab widget
        self.server_settings_tabs.addTab(iis_tab, "IIS Settings")
        self.server_settings_tabs.addTab(nginx_tab, "Nginx Settings")
        self.server_settings_tabs.addTab(linux_tab, "Linux Settings")

        # Optimization button
        self.optimize_btn = QPushButton("Optimize Server")
        self.optimize_btn.setMinimumHeight(40)
        self.optimize_btn.clicked.connect(self.optimize_server)

        # Status label
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)

        # Add to main layout
        main_layout.addWidget(server_type_group)
        main_layout.addWidget(self.server_settings_tabs)
        main_layout.addWidget(self.optimize_btn)
        main_layout.addWidget(self.status_label)
        main_layout.addStretch()

        # Connect signals
        self.server_type_combo.currentIndexChanged.connect(self.update_server_type)
        self.server_type_combo.currentIndexChanged.connect(self.settings_changed.emit)
        self.iis_site_name_edit.textChanged.connect(self.settings_changed.emit)
        self.iis_video_path_edit.textChanged.connect(self.settings_changed.emit)
        self.iis_http2_cb.toggled.connect(self.settings_changed.emit)
        self.iis_cors_cb.toggled.connect(self.settings_changed.emit)
        self.iis_cors_origin_edit.textChanged.connect(self.settings_changed.emit)
        self.nginx_output_path_edit.textChanged.connect(self.settings_changed.emit)
        self.nginx_server_name_edit.textChanged.connect(self.settings_changed.emit)
        self.nginx_ssl_cb.toggled.connect(self.settings_changed.emit)
        self.linux_apply_cb.toggled.connect(self.settings_changed.emit)

        # Load initial values
        self.load_config_values()
        self.update_server_type()

    def update_server_type(self):
        """Update UI based on selected server type"""
        server_type = self.server_type_combo.currentData()
        self.server_settings_tabs.setCurrentIndex({
            "iis": 0,
            "nginx": 1,
            "linux": 2
        }.get(server_type, 0))

        # Update button text
        if server_type == "nginx":
            self.optimize_btn.setText("Generate Nginx Configuration")
        elif server_type == "linux" and not self.linux_apply_cb.isChecked():
            self.optimize_btn.setText("Generate Optimization Script")
        else:
            self.optimize_btn.setText("Optimize Server")

        # Disable Linux apply checkbox on non-Linux systems
        if server_type == "linux":
            is_linux = platform.system() == "Linux"
            self.linux_apply_cb.setEnabled(is_linux)
            if not is_linux and self.linux_apply_cb.isChecked():
                self.linux_apply_cb.setChecked(False)
                self.status_label.setText("Direct application of Linux optimizations is only available on Linux systems.")

    def browse_iis_video_path(self):
        """Browse for IIS video path"""
        current_path = self.iis_video_path_edit.text() or str(self.config.output_folder)
        path = QFileDialog.getExistingDirectory(self, "Select Video Directory", current_path)
        if path:
            self.iis_video_path_edit.setText(path)

    def browse_nginx_output_path(self):
        """Browse for Nginx output path"""
        current_path = self.nginx_output_path_edit.text() or str(self.config.output_folder / "nginx.conf")
        path, _ = QFileDialog.getSaveFileName(self, "Save Nginx Configuration", current_path, "Configuration Files (*.conf)")
        if path:
            self.nginx_output_path_edit.setText(path)

    def load_config_values(self):
        """Load values from config into UI controls"""
        # Server type
        server_type = self.config.server_optimization.get("server_type", "iis")
        index = self.server_type_combo.findData(server_type)
        if index >= 0:
            self.server_type_combo.setCurrentIndex(index)

        # IIS settings
        iis_config = self.config.server_optimization.get("iis", {})
        self.iis_site_name_edit.setText(iis_config.get("site_name", "Default Web Site"))
        self.iis_video_path_edit.setText(iis_config.get("video_path", str(self.config.output_folder)))
        self.iis_http2_cb.setChecked(iis_config.get("enable_http2", True))
        self.iis_http3_cb.setChecked(iis_config.get("enable_http3", False))
        self.iis_cors_cb.setChecked(iis_config.get("enable_cors", True))
        self.iis_cors_origin_edit.setText(iis_config.get("cors_origin", "*"))

        # Nginx settings
        nginx_config = self.config.server_optimization.get("nginx", {})
        self.nginx_output_path_edit.setText(nginx_config.get("output_path", str(self.config.output_folder / "nginx.conf")))
        self.nginx_server_name_edit.setText(nginx_config.get("server_name", "yourdomain.com"))
        self.nginx_ssl_cb.setChecked(nginx_config.get("ssl_enabled", True))
        self.nginx_http3_cb.setChecked(nginx_config.get("enable_http3", False))

        # Linux settings
        linux_config = self.config.server_optimization.get("linux", {})
        self.linux_apply_cb.setChecked(linux_config.get("apply_changes", False))

    def save_to_config(self):
        """Save settings to config"""
        # Server type
        server_type = self.server_type_combo.currentData()
        self.config.server_optimization["server_type"] = server_type

        # IIS settings
        self.config.server_optimization["iis"] = {
            "site_name": self.iis_site_name_edit.text() or "Default Web Site",
            "video_path": self.iis_video_path_edit.text() or str(self.config.output_folder),
            "enable_http2": self.iis_http2_cb.isChecked(),
            "enable_http3": self.iis_http3_cb.isChecked(),
            "enable_cors": self.iis_cors_cb.isChecked(),
            "cors_origin": self.iis_cors_origin_edit.text() or "*"
        }

        # Nginx settings
        self.config.server_optimization["nginx"] = {
            "output_path": self.nginx_output_path_edit.text() or str(self.config.output_folder / "nginx.conf"),
            "server_name": self.nginx_server_name_edit.text() or "yourdomain.com",
            "ssl_enabled": self.nginx_ssl_cb.isChecked(),
            "enable_http3": self.nginx_http3_cb.isChecked()
        }

        # Linux settings
        self.config.server_optimization["linux"] = {
            "apply_changes": self.linux_apply_cb.isChecked()
        }

    def show_prerequisites(self):
        """Show prerequisites for server optimization"""
        from PyQt5.QtWidgets import QDialog, QTextBrowser, QVBoxLayout, QPushButton
        import os
        from pathlib import Path

        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Server Optimization Prerequisites")
        dialog.setMinimumSize(700, 500)

        # Create layout
        layout = QVBoxLayout(dialog)

        # Create text browser
        text_browser = QTextBrowser()
        text_browser.setOpenExternalLinks(True)

        # Load markdown file
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        md_path = base_dir / "docs" / "SERVER_OPTIMIZATION.md"

        if md_path.exists():
            with open(md_path, 'r') as f:
                content = f.read()

            # Simple markdown to HTML conversion for headers and code blocks
            # This is a basic implementation - for a full solution, consider using a markdown library
            html_content = content

            # Convert headers
            html_content = html_content.replace("# ", "<h1>")
            html_content = html_content.replace("## ", "<h2>")
            html_content = html_content.replace("### ", "<h3>")

            # Close header tags
            html_content = html_content.replace("\n", "</h1>\n", 1)  # First h1
            html_content = html_content.replace("\n", "</h2>\n", html_content.count("<h2>"))
            html_content = html_content.replace("\n", "</h3>\n", html_content.count("<h3>"))

            # Convert code blocks
            html_content = html_content.replace("```powershell\n", "<pre><code>")
            html_content = html_content.replace("```bash\n", "<pre><code>")
            html_content = html_content.replace("```\n", "</code></pre>\n")

            # Set content
            text_browser.setHtml(html_content)
        else:
            text_browser.setPlainText("Prerequisites documentation not found. Please refer to the docs/SERVER_OPTIMIZATION.md file.")

        layout.addWidget(text_browser)

        # Add close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        # Show dialog
        dialog.exec_()

    def optimize_server(self):
        """Run server optimization based on current settings"""
        # Save current settings to config
        self.save_to_config()

        # Get server type
        server_type = self.config.server_optimization["server_type"]

        # Show confirmation dialog
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)

        if server_type == "iis":
            msg.setText("This will optimize your IIS server for video streaming.")
            msg.setInformativeText("The script requires administrator privileges and will modify system settings. Continue?")
        elif server_type == "nginx":
            msg.setText("This will generate an optimized Nginx configuration file.")
            msg.setInformativeText("You will need to manually apply this configuration to your Nginx server. Continue?")
        elif server_type == "linux":
            if self.config.server_optimization["linux"]["apply_changes"]:
                msg.setText("This will apply system-level optimizations to your Linux server.")
                msg.setInformativeText("The script requires sudo privileges and will modify system settings. Continue?")
            else:
                msg.setText("This will generate a Linux optimization script.")
                msg.setInformativeText("You will need to manually run this script with sudo privileges. Continue?")

        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)

        if msg.exec_() != QMessageBox.Yes:
            return

        # Emit optimization started signal
        self.optimization_started.emit()

        # Clear status
        self.status_label.setText("")

        # Run optimization based on server type
        success = False
        message = ""
        script_path = None

        try:
            if server_type == "iis":
                iis_config = self.config.server_optimization["iis"]
                success, message = self.server_optimizer.optimize_iis(
                    site_name=iis_config["site_name"],
                    video_path=iis_config["video_path"],
                    enable_http2=iis_config["enable_http2"],
                    enable_http3=iis_config["enable_http3"],
                    enable_cors=iis_config["enable_cors"],
                    cors_origin=iis_config["cors_origin"]
                )
            elif server_type == "nginx":
                nginx_config = self.config.server_optimization["nginx"]
                success, message = self.server_optimizer.optimize_nginx(
                    output_path=nginx_config["output_path"],
                    server_name=nginx_config["server_name"],
                    ssl_enabled=nginx_config["ssl_enabled"],
                    enable_http3=nginx_config["enable_http3"]
                )
            elif server_type == "linux":
                linux_config = self.config.server_optimization["linux"]
                success, message, script_path = self.server_optimizer.optimize_linux(
                    apply_changes=linux_config["apply_changes"]
                )
        except Exception as e:
            success = False
            message = f"Error during optimization: {str(e)}"
            if self.logger:
                self.logger.error(message)

        # Update status label
        if success:
            self.status_label.setText(f"<span style='color:green'>{message}</span>")

            # If we generated a script, ask if user wants to open it
            if script_path and os.path.exists(script_path):
                open_msg = QMessageBox()
                open_msg.setIcon(QMessageBox.Question)
                open_msg.setText("Optimization script generated successfully.")
                open_msg.setInformativeText(f"Would you like to open the script at {script_path}?")
                open_msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                open_msg.setDefaultButton(QMessageBox.Yes)

                if open_msg.exec_() == QMessageBox.Yes:
                    # Open the script in the default text editor
                    import subprocess
                    if platform.system() == "Windows":
                        os.startfile(script_path)
                    elif platform.system() == "Darwin":  # macOS
                        subprocess.call(["open", script_path])
                    else:  # Linux
                        subprocess.call(["xdg-open", script_path])
        else:
            self.status_label.setText(f"<span style='color:red'>{message}</span>")

        # Emit optimization finished signal
        self.optimization_finished.emit(success, message)
