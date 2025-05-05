"""
Plugin interfaces for PyProcessor.

This module defines the interfaces for different types of plugins.
"""

from typing import Any, Dict, List

from pyprocessor.utils.plugin_manager import Plugin


class EncoderPlugin(Plugin):
    """
    Interface for encoder plugins.

    Encoder plugins provide encoding functionality for different formats.
    """

    name = "encoder_plugin"
    version = "0.1.0"
    description = "Base encoder plugin"
    author = "PyProcessor Team"

    def encode(
        self, input_file: str, output_file: str, options: Dict[str, Any] = None
    ) -> bool:
        """
        Encode a file.

        Args:
            input_file: Path to the input file
            output_file: Path to the output file
            options: Encoding options

        Returns:
            bool: True if encoding was successful, False otherwise
        """
        raise NotImplementedError("Encoder plugins must implement encode method")

    def get_supported_formats(self) -> List[str]:
        """
        Get supported input and output formats.

        Returns:
            List[str]: List of supported formats (e.g., ["mp4", "mkv"])
        """
        raise NotImplementedError(
            "Encoder plugins must implement get_supported_formats method"
        )

    def get_supported_codecs(self) -> Dict[str, List[str]]:
        """
        Get supported codecs for each format.

        Returns:
            Dict[str, List[str]]: Dictionary mapping formats to supported codecs
        """
        raise NotImplementedError(
            "Encoder plugins must implement get_supported_codecs method"
        )

    def get_default_options(self) -> Dict[str, Any]:
        """
        Get default encoding options.

        Returns:
            Dict[str, Any]: Default encoding options
        """
        raise NotImplementedError(
            "Encoder plugins must implement get_default_options method"
        )


class ProcessorPlugin(Plugin):
    """
    Interface for processor plugins.

    Processor plugins provide processing functionality for media files.
    """

    name = "processor_plugin"
    version = "0.1.0"
    description = "Base processor plugin"
    author = "PyProcessor Team"

    def process(
        self, input_file: str, output_file: str, options: Dict[str, Any] = None
    ) -> bool:
        """
        Process a file.

        Args:
            input_file: Path to the input file
            output_file: Path to the output file
            options: Processing options

        Returns:
            bool: True if processing was successful, False otherwise
        """
        raise NotImplementedError("Processor plugins must implement process method")

    def get_supported_formats(self) -> List[str]:
        """
        Get supported input and output formats.

        Returns:
            List[str]: List of supported formats (e.g., ["mp4", "mkv"])
        """
        raise NotImplementedError(
            "Processor plugins must implement get_supported_formats method"
        )

    def get_default_options(self) -> Dict[str, Any]:
        """
        Get default processing options.

        Returns:
            Dict[str, Any]: Default processing options
        """
        raise NotImplementedError(
            "Processor plugins must implement get_default_options method"
        )


class FilterPlugin(Plugin):
    """
    Interface for filter plugins.

    Filter plugins provide filtering functionality for media files.
    """

    name = "filter_plugin"
    version = "0.1.0"
    description = "Base filter plugin"
    author = "PyProcessor Team"

    def apply_filter(
        self, input_file: str, output_file: str, options: Dict[str, Any] = None
    ) -> bool:
        """
        Apply a filter to a file.

        Args:
            input_file: Path to the input file
            output_file: Path to the output file
            options: Filter options

        Returns:
            bool: True if filtering was successful, False otherwise
        """
        raise NotImplementedError("Filter plugins must implement apply_filter method")

    def get_supported_formats(self) -> List[str]:
        """
        Get supported input and output formats.

        Returns:
            List[str]: List of supported formats (e.g., ["mp4", "mkv"])
        """
        raise NotImplementedError(
            "Filter plugins must implement get_supported_formats method"
        )

    def get_default_options(self) -> Dict[str, Any]:
        """
        Get default filter options.

        Returns:
            Dict[str, Any]: Default filter options
        """
        raise NotImplementedError(
            "Filter plugins must implement get_default_options method"
        )


class AnalyzerPlugin(Plugin):
    """
    Interface for analyzer plugins.

    Analyzer plugins provide analysis functionality for media files.
    """

    name = "analyzer_plugin"
    version = "0.1.0"
    description = "Base analyzer plugin"
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
        raise NotImplementedError("Analyzer plugins must implement analyze method")

    def get_supported_formats(self) -> List[str]:
        """
        Get supported input formats.

        Returns:
            List[str]: List of supported formats (e.g., ["mp4", "mkv"])
        """
        raise NotImplementedError(
            "Analyzer plugins must implement get_supported_formats method"
        )

    def get_default_options(self) -> Dict[str, Any]:
        """
        Get default analysis options.

        Returns:
            Dict[str, Any]: Default analysis options
        """
        raise NotImplementedError(
            "Analyzer plugins must implement get_default_options method"
        )


class OutputPlugin(Plugin):
    """
    Interface for output plugins.

    Output plugins provide output functionality for processed files.
    """

    name = "output_plugin"
    version = "0.1.0"
    description = "Base output plugin"
    author = "PyProcessor Team"

    def output(self, input_file: str, options: Dict[str, Any] = None) -> bool:
        """
        Output a file.

        Args:
            input_file: Path to the input file
            options: Output options

        Returns:
            bool: True if output was successful, False otherwise
        """
        raise NotImplementedError("Output plugins must implement output method")

    def get_supported_formats(self) -> List[str]:
        """
        Get supported input formats.

        Returns:
            List[str]: List of supported formats (e.g., ["mp4", "mkv"])
        """
        raise NotImplementedError(
            "Output plugins must implement get_supported_formats method"
        )

    def get_default_options(self) -> Dict[str, Any]:
        """
        Get default output options.

        Returns:
            Dict[str, Any]: Default output options
        """
        raise NotImplementedError(
            "Output plugins must implement get_default_options method"
        )
