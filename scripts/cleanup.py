#!/usr/bin/env python
"""
Cleanup script for PyProcessor.

This script cleans up temporary files and build artifacts:
1. Removes __pycache__ directories and .pyc files
2. Removes build artifacts (build/, dist/, *.egg-info/)
3. Removes FFmpeg temporary files (optional)
4. Cleans up log files (optional)

Usage:
    python scripts/cleanup.py [--all] [--ffmpeg] [--logs]

Options:
    --all      Remove all temporary files and build artifacts
    --ffmpeg   Remove FFmpeg temporary files
    --logs     Clean up log files
"""

import os
import sys
import shutil
import argparse
from pathlib import Path

def remove_pycache():
    """Remove __pycache__ directories and .pyc files."""
    print("Removing __pycache__ directories and .pyc files...")
    
    # Find and remove __pycache__ directories
    pycache_dirs = list(Path(".").glob("**/__pycache__"))
    for directory in pycache_dirs:
        shutil.rmtree(directory)
    
    # Find and remove .pyc files
    pyc_files = list(Path(".").glob("**/*.pyc"))
    for file in pyc_files:
        file.unlink()
    
    print(f"✓ Removed {len(pycache_dirs)} __pycache__ directories and {len(pyc_files)} .pyc files")
    return True

def remove_build_artifacts():
    """Remove build artifacts."""
    print("Removing build artifacts...")
    
    # Directories to remove
    build_dirs = ["build", "dist"]
    egg_info_dirs = list(Path(".").glob("*.egg-info"))
    
    # Remove build directories
    removed_count = 0
    for directory in build_dirs:
        if os.path.exists(directory):
            shutil.rmtree(directory)
            removed_count += 1
    
    # Remove egg-info directories
    for directory in egg_info_dirs:
        shutil.rmtree(directory)
        removed_count += 1
    
    print(f"✓ Removed {removed_count} build artifact directories")
    return True

def remove_ffmpeg_temp():
    """Remove FFmpeg temporary files."""
    print("Removing FFmpeg temporary files...")
    
    # Files and directories to remove
    ffmpeg_files = ["ffmpeg.zip", "ffmpeg.7z"]
    ffmpeg_dirs = ["ffmpeg_temp"]
    
    # Remove files
    removed_files = 0
    for file in ffmpeg_files:
        if os.path.exists(file):
            os.remove(file)
            removed_files += 1
    
    # Remove directories
    removed_dirs = 0
    for directory in ffmpeg_dirs:
        if os.path.exists(directory):
            shutil.rmtree(directory)
            removed_dirs += 1
    
    print(f"✓ Removed {removed_files} FFmpeg files and {removed_dirs} FFmpeg directories")
    return True

def clean_logs():
    """Clean up log files."""
    print("Cleaning up log files...")
    
    # Find log files
    log_dir = Path("video_processor/logs")
    if not log_dir.exists():
        print("✓ No log directory found")
        return True
    
    # Keep .gitkeep file
    log_files = [f for f in log_dir.glob("*") if f.name != ".gitkeep"]
    
    # Remove log files
    for file in log_files:
        file.unlink()
    
    print(f"✓ Removed {len(log_files)} log files")
    return True

def main():
    """Parse arguments and run cleanup."""
    parser = argparse.ArgumentParser(description="Clean up PyProcessor temporary files and build artifacts")
    parser.add_argument("--all", action="store_true", help="Remove all temporary files and build artifacts")
    parser.add_argument("--ffmpeg", action="store_true", help="Remove FFmpeg temporary files")
    parser.add_argument("--logs", action="store_true", help="Clean up log files")
    args = parser.parse_args()
    
    # If no specific options are provided, just remove pycache and build artifacts
    if not (args.all or args.ffmpeg or args.logs):
        remove_pycache()
        remove_build_artifacts()
        return True
    
    # Otherwise, perform the requested cleanup operations
    if args.all or args.ffmpeg:
        remove_ffmpeg_temp()
    
    if args.all:
        remove_pycache()
        remove_build_artifacts()
    
    if args.all or args.logs:
        clean_logs()
    
    print("\n✓ Cleanup completed!")
    return True

if __name__ == "__main__":
    main()
