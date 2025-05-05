"""
Path utilities for platform-agnostic path handling.

This module provides utilities for working with paths in a platform-agnostic way,
ensuring consistent behavior across Windows, macOS, and Linux.
"""

import warnings

# Show deprecation warning
warnings.warn(
    "The path_utils module is deprecated and will be removed in a future version. "
    "Please use the path_manager module instead.",
    DeprecationWarning,
    stacklevel=2,
)


# All functions are imported from path_manager
