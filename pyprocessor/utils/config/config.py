import warnings

from pyprocessor.utils.config_manager import Config as NewConfig

# Show deprecation warning
warnings.warn(
    "The config module is deprecated and will be removed in a future version. "
    "Please use the config_manager module instead.",
    DeprecationWarning,
    stacklevel=2
)


class Config(NewConfig):
    """Enhanced configuration management for video processor

    This is a compatibility class that inherits from the new Config class
    in the config_manager module.
    """

    def __init__(self):
        """Initialize the configuration."""
        super().__init__()

        # Show deprecation warning
        warnings.warn(
            "The Config class is deprecated and will be removed in a future version. "
            "Please use the ConfigManager class from config_manager module instead.",
            DeprecationWarning,
            stacklevel=2
        )

    # All methods are inherited from the new Config class
