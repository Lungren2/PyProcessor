"""
Unit tests for the theme manager.
"""
import pytest
import os
import sys
from unittest.mock import patch, MagicMock

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the module to test
from video_processor.utils.logging import Logger
from video_processor.utils.theme_manager import ThemeManager

class TestThemeManager:
    """Test the ThemeManager class functionality"""
    
    def setup_method(self):
        """Set up test environment before each test method"""
        # Create a mock QApplication
        self.app = MagicMock()
        
        # Create a logger
        self.logger = Logger(level="INFO")
    
    @patch('video_processor.utils.theme_manager.darkdetect')
    @patch('video_processor.utils.theme_manager.qdarktheme')
    def test_initialization(self, mock_qdarktheme, mock_darkdetect):
        """Test that the ThemeManager initializes correctly"""
        # Create theme manager
        theme_manager = ThemeManager(self.app, self.logger)
        
        # Check that the theme manager was created
        assert theme_manager.app == self.app
        assert theme_manager.logger == self.logger
    
    @patch('video_processor.utils.theme_manager.darkdetect')
    @patch('video_processor.utils.theme_manager.qdarktheme')
    def test_setup_theme_light(self, mock_qdarktheme, mock_darkdetect):
        """Test setting up light theme"""
        # Mock darkdetect to return 'Light'
        mock_darkdetect.theme.return_value = 'Light'
        
        # Create theme manager
        theme_manager = ThemeManager(self.app, self.logger)
        
        # Set up theme
        theme_manager.setup_theme()
        
        # Verify that the light theme was applied
        mock_qdarktheme.setup_theme.assert_called_once_with('light')
    
    @patch('video_processor.utils.theme_manager.darkdetect')
    @patch('video_processor.utils.theme_manager.qdarktheme')
    def test_setup_theme_dark(self, mock_qdarktheme, mock_darkdetect):
        """Test setting up dark theme"""
        # Mock darkdetect to return 'Dark'
        mock_darkdetect.theme.return_value = 'Dark'
        
        # Create theme manager
        theme_manager = ThemeManager(self.app, self.logger)
        
        # Set up theme
        theme_manager.setup_theme()
        
        # Verify that the dark theme was applied
        mock_qdarktheme.setup_theme.assert_called_once_with('dark')
    
    @patch('video_processor.utils.theme_manager.darkdetect')
    @patch('video_processor.utils.theme_manager.qdarktheme')
    def test_setup_theme_no_darkdetect(self, mock_qdarktheme, mock_darkdetect):
        """Test setting up theme when darkdetect is not available"""
        # Mock darkdetect.theme to raise an exception
        mock_darkdetect.theme.side_effect = Exception("darkdetect not available")
        
        # Create theme manager
        theme_manager = ThemeManager(self.app, self.logger)
        
        # Set up theme
        theme_manager.setup_theme()
        
        # Verify that the default theme was applied
        mock_qdarktheme.setup_theme.assert_called_once_with('light')  # Default to light
    
    @patch('video_processor.utils.theme_manager.darkdetect')
    @patch('video_processor.utils.theme_manager.qdarktheme')
    def test_setup_theme_no_qdarktheme(self, mock_qdarktheme, mock_darkdetect):
        """Test setting up theme when qdarktheme is not available"""
        # Mock darkdetect to return 'Dark'
        mock_darkdetect.theme.return_value = 'Dark'
        
        # Mock qdarktheme.setup_theme to raise an exception
        mock_qdarktheme.setup_theme.side_effect = Exception("qdarktheme not available")
        
        # Create theme manager
        theme_manager = ThemeManager(self.app, self.logger)
        
        # Set up theme should not raise an exception
        theme_manager.setup_theme()
        
        # Verify that the logger recorded the error
        # This is hard to test directly, but we can verify that setup_theme was called
        mock_qdarktheme.setup_theme.assert_called_once_with('dark')
    
    @patch('video_processor.utils.theme_manager.darkdetect')
    @patch('video_processor.utils.theme_manager.qdarktheme')
    def test_set_theme_light(self, mock_qdarktheme, mock_darkdetect):
        """Test explicitly setting light theme"""
        # Create theme manager
        theme_manager = ThemeManager(self.app, self.logger)
        
        # Set light theme
        theme_manager.set_theme('light')
        
        # Verify that the light theme was applied
        mock_qdarktheme.setup_theme.assert_called_once_with('light')
    
    @patch('video_processor.utils.theme_manager.darkdetect')
    @patch('video_processor.utils.theme_manager.qdarktheme')
    def test_set_theme_dark(self, mock_qdarktheme, mock_darkdetect):
        """Test explicitly setting dark theme"""
        # Create theme manager
        theme_manager = ThemeManager(self.app, self.logger)
        
        # Set dark theme
        theme_manager.set_theme('dark')
        
        # Verify that the dark theme was applied
        mock_qdarktheme.setup_theme.assert_called_once_with('dark')
    
    @patch('video_processor.utils.theme_manager.darkdetect')
    @patch('video_processor.utils.theme_manager.qdarktheme')
    def test_set_theme_invalid(self, mock_qdarktheme, mock_darkdetect):
        """Test setting an invalid theme"""
        # Create theme manager
        theme_manager = ThemeManager(self.app, self.logger)
        
        # Set invalid theme
        theme_manager.set_theme('invalid')
        
        # Verify that the default theme was applied
        mock_qdarktheme.setup_theme.assert_called_once_with('light')  # Default to light
    
    @patch('video_processor.utils.theme_manager.darkdetect')
    @patch('video_processor.utils.theme_manager.qdarktheme')
    def test_toggle_theme_from_light(self, mock_qdarktheme, mock_darkdetect):
        """Test toggling theme from light to dark"""
        # Create theme manager
        theme_manager = ThemeManager(self.app, self.logger)
        
        # Set initial theme to light
        theme_manager.current_theme = 'light'
        
        # Toggle theme
        theme_manager.toggle_theme()
        
        # Verify that the theme was toggled to dark
        assert theme_manager.current_theme == 'dark'
        mock_qdarktheme.setup_theme.assert_called_once_with('dark')
    
    @patch('video_processor.utils.theme_manager.darkdetect')
    @patch('video_processor.utils.theme_manager.qdarktheme')
    def test_toggle_theme_from_dark(self, mock_qdarktheme, mock_darkdetect):
        """Test toggling theme from dark to light"""
        # Create theme manager
        theme_manager = ThemeManager(self.app, self.logger)
        
        # Set initial theme to dark
        theme_manager.current_theme = 'dark'
        
        # Toggle theme
        theme_manager.toggle_theme()
        
        # Verify that the theme was toggled to light
        assert theme_manager.current_theme == 'light'
        mock_qdarktheme.setup_theme.assert_called_once_with('light')
