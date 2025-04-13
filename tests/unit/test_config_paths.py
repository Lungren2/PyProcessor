"""
Unit tests for configuration path handling.
"""

import json
import os
import tempfile
from pathlib import Path


from pyprocessor.utils.config import Config


class TestConfigPaths:
    """Test the configuration path handling"""

    def setup_method(self):
        """Set up test environment before each test method"""
        # Save original environment variables
        self.original_env = os.environ.copy()

        # Create temporary directories
        self.temp_dir = tempfile.TemporaryDirectory()
        self.media_root = Path(self.temp_dir.name) / "media"
        self.profiles_dir = Path(self.temp_dir.name) / "profiles"

        # Create directories
        self.media_root.mkdir(exist_ok=True)
        (self.media_root / "input").mkdir(exist_ok=True)
        (self.media_root / "output").mkdir(exist_ok=True)
        self.profiles_dir.mkdir(exist_ok=True)

        # Set environment variables
        os.environ["MEDIA_ROOT"] = str(self.media_root)
        os.environ["PYPROCESSOR_PROFILES_DIR"] = str(self.profiles_dir)

    def teardown_method(self):
        """Clean up after each test method"""
        # Restore original environment variables
        os.environ.clear()
        os.environ.update(self.original_env)

        # Clean up temporary directory
        self.temp_dir.cleanup()

    def test_config_init_with_env_vars(self):
        """Test that Config initializes with environment variables"""
        config = Config()

        # Check that paths are set correctly
        assert config.input_folder == self.media_root / "input"
        assert config.output_folder == self.media_root / "output"

    def test_config_save_load_with_env_vars(self):
        """Test saving and loading config with environment variables"""
        config = Config()

        # Modify some settings
        config.max_parallel_jobs = 3
        config.auto_rename_files = False

        # Save to a profile
        config.save(profile_name="test_env_profile")

        # Check that the file was created in the profiles directory
        profile_path = self.profiles_dir / "test_env_profile.json"
        assert profile_path.exists()

        # Load the profile into a new config
        new_config = Config()
        new_config.load(profile_name="test_env_profile")

        # Check that settings were loaded correctly
        assert new_config.max_parallel_jobs == 3
        assert new_config.auto_rename_files is False
        assert new_config.input_folder == self.media_root / "input"
        assert new_config.output_folder == self.media_root / "output"

    def test_config_with_env_vars_in_json(self):
        """Test loading config with environment variables in JSON"""
        # Create a config file with environment variables
        config_data = {
            "input_folder": "${MEDIA_ROOT}/custom_input",
            "output_folder": "${MEDIA_ROOT}/custom_output",
            "max_parallel_jobs": 2
        }

        # Save to a file
        config_path = self.profiles_dir / "env_vars.json"
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        # Load the config
        config = Config()
        config.load(filepath=config_path)

        # Check that environment variables were expanded
        assert config.input_folder == self.media_root / "custom_input"
        assert config.output_folder == self.media_root / "custom_output"
        assert config.max_parallel_jobs == 2
