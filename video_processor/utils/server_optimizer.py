"""
Server optimization utilities for video streaming servers.

This module provides functionality to optimize different types of web servers
for video streaming, using optimization scripts from the optimization-utils directory.
"""

import os
import subprocess
import platform
import shutil
from pathlib import Path
import tempfile

from video_processor.utils.logging import Logger


class ServerOptimizer:
    """Server optimization utility for video streaming servers."""

    def __init__(self, config, logger=None):
        """Initialize the server optimizer.
        
        Args:
            config: Configuration instance
            logger: Logger instance (optional)
        """
        self.config = config
        self.logger = logger or Logger()
        
        # Get the base directory of the application
        self.base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.optimization_utils_dir = self.base_dir / "optimization-utils"
        
        # Check if optimization utils directory exists
        if not self.optimization_utils_dir.exists():
            self.logger.warning(f"Optimization utilities directory not found: {self.optimization_utils_dir}")
    
    def optimize_iis(self, site_name, video_path, enable_http2=True, enable_cors=True, cors_origin="*"):
        """Optimize IIS server for video streaming.
        
        Args:
            site_name: Name of the IIS website
            video_path: Path to video content directory
            enable_http2: Enable HTTP/2 protocol
            enable_cors: Enable CORS headers
            cors_origin: Value for Access-Control-Allow-Origin header
            
        Returns:
            tuple: (success, message)
        """
        if platform.system() != "Windows":
            return False, "IIS optimization is only available on Windows"
        
        # Check if PowerShell is available
        if not shutil.which("powershell.exe"):
            return False, "PowerShell is not available"
        
        # Check if video path exists
        if not os.path.exists(video_path):
            return False, f"Video path does not exist: {video_path}"
        
        # Path to the IIS optimization script
        script_path = self.optimization_utils_dir / "iis-optimization.ps1"
        if not script_path.exists():
            return False, f"IIS optimization script not found: {script_path}"
        
        # Build the PowerShell command
        command = [
            "powershell.exe",
            "-ExecutionPolicy", "Bypass",
            "-File", str(script_path),
            "-SiteName", site_name,
            "-VideoPath", video_path,
            "-EnableHttp2", "$true" if enable_http2 else "$false",
            "-EnableCors", "$true" if enable_cors else "$false",
            "-CorsOrigin", cors_origin
        ]
        
        try:
            self.logger.info(f"Running IIS optimization: {' '.join(command)}")
            
            # Run the PowerShell script
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False
            )
            
            # Log the output
            for line in result.stdout.splitlines():
                self.logger.info(f"IIS Optimizer: {line}")
            
            # Check for errors
            if result.returncode != 0:
                for line in result.stderr.splitlines():
                    self.logger.error(f"IIS Optimizer Error: {line}")
                return False, f"IIS optimization failed with exit code {result.returncode}"
            
            return True, "IIS optimization completed successfully"
            
        except Exception as e:
            self.logger.error(f"Error running IIS optimization: {str(e)}")
            return False, f"Error running IIS optimization: {str(e)}"
    
    def optimize_nginx(self, output_path, server_name="yourdomain.com", ssl_enabled=True):
        """Generate optimized Nginx configuration for video streaming.
        
        Args:
            output_path: Path to save the configuration file
            server_name: Server name for the Nginx configuration
            ssl_enabled: Enable SSL/TLS configuration
            
        Returns:
            tuple: (success, message)
        """
        # Path to the Nginx configuration template
        template_path = self.optimization_utils_dir / "nginx.config"
        if not template_path.exists():
            return False, f"Nginx configuration template not found: {template_path}"
        
        try:
            # Read the template
            with open(template_path, 'r') as f:
                config_content = f.read()
            
            # Replace placeholders
            config_content = config_content.replace("yourdomain.com", server_name)
            
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Write the configuration file
            with open(output_path, 'w') as f:
                f.write(config_content)
            
            self.logger.info(f"Nginx configuration saved to: {output_path}")
            
            return True, f"Nginx configuration saved to: {output_path}"
            
        except Exception as e:
            self.logger.error(f"Error generating Nginx configuration: {str(e)}")
            return False, f"Error generating Nginx configuration: {str(e)}"
    
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
                    return False, "Cannot apply Linux optimizations on non-Linux system", None
                
                # Apply optimizations directly
                result = subprocess.run(
                    ["bash", str(script_path)],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                # Log the output
                for line in result.stdout.splitlines():
                    self.logger.info(f"Linux Optimizer: {line}")
                
                # Check for errors
                if result.returncode != 0:
                    for line in result.stderr.splitlines():
                        self.logger.error(f"Linux Optimizer Error: {line}")
                    return False, f"Linux optimization failed with exit code {result.returncode}", None
                
                return True, "Linux optimizations applied successfully", None
            else:
                # Copy the script to a temporary location
                temp_dir = tempfile.mkdtemp()
                output_path = os.path.join(temp_dir, "linux-optimizations.bash")
                
                shutil.copy2(script_path, output_path)
                
                self.logger.info(f"Linux optimization script copied to: {output_path}")
                
                return True, f"Linux optimization script copied to: {output_path}", output_path
                
        except Exception as e:
            self.logger.error(f"Error with Linux optimizations: {str(e)}")
            return False, f"Error with Linux optimizations: {str(e)}", None
