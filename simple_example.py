"""
A simple example script that demonstrates the core functionality of PyProcessor.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

print("PyProcessor Simple Example")
print("=========================")

# Create necessary directories
print("\nCreating necessary directories...")
logs_dir = Path("pyprocessor/logs")
profiles_dir = Path("pyprocessor/profiles")

logs_dir.mkdir(parents=True, exist_ok=True)
profiles_dir.mkdir(parents=True, exist_ok=True)

print(f"✓ Created logs directory: {logs_dir}")
print(f"✓ Created profiles directory: {profiles_dir}")

# Create a simple log file
print("\nCreating a simple log file...")
log_file = logs_dir / "simple_example.log"
with open(log_file, "w") as f:
    f.write("This is a simple log file created by the simple example script.\n")
print(f"✓ Created log file: {log_file}")

# Create a simple profile file
print("\nCreating a simple profile file...")
profile_file = profiles_dir / "simple_profile.json"
with open(profile_file, "w") as f:
    f.write(
        '{\n  "name": "Simple Profile",\n  "description": "A simple profile created by the simple example script.",\n  "created": "2023-01-01"\n}\n'
    )
print(f"✓ Created profile file: {profile_file}")

print("\nSimple example completed successfully!")
