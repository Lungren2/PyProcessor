import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

print("Testing imports...")

try:
    from pyprocessor.utils.core.cache_manager import cache_get, cache_set

    print("✓ Successfully imported from cache_manager")
except ImportError as e:
    print(f"✗ Failed to import from cache_manager: {e}")

try:
    from pyprocessor.utils.process.resource_manager import get_cpu_usage

    print("✓ Successfully imported from resource_manager")
except ImportError as e:
    print(f"✗ Failed to import from resource_manager: {e}")

try:
    from pyprocessor.utils.core.notification_manager import add_notification

    print("✓ Successfully imported from notification_manager")
except ImportError as e:
    print(f"✗ Failed to import from notification_manager: {e}")

try:
    from pyprocessor.utils.media.ffmpeg_manager import FFmpegManager

    print("✓ Successfully imported from ffmpeg_manager")
except ImportError as e:
    print(f"✗ Failed to import from ffmpeg_manager: {e}")

print("Import test completed")
