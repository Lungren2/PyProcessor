import os
import re
import subprocess
import time
from pathlib import Path

class FFmpegEncoder:
    """FFmpeg encoder with advanced options including audio control"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.process = None
        self.encoding_progress = 0
    
    def check_ffmpeg(self):
        """Check if FFmpeg is installed and available"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            if "ffmpeg version" in result.stdout:
                self.logger.info(f"Found FFmpeg: {result.stdout.split('\\n')[0]}")
                return True
            return False
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            self.logger.error(f"FFmpeg check failed: {str(e)}")
            return False
    
    def has_audio(self, file_path):
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
        except subprocess.SubprocessError as e:
            self.logger.error(f"Error checking audio streams: {str(e)}")
            return False
    
    def build_command(self, input_file, output_folder):
        """Build FFmpeg command for HLS encoding with audio option"""
        # Check for audio streams and respect the include_audio setting
        has_audio = self.has_audio(input_file) and self.config.ffmpeg_params.get("include_audio", True)
        
        # Calculate buffer sizes
        bitrates = self.config.ffmpeg_params["bitrates"]
        bufsizes = {}
        for res, bitrate in bitrates.items():
            bufsize_value = int(bitrate.rstrip('k')) * 2
            bufsizes[res] = f"{bufsize_value}k"
        
        # Build filter complex string
        filter_complex = "[0:v]split=4[v1][v2][v3][v4];[v1]scale=1920:1080[v1out];[v2]scale=1280:720[v2out];[v3]scale=854:480[v3out];[v4]scale=640:360[v4out]"
        
        # Build FFmpeg command
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "info", "-stats", 
               "-i", str(input_file), "-filter_complex", filter_complex]
        
        # Video streams for all resolutions
        for i, (res, bitrate) in enumerate([("1080p", bitrates["1080p"]), 
                                           ("720p", bitrates["720p"]), 
                                           ("480p", bitrates["480p"]), 
                                           ("360p", bitrates["360p"])]):
            # Map video stream
            cmd.extend(["-map", f"[v{i+1}out]", 
                       "-c:v:" + str(i), self.config.ffmpeg_params["video_encoder"]])
            
            # Add preset and tune if applicable
            if self.config.ffmpeg_params["preset"]:
                cmd.extend([f"-preset:v:{i}", self.config.ffmpeg_params["preset"]])
            if self.config.ffmpeg_params["tune"]:
                cmd.extend([f"-tune:v:{i}", self.config.ffmpeg_params["tune"]])
            
            # Bitrate settings
            cmd.extend([f"-b:v:{i}", bitrate, 
                       f"-maxrate:v:{i}", bitrate, 
                       f"-bufsize:v:{i}", bufsizes[res]])
        
        # Audio streams if available and enabled
        audio_bitrates = self.config.ffmpeg_params["audio_bitrates"]
        if has_audio:
            for i, bitrate in enumerate(audio_bitrates):
                cmd.extend(["-map", "a:0", 
                           f"-c:a:{i}", "aac", 
                           f"-b:a:{i}", bitrate, 
                           "-ac", "2"])
            var_stream_map = "v:0,a:0 v:1,a:1 v:2,a:2 v:3,a:3"
        else:
            var_stream_map = "v:0 v:1 v:2 v:3"
            
            # If we're intentionally excluding audio, log it
            if not self.config.ffmpeg_params.get("include_audio", True):
                self.logger.info(f"Audio excluded per user settings for {input_file.name}")
        
        # HLS parameters
        segment_path = str(output_folder) + "/%v/segment_%03d.ts"
        playlist_path = str(output_folder) + "/%v/playlist.m3u8"
        
        cmd.extend(["-f", "hls", 
                   "-g", str(self.config.ffmpeg_params["fps"]), 
                   "-hls_time", "1", 
                   "-hls_playlist_type", "vod", 
                   "-hls_flags", "independent_segments", 
                   "-hls_segment_type", "mpegts", 
                   "-hls_segment_filename", segment_path, 
                   "-master_pl_name", "master.m3u8", 
                   "-var_stream_map", var_stream_map, 
                   playlist_path])
        
        return cmd
    
    def encode_video(self, input_file, output_folder):
        """Encode a video file to HLS format"""
        try:
            # Create output directory structure
            output_folder = Path(output_folder)
            output_folder.mkdir(parents=True, exist_ok=True)
            
            # Create directories for different resolutions
            for res in ["1080p", "720p", "480p", "360p"]:
                (output_folder / res).mkdir(parents=True, exist_ok=True)
            
            # Build command
            cmd = self.build_command(input_file, output_folder)
            self.logger.debug(f"Executing: {' '.join(cmd)}")
            
            # Execute FFmpeg
            self.process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True,
                universal_newlines=True
            )
            
            # Process stdout and stderr
            stdout, stderr = self.process.communicate()
            
            # Check for errors
            if self.process.returncode != 0:
                error_message = stderr.strip()
                self.logger.error(f"FFmpeg error encoding {input_file.name}: {error_message}")
                return False
            
            # Check if output files were created
            m3u8_file = output_folder / "master.m3u8"
            if not m3u8_file.exists():
                self.logger.error(f"Failed to create master playlist for {input_file.name}")
                return False
            
            self.logger.info(f"Successfully encoded {input_file.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Encoding error for {input_file.name}: {str(e)}")
            return False
    
    def terminate(self):
        """Terminate any active FFmpeg process"""
        if self.process and self.process.poll() is None:
            try:
                self.logger.info("Terminating active FFmpeg process")
                self.process.terminate()
                
                # Wait up to 5 seconds for graceful termination
                for _ in range(50):
                    if self.process.poll() is not None:
                        break
                    time.sleep(0.1)
                
                # Force kill if still running
                if self.process.poll() is None:
                    self.logger.warning("FFmpeg process did not terminate gracefully, force killing")
                    self.process.kill()
                    self.process.wait()
                
                return True
            except Exception as e:
                self.logger.error(f"Error terminating FFmpeg process: {str(e)}")
                return False
        return False
