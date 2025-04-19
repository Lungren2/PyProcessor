"""
Cross-platform server optimization utilities for video streaming servers.

This module provides functionality to optimize different types of web servers
for video streaming across Windows, macOS, and Linux platforms, using optimization
scripts from the optimization-utils directory.

Supported server types:
- IIS (Windows only)
- Nginx (All platforms)
- Apache (All platforms)
- Generic Linux optimizations (Linux only)
"""

import subprocess
import platform
import shutil
from pathlib import Path
import tempfile
import shlex

from pyprocessor.utils.file_system.path_manager import (
    normalize_path, ensure_dir_exists, get_base_dir, dir_exists
)

from pyprocessor.utils.logging.log_manager import get_logger


class ServerOptimizer:
    """Cross-platform server optimization utility for video streaming servers.

    This class provides methods to optimize different types of web servers
    for video streaming across Windows, macOS, and Linux platforms.
    """

    def __init__(self, config, logger=None):
        """Initialize the server optimizer.

        Args:
            config: Configuration instance
            logger: Logger instance (optional)
        """
        self.config = config
        self.logger = logger or get_logger()

        # Get system information
        self.system = platform.system().lower()
        self.is_windows = self.system == "windows"
        self.is_macos = self.system == "darwin"
        self.is_linux = self.system == "linux"

        # Get the base directory of the application
        self.base_dir = get_base_dir()
        self.optimization_utils_dir = self.base_dir / "optimization-utils"

        # Check if optimization utils directory exists
        if not self.optimization_utils_dir.exists():
            self.logger.warning(
                f"Optimization utilities directory not found: {self.optimization_utils_dir}"
            )

    def optimize_server(self, server_type, **kwargs):
        """Optimize a server for video streaming based on type and platform.

        This is the main entry point for server optimization. It will call the
        appropriate optimization method based on the server type and platform.

        Args:
            server_type: Type of server to optimize (iis, nginx, apache, linux)
            **kwargs: Additional arguments for the specific optimization method

        Returns:
            tuple: (success, message, script_path)
        """
        self.logger.info(f"Optimizing {server_type} server on {self.system}")

        # Check if server type is supported on this platform
        if server_type == "iis" and not self.is_windows:
            return False, "IIS optimization is only available on Windows", None
        elif server_type == "linux" and not self.is_linux:
            return False, "Linux system optimization is only available on Linux", None

        # Call the appropriate optimization method
        if server_type == "iis":
            success, message = self.optimize_iis(**kwargs)
            return success, message, None
        elif server_type == "nginx":
            success, message = self.optimize_nginx(**kwargs)
            return success, message, None
        elif server_type == "apache":
            success, message = self.optimize_apache(**kwargs)
            return success, message, None
        elif server_type == "linux":
            success, message, script_path = self.optimize_linux(**kwargs)
            return success, message, script_path
        else:
            return False, f"Unsupported server type: {server_type}", None

    def optimize_iis(
        self,
        site_name="Default Web Site",
        video_path=None,
        enable_http2=True,
        enable_http3=False,
        enable_cors=True,
        cors_origin="*",
    ):
        """Optimize IIS server for video streaming.

        Args:
            site_name: Name of the IIS website
            video_path: Path to video content directory
            enable_http2: Enable HTTP/2 protocol
            enable_http3: Enable HTTP/3 with Alt-Svc headers
            enable_cors: Enable CORS headers
            cors_origin: Value for Access-Control-Allow-Origin header

        Returns:
            tuple: (success, message)
        """
        if not self.is_windows:
            return False, "IIS optimization is only available on Windows"

        # Check if PowerShell is available
        if not shutil.which("powershell.exe"):
            return False, "PowerShell is not available"

        # Check if video path exists
        if not dir_exists(video_path):
            return False, f"Video path does not exist: {video_path}"

        # Path to the IIS optimization script
        script_path = self.optimization_utils_dir / "iis-optimization.ps1"
        if not script_path.exists():
            return False, f"IIS optimization script not found: {script_path}"

        # Build the PowerShell command
        safe_site_name = shlex.quote(site_name)
        safe_video_path = shlex.quote(video_path)
        command = [
            "powershell.exe",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
            "-SiteName",
            safe_site_name,
            "-VideoPath",
            safe_video_path,
            "-EnableHttp2",
            "$true" if enable_http2 else "$false",
            "-EnableHttp3",
            "$true" if enable_http3 else "$false",
            "-EnableCors",
            "$true" if enable_cors else "$false",
            "-CorsOrigin",
            cors_origin,
        ]

        try:
            self.logger.info(f"Running IIS optimization: {' '.join(command)}")

            # Run the PowerShell script
            result = subprocess.run(
                command, capture_output=True, text=True, check=False
            )

            # Log the output
            for line in result.stdout.splitlines():
                self.logger.info(f"IIS Optimizer: {line}")

            # Check for errors
            if result.returncode != 0:
                for line in result.stderr.splitlines():
                    self.logger.error(f"IIS Optimizer Error: {line}")
                return (
                    False,
                    f"IIS optimization failed with exit code {result.returncode}",
                )

            return True, "IIS optimization completed successfully"

        except Exception as e:
            self.logger.error(f"Error running IIS optimization: {str(e)}")
            return False, f"Error running IIS optimization: {str(e)}"

    def optimize_nginx(
        self,
        output_path=None,
        server_name="yourdomain.com",
        ssl_enabled=True,
        enable_http3=False,
        video_path="/var/www/videos",
    ):
        """Generate optimized Nginx configuration for video streaming.

        Args:
            output_path: Path to save the configuration file
            server_name: Server name for the Nginx configuration
            ssl_enabled: Enable SSL/TLS configuration
            enable_http3: Enable HTTP/3 with Alt-Svc headers

        Returns:
            tuple: (success, message)
        """
        # Set default output path if not provided
        if output_path is None:
            if self.is_windows:
                output_path = normalize_path("${USERPROFILE}/Desktop/nginx.conf")
            elif self.is_macos:
                output_path = normalize_path("~/Desktop/nginx.conf")
            else:  # Linux
                output_path = normalize_path("/tmp/nginx.conf")

        # Path to the Nginx configuration template
        template_path = self.optimization_utils_dir / "nginx.config"
        if not template_path.exists():
            return False, f"Nginx configuration template not found: {template_path}"

        try:
            # Read the template
            with open(template_path, "r") as f:
                config_content = f.read()

            # Replace placeholders
            config_content = config_content.replace("yourdomain.com", server_name)
            config_content = config_content.replace("/var/www/videos", video_path)

            # Configure SSL based on ssl_enabled parameter
            if not ssl_enabled:
                # Remove SSL configuration
                config_content = config_content.replace("listen 443 ssl http2;", "# listen 443 ssl http2;")
                config_content = config_content.replace("listen [::]:443 ssl http2;", "# listen [::]:443 ssl http2;")
                config_content = config_content.replace("ssl_certificate", "# ssl_certificate")
                config_content = config_content.replace("ssl_certificate_key", "# ssl_certificate_key")

                # Remove HTTP to HTTPS redirect
                config_content = config_content.replace("return 301 https://$host$request_uri;", "# return 301 https://$host$request_uri;")

            # Add HTTP/3 configuration if enabled
            if enable_http3:
                # Add HTTP/3 module and Alt-Svc header
                http3_config = """
    # HTTP/3 and QUIC support
    listen 443 quic reuseport; # UDP listener for QUIC+HTTP/3
    http3 on;
    quic_retry on;

    # Add Alt-Svc header to advertise HTTP/3 support with UDP/443 check
    add_header Alt-Svc 'h3=":443"; ma=86400, h3-29=":443"; ma=86400';
"""
                # Insert HTTP/3 config after the SSL configuration
                config_content = config_content.replace(
                    "listen 443 ssl http2;", "listen 443 ssl http2;\n" + http3_config
                )

            # Create output directory if it doesn't exist
            output_path = normalize_path(output_path)
            ensure_dir_exists(output_path.parent)

            # Write the configuration file
            with open(output_path, "w") as f:
                f.write(config_content)

            self.logger.info(f"Nginx configuration saved to: {output_path}")

            return True, f"Nginx configuration saved to: {output_path}"

        except Exception as e:
            self.logger.error(f"Error generating Nginx configuration: {str(e)}")
            return False, f"Error generating Nginx configuration: {str(e)}"

    def optimize_apache(
        self,
        output_path=None,
        server_name="yourdomain.com",
        ssl_enabled=True,
        enable_http2=True,
        enable_http3=False,
        enable_cors=True,
        cors_origin="*",
        video_path="/var/www/videos",
    ):
        """Generate optimized Apache configuration for video streaming.

        Args:
            output_path: Path to save the configuration file
            server_name: Server name for the Apache configuration
            ssl_enabled: Enable SSL/TLS configuration
            enable_http2: Enable HTTP/2 protocol
            enable_http3: Enable HTTP/3 with Alt-Svc headers
            enable_cors: Enable CORS headers
            cors_origin: Value for Access-Control-Allow-Origin header
            video_path: Path to video content directory

        Returns:
            tuple: (success, message)
        """
        # Set default output path if not provided
        if output_path is None:
            if self.is_windows:
                output_path = normalize_path("${USERPROFILE}/Desktop/apache.conf")
            elif self.is_macos:
                output_path = normalize_path("~/Desktop/apache.conf")
            else:  # Linux
                output_path = normalize_path("/tmp/apache.conf")

        try:
            # Create a basic Apache configuration for video streaming
            config_content = f"""# Apache configuration for video streaming

# Load required modules
LoadModule headers_module modules/mod_headers.so
LoadModule expires_module modules/mod_expires.so
LoadModule mime_module modules/mod_mime.so
{"LoadModule http2_module modules/mod_http2.so" if enable_http2 else "# LoadModule http2_module modules/mod_http2.so"}

# Enable HTTP/2 if requested
{"Protocols h2 http/1.1" if enable_http2 else "# Protocols h2 http/1.1"}

# MIME types for HLS streaming
AddType application/vnd.apple.mpegurl .m3u8
AddType video/mp2t .ts

<VirtualHost *:80>
    ServerName {server_name}
    DocumentRoot "{video_path}"

    # Redirect to HTTPS if SSL is enabled
    {"RewriteEngine On" if ssl_enabled else "# RewriteEngine On"}
    {"RewriteRule ^ https://%{{SERVER_NAME}}%{{REQUEST_URI}} [END,NE,R=permanent]" if ssl_enabled else "# RewriteRule ^ https://%{{SERVER_NAME}}%{{REQUEST_URI}} [END,NE,R=permanent]"}
</VirtualHost>

{"<VirtualHost *:443>" if ssl_enabled else "# <VirtualHost *:443>"}
    {"ServerName " + server_name if ssl_enabled else "# ServerName " + server_name}
    {"DocumentRoot \"" + video_path + "\"" if ssl_enabled else "# DocumentRoot \"" + video_path + "\""}

    {"# SSL Configuration" if ssl_enabled else "# SSL Configuration (disabled)"}
    {"SSLEngine on" if ssl_enabled else "# SSLEngine on"}
    {"SSLCertificateFile /path/to/cert.pem" if ssl_enabled else "# SSLCertificateFile /path/to/cert.pem"}
    {"SSLCertificateKeyFile /path/to/key.pem" if ssl_enabled else "# SSLCertificateKeyFile /path/to/key.pem"}

    # HTTP/3 Alt-Svc header
    {"Header always set Alt-Svc 'h3=\":\"443\"; ma=86400'" if enable_http3 else "# Header always set Alt-Svc 'h3=\":\"443\"; ma=86400'"}

    # CORS headers
    {"Header always set Access-Control-Allow-Origin \"" + cors_origin + "\"" if enable_cors else "# Header always set Access-Control-Allow-Origin \"*\""}
    {"Header always set Access-Control-Allow-Methods \"GET, OPTIONS\"" if enable_cors else "# Header always set Access-Control-Allow-Methods \"GET, OPTIONS\""}
    {"Header always set Access-Control-Allow-Headers \"DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range\"" if enable_cors else "# Header always set Access-Control-Allow-Headers \"DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range\""}

    # Cache control for HLS files
    <Directory "{video_path}">
        Options Indexes FollowSymLinks
        AllowOverride None
        Require all granted

        # Cache settings
        ExpiresActive On

        # HLS playlist files (.m3u8) - short cache time
        <FilesMatch "\.m3u8$">
            ExpiresDefault "access plus 5 seconds"
            Header set Cache-Control "public, max-age=5"
        </FilesMatch>

        # HLS segment files (.ts) - longer cache time
        <FilesMatch "\.ts$">
            ExpiresDefault "access plus 30 minutes"
            Header set Cache-Control "public, max-age=1800"
        </FilesMatch>
    </Directory>
{"</VirtualHost>" if ssl_enabled else "# </VirtualHost>"}
"""

            # Create output directory if it doesn't exist
            output_path = normalize_path(output_path)
            ensure_dir_exists(output_path.parent)

            # Write the configuration file
            with open(output_path, "w") as f:
                f.write(config_content)

            self.logger.info(f"Apache configuration saved to: {output_path}")

            return True, f"Apache configuration saved to: {output_path}"

        except Exception as e:
            self.logger.error(f"Error generating Apache configuration: {str(e)}")
            return False, f"Error generating Apache configuration: {str(e)}"

    def optimize_linux(self, apply_changes=False):
        """Generate or apply Linux system optimizations for video streaming.

        Args:
            apply_changes: If True, apply changes directly; if False, just generate script

        Returns:
            tuple: (success, message, script_path)
        """
        # Path to the Linux optimizations script
        script_path = self.optimization_utils_dir / "linux-optimizations.bash"
        if not script_path.exists():
            return False, f"Linux optimizations script not found: {script_path}", None

        try:
            if apply_changes:
                if platform.system() != "Linux":
                    return (
                        False,
                        "Cannot apply Linux optimizations on non-Linux system",
                        None,
                    )

                # Apply optimizations directly
                result = subprocess.run(
                    ["bash", str(script_path)],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                # Log the output
                for line in result.stdout.splitlines():
                    self.logger.info(f"Linux Optimizer: {line}")

                # Check for errors
                if result.returncode != 0:
                    for line in result.stderr.splitlines():
                        self.logger.error(f"Linux Optimizer Error: {line}")
                    return (
                        False,
                        f"Linux optimization failed with exit code {result.returncode}",
                        None,
                    )

                return True, "Linux optimizations applied successfully", None
            else:
                # Copy the script to a temporary location
                temp_dir = Path(tempfile.mkdtemp())
                output_path = temp_dir / "linux-optimizations.bash"

                shutil.copy2(script_path, output_path)

                self.logger.info(f"Linux optimization script copied to: {output_path}")

                return (
                    True,
                    f"Linux optimization script copied to: {output_path}",
                    output_path,
                )

        except Exception as e:
            self.logger.error(f"Error with Linux optimizations: {str(e)}")
            return False, f"Error with Linux optimizations: {str(e)}", None
