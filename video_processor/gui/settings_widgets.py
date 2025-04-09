from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QRadioButton, QButtonGroup, QGroupBox,
                           QCheckBox, QSpinBox, QSlider, QLineEdit,
                           QPushButton, QFormLayout, QToolTip)
from PyQt5.QtCore import Qt, pyqtSignal

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
            "Default: r\".*?(\\d+-\\d+).*?\\.mp4$\" - extracts numbers-numbers pattern."
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
        self.rename_pattern_edit.setText(r".*?(\d+-\d+).*?\.mp4$")

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
