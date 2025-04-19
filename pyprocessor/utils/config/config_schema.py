"""
Configuration schema for PyProcessor.

This module defines the schema for the PyProcessor configuration,
including default values, types, and validation rules.
"""

from typing import Dict, Any, List, Union, Optional
from enum import Enum


class ConfigValueType(Enum):
    """Enumeration of configuration value types."""
    
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    PATH = "path"
    ENUM = "enum"
    REGEX = "regex"


class ConfigSchema:
    """
    Configuration schema for PyProcessor.
    
    This class defines the schema for the PyProcessor configuration,
    including default values, types, and validation rules.
    """
    
    @staticmethod
    def get_schema() -> Dict[str, Any]:
        """
        Get the configuration schema.
        
        Returns:
            Dict[str, Any]: Configuration schema
        """
        from pyprocessor.utils.path_manager import get_default_media_root
        import multiprocessing
        
        # Calculate default parallel jobs
        cores = multiprocessing.cpu_count()
        default_parallel_jobs = max(1, int(cores * 0.75))
        
        # Get default media root
        media_root = get_default_media_root()
        
        # Define schema
        return {
            "input_folder": {
                "type": ConfigValueType.PATH,
                "default": str(media_root / "input"),
                "description": "Input folder for video files",
                "required": True,
                "env_var": "PYPROCESSOR_INPUT_FOLDER",
            },
            "output_folder": {
                "type": ConfigValueType.PATH,
                "default": str(media_root / "output"),
                "description": "Output folder for processed video files",
                "required": True,
                "env_var": "PYPROCESSOR_OUTPUT_FOLDER",
            },
            "ffmpeg_params": {
                "type": ConfigValueType.OBJECT,
                "description": "FFmpeg encoding parameters",
                "properties": {
                    "video_encoder": {
                        "type": ConfigValueType.ENUM,
                        "default": "libx265",
                        "description": "Video encoder to use",
                        "enum": ["libx264", "libx265", "h264_nvenc", "hevc_nvenc", "h264_amf", "hevc_amf", "h264_qsv", "hevc_qsv"],
                        "env_var": "PYPROCESSOR_VIDEO_ENCODER",
                    },
                    "preset": {
                        "type": ConfigValueType.ENUM,
                        "default": "ultrafast",
                        "description": "Encoding preset (speed vs quality)",
                        "enum": ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
                        "env_var": "PYPROCESSOR_PRESET",
                    },
                    "tune": {
                        "type": ConfigValueType.ENUM,
                        "default": "zerolatency",
                        "description": "Encoding tuning parameter",
                        "enum": ["film", "animation", "grain", "stillimage", "fastdecode", "zerolatency", "none"],
                        "env_var": "PYPROCESSOR_TUNE",
                    },
                    "fps": {
                        "type": ConfigValueType.INTEGER,
                        "default": 60,
                        "description": "Frames per second",
                        "min": 1,
                        "max": 240,
                        "env_var": "PYPROCESSOR_FPS",
                    },
                    "include_audio": {
                        "type": ConfigValueType.BOOLEAN,
                        "default": True,
                        "description": "Whether to include audio in the output",
                        "env_var": "PYPROCESSOR_INCLUDE_AUDIO",
                    },
                    "bitrates": {
                        "type": ConfigValueType.OBJECT,
                        "description": "Video bitrates for different resolutions",
                        "properties": {
                            "1080p": {
                                "type": ConfigValueType.STRING,
                                "default": "11000k",
                                "description": "Bitrate for 1080p resolution",
                            },
                            "720p": {
                                "type": ConfigValueType.STRING,
                                "default": "6500k",
                                "description": "Bitrate for 720p resolution",
                            },
                            "480p": {
                                "type": ConfigValueType.STRING,
                                "default": "4000k",
                                "description": "Bitrate for 480p resolution",
                            },
                            "360p": {
                                "type": ConfigValueType.STRING,
                                "default": "1500k",
                                "description": "Bitrate for 360p resolution",
                            },
                        },
                    },
                    "audio_bitrates": {
                        "type": ConfigValueType.ARRAY,
                        "default": ["192k", "128k", "96k", "64k"],
                        "description": "Audio bitrates for different quality levels",
                        "items": {
                            "type": ConfigValueType.STRING,
                        },
                    },
                },
            },
            "max_parallel_jobs": {
                "type": ConfigValueType.INTEGER,
                "default": default_parallel_jobs,
                "description": "Maximum number of parallel encoding jobs",
                "min": 1,
                "max": 32,
                "env_var": "PYPROCESSOR_MAX_PARALLEL_JOBS",
            },
            "auto_rename_files": {
                "type": ConfigValueType.BOOLEAN,
                "default": True,
                "description": "Whether to automatically rename files based on the pattern",
                "env_var": "PYPROCESSOR_AUTO_RENAME_FILES",
            },
            "auto_organize_folders": {
                "type": ConfigValueType.BOOLEAN,
                "default": True,
                "description": "Whether to automatically organize files into folders",
                "env_var": "PYPROCESSOR_AUTO_ORGANIZE_FOLDERS",
            },
            "last_used_profile": {
                "type": ConfigValueType.STRING,
                "default": "default",
                "description": "Last used configuration profile",
            },
            "file_rename_pattern": {
                "type": ConfigValueType.REGEX,
                "default": r".*?(\d+-\d+).*?\.mp4$",
                "description": "Regular expression pattern for renaming files",
                "env_var": "PYPROCESSOR_FILE_RENAME_PATTERN",
            },
            "file_validation_pattern": {
                "type": ConfigValueType.REGEX,
                "default": r"^\d+-\d+\.mp4$",
                "description": "Regular expression pattern for validating file names",
                "env_var": "PYPROCESSOR_FILE_VALIDATION_PATTERN",
            },
            "folder_organization_pattern": {
                "type": ConfigValueType.REGEX,
                "default": r"^(\d+)-\d+",
                "description": "Regular expression pattern for organizing files into folders",
                "env_var": "PYPROCESSOR_FOLDER_ORGANIZATION_PATTERN",
            },
            "server_optimization": {
                "type": ConfigValueType.OBJECT,
                "description": "Server optimization settings",
                "properties": {
                    "enabled": {
                        "type": ConfigValueType.BOOLEAN,
                        "default": False,
                        "description": "Whether server optimization is enabled",
                        "env_var": "PYPROCESSOR_SERVER_OPTIMIZATION_ENABLED",
                    },
                    "server_type": {
                        "type": ConfigValueType.ENUM,
                        "default": "iis",
                        "description": "Type of server to optimize",
                        "enum": ["iis", "nginx", "apache"],
                        "env_var": "PYPROCESSOR_SERVER_TYPE",
                    },
                    "iis": {
                        "type": ConfigValueType.OBJECT,
                        "description": "IIS server optimization settings",
                        "properties": {
                            "site_name": {
                                "type": ConfigValueType.STRING,
                                "default": "Default Web Site",
                                "description": "IIS site name",
                                "env_var": "PYPROCESSOR_IIS_SITE_NAME",
                            },
                            "video_path": {
                                "type": ConfigValueType.PATH,
                                "default": str(media_root / "output"),
                                "description": "Path to video files for IIS",
                                "env_var": "PYPROCESSOR_IIS_VIDEO_PATH",
                            },
                            "enable_http2": {
                                "type": ConfigValueType.BOOLEAN,
                                "default": True,
                                "description": "Whether to enable HTTP/2 for IIS",
                                "env_var": "PYPROCESSOR_IIS_ENABLE_HTTP2",
                            },
                            "enable_http3": {
                                "type": ConfigValueType.BOOLEAN,
                                "default": False,
                                "description": "Whether to enable HTTP/3 for IIS",
                                "env_var": "PYPROCESSOR_IIS_ENABLE_HTTP3",
                            },
                            "enable_cors": {
                                "type": ConfigValueType.BOOLEAN,
                                "default": True,
                                "description": "Whether to enable CORS for IIS",
                                "env_var": "PYPROCESSOR_IIS_ENABLE_CORS",
                            },
                            "cors_origin": {
                                "type": ConfigValueType.STRING,
                                "default": "*",
                                "description": "CORS origin for IIS",
                                "env_var": "PYPROCESSOR_IIS_CORS_ORIGIN",
                            },
                        },
                    },
                    "nginx": {
                        "type": ConfigValueType.OBJECT,
                        "description": "Nginx server optimization settings",
                        "properties": {
                            "output_path": {
                                "type": ConfigValueType.PATH,
                                "default": str(media_root / "output" / "nginx.conf"),
                                "description": "Output path for Nginx configuration",
                                "env_var": "PYPROCESSOR_NGINX_OUTPUT_PATH",
                            },
                            "server_name": {
                                "type": ConfigValueType.STRING,
                                "default": "yourdomain.com",
                                "description": "Server name for Nginx",
                                "env_var": "PYPROCESSOR_NGINX_SERVER_NAME",
                            },
                            "ssl_enabled": {
                                "type": ConfigValueType.BOOLEAN,
                                "default": True,
                                "description": "Whether to enable SSL for Nginx",
                                "env_var": "PYPROCESSOR_NGINX_SSL_ENABLED",
                            },
                            "enable_http3": {
                                "type": ConfigValueType.BOOLEAN,
                                "default": False,
                                "description": "Whether to enable HTTP/3 for Nginx",
                                "env_var": "PYPROCESSOR_NGINX_ENABLE_HTTP3",
                            },
                            "video_path": {
                                "type": ConfigValueType.PATH,
                                "default": str(media_root / "output"),
                                "description": "Path to video files for Nginx",
                                "env_var": "PYPROCESSOR_NGINX_VIDEO_PATH",
                            },
                        },
                    },
                    "apache": {
                        "type": ConfigValueType.OBJECT,
                        "description": "Apache server optimization settings",
                        "properties": {
                            "output_path": {
                                "type": ConfigValueType.PATH,
                                "default": str(media_root / "output" / "apache.conf"),
                                "description": "Output path for Apache configuration",
                                "env_var": "PYPROCESSOR_APACHE_OUTPUT_PATH",
                            },
                            "server_name": {
                                "type": ConfigValueType.STRING,
                                "default": "yourdomain.com",
                                "description": "Server name for Apache",
                                "env_var": "PYPROCESSOR_APACHE_SERVER_NAME",
                            },
                            "ssl_enabled": {
                                "type": ConfigValueType.BOOLEAN,
                                "default": True,
                                "description": "Whether to enable SSL for Apache",
                                "env_var": "PYPROCESSOR_APACHE_SSL_ENABLED",
                            },
                            "enable_http2": {
                                "type": ConfigValueType.BOOLEAN,
                                "default": True,
                                "description": "Whether to enable HTTP/2 for Apache",
                                "env_var": "PYPROCESSOR_APACHE_ENABLE_HTTP2",
                            },
                            "enable_http3": {
                                "type": ConfigValueType.BOOLEAN,
                                "default": False,
                                "description": "Whether to enable HTTP/3 for Apache",
                                "env_var": "PYPROCESSOR_APACHE_ENABLE_HTTP3",
                            },
                            "enable_cors": {
                                "type": ConfigValueType.BOOLEAN,
                                "default": True,
                                "description": "Whether to enable CORS for Apache",
                                "env_var": "PYPROCESSOR_APACHE_ENABLE_CORS",
                            },
                            "cors_origin": {
                                "type": ConfigValueType.STRING,
                                "default": "*",
                                "description": "CORS origin for Apache",
                                "env_var": "PYPROCESSOR_APACHE_CORS_ORIGIN",
                            },
                            "video_path": {
                                "type": ConfigValueType.PATH,
                                "default": str(media_root / "output"),
                                "description": "Path to video files for Apache",
                                "env_var": "PYPROCESSOR_APACHE_VIDEO_PATH",
                            },
                        },
                    },
                    "linux": {
                        "type": ConfigValueType.OBJECT,
                        "description": "Linux server optimization settings",
                        "properties": {
                            "apply_changes": {
                                "type": ConfigValueType.BOOLEAN,
                                "default": False,
                                "description": "Whether to apply changes to the server",
                                "env_var": "PYPROCESSOR_LINUX_APPLY_CHANGES",
                            },
                        },
                    },
                },
            },
        }
        
    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """
        Get the default configuration.
        
        Returns:
            Dict[str, Any]: Default configuration
        """
        schema = ConfigSchema.get_schema()
        return ConfigSchema._extract_defaults(schema)
        
    @staticmethod
    def _extract_defaults(schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract default values from schema.
        
        Args:
            schema: Schema to extract defaults from
            
        Returns:
            Dict[str, Any]: Default values
        """
        defaults = {}
        
        for key, value in schema.items():
            if "default" in value:
                defaults[key] = value["default"]
            elif value["type"] == ConfigValueType.OBJECT and "properties" in value:
                defaults[key] = ConfigSchema._extract_defaults(value["properties"])
                
        return defaults
