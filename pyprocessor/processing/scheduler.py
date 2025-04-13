import time
import subprocess
from concurrent.futures import ProcessPoolExecutor
from threading import Lock
from pathlib import Path

# Multiprocessing queue for progress updates
from multiprocessing import Manager
import re

from pyprocessor.utils.ffmpeg_locator import get_ffmpeg_path, get_ffprobe_path

# Global queues that will be shared between processes
progress_queue = None
output_files_queue = None

# Standalone function for multiprocessing that doesn't require encoder or logger
def process_video_task(file_path, output_folder_path, ffmpeg_params, task_id=None):
    """Process a single video file - standalone function for multiprocessing"""
    # Convert string paths to Path objects
    file = Path(file_path)
    output_folder = Path(output_folder_path)

    base_name = file.stem
    output_subfolder = output_folder / base_name

    # Create output directory structure
    output_subfolder.mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    global progress_queue

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
        ffmpeg_path = get_ffmpeg_path()
        cmd = [ffmpeg_path, "-hide_banner", "-loglevel", "info", "-stats",
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
            universal_newlines=True,
            bufsize=1  # Line buffered
        )

        # Process stderr in real-time to extract progress
        duration_regex = re.compile(r"Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})")
        time_regex = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
        duration_seconds = 0

        # Read and process stderr line by line
        for line in process.stderr:
            # Extract total duration
            duration_match = duration_regex.search(line)
            if duration_match:
                h, m, s, ms = map(int, duration_match.groups())
                duration_seconds = h * 3600 + m * 60 + s + ms / 100
                continue

            # Extract current time
            time_match = time_regex.search(line)
            if time_match and duration_seconds > 0 and progress_queue is not None:
                h, m, s, ms = map(int, time_match.groups())
                current_seconds = h * 3600 + m * 60 + s + ms / 100
                progress = min(int((current_seconds / duration_seconds) * 100), 100)
                # Put progress update in the queue
                if task_id is not None:
                    progress_queue.put((task_id, file.name, progress))

        # Wait for process to complete
        process.wait()

        # Check for errors
        if process.returncode != 0:
            error_message = ""
            for line in process.stderr:
                error_message += line
            return (file.name, False, time.time() - start_time, error_message.strip())

        # Check if output files were created
        m3u8_file = output_subfolder / "master.m3u8"
        if not m3u8_file.exists():
            return (file.name, False, time.time() - start_time, "Failed to create master playlist")

        # Log created files
        global output_files_queue
        if output_files_queue is not None and task_id is not None:
            # Log master playlist
            output_files_queue.put((task_id, "master.m3u8", None))

            # Log variant playlists and segments
            resolutions = ["1080p", "720p", "480p", "360p"]
            for res in resolutions:
                variant_dir = output_subfolder / res
                if variant_dir.exists():
                    # Log playlist
                    playlist_file = f"{res}/playlist.m3u8"
                    output_files_queue.put((task_id, playlist_file, res))

                    # Log a few segments (not all to avoid cluttering)
                    segments = list(variant_dir.glob("segment_*.ts"))
                    for i, segment in enumerate(segments[:3]):  # Log first 3 segments
                        segment_file = f"{res}/{segment.name}"
                        output_files_queue.put((task_id, segment_file, res))

                    # If there are more segments, log a summary
                    if len(segments) > 3:
                        output_files_queue.put((task_id, f"... and {len(segments)-3} more segments", res))

        # Ensure we report 100% at the end
        if progress_queue is not None and task_id is not None:
            progress_queue.put((task_id, file.name, 100))

        return (file.name, True, time.time() - start_time, None)

    except Exception as e:
        return (file.name, False, time.time() - start_time, str(e))

# Helper function to check for audio streams
def check_for_audio(file_path):
    """Check if the video file has audio streams"""
    try:
        ffprobe_path = get_ffprobe_path()
        result = subprocess.run(
            [ffprobe_path, "-i", str(file_path), "-show_streams",
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
        self.output_file_callback = None
        self.is_running = False
        self.abort_requested = False

    def set_progress_callback(self, callback):
        """Set a callback function for progress updates"""
        if callable(callback):
            self.progress_callback = callback
        else:
            self.logger.warning(f"Invalid progress callback: {callback} is not callable")

    def set_output_file_callback(self, callback):
        """Set a callback function for output file notifications"""
        if callable(callback):
            self.output_file_callback = callback
        else:
            self.logger.warning(f"Invalid output file callback: {callback} is not callable")

    def _monitor_progress_queue(self):
        """Monitor the progress queue for file-level progress updates"""
        global progress_queue

        # Keep track of the current progress for each task
        file_progress = {}

        while self.is_running and progress_queue is not None:
            try:
                # Non-blocking get with timeout
                try:
                    task_id, filename, progress = progress_queue.get(timeout=0.1)

                    # Store the progress for this task
                    file_progress[task_id] = (filename, progress)

                    # Call the progress callback with file-level progress
                    if self.progress_callback:
                        self.progress_callback(filename, progress, self.processed_count, self.total_files)

                except Exception:
                    # Queue.Empty or other exception, just continue
                    pass

            except Exception as e:
                # Log any other errors but keep the thread running
                if hasattr(self, 'logger'):
                    self.logger.error(f"Error in progress monitor: {str(e)}")

            # Small sleep to prevent CPU spinning
            import time
            time.sleep(0.01)

    def _monitor_output_files_queue(self):
        """Monitor the output files queue for file creation notifications"""
        global output_files_queue

        while self.is_running and output_files_queue is not None:
            try:
                # Non-blocking get with timeout
                try:
                    task_id, filename, resolution = output_files_queue.get(timeout=0.1)

                    # Call the output file callback
                    if self.output_file_callback:
                        self.output_file_callback(filename, resolution)

                except Exception:
                    # Queue.Empty or other exception, just continue
                    pass

            except Exception as e:
                # Log any other errors but keep the thread running
                if hasattr(self, 'logger'):
                    self.logger.error(f"Error in output files monitor: {str(e)}")

            # Small sleep to prevent CPU spinning
            import time
            time.sleep(0.01)

    def get_progress(self):
        """Get the current progress as a ratio (0.0 to 1.0)"""
        if self.total_files == 0:
            return 0.0
        return self.processed_count / self.total_files

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

            # Create a manager for sharing queues between processes
            global progress_queue, output_files_queue
            manager = Manager()
            progress_queue = manager.Queue()
            output_files_queue = manager.Queue()

            # Create threads to monitor the queues
            import threading

            # Thread for progress updates
            progress_thread = threading.Thread(
                target=self._monitor_progress_queue,
                daemon=True
            )
            progress_thread.start()

            # Thread for output file notifications
            output_files_thread = threading.Thread(
                target=self._monitor_output_files_queue,
                daemon=True
            )
            output_files_thread.start()

            # Process files in parallel using ProcessPoolExecutor
            with ProcessPoolExecutor(max_workers=self.config.max_parallel_jobs) as executor:
                # Submit all tasks
                futures = []
                for i, file in enumerate(valid_files):
                    # Pass serializable parameters to the worker function
                    future = executor.submit(
                        process_video_task,
                        str(file),  # Convert Path to string for pickling
                        str(self.config.output_folder),
                        self.config.ffmpeg_params,
                        i  # Task ID for progress tracking
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
                        self.is_running = False
                        return False

                    try:
                        filename, success, duration, error_msg = future.result()

                        # Update progress counter
                        with self.lock:
                            self.processed_count += 1
                            current = self.processed_count

                        # Call progress callback if set - this is for overall progress
                        # File-level progress is handled by the progress_queue thread
                        if self.progress_callback:
                            self.progress_callback(filename, 100, current, self.total_files)

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

            # Clean up the queues
            # global progress_queue, output_files_queue
            progress_queue = None
            output_files_queue = None

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
