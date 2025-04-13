"""
Performance tests for the server optimizer functionality.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import the modules to test
from pyprocessor.utils.config import Config
from pyprocessor.utils.logging import Logger
from pyprocessor.utils.server_optimizer import ServerOptimizer

# Import performance test base
from tests.performance.test_performance_base import (
    PerformanceTest,
    time_function,
    PerformanceResult,
    MemoryUsage,
)


class IISOptimizerPerformanceTest(PerformanceTest):
    """Test the performance of IIS server optimization."""

    def __init__(self, iterations: int = 5):
        """
        Initialize the test.

        Args:
            iterations: Number of iterations to run
        """
        super().__init__("IIS Server Optimization", iterations)
        self.temp_dir = None
        self.video_path = None
        self.config = None
        self.logger = None
        self.server_optimizer = None

    def setup(self) -> None:
        """Set up the test environment."""
        # Create temporary directory
        self.temp_dir = tempfile.TemporaryDirectory()
        self.video_path = Path(self.temp_dir.name) / "videos"
        self.video_path.mkdir(exist_ok=True)

        # Create config
        self.config = Config()

        # Create logger
        self.logger = Logger(level="INFO")

        # Create server optimizer
        self.server_optimizer = ServerOptimizer(self.config, self.logger)

        # Create optimization utils directory
        optimization_utils_dir = Path(self.temp_dir.name) / "optimization-utils"
        optimization_utils_dir.mkdir(exist_ok=True)

        # Create mock IIS optimization script
        iis_script_path = optimization_utils_dir / "iis-optimization.ps1"
        with open(iis_script_path, "w") as f:
            f.write(
                """
            param (
                [string]$SiteName = "Default Web Site",
                [string]$VideoPath = "C:\\inetpub\\wwwroot\\videos",
                [bool]$EnableHttp2 = $true,
                [bool]$EnableHttp3 = $false,
                [bool]$EnableCors = $true,
                [string]$CorsOrigin = "*"
            )

            Write-Output "Optimizing IIS server: $SiteName"
            Write-Output "Video path: $VideoPath"
            Write-Output "HTTP/2 enabled: $EnableHttp2"
            Write-Output "HTTP/3 enabled: $EnableHttp3"
            Write-Output "CORS enabled: $EnableCors"
            Write-Output "CORS origin: $CorsOrigin"

            # Simulate optimization work
            Start-Sleep -Milliseconds 100

            Write-Output "IIS optimization completed successfully"
            """
            )

        # Override optimization utils directory
        self.server_optimizer.optimization_utils_dir = optimization_utils_dir

    def teardown(self) -> None:
        """Clean up the test environment."""
        if self.temp_dir:
            self.temp_dir.cleanup()

    @patch("platform.system")
    @patch("shutil.which")
    @patch("subprocess.run")
    def run_iteration(self, mock_run, mock_which, mock_platform) -> PerformanceResult:
        """Run a single iteration of the test."""
        # Mock platform.system to return Windows
        mock_platform.return_value = "Windows"

        # Mock shutil.which to return PowerShell
        mock_which.return_value = (
            "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
        )

        # Mock subprocess.run to return success
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "IIS optimization completed successfully"
        mock_run.return_value.stderr = ""

        # Time the optimization
        _, execution_time = time_function(
            self.server_optimizer.optimize_iis,
            site_name="Default Web Site",
            video_path=str(self.video_path),
            enable_http2=True,
            enable_http3=True,
            enable_cors=True,
            cors_origin="*",
        )

        # Create a dummy memory usage object with zero values
        memory_usage = MemoryUsage(0, 0, 0)
        return PerformanceResult(execution_time, memory_usage)


class NginxOptimizerPerformanceTest(PerformanceTest):
    """Test the performance of Nginx server optimization."""

    def __init__(self, config_size: str, iterations: int = 5):
        """
        Initialize the test.

        Args:
            config_size: Size of the configuration ('small', 'medium', 'large')
            iterations: Number of iterations to run
        """
        super().__init__(f"Nginx Server Optimization ({config_size})", iterations)
        self.config_size = config_size
        self.temp_dir = None
        self.output_path = None
        self.config = None
        self.logger = None
        self.server_optimizer = None

    def setup(self) -> None:
        """Set up the test environment."""
        # Create temporary directory
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_path = Path(self.temp_dir.name) / "nginx.conf"

        # Create config
        self.config = Config()

        # Create logger
        self.logger = Logger(level="INFO")

        # Create server optimizer
        self.server_optimizer = ServerOptimizer(self.config, self.logger)

        # Create optimization utils directory
        optimization_utils_dir = Path(self.temp_dir.name) / "optimization-utils"
        optimization_utils_dir.mkdir(exist_ok=True)

        # Create mock Nginx configuration template
        nginx_template_path = optimization_utils_dir / "nginx.config"

        # Create template based on size
        if self.config_size == "small":
            template_content = self._create_small_template()
        elif self.config_size == "medium":
            template_content = self._create_medium_template()
        else:  # large
            template_content = self._create_large_template()

        with open(nginx_template_path, "w") as f:
            f.write(template_content)

        # Override optimization utils directory
        self.server_optimizer.optimization_utils_dir = optimization_utils_dir

    def teardown(self) -> None:
        """Clean up the test environment."""
        if self.temp_dir:
            self.temp_dir.cleanup()

    def _create_small_template(self) -> str:
        """Create a small Nginx configuration template."""
        return """
        server {
            listen 80;
            listen 443 ssl http2;
            server_name yourdomain.com;

            root /var/www/html;
            index index.html;

            # SSL configuration
            ssl_certificate /etc/ssl/certs/ssl-cert-snakeoil.pem;
            ssl_certificate_key /etc/ssl/private/ssl-cert-snakeoil.key;

            # HLS content
            location /hls {
                types {
                    application/vnd.apple.mpegurl m3u8;
                    video/mp2t ts;
                }
                root /var/www/html;
                add_header Cache-Control no-cache;
            }
        }
        """

    def _create_medium_template(self) -> str:
        """Create a medium Nginx configuration template."""
        return """
        server {
            listen 80;
            listen 443 ssl http2;
            server_name yourdomain.com;

            root /var/www/html;
            index index.html;

            # SSL configuration
            ssl_certificate /etc/ssl/certs/ssl-cert-snakeoil.pem;
            ssl_certificate_key /etc/ssl/private/ssl-cert-snakeoil.key;
            ssl_protocols TLSv1.2 TLSv1.3;
            ssl_ciphers HIGH:!aNULL:!MD5;
            ssl_prefer_server_ciphers on;
            ssl_session_cache shared:SSL:10m;
            ssl_session_timeout 10m;

            # HLS content
            location /hls {
                types {
                    application/vnd.apple.mpegurl m3u8;
                    video/mp2t ts;
                }
                root /var/www/html;
                add_header Cache-Control no-cache;

                # CORS configuration
                add_header Access-Control-Allow-Origin *;
                add_header Access-Control-Allow-Methods 'GET, HEAD, OPTIONS';
                add_header Access-Control-Allow-Headers 'Range,DNT,X-CustomHeader,Keep-Alive,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type';

                # Caching configuration
                expires 1d;
                add_header Cache-Control "public, max-age=86400";
            }

            # Compression
            gzip on;
            gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript application/vnd.apple.mpegurl;
            gzip_min_length 1000;
            gzip_comp_level 6;
            gzip_vary on;
        }
        """

    def _create_large_template(self) -> str:
        """Create a large Nginx configuration template."""
        base_template = self._create_medium_template()

        # Add multiple server blocks
        additional_blocks = ""
        for i in range(10):
            additional_blocks += f"""
            server {{
                listen 80;
                server_name subdomain{i}.yourdomain.com;
                return 301 https://$host$request_uri;
            }}

            server {{
                listen 443 ssl http2;
                server_name subdomain{i}.yourdomain.com;

                root /var/www/html/subdomain{i};
                index index.html;

                # SSL configuration
                ssl_certificate /etc/ssl/certs/ssl-cert-snakeoil.pem;
                ssl_certificate_key /etc/ssl/private/ssl-cert-snakeoil.key;
                ssl_protocols TLSv1.2 TLSv1.3;
                ssl_ciphers HIGH:!aNULL:!MD5;
                ssl_prefer_server_ciphers on;
                ssl_session_cache shared:SSL:10m;
                ssl_session_timeout 10m;

                # HLS content
                location /hls {{
                    types {{
                        application/vnd.apple.mpegurl m3u8;
                        video/mp2t ts;
                    }}
                    root /var/www/html/subdomain{i};
                    add_header Cache-Control no-cache;

                    # CORS configuration
                    add_header Access-Control-Allow-Origin *;
                    add_header Access-Control-Allow-Methods 'GET, HEAD, OPTIONS';
                    add_header Access-Control-Allow-Headers 'Range,DNT,X-CustomHeader,Keep-Alive,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type';
                }}
            }}
            """

        # Add upstream configuration
        upstream_config = """
        upstream backend {
            server backend1.example.com weight=5;
            server backend2.example.com;
            server backup1.example.com backup;
            server backup2.example.com backup;
        }
        """

        # Add HTTP configuration
        http_config = """
        http {
            include       mime.types;
            default_type  application/octet-stream;

            log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                             '$status $body_bytes_sent "$http_referer" '
                             '"$http_user_agent" "$http_x_forwarded_for"';

            access_log  /var/log/nginx/access.log  main;
            error_log   /var/log/nginx/error.log;

            sendfile        on;
            tcp_nopush      on;
            tcp_nodelay     on;

            keepalive_timeout  65;

            # SSL settings
            ssl_session_cache    shared:SSL:10m;
            ssl_session_timeout  10m;
            ssl_protocols        TLSv1.2 TLSv1.3;
            ssl_ciphers          HIGH:!aNULL:!MD5;
            ssl_prefer_server_ciphers  on;

            # Compression
            gzip  on;
            gzip_comp_level 6;
            gzip_min_length 1000;
            gzip_proxied any;
            gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript application/vnd.apple.mpegurl;
            gzip_vary on;

            # Rate limiting
            limit_req_zone $binary_remote_addr zone=one:10m rate=1r/s;
            limit_conn_zone $binary_remote_addr zone=addr:10m;

            # File cache
            open_file_cache max=1000 inactive=20s;
            open_file_cache_valid 30s;
            open_file_cache_min_uses 2;
            open_file_cache_errors on;

            # Include server blocks
            include /etc/nginx/conf.d/*.conf;
        }
        """

        return upstream_config + http_config + base_template + additional_blocks

    def run_iteration(self) -> PerformanceResult:
        """Run a single iteration of the test."""
        # Time the optimization
        _, execution_time = time_function(
            self.server_optimizer.optimize_nginx,
            output_path=str(self.output_path),
            server_name="example.com",
            ssl_enabled=True,
            enable_http3=True,
        )

        # Create a dummy memory usage object with zero values
        memory_usage = MemoryUsage(0, 0, 0)
        return PerformanceResult(execution_time, memory_usage)


class LinuxOptimizerPerformanceTest(PerformanceTest):
    """Test the performance of Linux system optimization."""

    def __init__(self, apply_changes: bool, iterations: int = 5):
        """
        Initialize the test.

        Args:
            apply_changes: Whether to apply changes directly
            iterations: Number of iterations to run
        """
        super().__init__(
            f"Linux System Optimization (apply_changes={apply_changes})", iterations
        )
        self.apply_changes = apply_changes
        self.temp_dir = None
        self.config = None
        self.logger = None
        self.server_optimizer = None

    def setup(self) -> None:
        """Set up the test environment."""
        # Create temporary directory
        self.temp_dir = tempfile.TemporaryDirectory()

        # Create config
        self.config = Config()

        # Create logger
        self.logger = Logger(level="INFO")

        # Create server optimizer
        self.server_optimizer = ServerOptimizer(self.config, self.logger)

        # Create optimization utils directory
        optimization_utils_dir = Path(self.temp_dir.name) / "optimization-utils"
        optimization_utils_dir.mkdir(exist_ok=True)

        # Create mock Linux optimization script
        linux_script_path = optimization_utils_dir / "linux-optimizations.bash"
        with open(linux_script_path, "w") as f:
            f.write(
                """
            #!/bin/bash

            echo "Optimizing Linux system for video streaming"

            # Simulate optimization work
            sleep 0.1

            echo "Linux system optimization completed successfully"
            exit 0
            """
            )

        # Make the script executable
        linux_script_path.chmod(0o755)

        # Override optimization utils directory
        self.server_optimizer.optimization_utils_dir = optimization_utils_dir

    def teardown(self) -> None:
        """Clean up the test environment."""
        if self.temp_dir:
            self.temp_dir.cleanup()

    @patch("platform.system")
    @patch("subprocess.run")
    def run_iteration(self, mock_run, mock_platform) -> PerformanceResult:
        """Run a single iteration of the test."""
        # Mock platform.system to return Linux if apply_changes is True
        mock_platform.return_value = "Linux" if self.apply_changes else "Windows"

        # Mock subprocess.run to return success
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = (
            "Linux system optimization completed successfully"
        )
        mock_run.return_value.stderr = ""

        # Time the optimization
        _, execution_time = time_function(
            self.server_optimizer.optimize_linux, apply_changes=self.apply_changes
        )

        # Create a dummy memory usage object with zero values
        memory_usage = MemoryUsage(0, 0, 0)
        return PerformanceResult(execution_time, memory_usage)


@patch("platform.system")
@patch("shutil.which")
@patch("subprocess.run")
def test_iis_optimizer_performance(mock_run, mock_which, mock_platform):
    """Test the performance of IIS server optimization."""
    # Mock platform.system to return Windows
    mock_platform.return_value = "Windows"

    # Mock shutil.which to return PowerShell
    mock_which.return_value = (
        "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
    )

    # Mock subprocess.run to return success
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "IIS optimization completed successfully"
    mock_run.return_value.stderr = ""

    test = IISOptimizerPerformanceTest()
    results = test.run()
    test.print_results(results)

    # Assert that the performance is reasonable
    assert results["avg_time"] < 0.1, "IIS server optimization is too slow"


def test_nginx_optimizer_performance():
    """Test the performance of Nginx server optimization with different configuration sizes."""
    config_sizes = ["small", "medium", "large"]

    for config_size in config_sizes:
        test = NginxOptimizerPerformanceTest(config_size)
        results = test.run()
        test.print_results(results)

        # Assert that the performance is reasonable
        if config_size == "small":
            assert (
                results["avg_time"] < 0.01
            ), f"Nginx server optimization for {config_size} config is too slow"
        elif config_size == "medium":
            assert (
                results["avg_time"] < 0.05
            ), f"Nginx server optimization for {config_size} config is too slow"
        elif config_size == "large":
            assert (
                results["avg_time"] < 0.1
            ), f"Nginx server optimization for {config_size} config is too slow"


@patch("platform.system")
@patch("subprocess.run")
def test_linux_optimizer_performance(mock_run, mock_platform):
    """Test the performance of Linux system optimization."""
    # Mock subprocess.run to return success
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "Linux system optimization completed successfully"
    mock_run.return_value.stderr = ""

    # Test with apply_changes=False
    mock_platform.return_value = "Windows"
    test_false = LinuxOptimizerPerformanceTest(apply_changes=False)
    results_false = test_false.run()
    test_false.print_results(results_false)

    # Test with apply_changes=True
    mock_platform.return_value = "Linux"
    test_true = LinuxOptimizerPerformanceTest(apply_changes=True)
    results_true = test_true.run()
    test_true.print_results(results_true)

    # Assert that the performance is reasonable
    assert (
        results_false["avg_time"] < 0.05
    ), "Linux system optimization (generate script) is too slow"
    assert (
        results_true["avg_time"] < 0.1
    ), "Linux system optimization (apply changes) is too slow"


if __name__ == "__main__":
    test_iis_optimizer_performance()
    test_nginx_optimizer_performance()
    test_linux_optimizer_performance()
