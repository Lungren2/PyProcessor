import time
import os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from threading import Lock

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
    
    def process_video(self, file):
        """Process a single video file"""
        # Check for abort
        if self.abort_requested:
            return False
            
        base_name = file.stem
        output_subfolder = self.config.output_folder / base_name
        
        start_time = time.time()
        self.logger.info(f"Starting processing: {base_name}")
        
        try:
            # Encode the video
            result = self.encoder.encode_video(file, output_subfolder)
            
            duration = time.time() - start_time
            if result:
                self.logger.info(f"Completed processing: {base_name} ({duration:.2f}s)")
            else:
                self.logger.error(f"Failed to process: {base_name}")
            
            # Update progress counter
            with self.lock:
                self.processed_count += 1
                current = self.processed_count
            
            # Call progress callback if set
            if self.progress_callback:
                self.progress_callback(file.name, current, self.total_files)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing {base_name}: {str(e)}")
            
            # Still update progress counter
            with self.lock:
                self.processed_count += 1
                current = self.processed_count
            
            # Call progress callback if set
            if self.progress_callback:
                self.progress_callback(file.name, current, self.total_files)
            
            return False
    
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
            
            # Process files in parallel using ProcessPoolExecutor
            with ProcessPoolExecutor(max_workers=self.config.max_parallel_jobs) as executor:
                # Submit all tasks
                futures = []
                for file in valid_files:
                    future = executor.submit(self.process_video, file)
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
                        result = future.result()
                        if result:
                            successful_count += 1
                        else:
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
