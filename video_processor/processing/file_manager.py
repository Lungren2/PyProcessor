import os
import re
import shutil
from pathlib import Path

class FileManager:
    """Enhanced file manager with option controls"""

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.input_folder = Path(config.input_folder)
        self.output_folder = Path(config.output_folder)

    def rename_files(self):
        """Rename files based on pattern matching and configuration"""
        # Skip if auto-rename is disabled
        if not self.config.auto_rename_files:
            self.logger.info("File renaming skipped (disabled in config)")
            return 0

        self.logger.info("Starting file renaming process")
        files = list(self.input_folder.glob('*.mp4'))
        total_files = len(files)
        renamed_count = 0

        for i, file in enumerate(files):
            try:
                # Remove all whitespace first
                name_without_spaces = file.name.replace(' ', '')

                # Check if matches pattern
                match = re.match(self.config.file_rename_pattern, name_without_spaces)
                if match:
                    new_name = f"{match.group(1)}.mp4"
                    new_path = file.parent / new_name

                    # Skip if file already has correct name
                    if file.name == new_name:
                        self.logger.debug(f"Skipping already correctly named file: {file.name}")
                        continue

                    # Check if destination exists
                    if new_path.exists():
                        self.logger.warning(f"Cannot rename {file.name} to {new_name} - destination exists")
                        continue

                    # Rename the file
                    file.rename(new_path)
                    self.logger.info(f"Renamed: {file.name} to {new_name}")
                    renamed_count += 1
                else:
                    self.logger.warning(f"Skipping non-matching file: {file.name}")
            except Exception as e:
                self.logger.error(f"Failed to rename {file.name}: {str(e)}")

        self.logger.info(f"File renaming completed: {renamed_count} of {total_files} files renamed")
        return renamed_count

    def validate_files(self):
        """Validate files for correct naming pattern"""
        valid_files = []
        invalid_files = []

        for file in self.input_folder.glob('*.mp4'):
            if re.match(self.config.file_validation_pattern, file.name):
                valid_files.append(file)
            else:
                invalid_files.append(file.name)

        return valid_files, invalid_files

    def organize_folders(self):
        """Organize processed folders based on naming patterns and configuration"""
        # Skip if auto-organize is disabled
        if not self.config.auto_organize_folders:
            self.logger.info("Folder organization skipped (disabled in config)")
            return 0

        self.logger.info("Starting folder organization")
        folders = list(self.output_folder.glob('*-*'))
        moved_count = 0

        for folder in folders:
            try:
                if not folder.is_dir():
                    continue

                match = re.match(self.config.folder_organization_pattern, folder.name)
                if match:
                    parent_folder = self.output_folder / match.group(1)
                    parent_folder.mkdir(exist_ok=True)

                    # Destination path
                    dest = parent_folder / folder.name

                    # Skip if already in correct location
                    if str(folder.parent) == str(parent_folder):
                        self.logger.debug(f"Folder already correctly organized: {folder.name}")
                        continue

                    # Check if destination exists
                    if dest.exists():
                        self.logger.warning(f"Cannot move {folder.name} - destination exists")
                        continue

                    # Move the folder
                    shutil.move(str(folder), str(dest))
                    self.logger.info(f"Moved {folder.name} to {parent_folder}")
                    moved_count += 1
            except Exception as e:
                self.logger.error(f"Failed to organize folder {folder.name}: {str(e)}")

        self.logger.info(f"Folder organization completed: {moved_count} folders moved")
        return moved_count

    def get_input_files_info(self):
        """Get information about input files"""
        files = list(self.input_folder.glob('*.mp4'))
        valid_files, invalid_files = self.validate_files()

        total_size = sum(f.stat().st_size for f in files)
        # Convert to MB
        total_size_mb = total_size / (1024 * 1024)

        return {
            'total_files': len(files),
            'valid_files': len(valid_files),
            'invalid_files': len(invalid_files),
            'total_size_mb': total_size_mb
        }

    def clean_input_directory(self):
        """Clean up processed files from input directory (optional)"""
        try:
            # This is a potentially destructive operation, so we'll implement
            # it with safeguards

            # Get all processed video names from output directory
            processed_videos = set()
            for folder in self.output_folder.glob('*-*'):
                if folder.is_dir():
                    processed_videos.add(folder.name + '.mp4')

            # Count how many files would be deleted
            to_delete = []
            for file in self.input_folder.glob('*.mp4'):
                if file.name in processed_videos:
                    to_delete.append(file)

            if not to_delete:
                self.logger.info("No processed files found to clean up")
                return 0

            self.logger.warning(f"Would delete {len(to_delete)} processed files from input directory")
            # Since this is destructive, we won't actually implement the deletion here
            # but would require explicit confirmation from the user

            return len(to_delete)
        except Exception as e:
            self.logger.error(f"Error in clean_input_directory: {str(e)}")
            return 0
