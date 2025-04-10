from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                           QRadioButton, QButtonGroup, QPushButton, QGroupBox,
                           QCheckBox, QSpinBox, QSlider, QTabWidget, QWidget)
from PyQt5.QtGui import QFont
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
