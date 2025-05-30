import re
import subprocess
import sys
import time

# Multiprocessing queue for progress updates
from multiprocessing import Manager
from pathlib import Path
from threading import Lock

# Import tqdm for CLI progress bars
from tqdm import tqdm

from pyprocessor.utils.media.ffmpeg_manager import get_ffmpeg_path, get_ffprobe_path
from pyprocessor.utils.process.scheduler_manager import (
    get_scheduler_manager,
    schedule_task,
    wait_for_task,
)

# Global queues that will be shared between processes
progress_queue = None
output_files_queue = None


# Standalone function for multiprocessing that doesn't require encoder or logger
def process_video_task(
    file_path,
    output_folder_path,
    ffmpeg_params,
    task_id=None,
    progress_callback=None,
    output_file_callback=None,
    encrypt_output=False,
    encryption_key_id=None,
):
    """Process a single video file - standalone function for multiprocessing or batch processing

    Args:
        file_path: Path to the video file
        output_folder_path: Path to the output folder
        ffmpeg_params: FFmpeg parameters
        task_id: Task ID for progress tracking
        progress_callback: Optional direct callback for progress updates (used in batch mode)
        output_file_callback: Optional direct callback for output file notifications (used in batch mode)

    Returns:
        Tuple of (filename, success, duration, error_message)
    """
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
            bufsize_value = int(bitrate.rstrip("k")) * 2
            bufsizes[res] = f"{bufsize_value}k"

        # Build filter complex string
        filter_complex = "[0:v]split=4[v1][v2][v3][v4];[v1]scale=1920:1080[v1out];[v2]scale=1280:720[v2out];[v3]scale=854:480[v3out];[v4]scale=640:360[v4out]"

        # Build FFmpeg command
        ffmpeg_path = get_ffmpeg_path()
        cmd = [
            ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "info",
            "-stats",
            "-i",
            str(file),
            "-filter_complex",
            filter_complex,
        ]

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
                    ffmpeg_params["video_encoder"],
                ]
            )

            # Add preset and tune if applicable
            if ffmpeg_params["preset"]:
                cmd.extend([f"-preset:v:{i}", ffmpeg_params["preset"]])
            if ffmpeg_params["tune"]:
                cmd.extend([f"-tune:v:{i}", ffmpeg_params["tune"]])

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
        audio_bitrates = ffmpeg_params["audio_bitrates"]
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

        # HLS parameters
        segment_path = str(output_subfolder) + "/%v/segment_%03d.ts"
        playlist_path = str(output_subfolder) + "/%v/playlist.m3u8"

        cmd.extend(
            [
                "-f",
                "hls",
                "-g",
                str(ffmpeg_params["fps"]),
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

        # Execute FFmpeg
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            universal_newlines=True,
            bufsize=1,  # Line buffered
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
            if time_match and duration_seconds > 0:
                h, m, s, ms = map(int, time_match.groups())
                current_seconds = h * 3600 + m * 60 + s + ms / 100
                progress = min(int((current_seconds / duration_seconds) * 100), 100)

                # Report progress either through queue or direct callback
                if task_id is not None:
                    # Put progress update in the queue if available
                    if progress_queue is not None:
                        progress_queue.put((task_id, file.name, progress))

                    # Use direct callback if provided (batch mode)
                    if progress_callback is not None:
                        progress_callback(file.name, progress, task_id, None)

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
            return (
                file.name,
                False,
                time.time() - start_time,
                "Failed to create master playlist",
            )

        # Log created files
        global output_files_queue

        # Function to report output files (either through queue or direct callback)
        def report_output_file(filename, resolution=None):
            if output_files_queue is not None and task_id is not None:
                output_files_queue.put((task_id, filename, resolution))
            if output_file_callback is not None:
                output_file_callback(filename, resolution)

        # Log master playlist
        report_output_file("master.m3u8", None)

        # Log variant playlists and segments
        resolutions = ["1080p", "720p", "480p", "360p"]
        for res in resolutions:
            variant_dir = output_subfolder / res
            if variant_dir.exists():
                # Log playlist
                playlist_file = f"{res}/playlist.m3u8"
                report_output_file(playlist_file, res)

                # Log a few segments (not all to avoid cluttering)
                segments = list(variant_dir.glob("segment_*.ts"))
                for i, segment in enumerate(segments[:3]):  # Log first 3 segments
                    segment_file = f"{res}/{segment.name}"
                    report_output_file(segment_file, res)

                # If there are more segments, log a summary
                if len(segments) > 3:
                    report_output_file(f"... and {len(segments)-3} more segments", res)

        # Ensure we report 100% at the end
        if task_id is not None:
            # Report through queue if available
            if progress_queue is not None:
                progress_queue.put((task_id, file.name, 100))

            # Use direct callback if provided (batch mode)
            if progress_callback is not None:
                progress_callback(file.name, 100, task_id, None)

        # Encrypt output if requested
        if encrypt_output:
            # Import here to avoid circular imports
            from pyprocessor.utils.security.encryption_manager import (
                get_encryption_manager,
            )

            # Get encryption manager
            encryption_manager = get_encryption_manager()

            # Encrypt output files
            # Use print for standalone process mode (no logger available)
            print(f"Encrypting output files in {output_subfolder}")
            encryption_success = encryption_manager.encrypt_output(
                output_subfolder, encryption_key_id
            )
            if not encryption_success:
                print(
                    f"Warning: Encryption of output files in {output_subfolder} was not fully successful"
                )

        return (file.name, True, time.time() - start_time, None)

    except Exception as e:
        return (file.name, False, time.time() - start_time, str(e))


# Helper function to check for audio streams
def check_for_audio(file_path):
    """Check if the video file has audio streams"""
    try:
        ffprobe_path = get_ffprobe_path()
        result = subprocess.run(
            [
                ffprobe_path,
                "-i",
                str(file_path),
                "-show_streams",
                "-select_streams",
                "a",
                "-loglevel",
                "error",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
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
            self.logger.warning(
                f"Invalid progress callback: {callback} is not callable"
            )

    def set_output_file_callback(self, callback):
        """Set a callback function for output file notifications"""
        if callable(callback):
            self.output_file_callback = callback
        else:
            self.logger.warning(
                f"Invalid output file callback: {callback} is not callable"
            )

    def _monitor_progress_queue(self):
        """Monitor the progress queue for file-level progress updates"""
        global progress_queue

        # Keep track of the current progress for each task
        file_progress = {}
        last_progress = {}

        while self.is_running and progress_queue is not None:
            try:
                # Non-blocking get with timeout
                try:
                    task_id, filename, progress = progress_queue.get(timeout=0.1)

                    # Store the progress for this task
                    file_progress[task_id] = (filename, progress)

                    # Update CLI progress bar if progress has changed
                    if (
                        task_id not in last_progress
                        or last_progress[task_id] != progress
                    ):
                        if (
                            hasattr(self, "progress_bars")
                            and "file" in self.progress_bars
                        ):
                            # Update the file progress bar
                            self.progress_bars["file"].set_description(
                                f"Processing: {filename}"
                            )
                            self.progress_bars["file"].n = progress
                            self.progress_bars["file"].refresh()
                        last_progress[task_id] = progress

                    # Call the progress callback with file-level progress
                    if self.progress_callback:
                        self.progress_callback(
                            filename, progress, self.processed_count, self.total_files
                        )

                except Exception:
                    # Queue.Empty or other exception, just continue
                    pass

            except Exception as e:
                # Log any other errors but keep the thread running
                if hasattr(self, "logger"):
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
                if hasattr(self, "logger"):
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

    def process_videos(self, encrypt_output=None, encryption_key_id=None):
        """Process all video files in parallel with CLI progress reporting

        Args:
            encrypt_output: Whether to encrypt output files (overrides config setting)
            encryption_key_id: Encryption key ID to use (overrides config setting)
        """
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

            # Create overall progress bar
            overall_progress = tqdm(
                total=len(valid_files),
                desc="Overall Progress",
                unit="file",
                position=0,
                leave=True,
                file=sys.stdout,
            )

            # Create file progress bar
            file_progress_bar = tqdm(
                total=100,
                desc="Current File",
                unit="%",
                position=1,
                leave=True,
                file=sys.stdout,
            )

            # Store the progress bars for updating
            self.progress_bars = {
                "overall": overall_progress,
                "file": file_progress_bar,
            }

            # Record start time
            processing_start = time.time()

            # Get encryption settings from config if not provided
            if encrypt_output is None:
                encrypt_output = self.config.get(
                    "security.encryption.encrypt_output", False
                )

            if encryption_key_id is None:
                encryption_key_id = self.config.get("security.encryption.key_id", None)

            # Log encryption settings
            if encrypt_output:
                self.logger.info(f"Output encryption is enabled")
                if encryption_key_id:
                    self.logger.info(f"Using encryption key: {encryption_key_id}")
                else:
                    self.logger.info("Using default encryption key")

            # Check if batch processing is enabled
            batch_enabled = self.config.get("batch_processing.enabled", True)

            if batch_enabled:
                # Use batch processing
                self.logger.info("Using batch processing mode")
                return self._process_videos_batch(
                    valid_files, processing_start, encrypt_output, encryption_key_id
                )
            else:
                # Use individual process mode
                self.logger.info("Using individual process mode")
                return self._process_videos_individual(
                    valid_files, processing_start, encrypt_output, encryption_key_id
                )

        except Exception as e:
            self.logger.error(f"Error in process_videos: {str(e)}")
            self.is_running = False
            return False

        finally:
            self.is_running = False

    def _process_videos_batch(
        self,
        valid_files,
        processing_start,
        encrypt_output=False,
        encryption_key_id=None,
    ):
        """Process videos using batch processing"""
        try:
            # Import batch processor here to avoid circular imports
            from pyprocessor.processing.batch_processor import (
                BatchProcessor,
                create_batches,
            )

            # Create a manager for sharing queues between processes
            global progress_queue, output_files_queue
            manager = Manager()
            progress_queue = manager.Queue()
            output_files_queue = manager.Queue()

            # Create threads to monitor the queues
            import threading

            # Thread for progress updates
            progress_thread = threading.Thread(
                target=self._monitor_progress_queue, daemon=True
            )
            progress_thread.start()

            # Thread for output file notifications
            output_files_thread = threading.Thread(
                target=self._monitor_output_files_queue, daemon=True
            )
            output_files_thread.start()

            # Create batch processor
            batch_processor = BatchProcessor(self.config, self.logger)

            # Get batch size if specified, otherwise use dynamic sizing
            batch_size = self.config.get("batch_processing.batch_size", None)

            # Create batches with dynamic sizing if batch_size is None
            batches = create_batches(valid_files, batch_size, self.config, self.logger)

            # Log batch information
            if batch_size is None:
                self.logger.info(f"Created {len(batches)} batches with dynamic sizing")
            else:
                self.logger.info(
                    f"Created {len(batches)} batches of up to {batch_size} files each"
                )

            # Process each batch
            successful_count = 0
            failed_count = 0

            for i, batch in enumerate(batches):
                if self.abort_requested:
                    self.logger.warning("Processing aborted by user")
                    self.is_running = False
                    return False

                self.logger.info(
                    f"Processing batch {i+1}/{len(batches)} with {len(batch)} files"
                )

                # Process the batch
                results = batch_processor.process_batch(
                    batch,
                    self.config.output_folder,
                    self.config.ffmpeg_params,
                    self.progress_callback,
                    self.output_file_callback,
                    encrypt_output=encrypt_output,
                    encryption_key_id=encryption_key_id,
                )

                # Process results
                for filename, success, duration, error_msg in results:
                    # Update progress counter
                    with self.lock:
                        self.processed_count += 1
                        current = self.processed_count

                    # Update overall progress bar
                    if (
                        hasattr(self, "progress_bars")
                        and "overall" in self.progress_bars
                    ):
                        self.progress_bars["overall"].update(1)
                        self.progress_bars["file"].reset()
                        self.progress_bars["file"].set_description(
                            f"Completed: {filename}"
                        )

                    if success:
                        successful_count += 1
                        self.logger.info(
                            f"Completed processing: {filename} ({duration:.2f}s)"
                        )
                    else:
                        failed_count += 1
                        if error_msg:
                            self.logger.error(
                                f"Error processing {filename}: {error_msg}"
                            )
                        else:
                            self.logger.error(f"Failed to process: {filename}")

            # Clean up the queues
            progress_queue = None
            output_files_queue = None

            # Close progress bars
            if hasattr(self, "progress_bars"):
                for bar in self.progress_bars.values():
                    bar.close()
                del self.progress_bars

            # Calculate statistics
            processing_duration = time.time() - processing_start
            processing_minutes = processing_duration / 60

            self.logger.info(
                f"Processing completed: {successful_count} successful, {failed_count} failed"
            )
            self.logger.info(f"Total processing time: {processing_minutes:.2f} minutes")

            self.is_running = False
            return failed_count == 0

        except Exception as e:
            self.logger.error(f"Error in batch processing: {str(e)}")
            self.is_running = False
            return False

    def _process_videos_individual(
        self,
        valid_files,
        processing_start,
        encrypt_output=False,
        encryption_key_id=None,
    ):
        """Process videos using individual processes for each file"""
        try:
            # Create a manager for sharing queues between processes
            global progress_queue, output_files_queue
            manager = Manager()
            progress_queue = manager.Queue()
            output_files_queue = manager.Queue()

            # Create threads to monitor the queues
            import threading

            # Thread for progress updates
            progress_thread = threading.Thread(
                target=self._monitor_progress_queue, daemon=True
            )
            progress_thread.start()

            # Thread for output file notifications
            output_files_thread = threading.Thread(
                target=self._monitor_output_files_queue, daemon=True
            )
            output_files_thread.start()

            # Get the scheduler manager
            scheduler = get_scheduler_manager()

            # Define task callback function
            def task_callback(task_id, success, result):
                if not success:
                    self.logger.error(f"Task {task_id} failed: {result}")
                    return

                filename, success, duration, error_msg = result

                # Update progress counter
                with self.lock:
                    self.processed_count += 1
                    current = self.processed_count

                # Call progress callback if set - this is for overall progress
                # File-level progress is handled by the progress_queue thread
                if self.progress_callback:
                    self.progress_callback(filename, 100, current, self.total_files)

                # Update overall progress bar
                if hasattr(self, "progress_bars") and "overall" in self.progress_bars:
                    self.progress_bars["overall"].update(1)
                    self.progress_bars["file"].reset()
                    self.progress_bars["file"].set_description(f"Completed: {filename}")

                if success:
                    self.logger.info(
                        f"Completed processing: {filename} ({duration:.2f}s)"
                    )
                else:
                    if error_msg:
                        self.logger.error(f"Error processing {filename}: {error_msg}")
                    else:
                        self.logger.error(f"Failed to process: {filename}")

            # Schedule tasks for all files
            task_ids = []
            for i, file in enumerate(valid_files):
                # Schedule the task
                task_id = schedule_task(
                    process_video_task,
                    str(file),  # Convert Path to string for pickling
                    str(self.config.output_folder),
                    self.config.ffmpeg_params,
                    i,  # Task ID for progress tracking
                    callback=task_callback,
                    priority=i,  # Lower index = higher priority
                    encrypt_output=encrypt_output,
                    encryption_key_id=encryption_key_id,
                )
                task_ids.append(task_id)

            # Wait for all tasks to complete or abort
            successful_count = 0
            failed_count = 0

            for task_id in task_ids:
                # Check for abort
                if self.abort_requested:
                    # Cancel remaining tasks
                    for tid in task_ids:
                        scheduler.cancel_task(tid)
                    self.logger.warning("Processing aborted by user")
                    self.is_running = False
                    return False

                # Wait for the task to complete
                result = wait_for_task(task_id)

                if result is not None:
                    filename, success, duration, error_msg = result
                    if success:
                        successful_count += 1
                    else:
                        failed_count += 1

            # Clean up the queues
            progress_queue = None
            output_files_queue = None

            # Close progress bars
            if hasattr(self, "progress_bars"):
                for bar in self.progress_bars.values():
                    bar.close()
                del self.progress_bars

            # Calculate statistics
            processing_duration = time.time() - processing_start
            processing_minutes = processing_duration / 60

            self.logger.info(
                f"Processing completed: {successful_count} successful, {failed_count} failed"
            )
            self.logger.info(f"Total processing time: {processing_minutes:.2f} minutes")

            self.is_running = False
            return failed_count == 0

        except Exception as e:
            self.logger.error(f"Error in individual processing: {str(e)}")
            self.is_running = False
            return False
