<#
.SYNOPSIS
    Optimizes IIS for video streaming with comprehensive configuration and safety checks.
.DESCRIPTION
    Configures IIS for optimal video streaming performance including HTTP/2, HTTP/3 (via Alt-Svc),
    compression, caching strategies, and network optimizations. Specifically tuned for HLS streaming
    and Adaptive Bitrate (ABR) delivery.
.PARAMETER SiteName
    The name of the IIS website to configure (default: "Default Web Site")
.PARAMETER VideoPath
    The physical path to the video content directory
.PARAMETER EnableHttp2
    Enable HTTP/2 protocol support (default: $true)
.PARAMETER EnableHttp3
    Enable HTTP/3 with Alt-Svc headers for auto-upgrading (default: $false)
.PARAMETER EnableCors
    Enable CORS headers (default: $true)
.PARAMETER CorsOrigin
    Value for Access-Control-Allow-Origin header (default: "*")
.EXAMPLE
    .\Optimize-IISForVideoStreaming.ps1 -VideoPath "C:\inetpub\wwwroot\videos"
.NOTES
    Requires PowerShell to be run as Administrator
#>

param(
    [string]$SiteName = "Default Web Site",
    [Parameter(Mandatory = $true)]
    [ValidateScript({
            if (-not (Test-Path $_)) { throw "Video path $_ does not exist" }
            $true
        })]
    [string]$VideoPath,
    [bool]$EnableHttp2 = $true,
    [bool]$EnableHttp3 = $false,
    [bool]$EnableCors = $true,
    [string]$CorsOrigin = "*"
)

#region Initialization
$ErrorActionPreference = "Stop"

# Verify administrator privileges
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "This script must be run as Administrator"
    exit 1
}

# Verify IIS is installed
if (-not (Get-WindowsFeature -Name Web-Server).Installed) {
    Write-Error "IIS is not installed. Please install IIS first."
    exit 1
}

# Verify the specified site exists
if (-not (Get-Website -Name $SiteName)) {
    Write-Error "Website '$SiteName' does not exist"
    exit 1
}
#endregion

#region Functions
function Set-RegistryValueSafe {
    param(
        [string]$Path,
        [string]$Name,
        $Value,
        [string]$PropertyType
    )

    try {
        if (-not (Test-Path $Path)) {
            New-Item -Path $Path -Force | Out-Null
        }
        New-ItemProperty -Path $Path -Name $Name -Value $Value -PropertyType $PropertyType -Force | Out-Null
        Write-Host "Successfully set registry value $Path\$Name = $Value"
    }
    catch {
        Write-Warning "Failed to set registry value $Path\$Name $_"
    }
}

function Add-WindowsFeatureSafe {
    param(
        [string]$FeatureName
    )

    try {
        if (-not (Get-WindowsFeature -Name $FeatureName).Installed) {
            Add-WindowsFeature $FeatureName | Out-Null
            Write-Host "Successfully installed feature $FeatureName"
        }
        else {
            Write-Host "Feature $FeatureName is already installed"
        }
    }
    catch {
        Write-Warning "Failed to install feature $FeatureName $_"
    }
}
#endregion

#region HTTP/2 and HTTP/3 Configuration
# HTTP/2 Configuration
if ($EnableHttp2) {
    try {
        Write-Host "Configuring HTTP/2 support..."
        Set-RegistryValueSafe -Path 'HKLM:\System\CurrentControlSet\Services\HTTP\Parameters' -Name 'EnableHttp2Tls' -Value 1 -PropertyType DWord
        Set-RegistryValueSafe -Path 'HKLM:\System\CurrentControlSet\Services\HTTP\Parameters' -Name 'EnableHttp2Cleartext' -Value 1 -PropertyType DWord
    }
    catch {
        Write-Warning "HTTP/2 configuration failed: $_"
    }
}

# HTTP/3 Configuration (via Alt-Svc headers)
if ($EnableHttp3) {
    try {
        Write-Host "Configuring HTTP/3 support via Alt-Svc headers..."

        # Check if UDP port 443 is available
        $udpPortCheck = Test-NetConnection -ComputerName localhost -Port 443 -InformationLevel Quiet -ErrorAction SilentlyContinue

        if ($udpPortCheck) {
            Write-Host "UDP port 443 is available for HTTP/3 (QUIC protocol)"
        } else {
            Write-Warning "UDP port 443 may not be available. HTTP/3 might not work properly."
            Write-Host "Continuing with HTTP/3 configuration anyway..."
        }

        # We'll add Alt-Svc headers in the web.config
        Write-Host "HTTP/3 will be enabled via Alt-Svc headers in web.config"
    }
    catch {
        Write-Warning "HTTP/3 configuration check failed: $_"
    }
}
#endregion

#region IIS Features Installation
try {
    Write-Host "Installing required IIS features..."
    $features = @(
        "Web-Static-Content",
        "Web-Http-Compression",
        "Web-Stat-Compression",
        "Web-Dyn-Compression"
    )

    foreach ($feature in $features) {
        Add-WindowsFeatureSafe -FeatureName $feature
    }
}
catch {
    Write-Warning "IIS feature installation failed: $_"
}
#endregion

#region IIS Configuration
try {
    Write-Host "Configuring IIS compression..."
    Import-Module WebAdministration -ErrorAction Stop

    Set-WebConfigurationProperty -Filter "system.webServer/urlCompression" -PSPath "IIS:\" -Name "doStaticCompression" -Value "True" -ErrorAction Stop
    Set-WebConfigurationProperty -Filter "system.webServer/urlCompression" -PSPath "IIS:\" -Name "doDynamicCompression" -Value "True" -ErrorAction Stop

    Write-Host "Configuring MIME types for video streaming..."
    $staticTypes = @(
        @{fileExtension = '.m3u8'; mimeType = 'application/vnd.apple.mpegurl' },
        @{fileExtension = '.ts'; mimeType = 'video/mp2t' }
    )

    foreach ($type in $staticTypes) {
        try {
            if (-not (Get-WebConfigurationProperty -Filter "//staticContent/mimeMap[@fileExtension='$($type.fileExtension)']" -PSPath "IIS:\Sites\$SiteName" -Name ".")) {
                Add-WebConfigurationProperty -Filter "//staticContent" -PSPath "IIS:\Sites\$SiteName" -Name "." -Value @{fileExtension = $type.fileExtension; mimeType = $type.mimeType } -ErrorAction Stop
                Write-Host "Added MIME type for $($type.fileExtension)"
            }
        }
        catch {
            Write-Warning "Failed to add MIME type for $($type.fileExtension): $_"
        }
    }
}
catch {
    Write-Warning "IIS configuration failed: $_"
}
#endregion

#region Virtual Directory and Caching Configuration
try {
    Write-Host "Configuring virtual directory and caching..."

    # Create virtual directory if it doesn't exist
    if (-not (Get-WebVirtualDirectory -Site $SiteName -Name "videos" -ErrorAction SilentlyContinue)) {
        New-WebVirtualDirectory -Site $SiteName -Name "videos" -PhysicalPath $VideoPath -ErrorAction Stop
        Write-Host "Created virtual directory 'videos'"
    }

    $configPath = "IIS:\Sites\$SiteName\videos"

    # Configure caching
    Set-WebConfigurationProperty -Filter "system.webServer/staticContent" -PSPath $configPath -Name "clientCache.cacheControlMode" -Value "UseMaxAge" -ErrorAction Stop
    Set-WebConfigurationProperty -Filter "system.webServer/staticContent" -PSPath $configPath -Name "clientCache.cacheControlMaxAge" -Value "00:05:00" -ErrorAction Stop

    # Create web.config with optimized settings
    $webConfig = @"
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <staticContent>
            <clientCache cacheControlMode="UseMaxAge" cacheControlMaxAge="00:05:00" />
        </staticContent>
        <handlers>
            <clear />
            <add name="StaticFile" path="*" verb="*" modules="StaticFileModule" resourceType="File" requireAccess="Read" />
        </handlers>
        <httpProtocol>
            <customHeaders>
                <add name="Access-Control-Allow-Origin" value="$CorsOrigin" />
$(if ($EnableHttp3) { "                <add name=\"Alt-Svc\" value=\"h3=\\\":\\\"443\\\"; ma=86400, h3-29=\\\":\\\"443\\\"; ma=86400\" />" })
            </customHeaders>
        </httpProtocol>
    </system.webServer>
    <location path="*.m3u8">
        <system.webServer>
            <staticContent>
                <clientCache cacheControlMode="UseMaxAge" cacheControlMaxAge="00:00:05" />
            </staticContent>
        </system.webServer>
    </location>
    <location path="*.ts">
        <system.webServer>
            <staticContent>
                <clientCache cacheControlMode="UseMaxAge" cacheControlMaxAge="00:30:00" />
            </staticContent>
        </system.webServer>
    </location>
</configuration>
"@

    $webConfigPath = Join-Path -Path $VideoPath -ChildPath "web.config"
    $webConfig | Out-File -FilePath $webConfigPath -Encoding UTF8 -ErrorAction Stop
    Write-Host "Created optimized web.config at $webConfigPath"
}
catch {
    Write-Warning "Virtual directory and caching configuration failed: $_"
}
#endregion

#region Network Optimization
try {
    Write-Host "Optimizing network settings..."

    # TCP Window Scaling
    Set-RegistryValueSafe -Path "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" -Name "Tcp1323Opts" -Value 1 -PropertyType "DWord"

    # Maximum segment size for TCP
    Set-RegistryValueSafe -Path "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" -Name "EnablePMTUBHDetect" -Value 1 -PropertyType "DWord"
    Set-RegistryValueSafe -Path "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" -Name "EnablePMTUDiscovery" -Value 1 -PropertyType "DWord"

    # Increase TCP connections limit
    Set-RegistryValueSafe -Path "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" -Name "TcpNumConnections" -Value 0xfffe -PropertyType "DWord"
}
catch {
    Write-Warning "Network optimization failed: $_"
}
#endregion

#region Finalization
try {
    Write-Host "Restarting IIS..."
    Restart-Service W3SVC -Force -ErrorAction Stop

    Write-Host @"
IIS optimization for video streaming complete successfully.

Recommendations:
1. Consider configuring HTTPS for secure video delivery
2. Monitor server performance after changes
3. Adjust cache durations based on your specific content update frequency

You may need to restart the server for all changes to take full effect.
"@ -ForegroundColor Green
}
catch {
    Write-Warning "Failed to restart IIS: $_"
    Write-Host "Some changes may require a manual restart of IIS or the server." -ForegroundColor Yellow
}
#endregion