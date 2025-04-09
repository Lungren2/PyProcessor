# Theme Support

The Video Processor application supports automatic switching between dark and light themes based on your system settings.

## Features

- Automatically detects and follows your system's theme settings (dark/light mode)
- Allows manual switching between dark and light themes
- Provides a fallback theme when external theme packages are not available

## Installation

For the best theme experience, install the following packages:

```bash
pip install darkdetect pyqtdarktheme
```

### Dependencies

- **darkdetect**: Detects the system's dark/light mode setting
- **pyqtdarktheme**: Provides high-quality dark and light themes for PyQt applications

## Usage

The theme can be changed through the "Theme" menu in the application:

- **Dark Mode**: Manually switch to dark theme
- **Light Mode**: Manually switch to light theme
- **Follow System Settings**: Automatically follow your system's theme settings (default)

## Fallback Theme

If the external theme packages are not installed, the application will use a built-in fallback theme based on PyQt's Fusion style. While this provides basic dark/light mode functionality, it is recommended to install the external packages for the best visual experience.

## Troubleshooting

If you encounter any issues with the theme:

1. Make sure you have installed the required packages
2. Try manually switching between themes using the Theme menu
3. Restart the application after installing new packages

## Technical Details

The theme system uses:

- `darkdetect` to detect the system theme and listen for theme changes
- `pyqtdarktheme` (qdarktheme) to apply high-quality themes to the application
- PyQt's built-in styling capabilities as a fallback

The theme manager is implemented in `video_processor/utils/theme_manager.py`.
