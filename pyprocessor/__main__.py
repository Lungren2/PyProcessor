"""
Main entry point for the pyprocessor package.
This allows running the package with 'python -m pyprocessor'

This module provides a cross-platform entry point for PyProcessor.
"""

import sys

from pyprocessor.main import main

if __name__ == "__main__":
    sys.exit(main())
