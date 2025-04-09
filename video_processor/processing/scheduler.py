import time
import subprocess
from concurrent.futures import ProcessPoolExecutor
from threading import Lock
from pathlib import Path

# Standalone function for multiprocessing that doesn't require encoder or logger
def process_video_task(file_path, output_folder_path, ffmpeg_params):
    """Process a single video file - standalone function for multiprocessing"""
    # Convert string paths to Path objects
    file = Path(file_path)
    output_folder = Path(output_folder_path)

    base_name = file.stem
    output_subfolder = output_folder / base_name

    # Create output directory structure
    output_subfolder.mkdir(parents=True, exist_ok=True)

    # Create directories for different resolutions
    for res in ["1080p", "720p", "480p", "360p"]:
        (output_subfolder / res).mkdir(parents=True, exist_ok=True)

    start_time = time.time()

    try:
        # Build FFmpeg command directly here
        # Check for audio streams
        has_audio = check_for_audio(file)
        if not ffmpeg_params.get("include_audio", True):
            has_audio = False

        # Calculate buffer sizes
        bitrates = ffmpeg_params["bitrates"]
        bufsizes = {}
        for res, bitrate in bitrates.items():
            bufsize_value = int(bitrate.rstrip('k')) * 2
            bufsizes[res] = f"{bufsize_value}k"

        # Build filter complex string
        filter_complex = "[0:v]split=4[v1][v2][v3][v4];[v1]scale=1920:1080[v1out];[v2]scale=1280:720[v2out];[v3]scale=854:480[v3out];[v4]scale=640:360[v4out]"

        # Build FFmpeg command
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "info", "-stats",
               "-i", str(file), "-filter_complex", filter_complex]

        # Video streams for all resolutions
        for i, (res, bitrate) in enumerate([("1080p", bitrates["1080p"]),
                                           ("720p", bitrates["720p"]),
                                           ("480p", bitrates["480p"]),
                                           ("360p", bitrates["360p"])]):
            # Map video stream
            cmd.extend(["-map", f"[v{i+1}out]",
                       "-c:v:" + str(i), ffmpeg_params["video_encoder"]])

            # Add preset and tune if applicable
            if ffmpeg_params["preset"]:
                cmd.extend([f"-preset:v:{i}", ffmpeg_params["preset"]])
            if ffmpeg_params["tune"]:
                cmd.extend([f"-tune:v:{i}", ffmpeg_params["tune"]])

            # Bitrate settings
            cmd.extend([f"-b:v:{i}", bitrate,
                       f"-maxrate:v:{i}", bitrate,
                       f"-bufsize:v:{i}", bufsizes[res]])

        # Audio streams if available and enabled
        audio_bitrates = ffmpeg_params["audio_bitrates"]
        if has_audio:
            for i, bitrate in enumerate(audio_bitrates):
                cmd.extend(["-map", "a:0",
                           f"-c:a:{i}", "aac",
                           f"-b:a:{i}", bitrate,
                           "-ac", "2"])
            var_stream_map = "v:0,a:0 v:1,a:1 v:2,a:2 v:3,a:3"
        else:
            var_stream_map = "v:0 v:1 v:2 v:3"

        # HLS parameters
        segment_path = str(output_subfolder) + "/%v/segment_%03d.ts"
        playlist_path = str(output_subfolder) + "/%v/playlist.m3u8"

        cmd.extend(["-f", "hls",
                   "-g", str(ffmpeg_params["fps"]),
                   "-hls_time", "1",
                   "-hls_playlist_type", "vod",
                   "-hls_flags", "independent_segments",
                   "-hls_segment_type", "mpegts",
                   "-hls_segment_filename", segment_path,
                   "-master_pl_name", "master.m3u8",
                   "-var_stream_map", var_stream_map,
                   playlist_path])

        # Execute FFmpeg
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            universal_newlines=True
        )

        # Process stdout and stderr
        _, stderr = process.communicate()

        # Check for errors
        if process.returncode != 0:
            return (file.name, False, time.time() - start_time, stderr.strip())

        # Check if output files were created
        m3u8_file = output_subfolder / "master.m3u8"
        if not m3u8_file.exists():
            return (file.name, False, time.time() - start_time, "Failed to create master playlist")

        return (file.name, True, time.time() - start_time, None)

    except Exception as e:
        return (file.name, False, time.time() - start_time, str(e))

# Helper function to check for audio streams
def check_for_audio(file_path):
    """Check if the video file has audio streams"""
    try:
        result = subprocess.run(
            ["ffprobe", "-i", str(file_path), "-show_streams",
             "-select_streams", "a", "-loglevel", "error"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        return bool(result.stdout.strip())
    except subprocess.SubprocessError:
        return False

class ProcessingScheduler:
    """Enhanced parallel processing scheduler for video encoding"""

    def __init__(self, config, logger, file_manager, encoder):
        self.config = config
        self.logger = logger
        self.file_manager = file_manager
        self.encoder = encoder
        self.lock = Lock()
        self.processed_count = 0
        self.total_files = 0
        self.progress_callback = None
        self.is_running = False
        self.abort_requested = False

    def set_progress_callback(self, callback):
        """Set a callback function for progress updates"""
        self.progress_callback = callback

    def request_abort(self):
        """Request abortion of the processing"""
        if not self.is_running:
            return False

        self.logger.warning("Processing abort requested")
        self.abort_requested = True
        return True

    def process_videos(self):
        """Process all video files in parallel"""
        self.is_running = True
        self.abort_requested = False

        try:
            # Validate files
            valid_files, invalid_files = self.file_manager.validate_files()

            if invalid_files:
                self.logger.warning("The following files have invalid naming format:")
                for file in invalid_files:
                    self.logger.warning(f"  - {file}")

            if not valid_files:
                self.logger.error("No valid files found to process")
                self.is_running = False
                return False

            self.logger.info(f"Found {len(valid_files)} valid files to process")
            self.total_files = len(valid_files)
            self.processed_count = 0

            processing_start = time.time()

            # We'll pass serializable parameters to the worker function
            # No need for partial function anymore

            # Process files in parallel using ProcessPoolExecutor
            with ProcessPoolExecutor(max_workers=self.config.max_parallel_jobs) as executor:
                # Submit all tasks
                futures = []
                for file in valid_files:
                    # Pass serializable parameters to the worker function
                    future = executor.submit(
                        process_video_task,
                        str(file),  # Convert Path to string for pickling
                        str(self.config.output_folder),
                        self.config.ffmpeg_params
                    )
                    futures.append(future)

                # Process results as they complete
                successful_count = 0
                failed_count = 0

                for future in futures:
                    # Check for abort
                    if self.abort_requested:
                        executor.shutdown(wait=False)
                        self.logger.warning("Processing aborted by user")
                        break

                    try:
                        filename, success, duration, error_msg = future.result()

                        # Update progress counter
                        with self.lock:
                            self.processed_count += 1
                            current = self.processed_count

                        # Call progress callback if set
                        if self.progress_callback:
                            self.progress_callback(filename, current, self.total_files)

                        if success:
                            self.logger.info(f"Completed processing: {filename} ({duration:.2f}s)")
                            successful_count += 1
                        else:
                            if error_msg:
                                self.logger.error(f"Error processing {filename}: {error_msg}")
                            else:
                                self.logger.error(f"Failed to process: {filename}")
                            failed_count += 1

                    except Exception as e:
                        self.logger.error(f"Error in processing task: {str(e)}")
                        failed_count += 1

            # Calculate statistics
            processing_duration = time.time() - processing_start
            processing_minutes = processing_duration / 60

            self.logger.info(f"Processing completed: {successful_count} successful, {failed_count} failed")
            self.logger.info(f"Total processing time: {processing_minutes:.2f} minutes")

            self.is_running = False
            return failed_count == 0

        except Exception as e:
            self.logger.error(f"Error in process_videos: {str(e)}")
            self.is_running = False
            return False

        finally:
            self.is_running = False
