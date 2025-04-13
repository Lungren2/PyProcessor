#!/usr/bin/env python
"""
Test script to verify the regex patterns used in the profiles.
"""
import re
import json
from pathlib import Path

def test_file_rename_pattern():
    """Test the file_rename_pattern to ensure it captures the entire numeral section."""
    # Load the pattern from the high_quality.json profile
    profile_path = Path("pyprocessor/profiles/high_quality.json")
    with open(profile_path, "r") as f:
        profile = json.load(f)

    pattern = profile["file_rename_pattern"]
    print(f"Testing pattern: {pattern}")

    # Test cases
    test_cases = [
        ("123-456.mp4", "123-456"),
        ("video-123-456.mp4", "123-456"),
        ("prefix_123-456_suffix.mp4", "123-456"),
        ("123-456_720p.mp4", "123-456"),
        ("movie_123-456_1080p.mp4", "123-456"),
        ("tv_show_123-456_season01.mp4", "123-456"),
        ("123-456-extra.mp4", "123-456"),  # Additional test case with hyphen
    ]

    # Run tests
    for filename, expected in test_cases:
        match = re.search(pattern, filename)
        if match:
            result = match.group(1)
            status = "✓" if result == expected else "✗"
            print(f"{status} {filename}: Expected '{expected}', Got '{result}'")
        else:
            print(f"✗ {filename}: No match found")

if __name__ == "__main__":
    test_file_rename_pattern()
