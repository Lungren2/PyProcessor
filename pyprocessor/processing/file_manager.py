import warnings

from pyprocessor.utils.file_manager import get_file_manager


class FileManager:
    """Enhanced file manager with option controls

    This is a compatibility class that uses the new centralized file manager.
    It will be deprecated in a future version.
    """

    def __init__(self, config, logger):
        # Show deprecation warning
        warnings.warn(
            "The FileManager class in processing/file_manager.py is deprecated and will be removed in a future version. "
            "Please use the FileManager class from utils/file_manager.py instead.",
            DeprecationWarning,
            stacklevel=2
        )

        self.config = config
        self.logger = logger

        # Get the centralized file manager
        self.file_manager = get_file_manager(config, logger)

    def rename_files(self):
        """Rename files based on pattern matching and configuration"""
        return self.file_manager.rename_files()

    def validate_files(self):
        """Validate files for correct naming pattern"""
        return self.file_manager.validate_files()

    def organize_folders(self):
        """Organize processed folders based on naming patterns and configuration"""
        return self.file_manager.organize_folders()

    def get_input_files_info(self):
        """Get information about input files"""
        return self.file_manager.get_input_files_info()

    def clean_input_directory(self):
        """Clean up processed files from input directory (optional)"""
        count, _ = self.file_manager.clean_input_directory(dry_run=True)
        return count
