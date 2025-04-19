#!/usr/bin/env python3
"""
Cross-platform cleanup script for PyProcessor.

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
import shutil
import argparse
from pathlib import Path


def remove_pycache():
    """Remove __pycache__ directories and .pyc files."""
    print("Removing __pycache__ directories and .pyc files...")

    # Find and remove __pycache__ directories
    pycache_dirs = list(Path(".").glob("**/__pycache__"))
    removed_dirs = 0
    for directory in pycache_dirs:
        try:
            shutil.rmtree(directory)
            removed_dirs += 1
        except Exception as e:
            print(f"✗ Failed to remove {directory}: {e}")

    # Find and remove .pyc files
    pyc_files = list(Path(".").glob("**/*.pyc"))
    removed_files = 0
    for file in pyc_files:
        try:
            file.unlink()
            removed_files += 1
        except Exception as e:
            print(f"✗ Failed to remove {file}: {e}")

    print(
        f"✓ Removed {removed_dirs} __pycache__ directories and {removed_files} .pyc files"
    )
    return True


def remove_build_artifacts():
    """Remove build artifacts."""
    print("Removing build artifacts...")

    # Directories to remove
    build_dirs = ["build", "dist", ".pytest_cache", "htmlcov"]
    glob_patterns = ["*.egg-info", "*.spec"]

    # Remove build directories
    removed_count = 0
    for directory in build_dirs:
        if os.path.exists(directory):
            try:
                shutil.rmtree(directory)
                removed_count += 1
                print(f"✓ Removed {directory}")
            except Exception as e:
                print(f"✗ Failed to remove {directory}: {e}")

    # Remove directories matching glob patterns
    for pattern in glob_patterns:
        for path in Path(".").glob(pattern):
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                removed_count += 1
                print(f"✓ Removed {path}")
            except Exception as e:
                print(f"✗ Failed to remove {path}: {e}")

    print(f"✓ Removed {removed_count} build artifacts in total")
    return True


def remove_ffmpeg_temp():
    """Remove FFmpeg temporary files."""
    print("Removing FFmpeg temporary files...")

    # Files and directories to remove
    ffmpeg_files = ["ffmpeg.zip", "ffmpeg.7z", "ffmpeg.tar.gz", "ffmpeg.tar.xz"]
    ffmpeg_dirs = ["ffmpeg_temp"]

    # Remove files
    removed_files = 0
    for file in ffmpeg_files:
        if os.path.exists(file):
            try:
                os.remove(file)
                removed_files += 1
                print(f"✓ Removed {file}")
            except Exception as e:
                print(f"✗ Failed to remove {file}: {e}")

    # Remove directories
    removed_dirs = 0
    for directory in ffmpeg_dirs:
        if os.path.exists(directory):
            try:
                shutil.rmtree(directory)
                removed_dirs += 1
                print(f"✓ Removed {directory}")
            except Exception as e:
                print(f"✗ Failed to remove {directory}: {e}")

    print(
        f"✓ Removed {removed_files} FFmpeg files and {removed_dirs} FFmpeg directories in total"
    )
    return True


def clean_logs():
    """Clean up log files."""
    print("Cleaning up log files...")

    # Find log files
    log_dir = Path("pyprocessor/logs")
    if not log_dir.exists():
        print("✓ No log directory found")
        return True

    # Keep .gitkeep file
    log_files = [f for f in log_dir.glob("*") if f.name != ".gitkeep"]

    # Remove log files
    removed_count = 0
    for file in log_files:
        try:
            file.unlink()
            removed_count += 1
            print(f"✓ Removed log file: {file}")
        except Exception as e:
            print(f"✗ Failed to remove log file {file}: {e}")

    print(f"✓ Removed {removed_count} log files in total")
    return True


def main():
    """Parse arguments and run cleanup."""
    parser = argparse.ArgumentParser(
        description="Clean up PyProcessor temporary files and build artifacts"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Remove all temporary files and build artifacts",
    )
    parser.add_argument(
        "--ffmpeg", action="store_true", help="Remove FFmpeg temporary files"
    )
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
    success = main()
    import sys
    sys.exit(0 if success else 1)
