# Server Optimization Guide

PyProcessor includes utilities to optimize various web servers for video streaming across Windows, macOS, and Linux platforms. This document provides information about the server optimization features, prerequisites, and usage.

## HTTP/3 Support

HTTP/3 is the latest version of the HTTP protocol that uses QUIC over UDP instead of TCP. It provides significant performance benefits, especially for mobile users (which typically represent >20% of user bases). HTTP/3 is particularly beneficial for Adaptive Bitrate (ABR) streaming.

### HTTP/3 Requirements

- UDP port 443 must be open and available
- For IIS: Windows Server 2022 or later for native HTTP/3 support
- For Nginx: Nginx 1.25.0+ with the ngx_http_v3_module
- Client browsers that support HTTP/3 (Chrome 85+, Edge 85+, Firefox 88+, Safari 14+)

### How HTTP/3 Auto-Upgrading Works

The server optimization scripts implement HTTP/3 support using Alt-Svc headers. This allows clients to:

1. Initially connect using HTTP/1.1 or HTTP/2
2. Receive the Alt-Svc header indicating HTTP/3 availability
3. Automatically upgrade to HTTP/3 for subsequent requests if supported
4. Fall back to HTTP/2 or HTTP/1.1 if HTTP/3 is not available

This approach ensures backward compatibility while providing performance benefits for supported clients.

## Supported Server Types

PyProcessor supports optimizing the following server types:

- **IIS** (Windows only): Microsoft Internet Information Services
- **Nginx** (All platforms): High-performance HTTP server and reverse proxy
- **Apache** (All platforms): Apache HTTP Server
- **Linux** (Linux only): General Linux system optimizations

## Cross-Platform Considerations

### Windows

- IIS optimization is only available on Windows
- Nginx and Apache configurations can be generated but must be manually installed
- PowerShell is used for IIS optimization

### macOS

- Nginx and Apache configurations can be generated
- Default output path is ~/Desktop/nginx.conf or ~/Desktop/apache.conf
- Manual installation is required

### Linux

- All server types are supported
- Default output path is /tmp/nginx.conf or /tmp/apache.conf
- Linux system optimizations can be applied directly with --apply-changes

## Usage

### Command Line

You can optimize a server using the command line:

```bash
python -m pyprocessor --optimize-server=nginx --server-name=example.com --output-config=/path/to/nginx.conf
```

Available options:

- `--optimize-server`: Server type to optimize (iis, nginx, apache, linux)
- `--site-name`: IIS site name (for IIS optimization)
- `--video-path`: Path to video content directory
- `--enable-http2`: Enable HTTP/2 protocol (default: true)
- `--enable-http3`: Enable HTTP/3 with Alt-Svc headers (default: false)
- `--enable-cors`: Enable CORS headers (default: true)
- `--cors-origin`: CORS origin value (default: *)
- `--output-config`: Output path for server configuration (for Nginx/Apache)
- `--server-name`: Server name for configuration (for Nginx/Apache)
- `--apply-changes`: Apply changes directly (for Linux optimization)

### Programmatic Usage

You can also use the server optimizer programmatically:

```python
from pyprocessor.utils.server_optimizer import ServerOptimizer
from pyprocessor.utils.config import Config
from pyprocessor.utils.logging import Logger

# Create configuration and logger
config = Config()
logger = Logger()

# Create server optimizer
optimizer = ServerOptimizer(config, logger)

# Optimize server
success, message, script_path = optimizer.optimize_server(
    server_type="nginx",
    output_path="/path/to/nginx.conf",
    server_name="example.com",
    ssl_enabled=True,
    enable_http3=False,
    video_path="/var/www/videos"
)

if success:
    print(f"Server optimization successful: {message}")
    if script_path:
        print(f"Generated script at: {script_path}")
else:
    print(f"Server optimization failed: {message}")
```

## Prerequisites

## Windows/IIS PowerShell Script

### System Requirements

- Windows Server 2012 R2 or later (for full HTTP/2 support)
- PowerShell 5.1 or later
- Administrative privileges

### IIS Components

- IIS 8.5 or later installed
- URL Rewrite Module (optional but recommended)
- Dynamic Content Compression module

### Pre-installation Steps

```powershell
# Verify IIS is installed
Get-WindowsFeature -Name Web-Server

# Install IIS if not present (requires admin)
Install-WindowsFeature -Name Web-Server -IncludeManagementTools
```

### Network Considerations

- Ports 80 (HTTP) and 443 (HTTPS) must be open for TCP traffic
- Port 443 must be open for UDP traffic if using HTTP/3
- SSL certificate configured if using HTTPS (required for HTTP/3)

## Linux/NGINX Implementation

### Linux System Requirements

- Linux distribution (Ubuntu 18.04+, CentOS 7+, etc.)
- Root/sudo access
- Minimum 2GB RAM (4GB+ recommended for production)

### Package Dependencies

```bash
# For Debian/Ubuntu:
sudo apt update
sudo apt install -y nginx openssl

# For RHEL/CentOS:
sudo yum install -y epel-release
sudo yum install -y nginx openssl
```

### Configuration Requirements

- NGINX 1.15.5+ for HTTP/2 full support
- NGINX 1.25.0+ for HTTP/3 support
- OpenSSL 1.1.1+ for TLS 1.3 support
- For HTTP/3: NGINX must be compiled with QUIC and HTTP/3 support

### Firewall Configuration

```bash
# Open ports (adjust for your firewall)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
# For HTTP/3 support
sudo ufw allow 443/udp
sudo ufw enable
```

## Linux/Apache Implementation

### Additional Requirements

```bash
# Install Apache with HTTP/2 support
sudo apt install -y apache2 libapache2-mod-http2  # Debian/Ubuntu
sudo yum install -y httpd mod_http2               # RHEL/CentOS
```

### Required Modules

```bash
# Enable necessary modules
sudo a2enmod http2 deflate headers rewrite ssl
sudo systemctl restart apache2
```

## Common Prerequisites for All Configurations

### For Video Streaming

- Video files in proper HLS format (.m3u8 manifests and .ts segments)
- Recommended directory structure:

  ```text
  /video-content/
  ├── live/
  │   ├── stream1.m3u8
  │   ├── stream1_1.ts
  │   └── ...
  └── vod/
      ├── movie1/
      │   ├── playlist.m3u8
      │   └── segments/
      └── ...
  ```

### SSL Certificate (Highly Recommended)

```bash
# Let's Encrypt example (Linux)
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### Hardware Considerations

- SSD storage for video files
- Adequate network bandwidth (minimum 1Gbps for production)
- Sufficient CPU cores (4+ recommended for encoding)

## Verification Steps After Installation

### For Windows/IIS

```powershell
Test-NetConnection -ComputerName localhost -Port 80
Get-WebBinding -Name "Default Web Site"
```

### For Linux

```bash
# Check web server status
sudo systemctl status nginx  # or apache2

# Verify HTTP/2 support
curl -I --http2 https://yourdomain.com

# Verify HTTP/3 support
curl -I --http3 https://yourdomain.com

# Check listening ports
sudo ss -tulnp | grep -E '(nginx|apache)'
```
