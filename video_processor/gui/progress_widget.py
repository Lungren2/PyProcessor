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
