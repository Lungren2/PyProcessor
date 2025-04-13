import threading

# Try to import theme-related packages
try:
    import darkdetect
except ImportError:
    darkdetect = None
    print("Warning: darkdetect module not found. Please install it with 'pip install darkdetect'")

try:
    import qdarktheme
except ImportError:
    qdarktheme = None
    print("Warning: qdarktheme module not found. Please install it with 'pip install pyqtdarktheme'")

from PyQt5.QtWidgets import QStyleFactory
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt


class ThemeManager:
    """Manages application theme based on system settings"""

    def __init__(self, app=None, logger=None):
        """Initialize theme manager

        Args:
            app: QApplication instance
            logger: Logger instance
        """
        self.app = app
        self.logger = logger
        self.current_theme = None
        self.theme_listener_thread = None
        self.follow_system_theme = True

    def setup_theme(self):
        """Set up the application theme based on system settings"""
        # Default to light theme if darkdetect is not available
        theme = "light"

        # Detect system theme if darkdetect is available
        if darkdetect is not None:
            try:
                system_theme = darkdetect.theme()
                theme = "dark" if system_theme == "Dark" else "light"

                # Start theme listener thread
                self._start_theme_listener()
            except Exception as e:
                print(f"Error detecting system theme: {str(e)}")
                if self.logger:
                    self.logger.error(f"Error detecting system theme: {str(e)}")
        else:
            if self.logger:
                self.logger.warning("darkdetect module not available, defaulting to light theme")
            print("darkdetect module not available, defaulting to light theme")

        # Apply theme
        self._apply_theme(theme)

        if self.logger:
            self.logger.info(f"Applied {theme} theme")

    def set_dark_theme(self):
        """Manually set dark theme"""
        self.follow_system_theme = False
        self._apply_theme("dark")

        if self.logger:
            self.logger.info("Manually switched to dark theme")

    def set_light_theme(self):
        """Manually set light theme"""
        self.follow_system_theme = False
        self._apply_theme("light")

        if self.logger:
            self.logger.info("Manually switched to light theme")

    def toggle_theme(self):
        """Toggle between dark and light theme"""
        if self.current_theme == "dark":
            self.set_light_theme()
        else:
            self.set_dark_theme()

    def follow_system(self):
        """Follow system theme settings"""
        self.follow_system_theme = True

        # Default to light theme if darkdetect is not available
        theme = "light"

        # Detect system theme if darkdetect is available
        if darkdetect is not None:
            try:
                system_theme = darkdetect.theme()
                theme = "dark" if system_theme == "Dark" else "light"
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error detecting system theme: {str(e)}")
                print(f"Error detecting system theme: {str(e)}")
        else:
            if self.logger:
                self.logger.warning("darkdetect module not available, defaulting to light theme")
            print("darkdetect module not available, defaulting to light theme")

        self._apply_theme(theme)

        if self.logger:
            self.logger.info("Following system theme settings")

    def _apply_theme(self, theme):
        """Apply the specified theme to the application

        Args:
            theme: Theme name ('dark' or 'light')
        """
        if theme == self.current_theme:
            return

        # Try to apply theme using pyqtdarktheme if available
        if qdarktheme is not None:
            try:
                # Try to apply the theme
                if hasattr(qdarktheme, 'setup_theme'):
                    qdarktheme.setup_theme(theme)
                elif hasattr(qdarktheme, 'apply_theme'):  # Alternative function name
                    qdarktheme.apply_theme(theme)
                elif hasattr(qdarktheme, 'load_theme'):  # Another alternative
                    qdarktheme.load_theme(theme)
                else:
                    # Print available functions for debugging
                    print(f"Available qdarktheme functions: {dir(qdarktheme)}")
                    if self.logger:
                        self.logger.error("Could not find appropriate theme function in qdarktheme module")
                    self._apply_fallback_theme(theme)  # Use fallback
                    return

                self.current_theme = theme

                if self.logger:
                    self.logger.debug(f"Theme changed to: {theme}")
            except Exception as e:
                print(f"Error applying theme: {str(e)}")
                if self.logger:
                    self.logger.error(f"Error applying theme: {str(e)}")
                self._apply_fallback_theme(theme)  # Use fallback on error
        else:
            # No theme module available, use fallback
            if self.logger:
                self.logger.warning("Theme modules not available. Using built-in fallback theme.")
            print("Theme modules not available. Using built-in fallback theme.")
            self._apply_fallback_theme(theme)

    def _apply_fallback_theme(self, theme):
        """Apply a fallback theme using PyQt's built-in capabilities

        Args:
            theme: Theme name ('dark' or 'light')
        """
        if not self.app:
            if self.logger:
                self.logger.error("Cannot apply fallback theme: No QApplication instance available")
            return

        # Set the application style to Fusion (cross-platform style that supports palette customization)
        self.app.setStyle(QStyleFactory.create("Fusion"))

        # Create a palette based on the theme
        palette = QPalette()

        if theme == "dark":
            # Dark theme palette
            palette.setColor(QPalette.Window, QColor(53, 53, 53))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(25, 25, 25))
            palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
            palette.setColor(QPalette.ToolTipBase, Qt.white)
            palette.setColor(QPalette.ToolTipText, Qt.white)
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ButtonText, Qt.white)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Link, QColor(42, 130, 218))
            palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.HighlightedText, Qt.black)
        else:
            # Light theme palette - use default
            pass

        # Apply the palette
        self.app.setPalette(palette)
        self.current_theme = theme

        if self.logger:
            self.logger.debug(f"Applied fallback {theme} theme")

    def _start_theme_listener(self):
        """Start a thread to listen for system theme changes"""
        # Check if darkdetect is available
        if darkdetect is None:
            if self.logger:
                self.logger.warning("Cannot start theme listener: darkdetect module not available")
            return

        # Check if listener function is available
        if not hasattr(darkdetect, 'listener'):
            if self.logger:
                self.logger.warning("Cannot start theme listener: darkdetect.listener function not available")
            return

        # Check if thread is already running
        if self.theme_listener_thread is not None and self.theme_listener_thread.is_alive():
            return

        def theme_change_callback(theme_name):
            """Callback for theme changes"""
            if self.follow_system_theme:
                theme = "dark" if theme_name == "Dark" else "light"
                self._apply_theme(theme)

                if self.logger:
                    self.logger.debug(f"System theme changed to: {theme}")

        try:
            self.theme_listener_thread = threading.Thread(
                target=darkdetect.listener,
                args=(theme_change_callback,),
                daemon=True
            )
            self.theme_listener_thread.start()

            if self.logger:
                self.logger.debug("Theme listener thread started")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to start theme listener: {str(e)}")
            print(f"Failed to start theme listener: {str(e)}")
