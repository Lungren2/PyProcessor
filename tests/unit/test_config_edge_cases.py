"""
Unit tests for configuration edge cases and error handling.
"""

import os
import sys
import json
import tempfile
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import the module to test
from pyprocessor.utils.config import Config


class TestConfigEdgeCases:
    """Test edge cases and error handling in the Config class"""

    def setup_method(self):
        """Set up test environment before each test method"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "config.json"
        self.profiles_dir = Path(self.temp_dir.name) / "profiles"
        self.profiles_dir.mkdir(exist_ok=True)

    def teardown_method(self):
        """Clean up after each test method"""
        self.temp_dir.cleanup()

    def test_load_nonexistent_file(self):
        """Test loading from a nonexistent file"""
        config = Config()
        nonexistent_path = Path(self.temp_dir.name) / "nonexistent.json"

        # Loading a nonexistent file should not raise an exception
        # but should log an error and use default values
        config.load(filepath=nonexistent_path)

        # Check that default values are used
        assert isinstance(config.input_folder, Path)
        assert isinstance(config.output_folder, Path)
        assert isinstance(config.ffmpeg_params, dict)

    def test_load_invalid_json(self):
        """Test loading from an invalid JSON file"""
        # Create an invalid JSON file
        with open(self.config_path, "w") as f:
            f.write("This is not valid JSON")

        config = Config()

        # Loading invalid JSON should not raise an exception
        # but should log an error and use default values
        config.load(filepath=self.config_path)

        # Check that default values are used
        assert isinstance(config.input_folder, Path)
        assert isinstance(config.output_folder, Path)
        assert isinstance(config.ffmpeg_params, dict)

    def test_load_incomplete_config(self):
        """Test loading from a config file with missing fields"""
        # Create a config file with missing fields
        incomplete_config = {
            "input_folder": str(Path(self.temp_dir.name) / "input"),
            # output_folder is missing
            "ffmpeg_params": {
                "video_encoder": "libx264"
                # other ffmpeg_params are missing
            },
            # other fields are missing
        }

        with open(self.config_path, "w") as f:
            json.dump(incomplete_config, f)

        config = Config()

        # Loading incomplete config should not raise an exception
        # but should use default values for missing fields
        config.load(filepath=self.config_path)

        # Check that specified values are loaded
        assert str(config.input_folder) == incomplete_config["input_folder"]
        assert (
            config.ffmpeg_params["video_encoder"]
            == incomplete_config["ffmpeg_params"]["video_encoder"]
        )

        # Check that default values are used for missing fields
        assert isinstance(config.output_folder, Path)
        assert "preset" in config.ffmpeg_params
        assert "tune" in config.ffmpeg_params
        assert "fps" in config.ffmpeg_params
        assert "include_audio" in config.ffmpeg_params
        assert "bitrates" in config.ffmpeg_params

    def test_load_nonexistent_profile(self):
        """Test loading a nonexistent profile"""
        config = Config()
        config.profiles_dir = self.profiles_dir

        # Loading a nonexistent profile should not raise an exception
        # but should log an error and use default values
        config.load(profile_name="nonexistent_profile")

        # Check that default values are used
        assert isinstance(config.input_folder, Path)
        assert isinstance(config.output_folder, Path)
        assert isinstance(config.ffmpeg_params, dict)

    def test_save_to_readonly_directory(self):
        """Test saving to a read-only directory"""
        # Create a read-only directory
        readonly_dir = Path(self.temp_dir.name) / "readonly"
        readonly_dir.mkdir(exist_ok=True)
        readonly_path = readonly_dir / "config.json"

        # Make the directory read-only
        os.chmod(readonly_dir, 0o500)  # r-x------

        config = Config()

        # Saving to a read-only directory should not raise an exception
        # but should log an error and return False
        result = config.save(filepath=readonly_path)

        # Check that save failed
        assert result is False
        assert not readonly_path.exists()

        # Restore permissions for cleanup
        os.chmod(readonly_dir, 0o700)  # rwx------

    def test_save_profile_to_readonly_directory(self):
        """Test saving a profile to a read-only directory"""
        # Create a read-only profiles directory
        readonly_profiles_dir = Path(self.temp_dir.name) / "readonly_profiles"
        readonly_profiles_dir.mkdir(exist_ok=True)

        # Make the directory read-only
        os.chmod(readonly_profiles_dir, 0o500)  # r-x------

        config = Config()
        config.profiles_dir = readonly_profiles_dir

        # Saving a profile to a read-only directory should not raise an exception
        # but should log an error and return False
        result = config.save(profile_name="test_profile")

        # Check that save failed
        assert result is False
        assert not (readonly_profiles_dir / "test_profile.json").exists()

        # Restore permissions for cleanup
        os.chmod(readonly_profiles_dir, 0o700)  # rwx------

    def test_validate_with_invalid_paths(self):
        """Test validation with invalid paths"""
        config = Config()

        # Set invalid paths that are not Path objects
        config.input_folder = "/nonexistent/input"
        config.output_folder = "/nonexistent/output"

        # Validate
        errors, warnings = config.validate()

        # Check that validation converted the paths to Path objects
        assert isinstance(config.input_folder, Path)
        assert isinstance(config.output_folder, Path)

        # The current implementation of validate() doesn't check if paths exist
        # It only ensures they are Path objects
        assert len(errors) == 0

    def test_validate_with_invalid_ffmpeg_params(self):
        """Test validation with invalid FFmpeg parameters"""
        config = Config()

        # Set invalid FFmpeg parameters
        config.ffmpeg_params["video_encoder"] = "invalid_encoder"
        config.ffmpeg_params["preset"] = "invalid_preset"
        config.ffmpeg_params["tune"] = "invalid_tune"
        config.ffmpeg_params["fps"] = -10  # Invalid FPS

        # Validate
        errors, warnings = config.validate()

        # Check that validation detected the warnings
        assert len(warnings) >= 4
        assert any("encoder" in warning.lower() for warning in warnings)
        assert any("preset" in warning.lower() for warning in warnings)
        assert any("tune" in warning.lower() for warning in warnings)
        assert any("fps" in warning.lower() for warning in warnings)

    def test_validate_with_invalid_parallel_jobs(self):
        """Test validation with invalid parallel jobs"""
        config = Config()

        # Set invalid parallel jobs
        config.max_parallel_jobs = -1  # Invalid number of jobs

        # Validate
        errors, warnings = config.validate()

        # Check that validation detected the warnings
        assert len(warnings) >= 1
        assert any("parallel jobs" in warning.lower() for warning in warnings)

    def test_validate_with_invalid_patterns(self):
        """Test validation with invalid regex patterns"""
        config = Config()

        # Set invalid regex patterns
        config.file_rename_pattern = "["  # Invalid regex
        config.file_validation_pattern = "["  # Invalid regex
        config.folder_organization_pattern = "["  # Invalid regex

        # Validate
        errors, warnings = config.validate()

        # Check that validation detected the warnings
        assert len(warnings) >= 3
        assert any("file rename pattern" in warning.lower() for warning in warnings)
        assert any("file validation pattern" in warning.lower() for warning in warnings)
        assert any(
            "folder organization pattern" in warning.lower() for warning in warnings
        )

    def test_apply_args_with_missing_values(self):
        """Test applying command-line arguments with missing values"""
        config = Config()

        # Create a mock args object with missing values
        class Args:
            def __init__(self):
                self.input = None
                self.output = None
                self.encoder = None
                self.preset = None
                self.tune = None
                self.fps = None
                self.no_audio = None
                self.jobs = None
                self.config = None
                self.profile = None

        args = Args()

        # Apply args to config
        config.apply_args(args)

        # Check that config was not changed
        assert isinstance(config.input_folder, Path)
        assert isinstance(config.output_folder, Path)
        assert isinstance(config.ffmpeg_params, dict)
        assert isinstance(config.max_parallel_jobs, int)

    def test_apply_args_with_invalid_values(self):
        """Test applying command-line arguments with invalid values"""
        config = Config()

        # Create a mock args object with invalid values
        class Args:
            def __init__(self):
                self.input = "/nonexistent/input"
                self.output = "/nonexistent/output"
                self.encoder = "invalid_encoder"
                self.preset = "invalid_preset"
                self.tune = "invalid_tune"
                self.fps = -10  # Invalid FPS
                self.no_audio = True
                self.jobs = -1  # Invalid number of jobs
                self.config = None
                self.profile = None

        args = Args()

        # Apply args to config
        config.apply_args(args)

        # Check that config was updated with the invalid values
        # (validation will catch these later)
        assert str(config.input_folder) == args.input
        assert str(config.output_folder) == args.output
        assert config.ffmpeg_params["video_encoder"] == args.encoder
        assert config.ffmpeg_params["preset"] == args.preset
        assert config.ffmpeg_params["tune"] == args.tune
        assert config.ffmpeg_params["fps"] == args.fps
        assert not config.ffmpeg_params["include_audio"]  # no_audio is True
        assert config.max_parallel_jobs == args.jobs
