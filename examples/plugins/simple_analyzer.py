"""
Simple analyzer plugin example.

This plugin demonstrates how to create a simple analyzer plugin.
"""

import os
import json
from typing import Dict, List, Any

from pyprocessor.plugins.interfaces import AnalyzerPlugin


class SimpleAnalyzerPlugin(AnalyzerPlugin):
    """
    Simple analyzer plugin.

    This plugin analyzes media files and returns basic information.
    """

    name = "simple_analyzer"
    version = "0.1.0"
    description = "Simple analyzer plugin"
    author = "PyProcessor Team"

    def analyze(
        self, input_file: str, options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Analyze a file.

        Args:
            input_file: Path to the input file
            options: Analysis options

        Returns:
            Dict[str, Any]: Analysis results
        """
        if not self.is_initialized():
            self.logger.error("Plugin not initialized")
            return {"error": "Plugin not initialized"}

        if not self.is_enabled():
            self.logger.error("Plugin not enabled")
            return {"error": "Plugin not enabled"}

        # Get analysis options
        options = options or self.get_default_options()

        # Check if file exists
        if not os.path.exists(input_file):
            self.logger.error(f"File not found: {input_file}")
            return {"error": f"File not found: {input_file}"}

        # Get basic file information
        file_size = os.path.getsize(input_file)
        file_extension = os.path.splitext(input_file)[1].lower().lstrip(".")

        # Perform analysis based on options
        results = {
            "file_path": input_file,
            "file_size": file_size,
            "file_extension": file_extension,
        }

        # Add additional analysis based on options
        if options.get("include_timestamps", False):
            results.update(
                {
                    "created_at": os.path.getctime(input_file),
                    "modified_at": os.path.getmtime(input_file),
                    "accessed_at": os.path.getatime(input_file),
                }
            )

        if options.get("include_permissions", False):
            results.update(
                {
                    "permissions": oct(os.stat(input_file).st_mode)[-3:],
                }
            )

        # Save results to file if requested
        if options.get("save_results", False) and options.get("output_file"):
            try:
                with open(options["output_file"], "w") as f:
                    json.dump(results, f, indent=4)
                self.logger.debug(f"Analysis results saved to {options['output_file']}")
            except Exception as e:
                self.logger.error(f"Error saving analysis results: {str(e)}")

        return results

    def get_supported_formats(self) -> List[str]:
        """
        Get supported input formats.

        Returns:
            List[str]: List of supported formats
        """
        # This analyzer supports all file formats
        return ["*"]

    def get_default_options(self) -> Dict[str, Any]:
        """
        Get default analysis options.

        Returns:
            Dict[str, Any]: Default analysis options
        """
        return {
            "include_timestamps": True,
            "include_permissions": True,
            "save_results": False,
            "output_file": None,
        }
