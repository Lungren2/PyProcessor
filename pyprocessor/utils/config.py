import os
import json
import multiprocessing
import platform
from pathlib import Path
import datetime

from pyprocessor.utils.path_utils import (
    normalize_path,
    expand_env_vars,
    get_default_media_root,
    get_app_data_dir
)


class Config:
    """Enhanced configuration management for video processor"""

    def __init__(self):
        # Base directories with platform-agnostic paths
        media_root = get_default_media_root()

        # Check for environment variables
        if "MEDIA_ROOT" in os.environ:
            media_root = normalize_path(os.environ["MEDIA_ROOT"])

        self.input_folder = media_root / "input"
        self.output_folder = media_root / "output"

        # FFmpeg parameters
        self.ffmpeg_params = {
            "video_encoder": "libx265",
            "preset": "ultrafast",
            "tune": "zerolatency",
            "fps": 60,
            "include_audio": True,  # New option to include/exclude audio
            "bitrates": {
                "1080p": "11000k",
                "720p": "6500k",
                "480p": "4000k",
                "360p": "1500k",
            },
            "audio_bitrates": ["192k", "128k", "96k", "64k"],
        }

        # Processing options
        self.max_parallel_jobs = self._calculate_parallel_jobs()

        # Additional settings
        self.auto_rename_files = True
        self.auto_organize_folders = True
        self.last_used_profile = "default"

        # Regex patterns for file operations
        self.file_rename_pattern = r".*?(\d+-\d+).*?\.mp4$"
        self.file_validation_pattern = r"^\d+-\d+\.mp4$"
        self.folder_organization_pattern = r"^(\d+)-\d+"

        # Server optimization settings
        self.server_optimization = {
            "enabled": False,
            "server_type": "iis",  # Options: iis, nginx, linux
            "iis": {
                "site_name": "Default Web Site",
                "video_path": str(self.output_folder),
                "enable_http2": True,
                "enable_http3": False,  # HTTP/3 with Alt-Svc headers
                "enable_cors": True,
                "cors_origin": "*",
            },
            "nginx": {
                "output_path": str(self.output_folder / "nginx.conf"),
                "server_name": "yourdomain.com",
                "ssl_enabled": True,
                "enable_http3": False,  # HTTP/3 with Alt-Svc headers
            },
            "linux": {"apply_changes": False},
        }

        # Create directories if they don't exist
        self._ensure_directories()

    def _calculate_parallel_jobs(self):
        """Calculate optimal number of parallel jobs based on CPU cores"""
        cores = multiprocessing.cpu_count()
        return max(1, int(cores * 0.75))

    def _ensure_directories(self):
        """Create required directories if they don't exist"""
        try:
            self.input_folder.mkdir(parents=True, exist_ok=True)
            self.output_folder.mkdir(parents=True, exist_ok=True)

            # Create a profiles directory in the pyprocessor folder
            # Check for environment variable first
            if "PYPROCESSOR_PROFILES_DIR" in os.environ:
                profiles_dir = normalize_path(os.environ["PYPROCESSOR_PROFILES_DIR"])
            else:
                # Get the base directory of the application
                base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                profiles_dir = base_dir / "profiles"

            profiles_dir.mkdir(parents=True, exist_ok=True)

            return True
        except Exception as e:
            print(f"Error creating directories: {str(e)}")
            return False

    def save(self, filepath=None, profile_name=None):
        """
        Save configuration to file

        Args:
            filepath: Optional custom path for saving
            profile_name: Optional profile name to save as
        """
        try:
            # Convert Path objects to strings for JSON serialization
            config_dict = {
                "input_folder": str(self.input_folder),
                "output_folder": str(self.output_folder),
                "ffmpeg_params": self.ffmpeg_params,
                "max_parallel_jobs": self.max_parallel_jobs,
                "auto_rename_files": self.auto_rename_files,
                "auto_organize_folders": self.auto_organize_folders,
                "file_rename_pattern": self.file_rename_pattern,
                "file_validation_pattern": self.file_validation_pattern,
                "folder_organization_pattern": self.folder_organization_pattern,
                "last_used_profile": self.last_used_profile,
                "server_optimization": self.server_optimization,
                "saved_at": datetime.datetime.now().isoformat(),
            }

            # Check for environment variable first
            if "PYPROCESSOR_PROFILES_DIR" in os.environ:
                profiles_dir = normalize_path(os.environ["PYPROCESSOR_PROFILES_DIR"])
            else:
                # Get the base directory of the application
                base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                profiles_dir = base_dir / "profiles"

            # If profile name is provided, save as a profile
            if profile_name:
                profile_path = profiles_dir / f"{profile_name}.json"
                filepath = profile_path
                self.last_used_profile = profile_name

            # If no filepath is specified, use default
            if not filepath:
                filepath = self.output_folder / "config.json"

            # Ensure directory exists
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            # Save the configuration
            with open(filepath, "w") as f:
                json.dump(config_dict, f, indent=4)

            return True
        except Exception as e:
            print(f"Error saving config: {str(e)}")
            return False

    def load(self, filepath=None, profile_name=None):
        """
        Load configuration from file

        Args:
            filepath: Optional custom path for loading
            profile_name: Optional profile name to load
        """
        try:
            # Check for environment variable first
            if "PYPROCESSOR_PROFILES_DIR" in os.environ:
                profiles_dir = normalize_path(os.environ["PYPROCESSOR_PROFILES_DIR"])
            else:
                # Get the base directory of the application
                base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                profiles_dir = base_dir / "profiles"

            # If profile name is provided, load from profiles directory
            if profile_name:
                filepath = profiles_dir / f"{profile_name}.json"
                self.last_used_profile = profile_name

            # If no filepath is specified, use default
            if not filepath:
                filepath = self.output_folder / "config.json"

            if not os.path.exists(filepath):
                print(f"Configuration file not found: {filepath}")
                return False

            with open(filepath, "r") as f:
                config_dict = json.load(f)

                # Load paths with environment variable expansion
                if "input_folder" in config_dict:
                    self.input_folder = normalize_path(config_dict["input_folder"])
                if "output_folder" in config_dict:
                    self.output_folder = normalize_path(config_dict["output_folder"])

                # Load FFmpeg parameters
                if "ffmpeg_params" in config_dict:
                    self.ffmpeg_params.update(config_dict["ffmpeg_params"])

                # Load other settings
                if "max_parallel_jobs" in config_dict:
                    self.max_parallel_jobs = int(config_dict["max_parallel_jobs"])
                if "auto_rename_files" in config_dict:
                    self.auto_rename_files = bool(config_dict["auto_rename_files"])
                if "auto_organize_folders" in config_dict:
                    self.auto_organize_folders = bool(
                        config_dict["auto_organize_folders"]
                    )
                if "file_rename_pattern" in config_dict:
                    self.file_rename_pattern = config_dict["file_rename_pattern"]
                if "file_validation_pattern" in config_dict:
                    self.file_validation_pattern = config_dict[
                        "file_validation_pattern"
                    ]
                if "folder_organization_pattern" in config_dict:
                    self.folder_organization_pattern = config_dict[
                        "folder_organization_pattern"
                    ]
                if "last_used_profile" in config_dict:
                    self.last_used_profile = config_dict["last_used_profile"]

                # Load server optimization settings
                if "server_optimization" in config_dict:
                    self.server_optimization.update(config_dict["server_optimization"])

            return True
        except Exception as e:
            print(f"Error loading config: {str(e)}")
            return False

    def get_available_profiles(self):
        """Get a list of available configuration profiles"""
        # Check for environment variable first
        if "PYPROCESSOR_PROFILES_DIR" in os.environ:
            profiles_dir = normalize_path(os.environ["PYPROCESSOR_PROFILES_DIR"])
        else:
            # Get the base directory of the application
            base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            profiles_dir = base_dir / "profiles"

        if not profiles_dir.exists():
            return []

        profile_files = list(profiles_dir.glob("*.json"))
        profiles = [file.stem for file in profile_files]
        return profiles

    def validate(self):
        """Validate configuration and return any errors or warnings"""
        errors = []
        warnings = []

        # Check directories
        if not isinstance(self.input_folder, Path):
            try:
                self.input_folder = normalize_path(self.input_folder)
            except Exception as e:
                errors.append(f"Invalid input folder path: {str(e)}")

        if not isinstance(self.output_folder, Path):
            try:
                self.output_folder = normalize_path(self.output_folder)
            except Exception as e:
                errors.append(f"Invalid output folder path: {str(e)}")

        # Check FFmpeg parameters
        valid_encoders = ["libx265", "h264_nvenc", "libx264"]
        if self.ffmpeg_params["video_encoder"] not in valid_encoders:
            warnings.append(
                f"Invalid encoder: {self.ffmpeg_params['video_encoder']}. Using libx265."
            )
            self.ffmpeg_params["video_encoder"] = "libx265"

        valid_presets = ["ultrafast", "veryfast", "medium", None]
        if self.ffmpeg_params["preset"] not in valid_presets:
            warnings.append(
                f"Invalid preset: {self.ffmpeg_params['preset']}. Using ultrafast."
            )
            self.ffmpeg_params["preset"] = "ultrafast"

        valid_tunes = ["zerolatency", "film", "animation", None]
        if self.ffmpeg_params["tune"] not in valid_tunes:
            warnings.append(
                f"Invalid tune: {self.ffmpeg_params['tune']}. Using zerolatency."
            )
            self.ffmpeg_params["tune"] = "zerolatency"

        valid_fps = [30, 60, 120]
        if self.ffmpeg_params["fps"] not in valid_fps:
            warnings.append(f"Invalid FPS: {self.ffmpeg_params['fps']}. Using 60.")
            self.ffmpeg_params["fps"] = 60

        # Check audio inclusion (ensure it's boolean)
        if not isinstance(self.ffmpeg_params.get("include_audio", True), bool):
            warnings.append("Invalid audio inclusion setting. Using default (True).")
            self.ffmpeg_params["include_audio"] = True

        # Check parallel jobs
        if not isinstance(self.max_parallel_jobs, int) or self.max_parallel_jobs < 1:
            warnings.append(
                f"Invalid parallel jobs: {self.max_parallel_jobs}. Recalculating."
            )
            self.max_parallel_jobs = self._calculate_parallel_jobs()

        # Check regex patterns
        try:
            import re

            re.compile(self.file_rename_pattern)
            re.compile(self.file_validation_pattern)
            re.compile(self.folder_organization_pattern)
        except re.error as e:
            warnings.append(f"Invalid regex pattern: {str(e)}. Using defaults.")
            self.file_rename_pattern = r".*?(\d+-\d+).*?\.mp4$"
            self.file_validation_pattern = r"^\d+-\d+\.mp4$"
            self.folder_organization_pattern = r"^(\d+)-\d+"

        # Validate server optimization settings
        if not isinstance(self.server_optimization, dict):
            warnings.append("Invalid server optimization settings. Using defaults.")
            self.server_optimization = {
                "enabled": False,
                "server_type": "iis",
                "iis": {
                    "site_name": "Default Web Site",
                    "video_path": str(self.output_folder),
                    "enable_http2": True,
                    "enable_http3": False,
                    "enable_cors": True,
                    "cors_origin": "*",
                },
                "nginx": {
                    "output_path": str(self.output_folder / "nginx.conf"),
                    "server_name": "yourdomain.com",
                    "ssl_enabled": True,
                    "enable_http3": False,
                },
                "linux": {"apply_changes": False},
            }

        return errors, warnings

    def apply_args(self, args):
        """Apply command line arguments to configuration

        Args:
            args: Command line arguments object
        """
        if hasattr(args, "input") and args.input:
            self.input_folder = normalize_path(args.input)

        if hasattr(args, "output") and args.output:
            self.output_folder = normalize_path(args.output)

        if hasattr(args, "encoder") and args.encoder:
            self.ffmpeg_params["video_encoder"] = args.encoder

        if hasattr(args, "preset") and args.preset:
            self.ffmpeg_params["preset"] = args.preset

        if hasattr(args, "tune") and args.tune:
            self.ffmpeg_params["tune"] = args.tune

        if hasattr(args, "fps") and args.fps is not None:
            self.ffmpeg_params["fps"] = args.fps

        if hasattr(args, "no_audio") and args.no_audio:
            self.ffmpeg_params["include_audio"] = False

        if hasattr(args, "jobs") and args.jobs is not None:
            self.max_parallel_jobs = args.jobs
