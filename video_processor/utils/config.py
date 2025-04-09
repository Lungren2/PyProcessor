import os
import json
import multiprocessing
from pathlib import Path
import datetime

class Config:
    """Enhanced configuration management for video processor"""

    def __init__(self):
        # Base directories
        self.input_folder = Path(r"C:\inetpub\wwwroot\media\input")
        self.output_folder = Path(r"C:\inetpub\wwwroot\media\output")

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
                "360p": "1500k"
            },
            "audio_bitrates": ["192k", "128k", "96k", "64k"]
        }

        # Processing options
        self.max_parallel_jobs = self._calculate_parallel_jobs()

        # Additional settings
        self.auto_rename_files = True
        self.auto_organize_folders = True
        self.last_used_profile = "default"

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

            # Create a profiles directory in the video_processor folder
            # Get the base directory of the application
            base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            profiles_dir = base_dir / "profiles"
            profiles_dir.mkdir(exist_ok=True)

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
                "last_used_profile": self.last_used_profile,
                "saved_at": datetime.datetime.now().isoformat()
            }

            # Get the base directory of the application
            base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

            # If profile name is provided, save as a profile
            if profile_name:
                profile_path = base_dir / "profiles" / f"{profile_name}.json"
                filepath = profile_path
                self.last_used_profile = profile_name

            # If no filepath is specified, use default
            if not filepath:
                filepath = self.output_folder / "config.json"

            # Ensure directory exists
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            # Save the configuration
            with open(filepath, 'w') as f:
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
            # Get the base directory of the application
            base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

            # If profile name is provided, load from profiles directory
            if profile_name:
                filepath = base_dir / "profiles" / f"{profile_name}.json"
                self.last_used_profile = profile_name

            # If no filepath is specified, use default
            if not filepath:
                filepath = self.output_folder / "config.json"

            if not os.path.exists(filepath):
                print(f"Configuration file not found: {filepath}")
                return False

            with open(filepath, 'r') as f:
                config_dict = json.load(f)

                # Load paths
                if "input_folder" in config_dict:
                    self.input_folder = Path(config_dict["input_folder"])
                if "output_folder" in config_dict:
                    self.output_folder = Path(config_dict["output_folder"])

                # Load FFmpeg parameters
                if "ffmpeg_params" in config_dict:
                    self.ffmpeg_params.update(config_dict["ffmpeg_params"])

                # Load other settings
                if "max_parallel_jobs" in config_dict:
                    self.max_parallel_jobs = int(config_dict["max_parallel_jobs"])
                if "auto_rename_files" in config_dict:
                    self.auto_rename_files = bool(config_dict["auto_rename_files"])
                if "auto_organize_folders" in config_dict:
                    self.auto_organize_folders = bool(config_dict["auto_organize_folders"])
                if "last_used_profile" in config_dict:
                    self.last_used_profile = config_dict["last_used_profile"]

            return True
        except Exception as e:
            print(f"Error loading config: {str(e)}")
            return False

    def get_available_profiles(self):
        """Get a list of available configuration profiles"""
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
                self.input_folder = Path(self.input_folder)
            except:
                errors.append("Invalid input folder path")

        if not isinstance(self.output_folder, Path):
            try:
                self.output_folder = Path(self.output_folder)
            except:
                errors.append("Invalid output folder path")

        # Check FFmpeg parameters
        valid_encoders = ["libx265", "h264_nvenc", "libx264"]
        if self.ffmpeg_params["video_encoder"] not in valid_encoders:
            warnings.append(f"Invalid encoder: {self.ffmpeg_params['video_encoder']}. Using libx265.")
            self.ffmpeg_params["video_encoder"] = "libx265"

        valid_presets = ["ultrafast", "veryfast", "medium", None]
        if self.ffmpeg_params["preset"] not in valid_presets:
            warnings.append(f"Invalid preset: {self.ffmpeg_params['preset']}. Using ultrafast.")
            self.ffmpeg_params["preset"] = "ultrafast"

        valid_tunes = ["zerolatency", "film", "animation", None]
        if self.ffmpeg_params["tune"] not in valid_tunes:
            warnings.append(f"Invalid tune: {self.ffmpeg_params['tune']}. Using zerolatency.")
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
            warnings.append(f"Invalid parallel jobs: {self.max_parallel_jobs}. Recalculating.")
            self.max_parallel_jobs = self._calculate_parallel_jobs()

        return errors, warnings
