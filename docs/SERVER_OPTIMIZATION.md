# Server Optimization Prerequisites

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
- Ports 80 (HTTP) and 443 (HTTPS) must be open
- SSL certificate configured if using HTTPS

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
- OpenSSL 1.1.1+ for TLS 1.3 support

### Firewall Configuration
```bash
# Open ports (adjust for your firewall)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
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

# Check listening ports
sudo ss -tulnp | grep -E '(nginx|apache)'
```
