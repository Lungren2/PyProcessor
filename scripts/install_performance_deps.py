#!/usr/bin/env python
"""
Script to install dependencies required for performance testing.

This script installs and verifies the dependencies needed for running
performance tests in the PyProcessor project. It includes version pinning
to ensure compatibility and comprehensive error handling.

Usage:
    python install_performance_deps.py [--dev] [--upgrade] [--verbose]

Options:
    --dev       Install development dependencies as well
    --upgrade   Upgrade existing packages to specified versions
    --verbose   Show detailed output during installation

Exit codes:
    0 - Success
    1 - General error
    2 - Package installation error
    3 - Package verification error
    4 - Invalid arguments
"""

import argparse
import importlib
import logging
import os
import platform
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("install_performance_deps")

# Exit codes
EXIT_SUCCESS = 0
EXIT_GENERAL_ERROR = 1
EXIT_PACKAGE_INSTALL_ERROR = 2
EXIT_PACKAGE_VERIFY_ERROR = 3
EXIT_INVALID_ARGS = 4

# Version-pinned dependencies
DEPENDENCIES = {
    # Core performance testing dependencies
    "psutil": "==5.9.5",  # System monitoring
    "pytest": "==7.3.1",  # Testing framework
    "pytest-cov": "==4.1.0",  # Coverage reporting
    "pytest-html": "==3.2.0",  # HTML test reports
    "pytest-benchmark": "==4.0.0",  # Benchmarking

    # Development dependencies
    "dev": {
        "black": "==23.3.0",  # Code formatting
        "flake8": "==6.0.0",  # Linting
        "mypy": "==1.3.0",  # Type checking
        "isort": "==5.12.0",  # Import sorting
    }
}

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description="Install dependencies required for performance testing."
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Install development dependencies as well"
    )
    parser.add_argument(
        "--upgrade",
        action="store_true",
        help="Upgrade existing packages to specified versions"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output during installation"
    )

    return parser.parse_args()

def get_pip_command() -> List[str]:
    """Get the appropriate pip command based on the environment.

    Returns:
        List[str]: The pip command as a list of strings
    """
    # Check if we're in a virtual environment
    in_venv = hasattr(sys, 'real_prefix') or \
              (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

    # Use pip directly if in a virtual environment, otherwise use python -m pip
    if in_venv and os.path.exists(os.path.join(sys.prefix, 'bin', 'pip')) or \
       (platform.system() == "Windows" and
        os.path.exists(os.path.join(sys.prefix, 'Scripts', 'pip.exe'))):
        return ["pip"]
    else:
        return [sys.executable, "-m", "pip"]

def build_install_command(
    dependencies: Dict[str, str],
    upgrade: bool = False,
    verbose: bool = False
) -> List[str]:
    """Build the pip install command with the specified dependencies.

    Args:
        dependencies: Dictionary of package names and version constraints
        upgrade: Whether to upgrade existing packages
        verbose: Whether to show detailed output

    Returns:
        List[str]: The pip install command as a list of strings
    """
    cmd = get_pip_command() + ["install"]

    # Add options
    if upgrade:
        cmd.append("--upgrade")
    if verbose:
        cmd.append("--verbose")
    else:
        cmd.append("--quiet")

    # Add dependencies with version constraints
    for package, version in dependencies.items():
        cmd.append(f"{package}{version}")

    return cmd

def run_command(cmd: List[str], description: str) -> Tuple[bool, Optional[str]]:
    """Run a command and handle its output and errors.

    Args:
        cmd: Command to run as a list of strings
        description: Description of the command for logging

    Returns:
        Tuple[bool, Optional[str]]: Success status and error message if any
    """
    logger.info(f"{description}...")
    if logger.level == logging.DEBUG:
        logger.debug(f"Running command: {' '.join(cmd)}")

    try:
        # Run the command and capture output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE if logger.level != logging.DEBUG else None,
            stderr=subprocess.PIPE if logger.level != logging.DEBUG else None,
            universal_newlines=True,
            text=True
        )

        stdout, stderr = process.communicate()

        if process.returncode != 0:
            error_msg = stderr or "Unknown error"
            logger.error(f"Command failed with exit code {process.returncode}")
            logger.error(f"Error details: {error_msg}")
            return False, error_msg

        if logger.level == logging.DEBUG and stdout:
            logger.debug(f"Command output: {stdout}")

        return True, None
    except Exception as e:
        logger.error(f"Exception while running command: {e}")
        return False, str(e)

def verify_installation(packages: List[str]) -> Tuple[bool, List[str]]:
    """Verify that the specified packages are installed correctly.

    Args:
        packages: List of package names to verify

    Returns:
        Tuple[bool, List[str]]: Success status and list of failed packages
    """
    logger.info("Verifying installed packages...")
    failed_packages = []

    for package in packages:
        try:
            # Try to import the package
            importlib.import_module(package)
            logger.info(f"✓ {package} verified successfully")
        except ImportError:
            # Some packages have different import names than their PyPI names
            # Handle common cases
            alt_name = None
            if package == "pytest-cov":
                alt_name = "pytest_cov"
            elif package == "pytest-html":
                alt_name = "pytest_html"
            elif package == "pytest-benchmark":
                alt_name = "pytest_benchmark"

            if alt_name:
                try:
                    importlib.import_module(alt_name)
                    logger.info(f"✓ {package} verified successfully (as {alt_name})")
                    continue
                except ImportError:
                    pass

            logger.error(f"✗ Failed to verify {package}")
            failed_packages.append(package)

    return len(failed_packages) == 0, failed_packages

def install_dependencies(dev: bool = False, upgrade: bool = False, verbose: bool = False) -> int:
    """Install dependencies required for performance testing.

    Args:
        dev: Whether to install development dependencies
        upgrade: Whether to upgrade existing packages
        verbose: Whether to show detailed output

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Set logging level based on verbosity
    if verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")

    # Get system information
    logger.info(f"Python version: {platform.python_version()}")
    logger.info(f"Platform: {platform.platform()}")

    # Prepare dependencies
    dependencies = {}
    dependencies.update({k: v for k, v in DEPENDENCIES.items() if k != "dev"})

    if dev:
        logger.info("Including development dependencies")
        dependencies.update(DEPENDENCIES["dev"])

    # Update pip first
    pip_cmd = get_pip_command() + ["install", "--upgrade", "pip"]
    success, error = run_command(pip_cmd, "Updating pip")
    if not success:
        logger.error(f"Failed to update pip: {error}")
        # Continue anyway, as this is not critical

    # Install dependencies
    install_cmd = build_install_command(dependencies, upgrade, verbose)
    success, error = run_command(install_cmd, "Installing dependencies")

    if not success:
        logger.error(f"Failed to install dependencies: {error}")
        return EXIT_PACKAGE_INSTALL_ERROR

    # Verify installation
    # We only verify the importable packages (excluding dev tools for simplicity)
    packages_to_verify = ["psutil", "pytest", "pytest-cov", "pytest-html", "pytest-benchmark"]
    success, failed_packages = verify_installation([p.split('==')[0] for p in packages_to_verify])

    if not success:
        logger.error(f"Failed to verify these packages: {', '.join(failed_packages)}")
        return EXIT_PACKAGE_VERIFY_ERROR

    logger.info("All dependencies installed and verified successfully")
    return EXIT_SUCCESS

def main() -> int:
    """Main entry point for the script.

    Returns:
        int: Exit code
    """
    try:
        args = parse_arguments()
        return install_dependencies(args.dev, args.upgrade, args.verbose)
    except KeyboardInterrupt:
        logger.error("\nInstallation interrupted by user")
        return EXIT_GENERAL_ERROR
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if logger.level == logging.DEBUG:
            import traceback
            logger.debug(traceback.format_exc())
        return EXIT_GENERAL_ERROR

if __name__ == "__main__":
    sys.exit(main())
