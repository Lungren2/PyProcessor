"""
Performance tests for configuration and profile management.
"""

import os
import sys
import tempfile
import json
from pathlib import Path
from typing import Dict, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import the modules to test
from pyprocessor.utils.config import Config

# Import performance test base
from tests.performance.test_performance_base import (
    PerformanceTest,
    time_function,
    PerformanceResult,
    MemoryUsage,
)


class ConfigLoadPerformanceTest(PerformanceTest):
    """Test the performance of loading configuration from a file."""

    def __init__(self, config_size: str, iterations: int = 5):
        """
        Initialize the test.

        Args:
            config_size: Size of the configuration file ('small', 'medium', 'large')
            iterations: Number of iterations to run
        """
        super().__init__(f"Config Load ({config_size})", iterations)
        self.config_size = config_size
        self.temp_dir = None
        self.config_path = None
        self.config = None

    def setup(self) -> None:
        """Set up the test environment."""
        # Create temporary directory
        self.temp_dir = tempfile.TemporaryDirectory()

        # Create config
        self.config = Config()

        # Create test config file
        self.config_path = Path(self.temp_dir.name) / "config.json"

        # Create config data based on size
        config_data = self._create_config_data()

        # Write config to file
        with open(self.config_path, "w") as f:
            json.dump(config_data, f, indent=4)

    def teardown(self) -> None:
        """Clean up the test environment."""
        if self.temp_dir:
            self.temp_dir.cleanup()

    def _create_config_data(self) -> Dict[str, Any]:
        """Create test configuration data based on size."""
        # Base configuration
        config_data = {
            "input_folder": str(Path(self.temp_dir.name) / "input"),
            "output_folder": str(Path(self.temp_dir.name) / "output"),
            "max_parallel_jobs": 4,
            "auto_rename_files": True,
            "auto_organize_folders": True,
            "file_rename_pattern": r"(.+?)_\d+p",
            "file_validation_pattern": r".+\.mp4$",
            "folder_organization_pattern": r"(.+?)_\d+p",
            "last_used_profile": "default",
        }

        # Add FFmpeg parameters
        config_data["ffmpeg_params"] = {
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
        }

        # Add server optimization settings
        config_data["server_optimization"] = {
            "server_type": "iis",
            "iis": {
                "site_name": "Default Web Site",
                "video_path": str(Path(self.temp_dir.name) / "output"),
                "enable_http2": True,
                "enable_http3": True,
                "enable_cors": True,
                "cors_origin": "*",
            },
            "nginx": {
                "server_name": "example.com",
                "output_config": "/etc/nginx/sites-available/hls",
                "enable_http2": True,
                "enable_http3": True,
                "enable_cors": True,
                "cors_origin": "*",
            },
            "linux": {"apply_changes": False},
        }

        # Add additional data based on size
        if self.config_size == "medium" or self.config_size == "large":
            # Add more bitrate options
            for i in range(10):
                resolution = f"{1080 + i * 120}p"
                bitrate = f"{5000 + i * 1000}k"
                config_data["ffmpeg_params"]["bitrates"][resolution] = bitrate

            # Add more audio bitrates
            config_data["ffmpeg_params"]["audio_bitrates"] = [
                "384k",
                "256k",
                "192k",
                "128k",
                "96k",
                "64k",
                "48k",
                "32k",
            ]

            # Add more encoding options
            config_data["ffmpeg_params"]["additional_options"] = {
                "crf": 23,
                "keyint": 60,
                "min_keyint": 30,
                "scenecut": 40,
                "rc_lookahead": 40,
                "ref": 4,
                "deblock": "0:0",
                "me": "hex",
                "subme": 7,
                "psy_rd": "1.0:0.0",
                "trellis": 1,
                "no_fast_pskip": 0,
                "bframes": 3,
            }

        if self.config_size == "large":
            # Add a large number of custom settings
            config_data["custom_settings"] = {}
            for i in range(100):
                key = f"custom_setting_{i}"
                value = f"value_{i}" * 10  # Make the value longer
                config_data["custom_settings"][key] = value

            # Add a large number of presets
            config_data["presets"] = {}
            for i in range(50):
                preset_name = f"preset_{i}"
                preset_data = {
                    "video_encoder": "libx264" if i % 2 == 0 else "libx265",
                    "preset": [
                        "ultrafast",
                        "superfast",
                        "veryfast",
                        "faster",
                        "fast",
                        "medium",
                        "slow",
                        "slower",
                        "veryslow",
                    ][i % 9],
                    "tune": [
                        "film",
                        "animation",
                        "grain",
                        "stillimage",
                        "fastdecode",
                        "zerolatency",
                    ][i % 6],
                    "bitrates": {},
                }

                # Add bitrates to preset
                for j in range(10):
                    resolution = f"{1080 - j * 120}p"
                    bitrate = f"{5000 - j * 500}k"
                    preset_data["bitrates"][resolution] = bitrate

                config_data["presets"][preset_name] = preset_data

        return config_data

    def run_iteration(self) -> PerformanceResult:
        """Run a single iteration of the test."""
        _, execution_time = time_function(self.config.load, filepath=self.config_path)
        # Create a dummy memory usage object with zero values
        memory_usage = MemoryUsage(0, 0, 0)
        return PerformanceResult(execution_time, memory_usage)


class ConfigSavePerformanceTest(PerformanceTest):
    """Test the performance of saving configuration to a file."""

    def __init__(self, config_size: str, iterations: int = 5):
        """
        Initialize the test.

        Args:
            config_size: Size of the configuration file ('small', 'medium', 'large')
            iterations: Number of iterations to run
        """
        super().__init__(f"Config Save ({config_size})", iterations)
        self.config_size = config_size
        self.temp_dir = None
        self.config_path = None
        self.config = None

    def setup(self) -> None:
        """Set up the test environment."""
        # Create temporary directory
        self.temp_dir = tempfile.TemporaryDirectory()

        # Create config
        self.config = Config()

        # Set config path
        self.config_path = Path(self.temp_dir.name) / "config.json"

        # Configure the config object based on size
        self._configure_config()

    def teardown(self) -> None:
        """Clean up the test environment."""
        if self.temp_dir:
            self.temp_dir.cleanup()

    def _configure_config(self) -> None:
        """Configure the config object based on size."""
        # Base configuration
        self.config.input_folder = Path(self.temp_dir.name) / "input"
        self.config.output_folder = Path(self.temp_dir.name) / "output"
        self.config.max_parallel_jobs = 4
        self.config.auto_rename_files = True
        self.config.auto_organize_folders = True
        self.config.file_rename_pattern = r"(.+?)_\d+p"
        self.config.file_validation_pattern = r".+\.mp4$"
        self.config.folder_organization_pattern = r"(.+?)_\d+p"

        # FFmpeg parameters
        self.config.ffmpeg_params = {
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
        }

        # Server optimization settings
        self.config.server_optimization = {
            "server_type": "iis",
            "iis": {
                "site_name": "Default Web Site",
                "video_path": str(self.config.output_folder),
                "enable_http2": True,
                "enable_http3": True,
                "enable_cors": True,
                "cors_origin": "*",
            },
            "nginx": {
                "server_name": "example.com",
                "output_config": "/etc/nginx/sites-available/hls",
                "enable_http2": True,
                "enable_http3": True,
                "enable_cors": True,
                "cors_origin": "*",
            },
            "linux": {"apply_changes": False},
        }

        # Add additional data based on size
        if self.config_size == "medium" or self.config_size == "large":
            # Add more bitrate options
            for i in range(10):
                resolution = f"{1080 + i * 120}p"
                bitrate = f"{5000 + i * 1000}k"
                self.config.ffmpeg_params["bitrates"][resolution] = bitrate

            # Add more audio bitrates
            self.config.ffmpeg_params["audio_bitrates"] = [
                "384k",
                "256k",
                "192k",
                "128k",
                "96k",
                "64k",
                "48k",
                "32k",
            ]

            # Add more encoding options
            self.config.ffmpeg_params["additional_options"] = {
                "crf": 23,
                "keyint": 60,
                "min_keyint": 30,
                "scenecut": 40,
                "rc_lookahead": 40,
                "ref": 4,
                "deblock": "0:0",
                "me": "hex",
                "subme": 7,
                "psy_rd": "1.0:0.0",
                "trellis": 1,
                "no_fast_pskip": 0,
                "bframes": 3,
            }

        if self.config_size == "large":
            # Add a large number of custom settings
            self.config.custom_settings = {}
            for i in range(100):
                key = f"custom_setting_{i}"
                value = f"value_{i}" * 10  # Make the value longer
                self.config.custom_settings[key] = value

            # Add a large number of presets
            self.config.presets = {}
            for i in range(50):
                preset_name = f"preset_{i}"
                preset_data = {
                    "video_encoder": "libx264" if i % 2 == 0 else "libx265",
                    "preset": [
                        "ultrafast",
                        "superfast",
                        "veryfast",
                        "faster",
                        "fast",
                        "medium",
                        "slow",
                        "slower",
                        "veryslow",
                    ][i % 9],
                    "tune": [
                        "film",
                        "animation",
                        "grain",
                        "stillimage",
                        "fastdecode",
                        "zerolatency",
                    ][i % 6],
                    "bitrates": {},
                }

                # Add bitrates to preset
                for j in range(10):
                    resolution = f"{1080 - j * 120}p"
                    bitrate = f"{5000 - j * 500}k"
                    preset_data["bitrates"][resolution] = bitrate

                self.config.presets[preset_name] = preset_data

    def run_iteration(self) -> PerformanceResult:
        """Run a single iteration of the test."""
        _, execution_time = time_function(self.config.save, filepath=self.config_path)
        # Create a dummy memory usage object with zero values
        memory_usage = MemoryUsage(0, 0, 0)
        return PerformanceResult(execution_time, memory_usage)


class ProfileManagementPerformanceTest(PerformanceTest):
    """Test the performance of profile management operations."""

    def __init__(self, profile_count: int, iterations: int = 5):
        """
        Initialize the test.

        Args:
            profile_count: Number of profiles to create
            iterations: Number of iterations to run
        """
        super().__init__(f"Profile Management ({profile_count} profiles)", iterations)
        self.profile_count = profile_count
        self.temp_dir = None
        self.profiles_dir = None
        self.config = None

    def setup(self) -> None:
        """Set up the test environment."""
        # Create temporary directory
        self.temp_dir = tempfile.TemporaryDirectory()

        # Create profiles directory
        self.profiles_dir = Path(self.temp_dir.name) / "profiles"
        self.profiles_dir.mkdir(exist_ok=True)

        # Create config
        self.config = Config()

        # Override profiles directory
        self.config.profiles_dir = self.profiles_dir

        # Create test profiles
        self._create_test_profiles()

    def teardown(self) -> None:
        """Clean up the test environment."""
        if self.temp_dir:
            self.temp_dir.cleanup()

    def _create_test_profiles(self) -> None:
        """Create test profiles."""
        for i in range(self.profile_count):
            profile_name = f"profile_{i}"
            profile_path = self.profiles_dir / f"{profile_name}.json"

            # Create profile data
            profile_data = {
                "input_folder": str(Path(self.temp_dir.name) / f"input_{i}"),
                "output_folder": str(Path(self.temp_dir.name) / f"output_{i}"),
                "ffmpeg_params": {
                    "video_encoder": "libx264" if i % 2 == 0 else "libx265",
                    "preset": [
                        "ultrafast",
                        "superfast",
                        "veryfast",
                        "faster",
                        "fast",
                        "medium",
                        "slow",
                        "slower",
                        "veryslow",
                    ][i % 9],
                    "tune": [
                        "film",
                        "animation",
                        "grain",
                        "stillimage",
                        "fastdecode",
                        "zerolatency",
                    ][i % 6],
                    "fps": 30,
                    "include_audio": True,
                    "bitrates": {
                        "1080p": f"{5000 + i * 100}k",
                        "720p": f"{3000 + i * 100}k",
                        "480p": f"{1500 + i * 100}k",
                        "360p": f"{800 + i * 100}k",
                    },
                },
                "max_parallel_jobs": (i % 8) + 1,
                "auto_rename_files": i % 2 == 0,
                "auto_organize_folders": i % 2 == 1,
                "file_rename_pattern": r"(.+?)_\d+p",
                "file_validation_pattern": r".+\.mp4$",
                "folder_organization_pattern": r"(.+?)_\d+p",
                "last_used_profile": profile_name,
            }

            # Write profile to file
            with open(profile_path, "w") as f:
                json.dump(profile_data, f, indent=4)

    def run_iteration(self) -> PerformanceResult:
        """Run a single iteration of the test."""

        def profile_management():
            # Get available profiles
            profiles = self.config.get_available_profiles()

            # Load each profile
            for profile in profiles:
                self.config.load(profile_name=profile)

        # Use time_function for consistent timing approach
        _, execution_time = time_function(profile_management)

        # Create a dummy memory usage object with zero values
        memory_usage = MemoryUsage(0, 0, 0)
        return PerformanceResult(execution_time, memory_usage)


def test_config_load_performance():
    """Test the performance of loading configuration with different sizes."""
    config_sizes = ["small", "medium", "large"]

    for config_size in config_sizes:
        test = ConfigLoadPerformanceTest(config_size)
        results = test.run()
        test.print_results(results)

        # Assert that the performance is reasonable
        if config_size == "small":
            assert (
                results["avg_time"] < 0.01
            ), f"Config load for {config_size} config is too slow"
        elif config_size == "medium":
            assert (
                results["avg_time"] < 0.05
            ), f"Config load for {config_size} config is too slow"
        elif config_size == "large":
            assert (
                results["avg_time"] < 0.1
            ), f"Config load for {config_size} config is too slow"


def test_config_save_performance():
    """Test the performance of saving configuration with different sizes."""
    config_sizes = ["small", "medium", "large"]

    for config_size in config_sizes:
        test = ConfigSavePerformanceTest(config_size)
        results = test.run()
        test.print_results(results)

        # Assert that the performance is reasonable
        if config_size == "small":
            assert (
                results["avg_time"] < 0.01
            ), f"Config save for {config_size} config is too slow"
        elif config_size == "medium":
            assert (
                results["avg_time"] < 0.05
            ), f"Config save for {config_size} config is too slow"
        elif config_size == "large":
            assert (
                results["avg_time"] < 0.1
            ), f"Config save for {config_size} config is too slow"


def test_profile_management_performance():
    """Test the performance of profile management with different numbers of profiles."""
    profile_counts = [10, 50, 100]

    for profile_count in profile_counts:
        test = ProfileManagementPerformanceTest(profile_count)
        results = test.run()
        test.print_results(results)

        # Assert that the performance is reasonable
        if profile_count == 10:
            assert (
                results["avg_time"] < 0.1
            ), f"Profile management for {profile_count} profiles is too slow"
        elif profile_count == 50:
            assert (
                results["avg_time"] < 0.5
            ), f"Profile management for {profile_count} profiles is too slow"
        elif profile_count == 100:
            assert (
                results["avg_time"] < 1.0
            ), f"Profile management for {profile_count} profiles is too slow"


if __name__ == "__main__":
    test_config_load_performance()
    test_config_save_performance()
    test_profile_management_performance()
