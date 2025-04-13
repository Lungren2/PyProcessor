"""
Unit tests for the configuration management system.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import the module to test
from pyprocessor.utils.config import Config


class TestConfig:
    """Test the Config class functionality"""

    def setup_method(self):
        """Set up test environment before each test method"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "config.json"
        self.profiles_dir = Path(self.temp_dir.name) / "profiles"
        self.profiles_dir.mkdir(exist_ok=True)

        # Set environment variables for testing
        os.environ["MEDIA_ROOT"] = str(Path(self.temp_dir.name))
        os.environ["PYPROCESSOR_PROFILES_DIR"] = str(self.profiles_dir)

        # Create a test config
        self.test_config = {
            "input_folder": str(Path(self.temp_dir.name) / "input"),
            "output_folder": str(Path(self.temp_dir.name) / "output"),
            "ffmpeg_params": {
                "video_encoder": "libx264",
                "preset": "medium",
                "tune": "film",
                "fps": 30,
                "include_audio": True,
                "bitrates": {
                    "1080p": "5000k",
                    "720p": "3000k",
                    "480p": "1500k",
                    "360p": "800k",
                },
            },
            "max_parallel_jobs": 4,
            "auto_rename_files": True,
            "auto_organize_folders": True,
            "file_rename_pattern": r"(.+?)_\d+p",
            "file_validation_pattern": r".+\.mp4$",
            "folder_organization_pattern": r"(.+?)_\d+p",
            "last_used_profile": "default",
            "server_optimization": {
                "server_type": "iis",
                "enable_http2": True,
                "enable_http3": True,
                "enable_cors": True,
                "cors_origin": "*",
            },
        }

        # Write the test config to a file
        with open(self.config_path, "w") as f:
            json.dump(self.test_config, f)

        # Create a test profile
        self.test_profile = {
            "input_folder": str(Path(self.temp_dir.name) / "profile_input"),
            "output_folder": str(Path(self.temp_dir.name) / "profile_output"),
            "ffmpeg_params": {
                "video_encoder": "libx265",
                "preset": "slow",
                "tune": "animation",
                "fps": 24,
                "include_audio": True,
                "bitrates": {
                    "1080p": "6000k",
                    "720p": "3500k",
                    "480p": "1800k",
                    "360p": "1000k",
                },
            },
            "max_parallel_jobs": 2,
            "auto_rename_files": False,
            "auto_organize_folders": False,
        }

        # Write the test profile to a file
        profile_path = self.profiles_dir / "test_profile.json"
        with open(profile_path, "w") as f:
            json.dump(self.test_profile, f)

    def teardown_method(self):
        """Clean up after each test method"""
        # Clean up environment variables
        if "MEDIA_ROOT" in os.environ:
            del os.environ["MEDIA_ROOT"]
        if "PYPROCESSOR_PROFILES_DIR" in os.environ:
            del os.environ["PYPROCESSOR_PROFILES_DIR"]

        self.temp_dir.cleanup()

    def test_config_initialization(self):
        """Test that the Config class initializes with default values"""
        config = Config()

        # Check that default values are set
        assert isinstance(config.input_folder, Path)
        assert isinstance(config.output_folder, Path)
        assert isinstance(config.ffmpeg_params, dict)
        assert isinstance(config.max_parallel_jobs, int)
        assert isinstance(config.auto_rename_files, bool)
        assert isinstance(config.auto_organize_folders, bool)
        assert isinstance(config.file_rename_pattern, str)
        assert isinstance(config.file_validation_pattern, str)
        assert isinstance(config.folder_organization_pattern, str)

    def test_load_config_from_file(self):
        """Test loading configuration from a file"""
        config = Config()
        config.load(filepath=self.config_path)

        # Check that values from the file are loaded
        assert str(config.input_folder) == self.test_config["input_folder"]
        assert str(config.output_folder) == self.test_config["output_folder"]
        assert (
            config.ffmpeg_params["video_encoder"]
            == self.test_config["ffmpeg_params"]["video_encoder"]
        )
        assert (
            config.ffmpeg_params["preset"]
            == self.test_config["ffmpeg_params"]["preset"]
        )
        assert config.max_parallel_jobs == self.test_config["max_parallel_jobs"]
        assert config.auto_rename_files == self.test_config["auto_rename_files"]
        assert config.auto_organize_folders == self.test_config["auto_organize_folders"]

    def test_load_profile(self):
        """Test loading a configuration profile"""
        config = Config()

        # The profiles directory is already set via environment variable in setup_method
        # No need to manually set profiles_dir as it's not an attribute of Config

        # Load the test profile
        config.load(profile_name="test_profile")

        # Check that values from the profile are loaded
        assert str(config.input_folder) == self.test_profile["input_folder"]
        assert str(config.output_folder) == self.test_profile["output_folder"]
        assert (
            config.ffmpeg_params["video_encoder"]
            == self.test_profile["ffmpeg_params"]["video_encoder"]
        )
        assert (
            config.ffmpeg_params["preset"]
            == self.test_profile["ffmpeg_params"]["preset"]
        )
        assert config.max_parallel_jobs == self.test_profile["max_parallel_jobs"]
        assert config.auto_rename_files == self.test_profile["auto_rename_files"]
        assert (
            config.auto_organize_folders == self.test_profile["auto_organize_folders"]
        )

    def test_save_config(self):
        """Test saving configuration to a file"""
        config = Config()

        # Set some custom values
        config.input_folder = Path("/custom/input")
        config.output_folder = Path("/custom/output")
        config.ffmpeg_params["video_encoder"] = "h264_nvenc"
        config.max_parallel_jobs = 8

        # Save to a new file
        new_config_path = Path(self.temp_dir.name) / "new_config.json"
        config.save(filepath=new_config_path)

        # Check that the file exists
        assert new_config_path.exists()

        # Load the saved config and verify values
        with open(new_config_path, "r") as f:
            saved_config = json.load(f)

        assert saved_config["input_folder"] == str(config.input_folder)
        assert saved_config["output_folder"] == str(config.output_folder)
        assert (
            saved_config["ffmpeg_params"]["video_encoder"]
            == config.ffmpeg_params["video_encoder"]
        )
        assert saved_config["max_parallel_jobs"] == config.max_parallel_jobs

    def test_save_profile(self):
        """Test saving a configuration profile"""
        config = Config()

        # The profiles directory is already set via environment variable in setup_method
        # No need to manually set profiles_dir as it's not an attribute of Config

        # Set some custom values
        config.input_folder = Path("/profile/input")
        config.output_folder = Path("/profile/output")
        config.ffmpeg_params["video_encoder"] = "libx265"
        config.max_parallel_jobs = 6

        # Save as a new profile
        config.save(profile_name="new_profile")

        # Check that the profile file exists
        profile_path = self.profiles_dir / "new_profile.json"
        assert profile_path.exists()

        # Load the saved profile and verify values
        with open(profile_path, "r") as f:
            saved_profile = json.load(f)

        assert saved_profile["input_folder"] == str(config.input_folder)
        assert saved_profile["output_folder"] == str(config.output_folder)
        assert (
            saved_profile["ffmpeg_params"]["video_encoder"]
            == config.ffmpeg_params["video_encoder"]
        )
        assert saved_profile["max_parallel_jobs"] == config.max_parallel_jobs

    def test_validate_config(self):
        """Test configuration validation"""
        config = Config()

        # Test with valid configuration
        config.input_folder = Path(self.temp_dir.name)
        config.output_folder = Path(self.temp_dir.name)
        errors, _ = config.validate()  # Ignoring warnings for this test
        assert len(errors) == 0

        # Test with invalid input folder
        config.input_folder = Path("/nonexistent/folder")

        # Patch the exists method to return False for the input folder
        with patch.object(Path, 'exists', return_value=False):
            errors, _ = config.validate()  # Ignoring warnings for this test
            assert len(errors) > 0
            assert any("input folder does not exist" in error.lower() for error in errors)

    def test_apply_command_line_args(self):
        """Test applying command line arguments to configuration"""
        config = Config()

        # Create a mock args object
        class Args:
            def __init__(self, temp_dir_name):
                self.input = str(Path(temp_dir_name) / "cli_input")
                self.output = str(Path(temp_dir_name) / "cli_output")
                self.encoder = "h264_nvenc"
                self.preset = "fast"
                self.tune = "zerolatency"
                self.fps = 60
                self.no_audio = True
                self.jobs = 12

        args = Args(self.temp_dir.name)

        # Apply args to config
        config.apply_args(args)

        # Check that values from args are applied
        assert str(config.input_folder) == args.input
        assert str(config.output_folder) == args.output
        assert config.ffmpeg_params["video_encoder"] == args.encoder
        assert config.ffmpeg_params["preset"] == args.preset
        assert config.ffmpeg_params["tune"] == args.tune
        assert config.ffmpeg_params["fps"] == args.fps
        assert not config.ffmpeg_params["include_audio"]  # no_audio is True
        assert config.max_parallel_jobs == args.jobs
