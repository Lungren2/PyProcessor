# Server Optimization Prerequisites

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

This document outlines the prerequisites for using the server optimization features in PyProcessor.

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

### System Requirements
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
  ```
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
