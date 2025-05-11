import json
import os
from pathlib import Path

from pyprocessor.utils.core.dependency_manager import check_ffmpeg
from pyprocessor.utils.file_system.temp_file_manager import (
    cleanup_temp_file,
    create_temp_dir,
    get_disk_space_info,
    mark_temp_file_in_use,
)

# Import the FFmpegManager and dependency manager
from pyprocessor.utils.media.ffmpeg_manager import FFmpegManager
from pyprocessor.utils.process.gpu_manager import (
    GPUCapability,
    get_all_gpu_usage,
    get_gpus,
    has_encoding_capability,
)
from pyprocessor.utils.security.encryption_manager import get_encryption_manager


class FFmpegEncoder:
    """FFmpeg encoder with advanced options including audio control"""

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.ffmpeg = FFmpegManager(logger)
        self.encryption_manager = get_encryption_manager()
        self.encoding_progress = 0

    def check_ffmpeg(self):
        """Check if FFmpeg is installed and available"""
        # Use the dependency manager to check FFmpeg
        is_available, _, _ = check_ffmpeg()
        return is_available

    def check_gpu_capabilities(self):
        """Check for available GPU encoding capabilities"""
        try:
            # Get available GPUs
            gpus = get_gpus()

            if not gpus:
                self.logger.info("No GPUs detected for hardware acceleration")
                return {
                    "has_gpu": False,
                    "has_h264": False,
                    "has_hevc": False,
                    "gpu_count": 0,
                    "gpu_names": [],
                }

            # Check for encoding capabilities
            has_h264 = has_encoding_capability(GPUCapability.H264)
            has_hevc = has_encoding_capability(GPUCapability.HEVC)

            gpu_names = [gpu.name for gpu in gpus]

            # Log GPU capabilities
            self.logger.info(f"Detected {len(gpus)} GPUs: {', '.join(gpu_names)}")
            if has_h264:
                self.logger.info("H.264 hardware encoding is supported (h264_nvenc)")
            if has_hevc:
                self.logger.info("HEVC hardware encoding is supported (hevc_nvenc)")

            return {
                "has_gpu": True,
                "has_h264": has_h264,
                "has_hevc": has_hevc,
                "gpu_count": len(gpus),
                "gpu_names": gpu_names,
            }

        except Exception as e:
            self.logger.warning(f"Error checking GPU capabilities: {str(e)}")
            return {
                "has_gpu": False,
                "has_h264": False,
                "has_hevc": False,
                "gpu_count": 0,
                "gpu_names": [],
            }

    def get_gpu_usage(self):
        """Get current GPU usage information"""
        try:
            gpu_usages = get_all_gpu_usage()
            if not gpu_usages:
                return None

            # Return the GPU with highest utilization
            return max(gpu_usages, key=lambda x: x.utilization)
        except Exception as e:
            self.logger.warning(f"Error getting GPU usage: {str(e)}")
            return None

    def has_audio(self, file_path):
        """Check if the video file has audio streams"""
        return self.ffmpeg.has_audio(file_path)

    def build_command(self, input_file, output_folder):
        """Build FFmpeg command for HLS encoding with audio option"""
        # Check for audio streams and respect the include_audio setting
        has_audio = self.has_audio(input_file) and self.config.ffmpeg_params.get(
            "include_audio", True
        )

        # Calculate buffer sizes
        bitrates = self.config.ffmpeg_params["bitrates"]
        bufsizes = {}
        for res, bitrate in bitrates.items():
            bufsize_value = int(bitrate.rstrip("k")) * 2
            bufsizes[res] = f"{bufsize_value}k"

        # Check GPU usage if using hardware encoding
        using_gpu = self.config.ffmpeg_params.get("video_encoder", "").endswith(
            "_nvenc"
        )
        if using_gpu:
            # Check GPU capabilities
            gpu_capabilities = self.check_gpu_capabilities()

            # Check current GPU usage
            gpu_usage = self.get_gpu_usage()

            # If GPU is heavily utilized, log a warning and consider throttling
            if gpu_usage and (
                gpu_usage.utilization > 0.8
                or (gpu_usage.encoder_usage and gpu_usage.encoder_usage > 0.8)
            ):
                self.logger.warning(
                    f"GPU is heavily utilized: {gpu_usage.utilization:.2%} util, "
                    f"{gpu_usage.encoder_usage:.2%} encoder usage"
                )
                self.logger.warning(
                    "Consider reducing batch size or using CPU encoding instead"
                )

                # If memory is also constrained, switch to CPU encoding
                if gpu_usage.memory_utilization > 0.9:
                    self.logger.warning(
                        f"GPU memory is critically low: {gpu_usage.memory_utilization:.2%} used"
                    )
                    self.logger.warning(
                        "Switching to CPU encoding due to GPU memory constraints"
                    )
                    # Switch to CPU encoding
                    self.config.ffmpeg_params["video_encoder"] = "libx264"
                    using_gpu = False

        # Build filter complex string
        filter_complex = "[0:v]split=4[v1][v2][v3][v4];[v1]scale=1920:1080[v1out];[v2]scale=1280:720[v2out];[v3]scale=854:480[v3out];[v4]scale=640:360[v4out]"

        # Build FFmpeg command
        cmd = [
            self.ffmpeg.get_ffmpeg_path(),
            "-hide_banner",
            "-loglevel",
            "info",
            "-stats",
            "-i",
            str(input_file),
            "-filter_complex",
            filter_complex,
        ]

        # Add GPU-specific options if using hardware encoding
        if using_gpu:
            # Add CUDA device selection if multiple GPUs are available
            gpu_capabilities = self.check_gpu_capabilities()
            if gpu_capabilities.get("gpu_count", 0) > 1:
                # Find the GPU with the most available memory
                gpu_usages = get_all_gpu_usage()
                if gpu_usages:
                    best_gpu = max(
                        gpu_usages, key=lambda x: (x.memory_total - x.memory_used)
                    )
                    cmd.extend(
                        ["-hwaccel", "cuda", "-hwaccel_device", str(best_gpu.index)]
                    )
                    self.logger.info(f"Selected GPU {best_gpu.index} for encoding")

        # Video streams for all resolutions
        for i, (res, bitrate) in enumerate(
            [
                ("1080p", bitrates["1080p"]),
                ("720p", bitrates["720p"]),
                ("480p", bitrates["480p"]),
                ("360p", bitrates["360p"]),
            ]
        ):
            # Map video stream
            cmd.extend(
                [
                    "-map",
                    f"[v{i+1}out]",
                    "-c:v:" + str(i),
                    self.config.ffmpeg_params["video_encoder"],
                ]
            )

            # Add preset and tune if applicable
            if self.config.ffmpeg_params["preset"]:
                cmd.extend([f"-preset:v:{i}", self.config.ffmpeg_params["preset"]])
            if self.config.ffmpeg_params["tune"]:
                cmd.extend([f"-tune:v:{i}", self.config.ffmpeg_params["tune"]])

            # Bitrate settings
            cmd.extend(
                [
                    f"-b:v:{i}",
                    bitrate,
                    f"-maxrate:v:{i}",
                    bitrate,
                    f"-bufsize:v:{i}",
                    bufsizes[res],
                ]
            )

        # Audio streams if available and enabled
        audio_bitrates = self.config.ffmpeg_params["audio_bitrates"]
        if has_audio:
            for i, bitrate in enumerate(audio_bitrates):
                cmd.extend(
                    [
                        "-map",
                        "a:0",
                        f"-c:a:{i}",
                        "aac",
                        f"-b:a:{i}",
                        bitrate,
                        "-ac",
                        "2",
                    ]
                )
            var_stream_map = "v:0,a:0 v:1,a:1 v:2,a:2 v:3,a:3"
        else:
            var_stream_map = "v:0 v:1 v:2 v:3"

            # If we're intentionally excluding audio, log it
            if not self.config.ffmpeg_params.get("include_audio", True):
                self.logger.info(
                    f"Audio excluded per user settings for {input_file.name}"
                )

        # HLS parameters
        segment_path = str(output_folder) + "/%v/segment_%03d.ts"
        playlist_path = str(output_folder) + "/%v/playlist.m3u8"

        cmd.extend(
            [
                "-f",
                "hls",
                "-g",
                str(self.config.ffmpeg_params["fps"]),
                "-hls_time",
                "1",
                "-hls_playlist_type",
                "vod",
                "-hls_flags",
                "independent_segments",
                "-hls_segment_type",
                "mpegts",
                "-hls_segment_filename",
                segment_path,
                "-master_pl_name",
                "master.m3u8",
                "-var_stream_map",
                var_stream_map,
                playlist_path,
            ]
        )

        return cmd

    def encode_video(
        self,
        input_file,
        output_folder,
        progress_callback=None,
        encrypt_output=False,
        encryption_key_id=None,
    ):
        """Encode a video file to HLS format with progress updates and optional encryption"""
        temp_dir = None
        try:
            # Check disk space before starting
            disk_info = get_disk_space_info(output_folder)
            if disk_info.get("state") == "critical":
                self.logger.error(
                    f"Critical disk space: {disk_info.get('utilization', 0):.2%} used. Cannot proceed with encoding."
                )
                return False
            elif disk_info.get("state") == "warning":
                self.logger.warning(
                    f"Low disk space: {disk_info.get('utilization', 0):.2%} used. Proceed with caution."
                )

            # Create output directory structure
            output_folder = Path(output_folder)
            output_folder.mkdir(parents=True, exist_ok=True)

            # Create temporary directory for intermediate files
            temp_dir = create_temp_dir(prefix=f"ffmpeg_{input_file.stem}_")
            self.logger.debug(f"Created temporary directory: {temp_dir}")

            # Check if using GPU encoding
            using_gpu = self.config.ffmpeg_params.get("video_encoder", "").endswith(
                "_nvenc"
            )
            if using_gpu:
                # Log initial GPU state
                gpu_usage = self.get_gpu_usage()
                if gpu_usage:
                    self.logger.info(
                        f"Initial GPU state: {gpu_usage.utilization:.2%} util, "
                        f"{gpu_usage.memory_utilization:.2%} memory used, "
                        f"{gpu_usage.encoder_usage:.2%} encoder usage"
                    )

            # Build command - use temp_dir for intermediate files
            cmd = self.build_command(input_file, temp_dir)

            # Setup GPU monitoring during encoding if using GPU
            gpu_monitor_callback = None
            if using_gpu:

                def gpu_monitor_callback(progress):
                    # Check GPU usage every 10% progress
                    if int(progress * 10) > int(self.encoding_progress * 10):
                        gpu_usage = self.get_gpu_usage()
                        if gpu_usage:
                            self.logger.info(
                                f"GPU at {progress:.1%}: {gpu_usage.utilization:.2%} util, "
                                f"{gpu_usage.memory_utilization:.2%} memory, "
                                f"{gpu_usage.encoder_usage:.2%} encoder"
                            )

                        # Check disk space during encoding
                        disk_info = get_disk_space_info(temp_dir)
                        if disk_info.get("state") == "critical":
                            self.logger.error(
                                f"Critical disk space during encoding: {disk_info.get('utilization', 0):.2%} used."
                            )
                            # We'll continue but log the issue

                    self.encoding_progress = progress
                    # Call the original progress callback if provided
                    if progress_callback:
                        progress_callback(progress)

            else:
                # If not using GPU, just use the provided progress callback but still monitor disk space
                def disk_monitor_callback(progress):
                    # Check disk space every 20% progress
                    if int(progress * 5) > int(self.encoding_progress * 5):
                        disk_info = get_disk_space_info(temp_dir)
                        if disk_info.get("state") == "critical":
                            self.logger.error(
                                f"Critical disk space during encoding: {disk_info.get('utilization', 0):.2%} used."
                            )

                    self.encoding_progress = progress
                    # Call the original progress callback if provided
                    if progress_callback:
                        progress_callback(progress)

                gpu_monitor_callback = disk_monitor_callback

            # Execute FFmpeg command using the FFmpegManager
            success = self.ffmpeg.execute_command(
                cmd,
                input_file=input_file.name,
                output_folder=temp_dir,
                progress_callback=gpu_monitor_callback,
            )

            # Log final GPU state if using GPU
            if using_gpu:
                gpu_usage = self.get_gpu_usage()
                if gpu_usage:
                    self.logger.info(
                        f"Final GPU state: {gpu_usage.utilization:.2%} util, "
                        f"{gpu_usage.memory_utilization:.2%} memory used, "
                        f"{gpu_usage.encoder_usage:.2%} encoder usage"
                    )

            if not success:
                self.logger.error(f"FFmpeg encoding failed for {input_file.name}")
                return False

            # Check if output files were created in temp directory
            m3u8_file = temp_dir / "master.m3u8"
            if not m3u8_file.exists():
                self.logger.error(
                    f"Failed to create master playlist for {input_file.name}"
                )
                return False

            # Move files from temp directory to output folder
            self.logger.info(
                "Moving encoded files from temporary directory to output folder"
            )

            # Check disk space in output folder before moving files
            disk_info = get_disk_space_info(output_folder)
            if disk_info.get("state") == "critical":
                self.logger.error(
                    f"Critical disk space in output folder: {disk_info.get('utilization', 0):.2%} used. Cannot move files."
                )
                return False

            # Copy all files from temp_dir to output_folder
            for item in temp_dir.glob("**/*"):
                # Get the relative path from temp_dir
                rel_path = item.relative_to(temp_dir)
                # Create the destination path
                dest_path = output_folder / rel_path

                # Create parent directories if needed
                if not dest_path.parent.exists():
                    dest_path.parent.mkdir(parents=True, exist_ok=True)

                # Copy file if it's a file
                if item.is_file():
                    import shutil

                    shutil.copy2(item, dest_path)

            self.logger.info(f"Successfully encoded {input_file.name}")

            # Encrypt output if requested
            if encrypt_output:
                self.logger.info(f"Encrypting output files in {output_folder}")
                encryption_success = self.encrypt_output(
                    output_folder, encryption_key_id
                )
                if not encryption_success:
                    self.logger.warning(
                        f"Encryption of output files in {output_folder} was not fully successful"
                    )

            return True

        except Exception as e:
            self.logger.error(f"Encoding error for {input_file.name}: {str(e)}")
            return False
        finally:
            # Clean up temporary directory
            if temp_dir is not None:
                try:
                    # Mark as not in use so it can be cleaned up
                    mark_temp_file_in_use(temp_dir, False)
                    cleanup_temp_file(temp_dir)
                    self.logger.debug(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as e:
                    self.logger.warning(
                        f"Failed to clean up temporary directory {temp_dir}: {str(e)}"
                    )

    def encrypt_output(self, output_folder, key_id=None):
        """
        Encrypt all output files in the specified folder.

        Args:
            output_folder: Path to the folder containing files to encrypt
            key_id: Encryption key ID to use (uses default key if not provided)

        Returns:
            bool: True if encryption was successful, False otherwise
        """
        try:
            output_folder = Path(output_folder)
            if not output_folder.exists() or not output_folder.is_dir():
                self.logger.error(f"Output folder does not exist: {output_folder}")
                return False

            # Get all files in the output folder and subfolders
            all_files = []
            for root, _, files in os.walk(output_folder):
                for file in files:
                    if file.endswith(".m3u8") or file.endswith(".ts"):
                        all_files.append(Path(root) / file)

            if not all_files:
                self.logger.warning(f"No files found to encrypt in {output_folder}")
                return True  # Not an error, just nothing to do

            # Create encryption metadata file
            metadata_file = output_folder / "encryption.json"
            encryption_metadata = {"encrypted": True, "files": {}}

            # Encrypt each file
            success_count = 0
            for file_path in all_files:
                # Encrypt the file
                success, encrypted_path, file_metadata = (
                    self.encryption_manager.encrypt_file(
                        input_path=file_path,
                        output_path=file_path.with_suffix(file_path.suffix + ".enc"),
                        key_id=key_id,
                    )
                )

                if success:
                    # Store metadata
                    rel_path = str(file_path.relative_to(output_folder))
                    encryption_metadata["files"][rel_path] = {
                        "encrypted_path": str(
                            encrypted_path.relative_to(output_folder)
                        ),
                        "metadata": file_metadata,
                    }

                    # Remove original file
                    os.remove(file_path)
                    success_count += 1
                else:
                    self.logger.error(f"Failed to encrypt file: {file_path}")

            # Write encryption metadata file
            with open(metadata_file, "w") as f:
                json.dump(encryption_metadata, f, indent=2)

            self.logger.info(
                f"Encrypted {success_count} of {len(all_files)} files in {output_folder}"
            )
            return success_count == len(all_files)

        except Exception as e:
            self.logger.error(f"Error encrypting output files: {str(e)}")
            return False

    def decrypt_input(self, input_folder):
        """
        Decrypt all encrypted files in the specified folder.

        Args:
            input_folder: Path to the folder containing encrypted files

        Returns:
            bool: True if decryption was successful, False otherwise
        """
        try:
            input_folder = Path(input_folder)
            if not input_folder.exists() or not input_folder.is_dir():
                self.logger.error(f"Input folder does not exist: {input_folder}")
                return False

            # Check for encryption metadata file
            metadata_file = input_folder / "encryption.json"
            if not metadata_file.exists():
                # Not encrypted, nothing to do
                return True

            # Read encryption metadata
            with open(metadata_file, "r") as f:
                encryption_metadata = json.load(f)

            if not encryption_metadata.get("encrypted", False):
                # Not encrypted, nothing to do
                return True

            # Decrypt each file
            files_metadata = encryption_metadata.get("files", {})
            success_count = 0
            total_files = len(files_metadata)

            for rel_path, file_metadata in files_metadata.items():
                # Get encrypted file path
                encrypted_rel_path = file_metadata["encrypted_path"]
                encrypted_path = input_folder / encrypted_rel_path
                original_path = input_folder / rel_path

                # Decrypt the file
                success, _ = self.encryption_manager.decrypt_file(
                    input_path=encrypted_path,
                    output_path=original_path,
                    metadata=file_metadata["metadata"],
                )

                if success:
                    # Remove encrypted file
                    os.remove(encrypted_path)
                    success_count += 1
                else:
                    self.logger.error(f"Failed to decrypt file: {encrypted_path}")

            # Remove encryption metadata file if all files were decrypted
            if success_count == total_files:
                os.remove(metadata_file)

            self.logger.info(
                f"Decrypted {success_count} of {total_files} files in {input_folder}"
            )
            return success_count == total_files

        except Exception as e:
            self.logger.error(f"Error decrypting input files: {str(e)}")
            return False

    def terminate(self):
        """Terminate any active FFmpeg process"""
        return self.ffmpeg.terminate()
