from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTextEdit,
    QPushButton,
    QHBoxLayout,
    QLabel,
    QComboBox,
)
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QFont, QTextCursor


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
