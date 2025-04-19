# Dependency Management

This document provides information about managing dependencies in PyProcessor across different platforms.

## Dependency Structure

PyProcessor uses a structured approach to manage dependencies across platforms:

- **Base Dependencies**: Common dependencies required on all platforms
- **Platform-Specific Dependencies**: Dependencies required only on specific platforms
- **Optional Dependencies**: Dependencies that provide additional functionality
- **Development Dependencies**: Dependencies required only for development

## Requirements Files

The following requirements files are available:

- `requirements.txt`: Base dependencies with platform markers
- `requirements-windows.txt`: Windows-specific dependencies
- `requirements-macos.txt`: macOS-specific dependencies
- `requirements-linux.txt`: Linux-specific dependencies
- `requirements-dev.txt`: Development dependencies

## Platform-Specific Dependencies

### Windows

```
pywin32>=305
winshell>=0.6
```

### macOS

```
pyobjc-core>=9.2
pyobjc-framework-Cocoa>=9.2
```

### Linux

```
python-xlib>=0.33
dbus-python>=1.3.2
```

## Optional Dependencies

PyProcessor supports optional dependencies that can be installed using extras:

- **dev**: Development tools (black, flake8, etc.)
- **ffmpeg**: FFmpeg Python bindings

To install with extras:

```bash
pip install -e ".[dev]"  # Install development dependencies
pip install -e ".[ffmpeg]"  # Install FFmpeg dependencies
pip install -e ".[dev,ffmpeg]"  # Install both
```

## Managing Dependencies

### Using the Dependency Management Script

PyProcessor includes a dependency management script that can be used to check, install, and update dependencies:

```bash
# Check for missing dependencies
python scripts/manage_dependencies.py --check

# Install dependencies
python scripts/manage_dependencies.py --install

# Update dependencies
python scripts/manage_dependencies.py --update

# Install with extras
python scripts/manage_dependencies.py --install --extras dev
```

### Using the Development Setup Script

The development setup script can be used to set up a development environment with all dependencies:

```bash
# Set up development environment for the current platform
python scripts/dev_setup.py

# Set up development environment for a specific platform
python scripts/dev_setup.py --platform windows
python scripts/dev_setup.py --platform macos
python scripts/dev_setup.py --platform linux
```

## Adding New Dependencies

When adding new dependencies to PyProcessor, follow these guidelines:

1. **Base Dependencies**: Add to `requirements.txt` and `setup.py`
2. **Platform-Specific Dependencies**: Add to the appropriate platform-specific requirements file and `setup.py`
3. **Optional Dependencies**: Add to `setup.py` under `extras_require`
4. **Development Dependencies**: Add to `requirements-dev.txt` and `setup.py` under `extras_require['dev']`

Example for adding a new dependency:

```python
# In setup.py
install_requires = [
    "tqdm>=4.60.0",
    "new-dependency>=1.0.0",  # Add base dependency here
]

# Platform-specific dependencies
if sys.platform == "win32":
    install_requires.extend([
        "pywin32>=305",
        "winshell>=0.6",
        "windows-specific-dependency>=1.0.0",  # Add Windows-specific dependency here
    ])

# Optional dependencies
extras_require = {
    'dev': [
        'black>=23.7.0',
        'new-dev-dependency>=1.0.0',  # Add development dependency here
    ],
    'ffmpeg': [
        'ffmpeg-python>=0.2.0',
    ],
    'new-extra': [
        'new-optional-dependency>=1.0.0',  # Add new optional dependency here
    ],
}
```

## Version Pinning

PyProcessor uses version pinning to ensure compatibility:

- **Minimum Version**: `>=x.y.z` specifies the minimum version required
- **Exact Version**: `==x.y.z` specifies an exact version
- **Compatible Release**: `~=x.y.z` specifies a compatible release

For critical dependencies, consider using exact versions to prevent compatibility issues.

## Virtual Environments

It's recommended to use virtual environments when working with PyProcessor:

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate

# Install dependencies
python scripts/manage_dependencies.py --install --extras dev
```

## Troubleshooting

### Common Issues

1. **Dependency Conflicts**: If you encounter dependency conflicts, try installing dependencies one by one or use `pip install --no-deps` to skip dependencies.

2. **Platform-Specific Issues**: If a dependency fails to install on a specific platform, check if there's a platform-specific alternative or if the dependency is actually needed on that platform.

3. **Missing Dependencies**: If you're missing dependencies, run `python scripts/manage_dependencies.py --check` to identify and install them.

### Updating Dependencies

To update dependencies to the latest versions:

```bash
python scripts/manage_dependencies.py --update
```

This will update all dependencies to their latest versions while respecting version constraints.
