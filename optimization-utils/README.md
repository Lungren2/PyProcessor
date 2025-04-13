# Server Optimization Utilities

This directory contains utility scripts for optimizing web servers for HLS content delivery.

## Available Utilities

### IIS Server Optimization

- **optimize_iis.ps1**: PowerShell script for optimizing IIS servers

  ```powershell
  .\optimize_iis.ps1 -SiteName "MyVideoSite" -VideoPath "C:\inetpub\wwwroot\videos" -EnableHTTP2 $true -EnableHTTP3 $true -EnableCORS $true -CORSOrigin "*"
  ```

### Nginx Server Optimization

- **optimize_nginx.sh**: Bash script for optimizing Nginx servers

  ```bash
  ./optimize_nginx.sh --server-name example.com --output-config /etc/nginx/sites-available/hls --enable-http2 --enable-http3 --enable-cors --cors-origin "*"
  ```

### Linux System Optimization

- **linux-optimizations.bash**: Bash script for optimizing Linux systems

  ```bash
  # Run in dry-run mode (shows what would be done without making changes)
  ./linux-optimizations.bash

  # Apply changes
  ./linux-optimizations.bash --apply-changes

  # Apply changes with verbose output
  ./linux-optimizations.bash --apply-changes --verbose

  # Apply changes without backing up configuration files
  ./linux-optimizations.bash --apply-changes --no-backup

  # Specify a custom log file
  ./linux-optimizations.bash --apply-changes --log-file=/var/log/optimization.log

  # Show help
  ./linux-optimizations.bash --help
  ```

## Prerequisites

### Windows/IIS

- Windows Server 2016 or later
- PowerShell 5.1 or later
- Administrator privileges
- IIS installed with the following features:
  - URL Rewrite Module
  - Application Request Routing
  - HTTP Redirection

### Linux/Nginx

- Ubuntu 18.04 or later / CentOS 7 or later
- Root access
- Nginx 1.18 or later
- The following packages:
  - openssl
  - curl
  - sed
  - grep

## Usage from PyProcessor

These utilities are integrated into PyProcessor and can be accessed through:

1. The GUI: Server Optimization tab
2. The command line:

   ```bash
   python -m pyprocessor --optimize-server iis --site-name "MyVideoSite" --video-path "C:\inetpub\wwwroot\videos" --enable-http2 --enable-http3 --enable-cors --cors-origin "*"
   ```

## Manual Usage

You can also use these utilities directly from the command line:

### IIS Optimization

```powershell
# Navigate to the optimization-utils directory
cd optimization-utils

# Run the IIS optimization script
.\optimize_iis.ps1 -SiteName "MyVideoSite" -VideoPath "C:\inetpub\wwwroot\videos" -EnableHTTP2 $true -EnableHTTP3 $true -EnableCORS $true -CORSOrigin "*"
```

### Nginx Optimization

```bash
# Navigate to the optimization-utils directory
cd optimization-utils

# Make the script executable
chmod +x optimize_nginx.sh

# Run the Nginx optimization script
./optimize_nginx.sh --server-name example.com --output-config /etc/nginx/sites-available/hls --enable-http2 --enable-http3 --enable-cors --cors-origin "*"
```

### Linux System Optimization Script

```bash
# Navigate to the optimization-utils directory
cd optimization-utils

# Make the script executable
chmod +x linux-optimizations.bash

# Run the Linux optimization script in dry-run mode (no changes applied)
./linux-optimizations.bash

# Apply changes with verbose output
./linux-optimizations.bash --apply-changes --verbose
```

## Customization

You can customize these scripts to fit your specific needs by modifying the parameters or editing the scripts directly.

For more information about server optimization, please refer to the [Server Optimization documentation](../docs/developer/SERVER_OPTIMIZATION.md).
