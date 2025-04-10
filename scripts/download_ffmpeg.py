"""
Script to download and extract FFmpeg binaries for packaging PyProcessor.
"""
import os
import sys
import zipfile
import shutil
from pathlib import Path
import urllib.request

def download_ffmpeg():
    """Download and extract FFmpeg binaries for packaging."""
    print("Downloading FFmpeg binaries...")
    
    # Create directories if they don't exist
    os.makedirs("ffmpeg_temp", exist_ok=True)
    
    # FFmpeg download URL
    ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    zip_path = "ffmpeg.zip"
    
    # Download FFmpeg
    try:
        print(f"Downloading from {ffmpeg_url}...")
        urllib.request.urlretrieve(ffmpeg_url, zip_path)
        print("Download complete.")
    except Exception as e:
        print(f"Error downloading FFmpeg: {str(e)}")
        return False
    
    # Extract FFmpeg
    try:
        print("Extracting FFmpeg...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall("ffmpeg_temp")
        print("Extraction complete.")
    except Exception as e:
        print(f"Error extracting FFmpeg: {str(e)}")
        return False
    
    # Create README file
    readme_path = "ffmpeg_temp/README.txt"
    readme_content = """FFmpeg Binaries for PyProcessor
==============================

These FFmpeg binaries are bundled with PyProcessor to enable video processing functionality without requiring a separate FFmpeg installation.

Source: https://www.gyan.dev/ffmpeg/builds/
Version: 7.1.1 (essentials build)

FFmpeg is licensed under the GNU Lesser General Public License (LGPL) version 2.1 or later.
For more information, visit: https://ffmpeg.org/legal.html

These binaries are included for convenience and are not modified in any way from their original distribution.
"""
    
    try:
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        print("Created README file.")
    except Exception as e:
        print(f"Error creating README file: {str(e)}")
    
    print("FFmpeg preparation complete. You can now run PyInstaller to create the executable.")
    return True

if __name__ == "__main__":
    download_ffmpeg()
