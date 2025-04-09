<#
.SYNOPSIS
Enhanced video processing script with comprehensive error handling, logging, and parallel processing

.DESCRIPTION
1. Processes video files through multiple stages:
   - File renaming based on pattern
   - Video encoding to HLS formats
   - Folder organization
2. Features enhanced error handling, logging, and configuration management
3. Supports parallel processing (PowerShell 7+ recommended)
#>

#region Configuration
Write-Host "For consistency the script generates directories for input and output automatically at: C:\inetpub\wwwroot\media\input and C:\inetpub\wwwroot\media\output. Please place your files in the input directory and then run the script" -ForegroundColor Red
$inputFolder = "C:\inetpub\wwwroot\media\input"
$outputFolder = "C:\inetpub\wwwroot\media\output"

$logFilePath = Join-Path $outputFolder "processing_log_$(Get-Date -Format 'yyyyMMdd-HHmmss').txt"

Write-Host "Loading configuration..." -ForegroundColor Blue

$cores = $env:NUMBER_OF_PROCESSORS
$cores = (Get-WmiObject -Class Win32_Processor).NumberOfCores
$cores = (Get-CimInstance -ClassName Win32_Processor).NumberOfCores
$cores = [Environment]::ProcessorCount

# Create directories if they don't exist
@($inputFolder, $outputFolder) | ForEach-Object {
    if (-not (Test-Path $_)) {
        New-Item -Path $_ -ItemType Directory -Force
        Write-Host "Created directory: $_"
    }
}

# Load required WPF assembly
Add-Type -AssemblyName PresentationFramework

# Define the XAML for our window
[xml]$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" 
        Title="FFmpeg Parameter Selection" Height="300" Width="400">
    <StackPanel Margin="10">
        <!-- Encoder Options -->
        <TextBlock Text="Select Encoder (cpu:libx265/libx264 gpu:h264_nvenc) :" Margin="0,0,0,5" />
        <StackPanel Orientation="Horizontal">
            <RadioButton Name="rbLibx265" Content="libx265" GroupName="Encoder" IsChecked="True" Margin="0,0,10,0"/>
            <RadioButton Name="rbH264_nvenc" Content="h264_nvenc" GroupName="Encoder" Margin="0,0,10,0"/>
            <RadioButton Name="rbLibx264" Content="libx264" GroupName="Encoder"/>
        </StackPanel>
        
        <!-- Preset Options -->
        <TextBlock Text="Select Preset:" Margin="0,10,0,5" />
        <StackPanel Orientation="Horizontal">
            <RadioButton Name="rbUltraFast" Content="ultrafast" GroupName="Preset" IsChecked="True" Margin="0,0,10,0"/>
            <RadioButton Name="rbVeryFast" Content="veryfast" GroupName="Preset" Margin="0,0,10,0"/>
            <RadioButton Name="rbMedium" Content="medium" GroupName="Preset"/>
        </StackPanel>
        
        <!-- Tune Options -->
        <TextBlock Text="Select Tune:" Margin="0,10,0,5" />
        <StackPanel Orientation="Horizontal">
            <RadioButton Name="rbZerolatency" Content="zerolatency" GroupName="Tune" IsChecked="True" Margin="0,0,10,0"/>
            <RadioButton Name="rbFilm" Content="film" GroupName="Tune" Margin="0,0,10,0"/>
            <RadioButton Name="rbAnimation" Content="animation" GroupName="Tune"/>
        </StackPanel>

         <!-- FPS Options -->
        <TextBlock Text="Select FPS:" Margin="0,10,0,5" />
        <StackPanel Orientation="Horizontal">
            <RadioButton Name="rbOneTwentyFPS" Content="120" GroupName="FPS" Margin="0,0,10,0"/>
            <RadioButton Name="rbSixtyFPS" Content="60" GroupName="FPS" IsChecked="True" Margin="0,0,10,0"/>
            <RadioButton Name="rbThirtyFPS" Content="30" GroupName="FPS" Margin="0,0,10,0"/>
        </StackPanel>
        
        <!-- OK Button -->
        <Button Name="btnOK" Content="OK" Width="100" Margin="0,20,0,0" HorizontalAlignment="Center"/>
    </StackPanel>
</Window>
"@

# Create the window from the XAML
$reader = (New-Object System.Xml.XmlNodeReader $xaml)
$window = [Windows.Markup.XamlReader]::Load($reader)

# Get references to the controls
$rbLibx265 = $window.FindName("rbLibx265")
$rbH264_nvenc = $window.FindName("rbH264_nvenc")
$rbLibx264 = $window.FindName("rbLibx264")

$rbUltraFast = $window.FindName("rbUltraFast")
$rbVeryFast = $window.FindName("rbVeryFast")
$rbMedium = $window.FindName("rbMedium")

$rbZerolatency = $window.FindName("rbZerolatency")
$rbFilm = $window.FindName("rbFilm")
$rbAnimation = $window.FindName("rbAnimation")

$rbOneTwentyFPS = $window.FindName("rbOneTwentyFPS")
$rbSixtyFPS = $window.FindName("rbSixtyFPS")
$rbThirtyFPS = $window.FindName("rbThirtyFPS")

$btnOK = $window.FindName("btnOK")

# Function to enable/disable preset and tune options
function UpdateOptions {
    if ($rbH264_nvenc.IsChecked) {
        # h264_nvenc doesn't support -preset or -tune
        $rbUltraFast.IsEnabled = $false
        $rbVeryFast.IsEnabled = $false
        $rbMedium.IsEnabled = $false

        $rbZerolatency.IsEnabled = $false
        $rbFilm.IsEnabled = $false
        $rbAnimation.IsEnabled = $false
    }
    else {
        # Enable preset and tune options for libx265 and libx264
        $rbUltraFast.IsEnabled = $true
        $rbVeryFast.IsEnabled = $true
        $rbMedium.IsEnabled = $true

        $rbZerolatency.IsEnabled = $true
        $rbFilm.IsEnabled = $true
        $rbAnimation.IsEnabled = $true
    }
}

# Attach event handlers to update options when encoder selection changes
$rbLibx265.Add_Click({ UpdateOptions })
$rbH264_nvenc.Add_Click({ UpdateOptions })
$rbLibx264.Add_Click({ UpdateOptions })
$rbOneTwentyFPS.Add_Click({ UpdateOptions })
$rbSixtyFPS.Add_Click({ UpdateOptions })
$rbThirtyFPS.Add_Click({ UpdateOptions })

# Set initial state
UpdateOptions

# Event handler for the OK button – close the window when clicked
$btnOK.Add_Click({
        $window.DialogResult = $true
        $window.Close()
    })

# Show the window as a modal dialog
$window.ShowDialog() | Out-Null

# Determine the selected encoder
if ($rbLibx265.IsChecked) {
    $encoder = "libx265"
}
elseif ($rbH264_nvenc.IsChecked) {
    $encoder = "h264_nvenc"
}
elseif ($rbLibx264.IsChecked) {
    $encoder = "libx264"
}

# Determine the selected preset (only if applicable)
if ($rbUltraFast.IsChecked -and $rbUltraFast.IsEnabled) {
    $preset = "ultrafast"
}
elseif ($rbVeryFast.IsChecked -and $rbVeryFast.IsEnabled) {
    $preset = "veryfast"
}
elseif ($rbMedium.IsChecked -and $rbMedium.IsEnabled) {
    $preset = "medium"
}
else {
    $preset = $null
}

# Determine the selected tune option (only if applicable)
if ($rbZerolatency.IsChecked -and $rbZerolatency.IsEnabled) {
    $tune = "zerolatency"
}
elseif ($rbFilm.IsChecked -and $rbFilm.IsEnabled) {
    $tune = "film"
}
elseif ($rbAnimation.IsChecked -and $rbAnimation.IsEnabled) {
    $tune = "animation"
}
else {
    $tune = $null
}

# Determine the selected FPS
if ($rbOneTwentyFPS.IsChecked) {
    $selectedFPS = 120
}
elseif ($rbSixtyFPS.IsChecked) {
    $selectedFPS = 60
}
elseif ($rbThirtyFPS.IsChecked) {
    $selectedFPS = 30
}
else {
    $selectedFPS = 60
}

# FFmpeg Configuration
$ffmpegParams = @{
    VideoEncoder  = $encoder
    Bitrates      = @{
        "1080p" = "11000k"
        "720p"  = "6500k"
        "480p"  = "4000k"
        "360p"  = "1500k"
    }
    AudioBitrates = @("192k", "128k", "96k", "64k")
}

# Only add preset and tune if they are defined
if ($preset) { $ffmpegParams.Preset = $preset }
if ($tune) { $ffmpegParams.Tune = $tune }

# Processing Options
$maxParallelJobs = [Math]::Max(1, [Math]::Floor($cores * 0.75))  # Set based on CPU cores
#endregion

#region Initialization
Write-Host "Initializing..." -ForegroundColor Blue
function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp][$Level] $Message"
    Add-Content -Path $logFilePath -Value $logEntry
}

function Test-FFmpeg {
    try {
        $null = Get-Command ffmpeg -ErrorAction Stop
        $null = Get-Command ffprobe -ErrorAction Stop
        return $true
    }
    catch {
        Write-Log -Message "FFmpeg/ffprobe not found in PATH" -Level "ERROR"
        return $false
    }
}

# Validate environment
if (-not (Test-Path $inputFolder)) {
    Write-Log -Message "Input folder missing: $inputFolder" -Level "ERROR"
    exit 1
}

if (-not (Test-FFmpeg)) {
    exit 1
}

try {
    New-Item -Path $outputFolder -ItemType Directory -Force | Out-Null
}
catch {
    Write-Log -Message "Failed to create output folder: $_" -Level "ERROR"
    exit 1
}
#endregion

#region File Renaming
Write-Log -Message "Starting file renaming process"
Write-Host "Starting file renaming..." -ForegroundColor Blue
$filesToRename = Get-ChildItem -Path $inputFolder -File
$totalFiles = $filesToRename.Count
$count = 0

Get-ChildItem -Path $inputFolder -File | ForEach-Object {
    $count++
    Write-Progress -Activity "Renaming Files" `
        -Status "Processing file $count of $totalFiles" `
        -PercentComplete (($count / $totalFiles) * 100)
    try {
        # Remove all whitespace first
        $nameWithoutSpaces = $_.Name -replace '\s+', ''
        
        if ($nameWithoutSpaces -match ".*?(\d+-\d+).*?\.mp4$") {
            $newName = $matches[1] + ".mp4"
            Rename-Item -Path $_.FullName -NewName $newName -Force -ErrorAction Stop
            Write-Log -Message "Renamed: $($_.Name) to $newName"
        }
        else {
            Write-Log -Message "Skipping non-matching file: $($_.Name)" -Level "WARNING"
        }
    }
    catch {
        Write-Log -Message "Failed to rename $($_.Name): $_" -Level "ERROR"
    }
}
Write-Log -Message "File renaming completed"
#endregion

#region Video Processing
Write-Host "Starting video processing..." -ForegroundColor Blue
Write-Host "With parameters: $($ffmpegParams | ConvertTo-Json) @ $selectedFPS FPS" -ForegroundColor Blue
Write-Host "This may take a while..." -ForegroundColor Blue
Write-Log -Message "Starting video processing"
$processingStart = Get-Date

$global:processedVideoCount = 1
$files = Get-ChildItem -Path $inputFolder -Filter *.mp4
$totalFiles = $files.Count

# Before processing, validate file names
$invalidFiles = @()
$validFiles = @()

$files | ForEach-Object {
    if ($_.Name -match '^\d+-\d+\.mp4$') {
        $validFiles += $_
    }
    else {
        $invalidFiles += $_.Name
    }
}

# Report invalid files if any
if ($invalidFiles.Count -gt 0) {
    Write-Host "The following files do not match the required format (number-number.mp4):" -ForegroundColor Yellow
    $invalidFiles | ForEach-Object {
        Write-Host "  - $_" -ForegroundColor Yellow
    }
}

# Only proceed if we have valid files
if ($validFiles.Count -eq 0) {
    Write-Host "No valid files found to process. Files must be named in the format: number-number.mp4" -ForegroundColor Red
    return
}
else {
    Write-Host "Found $($validFiles.Count) valid files to process." -ForegroundColor Green

    $totalFiles = $validFiles.Count  # Update totalFiles to only count valid files
    $processedVideoCount = 1
    
    # Replace $files with $validFiles in your processing block
    $validFiles | ForEach-Object -Parallel {
        $file = $_
        $baseName = $file.BaseName
        $outputSubfolder = Join-Path $using:outputFolder $baseName

        try {
            # Create output directory
            $null = New-Item -Path $outputSubfolder -ItemType Directory -Force

            # Check audio streams
            $hasAudio = [bool](ffprobe -i $file.FullName -show_streams -select_streams a -loglevel error 2>&1)

            # Calculate buffer sizes
            $bitrates = $using:ffmpegParams.Bitrates
            $bufsizes = @{}
            foreach ($res in $bitrates.Keys) {
                $bitrate = $bitrates[$res]
                $bufsizeValue = [int]($bitrate.TrimEnd('k')) * 2
                $bufsizes[$res] = "${bufsizeValue}k"
            }

            # Build FFmpeg command as an array (kept for configuration purposes)
            $command = @(
                "-hide_banner", "-loglevel", "error", "-stats",
                "-i", $file.FullName
            )

            # Construct the filter_complex argument as a single string
            $filterComplex = '[0:v]split=4[v1][v2][v3][v4];[v1]scale=1920:1080[v1out];[v2]scale=1280:720[v2out];[v3]scale=854:480[v3out];[v4]scale=640:360[v4out]'
            $command += "-filter_complex", $filterComplex

            # Video streams for all resolutions
            $command += @(
                # 1080p
                "-map", "[v1out]", "-c:v:0", $using:ffmpegParams.VideoEncoder,
                "-preset:v:0", $using:ffmpegParams.Preset,
                "-tune:v:0", $using:ffmpegParams.Tune,
                "-b:v:0", $bitrates['1080p'],
                "-maxrate:v:0", $bitrates['1080p'],
                "-bufsize:v:0", $bufsizes['1080p'],

                # 720p
                "-map", "[v2out]", "-c:v:1", $using:ffmpegParams.VideoEncoder,
                "-preset:v:1", $using:ffmpegParams.Preset,
                "-tune:v:1", $using:ffmpegParams.Tune,
                "-b:v:1", $bitrates['720p'],
                "-maxrate:v:1", $bitrates['720p'],
                "-bufsize:v:1", $bufsizes['720p'],

                # 480p
                "-map", "[v3out]", "-c:v:2", $using:ffmpegParams.VideoEncoder,
                "-preset:v:2", $using:ffmpegParams.Preset,
                "-tune:v:2", $using:ffmpegParams.Tune,
                "-b:v:2", $bitrates['480p'],
                "-maxrate:v:2", $bitrates['480p'],
                "-bufsize:v:2", $bufsizes['480p'],

                # 360p
                "-map", "[v4out]", "-c:v:3", $using:ffmpegParams.VideoEncoder,
                "-preset:v:3", $using:ffmpegParams.Preset,
                "-tune:v:3", $using:ffmpegParams.Tune,
                "-b:v:3", $bitrates['360p'],
                "-maxrate:v:3", $bitrates['360p'],
                "-bufsize:v:3", $bufsizes['360p']
            )

            # Audio streams
            $audioBitrates = $using:ffmpegParams.AudioBitrates
            if ($hasAudio) {
                for ($i = 0; $i -lt $audioBitrates.Count; $i++) {
                    $command += @(
                        "-map", "a:0", "-c:a:$i", "aac", "-b:a:$i", $audioBitrates[$i], "-ac", "2"
                    )
                }
                $varStreamMap = 'v:0,a:0 v:1,a:1 v:2,a:2 v:3,a:3'
            }
            else {
                $varStreamMap = 'v:0 v:1 v:2 v:3'
            }

            # HLS parameters
            $command += @(
                "-f", "hls",
                "-hls_time", "3",
                "-hls_playlist_type", "vod",
                "-hls_flags", "independent_segments",
                "-hls_segment_type", "mpegts",
                "-hls_segment_filename", "$outputSubfolder/%v/segment_%03d.ts",
                "-master_pl_name", "master.m3u8",
                "-var_stream_map", $varStreamMap,
                "$outputSubfolder/%v/playlist.m3u8"
            )

            # Execute FFmpeg
            $startTime = Get-Date
            $logMessage = "Starting processing: $baseName"
            Add-Content -Path $using:logFilePath -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')][INFO] $logMessage"
        
            # Create a single command string for execution - Fixed version
            $ffmpegCmd = "ffmpeg -hide_banner -loglevel error -stats -i `"$($file.FullName)`" -filter_complex `"$filterComplex`" "
        
            # Add video parameters
            $ffmpegCmd += "-map `"[v1out]`" -c:v:0 $($using:ffmpegParams.VideoEncoder) -preset:v:0 $($using:ffmpegParams.Preset) -tune:v:0 $($using:ffmpegParams.Tune) -b:v:0 $($bitrates['1080p']) -maxrate:v:0 $($bitrates['1080p']) -bufsize:v:0 $($bufsizes['1080p']) "
            $ffmpegCmd += "-map `"[v2out]`" -c:v:1 $($using:ffmpegParams.VideoEncoder) -preset:v:1 $($using:ffmpegParams.Preset) -tune:v:1 $($using:ffmpegParams.Tune) -b:v:1 $($bitrates['720p']) -maxrate:v:1 $($bitrates['720p']) -bufsize:v:1 $($bufsizes['720p']) "
            $ffmpegCmd += "-map `"[v3out]`" -c:v:2 $($using:ffmpegParams.VideoEncoder) -preset:v:2 $($using:ffmpegParams.Preset) -tune:v:2 $($using:ffmpegParams.Tune) -b:v:2 $($bitrates['480p']) -maxrate:v:2 $($bitrates['480p']) -bufsize:v:2 $($bufsizes['480p']) "
            $ffmpegCmd += "-map `"[v4out]`" -c:v:3 $($using:ffmpegParams.VideoEncoder) -preset:v:3 $($using:ffmpegParams.Preset) -tune:v:3 $($using:ffmpegParams.Tune) -b:v:3 $($bitrates['360p']) -maxrate:v:3 $($bitrates['360p']) -bufsize:v:3 $($bufsizes['360p']) "

            # Add audio parameters if audio exists
            if ($hasAudio) {
                for ($i = 0; $i -lt $audioBitrates.Count; $i++) {
                    $ffmpegCmd += "-map a:0 -c:a:$i aac -b:a:$i $($audioBitrates[$i]) -ac 2 "
                }
            }

            # Add HLS parameters
            $ffmpegCmd += "-f hls -g $using:selectedFPS -hls_time 1 -hls_playlist_type vod -hls_flags independent_segments -hls_segment_type mpegts "
            $ffmpegCmd += "-hls_segment_filename `"$outputSubfolder/%v/segment_%03d.ts`" -master_pl_name master.m3u8 "
            $ffmpegCmd += "-var_stream_map `"$varStreamMap`" "
            $ffmpegCmd += "`"$outputSubfolder/%v/playlist.m3u8`""

            # Create temporary files for capturing output and error
            $stdoutFile = Join-Path $outputSubfolder "stdout.tmp"
            $stderrFile = Join-Path $outputSubfolder "stderr.tmp"

            # Log the command being executed
            Add-Content -Path $using:logFilePath -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')][DEBUG] Executing: $ffmpegCmd"

            # Execute ffmpeg using Start-Process with file redirection
            $process = Start-Process -FilePath "ffmpeg" `
                -ArgumentList $ffmpegCmd.Substring("ffmpeg ".Length) `
                -NoNewWindow `
                -Wait `
                -PassThru `
                -RedirectStandardOutput $stdoutFile `
                -RedirectStandardError $stderrFile

            # Get the exit code
            $exitCode = $process.ExitCode

            # Read output and error content from the temporary files
            $output = Get-Content -Path $stdoutFile -Raw -ErrorAction SilentlyContinue
            $errorMsg = Get-Content -Path $stderrFile -Raw -ErrorAction SilentlyContinue

            # Log the output (if any)
            if ($output) {
                Add-Content -Path $using:logFilePath -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')][DEBUG] FFmpeg output: $output"
            }
            else {
                Add-Content -Path $using:logFilePath -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')][DEBUG] No FFmpeg output"
            }

            # Check if there was an error
            if ($exitCode -ne 0) {
                Add-Content -Path $using:logFilePath -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')][ERROR] FFmpeg error: $errorMsg"
                throw "FFmpeg exited with code $exitCode"
            }

            # Clean up temporary files
            Remove-Item -Path $stdoutFile, $stderrFile -Force -ErrorAction SilentlyContinue

            $duration = (Get-Date) - $startTime
            $logMessage = "Completed processing: $baseName ($($duration.TotalSeconds.ToString('0.00'))s)"
            Add-Content -Path $using:logFilePath -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')][INFO] $logMessage"
        }
        catch {
            $logMessage = "Failed to process ${baseName}: $_"
            Add-Content -Path $using:logFilePath -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')][ERROR] $logMessage"
        }

        [System.Threading.Interlocked]::Increment([ref]$using:processedVideoCount) | Out-Null

    } -ThrottleLimit $maxParallelJobs

    while ($processedVideoCount -lt $totalFiles) {
        Write-Progress -Activity "Processing Videos" `
            -Status "Completed $processedVideoCount of $totalFiles" `
            -PercentComplete (($processedVideoCount / $totalFiles) * 100)
        Start-Sleep -Milliseconds 500
    }
}

Write-Log -Message "Video processing loop completed. Processed count: $processedVideoCount, Total files: $totalFiles"
$totalDuration = (Get-Date) - $processingStart
Write-Log -Message "Video processing completed. Total duration: $($totalDuration.TotalMinutes.ToString('0.00')) minutes"
#endregion

#region Folder Organization
Write-Log -Message "Starting folder organization"
Write-Host "Organizing folders..." -ForegroundColor Blue
$foldersToProcess = Get-ChildItem -Directory -Path $outputFolder -Filter "*-*"
$totalFolders = $foldersToProcess.Count
$count = 0

Get-ChildItem -Directory -Path $outputFolder -Filter "*-*" | ForEach-Object {
    $count++
    Write-Progress -Activity "Organizing Folders" `
        -Status "Processing folder $count of $totalFolders" `
        -PercentComplete (($count / $totalFolders) * 100)
    try {
        if ($_.Name -match "^(\d+)-\d+") {
            $parentFolder = Join-Path $outputFolder $matches[1]
            
            if (-not (Test-Path $parentFolder)) {
                $null = New-Item -Path $parentFolder -ItemType Directory
                Write-Log -Message "Created parent folder: $parentFolder"
            }
            
            Move-Item -Path $_.FullName -Destination $parentFolder -ErrorAction Stop
            Write-Log -Message "Moved $($_.Name) to $parentFolder"
        }
    }
    catch {
        Write-Log -Message "Failed to organize folder $($_.Name): $_" -Level "ERROR"
    }
}
Write-Log -Message "Folder organization completed"
#endregion

Write-Host "Script execution completed successfully!" -ForegroundColor Green
Write-Log -Message "Script execution completed successfully"