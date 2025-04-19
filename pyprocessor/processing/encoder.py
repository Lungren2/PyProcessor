from pathlib import Path

# Import the FFmpegManager
from pyprocessor.utils.media.ffmpeg_manager import FFmpegManager


class FFmpegEncoder:
    """FFmpeg encoder with advanced options including audio control"""

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.ffmpeg = FFmpegManager(logger)
        self.encoding_progress = 0

    def check_ffmpeg(self):
        """Check if FFmpeg is installed and available"""
        return self.ffmpeg.check_ffmpeg()

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

    def encode_video(self, input_file, output_folder, progress_callback=None):
        """Encode a video file to HLS format with progress updates"""
        try:
            # Create output directory structure
            output_folder = Path(output_folder)
            output_folder.mkdir(parents=True, exist_ok=True)

            # Build command
            cmd = self.build_command(input_file, output_folder)

            # Execute FFmpeg command using the FFmpegManager
            success = self.ffmpeg.execute_command(
                cmd,
                input_file=input_file.name,
                output_folder=output_folder,
                progress_callback=progress_callback
            )

            if not success:
                return False

            # Check if output files were created
            m3u8_file = output_folder / "master.m3u8"
            if not m3u8_file.exists():
                self.logger.error(
                    f"Failed to create master playlist for {input_file.name}"
                )
                return False

            self.logger.info(f"Successfully encoded {input_file.name}")
            return True

        except Exception as e:
            self.logger.error(f"Encoding error for {input_file.name}: {str(e)}")
            return False

    def terminate(self):
        """Terminate any active FFmpeg process"""
        return self.ffmpeg.terminate()
