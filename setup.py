import sys
from setuptools import setup, find_packages

# Base requirements for all platforms
install_requires = [
    "tqdm>=4.60.0",
]

# Platform-specific requirements
if sys.platform == "win32":
    # Windows-specific dependencies
    install_requires.extend([
        "pywin32>=305",
        "winshell>=0.6",
    ])
elif sys.platform == "darwin":
    # macOS-specific dependencies
    install_requires.extend([
        "pyobjc-core>=9.2",
        "pyobjc-framework-Cocoa>=9.2",
    ])
elif sys.platform.startswith("linux"):
    # Linux-specific dependencies
    install_requires.extend([
        "python-xlib>=0.33",
        "dbus-python>=1.3.2",
    ])

# Optional dependencies
extras_require = {
    'dev': [
        'black>=23.7.0',
        'flake8>=6.1.0',
        'isort>=5.12.0',
        'pyinstaller>=5.13.0',
    ],
    'ffmpeg': [
        'ffmpeg-python>=0.2.0',
    ],
}

setup(
    name="pyprocessor",
    version="0.1.0",
    packages=find_packages(),
    install_requires=install_requires,
    entry_points={
        "console_scripts": [
            "pyprocessor=pyprocessor.main:main",
        ],
    },
    author="Ethan Ogle",
    author_email="ethanogle012@outlook.com",
    description="Cross-platform media processing engine",
    long_description="""PyProcessor is a cross-platform media processing engine
    that provides powerful video encoding capabilities using FFmpeg.
    It supports various encoding formats, parallel processing, and server optimization.""",
    keywords="video, encoding, ffmpeg, hls, media, processing",
    python_requires=">=3.6,<3.14",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Topic :: Multimedia :: Video",
        "Topic :: Multimedia :: Video :: Conversion",
    ],
    project_urls={
        "Source": "https://github.com/Lungren2/PyProcessor",
        "Bug Reports": "https://github.com/Lungren2/PyProcessor/issues",
    },
    include_package_data=True,
    package_data={
        "pyprocessor": [
            "profiles/*",
            "logs/.gitkeep",
        ],
    },
    extras_require=extras_require,
)
