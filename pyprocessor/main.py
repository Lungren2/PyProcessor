import argparse
import sys

from pyprocessor.utils.core.application_context import ApplicationContext

# Signal handling is now managed by ApplicationContext


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Video Processor")

    # File paths
    parser.add_argument("--input", help="Input directory path")
    parser.add_argument("--output", help="Output directory path")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--profile", help="Configuration profile name")

    # Processing options
    parser.add_argument(
        "--encoder",
        choices=["libx265", "h264_nvenc", "libx264"],
        help="Video encoder to use",
    )
    parser.add_argument(
        "--preset", choices=["ultrafast", "veryfast", "medium"], help="Encoding preset"
    )
    parser.add_argument(
        "--tune",
        choices=["zerolatency", "film", "animation"],
        help="Encoding tune parameter",
    )
    parser.add_argument(
        "--fps", type=int, choices=[30, 60, 120], help="Frames per second"
    )
    parser.add_argument(
        "--no-audio", action="store_true", help="Exclude audio from output"
    )
    parser.add_argument("--jobs", type=int, help="Number of parallel jobs")

    # Batch processing options
    batch_group = parser.add_argument_group("Batch Processing")
    batch_group.add_argument(
        "--batch-mode",
        choices=["enabled", "disabled"],
        help="Enable or disable batch processing mode"
    )
    batch_group.add_argument(
        "--batch-size",
        type=int,
        help="Number of videos to process in a single batch"
    )
    batch_group.add_argument(
        "--max-memory",
        type=int,
        help="Maximum memory usage percentage before throttling batches"
    )

    # Execution options
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    # Server optimization options
    server_group = parser.add_argument_group("Server Optimization")
    server_group.add_argument(
        "--optimize-server",
        choices=["iis", "nginx", "apache", "linux"],
        help="Optimize server for video streaming",
    )
    server_group.add_argument(
        "--site-name",
        default="Default Web Site",
        help="IIS site name (for --optimize-server=iis)",
    )
    server_group.add_argument(
        "--video-path",
        help="Path to video content directory (for --optimize-server=iis)",
    )
    server_group.add_argument(
        "--enable-http2",
        action="store_true",
        default=True,
        help="Enable HTTP/2 protocol (for --optimize-server=iis)",
    )
    server_group.add_argument(
        "--enable-http3",
        action="store_true",
        default=False,
        help="Enable HTTP/3 with Alt-Svc headers for auto-upgrading (for --optimize-server=iis or nginx)",
    )
    server_group.add_argument(
        "--enable-cors",
        action="store_true",
        default=True,
        help="Enable CORS headers (for --optimize-server=iis)",
    )
    server_group.add_argument(
        "--cors-origin",
        default="*",
        help="CORS origin value (for --optimize-server=iis)",
    )
    server_group.add_argument(
        "--output-config",
        help="Output path for server configuration (for --optimize-server=nginx)",
    )
    server_group.add_argument(
        "--server-name",
        default="yourdomain.com",
        help="Server name for configuration (for --optimize-server=nginx)",
    )
    server_group.add_argument(
        "--apply-changes",
        action="store_true",
        help="Apply changes directly (for --optimize-server=linux)",
    )

    # Security options
    security_group = parser.add_argument_group("Security Options")
    security_group.add_argument(
        "--enable-encryption",
        action="store_true",
        help="Enable content encryption",
    )
    security_group.add_argument(
        "--encrypt-output",
        action="store_true",
        help="Encrypt output files",
    )
    security_group.add_argument(
        "--encryption-key",
        help="Encryption key ID to use (uses default key if not specified)",
    )

    return parser.parse_args()


# Command line argument processing is now handled by ApplicationContext._apply_args_to_config


# CLI mode processing is now handled by ApplicationContext.run_cli_mode


def main():
    """Main application entry point"""
    # Parse command line arguments
    args = parse_args()

    # Create and initialize application context
    app_context = ApplicationContext()
    if not app_context.initialize(args):
        return 1

    # Run in CLI mode
    return app_context.run_cli_mode()


if __name__ == "__main__":
    sys.exit(main())
